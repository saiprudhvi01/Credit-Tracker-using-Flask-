import re
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from shop_tracker.db import get_db


api_bp = Blueprint("api", __name__)


@api_bp.route("/api/customers")
def api_customers():
    if "user_id" not in session:
        return jsonify([])

    customers = get_db().execute(
        "SELECT id, name FROM customers WHERE user_id = ? ORDER BY name",
        (session["user_id"],),
    ).fetchall()
    return jsonify([{"id": customer["id"], "name": customer["name"]} for customer in customers])


@api_bp.route("/api/transaction", methods=["POST"])
def api_add_transaction():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in"})

    data = request.get_json() or {}
    customer_id = data.get("customer_id")
    trans_type = data.get("type")
    amount = float(data.get("amount", 0))
    note = data.get("note")

    if not customer_id or not trans_type or not amount:
        return jsonify({"success": False, "message": "Missing required fields"})

    conn = get_db()
    customer = conn.execute(
        "SELECT id FROM customers WHERE id = ? AND user_id = ?",
        (customer_id, session["user_id"]),
    ).fetchone()
    if not customer:
        return jsonify({"success": False, "message": "Customer not found"})

    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute(
        "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
        (customer_id, amount, trans_type, note, date),
    )
    conn.commit()
    return jsonify({"success": True, "message": "Transaction added successfully"})


@api_bp.route("/api/voice-command", methods=["POST"])
def api_voice_command():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please log in first"})

    data = request.get_json() or {}
    command = data.get("command", "").lower().strip()
    conn = get_db()
    customers = conn.execute(
        "SELECT id, name FROM customers WHERE user_id = ?",
        (session["user_id"],),
    ).fetchall()
    customer_map = {customer["name"].lower(): customer["id"] for customer in customers}

    matched_name = None
    customer_id = None
    for name, candidate_id in customer_map.items():
        if name in command or command in name:
            matched_name = name
            customer_id = candidate_id
            break

    if "+" in command or "plus" in command:
        trans_type = "credit"
    elif "-" in command or "minus" in command:
        trans_type = "payment"
    else:
        trans_type = None

    amount_match = re.search(r"(\d+(?:,\d+)*(?:\.\d+)?)", command)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

    if customer_id and amount and trans_type:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO transactions (customer_id, amount, type, note, date) VALUES (?, ?, ?, ?, ?)",
            (customer_id, amount, trans_type, f"Voice: {command}", date),
        )
        conn.commit()
        actual_name = next(
            customer["name"] for customer in customers if customer["id"] == customer_id
        )
        if trans_type == "credit":
            message = f"✅ {actual_name}'s khata increased by ₹{amount} (+)"
        else:
            message = f"✅ {actual_name} paid ₹{amount}, khata decreased (-)"
        return jsonify({"success": True, "message": message})

    if not matched_name:
        if customers:
            available_names = "\n".join(
                f"{index}. {customer['name']}"
                for index, customer in enumerate(customers, start=1)
            )
            message = (
                f"🤔 Customer not found. Available customers "
                f"({len(customers)}):\n{available_names}"
            )
        else:
            message = "🤔 Customer not found. No customers have been added yet."
        return jsonify({"success": False, "message": message})

    if not amount:
        return jsonify({"success": False, "message": "💰 No amount found. Include a number."})

    if not trans_type:
        return jsonify({
            "success": False,
            "message": "🤷 Use + to increase khata or - for payment.\n\nExample: 'Venkat + 500' or 'Venkat - 1000'",
        })

    return jsonify({"success": False, "message": "🤔 Could not understand. Try: 'Venkat + 500' or 'Venkat - 1000'"})
