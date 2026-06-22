"""
StreamerApi.py — Web-based Radio GAMING Broadcaster
=====================================================
A Flask app that provides a REST API + WebSocket interface for streaming
audio to Icecast/Zeno FM, mirroring the desktop audio_streaming_system.

Auto-discovered by webAppsLauncher.py → mounted at /StreamerApi/
"""

import os
import sys
import subprocess
import threading
import time
import random
import queue
import json
import secrets
import urllib.request
import urllib.parse
import base64

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from flask import Flask, request, jsonify
from flask_cors import cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from api.config import RESTRICT_CORS, RADIO_ADMIN_USER_IDS
from api.FunctionsModule import get_db_connection

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

_CORS_ORIGINS = (
    ["https://radio-gaming.stream", "https://k5studio.dev"] if RESTRICT_CORS else "*"
)
CORS_OPTIONS = {
    "origins": _CORS_ORIGINS,
    "allow_headers": ["Authorization", "Content-Type"],
    "methods": ["GET", "POST", "OPTIONS"],
}

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

# ─── Admin Auth ────────────────────────────────────────────────────────────────
# Reuse the session store from DiscordAuthChatApi (shared process via DispatcherMiddleware)
# We import the module dynamically at runtime to get the live reference

_chat_api_module = None


def _get_chat_api():
    """Lazy import of DiscordAuthChatApi to access shared session data."""
    global _chat_api_module
    if _chat_api_module is None:
        import importlib.util

        chat_path = os.path.join(script_dir, "DiscordAuthChatApi.py")
        spec = importlib.util.spec_from_file_location("DiscordAuthChatApi", chat_path)
        _chat_api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_chat_api_module)
    return _chat_api_module


## RADIO_ADMIN_USER_IDS imported from api.config (centralized)
# Also check dynamic admins from DB (promoted at runtime by owner)

_dynamic_admin_cache = {"ids": set(), "ts": 0}


def _get_dynamic_admins():
    """Load dynamic admin IDs from radio_admins table with 30s cache."""
    now = time.time()
    if now - _dynamic_admin_cache["ts"] < 120:
        return _dynamic_admin_cache["ids"]
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM radio_admins")
        rows = cursor.fetchall()
        conn.close()
        _dynamic_admin_cache["ids"] = set(str(row["user_id"]) for row in rows)
        _dynamic_admin_cache["ts"] = now
    except Exception as e:
        print(f"[StreamerApi] Error loading dynamic admins: {e}")
    return _dynamic_admin_cache["ids"]


def is_admin(user_id):
    uid = str(user_id)
    if uid in RADIO_ADMIN_USER_IDS:
        return True
    return uid in _get_dynamic_admins()


def get_admin_session():
    """Validate Bearer token and check admin access. Returns (session, error_response)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Unauthorized"}), 401)

    token = auth_header.split(" ")[1]

    # Try to use the shared session store from DiscordAuthChatApi
    try:
        chat_api = _get_chat_api()
        session = chat_api.validate_session(token)
    except Exception:
        session = None

    if not session:
        return None, (jsonify({"error": "Invalid or expired session"}), 401)

    if not is_admin(session.get("id")):
        return None, (jsonify({"error": "Admin access required"}), 403)

    return session, None


# ─── Icecast Station Configuration ────────────────────────────────────────────
# Loaded from environment variables for security

STATION_CONFIGS = {
    0: {
        "name": "Radio GAMING DARK",
        "server": os.environ.get("ICECAST_SERVER", "link.zeno.fm"),
        "port": os.environ.get("ICECAST_PORT", "80"),
        "mount": os.environ.get("ICECAST_MOUNT_S0", "pfg9eajshnjtv"),
        "user": "source",
        "password": os.environ.get("ICECAST_PASS_S0", ""),
    },
    1: {
        "name": "Radio GAMING MARON FM",
        "server": os.environ.get("ICECAST_SERVER", "link.zeno.fm"),
        "port": os.environ.get("ICECAST_PORT", "80"),
        "mount": os.environ.get("ICECAST_MOUNT_S1", "5nhy0myl4jpuv"),
        "user": "source",
        "password": os.environ.get("ICECAST_PASS_S1", ""),
    },
    2: {
        "name": "Radio GAMING",
        "server": os.environ.get("ICECAST_SERVER", "link.zeno.fm"),
        "port": os.environ.get("ICECAST_PORT", "80"),
        "mount": os.environ.get("ICECAST_MOUNT_S2", "es4ngpu7ud6tv"),
        "user": "source",
        "password": os.environ.get("ICECAST_PASS_S2", ""),
    },
}


# ─── YouTube Cookies (persisted to DB across Heroku restarts) ──────────────────
COOKIE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "streamer_data")
os.makedirs(COOKIE_DIR, exist_ok=True)
COOKIE_FILE_PATH = os.path.join(COOKIE_DIR, "cookies.txt")


def _init_cookie_table():
    """Create the streamer_cookies table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streamer_cookies (
                id INT PRIMARY KEY DEFAULT 1,
                cookie_data LONGTEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Cookies] DB table init error: {e}")


def _restore_cookies_from_db():
    """On startup, restore cookies.txt from database if local file is missing."""
    if os.path.isfile(COOKIE_FILE_PATH):
        print("[Cookies] Local cookies.txt exists, skipping DB restore.")
        return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cookie_data FROM streamer_cookies WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            with open(COOKIE_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(row[0])
            print(f"[Cookies] Restored cookies.txt from DB ({len(row[0])} bytes)")
        else:
            print("[Cookies] No cookies in DB.")
    except Exception as e:
        print(f"[Cookies] DB restore error: {e}")


def _save_cookies_to_db(cookie_text):
    """Save cookie data to database for persistence."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO streamer_cookies (id, cookie_data) VALUES (1, %s)
            ON DUPLICATE KEY UPDATE cookie_data = %s, updated_at = CURRENT_TIMESTAMP
        """, (cookie_text, cookie_text))
        conn.commit()
        conn.close()
        print(f"[Cookies] Saved to DB ({len(cookie_text)} bytes)")
    except Exception as e:
        print(f"[Cookies] DB save error: {e}")


def _delete_cookies_from_db():
    """Remove cookies from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM streamer_cookies WHERE id = 1")
        conn.commit()
        conn.close()
        print("[Cookies] Deleted from DB.")
    except Exception as e:
        print(f"[Cookies] DB delete error: {e}")


# Initialize on module load
_init_cookie_table()
_restore_cookies_from_db()


# ─── Startup Config (per-station, persisted to DB) ─────────────────────────────

def _init_startup_table():
    """Create streamer_startup_config table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streamer_startup_config (
                station_id INT PRIMARY KEY,
                auto_connect TINYINT(1) DEFAULT 0,
                use_custom_icecast TINYINT(1) DEFAULT 0,
                icecast_server VARCHAR(255) DEFAULT '',
                icecast_port VARCHAR(10) DEFAULT '80',
                icecast_mount VARCHAR(255) DEFAULT '',
                icecast_password VARCHAR(255) DEFAULT '',
                playlist_url TEXT,
                shuffle_enabled TINYINT(1) DEFAULT 0,
                shuffle_count INT DEFAULT 1,
                loop_mode VARCHAR(10) DEFAULT 'off',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Startup] DB table init error: {e}")


def _load_startup_config(station_id):
    """Load startup config for a station from DB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM streamer_startup_config WHERE station_id = %s", (station_id,))
        row = cursor.fetchone()
        conn.close()
        return row
    except Exception as e:
        print(f"[Startup] DB load error: {e}")
        return None


def _save_startup_config(station_id, config):
    """Save startup config for a station to DB."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO streamer_startup_config
                (station_id, auto_connect, use_custom_icecast,
                 icecast_server, icecast_port, icecast_mount, icecast_password,
                 playlist_url, shuffle_enabled, shuffle_count, loop_mode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                auto_connect = VALUES(auto_connect),
                use_custom_icecast = VALUES(use_custom_icecast),
                icecast_server = VALUES(icecast_server),
                icecast_port = VALUES(icecast_port),
                icecast_mount = VALUES(icecast_mount),
                icecast_password = VALUES(icecast_password),
                playlist_url = VALUES(playlist_url),
                shuffle_enabled = VALUES(shuffle_enabled),
                shuffle_count = VALUES(shuffle_count),
                loop_mode = VALUES(loop_mode),
                updated_at = CURRENT_TIMESTAMP
        """, (
            station_id,
            config.get("auto_connect", False),
            config.get("use_custom_icecast", False),
            config.get("icecast_server", ""),
            config.get("icecast_port", "80"),
            config.get("icecast_mount", ""),
            config.get("icecast_password", ""),
            config.get("playlist_url", ""),
            config.get("shuffle_enabled", False),
            config.get("shuffle_count", 1),
            config.get("loop_mode", "off"),
        ))
        conn.commit()
        conn.close()
        print(f"[Startup] Config saved for station {station_id}")
    except Exception as e:
        print(f"[Startup] DB save error: {e}")


_init_startup_table()


# ─── Admin Presence Tracking (in-memory, no extra fetch needed) ────────────────

_admin_presence = {}  # user_id -> {name, avatar_url, last_heartbeat, online_since, actions: [{time, action}]}
_admin_presence_lock = threading.Lock()
ADMIN_ONLINE_THRESHOLD = 30  # seconds — consider offline after this
ADMIN_MAX_ACTIONS = 50  # max action log entries per admin


def _admin_heartbeat(session, action=None):
    """Update admin presence. Called automatically on every authenticated API call."""
    uid = str(session.get("id", ""))
    if not uid:
        return
    now = time.time()
    with _admin_presence_lock:
        if uid not in _admin_presence:
            _admin_presence[uid] = {
                "name": session.get("global_name") or session.get("username", "Admin"),
                "avatar_url": session.get("avatar_url", ""),
                "last_heartbeat": now,
                "online_since": now,
                "actions": [],
            }
            # Log the "came online" event
            _admin_presence[uid]["actions"].append({
                "time": time.strftime("%H:%M:%S"),
                "ts": now,
                "action": "Wszedł online",
            })
        else:
            entry = _admin_presence[uid]
            # If was offline and came back, reset online_since
            if now - entry["last_heartbeat"] > ADMIN_ONLINE_THRESHOLD:
                entry["online_since"] = now
                entry["actions"].append({
                    "time": time.strftime("%H:%M:%S"),
                    "ts": now,
                    "action": "Wrócił online",
                })
            entry["last_heartbeat"] = now
            entry["name"] = session.get("global_name") or session.get("username", entry["name"])
            entry["avatar_url"] = session.get("avatar_url", entry["avatar_url"])

        if action:
            _admin_presence[uid]["actions"].append({
                "time": time.strftime("%H:%M:%S"),
                "ts": now,
                "action": action,
            })
            # Trim old actions
            if len(_admin_presence[uid]["actions"]) > ADMIN_MAX_ACTIONS:
                _admin_presence[uid]["actions"] = _admin_presence[uid]["actions"][-ADMIN_MAX_ACTIONS:]


def _get_admin_presence_data():
    """Return list of admins with online status and recent actions."""
    now = time.time()
    result = []
    with _admin_presence_lock:
        for uid, data in _admin_presence.items():
            is_online = (now - data["last_heartbeat"]) < ADMIN_ONLINE_THRESHOLD
            result.append({
                "id": uid,
                "name": data["name"],
                "avatar_url": data["avatar_url"],
                "is_online": is_online,
                "online_since": data["online_since"],
                "last_heartbeat": data["last_heartbeat"],
                "actions": data["actions"][-15:],  # last 15 actions for UI
            })
    # Online admins first
    result.sort(key=lambda x: (x["is_online"], x["last_heartbeat"]), reverse=True)
    return result


# ─── Input History (persisted to DB) ───────────────────────────────────────────

def _init_input_history_table():
    """Create streamer_input_history table for persisting all enqueued inputs."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streamer_input_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                station_id INT NOT NULL,
                url TEXT NOT NULL,
                custom_name VARCHAR(255) DEFAULT NULL,
                resolved_title VARCHAR(255) DEFAULT NULL,
                added_by_id VARCHAR(64),
                added_by_name VARCHAR(128),
                instant TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_station (station_id),
                INDEX idx_created (created_at)
            )
        """)
        conn.commit()
        conn.close()
        print("[InputHistory] Table ready.")
    except Exception as e:
        print(f"[InputHistory] DB table init error: {e}")


def _save_input_history(station_id, url, admin_session, instant=False, custom_name=None):
    """Save an enqueued input to the history database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO streamer_input_history
                (station_id, url, custom_name, added_by_id, added_by_name, instant)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            station_id,
            url[:2000],  # cap URL length
            custom_name[:255] if custom_name else None,
            str(admin_session.get("id", "")),
            admin_session.get("global_name") or admin_session.get("username", "Unknown"),
            instant,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[InputHistory] Save error: {e}")


def _get_input_history(station_id=None, limit=50, offset=0):
    """Load input history from DB. Optional station filter."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if station_id is not None:
            cursor.execute("""
                SELECT * FROM streamer_input_history
                WHERE station_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (station_id, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM streamer_input_history
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        # Convert datetime objects to strings
        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        return rows
    except Exception as e:
        print(f"[InputHistory] Load error: {e}")
        return []


def _update_input_custom_name(entry_id, custom_name):
    """Update custom_name for an input history entry."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE streamer_input_history
            SET custom_name = %s
            WHERE id = %s
        """, (custom_name[:255] if custom_name else None, entry_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[InputHistory] Update error: {e}")
        return False


_init_input_history_table()


def get_cookie_opts():
    """Return cookiefile dict if cookies.txt exists, else empty dict."""
    if os.path.isfile(COOKIE_FILE_PATH):
        return {"cookiefile": COOKIE_FILE_PATH}
    return {}


# ─── Stream Station Engine (ported from audio_streaming_system) ────────────────


class WebStreamStation:
    """Server-side streaming station that encodes and transmits audio to Icecast.
    Ported from the desktop StreamStation class in stream_engine.py.
    """

    _connection_lock = threading.Lock()

    def __init__(self, station_id, callback=None):
        self.station_id = station_id
        self.callback = callback
        self.running = False
        self.transmitter = None
        self.feeder = None
        self.current_song = "None"
        self.loop_mode = "off"  # "off", "single", "queue"
        self.bitrate = "128k"
        self.skip_requested = False
        self.name = STATION_CONFIGS.get(station_id, {}).get(
            "name", f"Station {station_id + 1}"
        )
        self.manual_queue = []
        self.manual_history = []
        self._established = False
        self._url_processing = False
        self._queue_lock = threading.Lock()
        self._last_instant_id = 0
        self._conn_start_time = None
        self._conn_bytes_sent = 0
        self._log_buffer = []
        self._log_lock = threading.Lock()
        self.mic_active = False
        self.mic_queue = queue.Queue(maxsize=100)
        self._queue_titles = {}  # url -> display title
        self._queue_thumbnails = {}  # url -> thumbnail URL
        self._idle_since = None  # Timestamp when idle started (for auto-disconnect)
        self.auto_disconnect_empty = False  # Auto-disconnect when queue empties (no loop)

        # Preload system — download next 3 queue songs ahead as MP3
        self._preload_cache = {}   # original_path -> local_mp3_path
        self._preload_lock = threading.Lock()
        self.preload_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "streamer_data",
            f"preload_{station_id}",
        )
        os.makedirs(self.preload_dir, exist_ok=True)
        self._preload_thread = threading.Thread(target=self._preload_loop, daemon=True)
        self._preload_thread.start()

    def log(self, message):
        """Log a message and store it for polling."""
        with self._log_lock:
            self._log_buffer.append(
                {"time": time.strftime("%H:%M:%S"), "message": message}
            )
            # Keep last 200 log entries
            if len(self._log_buffer) > 200:
                self._log_buffer = self._log_buffer[-200:]

        if self.callback:
            self.callback(self.station_id, message)

        try:
            print(f"[{self.name}] {message}")
        except UnicodeEncodeError:
            sanitized = message.encode("ascii", "replace").decode("ascii")
            print(f"[{self.name}] {sanitized}")

    def get_logs(self, since_index=0):
        """Return log entries since a given index."""
        with self._log_lock:
            return self._log_buffer[since_index:]

    def get_status(self):
        """Return current station status."""
        with self._queue_lock:
            queue_list = list(self.manual_queue)

        # Only limit thumbnails (heavy URLs) to first 50; titles are lightweight strings
        visible_urls = set(queue_list[:50])
        visible_thumbs = {u: t for u, t in self._queue_thumbnails.items() if u in visible_urls}

        return {
            "station_id": self.station_id,
            "name": self.name,
            "running": self.running,
            "established": self._established,
            "current_song": self.current_song,
            "loop_mode": self.loop_mode,
            "mic_active": self.mic_active,
            "auto_disconnect_empty": self.auto_disconnect_empty,
            "queue": queue_list,
            "queue_length": len(queue_list),
            "queue_titles": dict(self._queue_titles),
            "queue_thumbnails": visible_thumbs,
            "history": self.manual_history[:20],
            "log_count": len(self._log_buffer),
        }

    def _add_to_history(self, item):
        if item in self.manual_history:
            self.manual_history.remove(item)
        self.manual_history.insert(0, item)
        if len(self.manual_history) > 100:
            self.manual_history = self.manual_history[:100]

    def start(self):
        if self.running:
            return

        config = STATION_CONFIGS.get(self.station_id)
        if not config:
            self.log("Error: No config for this station")
            return

        self.server = config.get("server", "")
        self.port = config.get("port", "80")
        self.mount = config.get("mount", "")
        self.user = config.get("user", "source")
        self.password = config.get("password", "")

        missing = []
        if not self.server:
            missing.append("Server Address")
        if not self.mount:
            missing.append("Mount Point")
        if not self.password:
            missing.append("Password")

        if missing:
            self.log(f"Error: Missing settings ({', '.join(missing)})")
            return

        self.running = True
        self._established = False
        self.thread = threading.Thread(target=self._run_stream, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.feeder:
            try:
                self.feeder.kill()
            except Exception:
                pass
        if self.transmitter:
            try:
                self.transmitter.stdin.close()
                self.transmitter.kill()
            except Exception:
                pass
        self._established = False

        # Clean up preload cache
        try:
            with self._preload_lock:
                self._preload_cache.clear()
            import shutil
            if os.path.exists(self.preload_dir):
                shutil.rmtree(self.preload_dir, ignore_errors=True)
                os.makedirs(self.preload_dir, exist_ok=True)
        except Exception:
            pass

        self.log("Stream stopped")

    # ─── Preload Worker ────────────────────────────────────────────────────────

    def _preload_loop(self):
        """Background worker: downloads next 3 songs from queue as MP3 to local storage."""
        while True:
            try:
                if not self.running:
                    time.sleep(3)
                    continue

                # Get next 3 from queue
                to_preload = []
                with self._queue_lock:
                    to_preload = list(self.manual_queue[:3])

                # Filter already cached
                targets = []
                for p in to_preload:
                    with self._preload_lock:
                        if p not in self._preload_cache:
                            targets.append(p)

                for path in targets:
                    if not self.running:
                        break

                    is_url = path.startswith("http") or path.startswith("ytsearch")
                    if not is_url:
                        continue

                    try:
                        import yt_dlp

                        # First get metadata for filename
                        with yt_dlp.YoutubeDL(
                            {"quiet": True, "no_warnings": True, **get_cookie_opts()}
                        ) as ydl:
                            info = ydl.extract_info(path, download=False)
                            if "entries" in info:
                                info = info["entries"][0]
                            title = info.get("title", "Unknown")
                            uploader = info.get("uploader", "Unknown")
                            if uploader.endswith(" - Topic"):
                                uploader = uploader[:-8]

                            # Build display name for logging
                            if uploader.lower() not in title.lower():
                                clean_name = f"{uploader} - {title}"
                            else:
                                clean_name = title

                            # Update queue title with full artist info for frontend display & cover search
                            if uploader.lower() not in title.lower():
                                self._queue_titles[path] = f"{uploader} - {title}"
                            else:
                                self._queue_titles[path] = title

                            # Save thumbnail URL
                            thumb = info.get("thumbnail") or ""
                            if thumb:
                                self._queue_thumbnails[path] = thumb

                        # Use UUID for filename to avoid emoji/encoding issues
                        import uuid as _uuid_pl
                        dl_id = _uuid_pl.uuid4().hex[:12]
                        local_dest = os.path.join(self.preload_dir, f"{dl_id}.mp3")

                        if os.path.exists(local_dest):
                            with self._preload_lock:
                                self._preload_cache[path] = local_dest
                            continue

                        ydl_opts = {
                            "format": "bestaudio/best",
                            "outtmpl": os.path.join(self.preload_dir, f"{dl_id}.%(ext)s"),
                            "postprocessors": [
                                {
                                    "key": "FFmpegExtractAudio",
                                    "preferredcodec": "mp3",
                                    "preferredquality": "192",
                                }
                            ],
                            "quiet": True,
                            "no_warnings": True,
                            **get_cookie_opts(),
                        }

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            self.log(f"Preloading: {clean_name}")
                            ydl.download([path])

                        if os.path.exists(local_dest):
                            with self._preload_lock:
                                self._preload_cache[path] = local_dest
                    except Exception as e:
                        self.log(f"Preload failed: {e}")
                        # Track failures — remove from queue after 2 failed attempts
                        if not hasattr(self, '_preload_failures'):
                            self._preload_failures = {}
                        self._preload_failures[path] = self._preload_failures.get(path, 0) + 1
                        if self._preload_failures[path] >= 2:
                            with self._queue_lock:
                                if path in self.manual_queue:
                                    self.manual_queue.remove(path)
                                    title = self._queue_titles.get(path, path)
                                    self.log(f"Removed unavailable: {title}")
                            self._preload_failures.pop(path, None)

                    time.sleep(1)  # Gap between downloads

            except Exception:
                time.sleep(5)
            time.sleep(5)  # Periodic check

    def _resolve_titles(self, urls):
        """Background: resolve proper 'Artist - Title' for queue items missing artist info.
        Prioritizes the first 20 (visible page) before resolving the rest.
        """
        import yt_dlp

        # Prioritize first 20 items (visible queue page), then the rest
        priority = urls[:20]
        remaining = urls[20:]
        ordered = priority + remaining

        resolved = 0
        for url in ordered:
            if not self.running:
                break

            # Skip if already has a dash (artist separator) in title
            existing = self._queue_titles.get(url, "")
            if " - " in existing:
                continue

            # Only resolve YouTube URLs
            if not (url.startswith("http") and ("youtube" in url or "youtu.be" in url)):
                continue

            try:
                with yt_dlp.YoutubeDL(
                    {"quiet": True, "no_warnings": True, "skip_download": True, **get_cookie_opts()}
                ) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if "entries" in info:
                        info = info["entries"][0]

                    title = info.get("title", "")
                    uploader = info.get("uploader", "")
                    if uploader and uploader.endswith(" - Topic"):
                        uploader = uploader[:-8]

                    if uploader and uploader.lower() not in title.lower():
                        self._queue_titles[url] = f"{uploader} - {title}"
                    elif title:
                        self._queue_titles[url] = title

                    # Save thumbnail URL
                    thumb = info.get("thumbnail") or ""
                    if thumb:
                        self._queue_thumbnails[url] = thumb

                    resolved += 1
                    if resolved == 20:
                        self.log(f"Resolved titles for visible page (20 items)")
                    elif resolved % 50 == 0:
                        self.log(f"Resolved titles: {resolved}/{len(ordered)}")

            except Exception:
                pass

            time.sleep(0.3)  # Rate limit — faster for priority items

    def skip_song(self):
        self.skip_requested = True
        if self.feeder:
            self.log("Skipping song...")
            try:
                self.feeder.kill()
            except Exception:
                pass

    def toggle_loop(self, mode):
        self.loop_mode = mode
        self.log(f"Loop mode set to: {mode.upper()}")

    def set_mic(self, active):
        """Toggle microphone broadcasting."""
        self.mic_active = active
        # Drain any leftover mic data when turning off
        if not active:
            while not self.mic_queue.empty():
                try:
                    self.mic_queue.get_nowait()
                except queue.Empty:
                    break
        self.log(f"Microphone: {'ON' if active else 'OFF'}")

    def feed_mic_data(self, pcm_bytes):
        """Accept raw PCM data from browser mic (s16le, 44100Hz, stereo)."""
        if not self.mic_active or not self.running:
            return
        try:
            self.mic_queue.put_nowait(pcm_bytes)
        except queue.Full:
            # Drop oldest chunk to prevent backpressure
            try:
                self.mic_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.mic_queue.put_nowait(pcm_bytes)
            except queue.Full:
                pass

    def enqueue(self, file_path, instant=False):
        """Add a song (URL or search query) to the queue."""
        with self._queue_lock:
            self._add_to_history(file_path)
            self._last_instant_id += 1
            my_id = self._last_instant_id

            # Handle URL processing in background
            if file_path.startswith("http") or file_path.startswith("ytsearch"):
                threading.Thread(
                    target=self._handle_url_enqueue,
                    args=(file_path, instant, my_id),
                    daemon=True,
                ).start()
                return

            # Treat as YouTube search if not a URL
            self.log(f"Searching YouTube for: {file_path}")
            search_query = f"ytsearch1:{file_path}"
            threading.Thread(
                target=self._handle_url_enqueue,
                args=(search_query, instant, my_id),
                daemon=True,
            ).start()

    def clear_queue(self):
        with self._queue_lock:
            self.manual_queue = []
        self.log("Queue cleared.")

    def shuffle_queue(self):
        with self._queue_lock:
            if len(self.manual_queue) > 1:
                random.shuffle(self.manual_queue)
                self.log("Queue shuffled.")
            else:
                self.log("Not enough items to shuffle.")

    def get_queue(self):
        with self._queue_lock:
            return list(self.manual_queue)

    def clear_history(self):
        self.manual_history = []
        self.log("History cleared.")

    def get_history(self):
        return list(self.manual_history)

    def restore_from_history(self, index, instant=False):
        if 0 <= index < len(self.manual_history):
            item = self.manual_history[index]
            self.enqueue(item, instant=instant)
            return True
        return False

    # ─── Icecast Metadata Update ──────────────────────────────────────────────

    def _send_metadata_request(self, title):
        """Send a single HTTP GET to Icecast admin API to update song metadata.
        Returns True on success, False on failure. Uses short timeout to avoid blocking."""
        try:
            mount_point = (
                self.mount if self.mount.startswith("/") else f"/{self.mount}"
            )
            params = urllib.parse.urlencode(
                {"mode": "updinfo", "mount": mount_point, "song": title}
            )
            url = f"http://{self.server}:{self.port}/admin/metadata?{params}"
            auth_str = f"{self.user}:{self.password}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()

            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Basic {encoded_auth}")
            req.add_header(
                "User-Agent",
                "Mozilla/5.0 RadioGamingWebStreamer/1.0",
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception as e:
            print(f"[{self.name}] Metadata update error: {e}")
            return False

    def _update_metadata(self, title, delay=0, retry_delays=None):
        """Send metadata to Icecast in separate threads for each attempt.
        Each attempt runs independently so a slow/hanging request can't block the others."""
        if not self.running:
            return

        if retry_delays is None:
            retry_delays = [5, 10]

        # Build list of absolute delays from start: [4, 9, 19] for delay=4, retries=[5,10]
        all_delays = [delay]
        cumulative = delay
        for rd in retry_delays:
            cumulative += rd
            all_delays.append(cumulative)

        for send_delay in all_delays:
            def _single_send(d=send_delay):
                try:
                    if d > 0:
                        time.sleep(d)
                    if not self.running or self.current_song != title:
                        return
                    self._send_metadata_request(title)
                except Exception as e:
                    print(f"[{self.name}] Metadata task error: {e}")

            threading.Thread(target=_single_send, daemon=True).start()

    # ─── Silence / Filler Feeding ─────────────────────────────────────────────

    def _feed_silence(self, duration_sec):
        """Feed silence to the transmitter for a specific duration."""
        if not self.transmitter or self.transmitter.poll() is not None:
            time.sleep(duration_sec)
            return

        start = time.time()
        bytes_per_sec = 44100 * 2 * 2

        if self._conn_start_time is None:
            self._conn_start_time = time.time()
            self._conn_bytes_sent = 0

        while self.running and (time.time() - start < duration_sec):
            try:
                chunk = b"\x00" * 4096
                self.transmitter.stdin.write(chunk)
                self._conn_bytes_sent += len(chunk)
            except Exception:
                break

            try:
                self.transmitter.stdin.flush()
            except Exception:
                pass

            expected = (self._conn_bytes_sent / bytes_per_sec) - 0.5
            actual = time.time() - self._conn_start_time
            if expected > actual:
                time.sleep(min(expected - actual, 0.01))
            else:
                time.sleep(0.001)

    def _handle_no_media(self):
        """Maintain stream when queue is empty: silence to keep connection alive.
        Auto-disconnects after 2 minutes of continuous idle,
        or immediately if auto_disconnect_empty is enabled and loop is off."""

        # Track idle start
        if self._idle_since is None:
            self._idle_since = time.time()

            # Immediate disconnect if checkbox enabled and not looping
            if self.auto_disconnect_empty and self.loop_mode == "off":
                self.log("Queue empty + auto-disconnect enabled. Rozłączam...")
                self.stop()
                return

            self.log("Queue empty. Entering idle mode...")
            self.current_song = "RADIO GAMING Live/Idle"
            self._update_metadata("RADIO GAMING Live/Idle", delay=1, retry_delays=[])

        # Auto-disconnect after 2 minutes idle
        idle_seconds = time.time() - self._idle_since
        if idle_seconds >= 120:
            self.log(f"Idle for {int(idle_seconds)}s. Auto-disconnecting...")
            self.stop()
            return

        bytes_per_sec = 44100 * 2 * 2
        start_time = time.time()

        if self._conn_start_time is None:
            self._conn_start_time = time.time()
            self._conn_bytes_sent = 0

        while self.running and (time.time() - start_time < 4):
            with self._queue_lock:
                if self.manual_queue:
                    self._idle_since = None  # Reset idle timer
                    return

            if self.transmitter and self.transmitter.poll() is not None:
                return

            silence = b"\x00" * 4096
            try:
                self.transmitter.stdin.write(silence)
                self._conn_bytes_sent += len(silence)
            except Exception:
                break

            expected = (self._conn_bytes_sent / bytes_per_sec) - 0.5
            actual = time.time() - self._conn_start_time
            if expected > actual:
                time.sleep(min(expected - actual, 0.1))

    # ─── Main Stream Loop ─────────────────────────────────────────────────────

    def _run_stream(self):
        while self.running:
            # Jitter to prevent simultaneous connections
            if self.running:
                jitter = random.uniform(1.0, 4.0)
                time.sleep(jitter)

            # Wait for first song to be preloaded before connecting to Icecast
            if self.running:
                self.log("Waiting for first song to be ready...")
                waited = 0
                while self.running and waited < 120:  # Max 2 min wait
                    with self._queue_lock:
                        first = self.manual_queue[0] if self.manual_queue else None
                    if not first:
                        break  # Empty queue, will handle in idle loop
                    # If it's a local file (not URL), it's ready
                    if not first.startswith("http") and not first.startswith("ytsearch"):
                        break
                    # Check if preloaded
                    with self._preload_lock:
                        if first in self._preload_cache:
                            self.log("First song preloaded, connecting...")
                            break
                    time.sleep(0.5)
                    waited += 0.5
                if not self.running:
                    break

            # Start FFmpeg transmitter → Icecast
            safe_user = urllib.parse.quote(self.user)
            safe_pass = urllib.parse.quote(self.password)
            norm_mount = self.mount if self.mount.startswith("/") else f"/{self.mount}"
            icecast_url = f"icecast://{safe_user}:{safe_pass}@{self.server}:{self.port}{norm_mount}"

            self.log("Waiting for connection slot...")
            with self._connection_lock:
                self.log("Server Handshake... (5s cooldown)")

                trans_cmd = [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "s16le",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-i",
                    "pipe:0",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    self.bitrate,
                    "-bufsize",
                    "512k",
                    "-f",
                    "mp3",
                    "-timeout",
                    "5000000",
                    icecast_url,
                ]

                try:
                    self.transmitter = subprocess.Popen(
                        trans_cmd,
                        stdin=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=512 * 1024,
                    )

                    # Monitor stderr in background
                    def monitor_transmitter(proc):
                        while proc.poll() is None:
                            try:
                                line = proc.stderr.readline().decode(
                                    "utf-8", errors="replace"
                                )
                                if not line:
                                    break
                                if any(
                                    x in line
                                    for x in ["Error", "401", "10053", "Aborted", "reset"]
                                ):
                                    if "401" in line:
                                        self.log(
                                            "Error: 401 Unauthorized. Check Icecast password."
                                        )
                                    elif "10053" in line or "reset" in line:
                                        self.log("Network: Connection aborted by server.")
                                    else:
                                        self.log(f"Transmitter Alert: {line.strip()}")
                            except Exception:
                                break

                    threading.Thread(
                        target=monitor_transmitter,
                        args=(self.transmitter,),
                        daemon=True,
                    ).start()

                except Exception as e:
                    self.log(f"Setup Failed: {e}")
                    time.sleep(5)
                    continue

                time.sleep(5)
                self._conn_start_time = time.time()
                self._conn_bytes_sent = 0
                self._established = True
                self.log("Connected to Icecast!")

            # Feed songs as PCM into the transmitter
            inner_running = True

            time.sleep(1)

            while self.running and inner_running:
                file_path = None

                with self._queue_lock:
                    if self.manual_queue:
                        file_path = self.manual_queue.pop(0)
                        self.skip_requested = False
                        self._idle_since = None  # Reset idle timer when song starts

                if not file_path:
                    self._handle_no_media()
                    if not self.running:  # Auto-disconnected
                        break
                    continue

                is_url = file_path.startswith("http") or file_path.startswith(
                    "ytsearch"
                )

                # Check preload cache — use local MP3 if available
                preloaded_path = None
                with self._preload_lock:
                    if file_path in self._preload_cache:
                        preloaded_path = self._preload_cache[file_path]
                        if os.path.exists(preloaded_path):
                            self.log(f"Using preloaded: {os.path.basename(preloaded_path)}")
                        else:
                            preloaded_path = None

                while self.running:
                    if preloaded_path:
                        # Play from preloaded local MP3
                        play_path = preloaded_path
                        clean_title = os.path.basename(preloaded_path).rsplit(".", 1)[0]
                        self.current_song = clean_title
                        is_url = False  # local file, no reconnect flags needed
                    elif is_url:
                        self.log(f"Fetching info: {file_path}")
                        try:
                            import yt_dlp

                            ydl_opts_fetch = {
                                "format": "bestaudio/best",
                                "quiet": True,
                                "no_warnings": True,
                                "noplaylist": True,
                                "nocheckcertificate": True,
                                **get_cookie_opts(),
                            }

                            fetch_res = {}

                            def do_fetch():
                                try:
                                    with yt_dlp.YoutubeDL(ydl_opts_fetch) as ydl:
                                        fetch_res["info"] = ydl.extract_info(
                                            file_path, download=False
                                        )
                                except Exception as e:
                                    fetch_res["error"] = e

                            t = threading.Thread(target=do_fetch, daemon=True)
                            t.start()

                            # Keep transmitter fed while fetching
                            while t.is_alive():
                                self._feed_silence(0.1)

                            if "error" in fetch_res:
                                raise fetch_res["error"]

                            info = fetch_res["info"]
                            if "entries" in info:
                                info = info["entries"][0]

                            # Build "Artist - Title" format
                            title = info.get("title", "Web Stream")
                            uploader = info.get("uploader", "")
                            if uploader and uploader.endswith(" - Topic"):
                                uploader = uploader[:-8]
                            if uploader and uploader.lower() not in title.lower():
                                clean_title = f"{uploader} - {title}"
                            else:
                                clean_title = title
                            self.current_song = clean_title

                            # Check if this is a live stream
                            if info.get("is_live"):
                                # Live stream — use direct URL streaming
                                play_path = info.get("url")
                                if (
                                    not play_path
                                    and "formats" in info
                                    and info["formats"]
                                ):
                                    play_path = info["formats"][-1].get("url")
                                if not play_path:
                                    raise Exception("No playable URL found.")
                                self.log(f"Live stream detected, streaming directly")
                            else:
                                # Not live — download as MP3 first, then play from local file
                                self.log(f"Downloading: {clean_title}")
                                import uuid as _uuid
                                # Use UUID for filename to avoid all encoding/emoji/filesystem issues
                                dl_id = _uuid.uuid4().hex[:12]
                                local_dest = os.path.join(self.preload_dir, f"{dl_id}.mp3")

                                dl_opts = {
                                    "format": "bestaudio/best",
                                    "quiet": True,
                                    "no_warnings": True,
                                    "noplaylist": True,
                                    "nocheckcertificate": True,
                                    "outtmpl": os.path.join(self.preload_dir, f"{dl_id}.%(ext)s"),
                                    "postprocessors": [{
                                        "key": "FFmpegExtractAudio",
                                        "preferredcodec": "mp3",
                                        "preferredquality": "192",
                                    }],
                                    **get_cookie_opts(),
                                }

                                dl_res = {}

                                def do_download():
                                    try:
                                        with yt_dlp.YoutubeDL(dl_opts) as ydl:
                                            ydl.download([file_path])
                                        dl_res["ok"] = True
                                    except Exception as e:
                                        dl_res["error"] = e

                                dl_thread = threading.Thread(target=do_download, daemon=True)
                                dl_thread.start()

                                # Keep transmitter fed while downloading
                                while dl_thread.is_alive():
                                    self._feed_silence(0.1)

                                if "error" in dl_res:
                                    raise dl_res["error"]

                                if not os.path.exists(local_dest):
                                    raise Exception(f"Download completed but file not found: {local_dest}")

                                play_path = local_dest
                                preloaded_path = local_dest  # Mark for cleanup after playing
                                is_url = False  # Local file, no reconnect flags needed
                                self.log(f"Downloaded OK, playing from local file")

                        except Exception as e:
                            self.log(f"Stream expansion failed: {e}")
                            self._feed_silence(2.0)
                            break
                    else:
                        play_path = file_path
                        clean_title = os.path.basename(file_path).rsplit(".", 1)[0]
                        self.current_song = clean_title
                    # Clean display title: strip (...) suffixes and stray quotes
                    import re
                    clean_title = re.sub(r'\s*\([^)]*\)', '', clean_title).strip()
                    clean_title = clean_title.replace('"', '').strip()
                    self.current_song = clean_title

                    self.log(f"Playing: {clean_title}")
                    self._update_metadata(clean_title, delay=4)

                    # Feeder: decode audio to raw PCM
                    feeder_cmd = [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "quiet",
                    ]

                    if is_url:
                        feeder_cmd.extend(
                            [
                                "-reconnect",
                                "1",
                                "-reconnect_at_eof",
                                "1",
                                "-reconnect_streamed",
                                "1",
                                "-reconnect_delay_max",
                                "5",
                            ]
                        )

                    feeder_cmd.extend(
                        ["-i", play_path, "-f", "s16le", "-ar", "44100", "-ac", "2", "pipe:1"]
                    )

                    try:
                        if self.transmitter.poll() is not None:
                            self.log("Transmitter died. Reconnecting...")
                            inner_running = False
                            break

                        self.feeder = subprocess.Popen(
                            feeder_cmd,
                            stdout=subprocess.PIPE,
                            bufsize=256 * 1024,
                        )

                        feeder_queue_local = queue.Queue(maxsize=20)

                        def feeder_worker(proc, q):
                            while self.running and proc.poll() is None:
                                try:
                                    c = proc.stdout.read(65536)
                                    if not c:
                                        break
                                    q.put(c)
                                except Exception:
                                    break

                        threading.Thread(
                            target=feeder_worker,
                            args=(self.feeder, feeder_queue_local),
                            daemon=True,
                        ).start()

                        # Stream PCM data with realtime throttling
                        bytes_per_sec = 44100 * 2 * 2

                        while self.running and not self.skip_requested:
                            if self._conn_start_time is None:
                                self._conn_start_time = time.time()
                                self._conn_bytes_sent = 0

                            # ─── Mic Priority: when mic is ON, feed mic data instead of music ───
                            if self.mic_active:
                                try:
                                    chunk = self.mic_queue.get(timeout=0.02)
                                except queue.Empty:
                                    # No mic data yet — send silence to keep stream alive
                                    chunk = b"\x00" * 4096

                                try:
                                    self.transmitter.stdin.write(chunk)
                                    self._conn_bytes_sent += len(chunk)
                                except Exception:
                                    inner_running = False
                                    break

                                # Drain feeder to prevent buffer buildup
                                try:
                                    feeder_queue_local.get_nowait()
                                except queue.Empty:
                                    pass

                                # Throttle
                                expected_elapsed = (self._conn_bytes_sent / bytes_per_sec) - 0.5
                                actual_elapsed = time.time() - self._conn_start_time
                                sleep_time = expected_elapsed - actual_elapsed
                                if sleep_time > 0.01:
                                    time.sleep(min(sleep_time, 0.2))
                                elif sleep_time < -5.0:
                                    self._conn_start_time = time.time()
                                    self._conn_bytes_sent = 0
                                else:
                                    time.sleep(0.005)
                                continue

                            # ─── Normal Music Playback ───────────────────────────────────────
                            try:
                                chunk = feeder_queue_local.get(timeout=0.05)
                            except queue.Empty:
                                if self.feeder.poll() is not None:
                                    break
                                silence = b"\x00" * 4096
                                try:
                                    self.transmitter.stdin.write(silence)
                                    self._conn_bytes_sent += len(silence)
                                except Exception:
                                    inner_running = False
                                    break
                                continue

                            try:
                                self.transmitter.stdin.write(chunk)
                                self._conn_bytes_sent += len(chunk)
                            except Exception as e:
                                self.log(f"Pipe Error: {e}. Reconnecting...")
                                inner_running = False
                                break

                            # Realtime throttle — stay ~1.5s ahead of realtime
                            expected_elapsed = (
                                self._conn_bytes_sent / bytes_per_sec
                            ) - 1.5
                            actual_elapsed = time.time() - self._conn_start_time
                            sleep_time = expected_elapsed - actual_elapsed
                            if sleep_time > 0.005:
                                time.sleep(min(sleep_time, 0.2))
                            elif sleep_time < -5.0:
                                self._conn_start_time = time.time()
                                self._conn_bytes_sent = 0
                            else:
                                time.sleep(0.001)

                        # Finalize
                        try:
                            self.transmitter.stdin.flush()
                        except Exception:
                            pass
                        try:
                            self.feeder.kill()
                        except Exception:
                            pass

                        # No silence gap — seamless transition self._feed_silence(0.5)

                        # Clean up preloaded file after playing
                        if preloaded_path and os.path.exists(preloaded_path):
                            try:
                                os.remove(preloaded_path)
                                with self._preload_lock:
                                    # Remove from cache by value
                                    keys_to_remove = [k for k, v in self._preload_cache.items() if v == preloaded_path]
                                    for k in keys_to_remove:
                                        del self._preload_cache[k]
                            except Exception:
                                pass

                        if not self.running or not inner_running:
                            break
                        if self.skip_requested:
                            self.log("Skip signal received.")
                            try:
                                self.transmitter.stdin.write(b"\x00" * 8192)
                            except Exception:
                                pass

                        if self.loop_mode == "single":
                            continue
                        elif self.loop_mode == "queue":
                            with self._queue_lock:
                                self.manual_queue.append(file_path)
                            break
                        else:
                            break
                    except Exception as e:
                        self.log(f"Playback error: {e}")
                        break

                if not self.running or not inner_running:
                    break

            # Clean up transmitter before reconnect
            if self.transmitter:
                try:
                    self.transmitter.stdin.close()
                    self.transmitter.kill()
                    self.transmitter.wait()
                except Exception:
                    pass
                self.transmitter = None

            if self.running:
                self.log("Global Cooldown (5s)...")
                time.sleep(5)

        self.running = False
        self._established = False

    # ─── URL Processing (YouTube/Spotify) ──────────────────────────────────────

    def _handle_url_enqueue(self, url, instant, req_id):
        """Process a URL (playlist or single) in background and add to queue."""
        self.log(f"Processing URL: {url}")

        # Convert YouTube Music URLs to regular YouTube — YT Music API caps at ~100
        # playlist items while regular YouTube returns all entries
        if "music.youtube.com" in url:
            url = url.replace("music.youtube.com", "www.youtube.com")
            self.log("Converted YouTube Music URL to standard YouTube.")

        # Strip tracking parameters (si= causes YouTube to limit playlists to 100 items!)
        if "si=" in url:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            params.pop("si", None)
            clean_query = urlencode(params, doseq=True)
            url = urlunparse(parsed._replace(query=clean_query))
            self.log(f"Stripped si param: {url}")

        processed_tracks = []

        # Spotify handling
        if "spotify.com" in url:
            tracks = self._get_spotify_tracks(url)
            if tracks:
                self.log(
                    f"Found {len(tracks)} Spotify tracks. Searching YouTube..."
                )
                for track in tracks:
                    processed_tracks.append(f"ytsearch1:{track}")
            else:
                self.log("Could not extract Spotify tracks. Trying yt-dlp direct...")

        if not processed_tracks:
            try:
                self.log("Loading playlist entries...")

                import yt_dlp

                cookie_opts = get_cookie_opts()
                has_cookies = "cookiefile" in cookie_opts
                self.log(f"yt-dlp v{yt_dlp.version.__version__}, cookies={'yes' if has_cookies else 'NO'}")

                all_entries = []

                is_yt = "youtube.com" in url or "youtu.be" in url or "music.youtube" in url
                is_playlist = "?list=" in url or "&list=" in url or "/sets/" in url or "/playlist" in url

                if is_playlist:
                    # Phase 1: Fast flat extract to count entries and get basic metadata
                    flat_opts = {
                        "ignoreerrors": True,
                        "extract_flat": "in_playlist",
                        "playlist-end": 2000,
                        "quiet": True,
                        "no_warnings": True,
                        **cookie_opts,
                    }

                    flat_entries = []
                    with yt_dlp.YoutubeDL(flat_opts) as ydl:
                        flat_info = ydl.extract_info(url, download=False)
                        if flat_info and "entries" in flat_info:
                            flat_entries = [e for e in flat_info["entries"] if e is not None]

                    entry_count = len(flat_entries)
                    self.log(f"Playlist has {entry_count} entries")

                    # Phase 2: Choose strategy based on size
                    if entry_count <= 100 and entry_count > 0:
                        # Small playlist — full extract for complete metadata (title, artist, thumbnail)
                        self.log(f"Small playlist ({entry_count} items) — extracting full metadata...")
                        full_opts = {
                            "ignoreerrors": True,
                            "extract_flat": False,
                            "playlist-end": 2000,
                            "format": "bestaudio/best",
                            "quiet": True,
                            "no_warnings": True,
                            "nocheckcertificate": True,
                            "skip_download": True,
                            **cookie_opts,
                        }
                        with yt_dlp.YoutubeDL(full_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if info and "entries" in info:
                                for video in info["entries"]:
                                    if video is None:
                                        continue
                                    if len(all_entries) >= 2000:
                                        break

                                    entry_url = video.get("webpage_url") or video.get("url")
                                    title = video.get("title", "Unknown Title")

                                    if not entry_url:
                                        vid_id = video.get("id", "")
                                        if vid_id:
                                            entry_url = f"https://www.youtube.com/watch?v={vid_id}"
                                        else:
                                            continue

                                    all_entries.append({"url": entry_url, "title": title, "video": video})

                    else:
                        # Large playlist — reuse flat entries from Phase 1 (no second fetch!)
                        for video in flat_entries:
                            if len(all_entries) >= 2000:
                                break

                            entry_url = video.get("url")
                            title = video.get("title", "Unknown Title")

                            # Groovy ie_key handling
                            if video.get("ie_key") == "Youtube":
                                if entry_url and "youtube.com/watch" not in entry_url:
                                    entry_url = f"https://www.youtube.com/watch?v={entry_url}"

                            if not entry_url:
                                vid_id = video.get("id", "")
                                if vid_id:
                                    entry_url = f"https://www.youtube.com/watch?v={vid_id}"
                                else:
                                    continue

                            all_entries.append({"url": entry_url, "title": title, "video": video})

                            if len(all_entries) % 100 == 0:
                                self.log(f"Loaded {len(all_entries)} tracks so far...")

                else:
                    # Single video
                    processed_tracks.append(url)
                    self.log("Single video detected.")
                    # Extract thumbnail from video ID immediately
                    import re as _re
                    yt_match = _re.search(r'[?&]v=([^&]+)', url) or _re.search(r'youtu\.be/([^?&]+)', url)
                    if yt_match:
                        self._queue_thumbnails[url] = f"https://img.youtube.com/vi/{yt_match.group(1)}/mqdefault.jpg"

                if all_entries:
                    self.log(f"Playlist loaded: {len(all_entries)} entries total")

                # Process entries in batches of 100 (can be outside with block)
                if all_entries:
                    batch = []
                    total = 0
                    is_first_batch = True

                    for entry in all_entries:
                        track_url = entry["url"]
                        title = entry["title"]
                        video = entry["video"]
                        uploader = video.get("uploader") or video.get("channel") or ""

                        batch.append(track_url)

                        # Build "Artist - Title" display name
                        if uploader and uploader.endswith(" - Topic"):
                            uploader = uploader[:-8]
                        if title:
                            if uploader and uploader.lower() not in title.lower():
                                self._queue_titles[track_url] = f"{uploader} - {title}"
                            else:
                                self._queue_titles[track_url] = title

                        if len(batch) >= 100:
                            with self._queue_lock:
                                if instant and req_id == self._last_instant_id and is_first_batch:
                                    self.manual_queue = batch + self.manual_queue
                                    is_first_batch = False
                                else:
                                    self.manual_queue.extend(batch)
                            processed_tracks.extend(batch)
                            total += len(batch)
                            self.log(f"Queued {total} tracks so far...")
                            batch = []

                    # Add remaining
                    if batch:
                        with self._queue_lock:
                            if instant and req_id == self._last_instant_id and is_first_batch:
                                self.manual_queue = batch + self.manual_queue
                            else:
                                self.manual_queue.extend(batch)
                        processed_tracks.extend(batch)
                        total += len(batch)

                    self.log(f"Playlist fully loaded: {total} tracks total.")

                    # Background: resolve thumbnails from entry metadata (instant, no API calls)
                    def _resolve_thumbnails(entries_data, station_ref):
                        for entry in entries_data:
                            track_url = entry["url"]
                            video = entry["video"]
                            thumb = video.get("thumbnail") or ""
                            if not thumb:
                                thumbs = video.get("thumbnails")
                                if thumbs and isinstance(thumbs, list):
                                    thumb = thumbs[-1].get("url", "")
                            if not thumb:
                                vid_id = video.get("id", "")
                                if vid_id:
                                    thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
                            if thumb:
                                station_ref._queue_thumbnails[track_url] = thumb

                    threading.Thread(
                        target=_resolve_thumbnails,
                        args=(list(all_entries), self),
                        daemon=True,
                    ).start()

                    # Start background title resolver only for large playlists (flat extract)
                    # Small playlists already have full metadata from non-flat extract
                    if entry_count > 100:
                        threading.Thread(
                            target=self._resolve_titles,
                            args=(list(processed_tracks),),
                            daemon=True,
                        ).start()
                    else:
                        self.log("Full metadata already extracted — skipping background resolve.")

                    return

            except Exception as e:
                self.log(f"URL Error: {str(e)}")
                return

        if not processed_tracks:
            return

        with self._queue_lock:
            if instant and req_id == self._last_instant_id:
                self.manual_queue = processed_tracks + self.manual_queue
                self.skip_requested = True
                if self.feeder:
                    try:
                        self.feeder.kill()
                    except Exception:
                        pass
                self.log(
                    f"Instant Play (URL): {len(processed_tracks)} tracks added."
                )
            else:
                self.manual_queue.extend(processed_tracks)
                self.log(f"Queued (URL): {len(processed_tracks)} tracks added.")

    def _get_spotify_tracks(self, url):
        """Extract track names from a Spotify playlist/album URL via scraping."""
        import requests
        import re

        try:
            target_url = url
            if "playlist" in url:
                target_url = url.replace(
                    "open.spotify.com/playlist/", "open.spotify.com/embed/playlist/"
                )
            elif "album" in url:
                target_url = url.replace(
                    "open.spotify.com/album/", "open.spotify.com/embed/album/"
                )

            response = requests.get(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 RadioGamingWebStreamer/1.0"
                },
                timeout=10,
            )

            # Primary: __NEXT_DATA__
            next_data_match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
                response.text,
            )
            if next_data_match:
                try:
                    data = json.loads(next_data_match.group(1))
                    tracks_data = (
                        data.get("props", {})
                        .get("pageProps", {})
                        .get("state", {})
                        .get("data", {})
                        .get("entity", {})
                        .get("trackList", [])
                    )
                    if not tracks_data:
                        tracks_data = (
                            data.get("props", {})
                            .get("pageProps", {})
                            .get("state", {})
                            .get("data", {})
                            .get("tracks", {})
                            .get("items", [])
                        )

                    if tracks_data:
                        tracks = []
                        for item in tracks_data:
                            t = item.get("track", item)
                            name = t.get("title") or t.get("name")
                            if name:
                                artists_str = ""
                                if "subtitle" in t:
                                    artists_str = t["subtitle"]
                                elif "artists" in t and t["artists"]:
                                    artists_str = ", ".join(
                                        a.get("name", "")
                                        for a in t["artists"]
                                        if a.get("name")
                                    )
                                if artists_str:
                                    tracks.append(f"{name} {artists_str}")
                                else:
                                    tracks.append(name)
                        if tracks:
                            return tracks
                except Exception as e:
                    print(f"Spotify NEXT_DATA parse error: {e}")

            # Fallback: regex
            matches = re.findall(
                r"\"name\":\"([^\"]+?)\",\"artists\":\[\{\"name\":\"([^\"]+?)\"",
                response.text,
            )
            if matches:
                seen = set()
                tracks = []
                for name, artist in matches:
                    clean_name = name.replace("\\u0026", "&").replace("\\u0027", "'")
                    clean_artist = artist.replace("\\u0026", "&").replace("\\u0027", "'")
                    full = f"{clean_name} {clean_artist}"
                    if full not in seen:
                        if not any(
                            x in full.lower()
                            for x in ["spotify", "log in", "sign up", "terms of"]
                        ):
                            tracks.append(full)
                            seen.add(full)
                if tracks:
                    return tracks

        except Exception as e:
            print(f"Spotify Scrape Error: {e}")
        return []


# ─── Global Station Instances ──────────────────────────────────────────────────

stations = {}
for i in range(3):
    stations[i] = WebStreamStation(i)

print("[StreamerApi] Initialized 3 station managers.")


def _apply_startup_configs():
    """Check DB for startup configs and auto-start configured stations."""
    for sid, station in stations.items():
        cfg = _load_startup_config(sid)
        if not cfg:
            continue
        if not cfg.get("auto_connect"):
            continue

        print(f"[Startup] Auto-starting station {sid} ({station.name})...")

        # Apply custom Icecast settings if enabled
        if cfg.get("use_custom_icecast"):
            if cfg.get("icecast_server"):
                STATION_CONFIGS[sid]["server"] = cfg["icecast_server"]
            if cfg.get("icecast_port"):
                STATION_CONFIGS[sid]["port"] = cfg["icecast_port"]
            if cfg.get("icecast_mount"):
                STATION_CONFIGS[sid]["mount"] = cfg["icecast_mount"]
            if cfg.get("icecast_password"):
                STATION_CONFIGS[sid]["password"] = cfg["icecast_password"]
            station.log("Applied custom Icecast settings from startup config.")

        # Set loop mode
        loop = cfg.get("loop_mode", "off")
        if loop in ("off", "single", "queue"):
            station.loop_mode = loop

        # Start the station
        station.start()

        # Load playlist in background if configured
        playlist_url = (cfg.get("playlist_url") or "").strip()
        shuffle = cfg.get("shuffle_enabled", False)
        shuffle_count = cfg.get("shuffle_count", 1) or 1

        if playlist_url:
            def _startup_enqueue(st, url, shuf, shuf_count):
                time.sleep(5)  # Wait for station to connect
                st.log(f"Startup: Loading playlist {url[:60]}...")

                # Call _handle_url_enqueue DIRECTLY (synchronous) so we wait
                # for the playlist to actually be loaded before shuffling
                st._handle_url_enqueue(url, False, 0)

                queue_len = len(st.manual_queue)
                st.log(f"Startup: Queue has {queue_len} items.")

                if shuf and queue_len > 1:
                    for _ in range(shuf_count):
                        st.shuffle_queue()
                    st.log(f"Startup: Shuffled queue {shuf_count}x")

            threading.Thread(
                target=_startup_enqueue,
                args=(station, playlist_url, shuffle, shuffle_count),
                daemon=True,
            ).start()

        time.sleep(2)  # Stagger auto-starts


# Run auto-start in background to not block module loading
# Guard against double execution (e.g. gunicorn preloading)
_startup_done = False
_startup_lock = threading.Lock()


def _guarded_startup():
    global _startup_done
    with _startup_lock:
        if _startup_done:
            return
        _startup_done = True
    time.sleep(3)  # Wait for app to fully initialize
    _apply_startup_configs()


threading.Thread(target=_guarded_startup, daemon=True).start()


# ─── REST API Endpoints ───────────────────────────────────────────────────────


@app.route("/")
def home():
    return jsonify({"service": "Radio GAMING Web Streamer", "status": "online"})


@app.route("/public/status", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def public_status():
    """Public endpoint: returns which stations are actively streaming and their queues.
    No admin auth required — safe for the radio frontend to poll."""
    result = {}
    for sid, station in stations.items():
        with station._queue_lock:
            queue_urls = list(station.manual_queue)
        # Build display titles and thumbnails lists from maps
        queue_display = []
        for url in queue_urls:
            title = station._queue_titles.get(url, url)
            thumb = station._queue_thumbnails.get(url, "")
            queue_display.append({"title": title, "thumbnail": thumb})

        # Current song thumbnail — try matching current playing URL
        current_thumb = ""
        if station.running and station.current_song:
            for url, t in station._queue_titles.items():
                if t == station.current_song:
                    current_thumb = station._queue_thumbnails.get(url, "")
                    break

        result[str(sid)] = {
            "station_id": sid,
            "name": station.name,
            "streaming": station.running and station._established,
            "current_song": station.current_song if station.running else None,
            "current_thumbnail": current_thumb,
            "queue": queue_display,
            "queue_length": len(queue_urls),
            "loop_mode": station.loop_mode,
        }
    return jsonify(result)

@app.route("/status", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_all_status():
    """Get status of all stations + admin presence. Admin only."""
    session, err = get_admin_session()
    if err:
        return err

    # Heartbeat — piggybacks on the existing status poll (no extra fetch needed)
    _admin_heartbeat(session)

    result = {}
    for sid, station in stations.items():
        result[str(sid)] = station.get_status()

    # Bundle admin presence data with status response
    result["_admin_presence"] = _get_admin_presence_data()

    return jsonify(result)


@app.route("/start/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def start_station(station_id):
    """Start streaming on a station."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    station = stations[station_id]
    if station.running:
        return jsonify({"error": "Station already running"}), 400

    station.start()
    _admin_heartbeat(session, f"Start: {station.name}")
    return jsonify({"success": True, "message": f"{station.name} starting..."})


@app.route("/stop/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def stop_station(station_id):
    """Stop streaming on a station."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    station = stations[station_id]
    station.stop()
    _admin_heartbeat(session, f"Stop: {station.name}")
    return jsonify({"success": True, "message": f"{station.name} stopped."})


@app.route("/skip/<int:station_id>", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def skip_song(station_id):
    """Skip current song."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    station_name = STATION_CONFIGS.get(station_id, {}).get("name", f"Station {station_id}")
    _admin_heartbeat(session, f"Skip na {station_name}")
    stations[station_id].skip_song()
    return jsonify({"success": True})


@app.route("/enqueue/<int:station_id>", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def enqueue_song(station_id):
    """Add a URL/search to queue. Body: {url: string, instant?: boolean, custom_name?: string}"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    instant = data.get("instant", False)
    custom_name = data.get("custom_name", "").strip() or None
    stations[station_id].enqueue(url, instant=instant)

    # Log admin action and save to input history DB
    station_name = STATION_CONFIGS.get(station_id, {}).get("name", f"Station {station_id}")
    mode = "Instant" if instant else "Queue"
    _admin_heartbeat(session, f"{mode}: {url[:80]} → {station_name}")
    _save_input_history(station_id, url, session, instant=instant, custom_name=custom_name)

    return jsonify({"success": True, "message": f"Processing: {url}"})


@app.route("/queue/<int:station_id>", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_queue(station_id):
    """Get current queue."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    return jsonify({"queue": stations[station_id].get_queue()})


@app.route("/queue/<int:station_id>/clear", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def clear_queue(station_id):
    """Clear queue."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    stations[station_id].clear_queue()
    return jsonify({"success": True})


@app.route("/queue/<int:station_id>/shuffle", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def shuffle_queue(station_id):
    """Shuffle queue."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    stations[station_id].shuffle_queue()
    return jsonify({"success": True})


@app.route("/queue/<int:station_id>/remove", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def remove_queue_item(station_id):
    """Remove a single item from queue by index. Body: {index: int}"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.get_json(silent=True) or {}
    index = data.get("index")
    if index is None or not isinstance(index, int):
        return jsonify({"error": "Missing index"}), 400

    station = stations[station_id]
    with station._queue_lock:
        if 0 <= index < len(station.manual_queue):
            removed = station.manual_queue.pop(index)
            station.log(f"Removed from queue: {removed[:60]}")
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Index out of range"}), 400


@app.route("/auto-disconnect/<int:station_id>", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def toggle_auto_disconnect(station_id):
    """Toggle auto-disconnect on empty queue. Body: {enabled: boolean}"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}
    enabled = bool(data.get("enabled", False))
    stations[station_id].auto_disconnect_empty = enabled
    state_text = "ON" if enabled else "OFF"
    stations[station_id].log(f"Auto-disconnect on empty: {state_text}")
    _admin_heartbeat(session, f"Auto-disconnect {state_text}: {stations[station_id].name}")
    return jsonify({"success": True, "enabled": enabled})


@app.route("/loop/<int:station_id>", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def set_loop_mode(station_id):
    """Set loop mode. Body: {mode: "off"|"single"|"queue"}"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}
    mode = data.get("mode", "off")
    if mode not in ("off", "single", "queue"):
        return jsonify({"error": "Invalid mode"}), 400

    stations[station_id].toggle_loop(mode)
    return jsonify({"success": True, "mode": mode})


@app.route("/history/<int:station_id>", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_history(station_id):
    """Get history."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    return jsonify({"history": stations[station_id].get_history()})


@app.route("/history/<int:station_id>/clear", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def clear_history(station_id):
    """Clear history."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    stations[station_id].clear_history()
    return jsonify({"success": True})


@app.route("/history/<int:station_id>/restore", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def restore_history(station_id):
    """Restore item from history. Body: {index: int, instant?: boolean}"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}
    index = data.get("index", 0)
    instant = data.get("instant", False)

    success = stations[station_id].restore_from_history(index, instant=instant)
    return jsonify({"success": success})


@app.route("/logs/<int:station_id>", methods=["GET"])
@limiter.limit("60 per minute")
@cross_origin(**CORS_OPTIONS)
def get_logs(station_id):
    """Get log entries for a station. Query: ?since=<index>"""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    since = request.args.get("since", 0, type=int)
    logs = stations[station_id].get_logs(since)
    total = len(stations[station_id]._log_buffer)

    return jsonify({"logs": logs, "total": total})


# ─── Startup Config Endpoints ─────────────────────────────────────────────────


@app.route("/startup/<int:station_id>", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_startup_config(station_id):
    """Get startup config for a station (passwords masked)."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    cfg = _load_startup_config(station_id) or {}

    return jsonify({
        "auto_connect": bool(cfg.get("auto_connect")),
        "use_custom_icecast": bool(cfg.get("use_custom_icecast")),
        "icecast_server": cfg.get("icecast_server", ""),
        "icecast_port": cfg.get("icecast_port", "80"),
        "icecast_mount": cfg.get("icecast_mount", ""),
        "has_password": bool(cfg.get("icecast_password")),
        "playlist_url": cfg.get("playlist_url", "") or "",
        "shuffle_enabled": bool(cfg.get("shuffle_enabled")),
        "shuffle_count": cfg.get("shuffle_count", 1) or 1,
        "loop_mode": cfg.get("loop_mode", "off") or "off",
    })


@app.route("/startup/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def set_startup_config(station_id):
    """Save startup config for a station to DB."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}

    # Load existing to preserve password if not provided
    existing = _load_startup_config(station_id) or {}

    config = {
        "auto_connect": data.get("auto_connect", False),
        "use_custom_icecast": data.get("use_custom_icecast", False),
        "icecast_server": data.get("icecast_server", ""),
        "icecast_port": data.get("icecast_port", "80"),
        "icecast_mount": data.get("icecast_mount", ""),
        "icecast_password": data.get("icecast_password") if data.get("icecast_password") else existing.get("icecast_password", ""),
        "playlist_url": data.get("playlist_url", ""),
        "shuffle_enabled": data.get("shuffle_enabled", False),
        "shuffle_count": data.get("shuffle_count", 1),
        "loop_mode": data.get("loop_mode", "off"),
    }

    _save_startup_config(station_id, config)
    stations[station_id].log("Startup config saved to database.")

    return jsonify({"success": True, "message": "Startup config saved."})


# ─── Station Config Endpoints ─────────────────────────────────────────────────


@app.route("/config/<int:station_id>", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_config(station_id):
    """Get current Icecast config for a station (passwords masked)."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in STATION_CONFIGS:
        return jsonify({"error": "Invalid station ID"}), 400

    cfg = STATION_CONFIGS[station_id]
    return jsonify({
        "server": cfg.get("server", ""),
        "port": cfg.get("port", ""),
        "mount": cfg.get("mount", ""),
        "user": cfg.get("user", "source"),
        "password_set": bool(cfg.get("password", "")),
    })


@app.route("/config/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def set_config(station_id):
    """Update Icecast config for a station at runtime.
    Body: {server?, port?, mount?, user?, password?}
    Only provided fields are updated.
    """
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in STATION_CONFIGS:
        return jsonify({"error": "Invalid station ID"}), 400

    data = request.json or {}
    cfg = STATION_CONFIGS[station_id]

    updated = []
    for key in ("server", "port", "mount", "user", "password"):
        if key in data and data[key] is not None:
            cfg[key] = str(data[key]).strip()
            updated.append(key)

    if not updated:
        return jsonify({"error": "No fields provided"}), 400

    # Log which fields were updated (without exposing password value)
    safe_fields = [f for f in updated if f != "password"]
    if "password" in updated:
        safe_fields.append("password(***)")
    station_name = cfg.get("name", f"Station {station_id}")

    if station_id in stations:
        stations[station_id].log(f"Config updated: {', '.join(safe_fields)}")

    return jsonify({"success": True, "message": f"Updated {', '.join(safe_fields)} for {station_name}"})


@app.route("/cookies", methods=["GET"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def get_cookies_status():
    """Check if cookies.txt is present."""
    session, err = get_admin_session()
    if err:
        return err

    exists = os.path.isfile(COOKIE_FILE_PATH)
    size = os.path.getsize(COOKIE_FILE_PATH) if exists else 0
    return jsonify({
        "has_cookies": exists,
        "file_size": size,
    })


@app.route("/cookies", methods=["POST"])
@limiter.limit("5 per minute")
@cross_origin(**CORS_OPTIONS)
def upload_cookies():
    """Upload cookies.txt file for YouTube authentication.
    Accepts multipart/form-data with a 'file' field,
    or raw text body with Content-Type text/plain.
    """
    session, err = get_admin_session()
    if err:
        return err

    cookie_data = None

    # Try multipart file upload first
    if "file" in request.files:
        f = request.files["file"]
        cookie_data = f.read()
    else:
        # Try raw body (text/plain or application/octet-stream)
        cookie_data = request.get_data()

    if not cookie_data or len(cookie_data) < 10:
        return jsonify({"error": "No valid cookie data received"}), 400

    # Validate it looks like a Netscape cookies file
    text = cookie_data.decode("utf-8", errors="replace")
    if not ("# Netscape HTTP Cookie File" in text or "\t" in text[:500]):
        return jsonify({"error": "Invalid cookies.txt format. Use Netscape/Mozilla format."}), 400

    try:
        with open(COOKIE_FILE_PATH, "wb") as f:
            f.write(cookie_data)

        size = os.path.getsize(COOKIE_FILE_PATH)

        # Persist to database so it survives dyno restarts
        _save_cookies_to_db(text)

        # Log to all running stations
        for sid, station in stations.items():
            station.log(f"Cookies.txt updated ({size} bytes) — saved to DB")

        return jsonify({
            "success": True,
            "message": f"Cookies.txt saved ({size} bytes) and persisted to database.",
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save cookies: {str(e)}"}), 500


@app.route("/cookies", methods=["DELETE"])
@limiter.limit("5 per minute")
@cross_origin(**CORS_OPTIONS)
def delete_cookies():
    """Remove cookies.txt."""
    session, err = get_admin_session()
    if err:
        return err

    if os.path.isfile(COOKIE_FILE_PATH):
        os.remove(COOKIE_FILE_PATH)
        _delete_cookies_from_db()
        for sid, station in stations.items():
            station.log("Cookies.txt removed from file and database.")
        return jsonify({"success": True, "message": "Cookies.txt deleted from file and database."})

    return jsonify({"error": "No cookies.txt to delete"}), 404

# ─── Microphone Endpoints ─────────────────────────────────────────────────────


@app.route("/mic/start/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def mic_start(station_id):
    """Enable microphone broadcasting on a station."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    station = stations[station_id]
    if not station.running:
        return jsonify({"error": "Station must be running to use mic"}), 400

    station.set_mic(True)
    return jsonify({"success": True, "message": f"Mic ON for {station.name}"})


@app.route("/mic/stop/<int:station_id>", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def mic_stop(station_id):
    """Disable microphone broadcasting."""
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    stations[station_id].set_mic(False)
    return jsonify({"success": True})


@app.route("/mic/data/<int:station_id>", methods=["POST"])
@limiter.limit("600 per minute")
@cross_origin(**CORS_OPTIONS)
def mic_data(station_id):
    """Receive raw PCM audio data from browser mic.
    Expected: binary body of s16le, 44100Hz, 2ch PCM data.
    Called ~5 times/sec with ~200ms of audio per chunk.
    """
    session, err = get_admin_session()
    if err:
        return err

    if station_id not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    station = stations[station_id]
    if not station.mic_active:
        return jsonify({"error": "Mic not active"}), 400

    pcm_data = request.get_data()
    if not pcm_data:
        return jsonify({"error": "No audio data"}), 400

    station.feed_mic_data(pcm_data)
    return jsonify({"success": True}), 200


# ─── Global Controls ──────────────────────────────────────────────────────────


@app.route("/start-all", methods=["POST"])
@limiter.limit("5 per minute")
@cross_origin(**CORS_OPTIONS)
def start_all():
    """Start all stations."""
    session, err = get_admin_session()
    if err:
        return err

    for sid, station in stations.items():
        if not station.running:
            station.start()
            time.sleep(2)  # Stagger starts

    return jsonify({"success": True, "message": "All stations starting..."})


@app.route("/stop-all", methods=["POST"])
@limiter.limit("5 per minute")
@cross_origin(**CORS_OPTIONS)
def stop_all():
    """Stop all stations."""
    session, err = get_admin_session()
    if err:
        return err

    for sid, station in stations.items():
        station.stop()

    return jsonify({"success": True, "message": "All stations stopped."})


# ─── Input History Endpoints ──────────────────────────────────────────────────


@app.route("/input-history", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_input_history():
    """Get input history. Query: ?station=<id>&limit=<n>&offset=<n>"""
    session, err = get_admin_session()
    if err:
        return err

    station_id = request.args.get("station", None, type=int)
    limit = min(request.args.get("limit", 50, type=int), 200)
    offset = request.args.get("offset", 0, type=int)

    history = _get_input_history(station_id=station_id, limit=limit, offset=offset)
    return jsonify({"history": history})


@app.route("/input-history/<int:entry_id>/name", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def update_input_name(entry_id):
    """Update custom_name for an input history entry. Body: {custom_name: string}"""
    session, err = get_admin_session()
    if err:
        return err

    data = request.json or {}
    custom_name = data.get("custom_name", "").strip()

    success = _update_input_custom_name(entry_id, custom_name if custom_name else None)
    if success:
        _admin_heartbeat(session, f"Renamed input #{entry_id}: {custom_name[:40]}")
        return jsonify({"success": True})
    return jsonify({"error": "Update failed"}), 500


@app.route("/input-history/<int:entry_id>/replay", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def replay_input(entry_id):
    """Re-enqueue an input from history. Body: {station_id: int, instant?: boolean}"""
    session, err = get_admin_session()
    if err:
        return err

    data = request.json or {}
    target_station = data.get("station_id", 0)
    instant = data.get("instant", False)

    if target_station not in stations:
        return jsonify({"error": "Invalid station ID"}), 400

    # Load the entry from DB
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT url FROM streamer_input_history WHERE id = %s", (entry_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Entry not found"}), 404

        url = row["url"]
        stations[target_station].enqueue(url, instant=instant)
        station_name = STATION_CONFIGS.get(target_station, {}).get("name", f"Station {target_station}")
        _admin_heartbeat(session, f"Replay #{entry_id} → {station_name}")
        return jsonify({"success": True, "message": f"Re-enqueued to {station_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_api():
    port = int(os.environ.get("PORT", 80))
    print(f"[StreamerApi] Starting on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
