from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
from datetime import date

def orders():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('orders.html', orders=[], couriers=[], foods=[])

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute('''
                SELECT o.*, r.restaurant_name 
                FROM orders o
                LEFT JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.order_status != 'awaiting_payment'
                ORDER BY o.order_id DESC
            ''')
            orders_data = cursor.fetchall()
            cursor.execute('SELECT * FROM couriers')
            couriers = cursor.fetchall()
            foods = []
        elif role == 'user' and restaurant_id:
            cursor.execute("SELECT * FROM orders WHERE restaurant_id = %s AND order_status != 'awaiting_payment' ORDER BY order_id DESC", (restaurant_id,))
            orders_data = cursor.fetchall()
            cursor.execute('SELECT * FROM couriers WHERE restaurant_id = %s', (restaurant_id,))
            couriers = cursor.fetchall()
            
            query_foods = """
                SELECT m.menu_id, f.food_id, COALESCE(m.custom_name, f.item_name) AS item_name, m.price 
                FROM menus m 
                JOIN foods f ON m.food_id = f.food_id 
                WHERE m.restaurant_id = %s
            """
            cursor.execute(query_foods, (restaurant_id,))
            foods = cursor.fetchall()
        else:
            flash("Yetkisiz erişim!", "danger")
            return redirect(url_for('index'))
    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        orders_data = []
        couriers = []
        foods = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('orders.html', orders=orders_data, couriers=couriers, foods=foods)
    
def order_action():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('orders'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            order_type = request.form.get('order_type')
            if not order_type:
                flash("Lütfen sipariş türünü seçin (Dine-in veya Delivery).", "warning")
                return redirect(url_for('orders'))
            
            restaurant_id = restaurant_id_session if role == 'user' else request.form.get('restaurant_id')

            customer_name = request.form.get('customer_name')
            customer_phone = request.form.get('customer_phone')
            customer_address = request.form.get('customer_address')
            courier_id = request.form.get('courier_id') or None
            table_no = request.form.get('table_no') or None

            if order_type == 'Delivery':
                table_no = None
                if not customer_name or not customer_phone or not customer_address:
                    flash("Paket servis için müşteri bilgileri zorunludur!", "warning")
                    return redirect(url_for('orders'))
            
            if order_type == 'Dine-in':
                if not table_no:
                    flash("Masa siparişi için lütfen Masa Numarası girin!", "warning")
                    return redirect(url_for('orders'))

            # 🚀 YENİ POS SEPET SİSTEMİ (Garson paneliyle birebir aynı mantık)
            cart_indices = request.form.getlist('cart_index')
            
            valid_items = []
            total_qty = 0
            total_amount = 0

            for idx in cart_indices:
                menu_id = request.form.get(f'menu_id_{idx}')
                qty_str = request.form.get(f'qty_{idx}', '0')
                note = request.form.get(f'note_{idx}', '').strip()
                selected_choices = request.form.getlist(f'choices_{idx}[]')

                if menu_id and qty_str:
                    try:
                        qty = int(qty_str)
                        if qty > 0:
                            cursor.execute("SELECT price, food_id, stock_quantity FROM menus WHERE menu_id = %s", (menu_id,))
                            menu_item = cursor.fetchone()
                            
                            if menu_item:
                                current_stock = menu_item['stock_quantity']
                                if current_stock < qty:
                                    flash(f"HATA: Stok yetersiz!", "danger")
                                    return redirect(url_for('orders'))
                                
                                base_price = float(menu_item['price'])
                                extras_price = 0
                                
                                if selected_choices:
                                    format_strings = ','.join(['%s'] * len(selected_choices))
                                    cursor.execute(f"SELECT additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", selected_choices)
                                    for row in cursor.fetchall():
                                        if row['additional_price']:
                                            extras_price += float(row['additional_price'])
                                
                                unit_price = base_price + extras_price
                                total_amount += (unit_price * qty)
                                total_qty += qty
                                
                                valid_items.append({
                                    'food_id': menu_item['food_id'],
                                    'quantity': qty,
                                    'unit_price': unit_price,
                                    'choices': selected_choices,
                                    'cart_index': idx,
                                    'note': note
                                })
                    except (ValueError, TypeError):
                        continue 

            if not restaurant_id:
                flash("Restoran ID zorunludur.", "warning")
                return redirect(url_for('orders'))

            if not valid_items: 
                 flash("Lütfen en az bir ürün ekleyin!", "warning")
                 return redirect(url_for('orders'))

            order_status = request.form.get('order_status') or 'pending'

            query = """
                INSERT INTO orders 
                (restaurant_id, order_date, order_status, sales_qty, sales_amount, 
                 order_type, table_no, customer_name, customer_phone, customer_address, courier_id)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (restaurant_id, order_status, total_qty, total_amount, 
                                   order_type, table_no, customer_name, customer_phone, customer_address, courier_id))
            final_order_id = cursor.lastrowid

            for item in valid_items:
                item_query = "INSERT INTO order_items (order_id, food_id, quantity, unit_price, cart_index, item_note) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(item_query, (final_order_id, item['food_id'], item['quantity'], item['unit_price'], item['cart_index'], item['note']))
                
                if item['choices']:
                    for choice_id in item['choices']:
                        cursor.execute("""
                            INSERT INTO order_item_choices (order_id, food_id, choice_id, cart_index)
                            VALUES (%s, %s, %s, %s)
                        """, (final_order_id, item['food_id'], choice_id, item['cart_index']))

            for item in valid_items:
                cursor.execute("""
                    UPDATE menus 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE food_id = %s
                """, (item['quantity'], item['food_id']))

            connection.commit()
            flash(f"Sipariş başarıyla eklendi! Toplam: ${total_amount:.2f} (ID: {final_order_id})", "success")

        elif action == 'delete':
            selected_ids = request.form.get('selected_orders')
            if not selected_ids:
                flash("Silinecek sipariş seçilmedi.", "warning")
                return redirect(url_for('orders'))

            ids_list = selected_ids.split(',')

            # Silinen siparişlerin stoklarını iade et
            for o_id in ids_list:
                cursor.execute("SELECT food_id, quantity FROM order_items WHERE order_id = %s", (o_id,))
                items_to_return = cursor.fetchall()
                for item in items_to_return:
                    cursor.execute("""
                        UPDATE menus 
                        SET stock_quantity = stock_quantity + %s 
                        WHERE food_id = %s
                    """, (item['quantity'], item['food_id']))

            format_strings = ','.join(['%s'] * len(ids_list))
            if role == 'user':
                query = f"DELETE FROM orders WHERE order_id IN ({format_strings}) AND restaurant_id = %s"
                cursor.execute(query, ids_list + [restaurant_id_session])
            else:
                query = f"DELETE FROM orders WHERE order_id IN ({format_strings})"
                cursor.execute(query, ids_list)

            connection.commit()
            flash(f"{cursor.rowcount} sipariş başarıyla silindi ve stoklar iade edildi.", "success")

        elif action == 'update':
            update_order_id = request.form.get('update_order_id')
            order_status = request.form.get('order_status')     
            order_type = request.form.get('order_type')
            table_no = request.form.get('table_no')
            
            restaurant_id = restaurant_id_session if role == 'user' else request.form.get('restaurant_id')

            if order_type == 'Delivery':
                table_no = None  
            
            customer_name = request.form.get('customer_name')
            customer_phone = request.form.get('customer_phone')
            customer_address = request.form.get('customer_address')
            courier_id = request.form.get('courier_id') or None

            if not update_order_id:
                flash("Güncellenecek sipariş seçilmedi.", "warning")
                return redirect(url_for('orders'))

            query = """
                UPDATE orders 
                SET order_status = %s, order_type = %s, table_no = %s, 
                    customer_name = %s, customer_phone = %s, customer_address = %s, courier_id = %s
                WHERE order_id = %s AND restaurant_id = %s
            """
            cursor.execute(query, (order_status, order_type, table_no, customer_name, customer_phone, customer_address, courier_id, update_order_id, restaurant_id))
            
            connection.commit()
            flash("Sipariş detayları başarıyla güncellendi!", "success")

        elif action == 'filter':
            order_id = request.form.get('order_id')

            query = """
                SELECT o.*, r.restaurant_name 
                FROM orders o
                LEFT JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.order_status != 'awaiting_payment'
            """
            params = []
            
            if role == 'user':
                query += " AND o.restaurant_id = %s"
                params.append(restaurant_id_session)

            if order_id:
                query += " AND o.order_id = %s"
                params.append(order_id)
            
            query += " ORDER BY o.order_id DESC"
            cursor.execute(query, params)
            orders_data = cursor.fetchall()
            
            if orders_data:
                flash(f"Arama sonucunda {len(orders_data)} sipariş bulundu.", "success")
            else:
                flash("Aradığınız sipariş bulunamadı.", "info")

            cursor.execute('SELECT * FROM couriers WHERE restaurant_id = %s' if role == 'user' else 'SELECT * FROM couriers', (restaurant_id_session,) if role == 'user' else ())
            couriers = cursor.fetchall()
            
            if role == 'user':
                cursor.execute("SELECT m.menu_id, f.food_id, COALESCE(m.custom_name, f.item_name) AS item_name, m.price FROM menus m JOIN foods f ON m.food_id = f.food_id WHERE m.restaurant_id = %s", (restaurant_id_session,))
            else:
                cursor.execute("SELECT m.menu_id, f.food_id, COALESCE(m.custom_name, f.item_name) AS item_name, m.price FROM menus m JOIN foods f ON m.food_id = f.food_id")
            foods = cursor.fetchall()
                
            return render_template('orders.html', orders=orders_data, foods=foods, couriers=couriers)
        
        elif action == 'assign_courier':
            assign_order_id = request.form.get('update_order_id')
            courier_id = request.form.get('courier_id')
            
            if not courier_id:
                flash("Lütfen yola çıkarmak için bir kurye seçin.", "warning")
                return redirect(url_for('orders'))

            cursor.execute("""
                UPDATE orders 
                SET order_status = 'ready', courier_id = %s 
                WHERE order_id = %s
            """, (courier_id, assign_order_id))
            
            connection.commit()
            flash("Kurye başarıyla atandı ve sipariş yola çıktı! 🚀", "success")

        elif action == 'clear':
            return redirect(url_for('orders'))

    except Error as e:
        flash(f"Bir hata oluştu: {e}", "danger")
        connection.rollback()
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('orders'))

def get_order_details(order_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Yetkisiz erişim'}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT f.food_id, COALESCE(m.custom_name, f.item_name) AS item_name, 
               oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) as subtotal,
               oi.cart_index, oi.item_note
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN foods f ON oi.food_id = f.food_id
        LEFT JOIN menus m ON oi.food_id = m.food_id AND o.restaurant_id = m.restaurant_id
        WHERE oi.order_id = %s
    """
    cursor.execute(query, (order_id,))
    items = cursor.fetchall()
    
    for item in items:
        # Eğer yeni sistemden geldiyse karışmaması için cart_index üzerinden arıyoruz!
        if item.get('cart_index'):
            cursor.execute("""
                SELECT moc.choice_name, moc.additional_price 
                FROM order_item_choices oic
                JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                WHERE oic.order_id = %s AND oic.cart_index = %s
            """, (order_id, item['cart_index']))
        else:
            cursor.execute("""
                SELECT moc.choice_name, moc.additional_price 
                FROM order_item_choices oic
                JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                WHERE oic.order_id = %s AND oic.food_id = %s
            """, (order_id, item['food_id']))
        item['choices'] = cursor.fetchall()
    
    cursor.close(); conn.close()
    return jsonify(items)

def get_restaurant_details(restaurant_id):
    if 'logged_in' not in session:
        return jsonify({'error': 'Yetkisiz erişim'}), 401
    
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
    if 'logged_in' not in session:
        return jsonify({'new_orders': False})
        
    role = session.get('role')
    if role not in ['admin', 'user']:
        return jsonify({'new_orders': False})
        
    client_max_id = request.args.get('last_id', 0, type=int)
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            if role == 'user':
                restaurant_id = session.get('restaurant_id')
                if not restaurant_id:
                    return jsonify({'new_orders': False})
                cursor.execute("SELECT MAX(order_id) as max_id FROM orders WHERE restaurant_id = %s AND order_status != 'awaiting_payment'", (restaurant_id,))
            else: 
                cursor.execute("SELECT MAX(order_id) as max_id FROM orders WHERE order_status != 'awaiting_payment'")
                
            result = cursor.fetchone()
            db_max_id = result['max_id'] if result and result['max_id'] else 0
            
            if db_max_id > client_max_id:
                return jsonify({'new_orders': True})
                
        except Exception as e:
            print(f"Sipariş API kontrol hatası: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return jsonify({'new_orders': False})

# ==========================================
# 🧑‍🍳 MUTFAK EKRANI (KITCHEN DISPLAY SYSTEM)
# ==========================================
def kitchen_display():
    if not session.get('logged_in') or session.get('role') != 'user':
        return redirect(url_for('login'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    orders_data = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # SADECE pending (bekliyor) ve preparing (hazırlanıyor) olan siparişleri, ESKİDEN YENİYE sırala (İlk giren ilk çıkar)
            cursor.execute("""
                SELECT * FROM orders 
                WHERE restaurant_id = %s AND order_status IN ('pending', 'preparing')
                ORDER BY order_date ASC
            """, (restaurant_id,))
            orders_list = cursor.fetchall()

            for order in orders_list:
                # 🚀 DÜZELTME: foods ve menus tablolarını birleştirip, yeni cart_index ve item_note verilerini de çekiyoruz
                cursor.execute("""
                    SELECT oi.*, COALESCE(m.custom_name, f.item_name) AS item_name 
                    FROM order_items oi
                    JOIN foods f ON oi.food_id = f.food_id
                    LEFT JOIN menus m ON oi.food_id = m.food_id AND m.restaurant_id = %s
                    WHERE oi.order_id = %s
                """, (order['restaurant_id'], order['order_id']))
                items = cursor.fetchall()

                for item in items:
                    # 🚀 YENİ ZIRH: Eğer ürün yeni sepet sistemiyle (cart_index) eklendiyse sadece kendi satırındaki ekstraları çek
                    if item.get('cart_index'):
                        cursor.execute("""
                            SELECT moc.choice_name 
                            FROM order_item_choices oic
                            JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                            WHERE oic.order_id = %s AND oic.cart_index = %s
                        """, (order['order_id'], item['cart_index']))
                    else:
                        # Eski siparişler için geriye dönük uyumluluk
                        cursor.execute("""
                            SELECT moc.choice_name 
                            FROM order_item_choices oic
                            JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                            WHERE oic.order_id = %s AND oic.food_id = %s
                        """, (order['order_id'], item['food_id']))
                        
                    choices = cursor.fetchall()
                    
                    if choices:
                        names = [c['choice_name'] for c in choices]
                        # Eğer custom_name veritabanında NULL ise ekranda "None" yazmasını engelliyoruz
                        current_name = item['item_name'] if item['item_name'] else "İsimsiz Menü"
                        item['item_name'] = f"{current_name} ({', '.join(names)})"
                
                order['items'] = items
                orders_data.append(order)

        finally:
            cursor.close()
            connection.close()

    return render_template('kitchen.html', orders=orders_data)

# ==========================================
# 🧑‍🍳 MUTFAK EKRANI GÜVENLİ İŞLEM (API)
# ==========================================
def kitchen_order_action():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    order_id = request.form.get('order_id')
    new_status = request.form.get('order_status')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # 📍 MÜKEMMEL ÇÖZÜM: Sadece durumu (order_status) güncelliyoruz. 
            # Müşteri bilgileri, kurye, adres vb. HİÇBİR ŞEYE dokunmuyoruz!
            cursor.execute("""
                UPDATE orders 
                SET order_status = %s 
                WHERE order_id = %s AND restaurant_id = %s
            """, (new_status, order_id, restaurant_id))
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    # İşlem bitince Mutfak Ekranına geri dön
    return redirect(url_for('kitchen_display'))