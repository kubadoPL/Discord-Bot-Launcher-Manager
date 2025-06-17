import os
import json
import requests

LOCAL_JSON_PATH = "bots.json"
ONLINE_JSON_URL = os.environ.get("ONLINE_JSON_URL")

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


BOTS = load_bots()

def get_running_bots():
    """Get a list of currently running bots."""
    running_bots = {}
    for bot_name, bot_info in BOTS.items():
        if bot_info.get("running", False):
            running_bots.append({
                bot_name
        
            })
    return running_bots

