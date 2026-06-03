from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 1. RESTORAN MENÜSÜNÜ GÖRÜNTÜLEME
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
                SELECT r.rating, r.comment, r.created_at, c.name AS customer_name 
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
            flash(f"Error loading menu: {e}", "danger")
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
            return jsonify({'success': False, 'message': 'Please login to add items.'}), 401
        flash("Sepetinize ürün eklemek için lütfen giriş yapın.", "danger")
        return redirect(url_for('customer_login'))

    if request.method == 'POST':
        menu_id = request.form.get('menu_id')
        restaurant_id = request.form.get('restaurant_id')
        food_name = request.form.get('food_name')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity', 1))

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

        # Aynı ürün ve aynı ekstra konfigürasyonuna sahip mi kontrolü
        found = False
        for item in session['cart']:
            if str(item['menu_id']) == str(menu_id) and sorted(item.get('choices', [])) == sorted(selected_choices):
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
                'choices': selected_choices # 📍 Seçim ID'leri session sepetine kaydoluyor
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
        flash(f"Added {quantity}x {food_name} to cart!", "success")
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

            # YENİ: Restoranın minimum sipariş tutarını çek
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
        total_amount = sum(item['price'] * item['quantity'] for item in cart) # Fiyat artık ekstralı!

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                if applied_promo_code:
                    cursor.execute("SELECT * FROM promo_codes WHERE code_name = %s AND restaurant_id = %s AND is_active = 1", (applied_promo_code, restaurant_id))
                    promo = cursor.fetchone()
                    
                    if promo and total_amount >= float(promo['min_cart_amount']):
                        discount = float(promo['discount_value']) if promo['discount_type'] == 'fixed' else (total_amount * float(promo['discount_value'])) / 100
                        if discount > total_amount: discount = total_amount
                        total_amount -= discount
                        order_note = f"[KUPON KULLANILDI: {applied_promo_code} | İndirim: ${discount:.2f}] " + order_note
                
                cursor.execute("SELECT min_order_amount FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                r_data = cursor.fetchone()
                min_order_amount = float(r_data['min_order_amount']) if r_data and r_data.get('min_order_amount') else 0.0

                if total_amount < min_order_amount:
                    flash(f"Minimum sipariş tutarı ${min_order_amount}. Lütfen sepetinize ürün ekleyin.", "danger")
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
                    VALUES (%s, 'pending', NOW(), %s, %s, 'Delivery', %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_order_query, (
                    restaurant_id, total_qty, total_amount, customer_id, customer_name, phone, address, order_note, payment_method, applied_promo_code
                ))
                
                new_order_id = cursor.lastrowid 

                # Sepetteki ürünleri order_items tablosuna ekle
                for item in cart:
                    cursor.execute("SELECT food_id FROM menus WHERE menu_id = %s", (item['menu_id'],))
                    menu_data = cursor.fetchone()
                    
                    if menu_data:
                        food_id = menu_data['food_id']
                        # unit_price artık ekstralar eklenmiş nihai fiyattır
                        cursor.execute("""
                            INSERT INTO order_items (order_id, food_id, quantity, unit_price)
                            VALUES (%s, %s, %s, %s)
                        """, (new_order_id, food_id, item['quantity'], item['price']))

                        # 📍 YENİ: Sipariş onaylandığı an ek seçenek tercihleri ilişki tablosuna tek tek yazılıyor
                        if item.get('choices'):
                            for choice_id in item['choices']:
                                cursor.execute("""
                                    INSERT INTO order_item_choices (order_id, food_id, choice_id)
                                    VALUES (%s, %s, %s)
                                """, (new_order_id, food_id, choice_id))

                connection.commit()
                
                if payment_method == 'Online Payment':
                    return redirect(url_for('checkout_payment')) 
                else:
                    session.pop('cart', None) 
                    flash("🎉 Siparişiniz başarıyla alındı! Restoran hazırlanıyor.", "success")
                    return redirect(url_for('index'))

            except Exception as e:
                connection.rollback()
                flash(f"Checkout failed: {e}", "danger")
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
                SELECT o.*, r.restaurant_name 
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.customer_id = %s
                ORDER BY o.order_date DESC
            """, (customer_id,))
            orders_list = cursor.fetchall()

            for order in orders_list:
                cursor.execute("""
                    SELECT oi.*, COALESCE(m.custom_name, f.item_name) AS item_name 
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    JOIN foods f ON oi.food_id = f.food_id
                    LEFT JOIN menus m ON oi.food_id = m.food_id AND o.restaurant_id = m.restaurant_id
                    WHERE oi.order_id = %s
                """, (order['order_id'],))
                order_items_list = cursor.fetchall()
                
                # 📍 YENİ: Geçmiş sipariş satırlarındaki yemeklerin ekstralarını bulup isme parantezle ekliyoruz
                for oi in order_items_list:
                    cursor.execute("""
                        SELECT moc.choice_name 
                        FROM order_item_choices oic
                        JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                        WHERE oic.order_id = %s AND oic.food_id = %s
                    """, (order['order_id'], oi['food_id']))
                    choices_data = cursor.fetchall()
                    
                    if choices_data:
                        names = [c['choice_name'] for c in choices_data]
                        oi['item_name'] += f" ({', '.join(names)})" # "Pizza (Ekstra Peynir, İnce Hamur)" formatı
                
                order['items'] = order_items_list
                
                cursor.execute("""
                    SELECT rating, comment FROM reviews WHERE order_id = %s
                """, (order['order_id'],))
                review_data = cursor.fetchone()
                
                if review_data:
                    order['review'] = review_data 
                else:
                    order['review'] = None 
                
                orders_data.append(order)

        except Exception as e:
            flash(f"Error loading your orders: {e}", "danger")
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
            # YENİ SQL: Aktif siparişleri her zaman getir. 
            # Teslim/İptal durumlarını ise SADECE sipariş son 2 saat içinde verildiyse getir.
            cursor.execute("""
                SELECT order_id, order_status 
                FROM orders 
                WHERE customer_id = %s 
                  AND (
                      order_status IN ('pending', 'preparing', 'on_the_way') 
                      OR order_date >= NOW() - INTERVAL 2 HOUR
                  )
                ORDER BY order_date DESC LIMIT 1
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
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası.'}), 500
        
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Eğer bu müşterinin ilk adresiyse otomatik aktif (is_active=True) yapalım
        cursor.execute("SELECT COUNT(*) as count FROM customer_addresses WHERE customer_id = %s", (customer_id,))
        is_first = cursor.fetchone()['count'] == 0
        is_active = 1 if is_first else 0
        
        # Eğer yeni adres aktif olacaksa, eski aktif adresleri pasif yap
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
        
        # Eğer aktif adres olarak kaydedildiyse session'ı da güncelle ki ana ekran anında yenilensin
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
        
        # Eğer düzenlenen adres şu an "seçili/aktif" adres ise, session'ı da (10 KM filtresi için) güncelle!
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
                return jsonify({'success': False, 'message': f"Bu kupon için sepet tutarınız en az ${promo['min_cart_amount']} olmalıdır."})
                
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
            SELECT oi.food_id, oi.quantity, f.item_name, m.price, m.restaurant_id, m.menu_id
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
        
        # Müşterinin sepetini yeni siparişle doldur
        new_cart = []
        for item in items:
            food_id = item['food_id']
            
            # 📍 GÜNCELLEME 1: Geçmiş seçimlerin ID'leri ile birlikte İSİMLERİNİ (choice_name) de çekiyoruz
            cursor.execute("""
                SELECT oic.choice_id, moc.choice_name 
                FROM order_item_choices oic
                JOIN menu_option_choices moc ON oic.choice_id = moc.choice_id
                WHERE oic.order_id = %s AND oic.food_id = %s
            """, (order_id, food_id))
            choices_data = cursor.fetchall()
            
            choices_list = [str(c['choice_id']) for c in choices_data]
            choices_names = [c['choice_name'] for c in choices_data] # İsimleri listeye aldık
            
            extra_price = 0.0
            # Eğer ekstra seçim varsa, güncel fiyatlarını topla
            if choices_list:
                format_strings = ','.join(['%s'] * len(choices_list))
                cursor.execute(f"""
                    SELECT SUM(additional_price) as total_extra 
                    FROM menu_option_choices 
                    WHERE choice_id IN ({format_strings})
                """, tuple(choices_list))
                extra_res = cursor.fetchone()
                if extra_res and extra_res['total_extra']:
                    extra_price = float(extra_res['total_extra'])

            # Ürünün güncel taban fiyatı + ekstraların güncel fiyatı
            current_total_price = float(item['price']) + extra_price

            # 📍 GÜNCELLEME 2: Senin parantezli isim formatını sıfırdan inşa ediyoruz!
            food_name_with_choices = item['item_name']
            if choices_names:
                # Eğer ekstralar varsa sonuna ekliyoruz: "Yemek Adı (Ekstra 1, Ekstra 2)"
                food_name_with_choices += f" ({', '.join(choices_names)})"

            new_cart.append({
                'menu_id': item['menu_id'],
                'food_id': food_id,
                'food_name': food_name_with_choices, # 📍 Artık sepete parantezli hali gidiyor!
                'price': current_total_price,
                'quantity': item['quantity'],
                'restaurant_id': target_restaurant_id,
                'choices': choices_list
            })
            
        session['cart'] = new_cart
        session.modified = True

        return {"success": True, "message": "Ürünler sepete eklendi!"}

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
    data = request.get_json()
    user_msg = data.get('message', '').strip()

    if not user_msg:
        return jsonify({'success': False, 'message': 'Boş mesaj gönderilemez.'})

    connection = get_db_connection()
    menu_context = ""
    history_context = "Müşterinin henüz geçmiş siparişi bulunmuyor."

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 📍 GÜNCELLEME 1: Müşterinin konumunu alıyoruz (10 KM filtresi için)
            user_lat = session.get('latitude')
            user_lon = session.get('longitude')
            
            if user_lat and user_lon:
                # Müşterinin konumuna SADECE 10 KM ve daha yakın olan AÇIK restoranları getir
                cursor.execute("""
                    SELECT r.restaurant_name, f.item_name, m.price,
                           (6371 * acos(cos(radians(%s)) * cos(radians(r.latitude)) * cos(radians(r.longitude) - radians(%s)) + sin(radians(%s)) * sin(radians(r.latitude)))) AS distance
                    FROM menus m 
                    JOIN foods f ON m.food_id = f.food_id 
                    JOIN restaurants r ON m.restaurant_id = r.restaurant_id 
                    WHERE r.is_manually_closed = 0 
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
                # Konum seçilmemişse sadece açık restoranları getir
                cursor.execute("""
                    SELECT r.restaurant_name, f.item_name, m.price 
                    FROM menus m 
                    JOIN foods f ON m.food_id = f.food_id 
                    JOIN restaurants r ON m.restaurant_id = r.restaurant_id 
                    WHERE r.is_manually_closed = 0 
                      AND (
                          (r.opening_time <= r.closing_time AND CURTIME() BETWEEN r.opening_time AND r.closing_time)
                          OR 
                          (r.opening_time > r.closing_time AND (CURTIME() >= r.opening_time OR CURTIME() <= r.closing_time))
                      )
                    LIMIT 20
                """)
                
            items = cursor.fetchall()
            
            if items:
                menu_context = "AÇIK VE SİPARİŞ VERİLEBİLECEK RESTORANLAR:\n"
                for item in items:
                    menu_context += f"- {item['restaurant_name']} ({item['item_name']}, {item['price']} TL)\n"
            else:
                menu_context = "ŞU AN AÇIK HİÇBİR RESTORAN YOK."
            
            # Geçmiş Siparişleri Çek
            if session.get('logged_in') and session.get('role') == 'customer':
                customer_id = session.get('customer_id')
                cursor.execute("""
                    SELECT r.restaurant_name, f.item_name 
                    FROM orders o
                    JOIN order_items oi ON o.order_id = oi.order_id
                    JOIN foods f ON oi.food_id = f.food_id
                    JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                    WHERE o.customer_id = %s AND o.order_status != 'canceled'
                    ORDER BY o.order_id DESC
                    LIMIT 5
                """, (customer_id,))
                past_orders = cursor.fetchall()
                
                if past_orders:
                    history_context = "Müşterinin son siparişleri:\n"
                    for po in past_orders:
                        history_context += f"- {po['restaurant_name']} restoranından {po['item_name']}\n"
                    
        except Exception as e:
            print("DB Hatası:", e)
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    # 📍 GÜNCELLEME 2: PEMBE FİL SENDROMUNU ÇÖZEN YENİ PROMPT
    # Uydurmasını istemediğimiz markaların isimlerini komuttan sildik. Artık aklına bile gelmeyecek.
    system_prompt = f"""
    Sen 'DeliveryApp' uygulamasının Gurme Asistanısın. Müşteriye yemek önerileri yapıyorsun.
    Müşterinin mesajı: "{user_msg}"
    
    {menu_context}
    
    {history_context}
    
    KESİN KURALLAR (HAYATİ ÖNEM TAŞIR):
    1. SADECE yukarıda sana verilen listedeki restoranları önerebilirsin.
    2. Eğer sana "ŞU AN AÇIK HİÇBİR RESTORAN YOK." bilgisi geldiyse, hiçbir yer ismi kullanmadan "Şu an çevrende açık bir restoran bulamadım. 😔" demelisin.
    3. Sistemde kayıtlı olmayan hiçbir markayı metne dahil etme. Asla veritabanı dışından isim kullanma.
    4. Samimi ve kısa bir dille cevap ver (Maksimum 3-4 cümle).
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_prompt
        )
        return jsonify({
            'success': True, 
            'response': response.text
        })
        
    except Exception as e:
        print("Gemini Hatası:", e)
        return jsonify({'success': False, 'response': 'Şu an mutfakta biraz yoğunum, lütfen birazdan tekrar dener misin? 🧑‍🍳'})
    
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