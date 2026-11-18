import base64
import os
from email.mime.text import MIMEText

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from shop_tracker.db import get_db
from shop_tracker.gmail_service import (
    SCOPES,
    get_account_email,
    get_credentials,
    token_file_for_user,
)


gmail_bp = Blueprint("gmail", __name__)
pending_oauth_flows = {}


@gmail_bp.route("/send_reminder", methods=["POST"])
def send_reminder():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json() or {}
    email = data.get("email")
    amount = data.get("amount")
    customer_id = data.get("customer_id")

    customer = get_db().execute(
        "SELECT name FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    ).fetchone()
    if not customer:
        return jsonify({"success": False, "message": "Customer not found"})

    credentials = get_credentials(session["user_id"])
    if not credentials:
        return jsonify({
            "success": False,
            "message": "Gmail not connected. Please setup Gmail first.",
        })

    message_text = f"""Hello {customer['name']},

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
        service = build("gmail", "v1", credentials=credentials)
        service.users().messages().send(
            userId="me", body={"raw": encoded_message}
        ).execute()
        return jsonify({"success": True, "message": "Reminder sent successfully!"})
    except Exception as error:
        return jsonify({"success": False, "message": f"Failed to send: {error}"})


@gmail_bp.route("/gmail_setup")
def gmail_setup():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    credentials = get_credentials(session["user_id"])
    return render_template(
        "gmail_setup.html",
        connected=credentials is not None,
        account_email=get_account_email(credentials) if credentials else None,
        message=session.pop("message", None),
    )


@gmail_bp.route("/authorize")
def authorize():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    flow = Flow.from_client_secrets_file(
        current_app.config["GOOGLE_CLIENT_FILE"],
        scopes=SCOPES,
        redirect_uri=current_app.config["OAUTH_REDIRECT_URI"],
        autogenerate_code_verifier=True,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent select_account",
    )
    pending_oauth_flows[state] = {"flow": flow, "user_id": session["user_id"]}
    return redirect(authorization_url)


@gmail_bp.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    flow_record = pending_oauth_flows.pop(state, None)
    if not flow_record:
        return "OAuth request not found. Please restart Gmail authorization.", 400

    try:
        flow = flow_record["flow"]
        callback_url = current_app.config["OAUTH_REDIRECT_URI"]
        flow.fetch_token(
            authorization_response=f"{callback_url}?{request.query_string.decode('ascii')}"
        )
        os.makedirs(current_app.config["GMAIL_TOKEN_DIR"], exist_ok=True)
        with open(token_file_for_user(flow_record["user_id"]), "w", encoding="utf-8") as token:
            token.write(flow.credentials.to_json())
        session["message"] = "Gmail connected successfully!"
        return redirect(url_for("gmail.gmail_setup"))
    except Exception as error:
        current_app.logger.exception("Google OAuth callback failed")
        return f"Google authorization failed: {error}", 400
