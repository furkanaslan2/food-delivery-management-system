from werkzeug.security import check_password_hash
from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection

def courier_dashboard(courier_id):
    logged_in_courier_id = session.get('courier_id')
    
    # 1. Kontrol: Session'da courier_id yoksa login'e at
    if not logged_in_courier_id:
        flash("Lütfen paneli görüntülemek için giriş yapın.", "warning")
        return redirect(url_for('login')) 
        
    # 2. Kontrol: Session'daki ID ile URL'deki ID eşleşmiyorsa kendi paneline geri fırlat
    if int(logged_in_courier_id) != int(courier_id):
        flash("Yetkisiz erişim! Sadece kendi panelinizi görüntüleyebilirsiniz.", "danger")
        return redirect(url_for('courier_dashboard', courier_id=logged_in_courier_id))
    
    connection = get_db_connection()
    active_orders = []
    courier_name = "Courier"
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Kuryenin adını çek
            cursor.execute("SELECT name FROM couriers WHERE courier_id = %s", (courier_id,))
            courier = cursor.fetchone()
            if courier:
                courier_name = courier['name']
            
            cursor.execute("""
                SELECT order_id, order_date, customer_name, customer_phone, customer_address, sales_amount, order_status, payment_method, order_note 
                FROM orders 
                WHERE courier_id = %s AND order_status IN ('ready', 'on_the_way')
                ORDER BY order_date DESC
            """, (courier_id,))
            active_orders = cursor.fetchall()
            
        except Exception as e:
            flash(f"Panel yüklenirken hata oluştu: {e}", "danger")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    return render_template('courier_dashboard.html', orders=active_orders, courier_name=courier_name, courier_id=courier_id)

def update_delivery_status():
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('new_status')
        courier_id = request.form.get('courier_id')
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                # Siparişin durumunu ("Yolda" veya "Teslim Edildi" olarak) güncelle
                cursor.execute("UPDATE orders SET order_status = %s WHERE order_id = %s", (new_status, order_id))
                connection.commit()
                flash("Sipariş durumu başarıyla güncellendi! 🛵", "success")
            except Exception as e:
                connection.rollback()
                flash(f"Durum güncellenirken hata oluştu: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return redirect(url_for('courier_dashboard', courier_id=courier_id))
    
def api_update_courier_location():
    # Sadece giriş yapmış kuryeler konum gönderebilir
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
            # Kuryenin güncel konumunu veritabanına yazıyoruz
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