from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection

# 1. RESTORAN MENÜSÜNÜ GÖRÜNTÜLEME
def view_restaurant(restaurant_id):
    if 'logged_in' not in session or session.get('role') != 'customer':
        flash("Please login to view restaurants.", "danger")
        return redirect(url_for('customer_login'))

    connection = get_db_connection()
    restaurant = None
    menu_items = []

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
            
        except Exception as e:
            flash(f"Error loading menu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('index'))

    return render_template('customer_restaurant.html', restaurant=restaurant, menu_items=menu_items)


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
                        sales_amount, order_type, customer_name, customer_phone, customer_address
                    )
                    VALUES (%s, 'pending', NOW(), %s, %s, 'Delivery', %s, %s, %s)
                """
                cursor.execute(insert_order_query, (
                    restaurant_id, total_qty, total_amount, customer_name, phone, address
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