
import os
import sqlite3
import base64
import hashlib
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")

oauth_flows = {}

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

CLIENT_FILE = "credentials.json"
TOKEN_FILE = "token.json"
DB_FILE = "shop_tracker.db"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.execute('''
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


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Shop Credit Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div id="loading" class="fixed inset-0 bg-white flex items-center justify-center z-50">
        <div class="text-center">
            <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600 mx-auto"></div>
            <p class="mt-4 text-gray-600">Loading...</p>
        </div>
    </div>
    
    <div class="max-w-md mx-auto p-4">
        {% if session.user_id %}
        <nav class="bg-white rounded-lg shadow p-4 mb-4 flex justify-between items-center">
            <h1 class="text-xl font-bold text-green-700">Ravi's Shop</h1>
            <div class="flex gap-2">
                <a href="/" class="text-sm text-gray-600">Home</a>
                <a href="/customers" class="text-sm text-gray-600">Customers</a>
                <a href="/logout" class="text-sm text-red-600">Logout</a>
            </div>
        </nav>
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <script>
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
        }, 500);
    </script>
</body>
</html>
'''

LOGIN_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-8">
    <h2 class="text-2xl font-bold text-gray-800 mb-6 text-center">Login</h2>
    {% if message %}
    <div class="bg-red-100 text-red-700 p-3 rounded mb-4">{{ message }}</div>
    {% endif %}
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required
            class="w-full p-3 border rounded mb-3">
        <input type="password" name="password" placeholder="Password" required
            class="w-full p-3 border rounded mb-3">
        <button type="submit" class="w-full bg-green-600 text-white p-3 rounded font-semibold hover:bg-green-700">
            Login
        </button>
    </form>
</div>
''')

HOME_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Dashboard</h2>
    <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-blue-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">Total Customers</p>
            <p class="text-2xl font-bold text-blue-700">{{ total_customers }}</p>
        </div>
        <div class="bg-red-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">Total Pending</p>
            <p class="text-2xl font-bold text-red-700">₹{{ total_pending }}</p>
        </div>
    </div>
    <div class="flex gap-2">
        <a href="/add_customer" class="flex-1 bg-green-600 text-white p-3 rounded text-center font-semibold hover:bg-green-700">
            + Add Customer
        </a>
        <a href="/add_transaction" class="flex-1 bg-blue-600 text-white p-3 rounded text-center font-semibold hover:bg-blue-700">
            + Add Entry
        </a>
    </div>
</div>

<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h3 class="text-lg font-bold text-gray-800 mb-4">Recent Transactions</h3>
    {% if recent_transactions %}
    <div class="space-y-3">
        {% for t in recent_transactions %}
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded">
            <div>
                <p class="font-semibold">{{ t.customer_name }}</p>
                <p class="text-sm text-gray-500">{{ t.date }}</p>
            </div>
            <div class="text-right">
                <p class="font-bold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                    {% if t.type == 'credit' %}-{% else %}+{% endif %}₹{{ t.amount }}
                </p>
                {% if t.email %}
                <button onclick="sendReminder({{ t.customer_id }}, '{{ t.email }}', {{ t.pending_amount }})" 
                    class="text-xs text-blue-600 hover:underline">Send Reminder</button>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500 text-center">No transactions yet</p>
    {% endif %}
</div>

<script>
function sendReminder(customerId, email, amount) {
    if (confirm('Send payment reminder to ' + email + '?')) {
        fetch('/send_reminder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({customer_id: customerId, email: email, amount: amount})
        }).then(r => r.json()).then(data => {
            alert(data.message);
        });
    }
}
</script>
''')


CUSTOMERS_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Customers</h2>
    <a href="/add_customer" class="block bg-green-600 text-white p-3 rounded text-center font-semibold hover:bg-green-700 mb-4">
        + Add Customer
    </a>
    {% if customers %}
    <div class="space-y-3">
        {% for c in customers %}
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded">
            <div>
                <p class="font-semibold">{{ c.name }}</p>
                <p class="text-sm text-gray-500">{{ c.phone or 'No phone' }}</p>
            </div>
            <div class="text-right">
                <p class="font-bold text-red-600">₹{{ c.pending }}</p>
                <a href="/customer/{{ c.id }}" class="text-xs text-blue-600 hover:underline">View</a>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500 text-center">No customers yet</p>
    {% endif %}
</div>
''')

ADD_CUSTOMER_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Add Customer</h2>
    <form method="POST">
        <input type="text" name="name" placeholder="Customer Name" required
            class="w-full p-3 border rounded mb-3">
        <input type="text" name="phone" placeholder="Phone (optional)"
            class="w-full p-3 border rounded mb-3">
        <input type="email" name="email" placeholder="Email (optional)"
            class="w-full p-3 border rounded mb-3">
        <button type="submit" class="w-full bg-green-600 text-white p-3 rounded font-semibold hover:bg-green-700">
            Add Customer
        </button>
        <a href="/" class="block text-center text-gray-600 mt-3">Cancel</a>
    </form>
</div>
''')

ADD_TRANSACTION_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Add Entry</h2>
    <form method="POST">
        <label class="block text-sm font-semibold mb-1">Customer</label>
        <select name="customer_id" required class="w-full p-3 border rounded mb-3">
            <option value="">Select customer</option>
            {% for c in customers %}
            <option value="{{ c.id }}">{{ c.name }} (Pending: ₹{{ c.pending }})</option>
            {% endfor %}
        </select>
        <label class="block text-sm font-semibold mb-1">Type</label>
        <select name="type" required class="w-full p-3 border rounded mb-3">
            <option value="credit">Credit (they owe you)</option>
            <option value="payment">Payment (they paid you)</option>
        </select>
        <input type="number" name="amount" placeholder="Amount (₹)" required min="1"
            class="w-full p-3 border rounded mb-3">
        <input type="text" name="note" placeholder="Note (optional)"
            class="w-full p-3 border rounded mb-3">
        <button type="submit" class="w-full bg-blue-600 text-white p-3 rounded font-semibold hover:bg-blue-700">
            Add Entry
        </button>
        <a href="/" class="block text-center text-gray-600 mt-3">Cancel</a>
    </form>
</div>
''')

CUSTOMER_DETAIL_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-2">{{ customer.name }}</h2>
    <p class="text-gray-600 mb-4">{{ customer.phone or 'No phone' }} | {{ customer.email or 'No email' }}</p>
    <div class="bg-red-50 p-4 rounded mb-4">
        <p class="text-sm text-gray-600">Total Pending</p>
        <p class="text-3xl font-bold text-red-700">₹{{ pending }}</p>
    </div>
    <a href="/add_transaction?customer_id={{ customer.id }}" 
        class="block bg-blue-600 text-white p-3 rounded text-center font-semibold hover:bg-blue-700 mb-4">
        + Add Entry
    </a>
    {% if customer.email %}
    <button onclick="sendReminder({{ customer.id }}, '{{ customer.email }}', {{ pending }})" 
        class="w-full bg-green-600 text-white p-3 rounded font-semibold hover:bg-green-700 mb-4">
        Send Payment Reminder
    </button>
    {% endif %}
</div>

<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h3 class="text-lg font-bold text-gray-800 mb-4">Transaction History</h3>
    {% if transactions %}
    <div class="space-y-3">
        {% for t in transactions %}
        <div class="flex justify-between items-center p-3 bg-gray-50 rounded">
            <div>
                <p class="font-semibold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                    {% if t.type == 'credit' %}Credit{% else %}Payment{% endif %}
                </p>
                <p class="text-sm text-gray-500">{{ t.date }}</p>
                {% if t.note %}<p class="text-sm text-gray-400">{{ t.note }}</p>{% endif %}
            </div>
            <p class="font-bold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                {% if t.type == 'credit' %}-{% else %}+{% endif %}₹{{ t.amount }}
            </p>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="text-gray-500 text-center">No transactions yet</p>
    {% endif %}
</div>

<script>
function sendReminder(customerId, email, amount) {
    if (confirm('Send payment reminder to ' + email + '?')) {
        fetch('/send_reminder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({customer_id: customerId, email: email, amount: amount})
        }).then(r => r.json()).then(data => {
            alert(data.message);
        });
    }
}
</script>
''')

GMAIL_SETUP_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="bg-white rounded-lg shadow p-6 mt-4">
    <h2 class="text-2xl font-bold text-gray-800 mb-4">Gmail Setup</h2>
    {% if message %}
    <div class="bg-blue-100 text-blue-700 p-3 rounded mb-4">{{ message }}</div>
    {% endif %}
    {% if not connected %}
    <a href="/authorize" class="block bg-green-600 text-white p-3 rounded text-center font-semibold hover:bg-green-700">
        Connect Gmail
    </a>
    {% else %}
    <p class="text-green-600 font-semibold mb-4">Gmail is connected!</p>
    <a href="/" class="block bg-blue-600 text-white p-3 rounded text-center font-semibold hover:bg-blue-700">
        Go to Dashboard
    </a>
    {% endif %}
</div>
''')


def get_credentials():
    if not os.path.exists(TOKEN_FILE):
        return None

    creds = Credentials.from_authorized_user_file(
        TOKEN_FILE, SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds if creds.valid else None


@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    user_id = session["user_id"]
    
    total_customers = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    
    total_pending = conn.execute("""
        SELECT COALESCE(SUM(t.amount), 0) 
        FROM transactions t 
        JOIN customers c ON t.customer_id = c.id 
        WHERE c.user_id = ? AND t.type = 'credit'
    """, (user_id,)).fetchone()[0]
    
    recent_transactions = conn.execute("""
        SELECT t.*, c.name as customer_name, c.email, 
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = t.customer_id AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = t.customer_id AND type = 'payment') as pending_amount
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.user_id = ?
        ORDER BY t.id DESC
        LIMIT 10
    """, (user_id,)).fetchall()
    
    conn.close()
    
    return render_template_string(
        HOME_HTML,
        total_customers=total_customers,
        total_pending=int(total_pending),
        recent_transactions=recent_transactions
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        
        if user and user["password_hash"] == hash_password(password):
            session["user_id"] = user["id"]
            return redirect(url_for("home"))
        else:
            return render_template_string(LOGIN_HTML, message="Invalid username or password")
    
    return render_template_string(LOGIN_HTML)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/customers")
def customers():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    user_id = session["user_id"]
    
    customers = conn.execute("""
        SELECT c.*, 
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') as pending
        FROM customers c
        WHERE c.user_id = ?
        ORDER BY c.name
    """, (user_id,)).fetchall()
    
    conn.close()
    
    return render_template_string(CUSTOMERS_HTML, customers=customers)


@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        
        conn = get_db()
        conn.execute(
            "INSERT INTO customers (name, phone, email, user_id) VALUES (?, ?, ?, ?)",
            (name, phone, email, session["user_id"])
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for("customers"))
    
    return render_template_string(ADD_CUSTOMER_HTML)


@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    user_id = session["user_id"]
    
    if request.method == "POST":
        customer_id = request.form["customer_id"]
        trans_type = request.form["type"]
        amount = float(request.form["amount"])
        note = request.form.get("note", "").strip() or None
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn.execute(
            "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
            (customer_id, amount, trans_type, note, date)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for("home"))
    
    customers = conn.execute("""
        SELECT c.*, 
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') as pending
        FROM customers c
        WHERE c.user_id = ?
        ORDER BY c.name
    """, (user_id,)).fetchall()
    
    conn.close()
    
    preselected = request.args.get("customer_id")
    return render_template_string(ADD_TRANSACTION_HTML, customers=customers, preselected=preselected)


@app.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"])
    ).fetchone()
    
    if not customer:
        conn.close()
        return "Customer not found", 404
    
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE customer_id = ? ORDER BY id DESC",
        (customer_id,)
    ).fetchall()
    
    pending = conn.execute("""
        SELECT (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = 'payment')
    """, (customer_id, customer_id)).fetchone()[0]
    
    conn.close()
    
    return render_template_string(
        CUSTOMER_DETAIL_HTML,
        customer=customer,
        transactions=transactions,
        pending=int(pending or 0)
    )


@app.route("/send_reminder", methods=["POST"])
def send_reminder():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    data = request.get_json()
    email = data.get("email")
    amount = data.get("amount")
    customer_id = data.get("customer_id")
    
    conn = get_db()
    customer = conn.execute(
        "SELECT name FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"])
    ).fetchone()
    conn.close()
    
    if not customer:
        return jsonify({"success": False, "message": "Customer not found"})
    
    creds = get_credentials()
    if not creds:
        return jsonify({"success": False, "message": "Gmail not connected. Please setup Gmail first."})
    
    message_text = f"""
Hello {customer['name']},

This is a gentle reminder that Rs. {amount}
is pending from your account at our shop.

Kindly make the payment whenever convenient.
Thank you for your support!

- Ravi
"""
    
    message = MIMEText(message_text)
    message["to"] = email
    message["subject"] = "Payment Reminder - Ravi's Shop"
    
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        service = build("gmail", "v1", credentials=creds)
        result = service.users().messages().send(
            userId="me",
            body={"raw": encoded_message}
        ).execute()
        return jsonify({"success": True, "message": "Reminder sent successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to send: {str(e)}"})


@app.route("/gmail_setup")
def gmail_setup():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    connected = get_credentials() is not None
    return render_template_string(GMAIL_SETUP_HTML, connected=connected, message=session.pop("message", None))


@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:5000/oauth2callback",
        autogenerate_code_verifier=True
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    oauth_flows[state] = flow
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    flow = oauth_flows.pop(state, None)
    if not flow:
        return "OAuth request not found. Please restart Gmail authorization.", 400

    try:
        flow.fetch_token(
            authorization_response=request.url
        )
        credentials = flow.credentials
        with open(TOKEN_FILE, "w") as token:
            token.write(credentials.to_json())
        session["message"] = "Gmail connected successfully!"
        return redirect(url_for("gmail_setup"))
    except Exception as e:
        return f"Google authorization failed: {str(e)}", 400


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)
