-- Smart Traffic Prediction and Route Recommendation System
-- MySQL Database Schema

CREATE DATABASE IF NOT EXISTS smart_traffic_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smart_traffic_db;

-- Users table
CREATE TABLE IF NOT EXISTS Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    city VARCHAR(100) DEFAULT 'Mumbai',
    phone_number VARCHAR(20),
    route_preference VARCHAR(50) DEFAULT 'fastest',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active TINYINT(1) DEFAULT 1,
    INDEX idx_users_email (email),
    INDEX idx_users_username (username)
) ENGINE=InnoDB;

-- Predictions table
CREATE TABLE IF NOT EXISTS Predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    city VARCHAR(100) NOT NULL,
    source_location VARCHAR(200),
    destination_location VARCHAR(200),
    travel_date VARCHAR(20),
    travel_time VARCHAR(10),
    weather_condition VARCHAR(50),
    temperature DECIMAL(5,2),
    visibility DECIMAL(6,2),
    festival_indicator TINYINT(1) DEFAULT 0,
    peak_hour_indicator TINYINT(1) DEFAULT 0,
    road_type VARCHAR(50),
    num_lanes INT DEFAULT 2,
    traffic_density DECIMAL(5,2),
    predicted_congestion ENUM('Low', 'Medium', 'High') NOT NULL,
    confidence_score DECIMAL(5,4),
    traffic_risk ENUM('Low', 'Medium', 'High') DEFAULT 'Medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    INDEX idx_predictions_user (user_id),
    INDEX idx_predictions_city (city),
    INDEX idx_predictions_created (created_at)
) ENGINE=InnoDB;

-- Travel History table
CREATE TABLE IF NOT EXISTS Travel_History (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_location VARCHAR(200) NOT NULL,
    destination_location VARCHAR(200) NOT NULL,
    route_name VARCHAR(50),
    predicted_congestion ENUM('Low', 'Medium', 'High'),
    risk_score DECIMAL(5,2),
    travel_difficulty ENUM('Easy', 'Moderate', 'Difficult'),
    distance_km DECIMAL(8,2),
    estimated_time_min INT,
    weather_condition VARCHAR(50),
    travel_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    INDEX idx_history_user (user_id),
    INDEX idx_history_date (travel_date)
) ENGINE=InnoDB;

-- Saved Routes table
CREATE TABLE IF NOT EXISTS Saved_Routes (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    route_name VARCHAR(100) NOT NULL,
    source_location VARCHAR(200) NOT NULL,
    destination_location VARCHAR(200) NOT NULL,
    preferred_route VARCHAR(50) DEFAULT 'Route A',
    source_lat DECIMAL(10,7),
    source_lng DECIMAL(10,7),
    dest_lat DECIMAL(10,7),
    dest_lng DECIMAL(10,7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP NULL,
    use_count INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    INDEX idx_saved_routes_user (user_id)
) ENGINE=InnoDB;

-- Feedback table
CREATE TABLE IF NOT EXISTS Feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    prediction_id INT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    feedback_type ENUM('prediction', 'route', 'general') DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (prediction_id) REFERENCES Predictions(prediction_id) ON DELETE SET NULL,
    INDEX idx_feedback_user (user_id)
) ENGINE=InnoDB;

-- Geocode Cache table
CREATE TABLE IF NOT EXISTS Geocode_Cache (
    query_text VARCHAR(255) PRIMARY KEY,
    resolved_name VARCHAR(255) NOT NULL,
    lat DECIMAL(10,7) NOT NULL,
    lng DECIMAL(10,7) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Route Cache table
CREATE TABLE IF NOT EXISTS Route_Cache (
    route_key VARCHAR(255) PRIMARY KEY,
    route_data LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Sample user (password: password123) - hash generated at runtime
-- INSERT handled by init script

