-- Create the database (SQLite does not use CREATE DATABASE)

-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    dp TEXT
);

-- Create transactions table
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date_submitted TEXT NOT NULL,
    payment_method TEXT NOT NULL, -- Use TEXT instead of ENUM
    txn_id TEXT NOT NULL,
    receipt TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);