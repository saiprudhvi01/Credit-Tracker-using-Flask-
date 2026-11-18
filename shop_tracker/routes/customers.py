from datetime import datetime

from flask import Blueprint, redirect, render_template, request, session, url_for

from shop_tracker.db import get_db


customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/customers")
def customers():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    rows = get_db().execute("""
        SELECT c.*,
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') AS pending
        FROM customers c
        WHERE c.user_id = ?
        ORDER BY c.name
    """, (session["user_id"],)).fetchall()
    return render_template("customers.html", customers=rows)


@customers_bp.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM customers WHERE LOWER(name) = LOWER(?) AND user_id = ?",
            (name, session["user_id"]),
        ).fetchone()

        if existing:
            error = "Customer with this name already exists!"
        else:
            conn.execute(
                "INSERT INTO customers (name, phone, email, user_id) VALUES (?, ?, ?, ?)",
                (name, phone, email, session["user_id"]),
            )
            conn.commit()
            return redirect(url_for("customers.customers"))

    return render_template("add_customer.html", error=error)


@customers_bp.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    if request.method == "POST":
        customer_id = request.form["customer_id"]
        trans_type = request.form["type"]
        amount = float(request.form["amount"])
        note = request.form.get("note", "").strip() or None
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
            (customer_id, amount, trans_type, note, date),
        )
        conn.commit()
        return redirect(url_for("dashboard.home"))

    customers = conn.execute("""
        SELECT c.*,
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = c.id AND type = 'payment') AS pending
        FROM customers c
        WHERE c.user_id = ?
        ORDER BY c.name
    """, (session["user_id"],)).fetchall()

    return render_template(
        "add_transaction.html",
        customers=customers,
        preselected=request.args.get("customer_id"),
    )


@customers_bp.route("/customer/<int:customer_id>")
def customer_detail(customer_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    ).fetchone()
    if not customer:
        return "Customer not found", 404

    transactions = conn.execute(
        "SELECT * FROM transactions WHERE customer_id = ? ORDER BY id DESC",
        (customer_id,),
    ).fetchall()
    pending = conn.execute("""
        SELECT (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = 'credit') -
               (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE customer_id = ? AND type = 'payment')
    """, (customer_id, customer_id)).fetchone()[0]

    return render_template(
        "customer_detail.html",
        customer=customer,
        transactions=transactions,
        pending=int(pending or 0),
    )


@customers_bp.route("/edit_customer/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    ).fetchone()
    if not customer:
        return "Customer not found", 404

    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        existing = conn.execute(
            "SELECT id FROM customers WHERE LOWER(name) = LOWER(?) AND user_id = ? AND id != ?",
            (name, session["user_id"], customer_id),
        ).fetchone()

        if existing:
            error = "Customer with this name already exists!"
        else:
            conn.execute(
                "UPDATE customers SET name = ?, phone = ?, email = ? WHERE id = ?",
                (name, phone, email, customer_id),
            )
            conn.commit()
            return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    return render_template("edit_customer.html", customer=customer, error=error)


@customers_bp.route("/delete_customer/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    customer = conn.execute(
        "SELECT id FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    ).fetchone()
    if not customer:
        return "Customer not found", 404

    conn.execute("DELETE FROM transactions WHERE customer_id = ?", (customer_id,))
    conn.execute(
        "DELETE FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    )
    conn.commit()
    return redirect(url_for("customers.customers"))
