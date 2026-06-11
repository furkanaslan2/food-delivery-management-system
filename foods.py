from flask import render_template, request, redirect, url_for, session, flash
from db import get_db_connection
from mysql.connector import Error

def foods():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    role = session.get('role')
    restaurant_id = session.get('restaurant_id')

    connection = get_db_connection()
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return render_template('foods.html', foods=[])

    try:
        cursor = connection.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute('''
                SELECT f.food_id, f.item_name,
                       COUNT(m.menu_id) as menu_count
                FROM foods f
                LEFT JOIN menus m ON f.food_id = m.food_id
                GROUP BY f.food_id, f.item_name
            ''')
        elif role == 'user' and restaurant_id:
            cursor.execute('''
                SELECT DISTINCT f.food_id, f.item_name,
                       COUNT(m.menu_id) as menu_count
                FROM foods f
                LEFT JOIN menus m ON f.food_id = m.food_id
                WHERE m.restaurant_id = %s OR m.restaurant_id IS NULL
                GROUP BY f.food_id, f.item_name
            ''', (restaurant_id,))
        else:
            flash("Yetkisiz erişim!", "danger")
            return redirect(url_for('index'))

        foods_list = cursor.fetchall()
        return render_template('foods.html', foods=foods_list)

    except Error as e:
        print(f"Database error: {str(e)}")
        flash(f"Sorgu hatası: {e}", "danger")
        return render_template('foods.html', foods=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def food_action():
    if 'logged_in' not in session:
        return redirect(url_for('foods'))

    action = request.form.get('action')
    connection = get_db_connection()
    
    if connection is None:
        flash("Veritabanına bağlanılamadı!", "danger")
        return redirect(url_for('foods'))

    try:
        cursor = connection.cursor(dictionary=True)

        if action == 'add':
            food_name = request.form.get('name')
            food_id = request.form.get('food_id')

            if not food_name:
                flash("Kategori adı zorunludur.", "warning")
                return redirect(url_for('foods'))

            try:
                if food_id:
                    cursor.execute("SELECT food_id FROM foods WHERE food_id = %s", (food_id,))
                    if cursor.fetchone():
                        flash("Bu Kategori ID zaten mevcut.", "warning")
                        return redirect(url_for('foods'))
                    
                    query = "INSERT INTO foods (food_id, item_name) VALUES (%s, %s)"
                    cursor.execute(query, (food_id, food_name))
                else:
                    query = "INSERT INTO foods (item_name) VALUES (%s)"
                    cursor.execute(query, (food_name,))

                connection.commit()
                flash("Kategori başarıyla eklendi!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Kategori eklenirken hata: {str(e)}", "danger")

        elif action == 'delete':
            selected_ids = request.form.get('selected_food_items')
            
            if not selected_ids:
                flash("Silinecek kategori seçilmedi.", "warning")
                return redirect(url_for('foods'))

            selected_ids = selected_ids.split(',')
            
            try:
                query = "DELETE FROM foods WHERE food_id IN ({})".format(','.join(['%s'] * len(selected_ids)))
                cursor.execute(query, selected_ids)
                connection.commit()
                
                if cursor.rowcount > 0:
                    flash(f"{cursor.rowcount} kategori başarıyla silindi.", "success")
                else:
                    flash("Hiçbir kategori silinemedi.", "warning")
                    
            except Error as e:
                flash(f"Kategoriler silinirken hata: {str(e)}", "danger")
                connection.rollback()

        elif action == 'update':
            update_food_id = request.form.get('update_food_id')
            food_name = request.form.get('name')

            if not update_food_id:
                flash("Güncellenecek kategori seçilmedi.", "warning")
                return redirect(url_for('foods'))
            
            if not food_name:
                flash("Güncelleme için kategori adı zorunludur.", "warning")
                return redirect(url_for('foods'))

            try:
                query = """
                    UPDATE foods 
                    SET item_name = %s
                    WHERE food_id = %s
                """
                cursor.execute(query, (food_name, update_food_id))
                connection.commit()
                flash("Kategori başarıyla güncellendi!", "success")

            except Error as e:
                connection.rollback()
                flash(f"Kategori güncellenirken hata: {str(e)}", "danger")

        elif action == 'filter':
            try:
                food_id = request.form.get('food_id')
                food_name = request.form.get('name')

                query = """
                    SELECT f.*, COUNT(m.menu_id) as menu_count
                    FROM foods f
                    LEFT JOIN menus m ON f.food_id = m.food_id
                    WHERE 1=1
                """
                params = []

                if food_id:
                    query += " AND f.food_id = %s"
                    params.append(food_id)
                if food_name:
                    query += " AND f.item_name LIKE %s"
                    params.append(f"%{food_name}%")

                query += " GROUP BY f.food_id, f.item_name"
                cursor.execute(query, params)
                foods = cursor.fetchall()
                
                if foods:
                    flash(f"Kriterlerinize uygun {len(foods)} kategori bulundu.", "success")
                else:
                    flash("Kriterlerinize uygun kategori bulunamadı.", "info")
                    
                return render_template('foods.html', foods=foods)

            except Error as e:
                flash(f"Filtreleme hatası: {str(e)}", "danger")
                return redirect(url_for('foods'))

        elif action == 'sort':
            sort_by = request.form.get('sort_by')
            sort_order = request.form.get('sort_order')

            if not sort_by or sort_order not in ['ASC', 'DESC']:
                flash("Geçersiz sıralama parametreleri.", "danger")
                return redirect(url_for('foods'))

            query = f"""
                SELECT f.*, COUNT(m.menu_id) as menu_count
                FROM foods f
                LEFT JOIN menus m ON f.food_id = m.food_id
                GROUP BY f.food_id, f.item_name
                ORDER BY f.{sort_by} {sort_order}
            """
            cursor.execute(query)
            foods = cursor.fetchall()
            flash("Kategoriler başarıyla sıralandı!", "success")
            return render_template('foods.html', foods=foods)

        elif action == 'clear':
            query = """
                SELECT f.*, COUNT(m.menu_id) as menu_count
                FROM foods f
                LEFT JOIN menus m ON f.food_id = m.food_id
                GROUP BY f.food_id, f.item_name
            """
            cursor.execute(query)
            foods = cursor.fetchall()
            flash("Tüm filtreler ve sıralamalar temizlendi.", "success")
            return render_template('foods.html', foods=foods)

    except Error as e:
        flash(f"Bir hata oluştu: {e}", "danger")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return redirect(url_for('foods'))