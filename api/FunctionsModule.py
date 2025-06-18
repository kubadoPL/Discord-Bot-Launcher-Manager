import os
import json
import requests
from functools import wraps
import requests
import mysql.connector

from flask import Flask, request, jsonify
import sys

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Add parent directory to sys.path so 'api' becomes importable
sys.path.append(parent_dir)

# Optional: change working directory
os.chdir(parent_dir)
print("Working directory set to:", os.getcwd())

import api.config as config
LOCAL_JSON_PATH = "bots.json"
ONLINE_JSON_URL = os.environ.get("ONLINE_JSON_URL")

def get_roblox_username(roblox_id):
    url = f"https://users.roblox.com/v1/users/{roblox_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # The 'name' field contains the username
        return data.get("name")
    else:
        return None  # User not found or request failed

def get_roblox_avatar(roblox_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={roblox_id}&size=100x100&format=Png&isCircular=true"
    headers = {"accept": "application/json"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0 and "imageUrl" in data["data"][0]:
            return data["data"][0]["imageUrl"]
    return None  # Default in case of failure

def get_discord_user_profile(user_id):
    token = os.environ.get("SOCIALCREDITBOT_TOKEN")
    url = "https://discord.com/api/v10/users/" + user_id
    headers = {
        "Authorization": f"Bot {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return {
            "id": data["id"],
            "username": data["username"],
            "discriminator": data["discriminator"],
            "avatar_url": f'https://cdn.discordapp.com/avatars/{data["id"]}/{data["avatar"]}.png' if data.get("avatar") else None,
   
        }

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch bot profile: {e}")
        return None

def get_discord_bot_profile(token):
    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "Authorization": f"Bot {token}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return {
            "id": data["id"],
            "username": data["username"],
            "discriminator": data["discriminator"],
            "avatar_url": f'https://cdn.discordapp.com/avatars/{data["id"]}/{data["avatar"]}.png' if data.get("avatar") else None,
            "bot": data["bot"]
        }

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch bot profile: {e}")
        return None

def load_bots():
    """Try to load bot data from an online URL; if it fails, use local JSON."""
    try:
        response = requests.get(ONLINE_JSON_URL, timeout=5)
        response.raise_for_status()
        print("Using online bot data.")
        return response.json()
    except requests.exceptions.RequestException:
        print("Failed to fetch online bot data. Using local JSON.")
        if os.path.exists(LOCAL_JSON_PATH):
            with open(LOCAL_JSON_PATH, "r", encoding="utf-8") as file:
                return json.load(file)
        else:
            print("Error: Local JSON file not found.")
            return {}

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

def get_running_bots():
    """Get a list of currently running bot names."""
    BOTS = load_bots() 
    
    running_bots = []
    for bot_name, config in BOTS.items():
        
        bot_token = os.environ.get(config.get("token"))

        if not bot_token:
            print(f"{bot_name}: No token found, skipping.")
            #running_bots.append(bot_name)
            continue
        profile = get_discord_bot_profile(bot_token)
        if profile:
            #print("Bot info:", profile)
            running_bots.append(profile)
        else:
            print("Invalid token or request failed.")
            #running_bots.append(bot_name)

        
        
    #print(f"Running bots: {running_bots}")
    return running_bots