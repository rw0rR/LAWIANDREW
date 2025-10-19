import os
import json
import time
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from firebase_admin import initialize_app, credentials, auth, firestore

# --- ADMIN BİLGİLERİ (Hard-Coded) ---
# UYARI: Bu yöntem sadece demo/test ortamları için uygundur, güvenli değildir.
ADMIN_USERNAME = 'rwr'
ADMIN_PASSWORD = '797608' 
# -----------------------------------

# --- Ortam Değişkenlerini Güvenli Yükleme ---
# Firebase ve Uygulama Kimlikleri
FIREBASE_CONFIG_JSON = os.environ.get('FIREBASE_CONFIG')
APP_ID = os.environ.get('APP_ID')
INITIAL_AUTH_TOKEN = os.environ.get('INITIAL_AUTH_TOKEN')
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')

if not all([FIREBASE_CONFIG_JSON, APP_ID, INITIAL_AUTH_TOKEN, SECRET_KEY]):
    print("HATA: Gerekli Ortam Değişkenleri (FIREBASE_CONFIG, APP_ID, TOKEN, SECRET_KEY) eksik.")
    # Sadece geliştirme amacıyla varsayılan değerler atanır, canlı ortamda çalışmayacaktır.
    if not FIREBASE_CONFIG_JSON: FIREBASE_CONFIG_JSON = '{}'
    if not APP_ID: APP_ID = 'default-app-id'
    if not INITIAL_AUTH_TOKEN: INITIAL_AUTH_TOKEN = 'default-token'
    if not SECRET_KEY: SECRET_KEY = 'super-secret-key'

# Flask Uygulamasını Başlat
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app)

# Firebase Yapılandırması
try:
    FIREBASE_CONFIG = json.loads(FIREBASE_CONFIG_JSON)
    # Firestore Client'ı başlat (Sunucu tarafı işlemler için)
    # Canvas ortamında Admin SDK'nın çalışması için gerekli değil, sadece referans almak için kullanıyoruz.
    # initialize_app(credentials.Certificate('path/to/your/serviceAccountKey.json')) 
except json.JSONDecodeError:
    print("HATA: FIREBASE_CONFIG değişkeni geçerli bir JSON formatında değil!")
    FIREBASE_CONFIG = {}
except ValueError:
    print("Firebase Admin SDK zaten başlatılmış.")

# --- Veritabanı (Firestore) Referans Yolu ---
def get_rooms_ref():
    """ Firestore'daki sohbet odalarının koleksiyon yolunu döndürür. """
    # Firestore client'ı sadece ortam değişkenleri tanımlıyken başlat
    try:
        db = firestore.client()
        return db.collection('artifacts').document(APP_ID).collection('public').document('data').collection('rooms')
    except Exception as e:
        print(f"Firestore başlatma hatası (Admin yetkisi için önemli): {e}")
        return None # Hata durumunda None döndür

# --- Middleware (Oturum Kontrolü) ---
@app.before_request
def check_auth_status():
    """Her istekten önce oturum durumunu kontrol eder."""
    if 'user_id' not in session:
        session['user_id'] = f"Anon-{time.time_ns()}"
        session['is_admin'] = False
    
    # Oturumda admin kontrolü yoksa varsayılan False yap
    if 'is_admin' not in session:
        session['is_admin'] = False

# --- ROUTES ---

@app.route('/')
def index():
    """Ana giriş sayfası"""
    return render_template('index.html', firebase_config=FIREBASE_CONFIG_JSON, app_id=APP_ID, initial_auth_token=INITIAL_AUTH_TOKEN)

@app.route('/dashboard')
def dashboard():
    """Oda listesi ve Admin paneli"""
    return render_template('dashboard.html', is_admin=session.get('is_admin', False))

@app.route('/join', methods=['POST'])
def join():
    """Odaya katılma isteğini işler ve admin yetkisini kontrol eder."""
    username = request.form.get('username', 'Misafir')
    room = request.form.get('room_code')
    admin_password = request.form.get('admin_password', '') # Yeni admin şifre alanı
    actual_uid = request.form.get('actual_uid', None) # Firebase Auth'tan gelen gerçek UID

    if not username or not room:
        return redirect(url_for('dashboard'))

    session['username'] = username
    session['room'] = room
    session['actual_uid'] = actual_uid

    # --- YENİ HARD-CODED ADMIN KONTROLÜ ---
    if username == ADMIN_USERNAME and admin_password == ADMIN_PASSWORD:
        session['is_admin'] = True
        print(f"Admin ({username}) başarıyla giriş yaptı.")
    else:
        session['is_admin'] = False
        print(f"Kullanıcı ({username}) giriş yaptı. Admin yetkisi yok.")

    return redirect(url_for('room_page'))

@app.route('/room')
def room_page():
    """Sohbet odası sayfası"""
    if 'room' not in session or 'username' not in session:
        return redirect(url_for('dashboard'))
    
    # is_admin bilgisini odaya gönder
    return render_template('room.html', room=session['room'], username=session['username'], is_admin=session.get('is_admin', False))

@app.route('/delete_room', methods=['POST'])
def delete_room():
    """Sadece Admin'in odaları silmesini sağlar."""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Erişim reddedildi. Bu işlemi sadece yöneticiler yapabilir.'}), 403

    room_to_delete = request.form.get('room')
    if not room_to_delete:
        return jsonify({'success': False, 'message': 'Silinecek oda belirtilmemiş.'}), 400

    rooms_ref = get_rooms_ref()
    if not rooms_ref:
         return jsonify({'success': False, 'message': 'Veritabanı bağlantısı kurulamadı.'}), 500

    try:
        # Admin yetkisi varsa odanın Firestore belgesini siler
        doc_ref = rooms_ref.document(room_to_delete)
        doc_ref.delete()
        
        # Tüm SocketIO bağlantılarına odanın silindiğini bildir
        socketio.emit('room_deleted', {'room': room_to_delete}, broadcast=True)

        return jsonify({'success': True, 'message': f'Oda "{room_to_delete}" başarıyla silindi.'}), 200
    except Exception as e:
        print(f"Oda silinirken hata oluştu: {e}")
        return jsonify({'success': False, 'message': f'Sunucu hatası: {e}'}), 500


# --- SOCKET.IO EVENTS ---

@socketio.on('join')
def on_join(data):
    """Kullanıcı bir odaya katıldığında"""
    room = session.get('room')
    username = session.get('username')
    
    if not room or not username:
        return

    join_room(room)
    send({'username': 'Sistem', 'message': f'{username} odaya katıldı.', 'timestamp': time.time()}, to=room)
    print(f'{username} odaya katıldı: {room}')

@socketio.on('message')
def handle_message(data):
    """Kullanıcı mesaj gönderdiğinde"""
    room = session.get('room')
    username = session.get('username')
    
    if not room or not username:
        return

    message_data = {
        'username': username,
        'message': data['message'],
        'timestamp': time.time()
    }
    
    # Odaya mesajı yayınla
    send(message_data, to=room)
    print(f'[{room}] {username}: {data["message"]}')

@socketio.on('leave')
def on_leave(data):
    """Kullanıcı odadan ayrıldığında"""
    room = session.get('room')
    username = session.get('username')

    if not room or not username:
        return
        
    leave_room(room)
    send({'username': 'Sistem', 'message': f'{username} odadan ayrıldı.', 'timestamp': time.time()}, to=room)
    print(f'{username} odadan ayrıldı: {room}')

if __name__ == '__main__':
    socketio.run(app, debug=True)
