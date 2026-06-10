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


# RADIO_ADMIN_USER_IDS imported from api.config (centralized)


def is_admin(user_id):
    return str(user_id) in RADIO_ADMIN_USER_IDS


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
        return {
            "station_id": self.station_id,
            "name": self.name,
            "running": self.running,
            "established": self._established,
            "current_song": self.current_song,
            "loop_mode": self.loop_mode,
            "mic_active": self.mic_active,
            "queue": queue_list,
            "queue_length": len(queue_list),
            "queue_titles": dict(self._queue_titles),
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

                            # Clean filename — avoid duplicate artist
                            if uploader.lower() not in title.lower():
                                clean_name = f"{uploader} - {title}"
                            else:
                                clean_name = title
                            for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                                clean_name = clean_name.replace(ch, '_')
                            local_dest = os.path.join(self.preload_dir, f"{clean_name[:120]}.mp3")

                            # Update queue title with full artist info for frontend display & cover search
                            if uploader.lower() not in title.lower():
                                self._queue_titles[path] = f"{uploader} - {title}"
                            else:
                                self._queue_titles[path] = title

                        if os.path.exists(local_dest):
                            with self._preload_lock:
                                self._preload_cache[path] = local_dest
                            continue

                        ydl_opts = {
                            "format": "bestaudio/best",
                            "outtmpl": local_dest.replace(".mp3", ".%(ext)s"),
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

                    time.sleep(1)  # Gap between downloads

            except Exception:
                time.sleep(5)
            time.sleep(5)  # Periodic check

    def _resolve_titles(self, urls):
        """Background: resolve proper 'Artist - Title' for queue items missing artist info."""
        import yt_dlp

        resolved = 0
        for url in urls:
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

                    resolved += 1
                    if resolved % 20 == 0:
                        self.log(f"Resolved titles: {resolved}/{len(urls)}")

            except Exception:
                pass

            time.sleep(0.5)  # Rate limit

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

    def _update_metadata(self, title, delay=0):
        """Send HTTP GET to Icecast admin API to update song metadata."""
        if not self.running:
            return

        def task():
            if delay > 0:
                time.sleep(delay)
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
                with urllib.request.urlopen(req, timeout=10) as response:
                    pass
            except Exception as e:
                print(f"[{self.name}] Metadata update error: {e}")

        threading.Thread(target=task, daemon=True).start()

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
        """Maintain stream when queue is empty: silence to keep connection alive."""
        self.log("Queue empty. Entering idle mode...")
        self.current_song = "RADIO GAMING Live/Idle"
        self._update_metadata("RADIO GAMING Live/Idle", delay=1)

        bytes_per_sec = 44100 * 2 * 2
        start_time = time.time()

        if self._conn_start_time is None:
            self._conn_start_time = time.time()
            self._conn_bytes_sent = 0

        while self.running and (time.time() - start_time < 4):
            with self._queue_lock:
                if self.manual_queue:
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
                    "128k",
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
                        bufsize=128 * 1024,
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

                if not file_path:
                    self._handle_no_media()
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
                        self.log(f"Fetching stream: {file_path}")
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

                            play_path = info.get("url")
                            if (
                                not play_path
                                and "formats" in info
                                and info["formats"]
                            ):
                                play_path = info["formats"][-1].get("url")

                            if not play_path:
                                raise Exception("No playable URL found.")

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
                        except Exception as e:
                            self.log(f"Stream expansion failed: {e}")
                            self._feed_silence(2.0)
                            break
                    else:
                        play_path = file_path
                        clean_title = os.path.basename(file_path).rsplit(".", 1)[0]
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

                        feeder_queue_local = queue.Queue(maxsize=5)

                        def feeder_worker(proc, q):
                            while self.running and proc.poll() is None:
                                try:
                                    c = proc.stdout.read(32768)
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
                                chunk = feeder_queue_local.get(timeout=0.01)
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

                            # Realtime throttle
                            expected_elapsed = (
                                self._conn_bytes_sent / bytes_per_sec
                            ) - 0.5
                            actual_elapsed = time.time() - self._conn_start_time
                            sleep_time = expected_elapsed - actual_elapsed
                            if sleep_time > 0.01:
                                time.sleep(min(sleep_time, 0.2))
                            elif sleep_time < -5.0:
                                self._conn_start_time = time.time()
                                self._conn_bytes_sent = 0
                            else:
                                time.sleep(0.005)

                        # Finalize
                        try:
                            self.transmitter.stdin.flush()
                        except Exception:
                            pass
                        try:
                            self.feeder.kill()
                        except Exception:
                            pass

                        self._feed_silence(0.5)

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

        # Convert YouTube Music URLs to regular YouTube for better playlist support
        if "music.youtube.com" in url:
            url = url.replace("music.youtube.com", "www.youtube.com")
            self.log("Converted YouTube Music URL to standard YouTube.")

        # Strip tracking parameters
        if "&si=" in url:
            url = url.split("&si=")[0]

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
                import yt_dlp

                ydl_opts = {
                    "extract_flat": "in_playlist",
                    "skip_download": True,
                    "quiet": True,
                    "no_warnings": True,
                    "nocheckcertificate": True,
                    "ignoreerrors": True,
                    **get_cookie_opts(),
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    if "entries" in info:
                        # Iterate the lazy generator properly for large playlists
                        self.log("Loading playlist entries...")
                        count = 0
                        batch = []

                        for entry in info["entries"]:
                            if not entry:
                                continue
                            track_url = entry.get("url") or entry.get("webpage_url")
                            if not track_url:
                                vid_id = entry.get("id")
                                if vid_id:
                                    track_url = f"https://www.youtube.com/watch?v={vid_id}"
                                else:
                                    continue
                            batch.append(track_url)
                            count += 1

                            # Save title for frontend display
                            entry_title = entry.get("title")
                            if entry_title:
                                uploader = entry.get("uploader") or entry.get("channel") or ""
                                if uploader and uploader.endswith(" - Topic"):
                                    uploader = uploader[:-8]
                                if uploader and uploader.lower() not in entry_title.lower():
                                    self._queue_titles[track_url] = f"{uploader} - {entry_title}"
                                else:
                                    self._queue_titles[track_url] = entry_title

                            # Every 100 tracks, add to queue immediately so playback can start
                            if len(batch) >= 100:
                                with self._queue_lock:
                                    if instant and req_id == self._last_instant_id and count <= 100:
                                        self.manual_queue = batch + self.manual_queue
                                    else:
                                        self.manual_queue.extend(batch)
                                self.log(f"Loaded {count} tracks so far...")
                                processed_tracks.extend(batch)
                                batch = []

                        # Add remaining batch
                        if batch:
                            with self._queue_lock:
                                if instant and req_id == self._last_instant_id and count <= len(batch):
                                    self.manual_queue = batch + self.manual_queue
                                else:
                                    self.manual_queue.extend(batch)
                            processed_tracks.extend(batch)

                        self.log(f"Playlist fully loaded: {count} tracks total.")

                        # Start background title resolver for items without artist info
                        threading.Thread(
                            target=self._resolve_titles,
                            args=(list(processed_tracks),),
                            daemon=True,
                        ).start()

                        # Skip the normal queue append below since we already added in batches
                        return
                    else:
                        processed_tracks.append(url)

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


# ─── REST API Endpoints ───────────────────────────────────────────────────────


@app.route("/")
def home():
    return jsonify({"service": "Radio GAMING Web Streamer", "status": "online"})


@app.route("/status", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_all_status():
    """Get status of all stations. Admin only."""
    session, err = get_admin_session()
    if err:
        return err

    result = {}
    for sid, station in stations.items():
        result[str(sid)] = station.get_status()

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

    stations[station_id].skip_song()
    return jsonify({"success": True})


@app.route("/enqueue/<int:station_id>", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def enqueue_song(station_id):
    """Add a URL/search to queue. Body: {url: string, instant?: boolean}"""
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
    stations[station_id].enqueue(url, instant=instant)
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


def run_api():
    port = int(os.environ.get("PORT", 80))
    print(f"[StreamerApi] Starting on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
