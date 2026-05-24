from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error

# 1. RESTORAN MENÜSÜNÜ GÖRÜNTÜLEME
def view_restaurant(restaurant_id):
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Please login to view restaurants.", "danger")
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
        flash("Restaurant not found.", "danger")
        return redirect(url_for('index'))

    return render_template('customer_restaurant.html', 
                           restaurant=restaurant, 
                           menu_items=menu_items, 
                           reviews=reviews,
                           grouped_menus=grouped_menus,
                           popular_items=popular_items,
                           is_favorited=is_favorited)


# 2. SEPETE ÜRÜN EKLEME (SESSION CART)
def add_to_cart():
    if 'logged_in' not in session or session.get('role') != 'customer':
        # AJAX isteği ise JSON hata dön, değilse normal redirect yap
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Please login to add items.'}), 401
        flash("Please login to add items to your cart.", "danger")
        return redirect(url_for('customer_login'))

    if request.method == 'POST':
        menu_id = request.form.get('menu_id')
        restaurant_id = request.form.get('restaurant_id')
        food_name = request.form.get('food_name')
        price = float(request.form.get('price'))
        quantity = int(request.form.get('quantity', 1))

        if 'cart' not in session:
            session['cart'] = []

        # Eğer sepette ürün varsa ve farklı restorandan ekleniyorsa sepeti temizle
        cart_cleared = False
        if len(session['cart']) > 0 and str(session['cart'][0]['restaurant_id']) != str(restaurant_id):
            session['cart'] = [] 
            cart_cleared = True

        found = False
        for item in session['cart']:
            if str(item['menu_id']) == str(menu_id):
                item['quantity'] += quantity
                found = True
                break

        if not found:
            session['cart'].append({
                'menu_id': menu_id,
                'restaurant_id': restaurant_id,
                'food_name': food_name,
                'price': price,
                'quantity': quantity
            })

        session.modified = True
        
        # Toplam sepet ürün sayısını hesapla
        total_cart_qty = sum(int(item['quantity']) for item in session['cart'])

        # --- YENİ EKLENEN AJAX (JSON) KONTROLÜ ---
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True, 
                'total_cart_qty': total_cart_qty,
                'cart_cleared': cart_cleared,
                'message': f"Added {quantity}x {food_name} to cart!"
            })
        # ----------------------------------------

        # Normal (Eski usul) form gönderimi ise:
        if cart_cleared:
            flash("Your cart was cleared because you selected a different restaurant.", "warning")
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
        flash("Please login to view your cart.", "danger")
        return redirect(url_for('customer_login'))

    cart = session.get('cart', [])
    total_amount = sum(item['price'] * item['quantity'] for item in cart)
    
    # YENİ: Müşterinin aktif (is_active=1) adresini veritabanından çek ve HTML'e gönder
    customer_id = session.get('customer_id')
    active_address = None
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM customer_addresses 
                WHERE customer_id = %s AND is_active = 1
            """, (customer_id,))
            active_address = cursor.fetchone()
        except Exception as e:
            print(f"Aktif adres yüklenirken hata: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return render_template('customer_cart.html', cart=cart, total_amount=total_amount, active_address=active_address)

# 4. SİPARİŞİ TAMAMLAMA (CHECKOUT)
def checkout():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return redirect(url_for('customer_login'))

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        order_note = request.form.get('order_note', '') 
        payment_method = request.form.get('payment_method')
        customer_id = session.get('customer_id')

        # Sepetteki toplam tutar ve miktarı hesapla
        restaurant_id = cart[0]['restaurant_id']
        total_qty = sum(item['quantity'] for item in cart)
        total_amount = sum(item['price'] * item['quantity'] for item in cart)

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # YENİ: Telefon ve Adres formdan değil, doğrudan aktif adresten çekiliyor!
                cursor.execute("""
                    SELECT * FROM customer_addresses 
                    WHERE customer_id = %s AND is_active = 1
                """, (customer_id,))
                active_address = cursor.fetchone()

                if not active_address:
                    flash("Lütfen siparişi tamamlamak için önce bir teslimat adresi seçin.", "danger")
                    return redirect(url_for('index'))

                phone = active_address['contact_phone']
                customer_name = active_address['contact_name']
                
                # Adresi formatlı bir metne çeviriyoruz
                address_parts = [f"{active_address['neighborhood']} Mh.", f"{active_address['street']} Sk.", f"No:{active_address['building_no']}"]
                if active_address.get('floor_no'): address_parts.append(f"Kat:{active_address['floor_no']}")
                if active_address.get('apt_no'): address_parts.append(f"Daire:{active_address['apt_no']}")
                address_parts.append(f"{active_address['district']}/{active_address['city']}")
                
                address = " ".join(address_parts)
                if active_address.get('directions'):
                    address += f" (Tarif: {active_address['directions']})"

                # 1. AŞAMA: Siparişi ana "orders" tablosuna kaydet
                insert_order_query = """
                    INSERT INTO orders (
                        restaurant_id, order_status, order_date, sales_qty, 
                        sales_amount, order_type, customer_id, customer_name, customer_phone, customer_address,
                        order_note, payment_method
                    )
                    VALUES (%s, 'pending', NOW(), %s, %s, 'Delivery', %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_order_query, (
                    restaurant_id, total_qty, total_amount, customer_id, customer_name, phone, address, order_note, payment_method
                ))
                
                new_order_id = cursor.lastrowid # Yeni oluşan Siparişin ID'si

                # 2. AŞAMA: Sepetteki her bir ürünü "order_items" tablosuna ekle
                for item in cart:
                    cursor.execute("SELECT food_id FROM menus WHERE menu_id = %s", (item['menu_id'],))
                    menu_data = cursor.fetchone()
                    
                    if menu_data:
                        food_id = menu_data['food_id']
                        cursor.execute("""
                            INSERT INTO order_items (order_id, food_id, quantity, unit_price)
                            VALUES (%s, %s, %s, %s)
                        """, (new_order_id, food_id, item['quantity'], item['price']))

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
        flash("Please login to view your orders.", "danger")
        return redirect(url_for('customer_login'))

    customer_id = session.get('customer_id')
    connection = get_db_connection()
    orders_data = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # 1. Aşama: Müşterinin tüm siparişlerini restoran isimleriyle çek
            cursor.execute("""
                SELECT o.*, r.restaurant_name 
                FROM orders o
                JOIN restaurants r ON o.restaurant_id = r.restaurant_id
                WHERE o.customer_id = %s
                ORDER BY o.order_date DESC
            """, (customer_id,))
            orders_list = cursor.fetchall()

            # 2. Aşama: Her bir siparişin iç detaylarını (yemekler) ve YORUMUNU çek!
            for order in orders_list:
                # Siparişe ait yemekleri (items) çekiyoruz
                cursor.execute("""
                    SELECT oi.*, f.item_name 
                    FROM order_items oi
                    JOIN foods f ON oi.food_id = f.food_id
                    WHERE oi.order_id = %s
                """, (order['order_id'],))
                order['items'] = cursor.fetchall()
                
                # --- YENİ EKLENEN KISIM: Bu sipariş için daha önce yorum yapılmış mı? ---
                cursor.execute("""
                    SELECT rating, comment FROM reviews WHERE order_id = %s
                """, (order['order_id'],))
                review_data = cursor.fetchone()
                
                if review_data:
                    order['review'] = review_data # Yorum varsa siparişin içine 'review' anahtarıyla ekle
                else:
                    order['review'] = None # Yorum yoksa None olarak işaretle
                # -----------------------------------------------------------------------
                
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
                
                # --- YENİ KISIM: Senin ENUM yapına göre sayıyı metne dönüştürüyoruz ---
                if exact_count >= 1000:
                    new_rating_count = '1K+ ratings'
                elif exact_count >= 500:
                    new_rating_count = '500+ ratings'
                elif exact_count >= 100:
                    new_rating_count = '100+ ratings'
                elif exact_count >= 50:
                    new_rating_count = '50+ ratings'
                elif exact_count >= 20:
                    new_rating_count = '20+ ratings'
                else:
                    new_rating_count = 'Too Few Ratings'
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
    connection = get_db_connection()
    favorited_restaurants = []

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Müşterinin favori tablosundaki restoran id'leri ile restoran detaylarını birleştirip çekiyoruz
            cursor.execute("""
                SELECT r.* FROM restaurants r
                JOIN favorite_restaurants fr ON r.restaurant_id = fr.restaurant_id
                WHERE fr.customer_id = %s
            """, (customer_id,))
            favorited_restaurants = cursor.fetchall()
            
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