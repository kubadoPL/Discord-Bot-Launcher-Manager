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
        connection_timeout=10,
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

def create_chat_tables():
    """Create tables for persisting chat data (messages, emojis, profiles)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id VARCHAR(32) PRIMARY KEY,
        station VARCHAR(64) NOT NULL,
        user_id VARCHAR(64) NOT NULL,
        content TEXT,
        image_data LONGTEXT,
        song_data JSON,
        reactions JSON,
        reaction_users JSON,
        timestamp DATETIME NOT NULL,
        last_update DATETIME NOT NULL,
        INDEX idx_station (station),
        INDEX idx_timestamp (timestamp)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_custom_emojis (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(64) NOT NULL,
        url LONGTEXT NOT NULL,
        creator_id VARCHAR(64) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_user_profiles (
        user_id VARCHAR(64) PRIMARY KEY,
        username VARCHAR(128) NOT NULL,
        global_name VARCHAR(128),
        avatar_url TEXT,
        banner_url TEXT,
        accent_color INT,
        last_seen_at DATETIME,
        last_station VARCHAR(64),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    )

    # Add columns for existing installations
    for col_sql in [
        "ALTER TABLE chat_user_profiles ADD COLUMN last_seen_at DATETIME",
        "ALTER TABLE chat_user_profiles ADD COLUMN last_station VARCHAR(64)",
    ]:
        try:
            cursor.execute(col_sql)
        except Exception:
            pass  # Column already exists

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS chat_user_sessions (
        session_token VARCHAR(128) PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL,
        discord_access_token TEXT,
        expires_at DATETIME NOT NULL,
        via_activity TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_expires (expires_at)
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS user_data (
        user_id VARCHAR(64) NOT NULL,
        data_key VARCHAR(128) NOT NULL,
        data_value LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, data_key)
    )
    """
    )

    conn.commit()
    conn.close()


def create_service_stats_table():
    """Create the service_stats table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS service_stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        service_name VARCHAR(128) NOT NULL,
        stat_name VARCHAR(128) NOT NULL,
        value DOUBLE NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_service_stat (service_name, stat_name)
    )
    """
    )
    conn.commit()
    conn.close()

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