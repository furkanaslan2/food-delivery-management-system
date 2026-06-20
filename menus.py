from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename
from PIL import Image

def menus():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('menus.html', menus=[], foods=[]) 

    try:
        cursor = connection.cursor(dictionary=True)
        restaurant_categories = [] # 🚀 YENİ: Hata almamak için boş tanımlıyoruz
        
        if role == 'admin':
            cursor.execute('''
                SELECT m.menu_id, m.restaurant_id, m.food_id, m.category_id, m.custom_name, m.price, m.stock_quantity, m.image_url,
                       f.item_name as food_name, f.category as global_category, r.restaurant_name, rc.category_name
                FROM menus m 
                LEFT JOIN foods f ON m.food_id = f.food_id
                LEFT JOIN restaurants r ON m.restaurant_id = r.restaurant_id
                LEFT JOIN restaurant_categories rc ON m.category_id = rc.category_id
            ''')
            menus = cursor.fetchall()
        elif role == 'user' and restaurant_id:
            # 🚀 YENİ: Restoranın kendi özel kategorilerini çekiyoruz
            cursor.execute("SELECT * FROM restaurant_categories WHERE restaurant_id = %s ORDER BY sort_order ASC", (restaurant_id,))
            restaurant_categories = cursor.fetchall()

            # 🚀 YENİ: Menüleri çekerken özel kategorisiyle (rc.category_name) birlikte çekiyoruz
            cursor.execute('''
                SELECT m.menu_id, m.restaurant_id, m.food_id, m.category_id, m.custom_name, m.price, m.stock_quantity, m.image_url,
                       f.item_name as food_name, f.category as global_category, rc.category_name
                FROM menus m 
                LEFT JOIN foods f ON m.food_id = f.food_id
                LEFT JOIN restaurant_categories rc ON m.category_id = rc.category_id
                WHERE m.restaurant_id = %s
            ''', (restaurant_id,))
            menus = cursor.fetchall()
        else:
            flash("Yetkisiz erişim!", "danger")
            return redirect(url_for('index'))

        cursor.execute("SELECT food_id, item_name, category FROM foods ORDER BY category ASC, item_name ASC")
        foods = cursor.fetchall()

    except Error as e:
        flash(f"Sorgu hatası: {e}", "danger")
        menus = []
        foods = []
        restaurant_categories = []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    # 🚀 YENİ: HTML'e 'restaurant_categories' listesini de gönderiyoruz
    return render_template('menus.html', menus=menus, foods=foods, restaurant_categories=restaurant_categories)

def menus_action():
    if 'logged_in' not in session:
        return redirect(url_for('menus'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('menus'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            food_id = request.form.get('food_id')
            custom_name = request.form.get('custom_name')
            category_id = request.form.get('category_id') or None 
            price = request.form.get('price')
            stock_quantity = request.form.get('stock_quantity')
            restaurant_id = request.form.get('restaurant_id')
            menu_id = request.form.get('menu_id')
            
            image_file = request.files.get('menu_image') 
            image_url = None

            if not stock_quantity:
                stock_quantity = 0

            missing_fields = []
            if not food_id: missing_fields.append('Ana Ürün Tipi (Kategori)')
            if not custom_name: missing_fields.append('Menüdeki Özel Adı')
            if not price: missing_fields.append('Fiyat')
            if not restaurant_id: missing_fields.append('Restoran ID')

            if missing_fields:
                flash(f"Lütfen şu alanları doldurun: {', '.join(missing_fields)}", "warning")
                return redirect(url_for('menus'))

            try:
                if image_file and image_file.filename != '':
                    ext = image_file.filename.rsplit('.', 1)[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        flash("Hata: Sadece JPG, PNG ve WEBP formatları yüklenebilir!", "danger")
                        return redirect(url_for('menus'))

                    filename = secure_filename(image_file.filename)
                    upload_folder = os.path.join('static', 'images', 'menus')
                    os.makedirs(upload_folder, exist_ok=True) 
                    file_path = os.path.join(upload_folder, filename)
                    
                    img = Image.open(image_file)
                    img.thumbnail((600, 600)) 
                    if img.mode != 'RGB' and ext != 'png':
                        img = img.convert('RGB')
                    img.save(file_path, optimize=True, quality=80)
                    
                    image_url = filename

                cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                if cursor.fetchone()['count'] == 0:
                    flash('Geçersiz Restoran ID!', 'danger')
                    return redirect(url_for('menus'))

                if menu_id:
                    cursor.execute("SELECT menu_id FROM menus WHERE menu_id = %s", (menu_id,))
                    if cursor.fetchone():
                        flash("Bu Menü ID zaten kullanılıyor. Lütfen farklı bir ID girin veya boş bırakın.", "warning")
                        return redirect(url_for('menus'))
                    
                    query = """
                        INSERT INTO menus (menu_id, restaurant_id, food_id, category_id, custom_name, price, stock_quantity, image_url) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (menu_id, restaurant_id, food_id, category_id, custom_name, price, stock_quantity, image_url))
                    inserted_menu_id = menu_id
                else:
                    query = """
                        INSERT INTO menus (restaurant_id, food_id, category_id, custom_name, price, stock_quantity, image_url) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (restaurant_id, food_id, category_id, custom_name, price, stock_quantity, image_url))
                    inserted_menu_id = cursor.lastrowid

                # 🛠️ YENİ EKLENEN: DİNAMİK OPSİYONLARI YAKALA VE VERİTABANINA KAYDET
                option_names = request.form.getlist('option_names[]')
                
                for i, opt_name in enumerate(option_names):
                    if not opt_name.strip():
                        continue # Boş grup adlarını atla
                        
                    # Checkbox değerlerini al (İşaretliyse 1, değilse 0)
                    is_required = 1 if request.form.get(f'is_required_{i}') else 0
                    is_multiple = 1 if request.form.get(f'is_multiple_{i}') else 0
                    
                    # 1. Aşama: Opsiyon Grubunu Ekle (Örn: Ekstra Peynir)
                    cursor.execute("""
                        INSERT INTO menu_options (menu_id, option_name, is_required, is_multiple) 
                        VALUES (%s, %s, %s, %s)
                    """, (inserted_menu_id, opt_name, is_required, is_multiple))
                    
                    option_id = cursor.lastrowid # Oluşan grubun ID'sini al
                    
                    # 2. Aşama: Bu Gruba Ait Şıkları Ekle (Örn: Kaşar, Cheddar)
                    choice_names = request.form.getlist(f'choice_names_{i}[]')
                    additional_prices = request.form.getlist(f'additional_prices_{i}[]')
                    
                    for j, choice_name in enumerate(choice_names):
                        if not choice_name.strip():
                            continue
                        
                        add_price = additional_prices[j] if j < len(additional_prices) and additional_prices[j] else 0
                        
                        cursor.execute("""
                            INSERT INTO menu_option_choices (option_id, choice_name, additional_price) 
                            VALUES (%s, %s, %s)
                        """, (option_id, choice_name, add_price))

                # Tüm işlemler bittikten sonra veritabanına kaydet
                connection.commit()
                flash("Menü ve seçenekler başarıyla eklendi!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Menü eklenirken hata: {str(e)}", "danger")

        elif action == 'delete':
            selected_ids = request.form.get('selected_menu_items')
            
            if not selected_ids:
                flash("Silmek için hiçbir menü seçilmedi.", "warning")
                return redirect(url_for('menus'))

            try:
                selected_ids = selected_ids.split(',')
                
                if role == 'user':
                    query = """
                        DELETE FROM menus 
                        WHERE menu_id IN ({}) 
                        AND restaurant_id = %s
                    """.format(','.join(['%s'] * len(selected_ids)))
                    params = selected_ids + [restaurant_id_session]
                else:
                    query = """
                        DELETE FROM menus 
                        WHERE menu_id IN ({})
                    """.format(','.join(['%s'] * len(selected_ids)))
                    params = selected_ids

                cursor.execute(query, params)
                connection.commit()
                
                if cursor.rowcount > 0:
                    flash(f"{cursor.rowcount} adet menü başarıyla silindi.", "success")
                else:
                    flash("Menü silinemedi. Yetkinizi kontrol edin.", "warning")
                    
            except Error as e:
                connection.rollback()
                flash(f"Silme hatası: {str(e)}", "danger")

            return redirect(url_for('menus'))

        elif action == 'update':
            update_menu_id = request.form.get('update_menu_id')
            new_menu_id = request.form.get('menu_id')
            food_id = request.form.get('food_id')
            custom_name = request.form.get('custom_name')
            price = request.form.get('price')
            restaurant_id = request.form.get('restaurant_id')
            stock_quantity = request.form.get('stock_quantity')
            category_id = request.form.get('category_id')
            
            image_file = request.files.get('menu_image') # YENİ GÖRSEL DEĞİŞKENİ

            if not stock_quantity:
                stock_quantity = 0

            if not update_menu_id:
                flash("Güncellenecek menü seçilmedi.", "warning")
                return redirect(url_for('menus'))
            
            if role == 'user' and (restaurant_id != str(restaurant_id_session) or new_menu_id != update_menu_id):
                flash("Yetkisiz işlem! Menü ID veya Restoran ID'nizi değiştiremezsiniz.", "danger")
                return redirect(url_for('menus'))
            
            missing_fields = []
            if not food_id: missing_fields.append('Ana Ürün Tipi (Kategori)')
            if not custom_name: missing_fields.append('Menüdeki Özel Adı')
            if not price: missing_fields.append('Fiyat')
            if not restaurant_id: missing_fields.append('Restoran ID')

            if missing_fields:
                flash(f"Güncelleme için şu alanlar eksik: {', '.join(missing_fields)}", "warning")
                return redirect(url_for('menus'))

            try:
                update_query = """
                    UPDATE menus 
                    SET food_id = %s, category_id = %s, custom_name = %s, price = %s, restaurant_id = %s, stock_quantity = %s 
                """
                params = [food_id, category_id, custom_name, price, restaurant_id, stock_quantity]

                if image_file and image_file.filename != '':
                    ext = image_file.filename.rsplit('.', 1)[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        flash("Hata: Sadece JPG, PNG ve WEBP formatları yüklenebilir!", "danger")
                        return redirect(url_for('menus'))

                    filename = secure_filename(image_file.filename)
                    upload_folder = os.path.join('static', 'images', 'menus')
                    os.makedirs(upload_folder, exist_ok=True) 
                    file_path = os.path.join(upload_folder, filename)
                    
                    img = Image.open(image_file)
                    img.thumbnail((600, 600))
                    if img.mode != 'RGB' and ext != 'png':
                        img = img.convert('RGB')
                    img.save(file_path, optimize=True, quality=80)
                    
                    update_query += ", image_url = %s"
                    params.append(filename)

                update_query += " WHERE menu_id = %s"
                params.append(update_menu_id)
                
                cursor.execute(update_query, tuple(params))
                # 🛠️ YENİ EKLENEN: DİNAMİK OPSİYONLARI GÜNCELLEME (Eskileri Sil, Yenileri Ekle)
                # 1. Eski opsiyonları ve şıklarını temizle
                cursor.execute("SELECT option_id FROM menu_options WHERE menu_id = %s", (update_menu_id,))
                old_options = cursor.fetchall()
                for old_opt in old_options:
                    cursor.execute("DELETE FROM menu_option_choices WHERE option_id = %s", (old_opt['option_id'],))
                cursor.execute("DELETE FROM menu_options WHERE menu_id = %s", (update_menu_id,))

                # 2. Formdan gelen güncel opsiyonları ekle (Tıpkı Add işlemindeki gibi)
                option_names = request.form.getlist('option_names[]')
                
                for i, opt_name in enumerate(option_names):
                    if not opt_name.strip():
                        continue 
                        
                    is_required = 1 if request.form.get(f'is_required_{i}') else 0
                    is_multiple = 1 if request.form.get(f'is_multiple_{i}') else 0
                    
                    cursor.execute("""
                        INSERT INTO menu_options (menu_id, option_name, is_required, is_multiple) 
                        VALUES (%s, %s, %s, %s)
                    """, (update_menu_id, opt_name, is_required, is_multiple))
                    
                    option_id = cursor.lastrowid
                    
                    choice_names = request.form.getlist(f'choice_names_{i}[]')
                    additional_prices = request.form.getlist(f'additional_prices_{i}[]')
                    
                    for j, choice_name in enumerate(choice_names):
                        if not choice_name.strip():
                            continue
                        
                        add_price = additional_prices[j] if j < len(additional_prices) and additional_prices[j] else 0
                        
                        cursor.execute("""
                            INSERT INTO menu_option_choices (option_id, choice_name, additional_price) 
                            VALUES (%s, %s, %s)
                        """, (option_id, choice_name, add_price))
                connection.commit()
                flash("Menü başarıyla güncellendi!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Güncelleme hatası: {str(e)}", "danger")
                return redirect(url_for('menus'))

        elif action == 'filter':
            try:
                menu_id = request.form.get('menu_id')
                food_name = request.form.get('name')
                price = request.form.get('price')
                restaurant_id = request.form.get('restaurant_id')

                query = """
                    SELECT m.menu_id, m.restaurant_id, m.food_id, m.category_id, m.custom_name, m.price, m.stock_quantity, m.image_url,
                           f.item_name as food_name, f.category as global_category, r.restaurant_name, rc.category_name
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
                    LEFT JOIN restaurants r ON m.restaurant_id = r.restaurant_id
                    LEFT JOIN restaurant_categories rc ON m.category_id = rc.category_id
                    WHERE 1=1
                """
                params = []

                if role == 'user':
                    query += " AND m.restaurant_id = %s"
                    params.append(restaurant_id_session)

                if menu_id:
                    query += " AND m.menu_id = %s"
                    params.append(menu_id)
                if food_name:
                    query += " AND (f.item_name LIKE %s OR m.custom_name LIKE %s)"
                    params.append(f"%{food_name}%")
                    params.append(f"%{food_name}%")
                if price:
                    query += " AND m.price = %s"
                    params.append(price)
                if restaurant_id:
                    query += " AND m.restaurant_id = %s"
                    params.append(restaurant_id)

                cursor.execute(query, params)
                menus = cursor.fetchall()
                
                if menus:
                    flash(f"Kriterlerinize uygun {len(menus)} yemek bulundu.", "success")
                else:
                    flash("Kriterlerinize uygun yemek bulunamadı.", "info")

                cursor.execute("SELECT food_id, item_name, category FROM foods ORDER BY category ASC, item_name ASC")
                foods = cursor.fetchall()
                
                restaurant_categories = []
                if role == 'user' and restaurant_id_session:
                    cursor.execute("SELECT * FROM restaurant_categories WHERE restaurant_id = %s ORDER BY sort_order ASC", (restaurant_id_session,))
                    restaurant_categories = cursor.fetchall()
                    
                return render_template('menus.html', menus=menus, foods=foods, restaurant_categories=restaurant_categories)

            except Error as e:
                flash(f"Filtreleme hatası: {str(e)}", "danger")
                return redirect(url_for('menus'))

        elif action == 'sort':
            sort_by = request.form.get('sort_by')
            sort_order = request.form.get('sort_order')

            if not sort_by or sort_order not in ['ASC', 'DESC']:
                flash("Geçersiz sıralama parametreleri.", "danger")
                return redirect(url_for('menus'))

            order_clause = ""
            if sort_by == 'item_name':
                order_clause = f"f.item_name {sort_order}"
            else:
                order_clause = f"m.{sort_by} {sort_order}"

            query = """
                    SELECT m.menu_id, m.restaurant_id, m.food_id, m.category_id, m.custom_name, m.price, m.stock_quantity, m.image_url,
                           f.item_name as food_name, f.category as global_category, r.restaurant_name, rc.category_name
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
                    LEFT JOIN restaurants r ON m.restaurant_id = r.restaurant_id
                    LEFT JOIN restaurant_categories rc ON m.category_id = rc.category_id
                    WHERE 1=1
                """
            params = []
            if role == 'user':
                query += " AND m.restaurant_id = %s"
                params.append(restaurant_id_session)

            query += f" ORDER BY {order_clause}"
            cursor.execute(query, params)
            menus = cursor.fetchall()

            flash("Menüler başarıyla sıralandı!", "success")

            cursor.execute("SELECT food_id, item_name, category FROM foods ORDER BY category ASC, item_name ASC")
            foods = cursor.fetchall()
            
            restaurant_categories = []
            if role == 'user' and restaurant_id_session:
                cursor.execute("SELECT * FROM restaurant_categories WHERE restaurant_id = %s ORDER BY sort_order ASC", (restaurant_id_session,))
                restaurant_categories = cursor.fetchall()

            return render_template('menus.html', menus=menus, foods=foods, restaurant_categories=restaurant_categories)

        elif action == 'clear':
            query = """
                    SELECT m.menu_id, m.restaurant_id, m.food_id, m.category_id, m.custom_name, m.price, m.stock_quantity, m.image_url,
                           f.item_name as food_name, f.category as global_category, r.restaurant_name, rc.category_name
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
                    LEFT JOIN restaurants r ON m.restaurant_id = r.restaurant_id
                    LEFT JOIN restaurant_categories rc ON m.category_id = rc.category_id
                    WHERE 1=1
                """
            params = []
            if role == 'user':
                query += " AND m.restaurant_id = %s"
                params.append(restaurant_id_session)

            cursor.execute(query, params)
            menus = cursor.fetchall()

            flash("Tüm filtreler temizlendi.", "success")

            cursor.execute("SELECT food_id, item_name, category FROM foods ORDER BY category ASC, item_name ASC")
            foods = cursor.fetchall()
            
            restaurant_categories = []
            if role == 'user' and restaurant_id_session:
                cursor.execute("SELECT * FROM restaurant_categories WHERE restaurant_id = %s ORDER BY sort_order ASC", (restaurant_id_session,))
                restaurant_categories = cursor.fetchall()

            return render_template('menus.html', menus=menus, foods=foods, restaurant_categories=restaurant_categories)

    except Error as e:
        flash(f"Bir hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('menus'))

def manage_menu_options():
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapmalısınız'}), 401

    # 📍 GÜVENLİK GÜNCELLEMESİ: Müşteriler (customer) seçenekleri OKUYABİLİR (GET), 
    # ancak ekleme/silme (POST) işlemlerini sadece restoran (user) yapabilir.
    role = session.get('role')
    if request.method == 'POST' and role not in ['user', 'admin']:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'}), 401

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı hatası'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        
        # Seçenekleri Okuma (GET)
        if request.method == 'GET':
            menu_id = request.args.get('menu_id')
            cursor.execute("SELECT * FROM menu_options WHERE menu_id = %s", (menu_id,))
            options = cursor.fetchall()
            
            for opt in options:
                cursor.execute("SELECT * FROM menu_option_choices WHERE option_id = %s", (opt['option_id'],))
                opt['choices'] = cursor.fetchall()
                
            return jsonify({'success': True, 'options': options})
            
        # Seçenek/Şık Ekleme & Silme İşlemleri (POST)
        elif request.method == 'POST':
            data = request.get_json()
            action = data.get('action')
            
            if action == 'add_option':
                cursor.execute("""
                    INSERT INTO menu_options (menu_id, option_name, is_required, is_multiple) 
                    VALUES (%s, %s, %s, %s)
                """, (data['menu_id'], data['option_name'], data['is_required'], data['is_multiple']))
                
            elif action == 'add_choice':
                cursor.execute("""
                    INSERT INTO menu_option_choices (option_id, choice_name, additional_price) 
                    VALUES (%s, %s, %s)
                """, (data['option_id'], data['choice_name'], data['additional_price']))
                
            elif action == 'delete_option':
                cursor.execute("DELETE FROM menu_options WHERE option_id = %s", (data['option_id'],))
                
            elif action == 'delete_choice':
                cursor.execute("DELETE FROM menu_option_choices WHERE choice_id = %s", (data['choice_id'],))
                
            connection.commit()
            return jsonify({'success': True})
            
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def upload_menu_image():
    if 'logged_in' not in session or session.get('role') not in ['user', 'admin']:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'}), 401

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'Görsel bulunamadı'}), 400

    file = request.files['image']
    menu_id = request.form.get('menu_id')

    if file.filename == '':
        return jsonify({'success': False, 'message': 'Dosya seçilmedi'}), 400

    if file and menu_id:
        filename = secure_filename(file.filename)
        # Klasör yoksa otomatik oluştur
        upload_folder = os.path.join('static', 'images', 'menus')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        
        ext = filename.rsplit('.', 1)[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            return jsonify({'success': False, 'message': 'Sadece JPG, PNG veya WEBP!'}), 400
            
        img = Image.open(file)
        img.thumbnail((600, 600))
        if img.mode != 'RGB' and ext != 'png':
            img = img.convert('RGB')
        img.save(filepath, optimize=True, quality=80)

        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("UPDATE menus SET image_url = %s WHERE menu_id = %s", (filename, menu_id))
                connection.commit()
                return jsonify({'success': True, 'image_url': filename})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
            finally:
                cursor.close()
                connection.close()

    return jsonify({'success': False, 'message': 'Hata oluştu'}), 400

def manage_promos():
    if 'logged_in' not in session or session.get('role') not in ['user', 'admin']:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'}), 401

    restaurant_id = session.get('restaurant_id')
    if not restaurant_id:
         return jsonify({'success': False, 'message': 'Restoran ID bulunamadı'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı hatası'}), 500

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'GET':
            cursor.execute("SELECT * FROM promo_codes WHERE restaurant_id = %s ORDER BY created_at DESC", (restaurant_id,))
            promos = cursor.fetchall()
            return jsonify({'success': True, 'promos': promos})

        elif request.method == 'POST':
            data = request.get_json()
            action = data.get('action')

            if action == 'add':
                code_name = data.get('code_name').upper()
                discount_type = data.get('discount_type')
                discount_value = data.get('discount_value')
                min_cart_amount = data.get('min_cart_amount', 0)

                # Kod daha önce eklenmiş mi kontrol et
                cursor.execute("SELECT promo_id FROM promo_codes WHERE restaurant_id = %s AND code_name = %s", (restaurant_id, code_name))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Bu kod zaten mevcut!'})

                cursor.execute("""
                    INSERT INTO promo_codes (restaurant_id, code_name, discount_type, discount_value, min_cart_amount)
                    VALUES (%s, %s, %s, %s, %s)
                """, (restaurant_id, code_name, discount_type, discount_value, min_cart_amount))

            elif action == 'delete':
                promo_id = data.get('promo_id')
                cursor.execute("DELETE FROM promo_codes WHERE promo_id = %s AND restaurant_id = %s", (promo_id, restaurant_id))

            elif action == 'toggle':
                promo_id = data.get('promo_id')
                cursor.execute("UPDATE promo_codes SET is_active = NOT is_active WHERE promo_id = %s AND restaurant_id = %s", (promo_id, restaurant_id))

            connection.commit()
            return jsonify({'success': True})

    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def manage_restaurant_categories():
    if 'logged_in' not in session or session.get('role') != 'user':
        return jsonify({'success': False, 'message': 'Yetkisiz erişim'}), 401

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Veritabanı hatası'}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM restaurant_categories WHERE restaurant_id = %s ORDER BY sort_order ASC", (restaurant_id,))
            categories = cursor.fetchall()
            return jsonify({'success': True, 'categories': categories})
            
        elif request.method == 'POST':
            data = request.get_json()
            action = data.get('action')
            
            if action == 'add':
                category_name = data.get('category_name').strip()
                
                if not category_name:
                    return jsonify({'success': False, 'message': 'Kategori adı boş olamaz!'})
                
                cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM restaurant_categories WHERE restaurant_id = %s", (restaurant_id,))
                next_order = cursor.fetchone()['next_order']
                
                cursor.execute("""
                    INSERT INTO restaurant_categories (restaurant_id, category_name, sort_order)
                    VALUES (%s, %s, %s)
                """, (restaurant_id, category_name, next_order))
                
                new_category_id = cursor.lastrowid 
                connection.commit()
                
                return jsonify({'success': True, 'category_id': new_category_id, 'category_name': category_name})
                
            elif action == 'delete':
                category_id = data.get('category_id')
                cursor.execute("DELETE FROM restaurant_categories WHERE category_id = %s AND restaurant_id = %s", (category_id, restaurant_id))
                connection.commit()
                return jsonify({'success': True})
            
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def restaurant_categories_page():
    if 'logged_in' not in session or session.get('role') != 'user':
        flash("Bu sayfayı görüntüleme yetkiniz yok.", "danger")
        return redirect(url_for('index'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    if not connection:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('index'))

    categories = []
    try:
        cursor = connection.cursor(dictionary=True)
        # Kategorileri ve içindeki yemek sayısını (Kullanım Sıklığı) birlikte çekiyoruz
        cursor.execute("""
            SELECT rc.*, COUNT(m.menu_id) as usage_count 
            FROM restaurant_categories rc
            LEFT JOIN menus m ON rc.category_id = m.category_id
            WHERE rc.restaurant_id = %s
            GROUP BY rc.category_id
            ORDER BY rc.sort_order ASC, rc.category_name ASC
        """, (restaurant_id,))
        categories = cursor.fetchall()
    except Exception as e:
        flash(f"Kategoriler yüklenirken hata: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return render_template('restaurant_categories.html', categories=categories)

def restaurant_categories_action():
    if 'logged_in' not in session or session.get('role') != 'user':
        if request.is_json: return jsonify({'success': False})
        return redirect(url_for('index'))

    restaurant_id = session.get('restaurant_id')
    connection = get_db_connection()
    
    if not connection:
        if request.is_json: return jsonify({'success': False})
        return redirect(url_for('restaurant_categories_page'))

    try:
        cursor = connection.cursor(dictionary=True)
        
        # 🚀 YENİ MİMARİ: Sürükle-Bırak Sıralamasını Yakala (Sessiz JSON İsteği)
        if request.is_json:
            data = request.get_json()
            if data.get('action') == 'reorder':
                ordered_ids = data.get('ordered_ids', [])
                for index, cat_id in enumerate(ordered_ids):
                    cursor.execute("UPDATE restaurant_categories SET sort_order = %s WHERE category_id = %s AND restaurant_id = %s", (index + 1, cat_id, restaurant_id))
                connection.commit()
                return jsonify({'success': True})

        # KLASİK FORM İŞLEMLERİ (Arama, Ekleme, Silme)
        action = request.form.get('action')
        
        if action == 'add':
            category_name = request.form.get('category_name').strip()
            if category_name:
                # Yeni kategori eklendiğinde otomatik olarak en son sıraya (MAX + 1) yerleşsin
                cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM restaurant_categories WHERE restaurant_id = %s", (restaurant_id,))
                next_order = cursor.fetchone()['next_order']
                
                cursor.execute("INSERT INTO restaurant_categories (restaurant_id, category_name, sort_order) VALUES (%s, %s, %s)", (restaurant_id, category_name, next_order))
                flash("Kategori başarıyla eklendi!", "success")
            
        elif action == 'update':
            category_id = request.form.get('category_id')
            category_name = request.form.get('category_name').strip()
            if category_name:
                cursor.execute("UPDATE restaurant_categories SET category_name = %s WHERE category_id = %s AND restaurant_id = %s", (category_name, category_id, restaurant_id))
                flash("Kategori adı güncellendi!", "success")
            
        elif action == 'delete':
            category_id = request.form.get('category_id')
            cursor.execute("DELETE FROM restaurant_categories WHERE category_id = %s AND restaurant_id = %s", (category_id, restaurant_id))
            flash("Kategori sistemden tamamen silindi.", "success")
            
        elif action == 'filter':
            search_query = request.form.get('name', '').strip()
            sql = """
                SELECT rc.*, COUNT(m.menu_id) as usage_count 
                FROM restaurant_categories rc
                LEFT JOIN menus m ON rc.category_id = m.category_id
                WHERE rc.restaurant_id = %s
            """
            params = [restaurant_id]
            
            if search_query:
                sql += " AND rc.category_name LIKE %s"
                params.append(f"%{search_query}%")
                
            sql += " GROUP BY rc.category_id ORDER BY rc.sort_order ASC, rc.category_name ASC"
            
            cursor.execute(sql, tuple(params))
            categories = cursor.fetchall()
            
            if categories:
                flash(f"Arama sonucunda {len(categories)} kategori bulundu.", "success")
            else:
                flash("Aradığınız kriterlere uygun kategori bulunamadı.", "info")
                
            return render_template('restaurant_categories.html', categories=categories)

        elif action == 'clear':
            flash("Tüm filtreler temizlendi.", "success")
            return redirect(url_for('restaurant_categories_page'))
            
        connection.commit()
    except Exception as e:
        connection.rollback()
        flash(f"İşlem sırasında hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('restaurant_categories_page'))