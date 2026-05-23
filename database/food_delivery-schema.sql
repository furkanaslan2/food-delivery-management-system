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
    rating_count ENUM('Too Few Ratings','20+ ratings','50+ ratings','100+ ratings','500+ ratings','1K+ ratings') NOT NULL,
    average_cost INT NOT NULL CHECK(average_cost > 0),
    cuisine VARCHAR(100) NOT NULL,
    restaurant_address TEXT NOT NULL,
    latitude DECIMAL(10, 8) NULL,   
    longitude DECIMAL(11, 8) NULL,
    table_count INT NOT NULL DEFAULT 10,
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
    PRIMARY KEY (courier_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE menus (
    menu_id INT AUTO_INCREMENT,
    restaurant_id INT NOT NULL,
    food_id INT,
    cuisine VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    stock_quantity INT DEFAULT 0 CHECK (stock_quantity >= 0), 
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
    order_status ENUM('pending', 'preparing', 'on_the_way', 'delivered', 'completed', 'canceled') NOT NULL DEFAULT 'pending',
    
    order_type ENUM('Dine-in', 'Delivery') NOT NULL DEFAULT 'Dine-in',
    table_no INT,               
    customer_name VARCHAR(100), 
    customer_phone VARCHAR(20), 
    customer_address TEXT,
    order_note TEXT,
    payment_method VARCHAR(50),
    
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
    password VARCHAR(255) NOT NULL, -- Şifreleri yine hash'leyerek tutacağız
    phone VARCHAR(20) NULL,
    city VARCHAR(50) NULL,      -- İlk aşamada hızlı şehir filtrelemesi için
    address TEXT NULL,          -- Kuryenin paketi götüreceği açık adres
    latitude DECIMAL(10, 8) NULL,   -- Gelişmiş mesafe hesabı için Enlem (Örn: 41.0082)
    longitude DECIMAL(11, 8) NULL,  -- Gelişmiş mesafe hesabı için Boylam (Örn: 28.9784)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Hesap açılış tarihi
    PRIMARY KEY (customer_id)
);

CREATE TABLE order_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    food_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
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