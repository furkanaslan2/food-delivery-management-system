import os
from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
from index import index
from auth import login, logout, register, customer_login, customer_register, verify_email_page, verify_email_code, resend_verification_code, forgot_password, reset_password, process_reset, resend_reset_code
from users import users, user_action
from restaurants import restaurants, restaurant_action, restaurant_analytics, restaurant_profile, restaurant_reviews, reply_review
from couriers import couriers, courier_action, api_check_courier_orders
from menus import menus, menus_action, manage_menu_options, upload_menu_image, manage_promos
from orders import orders, order_action, get_order_details, get_restaurant_details, api_check_new_orders, kitchen_display, kitchen_order_action
from foods import foods, food_action
from waiters import waiter_dashboard, waiter_create_order, waiters, waiter_action, waiter_close_bill, waiter_receipt
from customer import view_restaurant, add_to_cart, view_cart, checkout, customer_orders, set_location, remove_from_cart, increase_cart_item, decrease_cart_item, submit_review, get_active_order_status, toggle_favorite, view_favorites, get_addresses, add_address, select_address, update_address, cancel_order, apply_promo, ask_ai, api_reorder,api_restaurant_statuses, api_get_courier_location
from courier_panel import courier_dashboard, update_delivery_status, api_update_courier_location
from payment_handler import checkout_payment, payment_callback
from profile_settings import view_profile, update_profile
from admin_routes import partner_applications, approve_application

load_dotenv()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.secret_key = os.getenv('FLASK_SECRET_KEY')
Session(app)

app.add_url_rule('/', 'index', index)
app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', logout)
app.add_url_rule('/register', 'register', register, methods=['GET', 'POST'])
app.add_url_rule('/users', 'users', users)
app.add_url_rule('/users', 'user_action', user_action, methods=['POST'])
app.add_url_rule('/restaurants', 'restaurants', restaurants)
app.add_url_rule('/restaurants', 'restaurant_action', restaurant_action, methods=['POST'])
app.add_url_rule('/restaurant/<int:restaurant_id>', 'view_restaurant', view_restaurant)
app.add_url_rule('/restaurant/profile', view_func=restaurant_profile, methods=['GET', 'POST'])
app.add_url_rule('/couriers', 'couriers', couriers)
app.add_url_rule('/couriers', 'courier_action', courier_action, methods=['POST'])
app.add_url_rule('/menus', 'menus', menus)
app.add_url_rule('/menus', 'menus_action', menus_action, methods=['POST'])
app.add_url_rule('/orders', 'orders', orders)
app.add_url_rule('/orders', 'order_action', order_action, methods=['POST'])
app.add_url_rule('/order_details/<int:order_id>', 'get_order_details', get_order_details)
app.add_url_rule('/foods', 'foods', foods)
app.add_url_rule('/foods', 'food_action', food_action, methods=['POST'])
app.add_url_rule('/waiters', 'waiters', waiters)
app.add_url_rule('/waiters', 'waiter_action', waiter_action, methods=['POST'])
app.add_url_rule('/waiter_dashboard', 'waiter_dashboard', waiter_dashboard)
app.add_url_rule('/waiter_create_order', 'waiter_create_order', waiter_create_order, methods=['POST'])
app.add_url_rule('/waiter_close_bill', 'waiter_close_bill', waiter_close_bill, methods=['POST'])
app.add_url_rule('/waiter/receipt/<int:order_id>', endpoint='waiter_receipt', view_func=waiter_receipt, methods=['GET'])
app.add_url_rule('/analytics', view_func=restaurant_analytics, methods=['GET'])
app.add_url_rule('/customer_login', 'customer_login', customer_login, methods=['GET', 'POST'])
app.add_url_rule('/customer_register', 'customer_register', customer_register, methods=['GET', 'POST'])
app.add_url_rule('/cart', 'view_cart', view_cart) 
app.add_url_rule('/add_to_cart', 'add_to_cart', add_to_cart, methods=['POST'])
app.add_url_rule('/checkout', 'checkout', checkout, methods=['POST'])
app.add_url_rule('/my_orders', 'customer_orders', customer_orders)
app.add_url_rule('/set_location', 'set_location', set_location, methods=['POST'])
app.add_url_rule('/courier/<int:courier_id>', 'courier_dashboard', courier_dashboard)
app.add_url_rule('/update_delivery_status', 'update_delivery_status', update_delivery_status, methods=['POST'])
app.add_url_rule('/checkout_payment', 'checkout_payment', checkout_payment, methods=['POST', 'GET'])
app.add_url_rule('/payment_callback', 'payment_callback', payment_callback, methods=['POST'])
app.add_url_rule('/remove_from_cart/<int:menu_id>', view_func=remove_from_cart, methods=['POST'])
app.add_url_rule('/increase_item/<int:menu_id>', view_func=increase_cart_item, methods=['POST'])
app.add_url_rule('/decrease_item/<int:menu_id>', view_func=decrease_cart_item, methods=['POST'])
app.add_url_rule('/submit_review', view_func=submit_review, methods=['POST'])
app.add_url_rule('/profile', endpoint='view_profile', view_func=view_profile, methods=['GET'])
app.add_url_rule('/profile/update', endpoint='update_profile', view_func=update_profile, methods=['POST'])
app.add_url_rule('/api/active_order_status', view_func=get_active_order_status)
app.add_url_rule('/api/check_new_orders', view_func=api_check_new_orders)
app.add_url_rule('/api/check_courier_orders', view_func=api_check_courier_orders)
app.add_url_rule('/api/toggle_favorite', view_func=toggle_favorite, methods=['POST'])
app.add_url_rule('/favorites', view_func=view_favorites, methods=['GET'])
app.add_url_rule('/api/get_addresses', endpoint='api_get_addresses', view_func=get_addresses)
app.add_url_rule('/api/add_address', endpoint='api_add_address', view_func=add_address, methods=['POST'])
app.add_url_rule('/api/select_address', endpoint='api_select_address', view_func=select_address, methods=['POST'])
app.add_url_rule('/api/update_address', endpoint='api_update_address', view_func=update_address, methods=['POST'])
app.add_url_rule('/api/cancel_order', endpoint='cancel_order', view_func=cancel_order, methods=['POST'])
app.add_url_rule('/api/menu_options', endpoint='manage_menu_options', view_func=manage_menu_options, methods=['GET', 'POST'])
app.add_url_rule('/api/upload_menu_image', endpoint='upload_menu_image', view_func=upload_menu_image, methods=['POST'])
app.add_url_rule('/api/manage_promos', endpoint='manage_promos', view_func=manage_promos, methods=['GET', 'POST'])
app.add_url_rule('/api/apply_promo', endpoint='apply_promo', view_func=apply_promo, methods=['POST'])
app.add_url_rule('/api/ask_ai', endpoint='ask_ai', view_func=ask_ai, methods=['POST'])
app.add_url_rule('/api/reorder', view_func=api_reorder, methods=['POST'])
app.add_url_rule('/api/restaurant_statuses', view_func=api_restaurant_statuses, methods=['POST'])
app.add_url_rule('/api/update_courier_location', view_func=api_update_courier_location, methods=['POST'])
app.add_url_rule('/api/get_courier_location', view_func=api_get_courier_location, methods=['POST'])
app.add_url_rule('/restaurant/reviews', 'restaurant_reviews', restaurant_reviews, methods=['GET'])
app.add_url_rule('/api/reply_review', 'reply_review', reply_review, methods=['POST'])
app.add_url_rule('/kitchen', 'kitchen_display', kitchen_display)
app.add_url_rule('/kitchen/action', 'kitchen_order_action', kitchen_order_action, methods=['POST'])
app.add_url_rule('/applications', 'partner_applications', partner_applications)
app.add_url_rule('/approve_application/<int:app_id>', 'approve_application', approve_application, methods=['POST'])
app.add_url_rule('/verify_email', 'verify_email_page', verify_email_page, methods=['GET'])
app.add_url_rule('/verify_email_code', 'verify_email_code', verify_email_code, methods=['POST'])
app.add_url_rule('/resend_verification_code', 'resend_verification_code', resend_verification_code, methods=['GET'])
app.add_url_rule('/forgot_password', 'forgot_password', forgot_password, methods=['GET', 'POST'])
app.add_url_rule('/reset_password', 'reset_password', reset_password, methods=['GET'])
app.add_url_rule('/process_reset', 'process_reset', process_reset, methods=['POST'])
app.add_url_rule('/resend_reset_code', 'resend_reset_code', resend_reset_code, methods=['GET'])

if __name__ == '__main__':
    app.run(debug=True)
