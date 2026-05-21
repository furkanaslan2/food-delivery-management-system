from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection

def courier_dashboard(courier_id):
    # İleride buraya kurye login kontrolü (session) eklenebilir.
    
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
            
            # Kuryeye atanmış ve Aktif olan (Hazırlanıyor veya Yolda) siparişleri çek
            cursor.execute("""
                SELECT order_id, order_date, customer_name, customer_phone, customer_address, sales_amount, order_status 
                FROM orders 
                WHERE courier_id = %s AND order_status IN ('preparing', 'on_the_way')
                ORDER BY order_date ASC
            """, (courier_id,))
            active_orders = cursor.fetchall()
            
        except Exception as e:
            flash(f"Error loading dashboard: {e}", "danger")
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
                flash("Order status updated successfully! 🛵", "success")
            except Exception as e:
                connection.rollback()
                flash(f"Failed to update status: {e}", "danger")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return redirect(url_for('courier_dashboard', courier_id=courier_id))