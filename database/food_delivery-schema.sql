DROP DATABASE IF EXISTS food_delivery;
CREATE DATABASE food_delivery;
USE food_delivery;

CREATE TABLE admins (
    admin_id INT AUTO_INCREMENT,
    email VARCHAR(150) NOT NULL CHECK (LENGTH(email) >= 5 AND email LIKE '%@%'),
    password VARCHAR(255) NOT NULL,
    PRIMARY KEY (admin_id)
);

CREATE TABLE users (
    user_id INT AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL CHECK (LENGTH(email) >= 5 AND email LIKE '%@%'),
    password VARCHAR(255) NOT NULL,
    PRIMARY KEY (user_id)
);

CREATE TABLE restaurants (
    restaurant_id INT AUTO_INCREMENT,
    user_id INT,
    restaurant_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    rating DECIMAL(2,1),
    rating_count VARCHAR(50) DEFAULT 'Yeni',
    cuisine ENUM('Hamburger', 'Döner', 'Pizza', 'Pide & Lahmacun', 'Çiğ Köfte', 'Tatlı', 'Sokak Lezzetleri', 'Köfte', 'Tavuk', 'Salata & Sağlık', 'Mantı & Makarna', 'Kebap', 'Tantuni', 'Ev Yemekleri', 'Tost & Sandviç', 'Kahve & İçecek', 'Pastane & Fırın', 'Çorba', 'Dünya Mutfağı & Cafe', 'Uzak Doğu', 'Balık & Deniz Ürünleri', 'Meze', 'Dondurma', 'Steak', 'Kahvaltı', 'Börek') NOT NULL,
    restaurant_address TEXT NOT NULL,
    latitude DECIMAL(10, 8) NULL,   
    longitude DECIMAL(11, 8) NULL,
    table_count INT NOT NULL DEFAULT 10,
    opening_time TIME DEFAULT '09:00:00',
    closing_time TIME DEFAULT '23:00:00',
    is_manually_closed BOOLEAN DEFAULT FALSE,
    is_active TINYINT(1) DEFAULT 1,
    min_order_amount DECIMAL(10,2) DEFAULT 0.00,
    image_url VARCHAR(255) DEFAULT 'default_restaurant.jpg',
    PRIMARY KEY (restaurant_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE foods (
    food_id INT AUTO_INCREMENT,
    item_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) DEFAULT 'ANA YEMEK',
    PRIMARY KEY (food_id)
);

CREATE TABLE couriers (
    courier_id INT AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    gender ENUM('Male', 'Female') NOT NULL,
    birth_date DATE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL, 
    password VARCHAR(255) NOT NULL,
    restaurant_id INT,
    current_lat DECIMAL(10, 8) NULL,
    current_lon DECIMAL(11, 8) NULL,
    PRIMARY KEY (courier_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE menus (
    menu_id INT AUTO_INCREMENT,
    restaurant_id INT NOT NULL,
    food_id INT,
    custom_name VARCHAR(255) NULL
    price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    stock_quantity INT DEFAULT 0 CHECK (stock_quantity >= 0),
    image_url VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (menu_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT,
    order_date DATETIME NOT NULL,
    sales_qty FLOAT NOT NULL DEFAULT 1,
    sales_amount FLOAT NOT NULL DEFAULT 0,
    restaurant_id INT,
    courier_id INT, 
    customer_id INT,
    order_status VARCHAR(50) DEFAULT 'pending',
    
    order_type ENUM('Dine-in', 'Delivery') NOT NULL DEFAULT 'Dine-in',
    table_no INT,               
    customer_name VARCHAR(100), 
    customer_phone VARCHAR(20), 
    customer_address TEXT,
    order_note TEXT,
    payment_method VARCHAR(50),
    applied_promo_code VARCHAR(50) DEFAULT NULL,
    
    PRIMARY KEY (order_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
    FOREIGN KEY (courier_id) REFERENCES couriers(courier_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
	ON DELETE SET NULL
	ON UPDATE CASCADE
);

CREATE TABLE waiters (
    waiter_id INT AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL CHECK (LENGTH(email) >= 5 AND email LIKE '%@%'),
    password VARCHAR(255) NOT NULL,
    restaurant_id INT NOT NULL,
    PRIMARY KEY (waiter_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, 
    phone VARCHAR(20) NULL,
    latitude DECIMAL(10, 8) NULL,  
    longitude DECIMAL(11, 8) NULL,  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (customer_id)
);

CREATE TABLE order_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    food_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    cart_index VARCHAR(50) DEFAULT NULL,
    item_note TEXT DEFAULT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id)
);

CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,          
    restaurant_id INT NOT NULL,           
    customer_id INT NOT NULL,           
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5), 
    comment TEXT,    
    restaurant_reply TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE 
);

CREATE TABLE favorite_restaurants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    restaurant_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, restaurant_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);

CREATE TABLE customer_addresses (
    address_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    title VARCHAR(50) NOT NULL,            
    city VARCHAR(50) NOT NULL,             
    district VARCHAR(50) NOT NULL,        
    neighborhood VARCHAR(100) NOT NULL,    
    street VARCHAR(100) NOT NULL,         
    building_no VARCHAR(20) NOT NULL,      
    floor_no VARCHAR(10),                  
    apt_no VARCHAR(20),                    
    directions TEXT,                      
    latitude DECIMAL(10, 8),               
    longitude DECIMAL(11, 8),              
    contact_name VARCHAR(100),             
    contact_phone VARCHAR(20),             
    is_active BOOLEAN DEFAULT FALSE,       
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE menu_options (
    option_id INT AUTO_INCREMENT PRIMARY KEY,
    menu_id INT NOT NULL,
    option_name VARCHAR(255) NOT NULL,
    is_required BOOLEAN DEFAULT FALSE, 
    is_multiple BOOLEAN DEFAULT FALSE, 
    FOREIGN KEY (menu_id) REFERENCES menus(menu_id) ON DELETE CASCADE
);

CREATE TABLE menu_option_choices (
    choice_id INT AUTO_INCREMENT PRIMARY KEY,
    option_id INT NOT NULL,
    choice_name VARCHAR(255) NOT NULL,
    additional_price DECIMAL(10, 2) DEFAULT 0.00, 
    FOREIGN KEY (option_id) REFERENCES menu_options(option_id) ON DELETE CASCADE
);

CREATE TABLE order_item_choices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    food_id INT NOT NULL,
    choice_id INT NOT NULL,
    cart_index VARCHAR(50) DEFAULT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE CASCADE,
    FOREIGN KEY (choice_id) REFERENCES menu_option_choices(choice_id) ON DELETE CASCADE
);

CREATE TABLE promo_codes (
    promo_id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    code_name VARCHAR(50) NOT NULL, 
    discount_type ENUM('percentage', 'fixed') NOT NULL, 
    discount_value DECIMAL(10, 2) NOT NULL, 
    min_cart_amount DECIMAL(10, 2) DEFAULT 0.00, 
    is_active BOOLEAN DEFAULT TRUE, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE
);

CREATE TABLE restaurant_applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);