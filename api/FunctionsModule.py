import os
import json
import requests
from functools import wraps
import requests
import atexit
import time
import threading
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

# ─── Database connection pool ─────────────────────────────────────────────────
# Opening a fresh TLS connection to MySQL costs ~0.5s and, before pooling, every
# request did it. In the single-process web dyno that stall also froze the
# Icecast streaming loop (audible as dropouts during live DJ). The pool keeps a
# handful of connections warm; conn.close() on a pooled connection just returns
# it to the pool. If the pool is exhausted (callers that forgot to close), we
# fall back to a direct connection so nothing ever hard-fails.
_DB_CONFIG = dict(
    host=config.HOST,
    user=config.USER,
    password=config.PASSWORD,
    database=config.DATABASE,
    port=config.PORT,
    autocommit=True,
    connection_timeout=10,
)
# The MySQL user is capped at max_user_connections=10 and that budget is
# shared with the bots on the worker dyno AND with the old web dyno during a
# Heroku restart overlap. So the pool must be SMALL and LAZY: connections are
# opened one at a time, only when actually needed, never pre-filled.
_DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "3"))
_db_pool = None
_db_pool_lock = threading.Lock()


# Idle connections are really closed after this many seconds, so at rest the
# web dyno holds ZERO MySQL sessions — exactly like the old connect/close-per-
# request behaviour — while bursts of requests still reuse a warm connection.
_DB_POOL_IDLE_SECONDS = float(os.environ.get("DB_POOL_IDLE_SECONDS", "120"))
# How long a request waits for a busy pooled connection before opening a
# short-lived direct one (a release usually comes within milliseconds;
# a fresh handshake to the remote MySQL costs ~0.5-1 s).
_DB_POOL_WAIT_SECONDS = float(os.environ.get("DB_POOL_WAIT_SECONDS", "2"))


class PoolExhausted(Exception):
    pass


class _PooledConn:
    """Proxy returned to callers; close() hands the socket back to the pool."""

    __slots__ = ("_cnx", "_pool")

    def __init__(self, cnx, pool):
        self._cnx = cnx
        self._pool = pool

    def close(self):
        cnx, self._cnx = self._cnx, None
        if cnx is not None:
            self._pool.release(cnx)

    def __getattr__(self, name):
        cnx = object.__getattribute__(self, "_cnx")
        if cnx is None:
            raise mysql.connector.errors.OperationalError("Connection already closed")
        return getattr(cnx, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __del__(self):
        # Caller forgot close(): still give the socket back instead of leaking it.
        try:
            self.close()
        except Exception:
            pass


class _LazyMySQLPool:
    """Small on-demand pool with idle reaping and explicit shutdown.

    - opens a connection only when none is idle (never pre-fills)
    - at most `size` connections exist at any time
    - a connection idle for longer than `idle_ttl` seconds is closed for real
    - close_all() disconnects everything (used at process exit)

    Nothing slow happens under the lock: the ping of a recycled connection and
    the TCP/auth handshake of a new one run outside it, so parallel requests
    do not queue behind each other. When every connection is busy a caller
    waits up to `wait` seconds for one to be released before giving up.
    """

    def __init__(self, size, cfg, idle_ttl, wait=2.0, ping_after=15.0):
        self._size = size
        self._cfg = cfg
        self._idle_ttl = idle_ttl
        self._wait = wait
        self._ping_after = ping_after
        self._idle = []  # list of (cnx, last_used_ts)
        self._opened = 0
        self._cond = threading.Condition(threading.Lock())
        self._closed = False
        t = threading.Thread(target=self._reaper, daemon=True, name="db-pool-reaper")
        t.start()

    def _slot_freed(self):
        with self._cond:
            self._opened -= 1
            self._cond.notify()

    def get_connection(self):
        deadline = time.monotonic() + self._wait
        while True:
            cnx = None
            open_new = False
            need_ping = False
            with self._cond:
                if self._closed:
                    raise PoolExhausted("pool is closed")
                if self._idle:
                    cnx, last_used = self._idle.pop()
                    # A connection used a moment ago is fine; only ping (one
                    # DB round-trip) when it sat idle long enough to be dropped.
                    need_ping = (time.time() - last_used) > self._ping_after
                elif self._opened < self._size:
                    self._opened += 1
                    open_new = True
                else:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise PoolExhausted("all pooled connections are busy")
                    self._cond.wait(remaining)
                    continue

            if open_new:
                try:
                    cnx = mysql.connector.connect(**self._cfg)
                except Exception:
                    self._slot_freed()
                    raise
                return _PooledConn(cnx, self)

            if need_ping:
                alive = False
                try:
                    alive = cnx.is_connected()
                except Exception:
                    alive = False
                if not alive:
                    self._disconnect(cnx)
                    self._slot_freed()
                    continue
            return _PooledConn(cnx, self)

    def release(self, cnx):
        with self._cond:
            if self._closed:
                self._opened -= 1
                self._disconnect(cnx)
                return
            self._idle.append((cnx, time.time()))
            self._cond.notify()

    def _reaper(self):
        # idle_ttl <= 0 -> never close idle connections; they live until the
        # server drops them (detected by is_connected() on next checkout) or
        # until process exit. Costs up to `size` permanent sessions.
        if self._idle_ttl <= 0:
            return
        while not self._closed:
            time.sleep(5)
            cutoff = time.time() - self._idle_ttl
            to_close = []
            with self._cond:
                keep = []
                for cnx, ts in self._idle:
                    (to_close if ts < cutoff else keep).append((cnx, ts))
                self._idle = keep
                self._opened -= len(to_close)
                if to_close:
                    self._cond.notify_all()
            for cnx, _ in to_close:
                self._disconnect(cnx)

    def close_all(self):
        with self._cond:
            self._closed = True
            conns = [c for c, _ in self._idle]
            self._idle = []
            self._opened -= len(conns)
            self._cond.notify_all()
        for cnx in conns:
            self._disconnect(cnx)
        return len(conns)

    @staticmethod
    def _disconnect(cnx):
        try:
            cnx.close()  # sends COM_QUIT -> MySQL frees the session immediately
        except Exception:
            pass


def _get_db_pool():
    global _db_pool
    if _db_pool is None:
        with _db_pool_lock:
            if _db_pool is None:
                idle_desc = (
                    f"idle ones closed after {_DB_POOL_IDLE_SECONDS:.0f}s"
                    if _DB_POOL_IDLE_SECONDS > 0
                    else "idle ones kept until broken"
                )
                print(f"[INFO] MySQL pool: max {_DB_POOL_SIZE} connection(s), {idle_desc}")
                _db_pool = _LazyMySQLPool(_DB_POOL_SIZE, _DB_CONFIG, _DB_POOL_IDLE_SECONDS, wait=_DB_POOL_WAIT_SECONDS)
    return _db_pool


def close_db_pool():
    """Close every idle pooled connection (sends COM_QUIT to MySQL).

    Called from atexit and from the gunicorn worker_exit/on_exit hooks so a
    dyno restart or `heroku ps:restart` frees the MySQL sessions immediately
    instead of leaving them hanging until the server's wait_timeout.
    Safe to call more than once.
    """
    global _db_pool
    with _db_pool_lock:
        pool, _db_pool = _db_pool, None
    if pool is None:
        return
    closed = pool.close_all()
    print(f"[INFO] Closed {closed} pooled MySQL connection(s).")


atexit.register(close_db_pool)


def get_db_connection():
    """Return a pooled MySQL connection. Callers keep calling conn.close()."""
    try:
        return _get_db_pool().get_connection()
    except PoolExhausted:
        # All pooled connections are busy: open a short-lived direct one.
        # Its close() really closes, so it does not hold the user's quota.
        return mysql.connector.connect(**_DB_CONFIG)

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

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS anon_listener_stats (
        anon_id VARCHAR(64) NOT NULL PRIMARY KEY,
        station VARCHAR(64) DEFAULT '',
        total_time INT DEFAULT 0,
        song_count INT DEFAULT 0,
        favorites_count INT DEFAULT 0,
        stats_json LONGTEXT,
        first_seen TIMESTAMP NULL,
        last_seen TIMESTAMP NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS gif_favorites (
        user_id VARCHAR(64) NOT NULL,
        url TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        url_hash VARCHAR(64) AS (SHA2(url, 256)) STORED,
        PRIMARY KEY (user_id, url_hash),
        INDEX idx_user (user_id)
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