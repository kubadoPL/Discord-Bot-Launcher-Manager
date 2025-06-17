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
import time
import shutil 

BASE_DIR = "/tmp/bots"
GITHUB_USER = os.environ.get("GitHub_User")
GITHUB_TOKEN = os.environ.get("GitHub_TOKEN")
LOCAL_JSON_PATH = "bots.json"
ONLINE_JSON_URL = os.environ.get("ONLINE_JSON_URL")

running_processes = {}
latest_commits = {}

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


def get_latest_commit_hash(repo_name):
    """Fetch the latest commit hash for the repository."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/commits/main"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("sha")
    except requests.exceptions.RequestException:
        print(f"{repo_name}: Failed to fetch latest commit hash.")
        return None


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
            extracted_folder_name = z.namelist()[0].split('/')[0] 
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
            [sys.executable, "-u", bot_path], 
            env={**os.environ, "BOT_TOKEN": bot_token},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        running_processes[bot_name] = process
     
        print(f"{bot_name}: Bot started successfully with PID {process.pid}")

        def stream_output(stream, prefix):
            for line in iter(stream.readline, ''):
                print(f"{prefix} {line.strip()}")

        threading.Thread(target=stream_output, args=(process.stdout, f"[{bot_name} STDOUT]"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, f"[{bot_name} STDERR]"), daemon=True).start()

    except Exception as e:
        print(f"{bot_name}: Failed to start bot - {e}")


def stop_bot(bot_name):
    """Stop a specific bot process."""
    process = running_processes.get(bot_name)
    if process and process.poll() is None:
        print(f"{bot_name}: Stopping bot...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print(f"{bot_name}: Bot stopped.")
        del running_processes[bot_name]
    


def stop_all_bots():
    """Stop all running bots."""
    print("Stopping all bots...")
    for bot_name in list(running_processes.keys()):
        stop_bot(bot_name)


os.makedirs(BASE_DIR, exist_ok=True)

signal.signal(signal.SIGINT, lambda signum, frame: stop_all_bots())
signal.signal(signal.SIGTERM, lambda signum, frame: stop_all_bots())

atexit.register(stop_all_bots)

def delete_repo(repo_name):
    """Delete the bot's folder to remove old code."""
    bot_folder = repo_name.lower()
    bot_path = os.path.join(BASE_DIR, bot_folder)
    if os.path.exists(bot_path):
        print(f"Deleting old repository: {bot_folder} ...")
        shutil.rmtree(bot_path)
        print(f"Deleted old repository: {bot_folder}.")

def check_for_updates():
    """Periodically check for updates in the repositories and restart bots if needed."""
    global latest_commits
    while True:
        for bot_name, config in BOTS.items():
            repo_name = config.get("repo")
            bot_token = os.environ.get(config.get("token"))

            if not bot_token:
                print(f"{bot_name}: No token found, skipping.")
                continue

            bot_folder = bot_name.lower()

            latest_commit = get_latest_commit_hash(repo_name)

            if latest_commit and latest_commit != latest_commits.get(bot_name):
                print(f"{bot_name}: New update detected! Restarting bot...")
                stop_bot(bot_name)
                delete_repo(repo_name)
                download_repo(bot_name, repo_name)
                run_bot(bot_name, bot_folder, bot_token)
                latest_commits[bot_name] = latest_commit

        time.sleep(60)  



for bot_name, config in BOTS.items():
    repo_name = config.get("repo")
    bot_token = os.environ.get(config.get("token"))

    if not bot_token:
        print(f"{bot_name}: No token found, skipping.")
        continue

    bot_folder = bot_name.lower()
    download_repo(bot_name, repo_name)
    latest_commits[bot_name] = get_latest_commit_hash(repo_name)
    run_bot(bot_name, bot_folder, bot_token)


update_thread = threading.Thread(target=check_for_updates, daemon=True)
update_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    stop_all_bots()
