from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error

def view_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    connection = get_db_connection()
    user_data = None

    if connection is None:
        flash("Veritabanı bağlantısı başarısız!", "danger")
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. MÜŞTERİ PROFİLİ
        if role == 'customer':
            customer_id = session.get('customer_id')
            cursor.execute("SELECT name, phone, city, address FROM customers WHERE customer_id = %s", (customer_id,))
            user_data = cursor.fetchone()

        # 2. GARSON PROFİLİ
        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id') 
            cursor.execute("SELECT name, email, password FROM waiters WHERE waiter_id = %s", (waiter_id,))
            user_data = cursor.fetchone()

        # 3. RESTORAN SAHİBİ VEYA ADMIN PROFİLİ
        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            cursor.execute("SELECT name, email, password FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            if role == 'user' and user_data:
                restaurant_id = session.get('restaurant_id')
                if restaurant_id:
                    cursor.execute("SELECT latitude, longitude FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                    res_coords = cursor.fetchone()
                    if res_coords:
                        user_data['latitude'] = res_coords['latitude']
                        user_data['longitude'] = res_coords['longitude']

    except Error as e:
        flash(f"Profil bilgileri yüklenirken hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    if not user_data:
        flash("Kullanıcı bilgileri bulunamadı.", "warning")
        return redirect(url_for('index'))

    return render_template('profile.html', user_data=user_data)


def update_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    connection = get_db_connection()
    
    if connection is None:
        return redirect(url_for('view_profile'))

    try:
        cursor = connection.cursor(dictionary=True)

        # 1. MÜŞTERİ GÜNCELLEME
        if role == 'customer':
            customer_id = session.get('customer_id')
            name = request.form.get('name')
            phone = request.form.get('phone')
            city = request.form.get('city')
            address = request.form.get('address')

            cursor.execute("""
                UPDATE customers SET name = %s, phone = %s, city = %s, address = %s WHERE customer_id = %s
            """, (name, phone, city, address, customer_id))
            connection.commit()
            session['customer_city'] = city
            flash("Profil bilgileriniz başarıyla güncellendi! ✨", "success")

        # 2. GARSON GÜNCELLEME (Akıllı şifre kontrolü eklendi)
        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id')
            name = request.form.get('name')
            password = request.form.get('password')

            if password: # Eğer yeni bir şifre yazıldıysa şifreyi de güncelle
                cursor.execute("""
                    UPDATE waiters SET name = %s, password = %s WHERE waiter_id = %s
                """, (name, password, waiter_id))
            else: # Boş bırakıldıysa eski şifreyi koru, sadece adı güncelle
                cursor.execute("""
                    UPDATE waiters SET name = %s WHERE waiter_id = %s
                """, (name, waiter_id))
                
            connection.commit()
            flash("Garson profil bilgileriniz güncellendi! 🔐", "success")

        # 3. RESTORAN SAHİBİ / ADMIN GÜNCELLEME (Akıllı şifre kontrolü eklendi)
        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if password: # Yeni şifre girildiyse
                cursor.execute("""
                    UPDATE users SET name = %s, email = %s, password = %s WHERE user_id = %s
                """, (name, email, password, user_id))
            else: # Şifre boş bırakıldıysa eski şifreyi ezme
                cursor.execute("""
                    UPDATE users SET name = %s, email = %s WHERE user_id = %s
                """, (name, email, user_id))
            
            if role == 'user':
                restaurant_id = session.get('restaurant_id')
                latitude = request.form.get('latitude')
                longitude = request.form.get('longitude')
                
                if restaurant_id and latitude and longitude:
                    cursor.execute("""
                        UPDATE restaurants SET latitude = %s, longitude = %s WHERE restaurant_id = %s
                    """, (latitude, longitude, restaurant_id))

            connection.commit()
            flash("Yönetici hesap ayarlarınız başarıyla güncellendi! 🚀", "success")

    except Error as e:
        connection.rollback()
        flash(f"Güncelleme sırasında bir hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('view_profile'))