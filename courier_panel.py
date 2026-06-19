from werkzeug.security import check_password_hash
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection

def courier_dashboard(courier_id):
    logged_in_courier_id = session.get('courier_id')
    
    if not logged_in_courier_id:
        flash("Lütfen paneli görüntülemek için giriş yapın.", "warning")
        return redirect(url_for('login')) 
        
    if int(logged_in_courier_id) != int(courier_id):
        flash("Yetkisiz erişim! Sadece kendi panelinizi görüntüleyebilirsiniz.", "danger")
        return redirect(url_for('courier_dashboard', courier_id=logged_in_courier_id))
    
    connection = get_db_connection()
    active_orders = []
    courier_name = "Courier"
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT name, is_online FROM couriers WHERE courier_id = %s", (courier_id,))
            courier = cursor.fetchone()
            is_online = True
            if courier:
                courier_name = courier['name']
                is_online = courier.get('is_online', True)
            
            cursor.execute("""
                SELECT order_id, order_date, customer_name, customer_phone, customer_address, sales_amount, order_status, payment_method, order_note 
                FROM orders 
                WHERE courier_id = %s AND order_status IN ('ready', 'on_the_way')
                ORDER BY order_date DESC
            """, (courier_id,))
            active_orders = cursor.fetchall()
            
            for order in active_orders:
                cursor.execute("""
                    SELECT quantity, item_name_snapshot AS item_name, cart_index, food_id
                    FROM order_items 
                    WHERE order_id = %s
                """, (order['order_id'],))
                items = cursor.fetchall()
                
                for item in items:
                    if item.get('cart_index'):
                        cursor.execute("SELECT choice_name_snapshot AS choice_name FROM order_item_choices WHERE order_id = %s AND cart_index = %s", (order['order_id'], item['cart_index']))
                    else:
                        cursor.execute("SELECT choice_name_snapshot AS choice_name FROM order_item_choices WHERE order_id = %s AND food_id = %s", (order['order_id'], item['food_id']))
                        
                    choices = cursor.fetchall()
                    if choices:
                        names = [c['choice_name'] for c in choices]
                        current_name = item['item_name'] if item['item_name'] else "İsimsiz Menü"
                        item['item_name'] = f"{current_name} ({', '.join(names)})"
                        
                order['products'] = items

            cursor.execute("""
                SELECT payment_method, sales_amount 
                FROM orders 
                WHERE courier_id = %s AND order_status = 'delivered' AND DATE(order_date) = CURDATE()
            """, (courier_id,))
            todays_delivered = cursor.fetchall()
            
            daily_stats = {
                'total_packages': len(todays_delivered),
                'cash_total': sum(float(o['sales_amount']) for o in todays_delivered if o['payment_method'] == 'Cash'),
                'online_total': sum(float(o['sales_amount']) for o in todays_delivered if o['payment_method'] in ['Online Payment', 'Credit Card'])
            }
            
        except Exception as e:
            flash(f"Panel yüklenirken hata oluştu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('courier_dashboard.html', orders=active_orders, courier_name=courier_name, courier_id=courier_id, daily_stats=daily_stats, is_online=is_online)

def update_delivery_status():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('new_status')
        courier_id = request.form.get('courier_id')
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("UPDATE orders SET order_status = %s WHERE order_id = %s", (new_status, order_id))
                connection.commit()
                flash("Sipariş durumu başarıyla güncellendi!", "success")
            except Exception as e:
                connection.rollback()
                flash(f"Durum güncellenirken hata oluştu: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return redirect(url_for('courier_dashboard', courier_id=courier_id))
    
def api_update_courier_location():
    courier_id = session.get('courier_id')
    if not courier_id:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})

    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    if lat is None or lon is None:
        return jsonify({'success': False, 'message': 'Koordinat bilgisi eksik'})

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE couriers 
                SET current_lat = %s, current_lon = %s 
                WHERE courier_id = %s
            """, (lat, lon, courier_id))
            connection.commit()
            return jsonify({'success': True})
        except Exception as e:
            print("Konum Güncelleme Hatası:", e)
            return jsonify({'success': False, 'message': str(e)})
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası'})

def api_toggle_courier_status():
    courier_id = session.get('courier_id')
    if not courier_id:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'})
        
    data = request.get_json(silent=True) or {}
    new_status = data.get('is_online')
    
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE couriers SET is_online = %s WHERE courier_id = %s", (new_status, courier_id))
            connection.commit()
            return jsonify({'success': True, 'is_online': new_status})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    return jsonify({'success': False, 'message': 'Veritabanı bağlantı hatası'})