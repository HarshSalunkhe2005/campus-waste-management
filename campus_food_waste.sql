DROP DATABASE IF EXISTS campus_food_waste;
CREATE DATABASE campus_food_waste;
USE campus_food_waste;

-- =========================
-- USERS & ORGANIZATIONS
-- =========================

-- 1) Roles
CREATE TABLE roles (
  role_id INT PRIMARY KEY AUTO_INCREMENT,
  role_name ENUM('admin','canteen','ngo','student') NOT NULL UNIQUE
);

-- 2) Users
CREATE TABLE users (
  user_id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  role_id INT NOT NULL,
  ref_id INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (role_id) REFERENCES roles(role_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 3) Canteen
CREATE TABLE canteen (
  canteen_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  location VARCHAR(100) NOT NULL,
  contact_no VARCHAR(15),
  email VARCHAR(100) UNIQUE
);

-- 4) NGO
CREATE TABLE ngo (
  ngo_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  contact_person VARCHAR(100),
  phone VARCHAR(15),
  email VARCHAR(100) UNIQUE,
  type ENUM('ngo','student_group') DEFAULT 'ngo'
);

-- =========================
-- FOOD MANAGEMENT
-- =========================

-- 5) Canteen Menu
CREATE TABLE canteen_menu (
  menu_id INT PRIMARY KEY AUTO_INCREMENT,
  canteen_id INT NOT NULL,
  item_name VARCHAR(100) NOT NULL,
  default_quantity INT,
  unit VARCHAR(20) DEFAULT 'plates',
  FOREIGN KEY (canteen_id) REFERENCES canteen(canteen_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 6) Food
CREATE TABLE food (
  food_id INT PRIMARY KEY AUTO_INCREMENT,
  canteen_id INT NOT NULL,
  item_name VARCHAR(100) NOT NULL,
  category ENUM('Vegetarian','Non-Vegetarian','Beverage','Bakery','Other'),
  quantity INT CHECK (quantity > 0),
  unit VARCHAR(20) DEFAULT 'plates',
  expiry_time DATETIME NOT NULL,
  status ENUM('available','donated','expired','requested','approved') DEFAULT 'available',
  notes VARCHAR(255),
  FOREIGN KEY (canteen_id) REFERENCES canteen(canteen_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 7) Donation Request
CREATE TABLE donation_request (
  request_id INT PRIMARY KEY AUTO_INCREMENT,
  food_id INT NOT NULL,
  ngo_id INT NOT NULL,
  request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('pending','approved','completed','rejected') DEFAULT 'pending',
  approved_by INT,
  approved_time DATETIME,
  completed_time DATETIME,
  FOREIGN KEY (food_id) REFERENCES food(food_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (ngo_id) REFERENCES ngo(ngo_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (approved_by) REFERENCES users(user_id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

-- 8) Donation History
CREATE TABLE donation_history (
  donation_id INT PRIMARY KEY AUTO_INCREMENT,
  food_id INT NOT NULL,
  ngo_id INT NOT NULL,
  quantity INT NOT NULL,
  donated_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (food_id) REFERENCES food(food_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (ngo_id) REFERENCES ngo(ngo_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- =========================
-- TRACKING & ACCOUNTABILITY
-- =========================

-- 9) Expiry Alert
CREATE TABLE expiry_alert (
  alert_id INT PRIMARY KEY AUTO_INCREMENT,
  food_id INT NOT NULL,
  alert_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  message VARCHAR(255),
  FOREIGN KEY (food_id) REFERENCES food(food_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 10) Leaderboard
CREATE TABLE leaderboard (
  lb_id INT PRIMARY KEY AUTO_INCREMENT,
  canteen_id INT NOT NULL,
  total_items INT DEFAULT 0,
  donated_items INT DEFAULT 0,
  waste_score DECIMAL(6,3)
    GENERATED ALWAYS AS (
      CASE WHEN total_items = 0 THEN 0
           ELSE (donated_items / total_items) * 100 END
    ) STORED,
  FOREIGN KEY (canteen_id) REFERENCES canteen(canteen_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 11) Audit Log
CREATE TABLE audit_log (
  log_id INT PRIMARY KEY AUTO_INCREMENT,
  action VARCHAR(100) NOT NULL,
  table_name VARCHAR(50) NOT NULL,
  record_id INT NOT NULL,
  performed_by INT,
  event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (performed_by) REFERENCES users(user_id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

-- 12) Login Activity
CREATE TABLE login_activity (
  activity_id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  logout_time DATETIME,
  ip_address VARCHAR(45),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- =========================
-- IMPACT & WASTE
-- =========================

-- 13) Meal Beneficiary
CREATE TABLE meal_beneficiary (
  beneficiary_id INT PRIMARY KEY AUTO_INCREMENT,
  donation_id INT NOT NULL,
  people_served INT NOT NULL,
  location VARCHAR(100),
  recorded_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (donation_id) REFERENCES donation_history(donation_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- 14) Waste Report
CREATE TABLE waste_report (
  report_id INT PRIMARY KEY AUTO_INCREMENT,
  food_id INT NOT NULL,
  reported_by INT NOT NULL,
  reason ENUM('spoilage','late_pickup','over_preparation','other'),
  quantity_wasted INT,
  report_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (food_id) REFERENCES food(food_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (reported_by) REFERENCES users(user_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

-- =========================
-- SEED DATA
-- =========================

-- Roles
INSERT INTO roles (role_name) VALUES 
('admin'), ('canteen'), ('ngo'), ('student');

-- Canteens
INSERT INTO canteen (name, location, contact_no, email) VALUES
('SIT Mess', 'Block A', '1111111111', 'sit.mess@campus.edu'),
('HILLTOP Canteen', 'Block C', '9822001100', 'hilltop.canteen@campus.edu'),
('SUHRC Mess', 'Block D', '9822002200', 'suhrcmess@campus.edu');

-- NGOs
INSERT INTO ngo (name, contact_person, phone, email, type) VALUES
('Feeding India', 'Meera Shah', '9999988888', 'feedindia@ngo.org', 'ngo'),
('Food For All', 'Sahil Verma', '9999977777', 'ffa@ngo.org', 'ngo'),
('Helping Hands', 'Aditi Rao', '9999966666', 'hh@ngo.org', 'ngo'),
('Student Volunteers', 'Campus Council', '9999955555', 'stud.vol@campus.edu', 'student_group');

-- Users (mapped role_id: admin=1, canteen=2, ngo=3, student=4)
INSERT INTO users (username, password, email, role_id, ref_id) VALUES
('sit_mess_user', '12345', 'sitmess@campus.edu', 2, 1),
('hilltop_canteen_user', '12345', 'hilltop@campus.edu', 2, 2),
('suhrc_user', '12345', 'suhrc@campus.edu', 2, 3),
('feedingindia', '12345', 'feedingindia@ngo.org', 3, 1),
('ffa_user', '12345', 'ffa@ngo.org', 3, 2),
('admin_user', '12345', 'admin1@campus.edu', 1, NULL);

-- Food
INSERT INTO food (item_name, quantity, unit, expiry_time, canteen_id, status, notes) VALUES
('Paneer Curry', 25, 'plates', DATE_ADD(NOW(), INTERVAL 90 MINUTE), 1, 'available', 'Less spicy'),
('Jeera Rice', 40, 'plates', DATE_ADD(NOW(), INTERVAL 3 HOUR), 1, 'available', NULL),
('Veg Pulao', 30, 'plates', DATE_ADD(NOW(), INTERVAL 1 HOUR), 2, 'available', NULL),
('Bread Rolls', 50, 'pieces', DATE_ADD(NOW(), INTERVAL 5 HOUR), 2, 'available', NULL),
('Lemonade', 20, 'liters', DATE_ADD(NOW(), INTERVAL 1 DAY), 3, 'available', NULL),
('Chicken Biryani', 15, 'plates', DATE_ADD(NOW(), INTERVAL 2 HOUR), 3, 'available', NULL),
('Curd Rice', 20, 'plates', DATE_ADD(NOW(), INTERVAL 30 MINUTE), 1, 'available', NULL),
('Dal Tadka', 35, 'plates', DATE_ADD(NOW(), INTERVAL 7 HOUR), 1, 'available', NULL);

-- Leaderboard
INSERT INTO leaderboard (canteen_id, total_items, donated_items) VALUES
(1, 0, 0), (2, 0, 0), (3, 0, 0);

ALTER TABLE meal_beneficiary DROP FOREIGN KEY meal_beneficiary_ibfk_1;
ALTER TABLE meal_beneficiary ADD CONSTRAINT fk_donation_request FOREIGN KEY (donation_id) REFERENCES donation_request(request_id) ON DELETE CASCADE ON UPDATE CASCADE;
