import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore, auth

# ... (Uygulama ayarları ve Firebase başlatma kodu aynı kalıyor) ...

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
# ENDPOINT ADI: 'index'
@app.route('/')
def index():
    return render_template('index.html', current_user=session.get('user_id'))

# Kayıt Sayfası
# ENDPOINT ADI: 'register'
@app.route('/register', methods=['GET', 'POST'])
def register():
    if not firebase_auth:
        flash("Sistem hatası: Firebase bağlantısı kurulamadı.", "danger")
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = firebase_auth.create_user(email=email, password=password)
            flash("Kayıt başarılı. Lütfen giriş yapın.", "success")
            return redirect(url_for('login')) # Düzeltildi: 'login' endpoint'ini kullanır
        except Exception as e:
            flash(f"Kayıt hatası: {e}", "danger")
            return render_template('register.html')
    
    return render_template('register.html')

# Giriş Sayfası
# ENDPOINT ADI: 'login'
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == "test@example.com" and password == "123456":
            session['user_id'] = 'mock_user_id' 
            flash("Giriş başarılı.", "success")
            return redirect(url_for('dashboard')) # Düzeltildi: 'dashboard' endpoint'ini kullanır
        else:
            flash("Geçersiz e-posta veya şifre.", "danger")
            return render_template('login.html')

    return render_template('login.html')

# Çıkış
# ENDPOINT ADI: 'logout'
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for('index')) # Düzeltildi: 'index' endpoint'ini kullanır

# Dashboard/Profil Sayfası (Giriş gerektirir)
# ENDPOINT ADI: 'dashboard'
@app.route('/dashboard')
@login_required
def dashboard():
    # Firestore'dan kullanıcıya özel veri çekilebilir (eğer db başlatıldıysa)
    data = None
    if db:
        # Örnek: 'users' koleksiyonundan kullanıcının dökümanını çekme
        try:
            # ... Firestore çekme mantığı ...
            pass
        except Exception:
            pass # Hata yönetimi
            
    return render_template('dashboard.html', user_id=session['user_id'], user_data=data)

# ... (Uygulama çalıştırma kodu aynı kalıyor) ...
