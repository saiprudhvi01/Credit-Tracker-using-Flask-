import sqlite3
import hashlib

DB_FILE = "shop_tracker.db"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    conn.commit()
    conn.close()

def seed():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM users")
    
    # Create demo user
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("ravi", hash_password("ravi123"))
    )
    user_id = cursor.lastrowid
    
    # Sample customers
    customers_data = [
        ("Ramesh Kumar", "9876543210", "ramesh@email.com"),
        ("Sita Devi", "9876543211", "sita@email.com"),
        ("Mohammed Ali", "9876543212", "ali@email.com"),
        ("Lakshmi Prasad", "9876543213", None),
        ("Venkat Rao", "9876543214", "venkat@email.com"),
    ]
    
    customer_ids = []
    for name, phone, email in customers_data:
        cursor.execute(
            "INSERT INTO customers (name, phone, email, user_id) VALUES (?, ?, ?, ?)",
            (name, phone, email, user_id)
        )
        customer_ids.append(cursor.lastrowid)
    
    # Sample transactions
    from datetime import datetime, timedelta
    
    transactions_data = [
        (customer_ids[0], 5000, "credit", "Groceries", (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[0], 2000, "payment", "Partial payment", (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[1], 3500, "credit", "Rice and oil", (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[2], 8000, "credit", "Monthly supplies", (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[2], 3000, "payment", "Cash payment", (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[3], 1500, "credit", "Vegetables", (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[4], 6000, "credit", "Wholesale order", (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M")),
        (customer_ids[4], 1000, "payment", "Online transfer", (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d %H:%M")),
    ]
    
    for cust_id, amount, trans_type, note, date in transactions_data:
        cursor.execute(
            "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
            (cust_id, amount, trans_type, note, date)
        )
    
    conn.commit()
    conn.close()
    
    print("Database seeded successfully!")
    print("Demo login: username = 'ravi', password = 'ravi123'")

if __name__ == "__main__":
    seed()
