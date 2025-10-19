import os
import json
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import timedelta

# Firebase Admin SDK, Firestore ve Auth'u içe aktar
# Firebase istemci SDK'sı ise genellikle HTML/JS tarafında kullanılır.
# Ancak bu sunucu tarafı bir uygulama olduğu için Admin SDK kullanıyoruz.
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth, exceptions
except ImportError:
    print("WARNING: firebase_admin kütüphanesi yüklü değil. Firebase işlevleri devre dışı.")
    # Firebase kütüphanesi yüklü değilse sahte bir DB objesi oluşturuyoruz.
    class MockDB:
        def collection(self, name): return self
        def document(self, doc_id): return self
        def get(self): return self
        def to_dict(self): return {"name": "Mock User"}
        def stream(self): return []
        def add(self, data): return None
        def where(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, count): return self
    
    DB = MockDB()

# Uygulama ve Secret Key ayarları
app = Flask(__name__)
# Güvenlik için ortam değişkenlerinden çekilmesi önerilir.
app.secret_key = os.environ.get('SECRET_KEY', 'cokgizlibirsifre_buraya_gelecek')
app.permanent_session_lifetime = timedelta(minutes=60)

# Firebase Yapılandırması ve Başlatma
# Canvas ortamından gelen global değişkenleri kullanıyoruz.
def initialize_firebase():
    global DB

    firebase_config_str = os.environ.get('__firebase_config', 
        getattr(globals(), '__firebase_config', '{}'))
    app_id = os.environ.get('__app_id', 
        getattr(globals(), '__app_id', 'default-app-id'))

    try:
        firebase_config = json.loads(firebase_config_str)
        
        # Admin SDK, kimlik bilgilerini servis hesabı olarak kullanır.
        # Canvas ortamında Admin SDK kullanımı için özel bir kimlik doğrulama yöntemi
        # gerekebilir veya yapılandırmayı (config) doğrudan kullanabiliriz.
        
        if not firebase_admin._apps:
            # Firebase Admin SDK'yı yapılandırma ile başlat
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'projectId': firebase_config.get('projectId'),
            })

        DB = firestore.client()
        print(f"Firebase Admin SDK başarıyla başlatıldı. Project ID: {firebase_config.get('projectId')}")
        return True
        
    except Exception as e:
        print(f"HATA: Firebase başlatılamadı. Hata: {e}")
        # Hata durumunda sahte DB kullanmaya devam et
        DB = MockDB()
        return False

# Firebase'i başlat
firebase_initialized = initialize_firebase()

# ------------------------------------
# ORTAK FONKSİYONLAR VE DEKORATÖRLER
# ------------------------------------

def login_required(f):
    """Kullanıcının giriş yapıp yapmadığını kontrol eden dekoratör."""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Devam etmek için giriş yapmalısınız.", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    """Kullanıcının yönetici yetkisine sahip olup olmadığını kontrol eden dekoratör."""
    def wrapper(*args, **kwargs):
        if session.get('is_admin') != True:
            flash("Bu bölüme erişim yetkiniz yok.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ------------------------------------
# ROTALAR
# ------------------------------------

@app.route('/')
def index():
    """Uygulamanın ana sayfasını render eder."""
    return render_template('dashboard.html', user_id=session.get('user_id'), is_admin=session.get('is_admin', False))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı girişini yönetir (Anonim/Özel Token ile)."""
    if request.method == 'POST':
        # Gerçek uygulamada normal e-posta/şifre girişi yapılır.
        # Burada sadece anonim oturumu taklit ediyoruz.
        try:
            # Örnek: Basit bir kullanıcı adı/şifre kontrolü
            username = request.form['username']
            if username == 'admin' and request.form['password'] == '12345':
                session.permanent = True
                session['user_id'] = 'admin_user_id'
                session['is_admin'] = True
                flash("Yönetici olarak başarıyla giriş yaptınız.", "success")
                return redirect(url_for('admin_panel'))
            
            # Diğer kullanıcılar için anonim oturum taklidi
            session.permanent = True
            session['user_id'] = f'guest_{int(time.time())}'
            session['is_admin'] = False
            flash(f"Misafir olarak başarıyla giriş yaptınız.", "success")
            return redirect(url_for('index'))

        except exceptions.FirebaseError as e:
            flash(f"Giriş hatası: {e}", "error")
            return redirect(url_for('login'))
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Kullanıcının oturumunu sonlandırır."""
    session.pop('user_id', None)
    session.pop('is_admin', None)
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for('index'))

# ------------------------------------
# ** HATA ÇÖZÜMÜ İÇİN EKLENEN ROTA **
# ------------------------------------

@app.route('/news')
def news_index():
    """HTML'in talep ettiği 'news_index' endpoint'ini sağlar."""
    # Firebase'den haberleri çekme mantığı buraya gelir.
    try:
        news_ref = DB.collection('artifacts').document(app.config.get('APP_ID', 'default-app-id')).collection('public').document('data').collection('news')
        # Haberleri tarihe göre sıralayıp çekebilirsiniz
        # news_items = [doc.to_dict() for doc in news_ref.order_by('date', direction='DESCENDING').limit(20).stream()]
        news_items = [{"id": "1", "title": "Uygulama Güncellemesi", "content": "Admin paneli eklendi.", "date": "19/10/2025"}]
    except Exception as e:
        print(f"Haberleri çekerken hata oluştu: {e}")
        news_items = [{"id": "placeholder", "title": "Hata: Veritabanı Sorunu", "content": "Haberler yüklenemedi.", "date": "Bilinmiyor"}]

    # news_index.html şablonunu kullanır
    return render_template('news_index.html', news_items=news_items)

# ------------------------------------
# ADMIN ROTALARI
# ------------------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Yönetici giriş sayfası (login ile aynı mantıkta çalışabilir)."""
    return redirect(url_for('login')) # Yönetici girişi için genel login sayfasını kullanıyoruz

@app.route('/admin/panel')
@admin_required
def admin_panel():
    """Yönetici panelinin ana sayfası."""
    # Burada kullanıcı/sohbet istatistikleri veya diğer admin linkleri listelenir
    return render_template('admin_panel.html')

@app.route('/admin/news/edit', defaults={'news_id': 'add'}, methods=['GET', 'POST'])
@app.route('/admin/news/edit/<string:news_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_news(news_id):
    """Admin panelinde haber ekleme veya düzenleme formunu yönetir."""

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        news_data = {
            'title': title,
            'content': content,
            'date': firestore.SERVER_TIMESTAMP,
            'author_id': session.get('user_id')
        }

        try:
            news_collection = DB.collection('artifacts').document(app.config.get('APP_ID', 'default-app-id')).collection('public').document('data').collection('news')

            if news_id == 'add':
                news_collection.add(news_data)
                flash("Yeni haber başarıyla eklendi.", "success")
            else:
                news_collection.document(news_id).set(news_data, merge=True)
                flash("Haber başarıyla güncellendi.", "success")

            return redirect(url_for('admin_panel'))
        
        except Exception as e:
            flash(f"Haber kaydederken bir hata oluştu: {e}", "error")
            return redirect(url_for('admin_edit_news', news_id=news_id))

    # GET isteği: Formu gösterme
    news_item = {"title": "", "content": "", "id": news_id}
    if news_id != 'add':
        try:
            # Firestore'dan haberi çek
            # doc = DB.collection('news').document(news_id).get()
            # if doc.exists: news_item.update(doc.to_dict())
            news_item.update({"title": f"Mevcut Başlık ({news_id})", "content": "Mevcut içerik..."}) # Placeholder
        except Exception as e:
            print(f"Haber çekerken hata: {e}")
            flash("Haber bilgileri yüklenemedi.", "error")
            
    return render_template('admin_edit_news.html', news_item=news_item, news_id=news_id)


# ------------------------------------
# UYGULAMAYI BAŞLATMA
# ------------------------------------
if __name__ == '__main__':
    # Geliştirme ortamında çalıştırırken
    app.config['APP_ID'] = 'default-app-id'
    app.run(debug=True)
    
# Not: Dağıtım ortamında (Render/Gunicorn) bu blok çalışmayacaktır, 
# Gunicorn doğrudan `app` objesini kullanacaktır.
