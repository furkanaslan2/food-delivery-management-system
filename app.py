import os
from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
from index import index
from auth import login, logout, register, customer_login, customer_register
from users import users, user_action
from restaurants import restaurants, restaurant_action, restaurant_analytics
from couriers import couriers, courier_action
from menus import menus, menus_action
from orders import orders, order_action, get_order_details, get_restaurant_details
from foods import foods, food_action
from waiters import waiter_dashboard, waiter_create_order, waiters, waiter_action, waiter_close_bill, waiter_receipt
from customer import view_restaurant, add_to_cart, view_cart, checkout, customer_orders, set_location, remove_from_cart, increase_cart_item, decrease_cart_item, submit_review
from courier_panel import courier_dashboard, update_delivery_status, courier_login, courier_logout
from payment_handler import checkout_payment, payment_callback
from profile_settings import view_profile, update_profile

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
app.add_url_rule('/courier_login', view_func=courier_login, methods=['GET', 'POST'])
app.add_url_rule('/courier_logout', view_func=courier_logout)
app.add_url_rule('/submit_review', view_func=submit_review, methods=['POST'])
app.add_url_rule('/profile', endpoint='view_profile', view_func=view_profile, methods=['GET'])
app.add_url_rule('/profile/update', endpoint='update_profile', view_func=update_profile, methods=['POST'])

if __name__ == '__main__':
    app.run(debug=True)
