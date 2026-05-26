from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
import datetime 

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

        if role == 'customer':
            customer_id = session.get('customer_id')
            cursor.execute("SELECT name, phone FROM customers WHERE customer_id = %s", (customer_id,))
            user_data = cursor.fetchone()

        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id') 
            cursor.execute("SELECT name, email, password FROM waiters WHERE waiter_id = %s", (waiter_id,))
            user_data = cursor.fetchone()

        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            cursor.execute("SELECT name, email, password FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            if role == 'user' and user_data:
                restaurant_id = session.get('restaurant_id')
                if restaurant_id:
                    # YENİ: min_order_amount veritabanından çekiliyor
                    cursor.execute("SELECT latitude, longitude, opening_time, closing_time, is_manually_closed, min_order_amount FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                    res_data = cursor.fetchone()
                    
                    if res_data:
                        user_data['latitude'] = res_data['latitude']
                        user_data['longitude'] = res_data['longitude']
                        user_data['is_manually_closed'] = res_data['is_manually_closed']
                        user_data['min_order_amount'] = res_data.get('min_order_amount') or 0.00
                        
                        op_time = res_data.get('opening_time')
                        if isinstance(op_time, datetime.timedelta):
                            user_data['opening_time'] = (datetime.datetime.min + op_time).time().strftime('%H:%M')
                        else:
                            user_data['opening_time'] = "09:00"
                            
                        cl_time = res_data.get('closing_time')
                        if isinstance(cl_time, datetime.timedelta):
                            user_data['closing_time'] = (datetime.datetime.min + cl_time).time().strftime('%H:%M')
                        else:
                            user_data['closing_time'] = "23:00"

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

        if role == 'customer':
            customer_id = session.get('customer_id')
            name = request.form.get('name')
            phone = request.form.get('phone')

            cursor.execute("""
                UPDATE customers SET name = %s, phone = %s WHERE customer_id = %s
            """, (name, phone, customer_id))
            connection.commit()
            flash("Profil bilgileriniz başarıyla güncellendi! ✨", "success")

        elif role == 'waiter':
            waiter_id = session.get('waiter_id') or session.get('user_id')
            name = request.form.get('name')
            password = request.form.get('password')

            if password: 
                cursor.execute("UPDATE waiters SET name = %s, password = %s WHERE waiter_id = %s", (name, password, waiter_id))
            else: 
                cursor.execute("UPDATE waiters SET name = %s WHERE waiter_id = %s", (name, waiter_id))
                
            connection.commit()
            flash("Garson profil bilgileriniz güncellendi! 🔐", "success")

        elif role in ['user', 'admin']:
            user_id = session.get('user_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if password: 
                cursor.execute("UPDATE users SET name = %s, email = %s, password = %s WHERE user_id = %s", (name, email, password, user_id))
            else: 
                cursor.execute("UPDATE users SET name = %s, email = %s WHERE user_id = %s", (name, email, user_id))
            
            if role == 'user':
                restaurant_id = session.get('restaurant_id')
                latitude = request.form.get('latitude')
                longitude = request.form.get('longitude')
                opening_time = request.form.get('opening_time', '09:00')
                closing_time = request.form.get('closing_time', '23:00')
                is_manually_closed = 1 if request.form.get('is_manually_closed') == 'on' else 0
                
                # YENİ: min_order_amount formdan alınıp güncelleniyor
                min_order_amount = request.form.get('min_order_amount', 0)
                
                if restaurant_id:
                    cursor.execute("""
                        UPDATE restaurants 
                        SET latitude = %s, longitude = %s, opening_time = %s, closing_time = %s, is_manually_closed = %s, min_order_amount = %s 
                        WHERE restaurant_id = %s
                    """, (latitude, longitude, opening_time, closing_time, is_manually_closed, min_order_amount, restaurant_id))

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