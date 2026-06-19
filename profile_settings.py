from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
from werkzeug.security import generate_password_hash
import re

def view_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    connection = get_db_connection()
    user_data = None

    if connection is None:
        flash("Veritabanı bağlantısı başarısız!", "error")
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)

        if role == 'customer':
            customer_id = session.get('customer_id')
            # Müşterinin e-posta adresi de artık ekranda gösterildiği için sorguya 'email' eklendi
            cursor.execute("SELECT name, phone, email FROM customers WHERE customer_id = %s", (customer_id,))
            user_data = cursor.fetchone()
            
            # 📍 SİHİRLİ YÖNLENDİRME: Müşteri ise yepyeni B2C sayfasına yönlendir
            return render_template('customer_profile.html', user_data=user_data)

        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id') 
            cursor.execute("SELECT name, email FROM waiters WHERE waiter_id = %s", (waiter_id,))
            user_data = cursor.fetchone()
            
            # B2B paneli kullanmaya devam ederler
            return render_template('profile.html', user_data=user_data)

        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            cursor.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            # B2B paneli kullanmaya devam ederler (Harita/Saat verileri buradan tamamen söküldü!)
            return render_template('profile.html', user_data=user_data)

    except Error as e:
        flash(f"Profil bilgileri yüklenirken hata oluştu: {e}", "error")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    if not user_data:
        flash("Kullanıcı bilgileri bulunamadı.", "error")
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

        if role == 'customer':
            customer_id = session.get('customer_id')
            name = request.form.get('name')
            raw_phone = request.form.get('phone', '') 
            password = request.form.get('password') 

            clean_phone = re.sub(r'\D', '', raw_phone)
            
            if clean_phone and not re.match(r'^05\d{9}$', clean_phone):
                flash("Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)", "error")
                return redirect(url_for('view_profile'))

            if password:
                hashed_password = generate_password_hash(password)
                cursor.execute("""
                    UPDATE customers SET name = %s, phone = %s, password = %s WHERE customer_id = %s
                """, (name, clean_phone, hashed_password, customer_id)) 
            else:
                cursor.execute("""
                    UPDATE customers SET name = %s, phone = %s WHERE customer_id = %s
                """, (name, clean_phone, customer_id)) 
                
            connection.commit()
            flash("Profil bilgileriniz başarıyla güncellendi! ✨", "success")

        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id')
            name = request.form.get('name')
            password = request.form.get('password')

            if password: 
                hashed_password = generate_password_hash(password) 
                cursor.execute("UPDATE waiters SET name = %s, password = %s WHERE waiter_id = %s", (name, hashed_password, waiter_id))
            else: 
                cursor.execute("UPDATE waiters SET name = %s WHERE waiter_id = %s", (name, waiter_id))
                
            connection.commit()
            flash("Garson profil bilgileriniz güncellendi! <i class='ph-bold ph-lock-key'></i>", "success")

        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if password: 
                hashed_password = generate_password_hash(password) 
                cursor.execute("UPDATE users SET name = %s, email = %s, password = %s WHERE user_id = %s", (name, email, hashed_password, user_id))
            else: 
                cursor.execute("UPDATE users SET name = %s, email = %s WHERE user_id = %s", (name, email, user_id))
            
            connection.commit()
            flash("Hesap ayarlarınız başarıyla güncellendi! <i class='ph-bold ph-rocket-launch'></i>", "success")

    except Error as e:
        connection.rollback()
        flash(f"Güncelleme sırasında bir hata oluştu: {e}", "error")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('view_profile'))