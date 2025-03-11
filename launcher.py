import os
import subprocess

BASE_DIR = "bots"
GITHUB_USER = "kubadoPL"
GITHUB_TOKEN = os.environ.get("GitHub_TOKEN")

BOTS = {
    "EzeteriuszMaximusBOT": {
        "repo": "EzeteriuszMaximusBOT",
        "token": os.environ.get("EZETERIUSZ_TOKEN"),
    },
}

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
            ["python", bot_path],
            env={**os.environ, "BOT_TOKEN": bot_token},
             stdout=None, stderr=None,
        )
        print(f"{bot_name}: Bot started successfully with PID {process.pid}")
    except Exception as e:
        print(f"{bot_name}: Failed to start bot - {e}")

# Ensure bots directory exists
os.makedirs(BASE_DIR, exist_ok=True)

# Clone and run each bot
for bot_name, config in BOTS.items():
    repo_name = config["repo"]
    bot_token = config["token"]

    if not bot_token:
        print(f"{bot_name}: No token found, skipping.")
        continue

    bot_folder = bot_name.lower()
    clone_repo(bot_name, repo_name)
    run_bot(bot_name, bot_folder, bot_token)
