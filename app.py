import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Telegram credentials
TELEGRAM_TOKEN = "8429261662:AAEHM6epwtqQPbvs-Ci9akw1CqGuBKKQA0k"
CHAT_ID = "-4879332986"

# PAYME credentials
X_AUTH = "YOUR_X_AUTH"
PAYME_API = "https://checkout.paycom.uz/api"

headers = {
    "X-Auth": X_AUTH,
    "Content-Type": "application/json"
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pay", methods=["POST"])
def pay():
    data = request.json

    token = data.get("token")
    amount = int(float(data.get("amount")) * 100)  # tiyin
    description = data.get("description", "Payme QR Sale")
    
    # Track order identity (Payme requires this mapping inside the account object)
    order_id = data.get("order_id", str(uuid.uuid4())[:8])

    # 1. Create receipt
    receipt_payload = {
        "method": "receipts.create",
        "params": {
            "amount": amount,
            # Match "order_id" with the key configured in your Payme Dashboard
            "account": {"order_id": order_id},
            "description": description
        },
        "id": str(uuid.uuid4())
    }

    try:
        r = requests.post(
            PAYME_API,
            json=receipt_payload,
            headers=headers,
            timeout=10
        )
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "step": "create",
            "message": str(e)
        })

    if "result" not in receipt_res or "receipt" not in receipt_res["result"]:
        return jsonify({
            "status": "error",
            "step": "create",
            "response": receipt_res
        })

    receipt_id = receipt_res["result"]["receipt"]["_id"]

    # 2. Pay receipt
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
            timeout=10
        )
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        return jsonify({
            "status": "error",
            "step": "pay",
            "message": str(e)
        })

    # 3. Success
    if "result" in pay_res and "receipt" in pay_res["result"]:
        amount_uzs = amount / 100
        transaction_id = pay_res["result"]["receipt"]["_id"]

        # Evaluated safely outside the string to prevent code runtime evaluation crashes
        current_time = datetime.now(
            ZoneInfo("Asia/Tashkent")
        ).strftime("%Y-%m-%d %H:%M:%S")

        message = f"""
🎉 <b>Payment Successful!</b>

💰 <b>Amount:</b> {amount_uzs:,.0f} UZS
🆔 <b>Transaction ID:</b> {transaction_id}
🏪 <b>Merchant:</b> PAYME Payment
⏰ <b>Time:</b> {current_time} (Tashkent)

✅ Payment has been processed successfully!
"""

        # Telegram notification
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                params={
                    "chat_id": CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )
        except requests.exceptions.RequestException:
            pass

        return jsonify({
            "status": "success",
            "response": pay_res
        })

    else:
        return jsonify({
            "status": "error",
            "step": "pay",
            "response": pay_res
        })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
