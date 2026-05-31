from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
import json
import os
from werkzeug.utils import secure_filename

def restaurants():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    user_id = session.get('user_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('restaurants.html', restaurants=[])

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute('SELECT * FROM restaurants ORDER BY restaurant_id DESC')
            restaurants_data = cursor.fetchall()
        elif role == 'user' and user_id:
            cursor.execute('SELECT * FROM restaurants WHERE user_id = %s ORDER BY restaurant_id DESC', (user_id,))
            restaurants_data = cursor.fetchall()
        else:
            restaurants_data = []

    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        restaurants_data = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('restaurants.html', restaurants=restaurants_data)

def restaurant_action():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    session_user_id = session.get('user_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('restaurants'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            restaurant_name = request.form.get('restaurant_name')
            city = request.form.get('city')
            cuisine = request.form.get('cuisine')
            restaurant_address = request.form.get('restaurant_address')
            
            user_id = session_user_id if role == 'user' else request.form.get('user_id')

            if not all([restaurant_name, city, cuisine, restaurant_address, user_id]):
                flash("Lütfen gerekli tüm alanları doldurun.", "warning")
                return redirect(url_for('restaurants'))

            # Bir kullanıcının sadece 1 restoranı olabilir kontrolü
            cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE user_id = %s", (user_id,))
            if cursor.fetchone()['count'] > 0:
                flash("Bu kullanıcının zaten bir restoranı var!", "danger")
                return redirect(url_for('restaurants'))

            # MySQL AUTO_INCREMENT ID'yi otomatik atayacak. Manuel ID karmaşası kaldırıldı!
            query = '''INSERT INTO restaurants (user_id, restaurant_name, city, cuisine, restaurant_address) 
                       VALUES (%s, %s, %s, %s, %s)'''
            cursor.execute(query, (user_id, restaurant_name, city, cuisine, restaurant_address))
            connection.commit()
            flash("Restoran başarıyla eklendi!", "success")

        elif action == 'update':
            update_restaurant_id = request.form.get('update_restaurant_id')
            restaurant_name = request.form.get('restaurant_name')
            city = request.form.get('city')
            cuisine = request.form.get('cuisine')
            restaurant_address = request.form.get('restaurant_address')

            if not update_restaurant_id:
                flash("Güncellenecek restoran seçilmedi.", "warning")
                return redirect(url_for('restaurants'))

            # Güvenlik Kontrolü: Kullanıcı URL manipülasyonu ile başkasının restoranını güncelleyemez
            if role == 'user':
                cursor.execute("SELECT user_id FROM restaurants WHERE restaurant_id = %s", (update_restaurant_id,))
                res = cursor.fetchone()
                if not res or str(res['user_id']) != str(session_user_id):
                    flash("Yetkisiz işlem! Sadece kendi restoranınızı güncelleyebilirsiniz.", "danger")
                    return redirect(url_for('restaurants'))

            query = '''UPDATE restaurants 
                       SET restaurant_name = %s, city = %s, cuisine = %s, restaurant_address = %s 
                       WHERE restaurant_id = %s'''
            cursor.execute(query, (restaurant_name, city, cuisine, restaurant_address, update_restaurant_id))
            connection.commit()
            flash("Restoran bilgileri başarıyla güncellendi!", "success")

        elif action == 'delete':
            selected_ids = request.form.get('selected_restaurants')
            if not selected_ids:
                flash("Silinecek restoran seçilmedi.", "warning")
                return redirect(url_for('restaurants'))

            ids_list = selected_ids.split(',')
            format_strings = ','.join(['%s'] * len(ids_list))

            if role == 'user':
                query = f"DELETE FROM restaurants WHERE restaurant_id IN ({format_strings}) AND user_id = %s"
                cursor.execute(query, ids_list + [session_user_id])
            else:
                query = f"DELETE FROM restaurants WHERE restaurant_id IN ({format_strings})"
                cursor.execute(query, ids_list)

            connection.commit()
            flash(f"{cursor.rowcount} restoran başarıyla silindi.", "success")

        elif action == 'filter':
            restaurant_name = request.form.get('restaurant_name')
            
            query = "SELECT * FROM restaurants WHERE 1=1"
            params = []
            
            if role == 'user':
                query += " AND user_id = %s"
                params.append(session_user_id)

            if restaurant_name:
                query += " AND restaurant_name LIKE %s"
                params.append(f"%{restaurant_name}%")
            
            query += " ORDER BY restaurant_id DESC"
            cursor.execute(query, params)
            restaurants_data = cursor.fetchall()
            
            if restaurants_data:
                flash(f"Arama sonucunda {len(restaurants_data)} restoran bulundu.", "success")
            else:
                flash("Aradığınız kritere uygun restoran bulunamadı.", "info")
                
            return render_template('restaurants.html', restaurants=restaurants_data)

        elif action == 'clear':
            return redirect(url_for('restaurants'))

    except Error as e:
        connection.rollback()
        flash(f"Bir hata oluştu: {str(e)}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('restaurants'))

def restaurant_analytics():
    if not session.get('logged_in') or session.get('role') != 'user':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    
    if connection is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)

        query_charts = """
            SELECT f.item_name, SUM(oi.quantity) as total_sold
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN foods f ON oi.food_id = f.food_id
            WHERE o.restaurant_id = %s AND o.order_status IN ('completed', 'delivered')
            GROUP BY f.food_id
            ORDER BY total_sold DESC
            LIMIT 10
        """
        cursor.execute(query_charts, (restaurant_id,))
        results = cursor.fetchall()
        labels = [row['item_name'] for row in results]
        data = [float(row['total_sold']) for row in results] 

        cursor.execute("""
            SELECT SUM(sales_amount) as total_revenue, COUNT(*) as total_orders 
            FROM orders 
            WHERE restaurant_id = %s AND order_status IN ('completed', 'delivered')
        """, (restaurant_id,))
        stats = cursor.fetchone()
        total_revenue = float(stats['total_revenue']) if stats['total_revenue'] else 0.0
        total_orders = stats['total_orders'] if stats['total_orders'] else 0

        cursor.execute("""
            SELECT COUNT(*) as delivery_count 
            FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND (LOWER(order_type) NOT IN ('dine-in', 'masa') OR order_type IS NULL)
        """, (restaurant_id,))
        delivery_count = cursor.fetchone()['delivery_count']

        cursor.execute("""
            SELECT COUNT(*) as dinein_count 
            FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND LOWER(order_type) IN ('dine-in', 'masa')
        """, (restaurant_id,))
        dinein_count = cursor.fetchone()['dinein_count']

        cursor.execute("SELECT rating, rating_count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        res_info = cursor.fetchone()
        restaurant_rating = res_info['rating'] if res_info['rating'] else 0.0
        rating_enum = res_info['rating_count'] if res_info['rating_count'] else "No Ratings"

    except Exception as e:
        flash(f"Error fetching analytics: {e}", "danger")
        labels, data = [], []
        total_revenue, total_orders, delivery_count, dinein_count, restaurant_rating, rating_enum = 0, 0, 0, 0, 0, ""
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            
    return render_template(
        'analytics.html', 
        labels=labels, 
        data=data,
        total_revenue=total_revenue,
        total_orders=total_orders,
        delivery_count=delivery_count,
        dinein_count=dinein_count,
        restaurant_rating=restaurant_rating,
        rating_enum=rating_enum
    )

def restaurant_profile():
    if 'logged_in' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    restaurant = None

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            if request.method == 'POST':
                # Formdan gelen verileri al
                name = request.form.get('restaurant_name')
                cuisine = request.form.get('cuisine')
                opening_time = request.form.get('opening_time')
                closing_time = request.form.get('closing_time')
                min_order_amount = request.form.get('min_order_amount')
                is_manually_closed = 1 if request.form.get('is_manually_closed') else 0 
                latitude = request.form.get('latitude')
                longitude = request.form.get('longitude')
                image_file = request.files.get('restaurant_image')
                
                update_query = """
                    UPDATE restaurants 
                    SET restaurant_name = %s, 
                        cuisine = %s,
                        opening_time = %s,
                        closing_time = %s,
                        min_order_amount = %s,
                        is_manually_closed = %s,
                        latitude = %s,
                        longitude = %s
                """
                params = [name, cuisine, opening_time, closing_time, min_order_amount, is_manually_closed, latitude, longitude]
                
                # Resim yüklenmişse sorguya ekle
                if image_file and image_file.filename != '':
                    filename = secure_filename(image_file.filename)
                    upload_folder = os.path.join('static', 'images', 'restaurants')
                    os.makedirs(upload_folder, exist_ok=True) 
                    file_path = os.path.join(upload_folder, filename)
                    image_file.save(file_path)
                    
                    update_query += ", image_url = %s"
                    params.append(filename)
                
                update_query += " WHERE restaurant_id = %s"
                params.append(restaurant_id)
                
                cursor.execute(update_query, tuple(params))
                connection.commit()
                flash("Restoran ayarlarınız başarıyla güncellendi!", "success")

            # Ekranı yeniden yüklerken güncel verileri çek
            cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            restaurant = cursor.fetchone()
            
            # 🐛 BUG FİX: Zaman Formatını HTML5'in İstediği "09:00" Şekline Zorluyoruz
            if restaurant:
                for time_field in ['opening_time', 'closing_time']:
                    if restaurant.get(time_field) is not None:
                        t_str = str(restaurant[time_field])
                        # Eğer saat tek haneliyse (Örn: "9:00:00") başına "0" ekle ("09:00:00")
                        if len(t_str.split(':')[0]) == 1:
                            t_str = '0' + t_str
                        # Sadece ilk 5 karakteri (SS:DD) al ("09:00") ve HTML'e gönder
                        restaurant[time_field] = t_str[:5]
            
        except Exception as e:
            print(f"Profil güncellenirken hata: {e}")
            flash("Bir hata oluştu.", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('restaurant_profile.html', restaurant=restaurant)