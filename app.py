
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
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <style>
        * { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover { transition: all 0.3s ease; }
        .card-hover:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .fade-in { animation: fadeIn 0.5s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .stat-card { background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%); }
        .dark .stat-card { background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%); }
        .dark .bg-white { background-color: #1e293b !important; }
        .dark .bg-gray-50 { background-color: #0f172a !important; }
        .dark .bg-gray-100 { background-color: #334155 !important; }
        .dark .text-gray-800 { color: #f1f5f9 !important; }
        .dark .text-gray-500 { color: #94a3b8 !important; }
        .dark .text-gray-600 { color: #cbd5e1 !important; }
        .dark .text-gray-700 { color: #e2e8f0 !important; }
        .dark .border-gray-100 { border-color: #334155 !important; }
        .dark .border-gray-200 { border-color: #475569 !important; }
        .dark .from-gray-50 { --tw-gradient-from: #0f172a !important; }
        .dark .to-white { --tw-gradient-to: #1e293b !important; }
        .chat-bubble { animation: bubbleIn 0.3s ease-out; }
        @keyframes bubbleIn { from { opacity: 0; transform: scale(0.8); } to { opacity: 1; transform: scale(1); } }
        .pulse-ring { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(139, 92, 246, 0); } 100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); } }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 min-h-screen transition-colors duration-300">
    <div id="loading" class="fixed inset-0 bg-white dark:bg-slate-900 flex items-center justify-center z-50">
        <div class="text-center">
            <div class="relative">
                <div class="animate-spin rounded-full h-20 w-20 border-4 border-purple-200"></div>
                <div class="animate-spin rounded-full h-20 w-20 border-4 border-purple-600 border-t-transparent absolute top-0 left-0"></div>
            </div>
            <p class="mt-6 text-gray-600 dark:text-gray-400 font-medium">Loading your shop...</p>
        </div>
    </div>
    
    <div class="max-w-6xl mx-auto p-4 md:p-8">
        {% if session.user_id %}
        <nav class="bg-white/80 dark:bg-slate-800/80 backdrop-blur-lg rounded-2xl shadow-lg p-4 md:p-6 mb-6 flex flex-col md:flex-row justify-between items-center gap-4 fade-in">
            <div class="flex items-center gap-3">
                <div class="w-12 h-12 gradient-bg rounded-xl flex items-center justify-center">
                    <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                </div>
                <div>
                    <h1 class="text-xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Ravi's Shop</h1>
                    <p class="text-xs text-gray-500 dark:text-gray-400">Credit Tracker</p>
                </div>
            </div>
            <div class="flex gap-1 md:gap-2 bg-gray-100 dark:bg-slate-700 rounded-xl p-1">
                <a href="/" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/' %}bg-white dark:bg-slate-600 shadow text-purple-600{% else %}text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white{% endif %}">📊 Dashboard</a>
                <a href="/customers" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/customers' %}bg-white dark:bg-slate-600 shadow text-purple-600{% else %}text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white{% endif %}">👥 Customers</a>
                <a href="/gmail_setup" class="px-4 py-2 rounded-lg text-sm font-medium transition-all {% if request.path == '/gmail_setup' %}bg-white dark:bg-slate-600 shadow text-purple-600{% else %}text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white{% endif %}">📧 Gmail</a>
                <button onclick="toggleDarkMode()" class="px-4 py-2 rounded-lg text-sm font-medium transition-all text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                    🌙/☀️
                </button>
                <button onclick="toggleChat()" class="px-4 py-2 rounded-lg text-sm font-medium transition-all bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90">
                    🎤 Voice
                </button>
                <a href="/logout" class="px-4 py-2 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all">🚪 Logout</a>
            </div>
        </nav>
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <script>
        if (localStorage.getItem('darkMode') === 'true' || (!('darkMode' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        }
        function toggleDarkMode() {
            document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
        }
        setTimeout(() => {
            const loading = document.getElementById('loading');
            loading.style.opacity = '0';
            loading.style.transition = 'opacity 0.3s ease';
            setTimeout(() => loading.style.display = 'none', 300);
        }, 600);
        
        function toggleChat() {
            const chat = document.getElementById('voiceChat');
            chat.classList.toggle('hidden');
            if (!chat.classList.contains('hidden')) {
                const input = document.getElementById('chatInput');
                input.focus();
                // Remove existing listener if any
                input.removeEventListener('keypress', handleKeyPress);
                // Add new listener
                input.addEventListener('keypress', handleKeyPress);
            }
        }
        
        let recognition;
        let isListening = false;
        let speechSupported = false;
        
        // Check if speech recognition is supported
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            speechSupported = true;
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = function() {
                isListening = true;
                const btn = document.querySelector('[onclick="startVoiceInput()"]');
                if (btn) {
                    btn.classList.add('animate-pulse');
                    btn.innerHTML = '🔴';
                }
                addMessage('system', '🎤 Listening... Speak now');
            };
            
            recognition.onresult = function(event) {
                let finalTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    }
                }
                if (finalTranscript) {
                    document.getElementById('chatInput').value = finalTranscript;
                    sendMessage();
                }
            };
            
            recognition.onerror = function(event) {
                isListening = false;
                const btn = document.querySelector('[onclick="startVoiceInput()"]');
                if (btn) {
                    btn.classList.remove('animate-pulse');
                    btn.innerHTML = '🎤';
                }
                
                let errorMsg = 'Could not understand. Please try again.';
                if (event.error === 'no-speech') {
                    errorMsg = 'No speech detected. Speak clearly into your microphone.';
                } else if (event.error === 'audio-capture') {
                    errorMsg = 'Microphone not found. Check your device settings.';
                } else if (event.error === 'not-allowed') {
                    errorMsg = 'Microphone access denied. Allow microphone access in browser settings.';
                } else if (event.error === 'network') {
                    errorMsg = 'Network error. Voice recognition requires internet connection.';
                } else if (event.error === 'aborted') {
                    errorMsg = 'Recording was stopped.';
                }
                
                console.error('Speech recognition error:', event.error, event.message);
                addMessage('system', '❌ ' + errorMsg);
            };
            
            recognition.onend = function() {
                isListening = false;
                const btn = document.querySelector('[onclick="startVoiceInput()"]');
                if (btn) {
                    btn.classList.remove('animate-pulse');
                    btn.innerHTML = '🎤';
                }
            };
        } else {
            console.log('Speech recognition not supported in this browser');
        }
        
        function startVoiceInput() {
            if (isListening) {
                recognition.stop();
                return;
            }
            
            if (!speechSupported) {
                alert('Voice input is not supported in this browser. Please use Chrome or Edge, or type your command instead.');
                return;
            }
            
            if (recognition) {
                try {
                    recognition.start();
                } catch (e) {
                    console.error('Error starting recognition:', e);
                    addMessage('system', '❌ Error starting microphone. Please try typing instead.');
                }
            } else {
                addMessage('system', '❌ Voice recognition not available. Please type your command.');
            }
        }
        
        function addMessage(type, text) {
            const chatMessages = document.getElementById('chatMessages');
            const div = document.createElement('div');
            div.className = 'chat-bubble p-3 rounded-lg mb-2 max-w-[80%] ' + 
                (type === 'user' ? 'bg-purple-500 text-white ml-auto' : 
                 type === 'system' ? 'bg-gray-200 dark:bg-slate-700 text-gray-800 dark:text-white mx-auto text-center text-sm' :
                 'bg-white dark:bg-slate-700 text-gray-800 dark:text-white border border-gray-200 dark:border-slate-600');
            div.innerHTML = text;
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;
            
            addMessage('user', text);
            input.value = '';
            
            try {
                const response = await fetch('/api/voice-command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: text })
                });
                const data = await response.json();
                addMessage('bot', data.message);
            } catch (error) {
                addMessage('bot', 'Error processing command');
            }
        }
        
        function handleKeyPress(e) {
            if (e.key === 'Enter') sendMessage();
        }
    </script>
    
    <div id="voiceChat" class="hidden fixed bottom-6 right-6 w-96 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-slate-700 z-40">
        <div class="p-4 border-b border-gray-200 dark:border-slate-700 flex justify-between items-center">
            <h3 class="font-bold text-gray-800 dark:text-white">🎤 Voice Assistant</h3>
            <button onclick="toggleChat()" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white">✕</button>
        </div>
        <div id="chatMessages" class="h-64 overflow-y-auto p-4 space-y-2">
            <div class="chat-bubble bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-white p-3 rounded-lg text-sm">
                <strong>💡 Simple Format:</strong><br><br>
                <span class="text-red-600 font-semibold">➕ CREDIT (they owe you):</span><br>
                Use: <em>+</em> or <em>plus</em><br>
                Example: "Venkat + 500"<br><br>
                <span class="text-green-600 font-semibold">➖ PAYMENT (they paid you):</span><br>
                Use: <em>-</em> or <em>minus</em><br>
                Example: "Venkat - 1000"<br><br>
                <em>Format: [Name] [+/-] [amount]</em>
            </div>
        </div>
        <div class="p-4 border-t border-gray-200 dark:border-slate-700 flex gap-2">
            <button onclick="startVoiceInput()" class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl flex items-center justify-center hover:opacity-90 transition-all pulse-ring">
                🎤
            </button>
            <input type="text" id="chatInput" placeholder="e.g., Venkat + 500 or Venkat - 1000" onkeypress="if(event.key==='Enter')sendMessage()"
                class="flex-1 px-4 py-2 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none">
            <button onclick="sendMessage()" class="px-4 py-2 bg-purple-500 text-white rounded-xl hover:opacity-90 transition-all">
                Send
            </button>
        </div>
    </div>
</body>
</html>
'''

LOGIN_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="flex items-center justify-center min-h-[80vh]">
    <div class="bg-white dark:bg-slate-800 rounded-3xl shadow-2xl p-8 md:p-12 w-full max-w-md fade-in card-hover">
        <div class="text-center mb-8">
            <div class="w-20 h-20 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">👤</span>
            </div>
            <h2 class="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">Welcome Back</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-2">Sign in to manage your shop</p>
        </div>
        {% if message %}
        <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 p-4 rounded-xl mb-6 flex items-center gap-3">
            <span class="text-xl">⚠️</span>
            {{ message }}
        </div>
        {% endif %}
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Username</label>
                <input type="text" name="username" placeholder="Enter username" required
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Password</label>
                <input type="password" name="password" placeholder="Enter password" required
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
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
    <div class="stat-card dark:bg-slate-800 rounded-2xl shadow-lg p-6 card-hover border border-gray-100 dark:border-slate-700">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">👥 Total Customers</p>
                <p class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">{{ total_customers }}</p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Registered in your shop</p>
            </div>
            <div class="w-14 h-14 bg-blue-100 dark:bg-blue-900/50 rounded-2xl flex items-center justify-center">
                <span class="text-3xl">👥</span>
            </div>
        </div>
    </div>
    <div class="stat-card dark:bg-slate-800 rounded-2xl shadow-lg p-6 card-hover border border-gray-100 dark:border-slate-700 {% if total_pending > 0 %}ring-2 ring-red-200 dark:ring-red-800{% endif %}">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">💰 Total Pending</p>
                <p class="text-4xl font-bold bg-gradient-to-r from-red-600 to-pink-600 bg-clip-text text-transparent">₹{{ total_pending }}</p>
                {% if total_pending > 0 %}
                <p class="text-xs text-red-500 dark:text-red-400 mt-1 font-medium">⚠️ Money to collect</p>
                {% else %}
                <p class="text-xs text-green-500 dark:text-green-400 mt-1 font-medium">✅ All settled!</p>
                {% endif %}
            </div>
            <div class="w-14 h-14 {% if total_pending > 0 %}bg-red-100 dark:bg-red-900/50{% else %}bg-green-100 dark:bg-green-900/50{% endif %} rounded-2xl flex items-center justify-center">
                <span class="text-3xl">{% if total_pending > 0 %}💸{% else %}✅{% endif %}</span>
            </div>
        </div>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <a href="/add_customer" class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 card-hover border border-gray-100 dark:border-slate-700 flex items-center gap-4 group">
        <div class="w-14 h-14 gradient-bg rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
            <span class="text-3xl">➕</span>
        </div>
        <div>
            <h3 class="text-lg font-bold text-gray-800 dark:text-white">Add Customer</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Register a new customer</p>
        </div>
    </a>
    <a href="/add_transaction" class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 card-hover border border-gray-100 dark:border-slate-700 flex items-center gap-4 group">
        <div class="w-14 h-14 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
            <span class="text-3xl">📝</span>
        </div>
        <div>
            <h3 class="text-lg font-bold text-gray-800 dark:text-white">Add Entry</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">Record credit or payment</p>
        </div>
    </a>
</div>

<div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
    <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-bold text-gray-800 dark:text-white">📋 Recent Transactions</h3>
        <span class="text-sm text-gray-500 dark:text-gray-400">Last 10 entries</span>
    </div>
    {% if recent_transactions %}
    <div class="space-y-4">
        {% for t in recent_transactions %}
        <div class="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white dark:from-slate-700 dark:to-slate-800 rounded-xl border border-gray-100 dark:border-slate-600 card-hover">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 {% if t.type == 'credit' %}bg-red-100{% else %}bg-green-100{% endif %} rounded-xl flex items-center justify-center">
                    <span class="text-2xl">{% if t.type == 'credit' %}➖{% else %}➕{% endif %}</span>
                </div>
                <div>
                    <p class="font-semibold text-gray-800 dark:text-white">{{ t.customer_name }}</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{{ t.date }}</p>
                    <span class="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full {% if t.type == 'credit' %}bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300{% else %}bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300{% endif %}">
                        {% if t.type == 'credit' %}❌ CREDIT (THEY OWE){% else %}✅ PAYMENT (PAID){% endif %}
                    </span>
                </div>
            </div>
            <div class="text-right">
                <p class="text-xl font-bold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                    {% if t.type == 'credit' %}-{% else %}+{% endif %}₹{{ t.amount }}
                </p>
                {% if t.email %}
                <button onclick="sendReminder({{ t.customer_id }}, '{{ t.email }}', {{ t.pending_amount }})" 
                    class="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium mt-1 flex items-center gap-1 ml-auto">
                    📧 Remind
                </button>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span class="text-4xl">📋</span>
        </div>
        <p class="text-gray-500 dark:text-gray-400">No transactions yet</p>
        <a href="/add_transaction" class="inline-block mt-4 text-purple-600 dark:text-purple-400 font-medium hover:text-purple-700 dark:hover:text-purple-300">Add your first entry</a>
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
<div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
    <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-800 dark:text-white">👥 Customers</h2>
        <a href="/add_customer" class="gradient-bg text-white px-5 py-2.5 rounded-xl font-medium hover:opacity-90 transition-all flex items-center gap-2">
            ➕ Add Customer
        </a>
    </div>
    {% if customers %}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for c in customers %}
        <a href="/customer/{{ c.id }}" class="bg-gradient-to-br from-gray-50 to-white dark:from-slate-700 dark:to-slate-800 p-5 rounded-xl border border-gray-100 dark:border-slate-600 card-hover">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 bg-purple-100 dark:bg-purple-900/50 rounded-xl flex items-center justify-center">
                        <span class="text-2xl">👤</span>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800 dark:text-white">{{ c.name }}</p>
                        <p class="text-sm text-gray-500 dark:text-gray-400">{{ c.phone or 'No phone' }}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-xl font-bold {% if c.pending > 0 %}text-red-600{% else %}text-green-600{% endif %}">₹{{ c.pending }}</p>
                    <span class="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full {% if c.pending > 0 %}bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300{% else %}bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300{% endif %}">
                        {% if c.pending > 0 %}❌ PENDING{% else %}✅ CLEAR{% endif %}
                    </span>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-12">
        <div class="w-16 h-16 bg-gray-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span class="text-4xl">👥</span>
        </div>
        <p class="text-gray-500 dark:text-gray-400">No customers yet</p>
        <a href="/add_customer" class="inline-block mt-4 text-purple-600 dark:text-purple-400 font-medium hover:text-purple-700 dark:hover:text-purple-300">Add your first customer</a>
    </div>
    {% endif %}
</div>
''')

ADD_CUSTOMER_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="max-w-xl mx-auto">
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">👤</span>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-white">Add Customer</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-1">Register a new customer</p>
        </div>
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">👤 Customer Name</label>
                <input type="text" name="name" placeholder="Enter customer name" required
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">📱 Phone (optional)</label>
                <input type="text" name="phone" placeholder="Enter phone number"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">📧 Email (optional)</label>
                <input type="email" name="email" placeholder="Enter email address"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <button type="submit" class="w-full gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg mb-3">
                ➕ Add Customer
            </button>
            <a href="/customers" class="block text-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white font-medium">❌ Cancel</a>
        </form>
    </div>
</div>
''')

ADD_TRANSACTION_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="max-w-xl mx-auto">
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
        <div class="text-center mb-6">
            <div class="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">📝</span>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-white">Quick Entry</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-1">Record credit or payment</p>
        </div>

        <form method="POST" id="transactionForm">
            <div class="mb-4">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">👤 Customer</label>
                <select name="customer_id" id="customerSelect" required class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
                    <option value="">Select customer</option>
                    {% for c in customers %}
                    <option value="{{ c.id }}" {% if preselected == c.id|string %}selected{% endif %}>{{ c.name }} (Pending: ₹{{ c.pending }})</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">💰 Type</label>
                <div class="grid grid-cols-2 gap-3">
                    <label class="cursor-pointer">
                        <input type="radio" name="type" value="credit" id="creditType" class="hidden peer" required>
                        <div class="peer-checked:bg-red-500 peer-checked:text-white peer-checked:border-red-500 bg-white dark:bg-slate-700 border-2 border-gray-200 dark:border-slate-600 rounded-xl p-4 text-center transition-all">
                            <span class="text-2xl block mb-1">➖</span>
                            <span class="font-semibold">Gave Credit</span>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">They owe you</p>
                        </div>
                    </label>
                    <label class="cursor-pointer">
                        <input type="radio" name="type" value="payment" id="paymentType" class="hidden peer">
                        <div class="peer-checked:bg-green-500 peer-checked:text-white peer-checked:border-green-500 bg-white dark:bg-slate-700 border-2 border-gray-200 dark:border-slate-600 rounded-xl p-4 text-center transition-all">
                            <span class="text-2xl block mb-1">➕</span>
                            <span class="font-semibold">Got Payment</span>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">They paid you</p>
                        </div>
                    </label>
                </div>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">💵 Amount (₹)</label>
                <input type="number" name="amount" id="amountInput" placeholder="Enter amount" required min="1"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none text-2xl font-bold text-center">
                <div class="grid grid-cols-4 gap-2 mt-3">
                    <button type="button" onclick="setAmount(100)" class="bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg py-2 font-semibold text-gray-700 dark:text-gray-300 transition-all">₹100</button>
                    <button type="button" onclick="setAmount(500)" class="bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg py-2 font-semibold text-gray-700 dark:text-gray-300 transition-all">₹500</button>
                    <button type="button" onclick="setAmount(1000)" class="bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg py-2 font-semibold text-gray-700 dark:text-gray-300 transition-all">₹1000</button>
                    <button type="button" onclick="setAmount(2000)" class="bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg py-2 font-semibold text-gray-700 dark:text-gray-300 transition-all">₹2000</button>
                </div>
            </div>
            
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">📝 Note (optional)</label>
                <input type="text" name="note" id="noteInput" placeholder="Add a note"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            
            <button type="submit" class="w-full bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg mb-3">
                📝 Save Entry
            </button>
            <a href="/" class="block text-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white font-medium">❌ Cancel</a>
        </form>
    </div>
</div>

<script>
function setAmount(amount) {
    document.getElementById('amountInput').value = amount;
}
</script>
''')

CUSTOMER_DETAIL_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 fade-in">
    <div class="lg:col-span-1">
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-100 dark:border-slate-700">
            <div class="text-center mb-6">
                <div class="w-20 h-20 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <span class="text-4xl">👤</span>
                </div>
                <h2 class="text-2xl font-bold text-gray-800 dark:text-white">{{ customer.name }}</h2>
                <p class="text-gray-500 dark:text-gray-400">📱 {{ customer.phone or 'No phone' }}</p>
                <p class="text-gray-500 dark:text-gray-400">📧 {{ customer.email or 'No email' }}</p>
            </div>
            <div class="bg-gradient-to-br {% if pending > 0 %}from-red-50 to-pink-50 dark:from-red-900/30 dark:to-pink-900/30{% else %}from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30{% endif %} p-6 rounded-2xl mb-4">
                <p class="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">💰 Total Pending</p>
                <p class="text-4xl font-bold {% if pending > 0 %}text-red-600{% else %}text-green-600{% endif %}">₹{{ pending }}</p>
                <span class="inline-block mt-2 px-3 py-1 text-sm font-medium rounded-full {% if pending > 0 %}bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300{% else %}bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300{% endif %}">
                    {% if pending > 0 %}❌ MONEY TO COLLECT{% else %}✅ ALL SETTLED{% endif %}
                </span>
            </div>
            <div class="space-y-3">
                <a href="/add_transaction?customer_id={{ customer.id }}" 
                    class="block bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all text-center">
                    📝 + Add Entry
                </a>
                <a href="/edit_customer/{{ customer.id }}" 
                    class="block bg-gradient-to-br from-amber-500 to-orange-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all text-center">
                    ✏️ Edit Customer
                </a>
                {% if customer.email %}
                <button onclick="sendReminder({{ customer.id }}, '{{ customer.email }}', {{ pending }})" 
                    class="w-full gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all">
                    📧 Send Payment Reminder
                </button>
                {% endif %}
                <a href="/customers" class="block text-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white font-medium py-2">⬅️ Back to Customers</a>
            </div>
        </div>
    </div>
    <div class="lg:col-span-2">
        <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700">
            <h3 class="text-xl font-bold text-gray-800 dark:text-white mb-6">📋 Transaction History</h3>
            {% if transactions %}
            <div class="space-y-4">
                {% for t in transactions %}
                <div class="flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-white dark:from-slate-700 dark:to-slate-800 rounded-xl border border-gray-100 dark:border-slate-600">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 {% if t.type == 'credit' %}bg-red-100{% else %}bg-green-100{% endif %} rounded-xl flex items-center justify-center">
                            <span class="text-2xl">{% if t.type == 'credit' %}➖{% else %}➕{% endif %}</span>
                        </div>
                        <div>
                            <p class="font-semibold {% if t.type == 'credit' %}text-red-600{% else %}text-green-600{% endif %}">
                                {% if t.type == 'credit' %}❌ CREDIT (THEY OWE){% else %}✅ PAYMENT (PAID){% endif %}
                            </p>
                            <p class="text-sm text-gray-500 dark:text-gray-400">{{ t.date }}</p>
                            {% if t.note %}<p class="text-sm text-gray-400 dark:text-gray-500">📝 {{ t.note }}</p>{% endif %}
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
                <div class="w-16 h-16 bg-gray-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <span class="text-4xl">📋</span>
                </div>
                <p class="text-gray-500 dark:text-gray-400">No transactions yet</p>
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
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">📧</span>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-white">Gmail Setup</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-1">Connect your Gmail for payment reminders</p>
        </div>
        {% if message %}
        <div class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 p-4 rounded-xl mb-6 flex items-center gap-3">
            <span class="text-xl">ℹ️</span>
            {{ message }}
        </div>
        {% endif %}
        {% if not connected %}
        <a href="/authorize" class="block gradient-bg text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg text-center">
            🔗 Connect Gmail
        </a>
        {% else %}
        <div class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 p-6 rounded-xl mb-6 text-center">
            <div class="w-16 h-16 bg-green-100 dark:bg-green-900/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">✅</span>
            </div>
            <p class="text-green-700 dark:text-green-300 font-semibold text-lg">Gmail is connected!</p>
            <p class="text-green-600 dark:text-green-400 text-sm mt-1">You can now send payment reminders</p>
        </div>
        <a href="/" class="block bg-gradient-to-br from-cyan-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg text-center">
            🏠 Go to Dashboard
        </a>
        {% endif %}
    </div>
</div>
''')

EDIT_CUSTOMER_HTML = HTML.replace('{% block content %}{% endblock %}', '''
<div class="max-w-xl mx-auto">
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 md:p-8 border border-gray-100 dark:border-slate-700 fade-in">
        <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span class="text-4xl">✏️</span>
            </div>
            <h2 class="text-2xl font-bold text-gray-800 dark:text-white">Edit Customer</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-1">Update customer details</p>
        </div>
        <form method="POST">
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">👤 Customer Name</label>
                <input type="text" name="name" value="{{ customer.name }}" required
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-5">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">📱 Phone (optional)</label>
                <input type="text" name="phone" value="{{ customer.phone or '' }}" placeholder="Enter phone number"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <div class="mb-6">
                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">📧 Email (optional)</label>
                <input type="email" name="email" value="{{ customer.email or '' }}" placeholder="Enter email address"
                    class="w-full px-4 py-3 border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-800 dark:text-white rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none">
            </div>
            <button type="submit" class="w-full bg-gradient-to-br from-amber-500 to-orange-600 text-white py-3 rounded-xl font-semibold hover:opacity-90 transition-all transform hover:scale-[1.02] shadow-lg mb-3">
                ✏️ Save Changes
            </button>
            <a href="/customer/{{ customer.id }}" class="block text-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white font-medium">❌ Cancel</a>
        </form>
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


@app.route("/edit_customer/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
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
    
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        
        conn.execute(
            "UPDATE customers SET name = ?, phone = ?, email = ? WHERE id = ?",
            (name, phone, email, customer_id)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for("customer_detail", customer_id=customer_id))
    
    conn.close()
    return render_template_string(EDIT_CUSTOMER_HTML, customer=customer)


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


# API endpoints for Voice Assistant
@app.route("/api/customers")
def api_customers():
    if "user_id" not in session:
        return jsonify([])
    
    conn = get_db()
    customers = conn.execute(
        "SELECT id, name FROM customers WHERE user_id = ? ORDER BY name",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    
    return jsonify([{"id": c["id"], "name": c["name"]} for c in customers])


@app.route("/api/transaction", methods=["POST"])
def api_add_transaction():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    data = request.get_json()
    customer_id = data.get("customer_id")
    trans_type = data.get("type")
    amount = float(data.get("amount", 0))
    note = data.get("note")
    
    if not customer_id or not trans_type or not amount:
        return jsonify({"success": False, "message": "Missing required fields"})
    
    conn = get_db()
    
    # Verify customer belongs to user
    customer = conn.execute(
        "SELECT id FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"])
    ).fetchone()
    
    if not customer:
        conn.close()
        return jsonify({"success": False, "message": "Customer not found"})
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
        (customer_id, amount, trans_type, note, date)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Transaction added successfully"})


@app.route("/api/voice-command", methods=["POST"])
def api_voice_command():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in first"})
    
    data = request.get_json()
    command = data.get("command", "").lower().strip()
    
    # Parse command with + and - symbols
    import re
    
    # Get all customers for fuzzy matching
    conn = get_db()
    customers = conn.execute(
        "SELECT id, name FROM customers WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()
    customer_map = {c["name"].lower(): c["id"] for c in customers}
    
    # Try to find customer name in command
    customer_name = None
    customer_id = None
    
    for cust_name, cust_id in customer_map.items():
        if cust_name in command or command in cust_name:
            customer_name = cust_name
            customer_id = cust_id
            break
    
    # Determine transaction type based on + or - symbol
    trans_type = None
    
    if '+' in command or 'plus' in command:
        trans_type = 'credit'  # They owe you (add to balance)
    elif '-' in command or 'minus' in command:
        trans_type = 'payment'  # They paid you (subtract from balance)
    
    # Extract amount (find first number)
    amount_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)', command)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else None
    
    # If we have customer and amount, proceed
    if customer_id and amount and trans_type:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
            (customer_id, amount, trans_type, f'Voice: {command}', date)
        )
        conn.commit()
        
        # Get actual customer name for display
        actual_name = next(c["name"] for c in customers if c["id"] == customer_id)
        
        # Friendly response
        if trans_type == 'credit':
            response = f"✅ Added ₹{amount} credit for {actual_name} (+)"
        else:
            response = f"✅ Added ₹{amount} payment from {actual_name} (-)"
        
        conn.close()
        return jsonify({"success": True, "message": response})
    
    # Provide helpful error messages
    if not customer_name:
        conn.close()
        available_names = ", ".join([c["name"] for c in customers[:5]])
        if len(customers) > 5:
            available_names += f", and {len(customers) - 5} more"
        return jsonify({
            "success": False, 
            "message": f"🤔 Customer not found. Available: {available_names}"
        })
    
    if not amount:
        conn.close()
        return jsonify({
            "success": False, 
            "message": "💰 No amount found. Include a number."
        })
    
    if not trans_type:
        conn.close()
        return jsonify({
            "success": False, 
            "message": "🤷 Use + for credit or - for payment.<br><br>Example: 'Venkat + 500' or 'Venkat - 1000'"
        })
    
    conn.close()
    return jsonify({"success": False, "message": "🤔 Could not understand. Try: 'Venkat + 500' or 'Venkat - 1000'"})


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)
