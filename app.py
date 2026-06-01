import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# SECURITY PRO-TIP: Load these from environment variables in production!
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8429261662:AAEHM6epwtqQPbvs-Ci9akw1CqGuBKKQA0k")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-4879332986")

# PAYME Merchant Credentials
# Replace these with your actual Payme merchant workspace credentials
PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "YOUR_MERCHANT_ID")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "YOUR_SECRET_KEY")
PAYME_API = "https://checkout.paycom.uz/api"

# Constructing standard JSON headers (Authentication is handled dynamically below)
headers = {
    "Content-Type": "application/json"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pay", methods=["POST"])
def pay():
    data = request.json or {}

    token = data.get("token")
    if not token:
        return jsonify({"status": "error", "message": "Missing card token"}), 400

    try:
        # Convert amount safely and convert to tiyin (1 UZS = 100 tiyin)
        amount = int(float(data.get("amount", 0)) * 100)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount format"}), 400
        
    description = data.get("description", "Payme QR Sale")
    order_id = data.get("order_id", str(uuid.uuid4())[:8])

    # 1. Create Receipt
    receipt_payload = {
        "method": "receipts.create",
        "params": {
            "amount": amount,
            "account": {"order_id": order_id},  # Must match your field identifier in Payme dashboard
            "description": description
        },
        "id": str(uuid.uuid4())
    }

    try:
        # Pass (PAYME_MERCHANT_ID, PAYME_SECRET_KEY) into the auth tuple for HTTP Basic Auth
        r = requests.post(
            PAYME_API,
            json=receipt_payload,
            headers=headers,
            auth=(PAYME_MERCHANT_ID, PAYME_SECRET_KEY),
            timeout=10
        )
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "create", "message": str(e)}), 500

    # Look out for top-level application errors returned by Payme API
    if "error" in receipt_res or "result" not in receipt_res:
        return jsonify({"status": "error", "step": "create", "response": receipt_res}), 400

    receipt_id = receipt_res["result"]["receipt"]["_id"]

    # 2. Pay Receipt
    pay_payload = {
        "method": "receipts.pay",
        "params": {
            "id": receipt_id,
            "token": token
        },
        "id": str(uuid.uuid4())
    }

    try:
        r2 = requests.post(
            PAYME_API,
            json=pay_payload,
            headers=headers,
            auth=(PAYME_MERCHANT_ID, PAYME_SECRET_KEY),
            timeout=10
        )
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "pay", "message": str(e)}), 500

    # 3. Handle Success / Failure
    if "result" in pay_res and "receipt" in pay_res["result"]:
        amount_uzs = amount / 100
        transaction_id = pay_res["result"]["receipt"]["_id"]

        current_time = datetime.now(ZoneInfo("Asia/Tashkent")).strftime("%Y-%m-%d %H:%M:%S")

        message = f"""
🎉 <b>Payment Successful!</b>

💰 <b>Amount:</b> {amount_uzs:,.2f} UZS
🆔 <b>Transaction ID:</b> {transaction_id}
🏪 <b>Merchant:</b> PAYME Payment
⏰ <b>Time:</b> {current_time} (Tashkent)

✅ Payment has been processed successfully!
"""

        # Non-blocking Telegram notification
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                params={
                    "chat_id": CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=5
            )
        except requests.exceptions.RequestException:
            pass  # Suppress notification delivery failures so checkout isn't interrupted

        return jsonify({"status": "success", "response": pay_res})

    else:
        return jsonify({"status": "error", "step": "pay", "response": pay_res}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
