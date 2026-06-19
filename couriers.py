from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
from werkzeug.security import generate_password_hash

def couriers():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('couriers.html', couriers=[])

    try:
        cursor = connection.cursor(dictionary=True)
        # Kuryeleri en son eklenenden en eskiye doğru sıralıyoruz
        if role == 'admin':
            cursor.execute('''
                SELECT c.*, r.restaurant_name 
                FROM couriers c
                LEFT JOIN restaurants r ON c.restaurant_id = r.restaurant_id
                ORDER BY c.courier_id DESC
            ''')
            couriers = cursor.fetchall()
        elif role == 'user' and restaurant_id:
            cursor.execute('SELECT * FROM couriers WHERE restaurant_id = %s ORDER BY courier_id DESC', (restaurant_id,))
            couriers = cursor.fetchall()
        else:
            flash("Yetkisiz erişim!", "danger")
            return redirect(url_for('index'))
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        couriers = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('couriers.html', couriers=couriers)
    
def courier_action():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('couriers'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            name = request.form.get('name')
            gender = request.form.get('gender')
            birth_date = request.form.get('birth_date')
            email = request.form.get('email')
            password = request.form.get('password') 

            restaurant_id = restaurant_id_session if role == 'user' else request.form.get('restaurant_id')

            if not all([name, gender, birth_date, restaurant_id, email, password]):
                flash("Lütfen tüm alanları doldurun.", "warning")
                return redirect(url_for('couriers'))
            
            hashed_password = generate_password_hash(password)

            # Restoran kontrolü
            cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            if cursor.fetchone()['count'] == 0:
                flash('Geçersiz Restoran ID!', 'danger')
                return redirect(url_for('couriers'))

            # ID sormuyoruz! MySQL AUTO_INCREMENT otomatik olarak kendi verecek.
            query = '''INSERT INTO couriers (name, gender, birth_date, restaurant_id, email, password) 
                       VALUES (%s, %s, %s, %s, %s, %s)'''
            cursor.execute(query, (name, gender, birth_date, restaurant_id, email, hashed_password))
            connection.commit()
            flash("Kurye başarıyla eklendi!", "success")

        elif action == 'delete':
            selected_ids = request.form.get('selected_couriers')
            if not selected_ids:
                flash("Silinecek kurye seçilmedi.", "warning")
                return redirect(url_for('couriers'))

            ids_list = selected_ids.split(',')

            if role == 'user':
                format_strings = ','.join(['%s'] * len(ids_list))
                query = f"DELETE FROM couriers WHERE courier_id IN ({format_strings}) AND restaurant_id = %s"
                cursor.execute(query, ids_list + [restaurant_id_session])
            else:
                format_strings = ','.join(['%s'] * len(ids_list))
                query = f"DELETE FROM couriers WHERE courier_id IN ({format_strings})"
                cursor.execute(query, ids_list)

            connection.commit()
            flash(f"{cursor.rowcount} kurye başarıyla silindi.", "success")

        elif action == 'update':
            update_courier_id = request.form.get('update_courier_id')
            name = request.form.get('name')
            gender = request.form.get('gender')
            birth_date = request.form.get('birth_date')
            email = request.form.get('email')
            password = request.form.get('password')

            restaurant_id = restaurant_id_session if role == 'user' else request.form.get('restaurant_id')

            if not update_courier_id:
                flash("Güncellenecek kurye seçilmedi.", "warning")
                return redirect(url_for('couriers'))
            
            if not all([name, gender, birth_date, email]):
                flash("Lütfen güncelleme için gerekli tüm alanları doldurun.", "warning")
                return redirect(url_for('couriers'))

            # Şifre girildiyse şifreyi de güncelle, boş bırakıldıysa dokunma
            if password:
                hashed_password = generate_password_hash(password)
                query = '''UPDATE couriers 
                           SET name = %s, gender = %s, birth_date = %s, email = %s, password = %s 
                           WHERE courier_id = %s AND restaurant_id = %s'''
                cursor.execute(query, (name, gender, birth_date, email, hashed_password, update_courier_id, restaurant_id))
            else:
                query = '''UPDATE couriers 
                           SET name = %s, gender = %s, birth_date = %s, email = %s 
                           WHERE courier_id = %s AND restaurant_id = %s'''
                cursor.execute(query, (name, gender, birth_date, email, update_courier_id, restaurant_id))
            
            connection.commit()
            flash("Kurye başarıyla güncellendi!", "success")

        elif action == 'filter':
            name = request.form.get('name')

            query = """
                SELECT c.*, r.restaurant_name 
                FROM couriers c
                LEFT JOIN restaurants r ON c.restaurant_id = r.restaurant_id
                WHERE 1=1
            """
            params = []
            
            if role == 'user':
                query += " AND c.restaurant_id = %s"
                params.append(restaurant_id_session)

            if name:
                query += " AND c.name LIKE %s"
                params.append(f"%{name}%")

            query += " ORDER BY c.courier_id DESC"
            cursor.execute(query, params)
            couriers = cursor.fetchall()
            
            if couriers:
                flash(f"Arama sonucunda {len(couriers)} kurye bulundu.", "success")
            else:
                flash("Aradığınız kritere uygun kurye bulunamadı.", "info")
                
            return render_template('couriers.html', couriers=couriers)

        elif action == 'clear':
            return redirect(url_for('couriers'))

    except Error as e:
        connection.rollback()
        if "Duplicate entry" in str(e):
            flash("Bu e-posta adresi zaten başka bir personel tarafından kullanılıyor!", "danger")
        else:
            flash(f"Bir hata oluştu: {str(e)}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('couriers'))

def api_check_courier_orders():
    if 'courier_id' not in session:
        return jsonify({'has_changes': False})

    courier_id = session.get('courier_id')
    client_order_count = request.args.get('order_count', 0, type=int)

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT COUNT(*) as active_count 
                FROM orders 
                WHERE courier_id = %s AND order_status IN ('ready', 'on_the_way')
            """, (courier_id,))
            
            result = cursor.fetchone()
            db_active_count = result['active_count'] if result else 0
            
            if db_active_count > client_order_count:
                return jsonify({'has_changes': True, 'message': '<i class="ph-bold ph-package"></i> YENİ PAKET GELDİ!'})
            elif db_active_count < client_order_count:
                return jsonify({'has_changes': True, 'message': '<i class="ph-bold ph-arrows-clockwise"></i> Paket durumu değişti.'})
                
        except Exception as e:
            print(f"Kurye API hatası: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return jsonify({'has_changes': False})
