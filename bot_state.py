import os
import json
import requests

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

        
        
    print(f"Running bots: {running_bots}")
    return running_bots