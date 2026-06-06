from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from db import get_db_connection
from mysql.connector import Error

def partner_applications():
    # Sadece Admin girebilir
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash("Bu sayfayı görüntüleme yetkiniz yok.", "danger")
        return redirect(url_for('index'))

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanı bağlantısı kurulamadı.", "danger")
        return redirect(url_for('index'))

    applications = []
    try:
        cursor = connection.cursor(dictionary=True)
        # Sadece bekleyen başvuruları (pending) tersten sıralayarak al
        cursor.execute("SELECT * FROM restaurant_applications WHERE status = 'pending' ORDER BY applied_at DESC")
        applications = cursor.fetchall()
    except Error as e:
        flash(f"Başvurular yüklenirken hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('partner_applications.html', applications=applications)


def approve_application(app_id):
    if 'logged_in' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 1. Başvuruyu Bul
        cursor.execute("SELECT * FROM restaurant_applications WHERE application_id = %s AND status = 'pending'", (app_id,))
        app_data = cursor.fetchone()
        
        if not app_data:
            flash("Başvuru bulunamadı veya zaten işlenmiş.", "danger")
            return redirect(url_for('partner_applications'))

        # 2. Rastgele Kurumsal Şifre Üret (Örn: RestoranAdı2026)
        raw_password = f"{app_data['restaurant_name'].replace(' ', '')[:6]}2026!"
        hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')

        # 3. Adamı Restoran Sahibi (users) olarak kaydet
        cursor.execute(
            'INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', 
            (app_data['contact_name'], app_data['email'], hashed_password)
        )
        new_user_id = cursor.lastrowid 

        # 4. Adamın Restoran Profilini (restaurants) kur
        cursor.execute('''
            INSERT INTO restaurants 
            (user_id, restaurant_name, city, rating, rating_count, cuisine, restaurant_address, table_count) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            new_user_id, app_data['restaurant_name'], 'Belirtilmedi', 0.0, 'Too Few Ratings', 'Belirtilmedi', 'Belirtilmedi', 10
        ))

        # 5. Başvuruyu "Onaylandı" olarak işaretle (Bir daha ekranda görünmesin)
        cursor.execute("UPDATE restaurant_applications SET status = 'approved' WHERE application_id = %s", (app_id,))

        connection.commit()
        
        # Admin'e mesaj ver (Gerçekte bu şifre mail olarak gider, şimdilik ekrana basıyoruz)
        flash(f"✅ {app_data['restaurant_name']} başarıyla eklendi! Giriş E-postası: {app_data['email']}, Şifresi: {raw_password}", "success")
        
    except Error as e:
        connection.rollback()
        flash(f"Onaylama sırasında hata: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('partner_applications'))