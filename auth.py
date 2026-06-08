from flask import render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import check_password_hash, generate_password_hash 
from db import get_db_connection
from mysql.connector import Error
from functools import wraps
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(to_email, otp_code):
    # .env dosyasından e-posta bilgilerini çekiyoruz
    sender_email = os.getenv('MAIL_USERNAME')
    sender_password = os.getenv('MAIL_PASSWORD')

    if not sender_email or not sender_password:
        print("HATA: .env dosyasında MAIL_USERNAME veya MAIL_PASSWORD eksik!")
        return False

    subject = "Lezzet Kapında - E-posta Doğrulama Kodu"
    body = f"""
    Merhaba,
    
    Lezzet Kapında'ya kayıt olduğunuz için teşekkür ederiz!
    Hesabınızı doğrulamak için tek kullanımlık güvenlik kodunuz:
    
    GÜVENLİK KODU: {otp_code}
    
    Bu kod 3 dakika boyunca geçerlidir. Lütfen bu kodu kimseyle paylaşmayın.
    
    İyi günler dileriz,
    Lezzet Kapında Ekibi
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        # Gmail SMTP sunucusuna bağlanıyoruz
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Mail gönderme hatası: {e}")
        return False

def nocache(view):
    @wraps(view)
    def no_cache_wrapped(*args, **kwargs):
        # Fonksiyonu çalıştır ve sonucunu al
        response = make_response(view(*args, **kwargs))
        # Kalkan ayarlarını ekle
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_wrapped

@nocache
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        if connection is None:
            flash("Couldn't connect to the database!", "danger")
            return render_template('login.html')

        try:
            cursor = connection.cursor(dictionary=True)
            
            # 🕵️‍♂️ 1. KONTROL: Bu kişi bir ADMIN mi?
            cursor.execute('SELECT * FROM admins WHERE email = %s', (email,))
            admin = cursor.fetchone()
            if admin and check_password_hash(admin['password'], password):
                session['logged_in'] = True
                session['role'] = 'admin'
                flash("Admin login successful!", "success")
                return redirect(url_for('index'))

            # 🕵️‍♂️ 2. KONTROL: Bu kişi bir RESTORAN SAHİBİ mi?
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                cursor.execute('SELECT * FROM restaurants WHERE user_id = %s', (session['user_id'],))
                restaurant = cursor.fetchone()

                if restaurant:
                    session['logged_in'] = True
                    session['role'] = 'user'
                    session['restaurant_id'] = restaurant['restaurant_id']
                    flash("Restaurant Owner login successful!", "success")
                    return redirect(url_for('index'))
                else:
                    flash("Hesabınıza bağlı bir restoran bulunamadı.", "danger")
                    return redirect(url_for('login'))
                    
            # 🕵️‍♂️ 3. KONTROL: Bu kişi bir GARSON mu?
            cursor.execute('SELECT * FROM waiters WHERE email = %s', (email,))
            waiter = cursor.fetchone()
            if waiter and check_password_hash(waiter['password'], password):
                session['logged_in'] = True
                session['role'] = 'waiter'
                session['waiter_id'] = waiter['waiter_id']
                session['restaurant_id'] = waiter['restaurant_id']
                flash("Waiter login successful!", "success")
                return redirect(url_for('waiter_dashboard'))

            # 🕵️‍♂️ 4. KONTROL: Bu kişi bir KURYE mi?
            cursor.execute('SELECT * FROM couriers WHERE email = %s', (email,))
            courier = cursor.fetchone()
            if courier and check_password_hash(courier['password'], password):
                session['logged_in'] = True
                session['role'] = 'courier'
                session['courier_id'] = courier['courier_id']
                flash("Courier login successful!", "success")
                return redirect(url_for('courier_dashboard', courier_id=courier['courier_id']))

            flash("Invalid email or password.", "danger")
            return redirect(url_for('login')) 

        except Error as e:
            flash(f"Query failed: {e}", "danger")
            return redirect(url_for('login')) 
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('login.html')
    
def logout():
    # 1. Oturumu temizlemeden önce kullanıcının rolünü hafızaya alıyoruz
    role = session.get('role')
    
    # 2. Artık güvenle TÜM oturum verilerini silebiliriz
    session.clear()
    
    flash('You have been logged out!', 'success')
    
    # 3. Yönlendirme Mantığı (Kuryeyi de genel portala gönderiyoruz)
    if role == 'customer':
        return redirect(url_for('customer_login')) 
    else:
        # Garson, Kurye, Restoran Sahibi, Admin -> Hepsi Personel Portalına (login) döner!
        return redirect(url_for('login'))

@nocache
def register():
    if request.method == 'POST':
        # Yeni HTML formundan gelen başvuru bilgilerini yakalıyoruz
        restaurant_name = request.form['restaurant_name']
        contact_name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']

        connection = get_db_connection()
        if connection is None:
            flash("Veritabanına bağlanılamadı!", "danger")
            return redirect(url_for('register'))

        try:
            cursor = connection.cursor()
            
            # ADIM 1: Gelen verileri geçici "Başvuru Havuzuna" (restaurant_applications) kaydediyoruz
            # Durumu otomatik olarak 'pending' (beklemede) oluyor.
            cursor.execute(
                '''INSERT INTO restaurant_applications 
                   (restaurant_name, contact_name, email, phone, status) 
                   VALUES (%s, %s, %s, %s, 'pending')''',
                (restaurant_name, contact_name, email, phone)
            )
            
            connection.commit()
            
            # Başarılı başvuru sonrası anında sisteme almıyoruz, login'e yönlendirip bilgi veriyoruz
            flash("Başvurunuz başarıyla alındı! Ekibimiz en kısa sürede sizinle iletişime geçecektir. 🤝", "success")
            return redirect(url_for('login'))
            
        except Error as e:
            connection.rollback() 
            flash(f"Başvuru sırasında bir hata oluştu: {e}", "danger")
            return redirect(url_for('register'))
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # Eğer GET isteğiyle (linke tıklayarak) geldiyse sadece başvuru formunu göster
    return render_template('register.html')

@nocache
def customer_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        if connection is None:
            flash("Veritabanı bağlantısı kurulamadı!", "danger")
            return render_template('customer_register.html')

        try:
            cursor = connection.cursor(dictionary=True)
            
            # 🕵️‍♂️ 1. KONTROL: Bu e-posta zaten kayıtlı mı?
            cursor.execute('SELECT * FROM customers WHERE email = %s', (email,))
            if cursor.fetchone():
                flash("Bu e-posta adresi zaten kullanımda! Lütfen giriş yapın.", "danger")
                return redirect(url_for('customer_login'))
            
            # 🚀 2. KAYITLI DEĞİLSE: OTP (Kod) Üret
            otp_code = str(random.randint(100000, 999999))
            
            # 📨 3. MAİL GÖNDER
            if send_otp_email(email, otp_code):
                # Başarılıysa: Veritabanına YAZMA, geçici olarak Session'a at!
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                session['pending_name'] = name
                session['pending_email'] = email
                session['pending_password'] = hashed_password
                session['otp_code'] = otp_code
                
                return redirect(url_for('verify_email_page'))
            else:
                flash("Doğrulama kodu gönderilemedi. Lütfen geçerli bir e-posta girin.", "danger")
                return redirect(url_for('customer_register'))

        except Error as e:
            flash(f"Kayıt hatası: {e}", "danger")
            return redirect(url_for('customer_register')) 
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('customer_register.html')

@nocache
def verify_email_page():
    # Eğer bekleyen bir doğrulama işlemi yoksa kayıt sayfasına geri at
    if 'pending_email' not in session:
        return redirect(url_for('customer_register'))
    return render_template('verify_email.html')

@nocache
def verify_email_code():
    if request.method == 'POST':
        # AJAX (JSON) isteği mi kontrol et
        data = request.get_json(silent=True) or {}
        entered_code = data.get('verification_code') or request.form.get('verification_code')
        real_code = session.get('otp_code')
        
        # 🎯 KOD DOĞRUYSA
        if entered_code and real_code and entered_code == real_code:
            connection = get_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    cursor.execute(
                        'INSERT INTO customers (name, email, password) VALUES (%s, %s, %s)', 
                        (session['pending_name'], session['pending_email'], session['pending_password'])
                    )
                    connection.commit()
                    
                    session.pop('pending_name', None)
                    session.pop('pending_email', None)
                    session.pop('pending_password', None)
                    session.pop('otp_code', None)
                    
                    flash("Hesabınız başarıyla doğrulandı! 🎉 Lütfen giriş yapın.", "success")
                    
                    # AJAX'a Başarılı Yanıtı Dön
                    return {'success': True, 'redirect': url_for('customer_login')}
                    
                except Error as e:
                    connection.rollback()
                    return {'success': False, 'message': 'Kayıt sırasında veritabanı hatası oluştu.'}
                finally:
                    if connection.is_connected():
                        cursor.close()
                        connection.close()
        else:
            # ❌ KOD YANLIŞSA (Sayfa yenilemeden hata döndür)
            return {'success': False, 'message': 'Hatalı veya süresi geçmiş kod girdiniz!'}
            
    return redirect(url_for('verify_email_page'))

@nocache
def resend_verification_code():
    email = session.get('pending_email')
    if email:
        otp_code = str(random.randint(100000, 999999))
        if send_otp_email(email, otp_code):
            session['otp_code'] = otp_code
            # Flash yerine direkt JSON mesajı dönüyoruz
            return {'success': True, 'message': 'Yeni doğrulama kodu gönderildi! 📨'}
        else:
            return {'success': False, 'message': 'Kod gönderilemedi, lütfen tekrar deneyin.'}
            
    return {'success': False, 'message': 'Bekleyen bir doğrulama işlemi bulunamadı.'}

@nocache
def customer_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute('SELECT * FROM customers WHERE email = %s', (email,))
                customer = cursor.fetchone()
                
                if customer and check_password_hash(customer['password'], password):
                    session['logged_in'] = True
                    session['role'] = 'customer' 
                    session['customer_id'] = customer['customer_id']
                    
                    flash("Login successful! Welcome to the marketplace.", "success")
                    return redirect(url_for('index')) 
                else:
                    flash("Invalid email or password.", "danger")
                    return redirect(url_for('customer_login')) 
            except Error as e:
                flash(f"Login failed: {e}", "danger")
                return redirect(url_for('customer_login')) 
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

    return render_template('customer_login.html')