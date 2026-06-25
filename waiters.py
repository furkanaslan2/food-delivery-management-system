from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error
from werkzeug.security import generate_password_hash
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
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('waiters.html', waiters=[])

    try:
        cursor = connection.cursor(dictionary=True)
        
        if role == 'admin':
            cursor.execute('''
                SELECT w.*, r.restaurant_name 
                FROM waiters w
                LEFT JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                ORDER BY w.waiter_id DESC
            ''')
            waiters = cursor.fetchall()
        elif role == 'user' and restaurant_id:
            cursor.execute('SELECT * FROM waiters WHERE restaurant_id = %s ORDER BY waiter_id DESC', (restaurant_id,))
            waiters = cursor.fetchall()
            
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
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
            email = request.form.get('email')
            password = request.form.get('password')
            restaurant_id = request.form.get('restaurant_id') if role == 'admin' else restaurant_id_session           

            if not all([name, email, password, restaurant_id]):
                flash("Lütfen tüm alanları doldurun.", "warning")
                return redirect(url_for('waiters'))

            hashed_password = generate_password_hash(password)

            cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            if cursor.fetchone()['count'] == 0:
                flash('Geçersiz Restoran ID!', 'danger')
                return redirect(url_for('waiters'))

            query = 'INSERT INTO waiters (name, email, password, restaurant_id) VALUES (%s, %s, %s, %s)'
            cursor.execute(query, (name, email, hashed_password, restaurant_id))
            
            connection.commit()
            flash("Garson başarıyla eklendi!", "success")

        elif action == 'delete':
            selected_ids = request.form.get('selected_waiters')
            if not selected_ids:
                flash("Silinecek garson seçilmedi.", "warning")
                return redirect(url_for('waiters'))

            ids_list = selected_ids.split(',')

            if role == 'user':
                format_strings = ','.join(['%s'] * len(ids_list))
                query = f"DELETE FROM waiters WHERE waiter_id IN ({format_strings}) AND restaurant_id = %s"
                cursor.execute(query, ids_list + [restaurant_id_session])
            else:
                format_strings = ','.join(['%s'] * len(ids_list))
                query = f"DELETE FROM waiters WHERE waiter_id IN ({format_strings})"
                cursor.execute(query, ids_list)

            connection.commit()
            flash(f"{cursor.rowcount} garson başarıyla silindi.", "success")

        elif action == 'update':
            update_waiter_id = request.form.get('update_waiter_id')
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            restaurant_id = request.form.get('restaurant_id') if role == 'admin' else restaurant_id_session

            if not update_waiter_id:
                flash("Güncellenecek garson seçilmedi.", "warning")
                return redirect(url_for('waiters'))
            
            if not all([name, email]):
                flash("Lütfen ad ve email alanlarını doldurun.", "warning")
                return redirect(url_for('waiters'))

            if password:
                hashed_password = generate_password_hash(password)
                query = "UPDATE waiters SET name = %s, email = %s, password = %s WHERE waiter_id = %s AND restaurant_id = %s"
                cursor.execute(query, (name, email, hashed_password, update_waiter_id, restaurant_id))
            else:
                query = "UPDATE waiters SET name = %s, email = %s WHERE waiter_id = %s AND restaurant_id = %s"
                cursor.execute(query, (name, email, update_waiter_id, restaurant_id))
            
            connection.commit()
            flash("Garson başarıyla güncellendi!", "success")

        elif action == 'filter':
            name = request.form.get('name')

            query = """
                SELECT w.*, r.restaurant_name 
                FROM waiters w
                LEFT JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                WHERE 1=1
            """
            params = []
            
            if role == 'user':
                query += " AND w.restaurant_id = %s"
                params.append(restaurant_id_session)

            if name:
                query += " AND w.name LIKE %s" 
                params.append(f"%{name}%")
            
            query += " ORDER BY w.waiter_id DESC"

            cursor.execute(query, params)
            waiters = cursor.fetchall()
            
            if waiters:
                flash(f"Arama sonucunda {len(waiters)} garson bulundu.", "success")
            else:
                flash("Aradığınız kritere uygun garson bulunamadı.", "info")
                
            return render_template('waiters.html', waiters=waiters)

        elif action == 'clear':
            return redirect(url_for('waiters'))

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

    return redirect(url_for('waiters'))

def waiter_dashboard():
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
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
            SELECT m.menu_id, m.price, m.stock_quantity, f.item_name, m.custom_name 
            FROM menus m 
            JOIN foods f ON m.food_id = f.food_id 
            WHERE m.restaurant_id = %s AND m.is_visible = 1
        ''', (restaurant_id,))
        menus = cursor.fetchall()

        cursor.execute('''
            SELECT DISTINCT table_no 
            FROM orders 
            WHERE restaurant_id = %s AND order_status IN ('pending', 'preparing', 'ready', 'delivered')
        ''', (restaurant_id,))
        occupied_tables = [row['table_no'] for row in cursor.fetchall()]
        
        return render_template('waiter_dashboard.html', menus=menus, total_tables=total_tables, occupied_tables=occupied_tables)
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        return render_template('waiter_dashboard.html', menus=[], total_tables=0, occupied_tables=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def waiter_create_order():
    if not session.get('logged_in') or session.get('role') != 'waiter':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    table_no = request.form.get('table_no')
    cart_indices = request.form.getlist('cart_index')
    
    if not cart_indices:
        flash("Adisyona hiçbir ürün eklemediniz!", "warning")
        return redirect(url_for('waiter_dashboard'))
    
    connection = get_db_connection()
    if connection is None:
        return redirect(url_for('waiter_dashboard'))

    try:
        cursor = connection.cursor(dictionary=True)
        
        total_qty, total_amount = 0, 0
        order_details = [] 

        for idx in cart_indices:
            menu_id = request.form.get(f'menu_id_{idx}')
            qty = int(request.form.get(f'qty_{idx}', 0))
            note = request.form.get(f'note_{idx}', '').strip() 
            selected_choices = request.form.getlist(f'choices_{idx}[]')

            if qty > 0:
                cursor.execute('''
                    SELECT m.price, m.food_id, m.stock_quantity, COALESCE(m.custom_name, f.item_name) AS item_name 
                    FROM menus m JOIN foods f ON m.food_id = f.food_id WHERE m.menu_id = %s FOR UPDATE
                ''', (menu_id,))
                result = cursor.fetchone()
                
                if result:
                    current_stock = int(result['stock_quantity'])
                    if current_stock < qty:
                        connection.rollback()
                        flash(f"Üzgünüz, masaya eklemek istediğiniz '{result['item_name']}' için yeterli stok kalmamış. (Kalan: {current_stock})", "danger")
                        return redirect(url_for('waiter_dashboard'))
                        
                    cursor.execute("UPDATE menus SET stock_quantity = stock_quantity - %s WHERE menu_id = %s", (qty, menu_id))
                    
                    base_price = float(result['price'])
                    extras_price = 0
                    choice_details = [] 
                    
                    if selected_choices:
                        format_strings = ','.join(['%s'] * len(selected_choices))
                        cursor.execute(f"SELECT choice_id, choice_name, additional_price, linked_menu_id FROM menu_option_choices WHERE choice_id IN ({format_strings})", tuple(selected_choices))
                        choice_details = cursor.fetchall()
                        
                        for row in choice_details:
                            if row['additional_price']:
                                extras_price += float(row['additional_price'])
                                
                            # 🚀 DEĞİŞİKLİK 3: MASTER SKU (GÖLGE ÜRÜN) STOK KONTROLÜ
                            if row.get('linked_menu_id'):
                                linked_id = row['linked_menu_id']
                                cursor.execute("""
                                    SELECT m.stock_quantity, COALESCE(m.custom_name, f.item_name) AS item_name 
                                    FROM menus m 
                                    JOIN foods f ON m.food_id = f.food_id 
                                    WHERE m.menu_id = %s FOR UPDATE
                                """, (linked_id,))
                                linked_data = cursor.fetchone()
                                
                                if linked_data:
                                    linked_stock = int(linked_data['stock_quantity'])
                                    if linked_stock < qty:
                                        connection.rollback()
                                        flash(f"Üzgünüz, ekstra olarak seçilen '{row['choice_name']}' için yeterli stok kalmamış.", "danger")
                                        return redirect(url_for('waiter_dashboard'))
                                        
                                    cursor.execute("UPDATE menus SET stock_quantity = stock_quantity - %s WHERE menu_id = %s", (qty, linked_id))
                    
                    unit_price = base_price + extras_price
                    total_amount += (unit_price * qty)
                    total_qty += qty
                    
                    order_details.append({
                        'food_id': result['food_id'], 'menu_id': menu_id, 'item_name': result['item_name'],
                        'quantity': qty, 'price': unit_price,
                        'choices': choice_details, 'cart_index': idx, 'note': note
                    })

        if total_qty > 0:
            query = 'INSERT INTO orders (order_date, sales_qty, sales_amount, restaurant_id, order_status, table_no, order_type) VALUES (NOW(), %s, %s, %s, %s, %s, %s)'
            cursor.execute(query, (total_qty, total_amount, restaurant_id, 'pending', table_no, 'Dine-in'))
            order_id = cursor.lastrowid
            flash(f"Masa {table_no} için yeni lezzetler mutfağa iletildi.", "success")
            
            for item in order_details:
                cursor.execute("""
                    INSERT INTO order_items (order_id, food_id, menu_id, quantity, unit_price, cart_index, item_note, item_name_snapshot)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (order_id, item['food_id'], item['menu_id'], item['quantity'], item['price'], item['cart_index'], item['note'], item['item_name']))
                
                if item['choices']:
                    for choice in item['choices']:
                        cursor.execute("""
                            INSERT INTO order_item_choices (order_id, food_id, choice_id, cart_index, choice_name_snapshot, choice_price_snapshot)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (order_id, item['food_id'], choice['choice_id'], item['cart_index'], choice['choice_name'], float(choice['additional_price'] or 0.00)))
            
            connection.commit()
    except Error as e:
        connection.rollback() 
        print("Adisyon Hatası:", e)
    finally:
        if connection.is_connected(): cursor.close(); connection.close()
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

        # Masadaki tüm aktif fişleri (biletleri) eskiden yeniye doğru bul
        cursor.execute("""
            SELECT order_id FROM orders 
            WHERE restaurant_id = %s AND table_no = %s AND order_status IN ('pending', 'preparing', 'ready', 'delivered')
            ORDER BY order_id ASC
        """, (restaurant_id, table_no))
        active_orders = cursor.fetchall()

        if active_orders:
            main_order_id = active_orders[0]['order_id'] # Ana faturamız en eski açılan sipariş olacak
            
            # Eğer masada birden fazla fiş (Adana ayrı, Pepsi ayrı) varsa, hesabı kapatırken hepsini birleştir!
            if len(active_orders) > 1:
                other_order_ids = [str(o['order_id']) for o in active_orders[1:]]
                format_strings = ','.join(['%s'] * len(other_order_ids))
                
                # 1. Diğer siparişlerdeki yemekleri ana siparişe (main_order_id) taşı
                cursor.execute(f"""
                    UPDATE order_items 
                    SET order_id = %s 
                    WHERE order_id IN ({format_strings})
                """, [main_order_id] + other_order_ids)
                
                # 2. Ana siparişin toplam tutarını ve adetini her şey dahil şekilde yeniden hesapla
                cursor.execute("""
                    UPDATE orders o
                    SET 
                        sales_qty = (SELECT COALESCE(SUM(quantity), 0) FROM order_items WHERE order_id = %s),
                        sales_amount = (SELECT COALESCE(SUM(quantity * unit_price), 0) FROM order_items WHERE order_id = %s)
                    WHERE order_id = %s
                """, (main_order_id, main_order_id, main_order_id))
                
                # 3. İçi boşaltılan diğer fişleri veritabanından temizle
                cursor.execute(f"""
                    DELETE FROM orders 
                    WHERE order_id IN ({format_strings})
                """, other_order_ids)
            
            # Son olarak birleşmiş devasa ana siparişi "Tamamlandı" yap ve hesabı kapat
            cursor.execute("""
                UPDATE orders 
                SET order_status = 'completed' 
                WHERE order_id = %s
            """, (main_order_id,))
            
            connection.commit()
            
            flash(f"💳 Masa {table_no} hesabı kapatıldı. Adisyon hazırlanıyor...", "success")
            return redirect(url_for('waiter_receipt', order_id=main_order_id))
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

def waiter_receipt(order_id):
    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT restaurant_name, restaurant_address FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
        restaurant = cursor.fetchone()

        cursor.execute("SELECT order_id, order_date, sales_amount, table_no FROM orders WHERE order_id = %s AND restaurant_id = %s", (order_id, restaurant_id))
        order = cursor.fetchone()

        cursor.execute("""
            SELECT oi.food_id, oi.item_name_snapshot AS item_name, 
                   oi.quantity, oi.unit_price, oi.cart_index, oi.item_note
            FROM order_items oi
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()

        for item in items:
            if item['cart_index']:
                cursor.execute("""
                    SELECT choice_name_snapshot AS choice_name, choice_price_snapshot AS additional_price 
                    FROM order_item_choices 
                    WHERE order_id = %s AND cart_index = %s
                """, (order_id, item['cart_index']))
            else:
                # Geriye dönük uyumluluk (Eski siparişleri de bozmamak için)
                cursor.execute("""
                    SELECT choice_name_snapshot AS choice_name, choice_price_snapshot AS additional_price 
                    FROM order_item_choices 
                    WHERE order_id = %s AND food_id = %s
                """, (order_id, item['food_id']))
            item['choices'] = cursor.fetchall()

        return render_template('receipt.html', order=order, items=items, restaurant=restaurant)
    finally:
        cursor.close(); connection.close()