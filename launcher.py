import os
import subprocess
import signal
import atexit
import shutil
import threading
import sys

BASE_DIR = "bots"
GITHUB_USER = "kubadoPL"
GITHUB_TOKEN = os.environ.get("GitHub_TOKEN")

BOTS = {
    "EzeteriuszMaximusBOT": {
        "repo": "EzeteriuszMaximusBOT",
        "token": os.environ.get("EZETERIUSZ_TOKEN"),
    },
    "PszczelarzBOT": {
        "repo": "PszczelarzBOT",
        "token": os.environ.get("PszczelarzBOT_TOKEN"),
    },
     "Social-Credit-Bot": {
        "repo": "Social-Credit-Bot",
        "token": os.environ.get("SOCIALCREDITBOT_TOKEN"),
    },
}


running_processes = []

def clone_repo(bot_name, repo_name):
    """Clone the bot repository using GitHub token."""
    bot_folder = os.path.join(BASE_DIR, bot_name.lower())
    repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"

    if os.path.exists(bot_folder):
        print(f"{bot_name}: Repository already exists, skipping clone.")
        return

    print(f"{bot_name}: Cloning repository...")
    
    try:
        subprocess.run(["git", "clone", repo_url, bot_folder], check=True)
        print(f"{bot_name}: Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        print(f"{bot_name}: Failed to clone repository - {e}")

def run_bot(bot_name, bot_folder, bot_token):
    """Run bot.py with the bot token."""
    bot_path = os.path.join(BASE_DIR, bot_folder, "src", "bot.py")

    if not os.path.exists(bot_path):
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
    repo_name = config["repo"]
    bot_token = config["token"]

    if not bot_token:
        print(f"{bot_name}: No token found, skipping.")
        continue

    bot_folder = bot_name.lower()
    clone_repo(bot_name, repo_name)
    run_bot(bot_name, bot_folder, bot_token)


try:
    while True:
        pass  
except KeyboardInterrupt:
    pass  
finally:
    stop_bots()  
