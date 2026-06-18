from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
import os
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 1. RESTORAN MENÜSÜNÜ GÖRÜNTÜLEME
def view_restaurant(restaurant_id):
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Restoranları görmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    connection = get_db_connection()
    restaurant = None
    menu_items = []
    reviews = []
    
    grouped_menus = {}
    popular_items = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            restaurant = cursor.fetchone()

            if restaurant:
                # YENİ: Restoran detay sayfasına da restoranın Açık/Kapalı bilgisini gönderiyoruz
                now = datetime.now().time()
                is_open = True
                if restaurant.get('is_manually_closed'):
                    is_open = False
                elif restaurant.get('opening_time') is not None and restaurant.get('closing_time') is not None:
                    op_td = restaurant['opening_time']
                    cl_td = restaurant['closing_time']
                    op_time = (datetime.min + op_td).time() if isinstance(op_td, timedelta) else op_td
                    cl_time = (datetime.min + cl_td).time() if isinstance(cl_td, timedelta) else cl_td
                    
                    if op_time < cl_time:
                        is_open = op_time <= now <= cl_time
                    else:
                        is_open = now >= op_time or now <= cl_time
                        
                restaurant['is_open'] = is_open

            cursor.execute("""
                SELECT m.*, f.item_name AS food_name, f.category AS category 
                FROM menus m
                JOIN foods f ON m.food_id = f.food_id
                WHERE m.restaurant_id = %s AND m.stock_quantity > 0
            """, (restaurant_id,))
            menu_items = cursor.fetchall()
            
            for item in menu_items:
                cat = item.get('category') or 'Diğer' 
                if cat not in grouped_menus:
                    grouped_menus[cat] = []
                grouped_menus[cat].append(item)

            cursor.execute("""
                SELECT m.*, f.item_name AS food_name, 
                       COALESCE((
                           SELECT SUM(oi.quantity) 
                           FROM order_items oi 
                           JOIN orders o ON oi.order_id = o.order_id 
                           WHERE oi.food_id = m.food_id AND o.order_status = 'delivered'
                       ), 0) as total_sales
                FROM menus m
                JOIN foods f ON m.food_id = f.food_id
                WHERE m.restaurant_id = %s AND m.stock_quantity > 0
                ORDER BY total_sales DESC
                LIMIT 4
            """, (restaurant_id,))
            
            popular_items = cursor.fetchall()

            cursor.execute("""
                SELECT code_name, discount_type, discount_value, min_cart_amount 
                FROM promo_codes 
                WHERE restaurant_id = %s AND is_active = 1 
                ORDER BY created_at DESC
            """, (restaurant_id,))
            active_promos = cursor.fetchall()

            cursor.execute("""
                SELECT r.rating, r.comment, r.restaurant_reply, r.created_at, c.name AS customer_name 
                FROM reviews r
                JOIN customers c ON r.customer_id = c.customer_id
                WHERE r.restaurant_id = %s
                ORDER BY r.created_at DESC
            """, (restaurant_id,))
            reviews = cursor.fetchall()

            is_favorited = False
            customer_id = session.get('customer_id')
            if customer_id:
                cursor.execute("""
                    SELECT id FROM favorite_restaurants 
                    WHERE customer_id = %s AND restaurant_id = %s
                """, (customer_id, restaurant_id))
                if cursor.fetchone():
                    is_favorited = True
            
        except Exception as e:
            flash(f"Menü yüklenirken hata oluştu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    if not restaurant:
        flash("Restoran bulunamadı.", "danger")
        return redirect(url_for('index'))

    return render_template('customer_restaurant.html', 
                           restaurant=restaurant, 
                           menu_items=menu_items, 
                           reviews=reviews,
                           grouped_menus=grouped_menus,
                           popular_items=popular_items,
                           is_favorited=is_favorited,
                           active_promos=active_promos)


# 2. SEPETE ÜRÜN EKLEME (SESSION CART)
def add_to_cart():
    if 'logged_in' not in session or session.get('role') != 'customer':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Sepete ürün eklemek için lütfen giriş yapın.'}), 401
        flash("Sepetinize ürün eklemek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    if request.method == 'POST':
        menu_id = request.form.get('menu_id')
        restaurant_id = request.form.get('restaurant_id')
        food_name = request.form.get('food_name')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity', 1))
        item_note = request.form.get('item_note', '').strip()

        # 📍 YENİ: Ön yüzden seçilen ek seçeneklerin ID listesini alıyoruz
        selected_choices = request.form.getlist('choices') 

        # --- GÜVENLİK DUVARI (KAPALI RESTORANA SİPARİŞİ ENGELLE) ---
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT opening_time, closing_time, is_manually_closed FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                res = cursor.fetchone()
                if res:
                    now = datetime.now().time()
                    is_open = True
                    if res.get('is_manually_closed'):
                        is_open = False
                    elif res.get('opening_time') is not None and res.get('closing_time') is not None:
                        op_td = res['opening_time']
                        cl_td = res['closing_time']
                        op_time = (datetime.min + op_td).time() if isinstance(op_td, timedelta) else op_td
                        cl_time = (datetime.min + cl_td).time() if isinstance(cl_td, timedelta) else cl_td
                        
                        if op_time < cl_time:
                            is_open = op_time <= now <= cl_time
                        else:
                            is_open = now >= op_time or now <= cl_time
                            
                    if not is_open:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'message': 'Bu restoran şu an kapalıdır, sepete ürün ekleyemezsiniz.'}), 400
                        flash("Bu restoran şu an kapalıdır, sipariş veremezsiniz.", "danger")
                        return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))
                
                # 📍 YENİ: Seçilen seçeneklerin güncel fiyatlarını backend'de hesaplayıp fiyata ekliyoruz
                extra_price = 0.0
                choice_names = []
                if selected_choices:
                    format_strings = ','.join(['%s'] * len(selected_choices))
                    cursor.execute(f"SELECT choice_name, additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", tuple(selected_choices))
                    choices_res = cursor.fetchall()
                    for cr in choices_res:
                        extra_price += float(cr['additional_price'])
                        choice_names.append(cr['choice_name'])
                
                # Toplam birim fiyatı güncelliyoruz (Taban fiyat + Ekstralar)
                price += extra_price

                # Eğer isimde henüz parantez içi ekstralar yoksa backend'de de isme şıkça iliştiriyoruz
                if choice_names and "(" not in food_name:
                    food_name += f" ({', '.join(choice_names)})"

            finally:
                if connection.is_connected():
                    cursor.close()

        if 'cart' not in session:
            session['cart'] = []

        cart_cleared = False
        if len(session['cart']) > 0 and str(session['cart'][0]['restaurant_id']) != str(restaurant_id):
            session['cart'] = [] 
            cart_cleared = True

        found = False
        for item in session['cart']:
            if str(item['menu_id']) == str(menu_id) and sorted(item.get('choices', [])) == sorted(selected_choices) and item.get('item_note', '') == item_note:
                item['quantity'] += quantity
                found = True
                break

        if not found:
            session['cart'].append({
                'menu_id': menu_id,
                'restaurant_id': restaurant_id,
                'food_name': food_name,
                'price': price,
                'quantity': quantity,
                'choices': selected_choices,
                'item_note': item_note # 📍 YENİ: Notu session'a kaydet
            })

        session.modified = True
        
        total_cart_qty = sum(int(item['quantity']) for item in session['cart'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'total_cart_qty': total_cart_qty,
                'cart_cleared': cart_cleared,
                'message': f"{quantity} adet {food_name} sepete eklendi!"
            })

        if cart_cleared:
            flash("Farklı bir restoran seçtiğiniz için sepetiniz temizlendi.", "warning")
        flash(f"{quantity} adet {food_name} sepete eklendi!", "success")
        return redirect(url_for('view_restaurant', restaurant_id=restaurant_id))
    
def remove_from_cart(menu_id):
    if 'cart' in session:
        # Sepetteki ürünleri tarıyoruz ve sadece SİLİNMEK İSTENMEYEN ürünleri yeni sepette tutuyoruz
        session['cart'] = [item for item in session['cart'] if int(item['menu_id']) != menu_id]
        
        # Session'ı güncellediğimizi Flask'e bildiriyoruz
        session.modified = True 
        flash("Ürün sepetten çıkarıldı.", "success")
        
    # İşlem bitince müşteriyi tekrar sepet ekranına geri gönderiyoruz
    return redirect(url_for('view_cart'))

def increase_cart_item(menu_id):
    if 'cart' in session:
        for item in session['cart']:
            if int(item['menu_id']) == menu_id:
                item['quantity'] = int(item['quantity']) + 1
                break
        session.modified = True
    return redirect(url_for('view_cart'))

def decrease_cart_item(menu_id):
    if 'cart' in session:
        for item in session['cart']:
            if int(item['menu_id']) == menu_id:
                # Ürün miktarının 1'in altına düşmesini engelliyoruz (Silmek için çöp kutusu var)
                if int(item['quantity']) > 1:
                    item['quantity'] = int(item['quantity']) - 1
                break
        session.modified = True
    return redirect(url_for('view_cart'))
    
def view_cart():
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Sepetinizi görmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    customer_id = session.get('customer_id')

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT order_id FROM orders WHERE customer_id = %s AND order_status = 'awaiting_payment'", (customer_id,))
            ghost_orders = cursor.fetchall()
            
            for ghost in ghost_orders:
                g_id = ghost['order_id']
                cursor.execute("DELETE FROM order_item_choices WHERE order_id = %s", (g_id,))
                cursor.execute("DELETE FROM order_items WHERE order_id = %s", (g_id,))
                cursor.execute("DELETE FROM orders WHERE order_id = %s", (g_id,))
            
            connection.commit()
        except Exception as e:
            pass
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    session.pop('current_order_id', None)

    cart = session.get('cart', [])
    total_amount = sum(item['price'] * item['quantity'] for item in cart)
    
    customer_id = session.get('customer_id')
    active_address = None
    min_order_amount = 0.0

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Müşterinin aktif adresini çek
            cursor.execute("""
                SELECT * FROM customer_addresses 
                WHERE customer_id = %s AND is_active = 1
            """, (customer_id,))
            active_address = cursor.fetchone()

            # Restoranın minimum sipariş tutarını çek
            if cart:
                restaurant_id = cart[0]['restaurant_id']
                cursor.execute("SELECT min_order_amount FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                res = cursor.fetchone()
                if res and res.get('min_order_amount'):
                    min_order_amount = float(res['min_order_amount'])

        except Exception as e:
            print(f"Hata: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return render_template('customer_cart.html', cart=cart, total_amount=total_amount, active_address=active_address, min_order_amount=min_order_amount)


def checkout():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return redirect(url_for('customer_login'))

    cart = session.get('cart', [])
    if not cart:
        flash("Sepetiniz boş!", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        order_note = request.form.get('order_note', '') 
        payment_method = request.form.get('payment_method')
        applied_promo_code = request.form.get('applied_promo_code') 
        customer_id = session.get('customer_id')

        restaurant_id = cart[0]['restaurant_id']
        total_qty = sum(item['quantity'] for item in cart)
        total_amount = sum(item['price'] * item['quantity'] for item in cart) 

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)

                cursor.execute("SELECT order_id FROM orders WHERE customer_id = %s AND order_status = 'awaiting_payment'", (customer_id,))
                ghost_orders = cursor.fetchall()
                for ghost in ghost_orders:
                    g_id = ghost['order_id']
                    cursor.execute("DELETE FROM order_item_choices WHERE order_id = %s", (g_id,))
                    cursor.execute("DELETE FROM order_items WHERE order_id = %s", (g_id,))
                    cursor.execute("DELETE FROM orders WHERE order_id = %s", (g_id,))
                
                if applied_promo_code:
                    cursor.execute("SELECT * FROM promo_codes WHERE code_name = %s AND restaurant_id = %s AND is_active = 1", (applied_promo_code, restaurant_id))
                    promo = cursor.fetchone()
                    
                    if promo and total_amount >= float(promo['min_cart_amount']):
                        discount = float(promo['discount_value']) if promo['discount_type'] == 'fixed' else (total_amount * float(promo['discount_value'])) / 100
                        if discount > total_amount: discount = total_amount
                        total_amount -= discount
                        order_note = f"[KUPON KULLANILDI: {applied_promo_code} | İndirim: ₺{discount:.2f}] " + order_note
                
                cursor.execute("SELECT min_order_amount FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                r_data = cursor.fetchone()
                min_order_amount = float(r_data['min_order_amount']) if r_data and r_data.get('min_order_amount') else 0.0

                if total_amount < min_order_amount:
                    flash(f"Minimum sipariş tutarı ₺{min_order_amount}. Lütfen sepetinize ürün ekleyin.", "danger")
                    return redirect(url_for('view_cart'))

                cursor.execute("SELECT * FROM customer_addresses WHERE customer_id = %s AND is_active = 1", (customer_id,))
                active_address = cursor.fetchone()

                if not active_address:
                    flash("Lütfen siparişi tamamlamak için önce bir teslimat adresi seçin.", "danger")
                    return redirect(url_for('index'))

                phone = active_address['contact_phone']
                customer_name = active_address['contact_name']
                
                address_parts = [f"{active_address['neighborhood']} Mh.", f"{active_address['street']} Sk.", f"No:{active_address['building_no']}"]
                if active_address.get('floor_no'): address_parts.append(f"Kat:{active_address['floor_no']}")
                if active_address.get('apt_no'): address_parts.append(f"Daire:{active_address['apt_no']}")
                address_parts.append(f"{active_address['district']}/{active_address['city']}")
                
                address = " ".join(address_parts)
                if active_address.get('directions'):
                    address += f" (Tarif: {active_address['directions']})" 

                insert_order_query = """
                    INSERT INTO orders (
                        restaurant_id, order_status, order_date, sales_qty, 
                        sales_amount, order_type, customer_id, customer_name, customer_phone, customer_address,
                        order_note, payment_method, applied_promo_code
                    )
                    VALUES (%s, %s, NOW(), %s, %s, 'Delivery', %s, %s, %s, %s, %s, %s, %s)
                """
                
                initial_status = 'awaiting_payment' if payment_method == 'Online Payment' else 'pending'

                cursor.execute(insert_order_query, (
                    restaurant_id, initial_status, total_qty, total_amount, customer_id, customer_name, phone, address, order_note, payment_method, applied_promo_code
                ))
                
                new_order_id = cursor.lastrowid 

                # 🚀 1. DEĞİŞİKLİK: FİŞE MÜHÜR VURMA (SNAPSHOT) OPERASYONU BAŞLIYOR 🚀
                for idx, item in enumerate(cart):
                    cart_index = f"c_{idx}_{item['menu_id']}" # Eşsiz bir index yaratıyoruz
                    
                    # Ürünün o anki canlı adını ve fiyatını veritabanından çekiyoruz
                    cursor.execute("""
                        SELECT m.food_id, m.price, COALESCE(m.custom_name, f.item_name) AS item_name
                        FROM menus m
                        JOIN foods f ON m.food_id = f.food_id
                        WHERE m.menu_id = %s
                    """, (item['menu_id'],))
                    menu_data = cursor.fetchone()
                    
                    if menu_data:
                        food_id = menu_data['food_id']
                        item_name = menu_data['item_name']
                        base_price = float(menu_data['price'])
                        
                        extra_price = 0.0
                        choice_details = []
                        
                        # Eğer müşterinin seçtiği ekstralar varsa onların da canlı fiyat/isimlerini alıyoruz
                        if item.get('choices'):
                            format_strings = ','.join(['%s'] * len(item['choices']))
                            cursor.execute(f"SELECT choice_id, choice_name, additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", tuple(item['choices']))
                            choice_details = cursor.fetchall()
                            for ch in choice_details:
                                extra_price += float(ch['additional_price'] or 0.0)
                                
                        unit_price = base_price + extra_price
                        
                        # 1. Mühür (Ana Yemek)
                        cursor.execute("""
                            INSERT INTO order_items (order_id, food_id, menu_id, quantity, unit_price, cart_index, item_note, item_name_snapshot)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (new_order_id, food_id, item['menu_id'], item['quantity'], unit_price, cart_index, item.get('item_note', ''), item_name))

                        # 2. Mühür (Ekstra Seçenekler)
                        if choice_details:
                            for c in choice_details:
                                cursor.execute("""
                                    INSERT INTO order_item_choices (order_id, food_id, choice_id, cart_index, choice_name_snapshot, choice_price_snapshot)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (new_order_id, food_id, c['choice_id'], cart_index, c['choice_name'], float(c['additional_price'] or 0.0)))

                connection.commit()
                
                if payment_method == 'Online Payment':
                    session['current_order_id'] = new_order_id 
                    return redirect(url_for('checkout_payment')) 
                else:
                    session.pop('cart', None) 
                    flash("🎉 Siparişiniz başarıyla alındı! Restoran hazırlanıyor.", "success")
                    return redirect(url_for('index'))

            except Exception as e:
                connection.rollback()
                flash(f"Sipariş işlemi başarısız oldu: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()

    return redirect(url_for('view_cart'))

def customer_orders():
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Siparişlerinizi görmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    customer_id = session.get('customer_id')
    connection = get_db_connection()
    orders_data = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT o.*, r.restaurant_name, r.image_url 
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.customer_id = %s AND o.order_status != 'awaiting_payment'
                ORDER BY o.order_date DESC
            """, (customer_id,))
            orders_list = cursor.fetchall()

            for order in orders_list:
                # 🚀 2. DEĞİŞİKLİK: Artık mühürlü tablodan çekiyoruz (JOIN'leri sildik)
                cursor.execute("""
                    SELECT oi.*, oi.item_name_snapshot AS item_name 
                    FROM order_items oi
                    WHERE oi.order_id = %s
                """, (order['order_id'],))
                order_items_list = cursor.fetchall()
                
                for oi in order_items_list:
                    # Ekstraları da mühürlü tablodan çekiyoruz (Yeni sistemde cart_index kullanarak)
                    if oi.get('cart_index'):
                        cursor.execute("""
                            SELECT choice_name_snapshot AS choice_name 
                            FROM order_item_choices 
                            WHERE order_id = %s AND cart_index = %s
                        """, (order['order_id'], oi['cart_index']))
                    else:
                        # Eski siparişlere geriye dönük uyumluluk (cart_index olmayanlar için)
                        cursor.execute("""
                            SELECT choice_name_snapshot AS choice_name 
                            FROM order_item_choices 
                            WHERE order_id = %s AND food_id = %s
                        """, (order['order_id'], oi['food_id']))
                        
                    choices_data = cursor.fetchall()
                    
                    if choices_data:
                        names = [c['choice_name'] for c in choices_data]
                        current_name = oi['item_name'] if oi['item_name'] else "İsimsiz Menü"
                        oi['item_name'] = f"{current_name} ({', '.join(names)})"
                
                order['items'] = order_items_list
                
                # ... (Altındaki review_data = cursor.fetchone() kısmı aynen kalacak) ...
                cursor.execute("SELECT rating, comment, restaurant_reply FROM reviews WHERE order_id = %s", (order['order_id'],))
                review_data = cursor.fetchone()
                order['review'] = review_data if review_data else None 
                
                orders_data.append(order)

        except Exception as e:
            flash(f"Sipariş geçmişiniz yüklenirken hata oluştu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('customer_orders.html', orders=orders_data)

def set_location():
    if request.method == 'POST':
        data = request.get_json()
        session['latitude'] = data.get('latitude')
        session['longitude'] = data.get('longitude')
        return {"status": "success"}
    
def submit_review():
    if 'customer_id' not in session:
        return redirect(url_for('customer_login'))
        
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        restaurant_id = request.form.get('restaurant_id')
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        customer_id = session.get('customer_id') 
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # 1. Yorumu 'reviews' tablosuna ekle
                insert_query = """
                    INSERT INTO reviews (order_id, restaurant_id, customer_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (order_id, restaurant_id, customer_id, rating, comment))
                
                # 2. Restoranın tüm yorumlarını topla ve ortalamasını hesapla
                calc_query = "SELECT AVG(rating) as avg_rating, COUNT(*) as total_reviews FROM reviews WHERE restaurant_id = %s"
                cursor.execute(calc_query, (restaurant_id,))
                stats = cursor.fetchone()
                
                new_rating = round(stats['avg_rating'], 1) if stats['avg_rating'] else 0
                exact_count = stats['total_reviews']
                
                # --- 🧮 YENİ: DİNAMİK MATEMATİKSEL ALGORİTMA ---
                if exact_count == 0:
                    new_rating_count = 'Yeni'
                elif exact_count < 10:
                    # 10 yoruma kadar tam sayıyı göster (Örn: "5", "8")
                    new_rating_count = str(exact_count)
                else:
                    # 10 ve üzeri için dinamik gruplama (10+, 20+, 100+, 400+ vb.)
                    step = 10 ** (len(str(exact_count)) - 1)
                    bucketed_value = (exact_count // step) * step
                    
                    if bucketed_value >= 1000:
                        new_rating_count = f"{bucketed_value // 1000}K+"
                    else:
                        new_rating_count = f"{bucketed_value}+"
                # ------------------------------------------------------------------------
                
                # 3. Restoranlar tablosunu GÜNCELLE (review_count yerine senin rating_count sütunun kullanılıyor)
                update_query = "UPDATE restaurants SET rating = %s, rating_count = %s WHERE restaurant_id = %s"
                cursor.execute(update_query, (new_rating, new_rating_count, restaurant_id))
                
                connection.commit()
                flash("Değerlendirmeniz başarıyla kaydedildi! 🌟", "success")
                
            except Error as e:
                connection.rollback()
                if "Duplicate entry" in str(e):
                    flash("Bu siparişi zaten değerlendirdiniz.", "warning")
                else:
                    flash(f"Bir hata oluştu: {e}", "danger")
            finally:
                cursor.close()
                connection.close()
                
    return redirect(url_for('customer_orders'))

def get_active_order_status():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return jsonify({'has_active_order': False})

    customer_id = session.get('customer_id')
    connection = get_db_connection()
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # 📍 KESİN ÇÖZÜM: Canlı takip çubuğu sadece süreci devam eden AKTİF siparişleri getirmeli.
            # Teslim edilen (delivered), iptal edilen (canceled) veya ödeme bekleyen siparişler çubuğa asla yansımamalı.
            cursor.execute("""
                SELECT order_id, order_status 
                FROM orders 
                WHERE customer_id = %s 
                  AND order_status IN ('pending', 'preparing', 'ready', 'on_the_way')
                ORDER BY order_id DESC LIMIT 1
            """, (customer_id,))
            order = cursor.fetchone()
            
            if order:
                return jsonify({
                    'has_active_order': True, 
                    'order_status': order['order_status'], 
                    'order_id': order['order_id']
                })
        except Exception as e:
            print(f"Sipariş durumu çekilirken hata: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return jsonify({'has_active_order': False})

def toggle_favorite():
    # Güvenlik: Sadece giriş yapmış müşteriler favoriye ekleyebilir
    if 'logged_in' not in session or session.get('role') != 'customer':
        return jsonify({'success': False, 'message': 'Favorilere eklemek için giriş yapmalısınız.'}), 401

    customer_id = session.get('customer_id')
    
    # AJAX (JavaScript) üzerinden gelen JSON verisini alıyoruz
    data = request.get_json()
    restaurant_id = data.get('restaurant_id')

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 1. Önce kontrol et: Bu restoran zaten müşterinin favorilerinde var mı?
            cursor.execute("""
                SELECT * FROM favorite_restaurants 
                WHERE customer_id = %s AND restaurant_id = %s
            """, (customer_id, restaurant_id))
            exists = cursor.fetchone()

            if exists:
                # 2A. Zaten varsa favorilerden ÇIKAR (Kalp boşalır)
                cursor.execute("""
                    DELETE FROM favorite_restaurants 
                    WHERE customer_id = %s AND restaurant_id = %s
                """, (customer_id, restaurant_id))
                action = 'removed'
            else:
                # 2B. Yoksa favorilere EKLE (Kalp kırmızı olur)
                cursor.execute("""
                    INSERT INTO favorite_restaurants (customer_id, restaurant_id) 
                    VALUES (%s, %s)
                """, (customer_id, restaurant_id))
                action = 'added'

            connection.commit()
            return jsonify({'success': True, 'action': action})
            
        except Exception as e:
            print(f"Favori işlemi hatası: {e}")
            return jsonify({'success': False, 'message': 'Bir hata oluştu.'}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500

def view_favorites():
    # Güvenlik: Sadece giriş yapmış müşteriler görebilir
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Favorilerinizi görmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    customer_id = session.get('customer_id')
    user_lat = session.get('latitude')
    user_lon = session.get('longitude')
    
    connection = get_db_connection()
    favorited_restaurants = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 📍 1. EĞER KONUM VARSA MESAFE (DISTANCE) HESAPLAYARAK ÇEK
            if user_lat and user_lon:
                cursor.execute("""
                    SELECT r.*, 
                           ROUND((6371 * acos(cos(radians(%s)) * cos(radians(r.latitude)) * cos(radians(r.longitude) - radians(%s)) + sin(radians(%s)) * sin(radians(r.latitude)))), 1) AS distance
                    FROM restaurants r
                    JOIN favorite_restaurants fr ON r.restaurant_id = fr.restaurant_id
                    WHERE fr.customer_id = %s
                """, (user_lat, user_lon, user_lat, customer_id))
            else:
                # KONUM YOKSA MESAFESİZ ÇEK
                cursor.execute("""
                    SELECT r.*, 999 AS distance 
                    FROM restaurants r
                    JOIN favorite_restaurants fr ON r.restaurant_id = fr.restaurant_id
                    WHERE fr.customer_id = %s
                """, (customer_id,))
                
            favorited_restaurants = cursor.fetchall()
            
            # 📍 2. RESTORANLARIN AÇIK/KAPALI (IS_OPEN) DURUMLARINI HESAPLA
            now = datetime.now().time()
            for r in favorited_restaurants:
                is_open = True
                if r.get('is_manually_closed'):
                    is_open = False
                elif r.get('opening_time') is not None and r.get('closing_time') is not None:
                    op_td = r['opening_time']
                    cl_td = r['closing_time']
                    op_time = (datetime.min + op_td).time() if isinstance(op_td, timedelta) else op_td
                    cl_time = (datetime.min + cl_td).time() if isinstance(cl_td, timedelta) else cl_td
                    
                    if op_time < cl_time:
                        is_open = op_time <= now <= cl_time
                    else:
                        is_open = now >= op_time or now <= cl_time
                        
                r['is_open'] = is_open
            
        except Exception as e:
            print(f"Favoriler yüklenirken hata oluştu: {e}")
            flash("Favorileriniz yüklenirken bir hata oluştu.", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('customer_favorites.html', restaurants=favorited_restaurants)

def get_addresses():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401
        
    customer_id = session.get('customer_id')
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500
        
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM customer_addresses 
            WHERE customer_id = %s 
            ORDER BY is_active DESC, created_at DESC
        """, (customer_id,))
        addresses = cursor.fetchall()
        return jsonify({'success': True, 'addresses': addresses})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


def add_address():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401
        
    customer_id = session.get('customer_id')
    data = request.get_json()
    
    raw_phone = data.get('contact_phone', '')
    clean_phone = re.sub(r'\D', '', raw_phone) 
    
    if not re.match(r'^05\d{9}$', clean_phone):
        return jsonify({'success': False, 'message': 'Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)'}), 400
        
    data['contact_phone'] = clean_phone 
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500
        
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM customer_addresses WHERE customer_id = %s", (customer_id,))
        is_first = cursor.fetchone()['count'] == 0
        is_active = 1 if is_first else 0
        
        if is_active:
            cursor.execute("UPDATE customer_addresses SET is_active = 0 WHERE customer_id = %s", (customer_id,))

        query = """
            INSERT INTO customer_addresses (
                customer_id, title, city, district, neighborhood, street, 
                building_no, floor_no, apt_no, directions, latitude, longitude, 
                contact_name, contact_phone, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            customer_id, data.get('title'), data.get('city'), data.get('district'),
            data.get('neighborhood'), data.get('street'), data.get('building_no'),
            data.get('floor_no'), data.get('apt_no'), data.get('directions'),
            data.get('latitude'), data.get('longitude'), data.get('contact_name'),
            data.get('contact_phone'), is_active 
        ))
        connection.commit()
        
        if is_active:
            session['latitude'] = data.get('latitude')
            session['longitude'] = data.get('longitude')
            session['customer_city'] = f"{data.get('district')}, {data.get('city')}"
            
        return jsonify({'success': True, 'message': 'Adres başarıyla eklendi!'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


def select_address():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401
        
    customer_id = session.get('customer_id')
    data = request.get_json()
    address_id = data.get('address_id')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500
        
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Tüm adresleri pasif yap
        cursor.execute("UPDATE customer_addresses SET is_active = 0 WHERE customer_id = %s", (customer_id,))
        
        # Seçilen adresi aktif yap
        cursor.execute("UPDATE customer_addresses SET is_active = 1 WHERE address_id = %s AND customer_id = %s", (address_id, customer_id))
        
        # Seçilen adresin koordinatlarını çekip session'a yaz
        cursor.execute("SELECT latitude, longitude, city, district FROM customer_addresses WHERE address_id = %s", (address_id,))
        active_addr = cursor.fetchone()
        
        if active_addr:
            session['latitude'] = float(active_addr['latitude'])
            session['longitude'] = float(active_addr['longitude'])
            session['customer_city'] = f"{active_addr['district']}, {active_addr['city']}"
            
        connection.commit()
        return jsonify({'success': True, 'message': 'Teslimat adresi değiştirildi.'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

def update_address():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401
        
    customer_id = session.get('customer_id')
    data = request.get_json()
    
    raw_phone = data.get('contact_phone', '')
    clean_phone = re.sub(r'\D', '', raw_phone) 
    
    if not re.match(r'^05\d{9}$', clean_phone):
        return jsonify({'success': False, 'message': 'Lütfen geçerli bir cep telefonu numarası girin (Örn: 05xx xxx xx xx)'}), 400
        
    data['contact_phone'] = clean_phone 
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500
        
    try:
        cursor = connection.cursor(dictionary=True)
        
        query = """
            UPDATE customer_addresses SET 
                title = %s, city = %s, district = %s, neighborhood = %s, street = %s, 
                building_no = %s, floor_no = %s, apt_no = %s, directions = %s, 
                latitude = %s, longitude = %s, contact_name = %s, contact_phone = %s
            WHERE address_id = %s AND customer_id = %s
        """
        cursor.execute(query, (
            data.get('title'), data.get('city'), data.get('district'),
            data.get('neighborhood'), data.get('street'), data.get('building_no'),
            data.get('floor_no'), data.get('apt_no'), data.get('directions'),
            data.get('latitude'), data.get('longitude'), data.get('contact_name'),
            data.get('contact_phone'), data.get('address_id'), customer_id
        ))
        connection.commit()
        
        cursor.execute("SELECT is_active FROM customer_addresses WHERE address_id = %s", (data.get('address_id'),))
        res = cursor.fetchone()
        if res and res['is_active']:
            session['latitude'] = data.get('latitude')
            session['longitude'] = data.get('longitude')
            session['customer_city'] = f"{data.get('district')}, {data.get('city')}"
            
        return jsonify({'success': True, 'message': 'Adres başarıyla güncellendi!'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

def cancel_order():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401

    customer_id = session.get('customer_id')
    data = request.get_json()
    order_id = data.get('order_id')

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 1. Sipariş gerçekten bu müşteriye mi ait ve durumu nedir?
            cursor.execute("SELECT order_status FROM orders WHERE order_id = %s AND customer_id = %s", (order_id, customer_id))
            order = cursor.fetchone()

            if order:
                # 2. Sadece beklemede (pending) olan siparişler iptal edilebilir!
                if order['order_status'] == 'pending':
                    cursor.execute("UPDATE orders SET order_status = 'canceled' WHERE order_id = %s", (order_id,))
                    connection.commit()
                    return jsonify({'success': True, 'message': 'Siparişiniz başarıyla iptal edildi.'})
                else:
                    return jsonify({'success': False, 'message': 'Bu sipariş restoran tarafından onaylandığı için artık iptal edilemez.'})
            else:
                return jsonify({'success': False, 'message': 'Sipariş bulunamadı veya yetkiniz yok.'})
                
        except Exception as e:
            connection.rollback()
            return jsonify({'success': False, 'message': f'Hata: {e}'}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500

def apply_promo():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return jsonify({'success': False, 'message': 'Lütfen giriş yapın.'}), 401

    data = request.get_json()
    code_name = data.get('promo_code', '').upper()
    customer_id = session.get('customer_id') # 📍 Müşterinin kimliğini alıyoruz
    
    cart = session.get('cart', [])
    if not cart:
        return jsonify({'success': False, 'message': 'Sepetiniz boş.'}), 400
        
    restaurant_id = cart[0]['restaurant_id']
    total_amount = sum(item['price'] * item['quantity'] for item in cart)
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 📍 YENİ: Müşteri bu kodu daha önce başarıyla kullanmış mı? (İptal edilen siparişler sayılmaz)
            cursor.execute("SELECT order_id FROM orders WHERE customer_id = %s AND applied_promo_code = %s AND order_status != 'canceled'", (customer_id, code_name))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Bu promosyon kodunu daha önce kullandınız!'})

            # Kuponun geçerliliğini kontrol et
            cursor.execute("SELECT * FROM promo_codes WHERE code_name = %s AND restaurant_id = %s", (code_name, restaurant_id))
            promo = cursor.fetchone()
            
            if not promo:
                return jsonify({'success': False, 'message': 'Geçersiz veya bu restorana ait olmayan kupon.'})
            
            if not promo['is_active']:
                return jsonify({'success': False, 'message': 'Bu kuponun süresi dolmuş veya artık pasif.'})
                
            if total_amount < float(promo['min_cart_amount']):
                return jsonify({'success': False, 'message': f"Bu kupon için sepet tutarınız en az ₺{promo['min_cart_amount']} olmalıdır."})
                
            discount_amount = 0
            if promo['discount_type'] == 'fixed':
                discount_amount = float(promo['discount_value'])
            elif promo['discount_type'] == 'percentage':
                discount_amount = (total_amount * float(promo['discount_value'])) / 100
                
            if discount_amount > total_amount:
                discount_amount = total_amount
                
            new_total = total_amount - discount_amount
            
            return jsonify({
                'success': True, 
                'discount_amount': discount_amount,
                'new_total': new_total,
                'message': 'Kupon başarıyla uygulandı!'
            })
        finally:
            cursor.close()
            connection.close()
            
    return jsonify({'success': False, 'message': 'Veritabanı hatası.'}), 500

def api_reorder():
    if 'customer_id' not in session:
        return {"success": False, "message": "Lütfen önce giriş yapın."}, 401

    data = request.get_json()
    order_id = data.get('order_id')
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Geçmiş siparişteki ürünleri buluyoruz
        cursor.execute("""
            SELECT oi.food_id, oi.quantity, oi.cart_index, oi.item_note, 
                   COALESCE(m.custom_name, f.item_name) AS item_name, m.price, m.restaurant_id, m.menu_id
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN foods f ON oi.food_id = f.food_id
            JOIN menus m ON f.food_id = m.food_id AND m.restaurant_id = o.restaurant_id
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cursor.fetchall()

        if not items:
            return {"success": False, "message": "Bu siparişteki ürünler artık menüde bulunmuyor."}, 404

        target_restaurant_id = items[0]['restaurant_id']
        
        new_cart = []
        for item in items:
            food_id = item['food_id']
            menu_id = item['menu_id']
            
            # 🚀 1. DEĞİŞİKLİK: Eski siparişin ID'sini ve Mühürlü İSMİNİ çekiyoruz
            if item.get('cart_index'):
                cursor.execute("""
                    SELECT choice_id, choice_name_snapshot 
                    FROM order_item_choices 
                    WHERE order_id = %s AND cart_index = %s
                """, (order_id, item['cart_index']))
            else:
                cursor.execute("""
                    SELECT choice_id, choice_name_snapshot 
                    FROM order_item_choices 
                    WHERE order_id = %s AND food_id = %s
                """, (order_id, food_id))
                
            old_choices = cursor.fetchall()
            
            choices_list = []
            choices_names = []
            extra_price = 0.0
            
            # 🚀 2. DEĞİŞİKLİK: ZEKİ EŞLEŞTİRME (İsimden Kurtarma)
            for oc in old_choices:
                old_id = oc['choice_id']
                snapshot_name = oc['choice_name_snapshot']
                
                # Güncel menüde; ya eski ID'si tutan YA DA İSMİ TUTAN aktif seçeneği arıyoruz!
                cursor.execute("""
                    SELECT moc.choice_id, moc.choice_name, moc.additional_price 
                    FROM menu_option_choices moc
                    JOIN menu_options mo ON moc.option_id = mo.option_id
                    WHERE mo.menu_id = %s AND (moc.choice_id = %s OR moc.choice_name = %s)
                    LIMIT 1
                """, (menu_id, old_id, snapshot_name))
                
                current_choice = cursor.fetchone()
                
                # Eğer seçenek (yeni ID'siyle veya ismiyle) hala menüdeyse sepete ekle
                if current_choice:
                    choices_list.append(str(current_choice['choice_id']))
                    choices_names.append(current_choice['choice_name'])
                    extra_price += float(current_choice['additional_price'] or 0.0)

            # Ürünün güncel taban fiyatı + ekstraların GÜNCEL fiyatı
            current_total_price = float(item['price']) + extra_price

            # Yemeğin adını sepetteki gibi ekstralarla (Parantez içinde) süslüyoruz
            food_name_with_choices = item['item_name']
            if choices_names:
                food_name_with_choices += f" ({', '.join(choices_names)})"

            new_cart.append({
                'menu_id': menu_id,
                'food_id': food_id,
                'food_name': food_name_with_choices, 
                'price': current_total_price,
                'quantity': item['quantity'],
                'restaurant_id': target_restaurant_id,
                'choices': choices_list,
                'item_note': item.get('item_note') or '' 
            })
            
        session['cart'] = new_cart
        session.modified = True

        return {"success": True, "message": "Siparişiniz, notları ve ek seçenekleriyle birlikte sepete eklendi!"}

    except Exception as e:
        print(f"Reorder Error: {e}")
        return {"success": False, "message": "Sipariş kopyalanırken bir hata oluştu."}, 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def api_restaurant_statuses():
    data = request.get_json()
    restaurant_ids = data.get('restaurant_ids', [])
    
    if not restaurant_ids:
        return jsonify({'success': False, 'statuses': {}})

    connection = get_db_connection()
    statuses = {}
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Gelen ID listesini SQL için formatlıyoruz
            format_strings = ','.join(['%s'] * len(restaurant_ids))
            query = f"SELECT restaurant_id, opening_time, closing_time, is_manually_closed FROM restaurants WHERE restaurant_id IN ({format_strings})"
            cursor.execute(query, tuple(restaurant_ids))
            restaurants = cursor.fetchall()
            
            now = datetime.now().time()
            for r in restaurants:
                is_open = True
                if r.get('is_manually_closed'):
                    is_open = False
                elif r.get('opening_time') is not None and r.get('closing_time') is not None:
                    op_td = r['opening_time']
                    cl_td = r['closing_time']
                    op_time = (datetime.min + op_td).time() if isinstance(op_td, timedelta) else op_td
                    cl_time = (datetime.min + cl_td).time() if isinstance(cl_td, timedelta) else cl_td
                    
                    if op_time < cl_time:
                        is_open = op_time <= now <= cl_time
                    else:
                        is_open = now >= op_time or now <= cl_time
                        
                statuses[str(r['restaurant_id'])] = is_open
                
            return jsonify({'success': True, 'statuses': statuses})
        except Exception as e:
            print(f"Status check error: {e}")
            return jsonify({'success': False, 'message': str(e)})
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'})

def ask_ai():
    import json
    import re
    from datetime import datetime, timedelta
    
    data = request.get_json()
    user_msg = data.get('message', '').strip()

    if not user_msg:
        return jsonify({'success': False, 'message': 'Boş mesaj gönderilemez.'})

    # --- 🧠 1. HAFIZA (MEMORY) YÖNETİMİ ---
    if 'ai_chat_history' not in session:
        session['ai_chat_history'] = []
        
    session['ai_chat_history'].append({"role": "MÜŞTERİ", "content": user_msg})
    session['ai_chat_history'] = session['ai_chat_history'][-8:] # Hafızayı biraz daha uzattık ki adım adım soruları hatırlasın
    
    history_text = "--- SOHBET GEÇMİŞİ (Son Konuşulanlar) ---\n"
    for chat in session['ai_chat_history']:
        history_text += f"{chat['role']}: {chat['content']}\n"

    connection = get_db_connection()
    menu_context = ""

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            user_lat = session.get('latitude')
            user_lon = session.get('longitude')
            
            if user_lat and user_lon:
                cursor.execute("""
                    SELECT m.menu_id, r.restaurant_name, COALESCE(m.custom_name, f.item_name) AS item_name, m.price,
                           (6371 * acos(cos(radians(%s)) * cos(radians(r.latitude)) * cos(radians(r.longitude) - radians(%s)) + sin(radians(%s)) * sin(radians(r.latitude)))) AS distance
                    FROM menus m 
                    JOIN foods f ON m.food_id = f.food_id 
                    JOIN restaurants r ON m.restaurant_id = r.restaurant_id 
                    WHERE r.is_manually_closed = 0 
                      AND m.stock_quantity > 0
                      AND (
                          (r.opening_time <= r.closing_time AND CURTIME() BETWEEN r.opening_time AND r.closing_time)
                          OR 
                          (r.opening_time > r.closing_time AND (CURTIME() >= r.opening_time OR CURTIME() <= r.closing_time))
                      )
                    HAVING distance <= 10
                    ORDER BY distance ASC
                    LIMIT 20
                """, (user_lat, user_lon, user_lat))
            else:
                cursor.execute("""
                    SELECT m.menu_id, r.restaurant_name, COALESCE(m.custom_name, f.item_name) AS item_name, m.price 
                    FROM menus m 
                    JOIN foods f ON m.food_id = f.food_id 
                    JOIN restaurants r ON m.restaurant_id = r.restaurant_id 
                    WHERE r.is_manually_closed = 0 
                      AND m.stock_quantity > 0
                      AND (
                          (r.opening_time <= r.closing_time AND CURTIME() BETWEEN r.opening_time AND r.closing_time)
                          OR 
                          (r.opening_time > r.closing_time AND (CURTIME() >= r.opening_time OR CURTIME() <= r.closing_time))
                      )
                    LIMIT 20
                """)
                
            items = cursor.fetchall()
            
            if items:
                item_dict = {item['menu_id']: item for item in items}
                menu_ids = list(item_dict.keys())
                
                if menu_ids:
                    format_strings = ','.join(['%s'] * len(menu_ids))
                    try:
                        # 🎯 YENİ: Seçeneklerin is_required (zorunlu) ve is_multiple (çoklu) durumlarını da çekiyoruz
                        cursor.execute(f"""
                            SELECT mo.menu_id, mo.option_name, mo.is_required, mo.is_multiple, 
                                   moc.choice_id, moc.choice_name, moc.additional_price
                            FROM menu_options mo
                            JOIN menu_option_choices moc ON mo.option_id = moc.option_id
                            WHERE mo.menu_id IN ({format_strings})
                        """, tuple(menu_ids))
                        options_data = cursor.fetchall()
                        
                        # Seçenekleri yapılandırıyoruz (Zorunlu ve İsteğe Bağlı gruplar olarak)
                        for opt in options_data:
                            m_id = opt['menu_id']
                            opt_name = opt['option_name']
                            req_str = "ZORUNLU" if opt['is_required'] else "İSTEĞE BAĞLI"
                            mult_str = "Çoklu" if opt['is_multiple'] else "Tekli"
                            
                            if 'options_grouped' not in item_dict[m_id]:
                                item_dict[m_id]['options_grouped'] = {}
                                
                            if opt_name not in item_dict[m_id]['options_grouped']:
                                item_dict[m_id]['options_grouped'][opt_name] = {'type': f"{req_str}, {mult_str}", 'choices': []}
                            
                            price_str = f"(+₺{opt['additional_price']})" if float(opt['additional_price']) > 0 else ""
                            item_dict[m_id]['options_grouped'][opt_name]['choices'].append(f"[ID:{opt['choice_id']}] {opt['choice_name']} {price_str}")
                    except Exception as e:
                        print("Seçenekler Çekilemedi:", e)

                menu_context = "--- SİPARİŞ VERİLEBİLECEK ÜRÜNLER VE SEÇENEKLERİ ---\n"
                for item in items:
                    menu_context += f"[Ürün ID: {item['menu_id']}] {item['restaurant_name']} - {item['item_name']} (₺{item['price']})\n"
                    if 'options_grouped' in item:
                        for opt_name, opt_details in item['options_grouped'].items():
                            choices_str = ", ".join(opt_details['choices'])
                            menu_context += f"   -> {opt_name} ({opt_details['type']}): {choices_str}\n"
            else:
                menu_context = "ŞU AN AÇIK HİÇBİR RESTORAN YOK."
                
        except Exception as e:
            print("DB Hatası:", e)
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # --- 🤖 3. SYSTEM PROMPT (Kusursuz Ajan Kuralları) ---
    system_prompt = f"""
    Sen 'YeSende' uygulamasının aktif ve yetkili Dijital Garsonusun. 
    
    {menu_context}
    
    {history_text}
    
    DİKKAT! SİPARİŞ ALMA AKIŞI (Bu kurallara harfiyen uy!):
    Müşteri bir ürün sipariş etmek istediğinde hemen JSON DÖNDÜRME! Önce şu 3 ADIMI kontrol et:
    
    ADIM 1 (ZORUNLU SEÇENEKLER): Müşterinin istediği ürünün "ZORUNLU" olarak belirtilmiş ekstra seçenekleri var mı? Varsa ve müşteri mesajında bunları belirtmediyse, nazikçe bu zorunlu seçenekleri sor. 
    HAYATİ KURAL: "ZORUNLU" seçenekler ASLA es geçilemez veya boş bırakılamaz! Müşteri zorunlu bir seçeneği reddederse ("istemiyorum", "gerek yok" vb.), işlemin tamamlanması için seçimin şart olduğunu belirt. Eğer müşteri ısrarla reddetmeye devam eder veya sinirlenirse ("allah allah", "yeter" vb.), siparişi İPTAL ET ve "Anlıyorum ancak restoran kuralları gereği bu ürünü bu seçim yapılmadan hazırlayamıyoruz. Dilerseniz size başka bir ürün önerebilirim?" diyerek konuyu kibarca kapat. Asla pes edip zorunlu seçeneği boş bırakarak JSON döndürme!
    
    ADIM 2 (İSTEĞE BAĞLI SEÇENEKLER VE NOT): Zorunlu seçenekler eksiksiz tamamlandıysa, üründe "İSTEĞE BAĞLI" seçenekler varsa onları teklif et VE "Eklemek istediğiniz özel bir sipariş notunuz var mı?" diye sor.
    
    ADIM 3 (FİNAL ONAYI VE JSON): Eğer tüm "ZORUNLU" seçimler yapıldıysa ve not/isteğe bağlı kısımlar da sorulup cevaplandıysa (veya müşteri başta hepsini tek bir mesajda yazdıysa), İŞTE SADECE O ZAMAN metin cevabını bırakıp aşağıdaki JSON formatını döndür:
    
    {{
      "action": "add_to_cart", 
      "menu_id": <URUN_ID>, 
      "quantity": <ADET>, 
      "choices": [<MUSTERININ_SECIMLERINE_AIT_ID_NUMARALARI_LISTESI>], 
      "note": "<MUSTERININ_BELIRTTIGI_NOT_VEYA_BOS_BIRAK>"
    }}
    
    ÖNEMLİ: 
    - JSON döndürürken başına veya sonuna ASLA metin yazma.
    - Müşteri sadece sohbet ediyorsa JSON kullanma, normal cevap ver.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_prompt
        )
        
        response_text = response.text.strip()
        
        json_match = re.search(r'\{.*"action"\s*:\s*"add_to_cart".*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                action_data = json.loads(json_match.group(0))
                m_id = action_data.get('menu_id')
                qty = int(action_data.get('quantity', 1))
                choices = action_data.get('choices', [])
                if not isinstance(choices, list): choices = []
                note = str(action_data.get('note', '')).strip()
                if not note:
                    note = "Yapay Zeka Asistanı Ekledi 🤖"
                
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT m.menu_id, m.restaurant_id, m.price, COALESCE(m.custom_name, f.item_name) AS food_name FROM menus m JOIN foods f ON m.food_id = f.food_id WHERE m.menu_id = %s", (m_id,))
                item = cursor.fetchone()
                
                if item:
                    extra_price = 0.0
                    choice_names = []
                    if choices:
                        format_strings = ','.join(['%s'] * len(choices))
                        cursor.execute(f"SELECT choice_name, additional_price FROM menu_option_choices WHERE choice_id IN ({format_strings})", tuple(choices))
                        choices_res = cursor.fetchall()
                        for cr in choices_res:
                            extra_price += float(cr['additional_price'])
                            choice_names.append(cr['choice_name'])
                    
                    base_price = float(item['price'])
                    total_unit_price = base_price + extra_price
                    
                    food_name = item['food_name']
                    if choice_names and "(" not in food_name:
                        food_name += f" ({', '.join(choice_names)})"

                    if 'cart' not in session: session['cart'] = []
                    
                    cart_cleared = False
                    if len(session['cart']) > 0 and str(session['cart'][0]['restaurant_id']) != str(item['restaurant_id']):
                        session['cart'] = [] 
                        cart_cleared = True
                        
                    found = False
                    for c_item in session['cart']:
                        if str(c_item['menu_id']) == str(m_id) and sorted(c_item.get('choices', [])) == sorted(choices) and c_item.get('item_note', '') == note:
                            c_item['quantity'] += qty
                            found = True
                            break
                            
                    if not found:
                        session['cart'].append({
                            'menu_id': item['menu_id'],
                            'restaurant_id': item['restaurant_id'],
                            'food_name': food_name,
                            'price': total_unit_price,
                            'quantity': qty,
                            'choices': choices,
                            'item_note': note
                        })
                    session.modified = True
                    
                    success_msg = f"Talebiniz üzerine **{qty} adet {food_name}** sepetinize eklendi! Başka bir arzunuz var mı? 😋"
                    if cart_cleared:
                        success_msg += "\n*(Farklı bir restorandan ürün seçtiğiniz için önceki sepetiniz temizlendi.)*"
                        
                    session['ai_chat_history'].append({"role": "ASİSTAN", "content": success_msg})
                    session.modified = True
                    
                    cursor.close()
                    conn.close()
                    
                    return jsonify({'success': True, 'response': success_msg, 'action_taken': 'cart_updated'})
                    
            except Exception as e:
                print("Aksiyon Yakalama Hatası:", e)
        
        session['ai_chat_history'].append({"role": "ASİSTAN", "content": response_text})
        session.modified = True
        
        return jsonify({
            'success': True, 
            'response': response_text
        })
        
    except Exception as e:
        print("Gemini İletişim Hatası:", e)
        error_text = 'Şu an mutfakta biraz yoğunum, lütfen birazdan tekrar dener misin? 🧑‍🍳'
        return jsonify({'success': False, 'response': error_text, 'message': error_text})
    
def api_get_courier_location():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'success': False, 'message': 'Sipariş ID eksik'})

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # DİKKAT: "WHERE o.order_status = 'on_the_way'" şartını kaldırdık ve "o.order_status" sütununu ekledik
            cursor.execute("""
                SELECT c.current_lat, c.current_lon, c.name, 
                       r.restaurant_name, r.latitude AS rest_lat, r.longitude AS rest_lon,
                       o.order_status
                FROM orders o
                JOIN couriers c ON o.courier_id = c.courier_id
                JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.order_id = %s
            """, (order_id,))
            courier = cursor.fetchone()

            if courier:
                return jsonify({
                    'success': True, 
                    'lat': float(courier['current_lat']) if courier['current_lat'] else None, 
                    'lon': float(courier['current_lon']) if courier['current_lon'] else None,
                    'name': courier['name'],
                    'rest_name': courier['restaurant_name'],
                    'rest_lat': float(courier['rest_lat']) if courier['rest_lat'] else None,
                    'rest_lon': float(courier['rest_lon']) if courier['rest_lon'] else None,
                    'cust_lat': float(session.get('latitude')) if session.get('latitude') else None,
                    'cust_lon': float(session.get('longitude')) if session.get('longitude') else None,
                    'order_status': courier['order_status'] # 🟢 YENİ: Siparişin o anki durumunu gönderiyoruz
                })
            else:
                return jsonify({'success': False, 'message': 'Kurye veya sipariş bulunamadı'})
                
        except Exception as e:
            print("Kurye Konum Çekme Hatası:", e)
            return jsonify({'success': False})
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return jsonify({'success': False})