import os

from flask import current_app
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def token_file_for_user(user_id):
    return os.path.join(current_app.config["GMAIL_TOKEN_DIR"], f"gmail_{int(user_id)}.json")


def get_credentials(user_id):
    token_file = token_file_for_user(user_id)
    if not os.path.exists(token_file):
        return None

    credentials = Credentials.from_authorized_user_file(token_file, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        with open(token_file, "w", encoding="utf-8") as token:
            token.write(credentials.to_json())

    return credentials if credentials.valid else None


def get_account_email(credentials):
    try:
        profile = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        return profile.userinfo().get().execute().get("email")
    except Exception:
        # Older authorizations may need to be reconnected to grant the email scope.
        return None
