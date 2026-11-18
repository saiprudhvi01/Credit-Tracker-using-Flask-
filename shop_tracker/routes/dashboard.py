from datetime import datetime

from flask import Blueprint, redirect, render_template, session, url_for

from shop_tracker.db import get_db


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    user_id = session["user_id"]

    total_customers = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    total_pending = conn.execute("""
        WITH balances AS (
            SELECT
                (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
                (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') AS balance
            FROM customers c
            WHERE c.user_id = ?
        )
        SELECT COALESCE(SUM(CASE WHEN balance > 0 THEN ROUND(balance, 2) ELSE 0 END), 0)
        FROM balances
    """, (user_id,)).fetchone()[0]

    pending_customers = conn.execute("""
        SELECT COUNT(*) FROM customers c WHERE c.user_id = ? AND
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') > 0
    """, (user_id,)).fetchone()[0]

    current_month = datetime.now().strftime("%Y-%m")
    total_received = conn.execute("""
        SELECT COALESCE(SUM(t.amount), 0)
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.user_id = ? AND t.type = 'payment' AND strftime('%Y-%m', t.date) = ?
    """, (user_id, current_month)).fetchone()[0]

    monthly_credits = conn.execute("""
        SELECT COALESCE(SUM(t.amount), 0)
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.user_id = ? AND t.type = 'credit' AND strftime('%Y-%m', t.date) = ?
    """, (user_id, current_month)).fetchone()[0]

    monthly_payments = conn.execute("""
        SELECT COALESCE(SUM(t.amount), 0)
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.user_id = ? AND t.type = 'payment' AND strftime('%Y-%m', t.date) = ?
    """, (user_id, current_month)).fetchone()[0]

    high_pending = conn.execute("""
        WITH balances AS (
            SELECT c.id, c.name,
                   ROUND(
                       (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
                       (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment'),
                       2
                   ) AS pending
            FROM customers c
            WHERE c.user_id = ?
        )
        SELECT id, name, pending
        FROM balances
        WHERE pending > 0 AND pending = (SELECT MAX(pending) FROM balances)
        ORDER BY name
    """, (user_id,)).fetchall()

    recent_transactions = conn.execute("""
        SELECT t.*, c.name AS customer_name
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.user_id = ?
        ORDER BY t.id DESC
        LIMIT 10
    """, (user_id,)).fetchall()

    return render_template(
        "dashboard.html",
        total_customers=total_customers,
        total_pending=round(total_pending, 2),
        pending_customers=pending_customers,
        total_received=round(total_received, 2),
        monthly_credits=round(monthly_credits, 2),
        monthly_payments=round(monthly_payments, 2),
        high_pending=high_pending,
        recent_transactions=recent_transactions,
    )
