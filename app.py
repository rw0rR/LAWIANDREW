import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore, auth

# =================================================================
# UYGULAMA AYARLARI
# =================================================================
app = Flask(__name__)
# Güvenli oturumlar için gizli anahtar (Render ortam değişkeni olarak ayarlanmalıdır)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')

# Global değişkenler (Başlangıçta None olarak ayarlanır)
db = None
firebase_auth = None

# =================================================================
# FIREBASE BAĞLANTISI VE BAŞLATMA
# =================================================================

def initialize_firebase():
    """
    FIREBASE_CONFIG ortam değişkenini kullanarak Firebase Admin SDK'yı başlatır.
    """
    global db
    global firebase_auth
    
    try:
        # 1. Ortam değişkeninden JSON dizesini alın
        firebase_config_json = os.environ.get("FIREBASE_CONFIG")
        
        if not firebase_config_json:
            print("HATA: FIREBASE_CONFIG ortam değişkeni bulunamadı. Lütfen Render'da ayarlayın.")
            # Firebase başlatılamazsa, uygulamayı yer tutucu (placeholder) değerlerle devam ettir
            db = None
            firebase_auth = None
            return False

        # 2. JSON dizesini Python sözlüğüne çevirin
        cred_dict = json.loads(firebase_config_json)
        
        # 3. Kimlik bilgilerini (Credentials) başlatın
        cred = credentials.Certificate(cred_dict)
        
        # 4. Firebase uygulamasını başlatın
        # Birden fazla kez başlatılmasını önlemek için kontrol yapıyoruz
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK başarıyla başlatıldı.")

        # Firestore ve Auth servislerine erişim
        db = firestore.client()
        firebase_auth = auth
        return True

    except json.JSONDecodeError:
        print("HATA: FIREBASE_CONFIG değeri geçerli bir JSON formatında değil.")
        return False
    except Exception as e:
        print(f"HATA: Firebase başlatılırken bir sorun oluştu: {e}")
        return False

# Uygulama başlangıcında Firebase'i başlatın
# Not: WSGI sunucuları (Gunicorn/uWSGI) bu kodu çalıştıracaktır.
initialize_firebase()


# =================================================================
# YÖNLENDİRMELER (ROUTES)
# =================================================================

# Kullanıcı oturumunu kontrol eden dekoratör
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("Bu sayfaya erişmek için giriş yapmalısınız.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Anasayfa
@app.route('/')
def index():
    # current_user bilgisini HTML şablonuna gönderiyoruz
    return render_template('index.html', current_user=session.get('user_id'))

# Kayıt Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if not firebase_auth:
        flash("Sistem hatası: Firebase bağlantısı kurulamadı.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            # Firebase Admin SDK ile kullanıcı oluşturma
            user = firebase_auth.create_user(email=email, password=password)
            flash("Kayıt başarılı. Lütfen giriş yapın.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Kayıt hatası: {e}", "danger")
            # Firebase hatalarını daha kullanıcı dostu göstermek için burası özelleştirilebilir.
            return render_template('register.html')
    
    return render_template('register.html')

# Giriş Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # ÖNEMLİ: Admin SDK, doğrudan e-posta/şifre ile giriş yapmak için uygun değildir.
        # Giriş için genellikle Client SDK (JavaScript) veya özel bir JWT doğrulama akışı kullanılır.
        # Bu demo için sadece başarılı bir girişi simüle ediyoruz.
        email = request.form.get('email')
        password = request.form.get('password')

        if email == "test@example.com" and password == "123456":
            session['user_id'] = 'mock_user_id' 
            flash("Giriş başarılı.", "success")
            return redirect(url_for('dashboard'))
        else:
            # Gerçek bir uygulamada, burada Client SDK ile alınmış bir ID token doğrulanmalıdır.
            flash("Geçersiz e-posta veya şifre.", "danger")
            return render_template('login.html')

    return render_template('login.html')

# Çıkış
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for('index'))

# Dashboard/Profil Sayfası (Giriş gerektirir)
@app.route('/dashboard')
@login_required
def dashboard():
    # Firestore'dan kullanıcıya özel veri çekilebilir (eğer db başlatıldıysa)
    data = None
    if db:
        # Örnek: 'users' koleksiyonundan kullanıcının dökümanını çekme
        try:
            doc_ref = db.collection('users').document(session['user_id'])
            doc = doc_ref.get()
            data = doc.to_dict() if doc.exists else {"message": "Kullanıcı verisi bulunamadı."}
        except Exception as e:
            data = {"error": f"Veritabanı hatası: {e}"}
            
    return render_template('dashboard.html', user_id=session['user_id'], user_data=data)


# =================================================================
# UYGULAMAYI ÇALIŞTIRMA
# =================================================================

if __name__ == '__main__':
    # Local ortamda çalışırken varsayılan portu kullanır
    app.run(debug=True)
