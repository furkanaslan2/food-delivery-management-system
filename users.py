from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
from werkzeug.security import generate_password_hash

def users():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    user_id = session.get('user_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)
        
        if role == 'admin':
            # 📍 Admin için restoranları da getiren akıllı sorgu
            cursor.execute('''
                SELECT u.*, r.restaurant_name 
                FROM users u 
                LEFT JOIN restaurants r ON u.user_id = r.user_id 
                ORDER BY u.user_id DESC
            ''')
            users_data = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            users_data = cursor.fetchall()
            
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        users_data = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('users.html', users=users_data)

def user_action():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    session_user_id = session.get('user_id')

    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('users'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add' and role == 'admin':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password') 

            if not all([name, email, password]):
                flash("Lütfen ad, email ve şifre alanlarını doldurun.", "warning")
                return redirect(url_for('users'))
            
            hashed_password = generate_password_hash(password)

            query = 'INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)'
            cursor.execute(query, (name, email, hashed_password, 'user'))
            connection.commit()
            flash("Kullanıcı başarıyla eklendi!", "success")

        elif action == 'delete' and role == 'admin':
            selected_ids = request.form.get('selected_users')
            if not selected_ids:
                flash("Silinecek kullanıcı seçilmedi.", "warning")
                return redirect(url_for('users'))

            ids_list = selected_ids.split(',')
            format_strings = ','.join(['%s'] * len(ids_list))
            
            query = f"DELETE FROM users WHERE user_id IN ({format_strings}) AND role != 'admin'"
            cursor.execute(query, ids_list)
            connection.commit()
            flash(f"{cursor.rowcount} kullanıcı başarıyla silindi.", "success")

        elif action == 'update':
            update_user_id = request.form.get('update_user_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if not update_user_id:
                flash("Güncellenecek kullanıcı seçilmedi.", "warning")
                return redirect(url_for('users'))
            
            if role == 'user' and str(update_user_id) != str(session_user_id):
                flash("Sadece kendi profilinizi güncelleyebilirsiniz!", "danger")
                return redirect(url_for('users'))
            
            if not all([name, email]):
                flash("Lütfen ad ve email alanlarını doldurun.", "warning")
                return redirect(url_for('users'))

            if password:
                hashed_password = generate_password_hash(password)
                query = "UPDATE users SET name = %s, email = %s, password = %s WHERE user_id = %s"
                cursor.execute(query, (name, email, hashed_password, update_user_id))
            else:
                query = "UPDATE users SET name = %s, email = %s WHERE user_id = %s"
                cursor.execute(query, (name, email, update_user_id))
            
            connection.commit()
            flash("Profil bilgileri başarıyla güncellendi!", "success")

        elif action == 'filter' and role == 'admin':
            name = request.form.get('name')

            # 📍 Admin Filtrelemesinde de Restoranı getir
            query = """
                SELECT u.*, r.restaurant_name 
                FROM users u 
                LEFT JOIN restaurants r ON u.user_id = r.user_id 
                WHERE 1=1
            """
            params = []
            
            if name:
                query += " AND u.name LIKE %s" 
                params.append(f"%{name}%")
            
            query += " ORDER BY u.user_id DESC"

            cursor.execute(query, params)
            users_data = cursor.fetchall()
            
            if users_data:
                flash(f"Arama sonucunda {len(users_data)} kullanıcı bulundu.", "success")
            else:
                flash("Aradığınız kritere uygun kullanıcı bulunamadı.", "info")
                
            return render_template('users.html', users=users_data)

        elif action == 'clear':
            return redirect(url_for('users'))

    except Error as e:
        flash(f"Bir hata oluştu: {e}", "danger")
        connection.rollback()
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('users'))