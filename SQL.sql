SELECT * FROM webhook_responses ORDER BY 1 DESC;

SELECT * FROM users ORDER BY 1 DESC;

SELECT * FROM webhooks ORDER BY 1 DESC;

SHOW Tables;

-- DROP TABLE webhooks;

-- TRUNCATE TABLE webhook_responses;

USE webhook_db;

CREATE TABLE webhook_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    webhook_id VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    headers JSON NOT NULL,
    body JSON NOT NULL,
    query_params JSON NOT NULL,
    timestamp DATETIME NOT NULL
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);
