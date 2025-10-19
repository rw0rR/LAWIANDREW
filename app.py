# app.py (Nihai Versiyon: Kalıcı Veri Kaydı ve Admin İşlevleri)

from flask import Flask, render_template, request, redirect, url_for, session, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename 
import secrets 
import string
import time
import os 
import json # JSON kütüphanesi eklendi
from functools import wraps 
from flask_socketio import SocketIO, join_room, leave_room, send, emit

app = Flask(__name__)
# GÜVENLİK ANAHTARI
app.secret_key = 'cok_gizli_bir_anahtar_ve_sessiyon_sifresi' 

# ----------------- DOSYA YÜKLEME AYARLARI -----------------
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'data.json' # Kalıcı veri saklama dosyası

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- SOCKETIO ENTEGRASYONU -----------------
socketio = SocketIO(app, cors_allowed_origins="*") 

# ----------------- BELLEK VERİ YAPILARI -----------------
# Bu yapılar dosya yüklenene kadar boş kalır.
users = {} 
rooms = {} 
messages = {} 
news_articles = {} 
news_counter = 1 
admins = {} 
# ----------------- ------------------------------------


# ----------------- VERİ KAYIT YARDIMCI FONKSİYONLARI -----------------

def load_data():
    """Uygulama başlatıldığında verileri data.json'dan yükler."""
    global users, rooms, news_articles, news_counter, admins
    
    # Yeni adminlerinizi ve varsayılan admini tutacak geçici set
    default_admins_to_add = {
        'admin_kadir': 'sifre123', # Mevcut varsayılan admin
        'rwr': '797608'             # Yeni istediğiniz admin
    }

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                users = data.get('users', {})
                # news_articles'ın anahtarlarını int'e dönüştür (JSON'da string olarak saklanır)
                news_articles = {int(k): v for k, v in data.get('news_articles', {}).items()} 
                news_counter = data.get('news_counter', 1)
                admins = data.get('admins', {})
                
                # Mevcut adminler yüklendikten sonra, eksik olan varsayılan adminleri ekle
                for username, password in default_admins_to_add.items():
                    if username not in admins:
                        admins[username] = generate_password_hash(password)
                        print(f"Varsayılan admin '{username}' eklendi.")
                
        except (json.JSONDecodeError, FileNotFoundError):
            print(f"UYARI: {DATA_FILE} bozuk veya bulunamadı. Varsayılan verilerle devam ediliyor.")
    
    # Eğer dosya hiç yoksa veya yükleme başarısız olursa, tüm varsayılan adminleri ekle
    if not admins:
        for username, password in default_admins_to_add.items():
            admins[username] = generate_password_hash(password)
            print(f"İlk çalıştırmada varsayılan admin '{username}' eklendi.")

    # Eğer adminler yüklendi ancak 'rwr' eksikse (eski data.json'dan gelme ihtimali)
    if 'rwr' not in admins:
        admins['rwr'] = generate_password_hash('797608')

    save_data() # Yeni adminler eklendiği için veriyi kaydet
    print("Veriler başarıyla yüklendi ve güncellendi.")

def save_data():
    """Kullanıcıları, yöneticileri ve haberleri data.json'a kaydeder."""
    # Mesajlar ve aktif odalar kaydedilmez.
    data_to_save = {
        'users': users,
        'admins': admins,
        'news_articles': news_articles,
        'news_counter': news_counter
    }
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print("Veriler başarıyla data.json dosyasına kaydedildi.")
    except Exception as e:
        print(f"HATA: Veri kaydı sırasında hata oluştu: {e}")

# ----------------- YARDIMCI FONKSİYONLAR VE DEKORATÖRLER -----------------

def generate_room_code(length=6):
    """Rastgele 6 haneli kod üretir."""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(characters) for _ in range(length))
        if code not in rooms:
            return code

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            # Hata mesajı ile login sayfasına yönlendir
            from flask import flash
            flash('Bu sayfayı görmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login')) 
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            # Hata mesajı ile admin girişine yönlendir
            from flask import flash
            flash('Bu sayfa sadece yöneticilere özeldir.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function
# ----------------- ------------------------------------


# ----------------- ODA SEKME TEMİZLEME İŞLEMİ (KRİTİK DÜZELTME) -----------------
from flask import flash # Flash mesajları için import eklendi

@app.before_request
def clear_current_room():
    # Bu fonksiyon, oda içinde olmadığınızda menü sekmesinin düzgün çalışmasını sağlar
    allowed_endpoints = ['room_page', 'join_room_route', 'create_room', 'leave_room_route', 'static', 'admin_edit_news']
    
    if request.endpoint and request.endpoint not in allowed_endpoints:
        if 'current_room_code' in session:
            del session['current_room_code']

# ----------------- FLASK ROTALARI (Giriş/Kayıt/Çıkış) -----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users or username in admins:
            flash("Bu kullanıcı adı zaten alınmış.", 'warning')
            return render_template('register.html')
        users[username] = generate_password_hash(password)
        save_data() # Veriyi kaydet
        flash("Kayıt başarılı! Giriş yapabilirsiniz.", 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Kullanıcı veya Admin kontrolü
        user_hash = users.get(username) or admins.get(username)
        
        if user_hash and check_password_hash(user_hash, password):
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = username in admins # Admin durumu kontrolü
            flash(f"Hoş geldin, {username}!", 'success')
            return redirect(url_for('dashboard'))
        
        flash("Geçersiz kullanıcı adı veya şifre.", 'danger')
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    if 'current_room_code' in session: del session['current_room_code'] 
    flash("Başarıyla çıkış yaptınız.", 'success')
    return redirect(url_for('index'))

# ----------------- ODA YÖNETİMİ -----------------

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', rooms=rooms)

@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    room_name = request.form['room_name']
    room_password = request.form.get('room_password') 
    creator = session['username']
    room_code = generate_room_code()
    
    rooms[room_code] = {
        "name": room_name,
        "creator": creator,
        "users": [creator],
        "password_hash": generate_password_hash(room_password) if room_password else None 
    }
    flash(f"Oda '{room_name}' ({room_code}) başarıyla oluşturuldu.", 'success')
    return redirect(url_for('room_page', room_code=room_code))

@app.route('/join_room', methods=['POST'])
@login_required
def join_room_route(): 
    room_code = request.form.get('room_code', '').strip().upper() 
    submitted_password = request.form.get('room_password', '')
    
    if room_code in rooms:
        room = rooms[room_code]
        
        if room.get('password_hash'):
            # Şifre girişi gerekiyorsa, şifreyi al ve kontrol et
            if not submitted_password:
                # Şifre girişi eksikse, özel bir şablonla şifre girişi iste
                return render_template('join_room_password.html', room_code=room_code)
                
            if not check_password_hash(room['password_hash'], submitted_password):
                flash("Yanlış oda şifresi.", 'danger')
                return redirect(url_for('dashboard'))

        if session['username'] not in room['users']:
            room['users'].append(session['username'])
            
        flash(f"Oda '{room['name']}' ({room_code})'a katıldınız.", 'success')
        return redirect(url_for('room_page', room_code=room_code))
    else:
        flash("Yanlış oda kodu.", 'danger')
        return redirect(url_for('dashboard')) 


@app.route('/leave_room/<string:room_code>')
@login_required
def leave_room_route(room_code):
    room_code = room_code.upper()
    username = session['username']
    room_name = ""
    
    if room_code in rooms:
        room = rooms[room_code]
        room_name = room['name']
        
        if username in room['users']:
            room['users'].remove(username)
            
            socketio.emit('new_message', {
                'user': 'Sistem', 
                'text': f'{username} sohbetten ayrıldı.',
                'time': time.strftime("%H:%M")
            }, room=room_code)
            
        if not room['users']:
            if room_code in messages:
                del messages[room_code]
            del rooms[room_code]
            flash(f"Oda '{room_name}' boşaldığı için silindi.", 'warning')
        else:
            flash(f"Oda '{room_name}'dan ayrıldınız.", 'success')
            
    if 'current_room_code' in session: del session['current_room_code']
            
    return redirect(url_for('dashboard')) 


@app.route('/room/<string:room_code>')
@login_required
def room_page(room_code):
    room_code = room_code.upper()

    if room_code in rooms:
        room = rooms[room_code]
        user = session['username']
        
        if user not in room['users']:
            flash("Bu odaya giriş izniniz yok.", 'danger')
            return redirect(url_for('dashboard')) 
            
        if room_code not in messages:
            messages[room_code] = []
            
        session['current_room_code'] = room_code # Oda sekmesi için kaydet
        
        return render_template('room.html', room_code=room_code, room=room, messages=messages[room_code])
    else:
        if 'current_room_code' in session:
            del session['current_room_code']
        flash("Oda bulunamadı.", 'danger')
        return redirect(url_for('dashboard')) 

# ----------------- HABERLER ROTALARI -----------------

@app.route('/news')
def news_index():
    # Haberleri ID'ye göre tersten sırala (en yeniyi üste almak için)
    sorted_news = dict(sorted(news_articles.items(), key=lambda item: item[0], reverse=True))
    return render_template('news_index.html', news=sorted_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    article = news_articles.get(news_id)
    if article:
        return render_template('news_detail.html', article=article)
    flash("Haber bulunamadı.", 'danger')
    abort(404)

# ----------------- ADMIN ROTALARI -----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in admins and check_password_hash(admins[username], password):
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = True 
            flash(f"Admin girişi başarılı. Hoş geldin, {username}!", 'success')
            return redirect(url_for('admin_panel'))
        
        flash("Geçersiz Admin Bilgileri", 'danger')
        return render_template('admin_login.html')
    return render_template('admin_login.html')

@app.route('/admin/panel')
@admin_required
def admin_panel():
    # Hata almamak için tüm değişkenler buraya gönderilmeli
    return render_template('admin_panel.html', 
                             users=users, 
                             admins=admins, 
                             news=news_articles, 
                             rooms=rooms)

# --- ADMIN: KULLANICI YÖNETİMİ ---

@app.route('/admin/add_user', methods=['POST'])
@admin_required
def admin_add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if not username or not password:
        flash("Kullanıcı adı ve şifre boş bırakılamaz.", 'danger')
        return redirect(url_for('admin_panel'))
        
    if username in users or username in admins:
        flash(f"'{username}' zaten mevcut.", 'warning')
        return redirect(url_for('admin_panel')) 

    password_hash = generate_password_hash(password)
    
    if is_admin:
        admins[username] = password_hash
        flash(f"Admin kullanıcısı '{username}' başarıyla eklendi.", 'success')
    else:
        users[username] = password_hash
        flash(f"Kullanıcı '{username}' başarıyla eklendi.", 'success')
    
    save_data() # Değişiklikleri kalıcı hale getir
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<string:username>')
@admin_required
def admin_delete_user(username):
    # Admin kendi hesabını silemez
    if username == session.get('username'):
        flash("Kendi hesabınızı silemezsiniz.", 'danger')
        return redirect(url_for('admin_panel'))
        
    if username in users:
        del users[username]
        flash(f"Kullanıcı '{username}' silindi.", 'success')
    elif username in admins:
        if len(admins) > 1:
            del admins[username]
            flash(f"Admin kullanıcısı '{username}' silindi.", 'success')
        else:
            flash("Sistemde en az bir admin kalmalıdır.", 'danger')
            
    save_data() # Değişiklikleri kalıcı hale getir
    return redirect(url_for('admin_panel'))

# --- ADMIN: HABER YÖNETİMİ ---

@app.route('/admin/add_news', methods=['POST'])
@admin_required
def admin_add_news():
    global news_counter
    
    file = request.files.get('image')
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Klasör yoksa oluştur
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) 
        
    news_articles[news_counter] = {
        'id': news_counter,
        'title': request.form['title'],
        'summary': request.form['summary'],
        'content': request.form['content'],
        'image': filename 
    }
    flash(f"Haber '{request.form['title']}' başarıyla eklendi.", 'success')
    news_counter += 1
    save_data() # Değişiklikleri kalıcı hale getir
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_news/<int:news_id>')
@admin_required
def admin_delete_news(news_id):
    if news_id in news_articles:
        image_name = news_articles[news_id].get('image')
        article_title = news_articles[news_id].get('title', 'Bilinmeyen Haber')
        if image_name:
            try:
                # Resim dosyasını da sil
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_name))
            except Exception as e:
                print(f"Resim silinirken hata oluştu: {e}")
                
        del news_articles[news_id]
        flash(f"Haber '{article_title}' silindi.", 'success')
        save_data() # Değişiklikleri kalıcı hale getir
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit_news/<int:news_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_news(news_id):
    article = news_articles.get(news_id)
    if not article:
        flash("Düzenlenecek haber bulunamadı.", 'danger')
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        file = request.files.get('image')
        filename = article.get('image') 
        
        if file and allowed_file(file.filename):
            # Eski resmi sil ve yenisini kaydet
            if filename:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except:
                    pass
                    
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) 
            
        article['title'] = request.form['title']
        article['summary'] = request.form['summary']
        article['content'] = request.form['content']
        article['image'] = filename 
        
        save_data() # Değişiklikleri kalıcı hale getir
        flash(f"Haber '{article['title']}' başarıyla güncellendi.", 'success')
        return redirect(url_for('admin_panel'))

    return render_template('admin_edit_news.html', article=article)


# ----------------- SOCKETIO OLAY YÖNETİCİLERİ -----------------

@socketio.on('join')
def on_join(data):
    username = session.get('username')
    room = data.get('room')

    if not username or not room:
        return 

    join_room(room)
    
    system_message = {
        'user': 'Sistem', 
        'text': f'{username} sohbete katıldı.',
        'time': time.strftime("%H:%M")
    }
    emit('new_message', system_message, to=room)


@socketio.on('send_message')
def handle_message(data):
    username = session.get('username')
    room = data.get('room')
    message_text = data.get('message')

    if not username or not room or not message_text:
        return

    current_time = time.strftime("%H:%M")
    
    message_data = {
        'user': username,
        'text': message_text,
        'time': current_time
    }
    
    if room in messages:
        messages[room].append(message_data)
        
    emit('new_message', message_data, to=room)


# ----------------- UYGULAMAYI BAŞLATMA -----------------

if __name__ == '__main__':
    # Uygulama başlatıldığında verileri yükle
    load_data()
    
    print("SocketIO Sunucusu Başlatılıyor...")
    # Dosya yükleme klasörünün varlığını kontrol etme
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    # host='0.0.0.0' ayarı dış ağ erişimi için kritik
    socketio.run(app, debug=True, host='0.0.0.0')
