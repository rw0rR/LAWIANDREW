import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Uygulama ayarları
app = Flask(__name__)
# Güvenli oturumlar için gizli anahtar (Render ortam değişkeni olarak ayarlanmalıdır)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')


# =================================================================
# FIREBASE BAĞLANTISI VE BAŞLATMA
# =================================================================

def initialize_firebase():
    """
    FIREBASE_CONFIG ortam değişkenini kullanarak Firebase Admin SDK'yı başlatır.
    Bu değişken, Render'da tek satır JSON olarak ayarlanmalıdır.
    """
    try:
        # 1. Ortam değişkeninden JSON dizesini alın
        firebase_config_json = os.environ.get("FIREBASE_CONFIG")
        
        if not firebase_config_json:
            print("HATA: FIREBASE_CONFIG ortam değişkeni bulunamadı. Lütfen Render'da ayarlayın.")
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
        global db
        global firebase_auth
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
    # Burada ana sayfanın HTML dosyasını döndürün
    # Örn: return render_template('index.html', current_user=session.get('user_id'))
    return render_template('index.html')

# Kayıt Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Kayıt formunu işleyin
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = firebase_auth.create_user(email=email, password=password)
            flash("Kayıt başarılı. Lütfen giriş yapın.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Kayıt hatası: {e}", "danger")
            return render_template('register.html', error=e)
    
    return render_template('register.html')

# Giriş Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Kullanıcı adıyla (veya e-posta ile) giriş yapma mantığı
        # Admin SDK, sadece token doğrulaması için kullanılır. 
        # Bu kısım genellikle Client SDK ile halledilir, ancak 
        # burası server tarafı olduğu için farklı bir giriş akışı gerekir.
        # Bu demo için basitleştirilmiş bir yer tutucu bırakıyoruz.
        flash("Giriş işlemi tamamlandı (Gerçek Firebase Auth kodu burada olmalı).", "success")
        session['user_id'] = 'mock_user_id' # Başarılı bir girişten sonra user_id'yi ayarlayın
        return redirect(url_for('dashboard'))

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
    # Profil bilgilerini vb. gösterin
    return render_template('dashboard.html', user_id=session['user_id'])


# =================================================================
# UYGULAMAYI ÇALIŞTIRMA
# =================================================================

if __name__ == '__main__':
    # Local ortamda çalışırken varsayılan portu kullanır
    app.run(debug=True)

# Render üzerinde çalışırken
# Render, gunicorn/uwsgi gibi bir WSGI sunucusu ile uygulamayı çalıştıracaktır.
# Bu sunucu, 'app' adlı Flask uygulamasını otomatik olarak bulur.
