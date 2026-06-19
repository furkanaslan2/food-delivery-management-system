from db import get_db_connection
from flask import render_template, request, redirect, url_for, session, flash
import iyzipay
from iyzico_config import get_iyzipay_options
import json

def checkout_payment():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    cart = session.get('cart', [])
    if not cart:
        flash("Sepetiniz boş!", "warning")
        return redirect(url_for('index'))
        
    total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart)
    total_price = str(total_amount)

    # 📍 SİHİRLİ DOKUNUŞ 1: Sipariş ID'sini alıyoruz
    order_id = session.get('current_order_id')

    request_data = {
        'locale': 'tr',
        'conversationId': str(order_id) if order_id else '123456789',
        'price': total_price,
        'paidPrice': total_price,
        'currency': 'TRY',
        'basketId': str(order_id) if order_id else 'B67832',
        'paymentGroup': 'PRODUCT',
        
        # 🚀 KRİTİK ÇÖZÜM 1: order_id'yi URL'in sonuna açıkça ekliyoruz ki tarayıcı çerezleri silse bile kaybolmasın!
        'callbackUrl': url_for('payment_callback', order_id=order_id, _external=True),
        
        'enabledInstallments': ['2', '3', '6', '9'],
        'buyer': {
            'id': str(session.get('customer_id', 'BY789')),
            'name': 'Müşteri',
            'surname': 'Test',
            'gsmNumber': '+905350000000',
            'email': 'email@email.com',
            'identityNumber': '74300864791',
            'lastLoginDate': '2015-10-05 12:43:35',
            'registrationDate': '2013-04-21 15:12:09',
            'registrationAddress': 'Nidakule Göztepe',
            'ip': '85.34.78.112',
            'city': 'Istanbul',
            'country': 'Turkey',
            'zipCode': '34732'
        },
        'shippingAddress': {
            'contactName': 'Müşteri',
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Nidakule Göztepe',
            'zipCode': '34732'
        },
        'billingAddress': {
            'contactName': 'Müşteri',
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Nidakule Göztepe',
            'zipCode': '34732'
        },
        'basketItems': [
            {
                'id': 'BI101',
                'name': 'Yemek Siparişi',
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
        return redirect(url_for('customer_orders'))

def payment_callback():
    token = request.form.get('token')
    
    # 🚀 KRİTİK ÇÖZÜM 2: Artık session'a muhtaç değiliz, URL'den yakalıyoruz!
    order_id = request.args.get('order_id')
    
    if not token or not order_id:
        flash("Geçersiz ödeme isteği veya sipariş bilgisi bulunamadı!", "danger")
        return redirect(url_for('index'))

    request_data = {
        'locale': 'tr',
        'conversationId': str(order_id),
        'token': token
    }
    
    options = get_iyzipay_options()
    checkout_form_result = iyzipay.CheckoutForm().retrieve(request_data, options)
    response_json = json.loads(checkout_form_result.read().decode('utf-8'))

    # 🟢 ÖDEME BAŞARILIYSA
    if response_json.get('paymentStatus') == 'SUCCESS':
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # 1. Siparişin durumunu nihayet Onay Bekliyor (pending) olarak güncelle!
                cursor.execute("UPDATE orders SET order_status = 'pending' WHERE order_id = %s", (order_id,))
                
                # 2. Stok Düşme İşlemi: Çerezler (sepet) gizlendiği için veritabanındaki kayıtlı sipariş satırlarını okuyoruz
                cursor.execute("""
                    SELECT oi.food_id, oi.quantity, o.restaurant_id 
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    WHERE oi.order_id = %s
                """, (order_id,))
                ordered_items = cursor.fetchall()

                for item in ordered_items:
                    cursor.execute("""
                        UPDATE menus 
                        SET stock_quantity = stock_quantity - %s 
                        WHERE food_id = %s AND restaurant_id = %s
                    """, (item['quantity'], item['food_id'], item['restaurant_id']))

                connection.commit()
                
                session.pop('cart', None)
                session.pop('current_order_id', None)
                
                flash("Ödemeniz başarıyla alındı! Siparişiniz restoranın ekranına düştü. <i class='ph-bold ph-pizza'></i>", "success")
                return redirect(url_for('customer_orders'))
                
            except Exception as e:
                connection.rollback()
                flash("Ödeme alındı ancak sipariş güncellenirken hata oluştu.", "danger")
                return redirect(url_for('index'))
            finally:
                cursor.close()
                connection.close()

        return redirect(url_for('customer_orders'))
        
    # 🔴 ÖDEME BAŞARISIZSA VEYA İPTAL EDİLDİYSE
    else:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            # Ödeme başarısızsa havada kalan siparişi İptal (canceled) yap
            cursor.execute("UPDATE orders SET order_status = 'canceled' WHERE order_id = %s", (order_id,))
            connection.commit()
            cursor.close()
            connection.close()
            
        flash("Ödeme başarısız oldu veya tarafınızca iptal edildi.", "danger")
        return redirect(url_for('index'))