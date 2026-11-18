# Shop Credit Tracker

A local web app for managing customers, recording credit and payments, checking outstanding balances, and sending payment reminder emails manually through Gmail.

## Tech Stack

- **Language:** Python 3.8+
- **Web framework:** Flask 3 with Jinja2 templates and Werkzeug password-hashing utilities
- **Database:** SQLite; the database file is created automatically when the app starts
- **Frontend:** HTML, Tailwind CSS via CDN, and JavaScript with Web Speech API for voice input
- **Gmail integration:** Gmail API with Google OAuth 2.0 (`google-auth`, `google-auth-oauthlib`, and `google-api-python-client`)
- **Optional standalone voice assistant:** SpeechRecognition, PyAudio, and Requests

## Project Structure

```text
app.py                  Application entry point
shop_tracker/
  __init__.py            Flask app factory and blueprint registration
  config.py              Environment-based configuration
  db.py                  SQLite connection and schema setup
  security.py             Password hashing and legacy-hash verification
  gmail_service.py        Gmail OAuth credential helpers
  routes/                 Feature-based Flask blueprints
  templates/              Jinja page templates
seed_data.py              Optional demo-data loader
voice_assistant.py        Optional standalone voice assistant
requirements.txt          Python dependencies
```

## Run Locally

### 1. Install Python dependencies

Use Python 3.8 or newer. From the project folder, create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PyAudio may need operating-system audio development libraries on some platforms. It is used by the optional standalone voice assistant.

### 2. (Optional) Load demo data

```bash
python seed_data.py
```

This creates the demo login `ravi` / `ravi123` and sample customers. **Running the seed script clears existing users, customers, and transactions in `shop_tracker.db`.** Skip this step if you want to preserve existing data.

Without seeded data, the app has no user-registration page; create a user in the database before logging in.

### 3. Start the app

```bash
python app.py
```

The app initializes its SQLite tables on startup. Open [http://localhost:5000](http://localhost:5000) and sign in with the demo login if you seeded the database.

## Gmail Setup (Optional)

Gmail is only needed to send manual reminders. The app can run without connecting Gmail.

1. In Google Cloud Console, create a project, enable the Gmail API, and configure Google Auth Platform.
2. Create an OAuth client ID for a **Web application**.
3. Add this authorized redirect URI to the OAuth client: `http://localhost:5000/oauth2callback`.
4. Download the OAuth client JSON file and save it in the project folder as `credentials.json`.
5. While the OAuth app is in Testing, add each Google account that will authorize it under **Audience → Test users**.
6. Run the app, sign in, open **Gmail**, and connect the desired Google account.

The default callback is for local use. For a hosted deployment, set `OAUTH_REDIRECT_URI` to the public HTTPS callback URL and register the exact same URL in Google Cloud Console. Apps offered publicly with the `gmail.send` scope must complete Google's OAuth verification. External audience alone does not make an app available to all Google accounts.

To use a different Flask session secret, set the `FLASK_SECRET_KEY` environment variable before starting the app. Do not use the built-in development fallback for a public deployment.

## Reminders

The customer page can send a reminder email manually when Gmail is connected and the customer has an email address. Automatic/scheduled reminders are not implemented.

## Voice Assistant

The web interface includes **built-in voice input** using your browser's Web Speech API. No additional setup is needed - just click the "🎤 Voice" button in the chat widget after logging in.

**Standalone Voice Assistant (Optional):**

If you prefer terminal-based voice commands, you can run the standalone script:

```bash
# Terminal 1: Start the web app
python app.py

# Terminal 2: Run the standalone voice assistant
python voice_assistant.py
```

This uses your microphone and connects to the app at `http://localhost:5000`. Requires `SpeechRecognition` and `PyAudio` packages (already in requirements.txt).
