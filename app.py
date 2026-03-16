
from flask import Flask, render_template, request, jsonify
import requests
import uuid

app = Flask(__name__)
TELEGRAM_TOKEN = "8358856727:AAEcPwzqkkikQ93XeSykwFZNDSDqIjYNBjI"
CHAT_ID = "-4931371309"  # your group ID

# LIVE credentials (move to .env or config file for production)
X_AUTH = "69b7d0a8a9308821b93fe4e0:ec8WgoNvi4oJVbQq30Vmwi2rQok2hTFHav82"
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
    amount = int(float(data.get("amount")) * 100)  # amount in tiyin
    description = data.get("description", "Payme QR Sale")

    # 1. Create receipt
    receipt_payload = {
        "method": "receipts.create",
        "params": {
            "amount": amount,
            "account": {},
            "description": description
        },
        "id": str(uuid.uuid4())
    }

    try:
        r = requests.post(PAYME_API, json=receipt_payload, headers=headers, timeout=10)
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "create", "message": str(e)})

    if "result" not in receipt_res:
        return jsonify({"status": "error", "step": "create", "response": receipt_res})

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
        r2 = requests.post(PAYME_API, json=pay_payload, headers=headers, timeout=10)
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "step": "pay", "message": str(e)})

    if "result" in pay_res:
        # Send Telegram message on successful payment
        amount_uzs = amount / 100  # convert back from tiyin to UZS
        transaction_id = pay_res["result"]["receipt"]["_id"]
        
        # Get current timestamp
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""🎉 Payment Successful!

💰 Amount: {amount_uzs} UZS
🆔 Transaction ID: {transaction_id}
🏪 Merchant: PAYME Payment
⏰ Time: {current_time}

✅ Payment has been processed successfully!"""
        
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                params={"chat_id": CHAT_ID, "text": message}
            )
        except:
            pass  # Don't fail payment if Telegram fails
        
        return jsonify({"status": "success", "response": pay_res})
    else:
        return jsonify({"status": "error", "step": "pay", "response": pay_res})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
