-- ============================================
--  Sai Krupa Sawmill Management System Database
--  Database Name: sawmill_db
--  Author: Ayush Ghag
-- ============================================

-- Create the database
CREATE DATABASE IF NOT EXISTS sawmill_db;
USE sawmill_db;

-- ==============================
-- 1️⃣ Admin Users Table
-- ==============================
CREATE TABLE admin_users (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL
);

-- Default admin credentials
INSERT INTO admin_users (username, password_hash) VALUES ('admin', 'admin123');


-- ==============================
-- 2️⃣ Employees Table
-- ==============================
CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50),
    contact_number VARCHAR(15)
);


-- ==============================
-- 3️⃣ Employee Salary Table
-- ==============================
CREATE TABLE employee_salary (
    salary_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    month VARCHAR(20),
    basic_salary DECIMAL(10,2),
    allowances DECIMAL(10,2),
    deductions DECIMAL(10,2),
    net_salary DECIMAL(10,2),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE CASCADE
);


-- ==============================
-- 4️⃣ Suppliers Table
-- ==============================
CREATE TABLE suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_number VARCHAR(15),
    email VARCHAR(100),
    address VARCHAR(255)
);


-- ==============================
-- 5️⃣ Raw Materials Table
-- ==============================
CREATE TABLE raw_materials (
    material_id INT AUTO_INCREMENT PRIMARY KEY,
    material_name VARCHAR(100) NOT NULL,
    unit VARCHAR(20),
    price_per_unit DECIMAL(10,2),
    supplier_id INT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON DELETE SET NULL
);


-- ==============================
-- 6️⃣ Products Table
-- ==============================
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    unit VARCHAR(20),
    price_per_unit DECIMAL(10,2)
);


-- ==============================
-- 7️⃣ Customers Table
-- ==============================
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_number VARCHAR(15),
    email VARCHAR(100),
    address VARCHAR(255)
);


-- ==============================
-- 8️⃣ Stock Transactions Table
-- ==============================
CREATE TABLE stock_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    material_id INT,
    supplier_id INT,
    transaction_type ENUM('purchase', 'return', 'adjustment'),
    quantity DECIMAL(10,2),
    total_cost DECIMAL(10,2),
    transaction_date DATE,
    remarks VARCHAR(255),
    FOREIGN KEY (material_id) REFERENCES raw_materials(material_id)
        ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON DELETE SET NULL
);


-- ==============================
-- 9️⃣ Orders Table
-- ==============================
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    product_id INT,
    quantity INT,
    total_amount DECIMAL(10,2),
    order_date DATE,
    delivery_date DATE,
    delivery_agent VARCHAR(100),
    vehicle_number VARCHAR(50),
    delivery_status ENUM('Pending','Delivered','Cancelled'),
    status ENUM('Active','Completed','Cancelled'),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON DELETE SET NULL
);


-- ==============================
-- 🔟 Billing Invoices Table
-- ==============================
CREATE TABLE billing_invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    invoice_date DATE,
    total_amount DECIMAL(10,2),
    payment_status ENUM('paid', 'unpaid', 'partially_paid'),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE
);


