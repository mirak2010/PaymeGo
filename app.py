from flask import Flask, render_template, request, jsonify
import requests
import random
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8358856727:AAEcPwzqkkikQ93XeSykwFZNDSDqIjYNBjI"
CHAT_ID = "-4931371309"

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
    amount = int(float(data.get("amount")) * 100)  # convert UZS to tiyin
    description = data.get("description", "Payme QR Sale")
    order_id = data.get("order_id", str(random.randint(100000, 999999)))

    # 1. Create receipt
    receipt_payload = {
        "method": "receipts.create",
        "params": {
            "amount": amount,
            "account": {
                "order_id": order_id
            },
            "description": description
        },
        "id": random.randint(1, 99999)
    }

    try:
        r = requests.post(PAYME_API, json=receipt_payload, headers=headers, timeout=10)
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Receipt creation error: {str(e)}")
        return jsonify({"status": "error", "step": "create", "message": str(e)}), 500

    if "result" not in receipt_res:
        logging.error(f"Receipt creation failed: {receipt_res}")
        return jsonify({"status": "error", "step": "create", "response": receipt_res}), 400

    receipt_id = receipt_res["result"]["receipt"]["_id"]

    # 2. Pay receipt
    pay_payload = {
        "method": "receipts.pay",
        "params": {
            "id": receipt_id,
            "token": token
        },
        "id": random.randint(1, 99999)
    }

    try:
        r2 = requests.post(PAYME_API, json=pay_payload, headers=headers, timeout=10)
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Payment error: {str(e)}")
        return jsonify({"status": "error", "step": "pay", "message": str(e)}), 500

    if "result" in pay_res:
        amount_uzs = amount / 100
        transaction_id = pay_res["result"]["receipt"]["_id"]
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
                params={"chat_id": CHAT_ID, "text": message},
                timeout=5
            )
        except Exception as e:
            logging.warning(f"Telegram notification failed: {str(e)}")

        return jsonify({"status": "success", "response": pay_res}), 200
    else:
        logging.error(f"Payment failed: {pay_res}")
        return jsonify({"status": "error", "step": "pay", "response": pay_res}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logging.error(f"Server error: {str(error)}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
