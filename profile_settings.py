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
            cursor.execute("SELECT name, phone, address FROM customers WHERE customer_id = %s", (customer_id,))
            user_data = cursor.fetchone()

        # 2. GARSON PROFİLİ
        elif role == 'waiter':
            # Giriş sisteminizde garsonun ID'sini 'waiter_id' olarak tuttuğunuzu varsayıyoruz
            waiter_id = session.get('waiter_id') or session.get('user_id') 
            cursor.execute("SELECT name, email, password FROM waiters WHERE waiter_id = %s", (waiter_id,))
            user_data = cursor.fetchone()

        # 3. RESTORAN SAHİBİ VEYA ADMIN PROFİLİ
        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            # 'users' tablonuzdaki alan adlarına göre (username/email/password) uyarlayabilirsiniz
            cursor.execute("SELECT username, email, password FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()

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
            address = request.form.get('address')

            cursor.execute("""
                UPDATE customers SET name = %s, phone = %s, address = %s WHERE customer_id = %s
            """, (name, phone, address, customer_id))
            connection.commit()
            flash("Profil bilgileriniz başarıyla güncellendi! ✨", "success")

        # 2. GARSON GÜNCELLEME
        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id')
            name = request.form.get('name')
            password = request.form.get('password')

            cursor.execute("""
                UPDATE waiters SET name = %s, password = %s WHERE waiter_id = %s
            """, (name, password, waiter_id))
            connection.commit()
            flash("Garson profil ve şifre bilgileriniz güncellendi! 🔐", "success")

        # 3. RESTORAN SAHİBİ / ADMIN GÜNCELLEME
        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            cursor.execute("""
                UPDATE users SET username = %s, email = %s, password = %s WHERE user_id = %s
            """, (username, email, password, user_id))
            connection.commit()
            flash("Yönetici hesap ayarlarınız başarıyla güncellendi! 🚀", "success")

    except Error as e:
        connection.rollback()
        flash(f"Güncelleme sırasında bir hata oluşti: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('view_profile'))