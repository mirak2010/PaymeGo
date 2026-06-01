Skip to content
mirak2010
PaymeGo
Repository navigation
Code
Issues
Pull requests
Agents
Actions
Projects
Wiki
Security and quality
2
 (2)
Insights
Settings
PaymeGo
/
app.py
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

No wrap
Editing app.py file contents
  1
  2
  3
  4
  5
  6
  7
  8
  9
 10
 11
 12
 13
 14
 15
 16
 17
 18
 19
 20
 21
 22
 23
 24
 25
 26
 27
 28
 29
 30
 31
 32
 33
 34
 35
 36
 37
 38
 39
 40
 41
 42
 43
 44
 45
 46
 47
 48
 49
 50
 51
 52
 53
 54
 55
 56
 57
 58
 59
 60
 61
 62
 63
 64
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
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
