from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db import get_db_connection
from mysql.connector import Error
import os
from werkzeug.utils import secure_filename

def menus():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return render_template('menus.html', menus=[])

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute('''
                SELECT m.menu_id, m.restaurant_id, m.food_id, m.cuisine, m.price, m.stock_quantity, m.image_url,
                       f.item_name as food_name
                FROM menus m 
                LEFT JOIN foods f ON m.food_id = f.food_id
            ''')
        elif role == 'user' and restaurant_id:
            cursor.execute('''
                SELECT m.menu_id, m.restaurant_id, m.food_id, m.cuisine, m.price, m.stock_quantity, m.image_url,
                       f.item_name as food_name
                FROM menus m 
                LEFT JOIN foods f ON m.food_id = f.food_id 
                WHERE m.restaurant_id = %s
            ''', (restaurant_id,))
        else:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('index'))

        menus_list = cursor.fetchall()
        return render_template('menus.html', menus=menus_list)

    except Error as e:
        print(f"Database error: {str(e)}")
        flash(f"Query failed: {e}", "danger")
        return render_template('menus.html', menus=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def menus_action():
    if 'logged_in' not in session:
        return redirect(url_for('menus'))

    action = request.form.get('action')
    role = session.get('role')
    restaurant_id_session = session.get('restaurant_id') if role == 'user' else None

    connection = get_db_connection()
    if connection is None:
        flash("Couldn't connect to the database!", "danger")
        return redirect(url_for('menus'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            food_name = request.form.get('name')
            cuisine = request.form.get('cuisine')
            price = request.form.get('price')
            stock_quantity = request.form.get('stock_quantity', 0)
            restaurant_id = request.form.get('restaurant_id')
            menu_id = request.form.get('menu_id')

            if not all([food_name, cuisine, price, restaurant_id, stock_quantity]):
                flash("All fields are required except Menu ID.", "warning")
                return redirect(url_for('menus'))

            try:
                cursor.execute("SELECT COUNT(*) as count FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
                result = cursor.fetchone()
                if result['count'] == 0:
                    flash('No restaurant found with that Restaurant ID!', 'danger')
                    return redirect(url_for('menus'))

                cursor.execute("""
                    SELECT food_id FROM foods 
                    WHERE item_name = %s
                """, (food_name,))
                food_result = cursor.fetchone()

                if not food_result:
                    cursor.execute("""
                        INSERT INTO foods (item_name)
                        VALUES (%s)
                    """, (food_name,))
                    food_id = cursor.lastrowid
                else:
                    food_id = food_result['food_id']

                if menu_id:
                    cursor.execute("SELECT menu_id FROM menus WHERE menu_id = %s", (menu_id,))
                    if cursor.fetchone():
                        flash("Menu ID already exists. Please use a different ID.", "warning")
                        return redirect(url_for('menus'))
                    
                    query = """
                        INSERT INTO menus (menu_id, restaurant_id, food_id, cuisine, price, stock_quantity) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (menu_id, restaurant_id, food_id, cuisine, price, stock_quantity))
                else:
                    query = """
                        INSERT INTO menus (restaurant_id, food_id, cuisine, price, stock_quantity) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (restaurant_id, food_id, cuisine, price, stock_quantity))

                connection.commit()
                flash("Menu item added successfully!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Error adding menu item: {str(e)}", "danger")

        elif action == 'delete':
            selected_ids = request.form.get('selected_menu_items')
            
            if not selected_ids:
                flash("No menu item(s) selected for deletion.", "warning")
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
                    flash(f"Successfully deleted {cursor.rowcount} menu item(s).", "success")
                else:
                    flash("No menu items were deleted. Please check your permissions.", "warning")
                    
            except Error as e:
                connection.rollback()
                flash(f"Error deleting menu items: {str(e)}", "danger")

            return redirect(url_for('menus'))

        elif action == 'update':
            update_menu_id = request.form.get('update_menu_id')
            new_menu_id = request.form.get('menu_id')
            food_name = request.form.get('name')
            cuisine = request.form.get('cuisine')
            price = request.form.get('price')
            restaurant_id = request.form.get('restaurant_id')
            stock_quantity = request.form.get('stock_quantity', 0)

            if not update_menu_id:
                flash("No menu item selected for update.", "warning")
                return redirect(url_for('menus'))
            
            if role == 'user' and (restaurant_id != str(restaurant_id_session) or new_menu_id != update_menu_id):
                flash("Unauthorized action! You cannot change your Menu Item's ID or Restaurant ID.", "danger")
                return redirect(url_for('menus'))
            
            if not all([food_name, cuisine, price, restaurant_id]):
                flash("All fields (Name, Cuisine, Price, Restaurant ID) are required for update.", "warning")
                return redirect(url_for('menus'))
            
            if stock_quantity == "":
                flash("Stock quantity cannot be empty.", "warning")
                return redirect(url_for('menus'))

            try:
                cursor.execute("""
                    SELECT food_id FROM foods 
                    WHERE item_name = %s
                """, (food_name,))
                food_result = cursor.fetchone()
                
                if not food_result:
                    cursor.execute("""
                        INSERT INTO foods (item_name)
                        VALUES (%s)
                    """, (food_name,))
                    food_id = cursor.lastrowid
                else:
                    food_id = food_result['food_id']

                query = """
                    UPDATE menus 
                    SET food_id = %s, cuisine = %s, price = %s, restaurant_id = %s, stock_quantity = %s 
                    WHERE menu_id = %s
                """
                params = (food_id, cuisine, price, restaurant_id, stock_quantity, update_menu_id)
                
                cursor.execute(query, params)
                connection.commit()
                flash("Menu item updated successfully!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Error updating menu item: {str(e)}", "danger")
                return redirect(url_for('menus'))

        elif action == 'filter':
            try:
                menu_id = request.form.get('menu_id')
                food_name = request.form.get('name')
                cuisine = request.form.get('cuisine')
                price = request.form.get('price')
                restaurant_id = request.form.get('restaurant_id')

                query = """
                    SELECT m.menu_id, m.restaurant_id, m.cuisine, m.price,
                           f.item_name as food_name
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
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
                    query += " AND f.item_name LIKE %s"
                    params.append(f"%{food_name}%")
                if cuisine:
                    query += " AND m.cuisine LIKE %s"
                    params.append(f"%{cuisine}%")
                if price:
                    query += " AND m.price = %s"
                    params.append(price)
                if restaurant_id:
                    query += " AND m.restaurant_id = %s"
                    params.append(restaurant_id)

                cursor.execute(query, params)
                menus = cursor.fetchall()
                
                if menus:
                    flash(f"Found {len(menus)} menu item(s) matching your criteria.", "success")
                else:
                    flash("No menu items found matching your criteria.", "info")
                    
                return render_template('menus.html', menus=menus)

            except Error as e:
                flash(f"Error during filtering: {str(e)}", "danger")
                return redirect(url_for('menus'))

        elif action == 'sort':
            sort_by = request.form.get('sort_by')
            sort_order = request.form.get('sort_order')

            if not sort_by or sort_order not in ['ASC', 'DESC']:
                flash("Invalid sort parameters.", "danger")
                return redirect(url_for('menus'))

            order_clause = ""
            if sort_by == 'item_name':
                order_clause = f"f.item_name {sort_order}"
            else:
                order_clause = f"m.{sort_by} {sort_order}"

            if 'filtered_menus' in session and session['filtered_menus']:
                filtered_ids = [item['menus_id'] for item in session['filtered_menus']]

                query = f"""
                    SELECT m.*, f.item_name as food_name 
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
                    WHERE m.menus_id IN ({','.join(['%s'] * len(filtered_ids))}) 
                    ORDER BY {order_clause}
                """
                cursor.execute(query, filtered_ids)
                menus = cursor.fetchall()

                for item in menus:
                    if item['food_name']:
                        item['name'] = item['food_name']

                flash("Filtered menus items sorted successfully!", "success")
            else:
                query = """
                    SELECT m.*, f.item_name as food_name
                    FROM menus m 
                    LEFT JOIN foods f ON m.food_id = f.food_id 
                    WHERE 1=1
                """
                params = []
                if role == 'user':
                    query += " AND m.restaurant_id = %s"
                    params.append(restaurant_id_session)

                query += f" ORDER BY {order_clause}"
                cursor.execute(query, params)
                menus = cursor.fetchall()

                for item in menus:
                    if item['food_name']:
                        item['name'] = item['food_name']

                flash("Menus items sorted successfully!", "success")

            return render_template('menus.html', menus=menus)

        elif action == 'clear':
            if 'filtered_menus' in session:
                session.pop('filtered_menus', None)

            query = """
                SELECT m.*, f.item_name as food_name
                FROM menus m 
                LEFT JOIN foods f ON m.food_id = f.food_id 
                WHERE 1=1
            """
            params = []
            if role == 'user':
                query += " AND m.restaurant_id = %s"
                params.append(restaurant_id_session)

            cursor.execute(query, params)
            menus = cursor.fetchall()

            for item in menus:
                if item['food_name']:
                    item['name'] = item['food_name']

            flash("All filters, sorting, and selections have been cleared.", "success")
            return render_template('menus.html', menus=menus)

    except Error as e:
        flash(f"An error occurred: {e}", "danger")
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
        file.save(filepath)

        # Veritabanını güncelle
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