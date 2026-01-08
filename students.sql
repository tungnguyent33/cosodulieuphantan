-- Recreate the whole schema from scratch
DROP DATABASE IF EXISTS distributed_db;
CREATE DATABASE distributed_db;
USE distributed_db;

-- =========================
-- Core tables (Demo: Students / Subjects / Scores)
-- =========================

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NULL,
    date_of_birth DATE NULL,
    email VARCHAR(120) NULL,
    class_name VARCHAR(50) NULL
);

CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) NOT NULL UNIQUE,
    subject_name VARCHAR(120) NOT NULL,
    credits INT NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS scores (
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    score DECIMAL(4,2) NULL,
    PRIMARY KEY (student_id, subject_id),
    CONSTRAINT fk_scores_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_scores_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- =========================
-- Simple login table for Gradio demo
-- NOTE: plain-text password is ONLY for classroom demo.
-- =========================

CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(100) NOT NULL,
    role ENUM('teacher', 'student') NOT NULL,
    student_id INT NULL,
    CONSTRAINT uq_users_student UNIQUE (student_id),
    CONSTRAINT fk_users_student FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT chk_users_role_student CHECK (
        (role = 'teacher' AND student_id IS NULL)
        OR
        (role = 'student' AND student_id IS NOT NULL)
    )
);

-- =========================
-- Demo data
-- =========================

INSERT INTO students (id, full_name, address, date_of_birth, email, class_name)
VALUES
    (1, 'Nguyễn Văn A', 'Quận 1, TP.HCM', '2004-03-15', 'a@student.edu.vn', 'CS101'),
    (2, 'Trần Thị B', 'Quận 3, TP.HCM', '2004-07-02', 'b@student.edu.vn', 'CS101'),
    (3, 'Lê Văn C', 'Thủ Đức, TP.HCM', '2003-12-20', 'c@student.edu.vn', 'CS102')
ON DUPLICATE KEY UPDATE
    full_name=VALUES(full_name),
    address=VALUES(address),
    date_of_birth=VALUES(date_of_birth),
    email=VALUES(email),
    class_name=VALUES(class_name);

INSERT INTO subjects (id, subject_code, subject_name, credits)
VALUES
    (1, 'DBD', 'Cơ sở dữ liệu phân tán', 3),
    (2, 'DSA', 'Cấu trúc dữ liệu & Giải thuật', 3),
    (3, 'PY', 'Lập trình Python', 2)
ON DUPLICATE KEY UPDATE
    subject_code=VALUES(subject_code),
    subject_name=VALUES(subject_name),
    credits=VALUES(credits);

INSERT INTO scores (student_id, subject_id, score)
VALUES
    (1, 1, 8.50),
    (1, 2, 7.25),
    (1, 3, 9.00),
    (2, 1, 6.75),
    (2, 2, 8.00),
    (3, 1, 7.00)
ON DUPLICATE KEY UPDATE
    score=VALUES(score);

INSERT INTO users (username, password, role, student_id)
VALUES
    ('teacher', 'teacher', 'teacher', NULL),
    ('student1', 'student1', 'student', 1),
    ('student2', 'student2', 'student', 2),
    ('student3', 'student3', 'student', 3)
ON DUPLICATE KEY UPDATE
    password=VALUES(password),
    role=VALUES(role),
    student_id=VALUES(student_id);

-- Create replication user (to be executed on Primary)
DROP USER IF EXISTS 'repl'@'%';
CREATE USER IF NOT EXISTS 'repl'@'%' IDENTIFIED BY 'replpass';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
