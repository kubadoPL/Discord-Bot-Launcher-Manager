import os
import sys

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Add parent directory to sys.path so 'api' becomes importable
sys.path.append(parent_dir)

# Optional: change working directory
os.chdir(parent_dir)
print("Working directory set to:", os.getcwd())

# Now safely import
from flask import Flask, request, jsonify
import mysql.connector

import api.config as config
from api.bot_state import (
    get_running_bots,
    get_discord_user_profile,
    get_roblox_username,
    get_roblox_avatar
)

from flask import render_template
import json


from functools import wraps
import base64
import requests

from flask_cors import CORS

app = Flask(__name__, template_folder=parent_dir + "/api/templates")
CORS(app)  # enable CORS globally




def validate_api_key(api_key):
    """Validates API key by checking against stored hashed values"""
    hashed_key = api_key  # hashlib.sha256(api_key.encode()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM api_keys WHERE key_value = %s", (hashed_key,))
    result = cursor.fetchone()
    conn.close()

    return result is not None  # Returns True if key exists


def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or not validate_api_key(api_key):
            return jsonify({"error": "Invalid or missing API key"}), 403
        return func(*args, **kwargs)

    return wrapper


# Database connection function
def get_db_connection():
    print("[INFO] Connecting to the database...")
    conn = mysql.connector.connect(
        host=config.HOST,
        user=config.USER,
        password=config.PASSWORD,
        database=config.DATABASE,
        port=config.PORT,
        autocommit=True,
    )
    print("[INFO] Database connection established.")
    return conn


@app.route("/")
def main_page():
    return render_template("/main.html")


@app.route("/running_bots")
def running_bots():
    bots = get_running_bots()
    return jsonify(bots)


@app.route("/api_key_info", methods=["GET"])
@require_api_key
def api_key_info():
    api_key = request.headers.get("X-API-Key")
    hashed_key = api_key

    print(f"[REQUEST] GET /api_key_info - api_key: {api_key}")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, owner, created_at FROM api_keys WHERE key_value = %s", (hashed_key,)
    )
    key_info = cursor.fetchone()
    conn.close()

    if key_info:
        print(f"[SUCCESS] Found API key info for: {api_key}")
        return jsonify({"api_key_info": key_info})
    else:
        print("[ERROR] API key not found.")
        return jsonify({"error": "API key not found"}), 404


@app.route("/get_balance", methods=["GET"])
def get_balance():
    user_id = request.args.get("user_id")
    print(f"[REQUEST] GET /get_balance - user_id: {user_id}")

    if not user_id:
        print("[ERROR] Missing user_id in request.")
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for user_id: {user_id}")
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    conn.close()

    if user:
        print(f"[SUCCESS] Retrieved balance: {user['balance']} for user_id: {user_id}")
        discord_profile = get_discord_user_profile(user_id)
        return jsonify({"balance": user["balance"], "discord_profile": discord_profile})
    else:
        print("[ERROR] User not found.")
        return jsonify({"error": "User not found"}), 404


@app.route("/update_balance", methods=["POST"])
@require_api_key
def update_balance():
    data = request.json
    if data is None:
        return jsonify({"error": "Missing or invalid JSON body"}), 400
    user_id = data.get("user_id")
    amount = data.get("amount")

    print(f"[REQUEST] POST /update_balance - user_id: {user_id}, amount: {amount}")

    if not user_id or amount is None:
        print("[ERROR] Missing user_id or amount in request.")
        return jsonify({"error": "Missing user_id or amount"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for user_id: {user_id} by {amount}")
    cursor.execute(
        "UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id)
    )
    conn.commit()
    conn.close()

    print("[SUCCESS] Balance updated successfully.")
    return jsonify({"message": "Balance updated successfully"})


# Roblox support
@app.route("/roblox/get_balance", methods=["GET"])
def get_roblox_balance():
    roblox_id = request.args.get("roblox_id")
    print(f"[REQUEST] GET /roblox/get_balance - roblox_id: {roblox_id}")

    if not roblox_id:
        print("[ERROR] Missing roblox_id in request.")
        return jsonify({"error": "Missing roblox_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for roblox_id: {roblox_id}")
    cursor.execute("SELECT balance FROM users WHERE roblox_id = %s", (roblox_id,))
    user = cursor.fetchone()

    conn.close()

    if user:
        print(
            f"[SUCCESS] Retrieved balance: {user['balance']} for roblox_id: {roblox_id}"
        )
        robloxprofile = {
            "username": get_roblox_username(roblox_id),
            "avatar_url": get_roblox_avatar(roblox_id),
            "id": roblox_id,
        }
        return jsonify({"balance": user["balance"], "discord_profile": robloxprofile})
    else:
        print("[ERROR] Roblox user not found.")
        return jsonify({"error": "Roblox user not found"}), 404


@app.route("/roblox/update_balance", methods=["POST"])
@require_api_key
def update_roblox_balance():
    data = request.json
    if data is None:
        return jsonify({"error": "Missing or invalid JSON body"}), 400
    roblox_id = data.get("roblox_id")
    amount = data.get("amount")

    print(
        f"[REQUEST] POST /roblox/update_balance - roblox_id: {roblox_id}, amount: {amount}"
    )

    if not roblox_id or amount is None:
        print("[ERROR] Missing roblox_id or amount in request.")
        return jsonify({"error": "Missing roblox_id or amount"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for roblox_id: {roblox_id} by {amount}")
    cursor.execute(
        "UPDATE users SET balance = balance + %s WHERE roblox_id = %s",
        (amount, roblox_id),
    )
    conn.commit()
    conn.close()

    print("[SUCCESS] Roblox balance updated successfully.")
    return jsonify({"message": "Roblox balance updated successfully"})


@app.route("/spotify/token", methods=["GET"])
def get_spotify_token():
    #print("[REQUEST] GET /spotify/token")

    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

    token_url = "https://accounts.spotify.com/api/token"
    credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        #print("[SUCCESS] Spotify token retrieved")
        return jsonify(
            {
                "access_token": token_data["access_token"],
                "expires_in": token_data["expires_in"],
            }
        )
    else:
       # print("[ERROR] Failed to retrieve Spotify token")
        return (
            jsonify(
                {
                    "error": "Failed to retrieve Spotify token",
                    "details": response.json(),
                }
            ),
            response.status_code,
        )


def run_api():
    port = int(os.environ.get("PORT", 5000))  # Get the port from environment variable
    print(f"[INFO] Starting API server on port {port}...")
    app.run(host="0.0.0.0", port=port)


def createtable():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS api_keys (
        id INT AUTO_INCREMENT PRIMARY KEY,
        key_value VARCHAR(255) NOT NULL UNIQUE,
        owner VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )
    conn.commit()


# createtable()

#run_api()
