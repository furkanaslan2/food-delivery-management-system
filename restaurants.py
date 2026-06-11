from flask import render_template, request, redirect, url_for, session, flash, jsonify
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
            table_count = request.form.get('table_count') # 🛠️ EKLENDİ
            
            user_id = session_user_id if role == 'user' else request.form.get('user_id')

            if not all([restaurant_name, city, cuisine, restaurant_address, user_id, table_count]):
                flash("Lütfen gerekli tüm alanları doldurun.", "warning")
                return redirect(url_for('restaurants'))

            # Bir kullanıcının sadece 1 restoranı olabilir kontrolü
            cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE user_id = %s", (user_id,))
            if cursor.fetchone()['count'] > 0:
                flash("Bu kullanıcının zaten bir restoranı var!", "danger")
                return redirect(url_for('restaurants'))

            # 🛠️ SQL SORGUSUNA TABLE_COUNT EKLENDİ
            query = '''INSERT INTO restaurants (user_id, restaurant_name, city, cuisine, restaurant_address, table_count) 
                       VALUES (%s, %s, %s, %s, %s, %s)'''
            cursor.execute(query, (user_id, restaurant_name, city, cuisine, restaurant_address, table_count))
            connection.commit()
            flash("Restoran başarıyla eklendi!", "success")

        elif action == 'update':
            update_restaurant_id = request.form.get('update_restaurant_id')
            restaurant_name = request.form.get('restaurant_name')
            city = request.form.get('city')
            cuisine = request.form.get('cuisine')
            restaurant_address = request.form.get('restaurant_address')
            table_count = request.form.get('table_count') # 🛠️ EKLENDİ

            if not update_restaurant_id:
                flash("Güncellenecek restoran seçilmedi.", "warning")
                return redirect(url_for('restaurants'))

            # Güvenlik Kontrolü
            if role == 'user':
                cursor.execute("SELECT user_id FROM restaurants WHERE restaurant_id = %s", (update_restaurant_id,))
                res = cursor.fetchone()
                if not res or str(res['user_id']) != str(session_user_id):
                    flash("Yetkisiz işlem! Sadece kendi restoranınızı güncelleyebilirsiniz.", "danger")
                    return redirect(url_for('restaurants'))

            # 🛠️ SQL SORGUSUNA TABLE_COUNT EKLENDİ
            query = '''UPDATE restaurants 
                       SET restaurant_name = %s, city = %s, cuisine = %s, restaurant_address = %s, table_count = %s 
                       WHERE restaurant_id = %s'''
            cursor.execute(query, (restaurant_name, city, cuisine, restaurant_address, table_count, update_restaurant_id))
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
        flash("Veritabanı bağlantısı başarısız!", "danger")
        return redirect(url_for('index'))

    try:
        cursor = connection.cursor(dictionary=True)

        # 📊 1. GRAFİK: EN ÇOK SATAN 5 ÜRÜN (Son 30 Gün Trendi)
        cursor.execute("""
            SELECT COALESCE(m.custom_name, f.item_name) as item_name, SUM(oi.quantity) as total_sold
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN foods f ON oi.food_id = f.food_id
            LEFT JOIN menus m ON oi.food_id = m.food_id AND m.restaurant_id = o.restaurant_id
            WHERE o.restaurant_id = %s AND o.order_status IN ('completed', 'delivered')
            AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY oi.food_id, m.custom_name, f.item_name
            ORDER BY total_sold DESC
            LIMIT 5
        """, (restaurant_id,))
        top_items = cursor.fetchall()
        top_item_labels = [row['item_name'] for row in top_items]
        top_item_data = [float(row['total_sold']) for row in top_items]

        # 📈 2. GRAFİK: SON 7 GÜNLÜK CİRO TRENDİ
        cursor.execute("""
            SELECT DATE(order_date) as order_day, SUM(sales_amount) as daily_revenue
            FROM orders 
            WHERE restaurant_id = %s AND order_status IN ('completed', 'delivered')
            AND order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(order_date)
            ORDER BY DATE(order_date) ASC
        """, (restaurant_id,))
        revenue_trend = cursor.fetchall()
        trend_labels = [row['order_day'].strftime('%d %b') for row in revenue_trend]
        trend_data = [float(row['daily_revenue']) for row in revenue_trend]

        # 🛵 3. GRAFİK: KURYE PERFORMANSI (Son 30 Günde En Çok Atanlar)
        cursor.execute("""
            SELECT c.name as courier_name, COUNT(o.order_id) as total_deliveries
            FROM orders o
            JOIN couriers c ON o.courier_id = c.courier_id
            WHERE o.restaurant_id = %s AND o.order_status = 'delivered'
            AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY c.courier_id
            ORDER BY total_deliveries DESC
            LIMIT 5
        """, (restaurant_id,))
        courier_stats = cursor.fetchall()
        courier_labels = [row['courier_name'] for row in courier_stats]
        courier_data = [int(row['total_deliveries']) for row in courier_stats]

        # 🍩 4. GRAFİK: SİPARİŞ DAĞILIMI (Son 30 Gün)
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND (LOWER(order_type) NOT IN ('dine-in', 'masa') OR order_type IS NULL)
            AND order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, (restaurant_id,))
        chart_delivery_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND LOWER(order_type) IN ('dine-in', 'masa')
            AND order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, (restaurant_id,))
        chart_dinein_count = cursor.fetchone()['count']

        # 📝 ÖZET KARTLARI İÇİN GENEL VERİLER (SADECE BUGÜN!)
        cursor.execute("""
            SELECT SUM(sales_amount) as total_revenue, COUNT(*) as total_orders 
            FROM orders 
            WHERE restaurant_id = %s AND order_status IN ('completed', 'delivered')
            AND DATE(order_date) = CURDATE()
        """, (restaurant_id,))
        stats = cursor.fetchone()
        total_revenue = float(stats['total_revenue']) if stats['total_revenue'] else 0.0
        total_orders = stats['total_orders'] if stats['total_orders'] else 0

        cursor.execute("""
            SELECT COUNT(*) as delivery_count 
            FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND (LOWER(order_type) NOT IN ('dine-in', 'masa') OR order_type IS NULL)
            AND DATE(order_date) = CURDATE()
        """, (restaurant_id,))
        delivery_count = cursor.fetchone()['delivery_count']

        cursor.execute("""
            SELECT COUNT(*) as dinein_count 
            FROM orders 
            WHERE restaurant_id = %s AND order_status != 'canceled' 
            AND LOWER(order_type) IN ('dine-in', 'masa')
            AND DATE(order_date) = CURDATE()
        """, (restaurant_id,))
        dinein_count = cursor.fetchone()['dinein_count']

        # Restoran Puanı (Genel Prestij - Tüm Zamanlar)
        cursor.execute("SELECT rating, rating_count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        res_info = cursor.fetchone()
        restaurant_rating = res_info['rating'] if res_info['rating'] else 0.0
        rating_enum = res_info['rating_count'] if res_info['rating_count'] else "No Ratings"

    except Exception as e:
        flash(f"Analiz verileri alınırken hata oluştu: {e}", "danger")
        top_item_labels, top_item_data, trend_labels, trend_data, courier_labels, courier_data = [], [], [], [], [], []
        chart_delivery_count, chart_dinein_count = 0, 0
        total_revenue, total_orders, delivery_count, dinein_count, restaurant_rating, rating_enum = 0, 0, 0, 0, 0, ""
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            
    return render_template(
        'analytics.html', 
        top_item_labels=top_item_labels, top_item_data=top_item_data,
        trend_labels=trend_labels, trend_data=trend_data,
        courier_labels=courier_labels, courier_data=courier_data,
        chart_delivery_count=chart_delivery_count, chart_dinein_count=chart_dinein_count,
        total_revenue=total_revenue, total_orders=total_orders,
        delivery_count=delivery_count, dinein_count=dinein_count,
        restaurant_rating=restaurant_rating, rating_enum=rating_enum
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

def restaurant_reviews():
    # Sadece restoran sahipleri (user) görebilir
    if session.get('role') != 'user': 
        return redirect(url_for('login'))
        
    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    reviews = []
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Yorumları, müşteri adını ve sipariş bilgilerini birleştirerek çekiyoruz
            cursor.execute("""
                SELECT r.*, c.name as customer_name, o.order_date, o.sales_amount 
                FROM reviews r
                JOIN customers c ON r.customer_id = c.customer_id
                JOIN orders o ON r.order_id = o.order_id
                WHERE r.restaurant_id = %s
                ORDER BY r.created_at DESC
            """, (restaurant_id,))
            reviews = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
            
    return render_template('restaurant_reviews.html', reviews=reviews)

def reply_review():
    if session.get('role') != 'user':
        return jsonify({'success': False, 'message': 'Yetkisiz işlem.'}), 401

    data = request.get_json()
    order_id = data.get('order_id')
    reply_text = data.get('reply_text')
    restaurant_id = session.get('restaurant_id')

    if not reply_text:
        return jsonify({'success': False, 'message': 'Yanıt boş olamaz.'})

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE reviews 
                SET restaurant_reply = %s 
                WHERE order_id = %s AND restaurant_id = %s
            """, (reply_text, order_id, restaurant_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Yanıtınız başarıyla müşteriye iletildi!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cursor.close()
            connection.close()
            
    return jsonify({'success': False, 'message': 'Veritabanı hatası.'}), 500