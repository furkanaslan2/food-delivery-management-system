from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
from datetime import date
import re

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
            customer_address = request.form.get('customer_address')
            payment_method = request.form.get('payment_method') 
            courier_id = request.form.get('courier_id') or None
            table_no = request.form.get('table_no') or None

            raw_phone = request.form.get('customer_phone', '')
            clean_phone = re.sub(r'\D', '', raw_phone) if raw_phone else None
            if clean_phone == '05':
                clean_phone = None
            
            if order_type == 'Delivery':
                table_no = None
                if not customer_name or not clean_phone or not customer_address:
                    flash("Paket servis için müşteri bilgileri (telefon dahil) zorunludur!", "warning")
                    return redirect(url_for('orders'))
                if not re.match(r'^05\d{9}$', clean_phone):
                    flash("Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)", "danger")
                    return redirect(url_for('orders'))
            
            if order_type == 'Dine-in':
                if not table_no:
                    flash("Masa siparişi için lütfen Masa Numarası girin!", "warning")
                    return redirect(url_for('orders'))
                if clean_phone and not re.match(r'^05\d{9}$', clean_phone):
                    flash("Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)", "danger")
                    return redirect(url_for('orders'))

            customer_phone = clean_phone

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
                            # 🚀 1. DEĞİŞİKLİK: Sadece fiyatı değil, yemeğin anlık adını da (custom_name veya item_name) çekiyoruz!
                            cursor.execute("""
                                SELECT m.price, m.food_id, m.stock_quantity, 
                                       COALESCE(m.custom_name, f.item_name) AS item_name
                                FROM menus m
                                JOIN foods f ON m.food_id = f.food_id
                                WHERE m.menu_id = %s
                            """, (menu_id,))
                            menu_item = cursor.fetchone()
                            
                            if menu_item:
                                current_stock = menu_item['stock_quantity']
                                if current_stock < qty:
                                    flash(f"HATA: Stok yetersiz!", "danger")
                                    return redirect(url_for('orders'))
                                
                                base_price = float(menu_item['price'])
                                extras_price = 0
                                choice_details = [] # Ekstraların detaylarını (isim ve fiyat) tutacağımız yeni liste
                                
                                if selected_choices:
                                    format_strings = ','.join(['%s'] * len(selected_choices))
                                    # 🚀 2. DEĞİŞİKLİK: Ekstraların da sadece ID'sini değil, isim ve fiyatlarını da çekiyoruz!
                                    cursor.execute(f"SELECT choice_id, choice_name, additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", selected_choices)
                                    choice_details = cursor.fetchall()
                                    
                                    for row in choice_details:
                                        if row['additional_price']:
                                            extras_price += float(row['additional_price'])
                                
                                unit_price = base_price + extras_price
                                total_amount += (unit_price * qty)
                                total_qty += qty
                                
                                valid_items.append({
                                    'food_id': menu_item['food_id'],
                                    'menu_id': menu_id, # Tekrar sipariş için lazım olacak
                                    'item_name': menu_item['item_name'], # Mühürlenecek İsim!
                                    'quantity': qty,
                                    'unit_price': unit_price,
                                    'choice_details': choice_details, # Mühürlenecek Ekstra Listesi!
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
                 order_type, table_no, customer_name, customer_phone, customer_address, courier_id, payment_method)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (restaurant_id, order_status, total_qty, total_amount, 
                                   order_type, table_no, customer_name, customer_phone, customer_address, courier_id, payment_method))
            final_order_id = cursor.lastrowid

            # 🚀 3. DEĞİŞİKLİK: Fişe mühür (Snapshot) vurma operasyonu!
            for item in valid_items:
                item_query = """
                    INSERT INTO order_items 
                    (order_id, food_id, menu_id, quantity, unit_price, cart_index, item_note, item_name_snapshot) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(item_query, (final_order_id, item['food_id'], item['menu_id'], item['quantity'], item['unit_price'], item['cart_index'], item['note'], item['item_name']))
                
                if item['choice_details']:
                    for choice in item['choice_details']:
                        cursor.execute("""
                            INSERT INTO order_item_choices 
                            (order_id, food_id, choice_id, cart_index, choice_name_snapshot, choice_price_snapshot)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (final_order_id, item['food_id'], choice['choice_id'], item['cart_index'], choice['choice_name'], choice['additional_price'] or 0.00))

            for item in valid_items:
                cursor.execute("""
                    UPDATE menus 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE food_id = %s
                """, (item['quantity'], item['food_id']))

            connection.commit()
            flash(f"Sipariş başarıyla eklendi! Toplam: ₺{total_amount:.2f} (ID: {final_order_id})", "success")

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

            customer_name = request.form.get('customer_name')
            customer_address = request.form.get('customer_address')
            courier_id = request.form.get('courier_id') or None
            payment_method = request.form.get('payment_method')

            raw_phone = request.form.get('customer_phone', '')
            clean_phone = re.sub(r'\D', '', raw_phone) if raw_phone else None
            if clean_phone == '05':
                clean_phone = None

            if order_type == 'Delivery':
                table_no = None  
                if not customer_name or not clean_phone or not customer_address or not payment_method:
                    flash("Paket servis için müşteri bilgileri (telefon dahil) ve ödeme yöntemi zorunludur!", "warning")
                    return redirect(url_for('orders'))
                if not re.match(r'^05\d{9}$', clean_phone):
                    flash("Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)", "danger")
                    return redirect(url_for('orders'))
            
            if order_type == 'Dine-in' and clean_phone and not re.match(r'^05\d{9}$', clean_phone):
                flash("Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)", "danger")
                return redirect(url_for('orders'))

            customer_phone = clean_phone

            if not update_order_id:
                flash("Güncellenecek sipariş seçilmedi.", "warning")
                return redirect(url_for('orders'))

            # 🚀 YENİ EKLENEN BÖLÜM: ÜRÜN LİSTESİ GÜNCELLEMESİ 🚀
            cart_indices = request.form.getlist('cart_index')
            
            # Eğer JS tarafı ürünleri göndermişse (Yani Online Ödeme değilse ve ürün listesi açıksa)
            if cart_indices:
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
                                cursor.execute("""
                                    SELECT m.price, m.food_id, m.stock_quantity, 
                                           COALESCE(m.custom_name, f.item_name) AS item_name
                                    FROM menus m
                                    JOIN foods f ON m.food_id = f.food_id
                                    WHERE m.menu_id = %s
                                """, (menu_id,))
                                menu_item = cursor.fetchone()
                                
                                if menu_item:
                                    base_price = float(menu_item['price'])
                                    extras_price = 0
                                    choice_details = []
                                    
                                    if selected_choices:
                                        format_strings = ','.join(['%s'] * len(selected_choices))
                                        cursor.execute(f"SELECT choice_id, choice_name, additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", selected_choices)
                                        choice_details = cursor.fetchall()
                                        for row in choice_details:
                                            if row['additional_price']:
                                                extras_price += float(row['additional_price'])
                                    
                                    unit_price = base_price + extras_price
                                    total_amount += (unit_price * qty)
                                    total_qty += qty
                                    
                                    valid_items.append({
                                        'food_id': menu_item['food_id'],
                                        'menu_id': menu_id,
                                        'item_name': menu_item['item_name'],
                                        'quantity': qty,
                                        'unit_price': unit_price,
                                        'choice_details': choice_details,
                                        'cart_index': idx,
                                        'note': note
                                    })
                        except (ValueError, TypeError):
                            continue
                            
                if not valid_items:
                    flash("Lütfen siparişe en az bir ürün ekleyin!", "warning")
                    return redirect(url_for('orders'))
                
                # 1. Eski siparişin stoklarını iade et
                cursor.execute("SELECT food_id, quantity FROM order_items WHERE order_id = %s", (update_order_id,))
                old_items = cursor.fetchall()
                for old_item in old_items:
                    cursor.execute("UPDATE menus SET stock_quantity = stock_quantity + %s WHERE food_id = %s", (old_item['quantity'], old_item['food_id']))
                
                # 2. Eski kalemleri ve ekstraları tamamen sil
                cursor.execute("DELETE FROM order_item_choices WHERE order_id = %s", (update_order_id,))
                cursor.execute("DELETE FROM order_items WHERE order_id = %s", (update_order_id,))
                
                # 3. Yeni kalemleri Snapshot (Mühür) ile kaydet
                for item in valid_items:
                    item_query = """
                        INSERT INTO order_items 
                        (order_id, food_id, menu_id, quantity, unit_price, cart_index, item_note, item_name_snapshot) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(item_query, (update_order_id, item['food_id'], item['menu_id'], item['quantity'], item['unit_price'], item['cart_index'], item['note'], item['item_name']))
                    
                    if item['choice_details']:
                        for choice in item['choice_details']:
                            cursor.execute("""
                                INSERT INTO order_item_choices 
                                (order_id, food_id, choice_id, cart_index, choice_name_snapshot, choice_price_snapshot)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (update_order_id, item['food_id'], choice['choice_id'], item['cart_index'], choice['choice_name'], float(choice['additional_price'] or 0.00)))
                            
                    # Yeni stokları düşür
                    cursor.execute("UPDATE menus SET stock_quantity = stock_quantity - %s WHERE food_id = %s", (item['quantity'], item['food_id']))

                # 4. Faturanın ana verilerini güncelle (Yeni Fiyat ve Yeni Adet)
                cursor.execute("""
                    UPDATE orders 
                    SET sales_qty = %s, sales_amount = %s
                    WHERE order_id = %s
                """, (total_qty, total_amount, update_order_id))

            # 🚀 HER HALÜKARDA ANA SİPARİŞ BİLGİLERİNİ GÜNCELLE
            query = """
                UPDATE orders 
                SET order_status = %s, order_type = %s, table_no = %s, 
                    customer_name = %s, customer_phone = %s, customer_address = %s, courier_id = %s, payment_method = %s
                WHERE order_id = %s AND restaurant_id = %s
            """
            cursor.execute(query, (order_status, order_type, table_no, customer_name, customer_phone, customer_address, courier_id, payment_method, update_order_id, restaurant_id))
            
            connection.commit()
            flash("Sipariş başarıyla güncellendi!", "success")

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
    
    # 🚀 DEĞİŞİKLİK 1: oi.menu_id sütunu eklendi
    query = """
        SELECT oi.food_id, oi.menu_id, oi.item_name_snapshot AS item_name, 
               oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) as subtotal,
               oi.cart_index, oi.item_note
        FROM order_items oi
        WHERE oi.order_id = %s
    """
    cursor.execute(query, (order_id,))
    items = cursor.fetchall()
    
    for item in items:
        # 🚀 DEĞİŞİKLİK 2: choice_id sütunu eklendi
        if item.get('cart_index'):
            cursor.execute("""
                SELECT choice_id, choice_name_snapshot AS choice_name, choice_price_snapshot AS additional_price 
                FROM order_item_choices 
                WHERE order_id = %s AND cart_index = %s
            """, (order_id, item['cart_index']))
        else:
            cursor.execute("""
                SELECT choice_id, choice_name_snapshot AS choice_name, choice_price_snapshot AS additional_price 
                FROM order_item_choices 
                WHERE order_id = %s AND food_id = %s
            """, (order_id, item['food_id']))
        item['choices'] = cursor.fetchall()
    
    cursor.close()
    conn.close()
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
                # 🚀 SADECE SİPARİŞ TABLOSUNDAKİ MÜHÜRLÜ İSMİ ÇEKİYORUZ
                cursor.execute("""
                    SELECT oi.*, oi.item_name_snapshot AS item_name 
                    FROM order_items oi
                    WHERE oi.order_id = %s
                """, (order['order_id'],))
                items = cursor.fetchall()

                for item in items:
                    if item.get('cart_index'):
                        cursor.execute("""
                            SELECT choice_name_snapshot AS choice_name 
                            FROM order_item_choices 
                            WHERE order_id = %s AND cart_index = %s
                        """, (order['order_id'], item['cart_index']))
                    else:
                        cursor.execute("""
                            SELECT choice_name_snapshot AS choice_name 
                            FROM order_item_choices 
                            WHERE order_id = %s AND food_id = %s
                        """, (order['order_id'], item['food_id']))
                        
                    choices = cursor.fetchall()
                    
                    if choices:
                        names = [c['choice_name'] for c in choices]
                        # İsimsiz kalma ihtimaline karşı güvenlik bariyeri
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