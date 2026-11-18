from flask import Blueprint, redirect, render_template, request, session, url_for

from shop_tracker.db import get_db
from shop_tracker.security import hash_password, needs_password_rehash, verify_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and verify_password(user["password_hash"], password):
            if needs_password_rehash(user["password_hash"]):
                conn = get_db()
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (hash_password(password), user["id"]),
                )
                conn.commit()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard.home"))
        return render_template("login.html", message="Invalid username or password")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    message = None
    conn = get_db()
    
    if request.method == "POST":
        reminder_days = int(request.form.get("reminder_days", 30))
        reminder_amount = int(request.form.get("reminder_amount", 5000))
        
        conn.execute("""
            INSERT OR REPLACE INTO settings (user_id, reminder_days, reminder_amount)
            VALUES (?, ?, ?)
        """, (session["user_id"], reminder_days, reminder_amount))
        conn.commit()
        message = "Settings saved successfully."
    
    settings = conn.execute(
        "SELECT * FROM settings WHERE user_id = ?", (session["user_id"],)
    ).fetchone()
    
    return render_template("settings.html", message=message, settings=settings)
