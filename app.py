import os
import re
import uuid
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})

BASE = os.getenv("GOXTOP_BASE_URL", "https://goxtop.com/api/v.1").rstrip("/")
API_KEY = os.getenv("GOXTOP_API_KEY", "")
GAME_CODE = os.getenv("GOXTOP_FREEFIRE_GAME_CODE", "freefire_global")
ORDER_PATH = os.getenv("GOXTOP_ORDER_PATH", "/create-order")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

def goxtop(method, path, **kwargs):
    if not API_KEY:
        raise RuntimeError("GOXTOP_API_KEY is missing")
    headers = kwargs.pop("headers", {})
    headers["x-api-key"] = API_KEY
    r = requests.request(method, f"{BASE}/{path.lstrip('/')}",
                         headers=headers, timeout=20, **kwargs)
    r.raise_for_status()
    return r.json()

@app.get("/")
def index():
    return jsonify(success=True, service="Lama Topup API", status="online")

@app.get("/api/health")
def health():
    return jsonify(success=True, dry_run=DRY_RUN, game_code=GAME_CODE)

@app.get("/api/freefire/products")
def products():
    try:
        return jsonify(goxtop("GET", f"/products/{GAME_CODE}"))
    except Exception as e:
        return jsonify(success=False, error=str(e)), 502

@app.post("/api/orders")
def orders():
    data = request.get_json(silent=True) or {}
    uid = str(data.get("user_id", "")).strip()
    pack = str(data.get("pack", "")).strip()
    order_id = str(data.get("partner_order_id") or
                   f"LAMA-{uuid.uuid4().hex[:18].upper()}").strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{4,32}", uid):
        return jsonify(success=False, error="Invalid Free Fire UID"), 400
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,100}", pack):
        return jsonify(success=False, error="Invalid product pack"), 400

    payload = {
        "gamecode": GAME_CODE,
        "pack": pack,
        "userid": uid,
        "partner_orderid": order_id
    }

    if DRY_RUN:
        return jsonify(success=True, dry_run=True, order=payload,
                       message="No GoXtop order was created")

    try:
        return jsonify(goxtop("POST", ORDER_PATH, json=payload))
    except Exception as e:
        return jsonify(success=False, error=str(e)), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
