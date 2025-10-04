-- Create and use the database

CREATE DATABASE IF NOT EXISTS Hackathon;
USE Hackathon;



-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Applicant CV table
CREATE TABLE IF NOT EXISTS applicant_cv (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    education JSON,
    skills JSON,
    experience JSON,
    experience_years INT,
    projects JSON,
    certifications JSON,
    cv_graph JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    job_level VARCHAR(100) NOT NULL,
    years_experience VARCHAR(50) NOT NULL,
    requirements JSON NOT NULL,
    responsibilities JSON NOT NULL,
    required_certifications JSON,
    job_graph JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    date_offered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    CONSTRAINT chk_status CHECK (status IN ('open', 'closed'))
);


-- Insert values into the departments table
INSERT INTO departments (id, name, email, password)
VALUES 
  (1, 'AI', 'ai@gmail.com', 'ai'),
  (2, 'Finance', 'finance@gmail.com', 'finance'),
  (3, 'Marketing', 'marketing@gmail.com', 'marketing'),
  (4, 'IT', 'it@gmail.com', 'it'),
  (5, 'Sales', 'sales@gmail.com', 'sales'),
  (6, 'Logistics', 'logistics@gmail.com', 'logistics'),
  (7, 'Legal', 'legal@gmail.com', 'legal'),
  (8, 'Operations', 'operations@gmail.com', 'operations'),
  (9, 'R&D', 'rnd@gmail.com', 'rnd'),
  (10, 'Mechanical Engineering', 'mech_eng@gmail.com', 'mech'),
  (11, 'Electrical Engineering', 'elec_eng@gmail.com', 'elec'),
  (12, 'Civil Engineering', 'civil_eng@gmail.com', 'civil'),
  (13, 'Chemical Engineering', 'chem_eng@gmail.com', 'chem'),
  (14, 'Computer Engineering', 'comp_eng@gmail.com', 'comp'),
  (15, 'Software Engineering', 'soft_eng@gmail.com', 'soft'),
  (16, 'Aerospace Engineering', 'aero_eng@gmail.com', 'aero'),
  (17, 'Biomedical Engineering', 'biomed_eng@gmail.com', 'biomed'),
  (18, 'Industrial Engineering', 'indust_eng@gmail.com', 'indust'),
  (19, 'Environmental Engineering', 'env_eng@gmail.com', 'env');