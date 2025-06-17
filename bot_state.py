import os
import json
import threading
import os
import datetime
# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

LOCK = threading.Lock()
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "/tmp/bot_registry.json")

def load_registry():
    if not os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "w") as f:
            json.dump({}, f)
    with open(REGISTRY_FILE, "r") as f:
        return json.load(f)

def save_registry(data):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f)
    print(f"[DEBUG] Writing registry file to: {REGISTRY_FILE}")


def register_bot(name):
    data = load_registry()
    data[name] = {"started": str(datetime.datetime.utcnow())}
    save_registry(data)


def unregister_bot(bot_name):
    registry = load_registry()
    if bot_name in registry:
        del registry[bot_name]
        save_registry(registry)

def get_running_bots():
    print(list(load_registry().keys()))
    return list(load_registry().keys())

