from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
from datetime import date

def waiters():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    if role not in ['admin', 'user']:
        return redirect(url_for('index'))

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return render_template('waiters.html', waiters=[])

    try:
        cursor = connection.cursor(dictionary=True, buffered=True)
        
        if 'filtered_waiters' in session:
            waiters = session['filtered_waiters']
        else:
            if role == 'admin':
                cursor.execute('SELECT * FROM waiters')
            elif role == 'user' and restaurant_id:
                cursor.execute('SELECT * FROM waiters WHERE restaurant_id = %s', (restaurant_id,))
            waiters = cursor.fetchall()
            
    except Error as e:
        flash(f"Query failed: {e}", "danger")
        waiters = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('waiters.html', waiters=waiters)

def waiter_action():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    if role not in ['admin', 'user']:
        return redirect(url_for('index'))

    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('waiters'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            name = request.form.get('name')
            restaurant_id = request.form.get('restaurant_id')           
            default_password = "12345"

            if role == 'user' and str(restaurant_id) != str(restaurant_id_session):
                flash("Unauthorized action! You can only add waiters for your restaurant.", "danger")
                return redirect(url_for('waiters'))

            if not name or not restaurant_id:
                flash("Name and Restaurant ID are required.", "warning")
                return redirect(url_for('waiters'))

            cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            if cursor.fetchone()['count'] == 0:
                flash('No restaurant found with that Restaurant ID!', 'danger')
                return redirect(url_for('waiters'))

            clean_name = name.replace(" ", "").lower()
            generated_email = f"{clean_name}@{restaurant_id}.com"

            query = 'INSERT INTO waiters (name, email, password, restaurant_id) VALUES (%s, %s, %s, %s)'
            cursor.execute(query, (name, generated_email, default_password, restaurant_id))
            
            new_id = cursor.lastrowid
            connection.commit()
            flash(f"Waiter added successfully! Assigned ID: {new_id}, Login: {generated_email}, Pass: {default_password}", "success")

        elif action == 'delete':
            selected_ids = request.form.get('selected_waiters')
            if not selected_ids:
                flash("No waiter(s) selected for deletion.", "warning")
                return redirect(url_for('waiters'))

            selected_ids = selected_ids.split(',')

            if role == 'user':
                query = "DELETE FROM waiters WHERE waiter_id IN ({}) AND restaurant_id = %s".format(','.join(['%s'] * len(selected_ids)))
                cursor.execute(query, selected_ids + [restaurant_id_session])
            else:
                query = "DELETE FROM waiters WHERE waiter_id IN (%s)" % ','.join(['%s'] * len(selected_ids))
                cursor.execute(query, selected_ids)

            connection.commit()
            flash(f"Successfully deleted {cursor.rowcount} waiter(s).", "success")

        elif action == 'update':
            update_waiter_id = request.form.get('update_waiter_id')
            new_waiter_id = request.form.get('waiter_id')
            name = request.form.get('name')
            restaurant_id = request.form.get('restaurant_id')

            if not update_waiter_id:
                flash("No waiter selected for update.", "warning")
                return redirect(url_for('waiters'))
            
            if role == 'user' and (restaurant_id != str(restaurant_id_session) or new_waiter_id != update_waiter_id):
                flash("Unauthorized action! You cannot change your Waiter's ID or Restaurant ID.", "danger")
                return redirect(url_for('waiters'))

            if new_waiter_id and new_waiter_id != update_waiter_id:
                cursor.execute("SELECT waiter_id FROM waiters WHERE waiter_id = %s", (new_waiter_id,))
                if cursor.fetchone():
                    flash("The new Waiter ID is already in use.", "warning")
                    return redirect(url_for('waiters'))
            
            target_id = new_waiter_id if new_waiter_id else update_waiter_id

            query = "UPDATE waiters SET waiter_id = %s, name = %s, restaurant_id = %s WHERE waiter_id = %s"
            cursor.execute(query, (target_id, name, restaurant_id, update_waiter_id))
            
            connection.commit()
            flash("Waiter updated successfully!", "success")

        elif action == 'filter':
            waiter_id = request.form.get('waiter_id')
            name = request.form.get('name')
            restaurant_id = request.form.get('restaurant_id')

            if not any([waiter_id, name, restaurant_id]):
                 flash("Please provide at least one filter criteria.", "warning")
                 return redirect(url_for('waiters'))

            query = "SELECT * FROM waiters WHERE 1=1"
            params = []
            
            if role == 'user':
                query += " AND restaurant_id = %s"
                params.append(restaurant_id_session)

            if waiter_id:
                query += " AND waiter_id = %s"
                params.append(waiter_id)
            if name:
                query += " AND name LIKE %s" 
                params.append(f"%{name}%")
            
            if restaurant_id:
                if role == 'admin' or (role == 'user' and str(restaurant_id) == str(restaurant_id_session)):
                    query += " AND restaurant_id = %s"
                    params.append(restaurant_id)

            cursor.execute(query, params)
            waiters = cursor.fetchall()
            session['filtered_waiters'] = waiters
            flash(f"Found {len(waiters)} waiter(s) matching the criteria(s).", "success")
            return render_template('waiters.html', waiters=waiters)

        elif action == 'clear':
            if 'filtered_waiters' in session:
                session.pop('filtered_waiters', None)
            
            query = "SELECT * FROM waiters"
            params = []
            if role == 'user':
                query += " WHERE restaurant_id = %s"
                params.append(restaurant_id_session)
            
            cursor.execute(query, params)
            waiters = cursor.fetchall()

            flash("All filters, sorting, and selections have been cleared.", "success")
            return render_template('waiters.html', waiters=waiters)

        elif action == 'sort':
            sort_by = request.form.get('sort_by')
            sort_order = request.form.get('sort_order')
            
            if not sort_by or sort_order not in ['ASC', 'DESC']:
                flash("Invalid sort parameters.", "danger")
                return redirect(url_for('waiters'))

            if 'filtered_waiters' in session and session['filtered_waiters']:
                filtered_ids = [w['waiter_id'] for w in session['filtered_waiters']]
                if filtered_ids:
                    query = f"SELECT * FROM waiters WHERE waiter_id IN ({','.join(['%s'] * len(filtered_ids))}) ORDER BY {sort_by} {sort_order}"
                    cursor.execute(query, tuple(filtered_ids))
                    waiters = cursor.fetchall()
                    flash("Filtered waiters sorted successfully!", "success")
                else:
                    waiters = []
            else:
                query = "SELECT * FROM waiters WHERE 1=1"
                params = []
                if role == 'user':
                    query += " AND restaurant_id = %s"
                    params.append(restaurant_id_session)
                
                query += f" ORDER BY {sort_by} {sort_order}"
                cursor.execute(query, params)
                waiters = cursor.fetchall()
                flash("Waiters sorted successfully!", "success")
            
            return render_template('waiters.html', waiters=waiters)

    except Error as e:
        flash(f"An error occurred: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('waiters'))

def waiter_dashboard():
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return render_template('waiter_dashboard.html', menus=[])

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT table_count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        res_info = cursor.fetchone()
        
        if res_info and res_info['table_count']:
            total_tables = res_info['table_count']
        else:
            total_tables = 0

        cursor.execute('''
            SELECT m.menu_id, m.price, m.stock_quantity, f.item_name, f.veg_or_non_veg, m.cuisine 
            FROM menus m 
            JOIN foods f ON m.food_id = f.food_id 
            WHERE m.restaurant_id = %s
        ''', (restaurant_id,))
        menus = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT table_no 
            FROM orders 
            WHERE restaurant_id = %s AND order_status = 'pending'
        ''', (restaurant_id,))
        occupied_tables = [row['table_no'] for row in cursor.fetchall()]
        
        return render_template('waiter_dashboard.html', menus=menus, total_tables=total_tables, occupied_tables=occupied_tables)
    except Error as e:
        flash(f"Query failed: {e}", "danger")
        return render_template('waiter_dashboard.html', menus=[], total_tables=0, occupied_tables=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def waiter_create_order():
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    selected_menus = request.form.getlist('selected_items')
    table_no = request.form.get('table_no')
    
    if not selected_menus:
        flash("No items selected!", "warning")
        return redirect(url_for('waiter_dashboard'))
    
    if not table_no:
        flash("Please enter a table number!", "danger")
        return redirect(url_for('waiter_dashboard'))

    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('waiter_dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT table_count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        res_info = cursor.fetchone()
        
        if res_info and res_info['table_count']:
            max_limit = res_info['table_count']
            if int(table_no) > max_limit:
                flash(f"Invalid Table Number! This restaurant only has {max_limit} tables.", "warning")
                cursor.close()
                connection.close()
                return redirect(url_for('waiter_dashboard'))
        
        total_qty = 0
        total_amount = 0

        order_details = [] 

        for menu_id in selected_menus:
            qty = int(request.form.get(f'qty_{menu_id}', 0))
            if qty > 0:
                cursor.execute('SELECT price, food_id, stock_quantity FROM menus WHERE menu_id = %s', (menu_id,))
                result = cursor.fetchone()
                
                if result:
                    if result['stock_quantity'] < qty:
                        flash(f"ERROR: Insufficient stock! Some items are out of stock.", "danger")
                        connection.close()
                        return redirect(url_for('waiter_dashboard'))
                    
                    total_qty += qty

                    unit_price = float(result['price']) 
                    
                    item_total = unit_price * qty
                    total_amount += item_total
                    
                    order_details.append({
                        'food_id': result['food_id'],
                        'quantity': qty,
                        'price': unit_price  
                    })

        if total_qty > 0:
            cursor.execute("""
                SELECT order_id, sales_amount, sales_qty 
                FROM orders 
                WHERE restaurant_id = %s AND table_no = %s AND order_status = 'pending'
            """, (restaurant_id, table_no))
            
            existing_order = cursor.fetchone()

            if existing_order:
                order_id = existing_order['order_id']
                
                new_sales_qty = float(existing_order['sales_qty']) + total_qty
                new_sales_amount = float(existing_order['sales_amount']) + total_amount
                
                cursor.execute("""
                    UPDATE orders 
                    SET sales_amount = %s, sales_qty = %s, order_date = %s
                    WHERE order_id = %s
                """, (new_sales_amount, new_sales_qty, date.today(), order_id))
                
                flash(f"Items added to existing Order #{order_id} for Table {table_no}", "info")
            else:
                query = 'INSERT INTO orders (order_date, sales_qty, sales_amount, restaurant_id, order_status, table_no) VALUES (%s, %s, %s, %s, %s, %s)'
                cursor.execute(query, (date.today(), total_qty, total_amount, restaurant_id, 'pending', table_no))
                
                order_id = cursor.lastrowid
                flash(f"New Order #{order_id} created for Table {table_no}", "success")
            
            for item in order_details:
                food_id = item['food_id']
                qty = item['quantity']
                price = item['price']

                cursor.execute("""
                    SELECT item_id, quantity 
                    FROM order_items 
                    WHERE order_id = %s AND food_id = %s
                """, (order_id, food_id))
                
                existing_item = cursor.fetchone()

                if existing_item:
                    new_item_qty = existing_item['quantity'] + qty
                    cursor.execute("""
                        UPDATE order_items 
                        SET quantity = %s 
                        WHERE item_id = %s
                    """, (new_item_qty, existing_item['item_id']))
                    
                else:
                    cursor.execute("""
                        INSERT INTO order_items (order_id, food_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (order_id, food_id, qty, price))
            
            for item in order_details:
                cursor.execute("""
                    UPDATE menus 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE food_id = %s
                """, (item['quantity'], item['food_id']))
            
            connection.commit()
        else:
            flash("Invalid quantity selected.", "warning")

    except Error as e:
        flash(f"Error creating order: {e}", "danger")
        connection.rollback() 
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('waiter_dashboard'))

def waiter_close_bill():
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    table_no = request.form.get('table_no')
    
    if not table_no:
        flash("Lütfen hesabı kapatılacak masa numarasını seçin veya girin!", "danger")
        return redirect(url_for('waiter_dashboard'))

    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('waiter_dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)

        # Aktif adisyonu bul
        cursor.execute("""
            SELECT order_id FROM orders 
            WHERE restaurant_id = %s AND table_no = %s AND order_status = 'pending'
        """, (restaurant_id, table_no))
        order = cursor.fetchone()

        if order:
            order_id = order['order_id']
            
            # Durumu tamamlandı yap
            cursor.execute("""
                UPDATE orders 
                SET order_status = 'completed' 
                WHERE order_id = %s
            """, (order_id,))
            
            connection.commit()
            
            # DEĞİŞİKLİK: Dashboard'a dönmek yerine doğrudan adisyon sayfasına yönlendiriyoruz!
            flash(f"💳 Masa {table_no} hesabı kapatıldı. Adisyon hazırlanıyor...", "success")
            return redirect(url_for('waiter_receipt', order_id=order_id))
        else:
            flash(f"Masa {table_no} zaten boş veya aktif bir adisyonu bulunmuyor.", "warning")
            return redirect(url_for('waiter_dashboard'))

    except Error as e:
        flash(f"Hesap kapatılırken bir hata oluştu: {e}", "danger")
        connection.rollback()
        return redirect(url_for('waiter_dashboard'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# YENİ FONKSİYON: Adisyon Fişi Verilerini Getirir
def waiter_receipt(order_id):
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('waiter_dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        
        # 1. Restoran Bilgisi
        cursor.execute("SELECT restaurant_name, restaurant_address FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        restaurant = cursor.fetchone()

        # 2. Sipariş Ana Bilgileri
        cursor.execute("""
            SELECT order_id, order_date, sales_amount, table_no 
            FROM orders 
            WHERE order_id = %s AND restaurant_id = %s
        """, (order_id, restaurant_id))
        order = cursor.fetchone()

        if not order:
            flash("Adisyon bulunamadı!", "danger")
            return redirect(url_for('waiter_dashboard'))

        # 3. Sipariş Edilen Yemekler (Kalemler)
        cursor.execute("""
            SELECT f.item_name, oi.quantity, oi.unit_price 
            FROM order_items oi
            JOIN foods f ON oi.food_id = f.food_id
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()

        return render_template('receipt.html', order=order, items=items, restaurant=restaurant)

    except Error as e:
        flash(f"Adisyon yüklenirken hata: {e}", "danger")
        return redirect(url_for('waiter_dashboard'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()