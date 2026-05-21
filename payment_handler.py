from db import get_db_connection
from flask import render_template, request, redirect, url_for, session, flash
import iyzipay
from iyzico_config import get_iyzipay_options
import json

def checkout_payment():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        session['phone'] = request.form.get('phone')
        session['address'] = request.form.get('address')
        
    # 2. Gerçek Sepet Tutarını Hesapla (Sabit 150 TL'yi kaldırıyoruz)
    cart = session.get('cart', [])
    if not cart:
        flash("Sepetiniz boş!", "warning")
        return redirect(url_for('index'))
        
    # Sepetteki tüm ürünlerin fiyat * miktar toplamını alıyoruz
    total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart)
    total_price = str(total_amount) # İyzico tutarı metin (string) olarak bekler 

    request_data = {
        'locale': 'tr',
        'conversationId': '123456789',
        'price': total_price,
        'paidPrice': total_price,
        'currency': 'TRY',
        'basketId': 'B67832',
        'paymentGroup': 'PRODUCT',
        'callbackUrl': url_for('payment_callback', _external=True),
        'enabledInstallments': ['2', '3', '6', '9'],
        'buyer': {
            'id': 'BY789',
            'name': 'John',
            'surname': 'Doe',
            'gsmNumber': '+905350000000',
            'email': 'email@email.com',
            'identityNumber': '74300864791',
            'lastLoginDate': '2015-10-05 12:43:35',
            'registrationDate': '2013-04-21 15:12:09',
            'registrationAddress': 'Nidakule Göztepe, Merdivenköy Mah. Bora Sok. No:1',
            'ip': '85.34.78.112',
            'city': 'Istanbul',
            'country': 'Turkey',
            'zipCode': '34732'
        },
        'shippingAddress': {
            'contactName': 'Jane Doe',
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Nidakule Göztepe, Merdivenköy Mah. Bora Sok. No:1',
            'zipCode': '34732'
        },
        'billingAddress': {
            'contactName': 'Jane Doe',
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Nidakule Göztepe, Merdivenköy Mah. Bora Sok. No:1',
            'zipCode': '34732'
        },
        'basketItems': [
            {
                'id': 'BI101',
                'name': 'Yemek Sepeti Siparişi',
                'category1': 'Food',
                'itemType': 'PHYSICAL',
                'price': total_price
            }
        ]
    }

    options = get_iyzipay_options()
    checkout_form_initialize = iyzipay.CheckoutFormInitialize().create(request_data, options)

    response = checkout_form_initialize.read().decode('utf-8')
    response_json = json.loads(response)

    if response_json.get('status') == 'success':
        form_content = response_json.get('checkoutFormContent')
        return render_template('payment.html', form_content=form_content)
    else:
        flash(f"Ödeme sistemi başlatılamadı: {response_json.get('errorMessage')}", "danger")
        return redirect(url_for('orders'))

def payment_callback():
    token = request.form.get('token')
    
    if not token:
        flash("Geçersiz ödeme isteği!", "danger")
        return redirect(url_for('index'))

    request_data = {
        'locale': 'tr',
        'conversationId': '123456789',
        'token': token
    }
    
    options = get_iyzipay_options()
    checkout_form_result = iyzipay.CheckoutForm().retrieve(request_data, options)
    
    response_json = json.loads(checkout_form_result.read().decode('utf-8'))

    # ÖDEME BAŞARILIYSA
    if response_json.get('paymentStatus') == 'SUCCESS':
        cart = session.get('cart', [])
        
        if not cart:
            flash("Ödeme başarılı ancak sepet boş bulundu!", "warning")
            return redirect(url_for('my_orders'))

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                customer_id = session.get('customer_id') or session.get('user_id') or session.get('id')
                
                # Toplam miktar ve tutarı hesapla
                total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart)
                total_qty = sum(int(item['quantity']) for item in cart)
                
                restaurant_id = cart[0].get('restaurant_id') 
                customer_phone = session.get('phone', 'Kayıtlı Değil')
                customer_address = session.get('address', 'Müşteri Adresi')

                # 2. Ana Siparişi (orders) Veritabanına Yaz (Sütun adını customer_id yaptık)
                query = """
                    INSERT INTO orders 
                    (customer_id, restaurant_id, order_date, order_status, sales_qty, sales_amount, 
                     order_type, customer_phone, customer_address)
                    VALUES (%s, %s, NOW(), 'Pending', %s, %s, 'Delivery', %s, %s)
                """
                cursor.execute(query, (customer_id, restaurant_id, total_qty, total_amount, customer_phone, customer_address))
                order_id = cursor.lastrowid 

                # 3. Sipariş Detaylarını Yaz (Daha önce düzelttiğimiz çalışan kısım)
                # 3. Sipariş Detaylarını Yaz 
                for item in cart:
                    menu_id = item['menu_id']
                    
                    cursor.execute("SELECT food_id FROM menus WHERE menu_id = %s", (menu_id,))
                    menu_record = cursor.fetchone()
                    
                    if not menu_record:
                        raise Exception(f"Menüde {menu_id} ID'li bir kayıt bulunamadı!")
                        
                    real_food_id = menu_record['food_id']

                    item_query = "INSERT INTO order_items (order_id, food_id, quantity, unit_price) VALUES (%s, %s, %s, %s)"
                    cursor.execute(item_query, (order_id, real_food_id, item['quantity'], item['price']))
                    
                    # İŞTE DÜZELTTİĞİMİZ KISIM BURASI (stock_query olarak değiştirdim)
                    stock_query = "UPDATE menus SET stock_quantity = stock_quantity - %s WHERE menu_id = %s"
                    cursor.execute(stock_query, (item['quantity'], menu_id))

                # Her şey hatasızsa veritabanına kaydet
                connection.commit()
                
                # 4. Müşterinin Sepetini Temizle
                session.pop('cart', None)
                
                flash("Ödemeniz başarıyla alındı! Siparişiniz restoranın ekranına düştü. 🍕", "success")
                return redirect(url_for('customer_orders'))
                
            except Exception as e:
                connection.rollback()
                print(f"!!! KRİTİK SİPARİŞ KAYIT HATASI: {e} !!!")
                flash("Ödeme alındı ancak sipariş oluşturulurken sistemde bir hata yaşandı.", "danger")
                return redirect(url_for('index'))
            finally:
                cursor.close()
                connection.close()

        flash("Ödemeniz başarıyla alındı! Siparişiniz restoranın ekranına düştü. 🍕", "success")
        return redirect(url_for('customer_orders'))
        
    # ÖDEME BAŞARISIZSA
    else:
        flash("Ödeme başarısız oldu. Lütfen tekrar deneyin.", "danger")
        return redirect(url_for('index'))