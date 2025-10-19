import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ==============================================================================
# IN-MEMORY VERİ DEPOLAMA (Uygulama yeniden başlatıldığında veriler kaybolur)
# ==============================================================================

# Kullanıcı verilerini saklar (Kullanıcı adı benzersiz kimliktir)
USERS = {
    'admin': {
        'password_hash': generate_password_hash('123456'), # Varsayılan Admin Şifresi
        'is_admin': True
    }
}

# Oda verilerini ve mesaj geçmişini saklar
ROOMS = {
    'TEST01': {
        'name': 'Genel Sohbet Odası', 
        'history': [
            {'username': 'Sistem', 'message': 'Bu oda veritabanı yerine bellekte saklanmaktadır.'},
            {'username': 'Sistem', 'message': 'Uygulama yeniden başlatılırsa mesaj geçmişi kaybolur.'}
        ],
        'creator_id': 'admin'
    }
}

# ==============================================================================
# FLASK ve SOCKETIO KURULUMU
# ==============================================================================

app = Flask(__name__)
# Gizli anahtar olarak rastgele bir dize kullan
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16)) 
socketio = SocketIO(app) 


# ==============================================================================
# OTURUM KONTROL YARDIMCISI
# ==============================================================================

def login_required(f):
    """Giriş yapılmasını gerektiren dekoratör."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Bu sayfayı görmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Admin yetkisi gerektiren dekoratör."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# FLASK YOLLARI (ROUTES)
# ==============================================================================

@app.route('/')
def index():
    """Ana sayfa."""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Kullanıcı kayıt sayfası ve işlevi."""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('Kullanıcı adı ve şifre boş bırakılamaz.', 'danger')
            return render_template('register.html')

        # Kullanıcı adının sistemde olup olmadığını kontrol et
        if username in USERS:
            flash('Bu kullanıcı adı zaten alınmış.', 'danger')
            return render_template('register.html')
        
        # Yeni kullanıcıyı in-memory USERS sözlüğüne kaydet
        USERS[username] = {
            'password_hash': generate_password_hash(password),
            'is_admin': False
        }

        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı giriş sayfası ve işlevi."""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        # Kullanıcıyı USERS sözlüğünde ara ve şifreyi kontrol et
        if username in USERS and check_password_hash(USERS[username]['password_hash'], password):
            
            user_data = USERS[username]
            
            # Oturum bilgilerini ayarla
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = user_data.get('is_admin', False)
            
            flash('Başarıyla giriş yaptınız.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Kullanıcı adı veya şifre yanlış.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Çıkış yapma işlevi."""
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    session.pop('current_room_code', None)
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Sohbet odası listesini gösterir."""
    # ROOMS sözlüğünden odaları al
    room_list = [{'code': code, 'name': room['name']} for code, room in ROOMS.items()]
    
    return render_template('dashboard.html', 
                           rooms=room_list, 
                           current_user=session.get('username'),
                           rooms_data=ROOMS) # rooms_data'yı base.html için gönderiyoruz


@app.route('/create_room', methods=['POST'])
@login_required
def create_room():
    """Yeni sohbet odası oluşturur."""
    room_name = request.form['room_name'].strip()
    
    if not room_name:
        flash('Oda adı boş bırakılamaz.', 'danger')
        return redirect(url_for('dashboard'))

    # Benzersiz bir oda kodu oluştur
    room_code = secrets.token_hex(4).upper()
    while room_code in ROOMS:
        room_code = secrets.token_hex(4).upper()

    # Yeni odayı ROOMS sözlüğüne kaydet
    ROOMS[room_code] = {
        'name': room_name,
        'history': [{'username': 'Sistem', 'message': f'Oda "{room_name}" oluşturuldu.'}],
        'creator_id': session['username']
    }
    
    # Yeni odayı aktif oda olarak ayarla
    session['current_room_code'] = room_code
    flash(f'Oda "{room_name}" başarıyla oluşturuldu.', 'success')
    return redirect(url_for('room_page', room_code=room_code))


@app.route('/room/<room_code>')
@login_required
def room_page(room_code):
    """Belirli bir sohbet odasının sayfasını gösterir."""
    if room_code not in ROOMS:
        flash('Böyle bir sohbet odası bulunamadı.', 'danger')
        return redirect(url_for('dashboard'))

    room = ROOMS[room_code]
    
    # Odanın aktif oda olarak ayarlanması
    session['current_room_code'] = room_code
    
    # room.html'e geçmişi gönder
    return render_template('room.html', 
                           room_code=room_code, 
                           room_name=room['name'], 
                           chat_history=room['history'],
                           rooms_data=ROOMS) # rooms_data'yı base.html için gönderiyoruz


@app.route('/join_room', methods=['POST'])
@login_required
def join_room_route():
    """Kullanıcının mevcut bir odaya katılması."""
    room_code = request.form['room_code'].strip().upper()
    
    if room_code not in ROOMS:
        flash('Girilen kod ile oda bulunamadı.', 'danger')
        return redirect(url_for('dashboard'))

    # Odaya yönlendir
    return redirect(url_for('room_page', room_code=room_code))


@app.route('/admin_panel')
@admin_required
def admin_panel():
    """Admin paneli: Kullanıcı ve oda yönetimi."""
    # In-memory verileri paneli render etmek için kullan
    user_list = [{'username': k, 'is_admin': v['is_admin']} for k, v in USERS.items()]
    room_list = [{'code': code, 'name': room['name'], 'creator': room['creator_id']} for code, room in ROOMS.items()]
    
    return render_template('admin_panel.html', users=user_list, rooms=room_list, rooms_data=ROOMS)


@app.route('/admin/delete_room/<room_code>', methods=['POST'])
@admin_required
def delete_room(room_code):
    """Admin: Oda silme."""
    if room_code in ROOMS:
        del ROOMS[room_code]
        flash(f'Oda ({room_code}) başarıyla silindi.', 'success')
    else:
        flash('Silinecek oda bulunamadı.', 'danger')
        
    return redirect(url_for('admin_panel'))


# ==============================================================================
# SOCKETIO OLAYLARI (CHAT)
# ==============================================================================

@socketio.on('join')
@login_required
def on_join(data):
    """Kullanıcı bir odaya katıldığında tetiklenir."""
    room_code = data.get('room_code')
    username = session.get('username')

    if not room_code or room_code not in ROOMS:
        return 
        
    # Flask-SocketIO'nun kendi join_room işlevini kullan
    join_room(room_code)
    
    # Odaya katıldığını yayınla
    join_message = f'{username} odaya katıldı.'
    emit('status', {'msg': join_message}, room=room_code)
    
    # Mesajı geçmişe kaydet (Sadece durum mesajları belleğe kaydedilmez)
    # Bu kısmı basitleştiriyoruz, kullanıcı mesajlarını kaydetmek yeterli.

    print(f"{username} joined room {room_code}")


@socketio.on('leave')
@login_required
def on_leave(data):
    """Kullanıcı odadan ayrıldığında tetiklenir."""
    room_code = data.get('room_code')
    username = session.get('username')
    
    if not room_code or room_code not in ROOMS:
        return 
        
    leave_room(room_code)
    
    leave_message = f'{username} odadan ayrıldı.'
    emit('status', {'msg': leave_message}, room=room_code)

    print(f"{username} left room {room_code}")


@socketio.on('message')
@login_required
def handle_message(data):
    """Kullanıcıdan gelen mesajı işler ve yayınlar."""
    room_code = data.get('room_code')
    message = data.get('message')
    username = session.get('username')
    
    if not room_code or room_code not in ROOMS or not message:
        return

    timestamp = datetime.now().strftime('%H:%M')
    
    # Yayınlanacak veri
    message_data = {
        'username': username,
        'message': message,
        'timestamp': timestamp,
        'is_admin': session.get('is_admin', False)
    }

    # Mesajı odaya yayınla
    emit('new_message', message_data, room=room_code)

    # Mesajı in-memory geçmişe kaydet (Son 100 mesajı tutalım)
    room_history = ROOMS[room_code]['history']
    room_history.append(message_data)
    
    # Geçmişi sınırlayalım (Örn: En fazla 100 mesaj)
    ROOMS[room_code]['history'] = room_history[-100:]

    print(f"[{room_code}] {username}: {message}")


# ==============================================================================
# UYGULAMA BAŞLATMA
# ==============================================================================

if __name__ == '__main__':
    # Flask'ı geliştirme modunda çalıştırıyoruz. 
    # SocketIO ile birlikte kullanırken socketio.run() kullanın.
    socketio.run(app, debug=True)
