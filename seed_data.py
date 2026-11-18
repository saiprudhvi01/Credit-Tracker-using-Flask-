from datetime import datetime, timedelta

from shop_tracker import create_app
from shop_tracker.db import get_db
from shop_tracker.security import hash_password

def seed():
    app = create_app()
    with app.app_context():
        conn = get_db()

        # Clear existing data before loading the demo dataset.
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM customers")
        conn.execute("DELETE FROM users")

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("ravi", hash_password("ravi123")),
        )
        user_id = cursor.lastrowid

        customers_data = [
            ("Ramesh Kumar", "9876543210", "ramesh@email.com"),
            ("Sita Devi", "9876543211", "sita@email.com"),
            ("Mohammed Ali", "9876543212", "ali@email.com"),
            ("Lakshmi Prasad", "9876543213", None),
            ("Venkat Rao", "9876543214", "venkat@email.com"),
        ]
        customer_ids = []
        for name, phone, email in customers_data:
            cursor = conn.execute(
                "INSERT INTO customers (name, phone, email, user_id) VALUES (?, ?, ?, ?)",
                (name, phone, email, user_id),
            )
            customer_ids.append(cursor.lastrowid)

        transactions_data = [
            (customer_ids[0], 5000, "credit", "Groceries", 5),
            (customer_ids[0], 2000, "payment", "Partial payment", 3),
            (customer_ids[1], 3500, "credit", "Rice and oil", 7),
            (customer_ids[2], 8000, "credit", "Monthly supplies", 10),
            (customer_ids[2], 3000, "payment", "Cash payment", 6),
            (customer_ids[3], 1500, "credit", "Vegetables", 2),
            (customer_ids[4], 6000, "credit", "Wholesale order", 8),
            (customer_ids[4], 1000, "payment", "Online transfer", 4),
        ]
        for customer_id, amount, trans_type, note, days_ago in transactions_data:
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M")
            conn.execute(
                "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
                (customer_id, amount, trans_type, note, date),
            )

        conn.commit()
    
    print("Database seeded successfully!")
    print("Demo login: username = 'ravi', password = 'ravi123'")

if __name__ == "__main__":
    seed()
