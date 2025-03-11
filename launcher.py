import os
import subprocess
import signal
import atexit
import threading
import sys
import zipfile
import io
import requests
import json

BASE_DIR = "bots"
GITHUB_USER = os.environ.get("GitHub_User")
GITHUB_TOKEN = os.environ.get("GitHub_TOKEN")
LOCAL_JSON_PATH = "bots.json"
ONLINE_JSON_URL = os.environ.get("ONLINE_JSON_URL")

running_processes = []


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


def download_repo(bot_name, repo_name):
    """Download and extract a private GitHub repo ZIP using authentication."""
    bot_folder = os.path.join(BASE_DIR, bot_name.lower())

    if os.path.exists(bot_folder):
        print(f"{bot_name}: Repository already exists, skipping download.")
        return

    zip_url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/zipball/main"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    print(f"{bot_name}: Downloading repository ZIP...")

    try:
        response = requests.get(zip_url, headers=headers, stream=True)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            extracted_folder_name = z.namelist()[0].split('/')[0]  # Extract folder name from ZIP
            z.extractall(BASE_DIR)

        os.rename(os.path.join(BASE_DIR, extracted_folder_name), bot_folder)

        print(f"{bot_name}: Repository downloaded and extracted successfully.")

    except requests.exceptions.RequestException as e:
        print(f"{bot_name}: Failed to download repository - {e}")
    except zipfile.BadZipFile:
        print(f"{bot_name}: Error: Downloaded file is not a valid ZIP archive.")


def run_bot(bot_name, bot_folder, bot_token):
    """Run bot.py with the bot token."""
    possible_paths = [
        os.path.join(BASE_DIR, bot_folder, "src", "bot.py"),
        os.path.join(BASE_DIR, bot_folder, "bot.py"),
        os.path.join(BASE_DIR, bot_folder, "src", "Bot.py"),
        os.path.join(BASE_DIR, bot_folder, "Bot.py"),
    ]

    bot_path = next((path for path in possible_paths if os.path.exists(path)), None)

    if not bot_path:
        print(f"{bot_name}: Error: bot.py is missing or not a file.")
        return

    try:
        process = subprocess.Popen(
            [sys.executable, "-u", bot_path],  # Use -u to disable buffering
            env={**os.environ, "BOT_TOKEN": bot_token},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        running_processes.append(process)
        print(f"{bot_name}: Bot started successfully with PID {process.pid}")

        def stream_output(stream, prefix):
            for line in iter(stream.readline, ''):
                print(f"{prefix} {line.strip()}")

        threading.Thread(target=stream_output, args=(process.stdout, f"[{bot_name} STDOUT]"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, f"[{bot_name} STDERR]"), daemon=True).start()

    except Exception as e:
        print(f"{bot_name}: Failed to start bot - {e}")


def stop_bots():
    """Terminate all running bots."""
    print("Stopping all bots...")
    for process in running_processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print(f"Terminated bot with PID {process.pid}")


os.makedirs(BASE_DIR, exist_ok=True)

signal.signal(signal.SIGINT, lambda signum, frame: stop_bots())
signal.signal(signal.SIGTERM, lambda signum, frame: stop_bots())

atexit.register(stop_bots)

for bot_name, config in BOTS.items():
    repo_name = config.get("repo")
    bot_token = os.environ.get(config.get("token"))

    if not bot_token:
        print(f"{bot_name}: No token found, skipping.")
        continue

    bot_folder = bot_name.lower()
    download_repo(bot_name, repo_name)
    run_bot(bot_name, bot_folder, bot_token)

try:
    while True:
        pass
except KeyboardInterrupt:
    pass
finally:
    stop_bots()
