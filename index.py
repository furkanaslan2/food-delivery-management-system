from flask import render_template, request, redirect, url_for, session, flash
import math
import datetime 
from db import get_db_connection
from mysql.connector import Error

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def index():
    if 'logged_in' not in session:
        return redirect(url_for('customer_login'))

    role = session.get('role')

    if role == 'customer':
        search_query = request.args.get('search', '').strip()
        min_rating = request.args.get('min_rating', '0')
        
        connection = get_db_connection()
        restaurants = []
        
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                sql_query = """
                    SELECT DISTINCT r.* FROM restaurants r
                    LEFT JOIN menus m ON r.restaurant_id = m.restaurant_id
                    LEFT JOIN foods f ON m.food_id = f.food_id
                    WHERE 1=1
                """
                query_params = []

                if search_query:
                    sql_query += " AND (r.restaurant_name LIKE %s OR r.cuisine LIKE %s OR f.item_name LIKE %s)"
                    like_pattern = f"%{search_query}%"
                    query_params.extend([like_pattern, like_pattern, like_pattern])

                if min_rating and float(min_rating) > 0:
                    sql_query += " AND r.rating >= %s"
                    query_params.append(float(min_rating))

                cursor.execute(sql_query, tuple(query_params))
                all_restaurants = cursor.fetchall()
                
                customer_lat = session.get('latitude')
                customer_lon = session.get('longitude')
                now = datetime.datetime.now().time()

                if (not customer_lat or not customer_lon) and session.get('customer_id'):
                    cursor.execute("SELECT latitude, longitude, city, district FROM customer_addresses WHERE customer_id = %s AND is_active = 1", (session.get('customer_id'),))
                    active_addr = cursor.fetchone()
                    if active_addr:
                        customer_lat = active_addr['latitude']
                        customer_lon = active_addr['longitude']
                        session['latitude'] = customer_lat
                        session['longitude'] = customer_lon
                        session['customer_city'] = f"{active_addr['district']}, {active_addr['city']}"

                if customer_lat and customer_lon:
                    nearby_restaurants = []
                    for r in all_restaurants:
                        if r['latitude'] and r['longitude']:
                            dist = calculate_distance(float(customer_lat), float(customer_lon), float(r['latitude']), float(r['longitude']))
                            r['distance'] = round(dist, 1) 
                            
                            if r['distance'] <= 10.0:
                                nearby_restaurants.append(r)
                                
                    all_restaurants = nearby_restaurants 
                else:
                    for r in all_restaurants:
                        r['distance'] = 999 

                for r in all_restaurants:
                    is_open = True
                    if r.get('is_manually_closed'):
                        is_open = False
                    elif r.get('opening_time') is not None and r.get('closing_time') is not None:
                        op_td = r['opening_time']
                        cl_td = r['closing_time']
                        
                        op_time = (datetime.datetime.min + op_td).time() if isinstance(op_td, datetime.timedelta) else op_td
                        cl_time = (datetime.datetime.min + cl_td).time() if isinstance(cl_td, datetime.timedelta) else cl_td
                        
                        if op_time < cl_time:
                            is_open = op_time <= now <= cl_time
                        else:
                            is_open = now >= op_time or now <= cl_time
                            
                    r['is_open'] = is_open

                if customer_lat and customer_lon:
                    all_restaurants.sort(key=lambda x: (not x.get('is_open', True), x.get('distance', 999)))
                else:
                    all_restaurants.sort(key=lambda x: (not x.get('is_open', True), -float(x.get('rating', 0) or 0)))

                restaurants = all_restaurants

                favorited_restaurant_ids = []
                if session.get('customer_id'):
                    cursor.execute("SELECT restaurant_id FROM favorite_restaurants WHERE customer_id = %s", (session.get('customer_id'),))
                    favorited_restaurant_ids = [row['restaurant_id'] for row in cursor.fetchall()]

            except Exception as e:
                print(f"Restoranlar yüklenirken hata: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return render_template('customer_index.html', restaurants=restaurants, favorited_restaurant_ids=favorited_restaurant_ids)

    if role == 'waiter':
        return redirect(url_for('waiter_dashboard'))

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('index.html', statistics=[])

    statistics = {
        'users': 0, 'restaurants': 0, 'menus': 0, 'foods': 0,
        'orders': 0, 'couriers': 0, 'waiters': 0
    }
    
    # 🔥 YENİ: Son Siparişleri Tutacağımız Liste
    recent_orders = []

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            # Admin için tüm restoranlardan gelen son 5 sipariş
            cursor.execute("SELECT order_id, order_date, order_type, customer_name, table_no, sales_amount, order_status FROM orders WHERE order_status != 'awaiting_payment' ORDER BY order_id DESC LIMIT 5")
            recent_orders = cursor.fetchall()
            
            queries = {
                'users': "SELECT COUNT(*) AS count FROM users",
                'restaurants': "SELECT COUNT(*) AS count FROM restaurants",
                'menus': "SELECT COUNT(*) AS count FROM menus",
                'foods': "SELECT COUNT(*) AS count FROM foods",
                'orders': "SELECT COUNT(*) AS count FROM orders WHERE order_status != 'awaiting_payment'",
                'couriers': "SELECT COUNT(*) AS count FROM couriers",
                'waiters': "SELECT COUNT(*) AS count FROM waiters"
            }
        elif role == 'user':
            user_id = session.get('user_id')
            restaurant_id = session.get('restaurant_id')
            
            # Sadece o restorana ait son 5 sipariş
            # 📍 KESİN ÇÖZÜM: Son 5 siparişi getir ama ödeme bekleyen "hayaletleri" hariç tut!
            cursor.execute("SELECT order_id, order_date, order_type, customer_name, table_no, sales_amount, order_status FROM orders WHERE restaurant_id = %s AND order_status != 'awaiting_payment' ORDER BY order_id DESC LIMIT 5", (restaurant_id,))
            recent_orders = cursor.fetchall()
            
            queries = {
                'menus': f"SELECT COUNT(*) AS count FROM menus WHERE restaurant_id = {restaurant_id}",
                'foods': f"SELECT COUNT(DISTINCT f.food_id) AS count FROM foods f JOIN menus m ON f.food_id = m.food_id JOIN restaurants r ON m.restaurant_id = r.restaurant_id WHERE r.user_id = {user_id}",
                'orders': f"SELECT COUNT(*) AS count FROM orders WHERE restaurant_id = {restaurant_id} AND order_status != 'awaiting_payment'",
                'couriers': f"SELECT COUNT(*) AS count FROM couriers WHERE restaurant_id = {restaurant_id}",
                'waiters': f"SELECT COUNT(*) AS count FROM waiters WHERE restaurant_id = {restaurant_id}",
            }
            
        for key, query in queries.items():
            cursor.execute(query)
            result = cursor.fetchone()
            statistics[key] = result['count'] if result and 'count' in result else 0
            
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    # recent_orders HTML'e gönderiliyor
    return render_template('index.html', role=role, statistics=statistics, recent_orders=recent_orders)