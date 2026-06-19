from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from db import get_db_connection
from mysql.connector import Error
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        
        cursor.execute("SELECT * FROM restaurant_applications WHERE application_id = %s AND status = 'pending'", (app_id,))
        app_data = cursor.fetchone()
        
        if not app_data:
            flash("Başvuru bulunamadı veya zaten işlenmiş.", "danger")
            return redirect(url_for('partner_applications'))

        raw_password = f"{app_data['restaurant_name'].replace(' ', '')[:6]}2026!"
        hashed_password = generate_password_hash(raw_password, method='pbkdf2:sha256')

        cursor.execute(
            'INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', 
            (app_data['contact_name'], app_data['email'], hashed_password)
        )
        new_user_id = cursor.lastrowid 

        cursor.execute('''
            INSERT INTO restaurants 
            (user_id, restaurant_name, city, rating, rating_count, cuisine, restaurant_address, table_count) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            new_user_id, app_data['restaurant_name'], 'Belirtilmedi', 0.0, 'Yeni', 'Belirtilmedi', 'Belirtilmedi', 10
        ))

        cursor.execute("UPDATE restaurant_applications SET status = 'approved' WHERE application_id = %s", (app_id,))

        connection.commit()
        
        mail_sent = send_approval_email(app_data['email'], app_data['restaurant_name'], raw_password)
        
        if mail_sent:
            flash(f"<i class='ph-bold ph-check-circle'></i> {app_data['restaurant_name']} onaylandı ve giriş şifresi e-posta adresine başarıyla gönderildi!", "success")
        else:
            flash(f"<i class='ph-bold ph-check-circle'></i> {app_data['restaurant_name']} onaylandı ANCAK e-posta gönderilemedi. Lütfen şifreyi manuel iletin: {raw_password}", "warning")
        
    except Error as e:
        connection.rollback()
        flash(f"Onaylama sırasında hata: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('partner_applications'))

def reject_application(app_id):
    # Sadece Admin girebilir
    if 'logged_in' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanı bağlantısı kurulamadı.", "danger")
        return redirect(url_for('partner_applications'))

    try:
        cursor = connection.cursor()

        cursor.execute("DELETE FROM restaurant_applications WHERE application_id = %s", (app_id,))
        connection.commit()
        
        flash("<i class='ph-bold ph-x-circle'></i> İş ortağı başvurusu reddedildi ve sistemden silindi.", "success")
        
    except Error as e:
        connection.rollback()
        flash(f"Reddetme işlemi sırasında hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('partner_applications'))

def send_approval_email(to_email, restaurant_name, password):
    sender_email = os.getenv('MAIL_USERNAME')
    sender_password = os.getenv('MAIL_PASSWORD')

    if not sender_email or not sender_password:
        print("HATA: .env dosyasında MAIL_USERNAME veya MAIL_PASSWORD eksik!")
        return False

    subject = "Tebrikler! YeSende Restoran Başvurunuz Onaylandı 🎉"
    body = f"""
    Merhaba,
    
    Tebrikler! {restaurant_name} için yapmış olduğunuz YeSende iş ortağı başvurunuz onaylanmıştır.
    
    Sisteme giriş yaparak menünüzü oluşturabilir, çalışma saatlerinizi ayarlayabilir ve hemen sipariş almaya başlayabilirsiniz.
    
    Giriş Bağlantısı: http://127.0.0.1:5000/login
    Giriş E-postanız: {to_email}
    Geçici Şifreniz: {password}
    
    Güvenliğiniz için lütfen giriş yaptıktan sonra 'Ayarlar' bölümünden şifrenizi değiştirmeyi unutmayın.
    
    Aramıza hoş geldiniz!
    YeSende Ekibi
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Onay maili gönderme hatası: {e}")
        return False