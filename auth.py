from flask import render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import check_password_hash, generate_password_hash 
from db import get_db_connection
from mysql.connector import Error
from functools import wraps

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
        name = request.form['name']
        email = request.form['email']
        restaurant_name = request.form['restaurant_name'] 
        password = request.form['password']
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        connection = get_db_connection()
        if connection is None:
            flash("Couldn't connect to the database!", "danger")
            return render_template('register.html')

        try:
            cursor = connection.cursor()
            
            # 1. ADIM: Kullanıcıyı (Restoran Sahibini) users tablosuna kaydet
            cursor.execute(
                'INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', 
                (name, email, hashed_password)
            )
            
            # Veritabanının bu yeni kullanıcıya verdiği otomatik ID'yi yakala
            new_user_id = cursor.lastrowid 
            
            # 2. ADIM: Yakalanan ID ve Varsayılan (Default) Değerlerle Restoranı Kur
            # Puanları 0, metinleri "Not Specified" (Belirtilmedi) olarak atıyoruz.
            # 2. ADIM: Yakalanan ID ve Veritabanı Kurallarına Uygun (Default) Değerlerle Restoranı Kur
            cursor.execute('''
                INSERT INTO restaurants 
                (user_id, restaurant_name, city, rating, rating_count, average_cost, cuisine, restaurant_address, table_count) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                new_user_id, 
                restaurant_name, 
                'Not Specified',     # city
                0.0,                 # rating (Sayısal Decimal)
                'Too Few Ratings',   # rating_count (ENUM listesinden seçildi)
                1,                   # average_cost (Kural: 0'dan büyük olmalı, 1 yaptık)
                'Not Specified',     # cuisine
                'Not Specified',     # restaurant_address
                10                   # table_count (Varsayılan 10 masa)
            ))
            
            # Her iki işlemi de tek seferde onayla
            connection.commit()
            
            flash("Account and Restaurant created successfully! Please login.", "success")
            return redirect(url_for('login'))
            
        except Error as e:
            connection.rollback() 
            flash(f"Registration failed: {e}", "danger")
            return redirect(url_for('register'))
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('register.html')

@nocache
def customer_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        connection = get_db_connection()
        if connection is None:
            flash("Database connection failed!", "danger")
            return render_template('customer_register.html')

        try:
            cursor = connection.cursor()
            # Sadece isim, e-posta ve şifre kaydediyoruz. Diğer alanlar (NULL) olarak kalacak.
            cursor.execute(
                'INSERT INTO customers (name, email, password) VALUES (%s, %s, %s)', 
                (name, email, hashed_password)
            )
            connection.commit()
            flash("Account created! Please login to order.", "success")
            return redirect(url_for('customer_login'))
            
        except Error as e:
            connection.rollback()
            flash("Registration failed: Email might be already in use.", "danger")
            return redirect(url_for('customer_register')) 
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('customer_register.html')

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