from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error

def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    role = session.get('role')

    if role == 'customer':
        connection = get_db_connection()
        restaurants = []
        if connection:
            cursor = connection.cursor(dictionary=True)
            # Şimdilik tüm restoranları çekiyoruz. İleride buraya "WHERE city = session['customer_city']" gibi konum filtreleri ekleyeceğiz.
            cursor.execute("SELECT * FROM restaurants")
            restaurants = cursor.fetchall()
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
