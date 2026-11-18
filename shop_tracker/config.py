import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")
    DATABASE = os.environ.get("DATABASE_PATH", str(BASE_DIR / "shop_tracker.db"))
    GOOGLE_CLIENT_FILE = os.environ.get(
        "GOOGLE_CLIENT_FILE", str(BASE_DIR / "credentials.json")
    )
    GMAIL_TOKEN_DIR = os.environ.get(
        "GMAIL_TOKEN_DIR", str(BASE_DIR / "gmail_tokens")
    )
    OAUTH_REDIRECT_URI = os.environ.get(
        "OAUTH_REDIRECT_URI", "http://localhost:5000/oauth2callback"
    )
