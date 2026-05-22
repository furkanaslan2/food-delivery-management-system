from werkzeug.security import check_password_hash
from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection

def courier_dashboard(courier_id):
    logged_in_courier_id = session.get('courier_id')
    
    # 1. Kontrol: Session'da courier_id yoksa login'e at
    if not logged_in_courier_id:
        flash("Lütfen paneli görüntülemek için giriş yapın.", "warning")
        return redirect(url_for('courier_login'))
        
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
            
            # Kuryeye atanmış ve Aktif olan (Hazırlanıyor veya Yolda) siparişleri çek
            cursor.execute("""
                SELECT order_id, order_date, customer_name, customer_phone, customer_address, sales_amount, order_status 
                FROM orders 
                WHERE courier_id = %s AND order_status IN ('preparing', 'on_the_way')
                ORDER BY order_date DESC
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
    
def courier_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                
                # 1. Adım: Sadece e-posta ile kuryeyi veritabanından çekiyoruz
                cursor.execute("SELECT * FROM couriers WHERE email = %s", (email,))
                courier = cursor.fetchone()
                
                # 2. Adım: Kurye bulunduysa, girilen şifreyi veritabanındaki HASH ile karşılaştırıyoruz
                if courier and check_password_hash(courier['password'], password):
                    # Giriş başarılı!
                    session['courier_id'] = courier['courier_id']
                    session['courier_name'] = courier['name']
                    return redirect(url_for('courier_dashboard', courier_id=courier['courier_id']))
                else:
                    flash("Invalid email or password! Please try again.", "danger")
                    
            except Exception as e:
                print(f"Login error: {e}")
                flash("An error occurred during login.", "danger")
            finally:
                cursor.close()
                connection.close()
                
    # GET isteği gelirse sadece HTML formunu göster
    return render_template('courier_login.html')

def courier_logout():
    # Kuryeye ait session verilerini hafızadan temizliyoruz
    session.pop('courier_id', None)
    session.pop('courier_name', None)
    
    flash("Başarıyla çıkış yaptınız. İyi dinlenmeler! 🛵", "success")
    return redirect(url_for('courier_login'))