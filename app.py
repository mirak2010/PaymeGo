import os
import time
import requests
from flask import Flask, jsonify, render_template, request
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# Security Credentials
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8429261662:AAEHM6epwtqQPbvs-Ci9akw1CqGuBKKQA0k")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-4879332986")

PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "YOUR_MERCHANT_ID")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "YOUR_SECRET_KEY")

# API Base (Switch to checkout.test.paycom.uz if in staging/sandbox environment)
PAYME_API = "https://checkout.paycom.uz/api"

# Exact Payme Subscription Header Construction
headers = {
    "X-Auth": f"{PAYME_MERCHANT_ID}:{PAYME_SECRET_KEY}",
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
        # Payme handles monetary digits in Tiyin (1 UZS = 100 Tiyin)
        amount = int(float(data.get("amount", 0)) * 100)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount format"}), 400

    description = data.get("description", "Payme QR Sale")
    order_id = str(data.get("order_id", int(time.time())))

    # 1. Create Receipt Payload (Strict JSON-RPC Structure)
    rpc_id = int(time.time() * 1000)
    receipt_payload = {
        "jsonrpc": "2.0",
        "method": "receipts.create",
        "params": {
            "amount": amount,
            "account": {"order_id": order_id}, 
            "description": description
        },
        "id": rpc_id
    }

    try:
        r = requests.post(PAYME_API, json=receipt_payload, headers=headers, timeout=10)
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "create_network", "message": str(e)}), 500

    # Catch internal JSON-RPC business logic errors
    if "error" in receipt_res:
        return jsonify({"status": "error", "step": "create_business", "response": receipt_res}), 400
    if "result" not in receipt_res or "receipt" not in receipt_res["result"]:
        return jsonify({"status": "error", "step": "create_parsing", "response": receipt_res}), 400

    receipt_id = receipt_res["result"]["receipt"]["_id"]

    # 2. Pay Receipt Payload
    pay_payload = {
        "jsonrpc": "2.0",
        "method": "receipts.pay",
        "params": {
            "id": receipt_id,
            "token": token
        },
        "id": rpc_id + 1
    }

    try:
        r2 = requests.post(PAYME_API, json=pay_payload, headers=headers, timeout=10)
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "pay_network", "message": str(e)}), 500

    if "error" in pay_res:
        return jsonify({"status": "error", "step": "pay_business", "response": pay_res}), 400

    # 3. Handle Application Success Output
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
        # Async-safe Notification dispatching 
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                params={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
                timeout=4
            )
        except requests.exceptions.RequestException:
            pass

        return jsonify({"status": "success", "response": pay_res})

    else:
        return jsonify({"status": "error", "step": "pay_unknown", "response": pay_res}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
