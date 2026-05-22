from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error

def orders():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return render_template('orders.html', orders=[])

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute('SELECT * FROM orders')
            orders = cursor.fetchall()
            cursor.execute('SELECT * FROM couriers')
            couriers = cursor.fetchall()
            foods = []
        elif role == 'user' and restaurant_id:
            cursor.execute('SELECT * FROM orders WHERE restaurant_id = %s', (restaurant_id,))
            orders = cursor.fetchall()
            cursor.execute('SELECT * FROM couriers WHERE restaurant_id = %s', (restaurant_id,))
            couriers = cursor.fetchall()
            query_foods = """
                SELECT f.food_id, f.item_name, m.price 
                FROM menus m 
                JOIN foods f ON m.food_id = f.food_id 
                WHERE m.restaurant_id = %s
            """
            cursor.execute(query_foods, (restaurant_id,))
            foods = cursor.fetchall()
        else:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('index'))
    except Error as e:
        flash(f"Query failed: {e}", "danger")
        orders = []
        couriers = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('orders.html', orders=orders, couriers=couriers, foods=foods)
    
def order_action():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return redirect(url_for('orders'))

    try:
        cursor = connection.cursor(dictionary=True, buffered=True)

        if action == 'add':
            order_type = request.form.get('order_type')

            if not order_type:
                flash("Please select an Order Type (Dine-in or Delivery)!", "warning")
                return redirect(url_for('orders'))
            
            if order_type == 'Dine-in':
                flash("You cannot add Dine-in orders manually! Please use the Waiter system.", "danger")
                return redirect(url_for('orders'))

            order_id = request.form.get('order_id')

            if role == 'user':
                restaurant_id = restaurant_id_session 
            else:
                restaurant_id = request.form.get('restaurant_id')

            customer_name = request.form.get('customer_name')
            customer_phone = request.form.get('customer_phone')
            customer_address = request.form.get('customer_address')
            courier_id = request.form.get('courier_id') or None

            food_ids = request.form.getlist('food_id')    
            quantities = request.form.getlist('quantity') 
            
            valid_items = []
            total_qty = 0
            total_amount = 0

            for i in range(len(food_ids)):
                f_id = food_ids[i]
                qty_str = quantities[i]
                
                if f_id and qty_str:
                    try:
                        qty = int(qty_str)
                        if qty > 0:
                            cursor.execute("SELECT price, stock_quantity FROM menus WHERE food_id = %s", (f_id,))
                            menu_item = cursor.fetchone()
                            if menu_item:
                                current_stock = menu_item['stock_quantity']
                                if current_stock < qty:
                                    flash(f"ERROR: Insufficient stock for item ID {f_id}! (Available: {current_stock})", "danger")
                                    connection.close()
                                    return redirect(url_for('orders'))
                                
                                price = menu_item['price']
                                item_total = price * qty
                                total_amount += item_total
                                total_qty += qty
                                
                                valid_items.append({
                                    'food_id': f_id,
                                    'quantity': qty,
                                    'unit_price': price
                                })
                    except (ValueError, TypeError):
                        continue 

            if not restaurant_id:
                flash("Restaurant ID is required.", "warning")
                return redirect(url_for('orders'))
            
            cursor.execute("SELECT COUNT(*) FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            if cursor.fetchone()['COUNT(*)'] == 0:
                flash('No restaurant found with that Restaurant ID!', 'danger')
                return redirect(url_for('orders'))

            if order_type == 'Delivery':
                 if not customer_name or not customer_phone or not customer_address:
                     flash("Customer details are required for Delivery!", "warning")
                     return redirect(url_for('orders'))
                 if not valid_items: 
                     flash("Please add at least one food item!", "warning")
                     return redirect(url_for('orders'))

            order_status = request.form.get('order_status') or 'Pending'

            if order_id:
                cursor.execute("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
                if cursor.fetchone():
                    cursor.execute("SELECT order_id FROM orders")
                    used_ids = {row['order_id'] for row in cursor.fetchall()}
                    all_possible_ids = set(range(1, 1001))
                    unused_ids = all_possible_ids - used_ids
                    suggestions = ', '.join(map(str, sorted(unused_ids)[:3]))
                    flash(f"The Order ID {order_id} is already in use. Suggestions: {suggestions}", "warning")
                    return redirect(url_for('orders'))

                query = """
                    INSERT INTO orders 
                    (order_id, restaurant_id, order_date, order_status, sales_qty, sales_amount, 
                     order_type, table_no, customer_name, customer_phone, customer_address, courier_id)
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (order_id, restaurant_id, order_status, total_qty, total_amount, 
                                       order_type, None, customer_name, customer_phone, customer_address, courier_id))
                final_order_id = order_id
            else:
                query = """
                    INSERT INTO orders 
                    (restaurant_id, order_date, order_status, sales_qty, sales_amount, 
                     order_type, table_no, customer_name, customer_phone, customer_address, courier_id)
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (restaurant_id, order_status, total_qty, total_amount, 
                                       order_type, None, customer_name, customer_phone, customer_address, courier_id))
                final_order_id = cursor.lastrowid

            for item in valid_items:
                item_query = "INSERT INTO order_items (order_id, food_id, quantity, unit_price) VALUES (%s, %s, %s, %s)"
                cursor.execute(item_query, (final_order_id, item['food_id'], item['quantity'], item['unit_price']))

            for item in valid_items:
                cursor.execute("""
                    UPDATE menus 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE food_id = %s
                """, (item['quantity'], item['food_id']))

            connection.commit()
            flash(f"Order added successfully! Total: ${total_amount} (ID: {final_order_id})", "success")
            return redirect(url_for('orders'))

        elif action == 'delete':
            selected_ids = request.form.get('selected_orders')
            if not selected_ids:
                flash("No order(s) selected for deletion.", "warning")
                return redirect(url_for('orders'))

            selected_ids = selected_ids.split(',')

            for o_id in selected_ids:
                cursor.execute("SELECT food_id, quantity FROM order_items WHERE order_id = %s", (o_id,))
                items_to_return = cursor.fetchall()

                for item in items_to_return:
                    cursor.execute("""
                        UPDATE menus 
                        SET stock_quantity = stock_quantity + %s 
                        WHERE food_id = %s
                    """, (item['quantity'], item['food_id']))

            if role == 'user':
                query = "DELETE FROM orders WHERE order_id IN ({}) AND restaurant_id = %s".format(','.join(['%s'] * len(selected_ids)))
                cursor.execute(query, selected_ids + [restaurant_id_session])
            else:
                query = "DELETE FROM orders WHERE order_id IN (%s)" % ','.join(['%s'] * len(selected_ids))
                cursor.execute(query, selected_ids)

            connection.commit()
            flash(f"Successfully deleted {cursor.rowcount} order(s).", "success")

        elif action == 'update':
            update_order_id = request.form.get('update_order_id')
            new_order_id = request.form.get('order_id')         
            if role == 'user':
                restaurant_id = restaurant_id_session
            else:
                restaurant_id = request.form.get('restaurant_id')
            order_status = request.form.get('order_status')     
            order_type = request.form.get('order_type')
            table_no = request.form.get('table_no')

            if order_type == 'Delivery':
                table_no = None  
            else:
                table_no = table_no if table_no else None

            customer_name = request.form.get('customer_name')
            customer_phone = request.form.get('customer_phone')
            customer_address = request.form.get('customer_address')
            courier_id = request.form.get('courier_id')
            
            food_ids = request.form.getlist('food_id')    
            quantities = request.form.getlist('quantity') 

            valid_items = []
            total_qty = 0
            total_amount = 0
            
            if food_ids and any(f for f in food_ids):
                for i in range(len(food_ids)):
                    f_id = food_ids[i]
                    qty_str = quantities[i]
                    
                    if f_id and qty_str:
                        try:
                            qty = int(qty_str)
                            if qty > 0:
                                cursor.execute("SELECT price FROM menus WHERE food_id = %s", (f_id,))
                                price_res = cursor.fetchone()
                                if price_res:
                                    price = float(price_res['price'])
                                    item_total = price * qty
                                    
                                    total_qty += qty
                                    total_amount += item_total
                                    
                                    valid_items.append({
                                        'food_id': f_id,
                                        'quantity': qty,
                                        'unit_price': price
                                    })
                        except (ValueError, TypeError):
                            continue
            else:
                if order_type == 'Delivery':
                    pass
                else:
                    total_qty = request.form.get('sales_qty')
                    total_amount = request.form.get('sales_amount')


            if not table_no: table_no = None
            if not courier_id: courier_id = None

            if not update_order_id:
                flash("No order selected for update.", "warning")
                return redirect(url_for('orders'))

            if role == 'user' and str(new_order_id) != str(update_order_id):
                flash("Unauthorized action! You cannot change your Order's ID.", "danger")
                return redirect(url_for('orders'))
            
            if new_order_id != update_order_id:
                cursor.execute("SELECT COUNT(*) AS count FROM orders WHERE order_id = %s", (new_order_id,))
                result = cursor.fetchone()
                if result['count'] > 0:
                     flash(f"The new Order ID is already in use.", "warning")
                     return redirect(url_for('orders'))

            query = """
                UPDATE orders 
                SET order_id = %s, sales_qty = %s, sales_amount = %s, 
                    restaurant_id = %s, order_status = %s,
                    order_type = %s, table_no = %s, 
                    customer_name = %s, customer_phone = %s, customer_address = %s, courier_id = %s
                WHERE order_id = %s
            """
            cursor.execute(query, (new_order_id, total_qty, total_amount, 
                                   restaurant_id, order_status,
                                   order_type, table_no, 
                                   customer_name, customer_phone, customer_address, courier_id,
                                   update_order_id))
            
            if order_type == 'Delivery' and valid_items:
                cursor.execute("DELETE FROM order_items WHERE order_id = %s", (new_order_id,))
                
                for item in valid_items:
                    item_query = "INSERT INTO order_items (order_id, food_id, quantity, unit_price) VALUES (%s, %s, %s, %s)"
                    cursor.execute(item_query, (new_order_id, item['food_id'], item['quantity'], item['unit_price']))

            connection.commit()
            flash("Order updated successfully!", "success")

        elif action == 'filter':
            order_id = request.form.get('order_id')
            order_date = request.form.get('order_date')
            sales_qty = request.form.get('sales_qty')
            sales_amount = request.form.get('sales_amount')
            restaurant_id = request.form.get('restaurant_id')
            order_status = request.form.get('order_status')
            table_no = request.form.get('table_no')
            order_type = request.form.get('order_type')
            customer_name = request.form.get('customer_name')
            customer_phone = request.form.get('customer_phone')
            courier_id = request.form.get('courier_id')

            if not any([order_id, order_date, sales_qty, sales_amount, restaurant_id, 
                        order_status, table_no, order_type, customer_name, customer_phone, courier_id]):
                flash("Please provide at least one filter criteria.", "warning")
                return redirect(url_for('orders'))

            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            
            if role == 'user':
                query += " AND restaurant_id = %s"
                params.append(restaurant_id_session)

            if order_id:
                query += " AND order_id = %s"
                params.append(order_id)
            
            if order_date:
                query += " AND order_date LIKE %s"
                params.append(f"%{order_date}%")
            
            if sales_qty:
                query += " AND sales_qty = %s"
                params.append(sales_qty)
            
            if sales_amount:
                query += " AND sales_amount = %s"
                params.append(sales_amount)
            
            if restaurant_id:
                if role == 'admin':
                     query += " AND restaurant_id = %s"
                     params.append(restaurant_id)

            if order_status:
                query += " AND order_status = %s"
                params.append(order_status)
            
            if table_no:
                query += " AND table_no = %s"
                params.append(table_no)

            if order_type:
                query += " AND order_type = %s"
                params.append(order_type)
            
            if customer_name:
                query += " AND customer_name LIKE %s"
                params.append(f"%{customer_name}%")
            
            if customer_phone:
                query += " AND customer_phone LIKE %s"
                params.append(f"%{customer_phone}%")
            
            if courier_id:
                query += " AND courier_id = %s"
                params.append(courier_id)

            cursor.execute(query, params)
            orders = cursor.fetchall()
            
            session['filtered_orders'] = orders
            flash(f"Found {len(orders)} order(s) matching the criteria(s).", "success")

            if role == 'user':
                cursor.execute('SELECT * FROM couriers WHERE restaurant_id = %s', (restaurant_id_session,))
                couriers = cursor.fetchall()

                query_foods = """
                    SELECT f.food_id, f.item_name, m.price 
                    FROM menus m 
                    JOIN foods f ON m.food_id = f.food_id 
                    WHERE m.restaurant_id = %s
                """
                cursor.execute(query_foods, (restaurant_id_session,))
                foods = cursor.fetchall()
            else:
                cursor.execute("SELECT * FROM couriers")
                couriers = cursor.fetchall()
                cursor.execute("SELECT * FROM foods") 
                foods = cursor.fetchall()

            return render_template('orders.html', orders=orders, foods=foods, couriers=couriers)

        elif action == 'sort':
            sort_by = request.form.get('sort_by')
            sort_order = request.form.get('sort_order')

            if not sort_by or sort_order not in ['ASC', 'DESC']:
                flash("Invalid sort parameters.", "danger")
                return redirect(url_for('orders'))

            if 'filtered_orders' in session and session['filtered_orders']:
                filtered_ids = [order['order_id'] for order in session['filtered_orders']]

                query = f"SELECT * FROM orders WHERE order_id IN ({','.join(['%s'] * len(filtered_ids))}) ORDER BY {sort_by} {sort_order}"
                cursor.execute(query, filtered_ids)
                orders = cursor.fetchall()

                flash("Filtered orders sorted successfully!", "success")
            else:
                query = "SELECT * FROM orders WHERE 1=1"
                params = []
                if role == 'user':
                    query += " AND restaurant_id = %s"
                    params.append(restaurant_id_session)

                query += f" ORDER BY {sort_by} {sort_order}"
                cursor.execute(query, params)
                orders = cursor.fetchall()
                flash("Orders sorted successfully!", "success")

            return render_template('orders.html', orders=orders)

        elif action == 'clear':
            if 'filtered_orders' in session:
                session.pop('filtered_orders', None)

            flash("All filters, sorting, and selections have been cleared.", "success")
            return redirect(url_for('orders'))
    except Error as e:
        flash(f"An error occurred: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('orders'))

def get_order_details(order_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT f.food_id, f.item_name, oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) as subtotal
        FROM order_items oi
        JOIN foods f ON oi.food_id = f.food_id
        WHERE oi.order_id = %s
    """
    cursor.execute(query, (order_id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(items)

def get_restaurant_details(restaurant_id):
    if 'logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT f.food_id, f.item_name, m.price, m.stock_quantity 
            FROM menus m 
            JOIN foods f ON m.food_id = f.food_id 
            WHERE m.restaurant_id = %s AND m.stock_quantity > 0
        """, (restaurant_id,))
        foods = cursor.fetchall()
        
        cursor.execute("""
            SELECT courier_id, name 
            FROM couriers 
            WHERE restaurant_id = %s
        """, (restaurant_id,))
        couriers = cursor.fetchall()
        
        return jsonify({'foods': foods, 'couriers': couriers})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def api_check_new_orders():
    # Sadece giriş yapmış yetkili kişiler (admin veya restoran sahibi) burayı sorgulayabilir
    if 'logged_in' not in session:
        return jsonify({'new_orders': False})
        
    role = session.get('role')
    if role not in ['admin', 'user']:
        return jsonify({'new_orders': False})
        
    # HTML'den gelen, ekrandaki en son (en büyük) sipariş ID'sini al
    client_max_id = request.args.get('last_id', 0, type=int)
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Rolüne göre veritabanındaki en son siparişin ID'sini bul
            if role == 'user':
                restaurant_id = session.get('restaurant_id')
                if not restaurant_id:
                    return jsonify({'new_orders': False})
                cursor.execute("SELECT MAX(order_id) as max_id FROM orders WHERE restaurant_id = %s", (restaurant_id,))
            else: # admin
                cursor.execute("SELECT MAX(order_id) as max_id FROM orders")
                
            result = cursor.fetchone()
            db_max_id = result['max_id'] if result and result['max_id'] else 0
            
            # Eğer veritabanındaki son ID, ekrandaki son ID'den büyükse YENİ SİPARİŞ VARDIR!
            if db_max_id > client_max_id:
                return jsonify({'new_orders': True})
                
        except Exception as e:
            print(f"Sipariş API kontrol hatası: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return jsonify({'new_orders': False})