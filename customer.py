from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash
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
    reviews = [] # Yorumları tutacağımız yeni listemiz

    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # 1. Restoran Bilgilerini Çek
            cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
            restaurant = cursor.fetchone()

            # 2. Menüleri Foods (Yemekler) tablosuyla birleştirerek (JOIN) çek!
            cursor.execute("""
                SELECT m.*, f.item_name AS food_name, f.veg_or_non_veg 
                FROM menus m
                JOIN foods f ON m.food_id = f.food_id
                WHERE m.restaurant_id = %s AND m.stock_quantity > 0
            """, (restaurant_id,))
            menu_items = cursor.fetchall()
            
            # 3. YENİ AŞAMA: Bu restorana ait yorumları ve müşteri isimlerini çek!
            cursor.execute("""
                SELECT r.rating, r.comment, r.created_at, c.name AS customer_name 
                FROM reviews r
                JOIN customers c ON r.customer_id = c.customer_id
                WHERE r.restaurant_id = %s
                ORDER BY r.created_at DESC
            """, (restaurant_id,))
            reviews = cursor.fetchall()
            
        except Exception as e:
            flash(f"Error loading menu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('index'))

    # 'reviews=reviews' kısmını HTML'e göndermek için ekledik
    return render_template('customer_restaurant.html', restaurant=restaurant, menu_items=menu_items, reviews=reviews)


# 2. SEPETE ÜRÜN EKLEME (SESSION CART)
def add_to_cart():
    if 'logged_in' not in session or session.get('role') != 'customer':
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

        # Eğer sepette ürün varsa ve farklı restorandan ürün eklenmeye çalışılıyorsa sepeti temizle
        if len(session['cart']) > 0 and str(session['cart'][0]['restaurant_id']) != str(restaurant_id):
            session['cart'] = [] 
            flash("Your cart was cleared because you selected a different restaurant.", "warning")

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
    
    return render_template('customer_cart.html', cart=cart, total_amount=total_amount)

# 4. SİPARİŞİ TAMAMLAMA (CHECKOUT)
def checkout():
    if 'logged_in' not in session or session.get('role') != 'customer':
        return redirect(url_for('customer_login'))

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        phone = request.form.get('phone')
        address = request.form.get('address')
        customer_id = session.get('customer_id')

        # Sepetteki toplam tutar ve miktarı hesapla
        restaurant_id = cart[0]['restaurant_id']
        total_qty = sum(item['quantity'] for item in cart)
        total_amount = sum(item['price'] * item['quantity'] for item in cart)

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # Müşterinin adını alıyoruz
                cursor.execute("SELECT name FROM customers WHERE customer_id = %s", (customer_id,))
                customer = cursor.fetchone()
                customer_name = customer['name'] if customer else 'Unknown Customer'

                # 1. AŞAMA: Siparişi ana "orders" tablosuna kaydet
                insert_order_query = """
                    INSERT INTO orders (
                        restaurant_id, order_status, order_date, sales_qty, 
                        sales_amount, order_type, customer_id, customer_name, customer_phone, customer_address
                    )
                    VALUES (%s, 'pending', NOW(), %s, %s, 'Delivery', %s, %s, %s, %s)
                """
                cursor.execute(insert_order_query, (
                    restaurant_id, total_qty, total_amount, customer_id, customer_name, phone, address
                ))
                
                new_order_id = cursor.lastrowid # Yeni oluşan Siparişin ID'si

                # 2. AŞAMA: Sepetteki her bir ürünü "order_items" tablosuna ekle
                for item in cart:
                    # Tablomuz food_id istiyor. Önce menu_id üzerinden food_id'yi bulalım:
                    cursor.execute("SELECT food_id FROM menus WHERE menu_id = %s", (item['menu_id'],))
                    menu_data = cursor.fetchone()
                    
                    if menu_data:
                        food_id = menu_data['food_id']
                        # Şimdi alt detayları order_items tablosuna yazıyoruz
                        cursor.execute("""
                            INSERT INTO order_items (order_id, food_id, quantity, unit_price)
                            VALUES (%s, %s, %s, %s)
                        """, (new_order_id, food_id, item['quantity'], item['price']))

                # 3. AŞAMA (Opsiyonel): Müşteri tablosundaki telefon ve adresi güncelle (Gelecek sefere kolaylık)
                cursor.execute("UPDATE customers SET phone = %s, address = %s WHERE customer_id = %s AND phone IS NULL", (phone, address, customer_id))

                connection.commit()
                
                # İşlem bitti, sepeti temizle
                session.pop('cart', None) 
                flash("🎉 Order placed successfully! The restaurant has received your order.", "success")
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