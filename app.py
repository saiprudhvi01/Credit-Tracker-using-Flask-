
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover { transition: all 0.3s ease; }
        .card-hover:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .fade-in { animation: fadeIn 0.5s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .stat-card { background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%); }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <div id="loading" class="fixed inset-0 bg-white flex items-center justify-center z-50">
        <div class="text-center">
            <div class="relative">
                <div class="animate-spin rounded-full h-20 w-20 border-4 border-purple-200"></div>
                <div class="animate-spin rounded-full h-20 w-20 border-4 border-purple-600 border-t-transparent absolute top-0 left-0"></div>
            </div>
            <p class="mt-6 text-gray-600 font-medium">Loading your shop...</p>
        </div>
    </div>
    
    <div class="max-w-6xl mx-auto p-4 md:p-8">
        {% if session.user_id %}
        <nav class="bg-white/80 backdrop-blur-lg rounded-2xl shadow-lg p-4 md:p-6 mb-6 flex flex-col md:flex-row justify-between items-center gap-4 fade-in">
            <div class="flex items-center gap-3">
                <div class="w-12 h-12 gradient-bg rounded-xl flex items-center justify-center">
                    <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                </div>
                <div>
                    <h1 class="text-xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Ravi's Shop</h1>
                    <p class="text-xs text-gray-500">Credit Tracker</p>
                </div>
            </div>
            <div class="flex gap-1 md:gap-2 bg-gray-100 rounded-xl p-1">
                <a href="/" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/' %}bg-white shadow text-purple-600{% else %}text-gray-600 hover:text-gray-900%}">Dashboard</a>
                <a href="/customers" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/customers' %}bg-white shadow text-purple-600{% else %}text-gray-600 hover:text-gray-900%}">Customers</a>
                <a href="/gmail_setup" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/gmail_setup' %}bg-white shadow text-purple-600{% else %}text-gray-600 hover:text-gray-900%}">Gmail</a>
                <a href="/logout" class="px-4 py-2 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 transition-all">Logout</a>
            </div>
        </nav>
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <script>
        setTimeout(() => {
            const loading = document.getElementById('loading');
            loading.style.opacity = '0';
            loading.style.transition = 'opacity 0.3s ease';
            setTimeout(() => loading.style.display = 'none', 300);
        }, 600);
    </script>
</body>
</html>
'''

LOGIN_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="flex items-center justify-center min-h-[80vh]">
    <div class="bg-white rounded-3xl shadow-2xl p-8 md:p-12 w-full max-w-md fade-in card-hover">
        <div class="text-center mb-8">
            <div class="w-20 h-20 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                </svg>
            </div>
            <h2 class="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Welcome Back</h2>
            <p class="text-gray-500 mt-2">Sign in to manage your shop</p>
        </div>
        {% if message %}
        <div class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl mb-6 flex items-center gap-3">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
            {{ message }}
        </div>
        {% endif %}
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Username</label>
                <input type="text" name="username" placeholder="Enter username" required
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Password</label>
                <input type="password" name="password" placeholder="Enter password" required
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <button type="submit" class="w-full gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg">
                Sign In
            </button>
        </form>
    </div>
</div>
''')

HOME_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 fade-in">
    <div class="stat-card rounded-2xl shadow-lg p-6 card-hover border border-gray-100">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm font-medium text-gray-500 mb-1">Total Customers</p>
                <p class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">{{ total_customers }}</p>
            </div>
            <div class="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center">
                <svg class="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
            </div>
        </div>
    </div>
    <div class="stat-card rounded-2xl shadow-lg p-6 card-hover border border-gray-100">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm font-medium text-gray-500 mb-1">Total Pending</p>
                <p class="text-4xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent">₹{{ total_pending }}</p>
            </div>
            <div class="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center">
                <svg class="w-7 h-7 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            </div>
        </div>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <a href="/add_customer" class="bg-white rounded-2xl shadow-lg p-6 card-hover border border-gray-100 flex items-center gap-4 group">
        <div class="w-14 h-14 gradient-bg rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
            </svg>
        </div>
        <div>
            <h3 class="text-lg font-bold text-gray-800">Add Customer</h3>
            <p class="text-sm text-gray-500">Register a new customer</p>
        </div>
    </a>
    <a href="/add_transaction" class="bg-white rounded-2xl shadow-lg p-6 card-hover border border-gray-100 flex items-center gap-4 group">
        <div class="w-14 h-14 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
            </svg>
        </div>
        <div>
            <h3 class="text-lg font-bold text-gray-800">Add Entry</h3>
            <p class="text-sm text-gray-500">Record credit or payment</p>
        </div>
    </a>
</div>

<div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 fade-in">
    <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-bold text-gray-800">Recent Transactions</h3>
        <span class="text-sm text-gray-500">Last 10 entries</span>
    </div>
    {% if recent_transactions %}
    <div class="space-y-4">
        {% for t in recent_transactions %}
        <div class="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-100 card-hover">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 {% if t.type == 'credit' %}bg-red-100{% else %}bg-green-100{% endif %} rounded-xl flex items-center justify-center">
                    {% if t.type == 'credit' %}
                    <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path></svg>
                    {% else %}
                    <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                    {% endif %}
                </div>
                <div>
                    <p class="font-semibold text-gray-800">{{ t.customer_name }}</p>
                    <p class="text-sm text-gray-500">{{ t.date }}</p>
                </div>
            </div>
            <div class="text-right">
                <p class="text-xl font-bold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                    {% if t.type == 'credit' %}-{% else %}+{% endif %}₹{{ t.amount }}
                </p>
                {% if t.email %}
                <button onclick="sendReminder({{ t.customer_id }}, '{{ t.email }}', {{ t.pending_amount }})" 
                    class="text-sm text-purple-600 hover:text-purple-700 font-medium mt-1 flex items-center gap-1 ml-auto">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                    Remind
                </button>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
        </div>
        <p class="text-gray-500">No transactions yet</p>
        <a href="/add_transaction" class="inline-block mt-4 text-purple-600 font-medium hover:text-purple-700">Add your first entry</a>
    </div>
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
<div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 fade-in">
    <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800">Customers</h2>
        <a href="/add_customer" class="gradient-bg text-white px-5 py-2.5 rounded-xl font-medium hover:opacity-90 transition-all flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
            Add Customer
        </a>
    </div>
    {% if customers %}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for c in customers %}
        <a href="/customer/{{ c.id }}" class="bg-gradient-to-br from-gray-50 to-white p-5 rounded-xl border border-gray-100 card-hover">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                        <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800">{{ c.name }}</p>
                        <p class="text-sm text-gray-500">{{ c.phone or 'No phone' }}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-xl font-bold {% if c.pending > 0 %}text-red-600{% else %}text-green-600{% endif %}">₹{{ c.pending }}</p>
                    <p class="text-xs text-gray-500">pending</p>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
        </div>
        <p class="text-gray-500">No customers yet</p>
        <a href="/add_customer" class="inline-block mt-4 text-purple-600 font-medium hover:text-purple-700">Add your first customer</a>
    </div>
    {% endif %}
</div>
''')

ADD_CUSTOMER_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="max-w-xl mx-auto">
    <div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path></svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-800">Add Customer</h2>
            <p class="text-gray-500 mt-1">Register a new customer</p>
        </div>
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Customer Name</label>
                <input type="text" name="name" placeholder="Enter customer name" required
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Phone (optional)</label>
                <input type="text" name="phone" placeholder="Enter phone number"
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Email (optional)</label>
                <input type="email" name="email" placeholder="Enter email address"
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <button type="submit" class="w-full gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg mb-3">
                Add Customer
            </button>
            <a href="/customers" class="block text-center text-gray-600 hover:text-gray-800 font-medium">Cancel</a>
        </form>
    </div>
</div>
''')

ADD_TRANSACTION_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="max-w-xl mx-auto">
    <div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-800">Add Entry</h2>
            <p class="text-gray-500 mt-1">Record credit or payment</p>
        </div>
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Customer</label>
                <select name="customer_id" required class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
                    <option value="">Select customer</option>
                    {% for c in customers %}
                    <option value="{{ c.id }}" {% if preselected == c.id|string %}selected{% endif %}>{{ c.name }} (Pending: ₹{{ c.pending }})</option>
                    {% endfor %}
                </select>
            </div>
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Type</label>
                <select name="type" required class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
                    <option value="credit">Credit (they owe you)</option>
                    <option value="payment">Payment (they paid you)</option>
                </select>
            </div>
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Amount (₹)</label>
                <input type="number" name="amount" placeholder="Enter amount" required min="1"
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 mb-2">Note (optional)</label>
                <input type="text" name="note" placeholder="Add a note"
                    class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <button type="submit" class="w-full bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg mb-3">
                Add Entry
            </button>
            <a href="/" class="block text-center text-gray-600 hover:text-gray-800 font-medium">Cancel</a>
        </form>
    </div>
</div>
''')

CUSTOMER_DETAIL_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 fade-in">
    <div class="lg:col-span-1">
        <div class="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
            <div class="text-center mb-6">
                <div class="w-20 h-20 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                </div>
                <h2 class="text-2xl font-bold text-gray-800">{{ customer.name }}</h2>
                <p class="text-gray-500">{{ customer.phone or 'No phone' }}</p>
                <p class="text-gray-500">{{ customer.email or 'No email' }}</p>
            </div>
            <div class="bg-gradient-to-br from-red-50 to-pink-50 p-6 rounded-2xl mb-4">
                <p class="text-sm font-medium text-gray-600 mb-1">Total Pending</p>
                <p class="text-4xl font-bold text-red-600">₹{{ pending }}</p>
            </div>
            <div class="space-y-3">
                <a href="/add_transaction?customer_id={{ customer.id }}" 
                    class="block bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all text-center">
                    + Add Entry
                </a>
                {% if customer.email %}
                <button onclick="sendReminder({{ customer.id }}, '{{ customer.email }}', {{ pending }})" 
                    class="w-full gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all">
                    Send Payment Reminder
                </button>
                {% endif %}
                <a href="/customers" class="block text-center text-gray-600 hover:text-gray-800 font-medium py-2">Back to Customers</a>
            </div>
        </div>
    </div>
    <div class="lg:col-span-2">
        <div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100">
            <h3 class="text-xl font-bold text-gray-800 mb-6">Transaction History</h3>
            {% if transactions %}
            <div class="space-y-4">
                {% for t in transactions %}
                <div class="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-100">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 {% if t.type == 'credit' %}bg-red-100{% else %}bg-green-100{% endif %} rounded-xl flex items-center justify-center">
                            {% if t.type == 'credit' %}
                            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path></svg>
                            {% else %}
                            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                            {% endif %}
                        </div>
                        <div>
                            <p class="font-semibold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                                {% if t.type == 'credit' %}Credit{% else %}Payment{% endif %}
                            </p>
                            <p class="text-sm text-gray-500">{{ t.date }}</p>
                            {% if t.note %}<p class="text-sm text-gray-400">{{ t.note }}</p>{% endif %}
                        </div>
                    </div>
                    <p class="text-xl font-bold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                        {% if t.type == 'credit' %}-{% else %}+{% endif %}₹{{ t.amount }}
                    </p>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-12">
                <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                </div>
                <p class="text-gray-500">No transactions yet</p>
            </div>
            {% endif %}
        </div>
    </div>
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
<div class="max-w-xl mx-auto">
    <div class="bg-white rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-800">Gmail Setup</h2>
            <p class="text-gray-500 mt-1">Connect your Gmail for payment reminders</p>
        </div>
        {% if message %}
        <div class="bg-blue-50 border border-blue-200 text-blue-700 p-4 rounded-xl mb-6 flex items-center gap-3">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>
            {{ message }}
        </div>
        {% endif %}
        {% if not connected %}
        <a href="/authorize" class="block gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg text-center">
            Connect Gmail
        </a>
        {% else %}
        <div class="bg-green-50 border border-green-200 p-6 rounded-xl mb-6 text-center">
            <div class="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <p class="text-green-700 font-semibold text-lg">Gmail is connected!</p>
            <p class="text-green-600 text-sm mt-1">You can now send payment reminders</p>
        </div>
        <a href="/" class="block bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg text-center">
            Go to Dashboard
        </a>
        {% endif %}
    </div>
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
