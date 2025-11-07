DROP DATABASE IF EXISTS campus_food_waste;
CREATE DATABASE campus_food_waste;
USE campus_food_waste;

CREATE TABLE roles (
  role_id INT PRIMARY KEY AUTO_INCREMENT,
  role_name ENUM('admin','canteen','ngo','student') NOT NULL UNIQUE
);

CREATE TABLE canteen (
  canteen_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  location VARCHAR(100) NOT NULL,
  contact_no VARCHAR(15),
  email VARCHAR(100) UNIQUE
);

CREATE TABLE ngo (
  ngo_id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  contact_person VARCHAR(100),
  phone VARCHAR(15),
  email VARCHAR(100) UNIQUE,
  type ENUM('ngo','student_group') DEFAULT 'ngo'
);

CREATE TABLE users (
  user_id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  role_id INT NOT NULL,
  ref_id INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (role_id) REFERENCES roles(role_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

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

CREATE TABLE leaderboard (
  lb_id INT PRIMARY KEY AUTO_INCREMENT,
  canteen_id INT NOT NULL UNIQUE,
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

CREATE TABLE login_activity (
  activity_id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  logout_time DATETIME,
  ip_address VARCHAR(45),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE meal_beneficiary (
  beneficiary_id INT PRIMARY KEY AUTO_INCREMENT,
  donation_id INT NOT NULL,
  people_served INT NOT NULL,
  location VARCHAR(100),
  recorded_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (donation_id) REFERENCES donation_request(request_id)
    ON UPDATE CASCADE ON DELETE CASCADE
);

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

INSERT INTO roles (role_name)
VALUES ('admin'), ('canteen'), ('ngo'), ('student');

INSERT INTO canteen (name, location, contact_no, email)
VALUES
('Symbi Central Canteen', 'Main Block - Ground Floor', '9876543210', 'centralcanteen@sit.edu'),
('Hostel Food Court', 'Hostel Zone', '9765432109', 'hostelcanteen@sit.edu'),
('Tech Café', 'Innovation Centre', '9988776655', 'techcafe@sit.edu');

INSERT INTO ngo (name, contact_person, phone, email, type)
VALUES
('Feeding Hands', 'Amit Sharma', '9812345678', 'feedinghands@gmail.com', 'ngo'),
('Green Plate', 'Priya Desai', '9822334455', 'greenplate@gmail.com', 'ngo'),
('Helping Hearts', 'Raj Mehta', '9898765432', 'helpinghearts@gmail.com', 'student_group');

INSERT INTO users (username, password, email, role_id)
VALUES ('admin1', 'admin@123', 'admin@sit.edu', 1);

INSERT INTO users (username, password, email, role_id, ref_id)
VALUES 
('canteen_central', 'canteen@123', 'centralcanteen@sit.edu', 2, 1),
('canteen_hostel', 'canteen@123', 'hostelcanteen@sit.edu', 2, 2),
('canteen_tech', 'canteen@123', 'techcafe@sit.edu', 2, 3);

INSERT INTO users (username, password, email, role_id, ref_id)
VALUES 
('ngo_feedinghands', 'ngo@123', 'feedinghands@gmail.com', 3, 1),
('ngo_greenplate', 'ngo@123', 'greenplate@gmail.com', 3, 2),
('ngo_helpinghearts', 'ngo@123', 'helpinghearts@gmail.com', 3, 3);

INSERT INTO users (username, password, email, role_id)
VALUES
('student_raj', 'student@123', 'raj@student.edu', 4),
('student_kavya', 'student@123', 'kavya@student.edu', 4);

INSERT INTO food (canteen_id, item_name, category, quantity, unit, expiry_time, status)
VALUES
(1, 'Veg Thali', 'Vegetarian', 15, 'plates', DATE_ADD(NOW(), INTERVAL 2 HOUR), 'available'),
(1, 'Idli Sambar', 'Vegetarian', 20, 'plates', DATE_ADD(NOW(), INTERVAL 3 HOUR), 'available'),
(2, 'Paneer Roll', 'Vegetarian', 10, 'pieces', DATE_ADD(NOW(), INTERVAL 1 HOUR), 'available'),
(3, 'Cold Coffee', 'Beverage', 25, 'cups', DATE_ADD(NOW(), INTERVAL 4 HOUR), 'available'),
(3, 'Veg Sandwich', 'Vegetarian', 12, 'pieces', DATE_ADD(NOW(), INTERVAL 30 MINUTE), 'expired'),
(1, 'Chicken Biryani', 'Non-Vegetarian', 30, 'plates', DATE_ADD(NOW(), INTERVAL 2 HOUR), 'available'),
(2, 'Masala Dosa', 'Vegetarian', 25, 'plates', DATE_ADD(NOW(), INTERVAL 1 HOUR), 'available'),
(3, 'Pasta', 'Vegetarian', 10, 'plates', DATE_ADD(NOW(), INTERVAL 5 HOUR), 'available'),
(1, 'Samosa', 'Vegetarian', 50, 'pieces', DATE_ADD(NOW(), INTERVAL 6 HOUR), 'available'),
(2, 'Chole Bhature', 'Vegetarian', 15, 'plates', DATE_ADD(NOW(), INTERVAL 3 HOUR), 'available'),
(3, 'Brownie', 'Bakery', 20, 'pieces', DATE_ADD(NOW(), INTERVAL 12 HOUR), 'available'),
(1, 'Dal Fry', 'Vegetarian', 10, 'plates', DATE_ADD(NOW(), INTERVAL 2 HOUR), 'available'),
(2, 'Veg Pulao', 'Vegetarian', 20, 'plates', DATE_ADD(NOW(), INTERVAL 4 HOUR), 'available'),
(3, 'Iced Tea', 'Beverage', 30, 'cups', DATE_ADD(NOW(), INTERVAL 24 HOUR), 'available'),
(1, 'Gulab Jamun', 'Other', 40, 'pieces', DATE_ADD(NOW(), INTERVAL 48 HOUR), 'available'),
(2, 'Misal Pav', 'Vegetarian', 15, 'plates', DATE_ADD(NOW(), INTERVAL 1 HOUR), 'available');


INSERT INTO donation_request (food_id, ngo_id, status) VALUES (1, 1, 'approved');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (2, 2, 'pending');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (3, 3, 'completed');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (4, 1, 'rejected');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (6, 2, 'pending');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (7, 1, 'approved');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (8, 3, 'pending');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (9, 2, 'approved');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (10, 1, 'pending');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (11, 3, 'rejected');
INSERT INTO donation_request (food_id, ngo_id, status) VALUES (12, 2, 'pending');

INSERT INTO leaderboard (canteen_id, total_items, donated_items)
VALUES (1, 0, 0), (2, 0, 0), (3, 0, 0);

INSERT INTO meal_beneficiary (donation_id, people_served, location)
VALUES
(1, 25, 'Sinhgad NGO Center'),
(3, 20, 'Orphanage Home Pune'),
(7, 22, 'City Shelter');

INSERT INTO waste_report (food_id, reported_by, reason, quantity_wasted)
VALUES
(5, 2, 'spoilage', 12),
(4, 3, 'late_pickup', 5),
(11, 3, 'over_preparation', 10);

INSERT INTO audit_log (action, table_name, record_id, performed_by)
VALUES ('Seeded admin user', 'users', 1, 1);
INSERT INTO login_activity (user_id, ip_address) VALUES (1, '127.0.0.1');