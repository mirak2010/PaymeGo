from flask import Flask, render_template, request, jsonify
import requests
import random
import logging
from datetime import datetime, timezone, timedelta

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

    logging.info(f"=== NEW PAYMENT REQUEST ===")
    logging.info(f"Amount (tiyin): {amount}")
    logging.info(f"Order ID: {order_id}")
    logging.info(f"Token: {token}")

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

    logging.info(f"--- receipts.create payload: {receipt_payload}")

    try:
        r = requests.post(PAYME_API, json=receipt_payload, headers=headers, timeout=10)
        logging.info(f"receipts.create HTTP status: {r.status_code}")
        logging.info(f"receipts.create raw response: {r.text}")
        r.raise_for_status()
        receipt_res = r.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Receipt creation request error: {str(e)}")
        return jsonify({"status": "error", "step": "create", "message": str(e)}), 500

    if "result" not in receipt_res:
        error_detail = receipt_res.get("error", receipt_res)
        logging.error(f"receipts.create failed. Error code: {error_detail.get('code') if isinstance(error_detail, dict) else 'N/A'}")
        logging.error(f"receipts.create failed. Error message: {error_detail.get('message') if isinstance(error_detail, dict) else error_detail}")
        logging.error(f"receipts.create full response: {receipt_res}")
        return jsonify({
            "status": "error",
            "step": "create",
            "error_code": error_detail.get("code") if isinstance(error_detail, dict) else None,
            "error_message": error_detail.get("message") if isinstance(error_detail, dict) else str(error_detail),
            "full_response": receipt_res
        }), 400

    receipt_id = receipt_res["result"]["receipt"]["_id"]
    logging.info(f"Receipt created successfully. ID: {receipt_id}")

    # 2. Pay receipt
    pay_payload = {
        "method": "receipts.pay",
        "params": {
            "id": receipt_id,
            "token": token
        },
        "id": random.randint(1, 99999)
    }

    logging.info(f"--- receipts.pay payload: {pay_payload}")

    try:
        r2 = requests.post(PAYME_API, json=pay_payload, headers=headers, timeout=10)
        logging.info(f"receipts.pay HTTP status: {r2.status_code}")
        logging.info(f"receipts.pay raw response: {r2.text}")
        r2.raise_for_status()
        pay_res = r2.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Payment request error: {str(e)}")
        return jsonify({"status": "error", "step": "pay", "message": str(e)}), 500

    if "result" in pay_res:
        amount_uzs = amount / 100
        transaction_id = pay_res["result"]["receipt"]["_id"]
        tashkent = timezone(timedelta(hours=5))
        current_time = datetime.now(tashkent).strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Payment successful! Transaction ID: {transaction_id}")

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
        error_detail = pay_res.get("error", pay_res)
        logging.error(f"receipts.pay failed. Error code: {error_detail.get('code') if isinstance(error_detail, dict) else 'N/A'}")
        logging.error(f"receipts.pay failed. Error message: {error_detail.get('message') if isinstance(error_detail, dict) else error_detail}")
        logging.error(f"receipts.pay full response: {pay_res}")
        return jsonify({
            "status": "error",
            "step": "pay",
            "error_code": error_detail.get("code") if isinstance(error_detail, dict) else None,
            "error_message": error_detail.get("message") if isinstance(error_detail, dict) else str(error_detail),
            "full_response": pay_res
        }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logging.error(f"Server error: {str(error)}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
