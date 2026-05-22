from flask import render_template, request, redirect, url_for, session, flash
import math
from db import get_db_connection
from mysql.connector import Error

def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine Formülü (İki koordinat arası km hesabı)
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    role = session.get('role')

    if role == 'customer':
        # 1. Formdan gelen arama parametrelerini yakala
        search_query = request.args.get('search', '').strip()
        min_rating = request.args.get('min_rating', '0')
        
        connection = get_db_connection()
        restaurants = []
        
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # 2. Akıllı SQL Sorgusu Hazırlığı
                sql_query = "SELECT * FROM restaurants WHERE 1=1"
                query_params = []

                # Kelime araması (İsim veya Mutfak türü)
                if search_query:
                    sql_query += " AND (restaurant_name LIKE %s OR cuisine LIKE %s)"
                    like_pattern = f"%{search_query}%"
                    query_params.extend([like_pattern, like_pattern])

                # Puan filtresi
                if min_rating and float(min_rating) > 0:
                    sql_query += " AND rating >= %s"
                    query_params.append(float(min_rating))

                # 3. Sorguyu çalıştır ve filtrelenmiş verileri al
                cursor.execute(sql_query, tuple(query_params))
                all_restaurants = cursor.fetchall()
                
                # 4. MEVCUT SİSTEMİN: Mesafe Hesaplama ve Sıralama
                customer_lat = session.get('latitude')
                customer_lon = session.get('longitude')

                if customer_lat and customer_lon:
                    for r in all_restaurants:
                        if r['latitude'] and r['longitude']:
                            dist = calculate_distance(float(customer_lat), float(customer_lon), float(r['latitude']), float(r['longitude']))
                            r['distance'] = round(dist, 1) # Virgülden sonra 1 basamak (Örn: 2.4 km)
                        else:
                            r['distance'] = 999 # Restoranın konumu girilmediyse en sona at

                    # Restoranları mesafeye göre yakından uzağa sırala
                    all_restaurants.sort(key=lambda x: x.get('distance', 999))
                else:
                    # Müşteri konum izni vermediyse veya lokasyon yoksa, varsayılan olarak puana göre sırala
                    all_restaurants.sort(key=lambda x: float(x.get('rating', 0) or 0), reverse=True)

                restaurants = all_restaurants

            except Exception as e:
                print(f"Restoranlar yüklenirken bir hata oluştu: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return render_template('customer_index.html', restaurants=restaurants)

    if role == 'waiter':
        return redirect(url_for('waiter_dashboard'))

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return render_template('index.html', statistics=[])

    statistics = {
        'users': 0,
        'restaurants': 0,
        'menus': 0,
        'foods': 0,
        'orders': 0,
        'couriers': 0,
        'waiters': 0
    }

    try:
        cursor = connection.cursor(dictionary=True)

        if role == 'admin':
            queries = {
                'users': "SELECT COUNT(*) AS count FROM users",
                'restaurants': "SELECT COUNT(*) AS count FROM restaurants",
                'menus': "SELECT COUNT(*) AS count FROM menus",
                'foods': "SELECT COUNT(*) AS count FROM foods",
                'orders': "SELECT COUNT(*) AS count FROM orders",
                'couriers': "SELECT COUNT(*) AS count FROM couriers",
                'waiters': "SELECT COUNT(*) AS count FROM waiters"
            }
        elif role == 'user':
            user_id = session.get('user_id')
            restaurant_id = session.get('restaurant_id')

            queries = {
                'menus': f"SELECT COUNT(*) AS count FROM menus WHERE restaurant_id = {restaurant_id}",
                'foods': f"""
                    SELECT COUNT(DISTINCT f.food_id) AS count
                    FROM foods f
                    JOIN menus m ON f.food_id = m.food_id
                    JOIN restaurants r ON m.restaurant_id = r.restaurant_id
                    WHERE r.user_id = {user_id}
                """,
                'orders': f"SELECT COUNT(*) AS count FROM orders WHERE restaurant_id = {restaurant_id}",
                'couriers': f"SELECT COUNT(*) AS count FROM couriers WHERE restaurant_id = {restaurant_id}",
                'waiters': f"SELECT COUNT(*) AS count FROM waiters WHERE restaurant_id = {restaurant_id}",
            }
        
        for key, query in queries.items():
            cursor.execute(query)
            result = cursor.fetchone()
            statistics[key] = result['count'] if result and 'count' in result else 0
            
    except Error as e:
        flash(f"Query failed: {e}", "danger")
    except UnboundLocalError:
        pass
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('index.html', role=role, statistics=statistics)
