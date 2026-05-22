from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash # ŞİFRELEME İÇİN EKLENDİ
from db import get_db_connection
from mysql.connector import Error

def login():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection()
        if connection is None:
            flash("Couldn't connect to the database!", "danger")
            return render_template('login.html')

        try:
            cursor = connection.cursor(dictionary=True)
            
            if role == 'admin':
                # Sadece emaili arıyoruz
                cursor.execute('SELECT * FROM admins WHERE email = %s', (email,))
                admin = cursor.fetchone()

                # Şifreyi check_password_hash ile doğruluyoruz
                if admin and check_password_hash(admin['password'], password):
                    session['logged_in'] = True
                    session['role'] = 'admin'
                    flash("Admin login successful!", "success")
                    return redirect(url_for('index'))
                else:
                    flash('Invalid email or password', 'danger')

            elif role == 'user':
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
                        flash("Invalid email or password.", "danger")
                else:
                    flash("Invalid email or password.", "danger")
                    
            elif role == 'waiter':
                cursor.execute('SELECT * FROM waiters WHERE email = %s', (email,))
                waiter = cursor.fetchone()

                if waiter and check_password_hash(waiter['password'], password):
                    session['logged_in'] = True
                    session['role'] = 'waiter'
                    session['waiter_id'] = waiter['waiter_id']
                    session['restaurant_id'] = waiter['restaurant_id']
                    flash("Waiter login successful!", "success")
                    return redirect(url_for('waiter_dashboard'))
                else:
                    flash("Invalid email or password.", "danger")

        except Error as e:
            flash(f"Query failed: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('login.html')
    
def logout():
    # 1. Oturumu temizlemeden önce kullanıcının rolünü hafızaya alıyoruz
    role = session.get('role')
    
    # 2. Artık güvenle TÜM oturum verilerini silebiliriz (sepet, id'ler, lokasyon vb. her şey sıfırlanır)
    session.clear()
    
    # 3. Flash mesajını session temizlendikten SONRA eklemeliyiz (çünkü flash da arka planda session kullanır)
    flash('You have been logged out!', 'success')
    
    # 4. Öğrendiğimiz role göre kişiyi kendi giriş kapısına yönlendiriyoruz
    if role == 'customer':
        return redirect(url_for('customer_login')) 
    elif role == 'courier':
        return redirect(url_for('courier_login'))
    else:
        # Garson, Restoran Sahibi (user), Admin veya role atanmamışsa ana login'e gönder
        return redirect(url_for('login'))

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
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('register.html')

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
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('customer_register.html')


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
                    session['role'] = 'customer' # Müşteriyi B2B panelden ayırmak için
                    session['customer_id'] = customer['customer_id']
                    session['customer_city'] = customer['city'] # İleride sadece kendi şehrindeki restoranları görsün diye
                    
                    flash("Login successful! Welcome to the marketplace.", "success")
                    return redirect(url_for('index')) # Vitrin sayfası yapılınca oraya yönlendireceğiz
                else:
                    flash("Invalid email or password.", "danger")
            except Error as e:
                flash(f"Login failed: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

    return render_template('customer_login.html')