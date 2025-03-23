import os
# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

MAX_PIWO = 6  # Max Piwo per day
MAX_HP = 100  # Max HP
HP_PER_PIWO = 30  # HP gained per Piwo
PIWO_COST = 50  # Cost per Piwo
HP_LOSS_PER_WORK = 10  # HP lost per work action
DEFAULT_BALANCE = 100  # Default starting balance
NITRO_BONUS = 100  # Bonus for Nitro Boosters
ADMIN_IDS = [264079253757231104,]  # List of admin user IDs
HOST = os.getenv("DATABASE_HOST")
USER = os.getenv("DATABASE_USER")
PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE = os.getenv("DATABASE_DATABASE")
PORT = os.getenv("DATABASE_PORT")
GRZYWNA_AMOUNT = 1  # Kara w Social Credit
KOPALNIAMIN = 1
KOPALNIAMAX = 50
GAMBLING_CHANNEL = "🃏-czerepalnia-gambling"
BLOXLINK_API_KEY_815660960097239040 = os.getenv("BLOXLINK_API_KEY_815660960097239040")
BLOXLINK_API_KEY_637696690853511184 = os.getenv("BLOXLINK_API_KEY_637696690853511184")