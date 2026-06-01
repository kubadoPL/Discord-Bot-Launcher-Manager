import os
import sys
import secrets
import re
import threading
import queue
from datetime import datetime, timedelta

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from flask import Flask, request, jsonify, redirect, Blueprint
from flask_cors import cross_origin
import requests as http_requests
import json
from api.config import RESTRICT_CORS
from api.FunctionsModule import get_db_connection, create_chat_tables

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# CORS options for all API routes
if RESTRICT_CORS:
    CORS_OPTIONS = {
        "origins": ["https://radio-gaming.stream", "https://k5studio.dev"],
        "allow_headers": ["Authorization", "Content-Type", "X-Playing-Station"],
        "methods": ["GET", "POST", "OPTIONS"],
    }
else:
    CORS_OPTIONS = {
        "origins": "*",
        "allow_headers": ["Authorization", "Content-Type", "X-Playing-Station"],
        "methods": ["GET", "POST", "OPTIONS"],
    }

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB max request size

chat_api = Blueprint("chat_api", __name__)

# Discord OAuth2 Configuration
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.environ.get(
    "DISCORD_REDIRECT_URI",
)
DISCORD_API_URL = "https://discord.com/api/v10"

# In-memory storage (loaded from DB on startup)
user_sessions = {}
chat_messages = {"RADIOGAMING": [], "RADIOGAMINGDARK": [], "RADIOGAMINGMARONFM": []}
user_profiles = {}  # user_id -> profile_data (safe subset)
user_last_station = {}  # user_id -> station_key
online_users = {}  # station_key -> {user_id -> last_activity_timestamp}
MAX_MESSAGES_PER_CHANNEL = 100
SAVE_EMOJIS = True  # Set to True to persist custom emojis in the database
message_cooldowns = {}
MESSAGE_COOLDOWN_SECONDS = 2
ONLINE_THRESHOLD_SECONDS = 60
OFFLINE_THRESHOLD_SECONDS = 86400  # 24 hours
all_user_activity = {}  # user_id -> last_activity_timestamp (global)
custom_emojis = []  # List of {id, name, url, creator_id}
anonymous_listeners = {}  # station_key -> {anon_id -> last_activity_timestamp}

# Cache for online users results to reduce CPU load
online_users_cache = (
    {}
)  # station_key -> {"count": int, "users": list, "timestamp": datetime}
CACHE_TTL_SECONDS = 10
_last_seen_db_writes = {}  # user_id -> last DB write datetime (debounce)


# ─── DB Write Queue (background thread) ───────────────────────────────────────

_db_write_queue = queue.Queue()


def _db_worker():
    """Background thread that processes all DB write operations."""
    while True:
        task = _db_write_queue.get()
        if task is None:
            break
        func, args, kwargs = task
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"[DB Worker] Error executing {func.__name__}: {e}")
        finally:
            _db_write_queue.task_done()


_db_thread = threading.Thread(target=_db_worker, daemon=True, name="db-write-worker")
_db_thread.start()


def _db_enqueue(func, *args, **kwargs):
    """Enqueue a DB write operation to be processed in the background thread."""
    _db_write_queue.put((func, args, kwargs))


# ─── DB Persistence Helpers (executed by the worker thread) ────────────────

def _do_save_message(msg_obj):
    """Save or update a single chat message in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_messages (id, station, user_id, content, image_data, song_data, reactions, reaction_users, timestamp, last_update)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            content = VALUES(content),
            reactions = VALUES(reactions),
            reaction_users = VALUES(reaction_users),
            last_update = VALUES(last_update)
        """,
        (
            msg_obj["id"],
            msg_obj["station"],
            msg_obj["user"]["id"],
            msg_obj.get("content"),
            msg_obj.get("image_data"),
            json.dumps(msg_obj.get("song_data")),
            json.dumps(msg_obj.get("reactions", {})),
            json.dumps(msg_obj.get("reaction_users", {})),
            msg_obj["timestamp"].replace("Z", ""),
            msg_obj["last_update"].replace("Z", ""),
        ),
    )
    conn.commit()

    # Cleanup: keep only the newest MAX_MESSAGES_PER_CHANNEL messages globally (all stations)
    cursor.execute(
        """
        DELETE FROM chat_messages
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id FROM chat_messages
                ORDER BY timestamp DESC
                LIMIT %s
            ) AS keep
        )
        """,
        (MAX_MESSAGES_PER_CHANNEL,),
    )
    if cursor.rowcount > 0:
        conn.commit()
        print(f"[DB] Cleaned up {cursor.rowcount} old messages globally")

    conn.close()


def _do_delete_message(msg_id):
    """Delete a single chat message from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE id = %s", (msg_id,))
    conn.commit()
    conn.close()


def _do_save_emoji(emoji_obj):
    """Save a custom emoji to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_custom_emojis (id, name, url, creator_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name), url = VALUES(url)
        """,
        (emoji_obj["id"], emoji_obj["name"], emoji_obj["url"], emoji_obj["creator_id"]),
    )
    conn.commit()
    conn.close()


def _do_delete_emoji(emoji_id):
    """Delete a custom emoji from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_custom_emojis WHERE id = %s", (emoji_id,))
    conn.commit()
    conn.close()


def _do_save_profile(profile):
    """Save or update a user profile in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    accent = profile.get("accent_color")
    cursor.execute(
        """
        INSERT INTO chat_user_profiles (user_id, username, global_name, avatar_url, banner_url, accent_color)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            global_name = VALUES(global_name),
            avatar_url = VALUES(avatar_url),
            banner_url = VALUES(banner_url),
            accent_color = VALUES(accent_color)
        """,
        (
            profile["id"],
            profile["username"],
            profile.get("global_name"),
            profile.get("avatar_url"),
            profile.get("banner_url"),
            int(accent) if accent is not None else None,
        ),
    )
    conn.commit()
    conn.close()


def _do_update_last_seen(user_id, last_seen_at, last_station):
    """Update user's last_seen_at and last_station in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE chat_user_profiles
        SET last_seen_at = %s, last_station = %s
        WHERE user_id = %s
        """,
        (last_seen_at, last_station, user_id),
    )
    conn.commit()
    conn.close()


def _db_update_last_seen(user_id, last_seen_at, last_station):
    _db_enqueue(_do_update_last_seen, user_id, last_seen_at, last_station)


def _do_save_session(session_token, session_data):
    """Save or update a user session in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    expires_at = session_data["expires_at"].replace("Z", "")
    cursor.execute(
        """
        INSERT INTO chat_user_sessions (session_token, user_id, discord_access_token, expires_at, via_activity)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            discord_access_token = VALUES(discord_access_token),
            expires_at = VALUES(expires_at)
        """,
        (
            session_token,
            session_data["id"],
            session_data.get("discord_access_token"),
            expires_at,
            1 if session_data.get("via_activity") else 0,
        ),
    )
    conn.commit()
    conn.close()


def _do_delete_session(session_token):
    """Delete a session from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_user_sessions WHERE session_token = %s", (session_token,))
    conn.commit()
    conn.close()


# --- Public API (enqueue wrappers) ---

def _db_save_message(msg_obj):
    _db_enqueue(_do_save_message, msg_obj)

def _db_delete_message(msg_id):
    _db_enqueue(_do_delete_message, msg_id)

def _db_save_emoji(emoji_obj):
    _db_enqueue(_do_save_emoji, emoji_obj)

def _db_delete_emoji(emoji_id):
    _db_enqueue(_do_delete_emoji, emoji_id)

def _db_save_profile(profile):
    _db_enqueue(_do_save_profile, profile)

def _db_save_session(session_token, session_data):
    _db_enqueue(_do_save_session, session_token, session_data)

def _db_delete_session(session_token):
    _db_enqueue(_do_delete_session, session_token)


def _db_delete_expired_sessions():
    """Remove expired sessions from the database (runs synchronously at startup)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_user_sessions WHERE expires_at < NOW()")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            print(f"[DB] Cleaned up {deleted} expired sessions")
    except Exception as e:
        print(f"[DB] Error cleaning sessions: {e}")


def _load_chat_data_from_db():
    """Load chat messages, custom emojis, user profiles, and sessions from the database."""
    global chat_messages, custom_emojis, user_profiles, user_sessions

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Load user profiles first (needed to reconstruct message user objects)
        cursor.execute("SELECT * FROM chat_user_profiles")
        for row in cursor.fetchall():
            user_profiles[row["user_id"]] = {
                "id": row["user_id"],
                "username": row["username"],
                "global_name": row.get("global_name") or row["username"],
                "avatar_url": row.get("avatar_url"),
                "banner_url": row.get("banner_url"),
                "accent_color": row.get("accent_color"),
            }
        print(f"[DB] Loaded {len(user_profiles)} user profiles")

        # Load custom emojis (only if persistence is enabled)
        if SAVE_EMOJIS:
            cursor.execute("SELECT * FROM chat_custom_emojis ORDER BY created_at ASC")
            custom_emojis.clear()
            for row in cursor.fetchall():
                custom_emojis.append({
                    "id": row["id"],
                    "name": row["name"],
                    "url": row["url"],
                    "creator_id": row["creator_id"],
                })
            print(f"[DB] Loaded {len(custom_emojis)} custom emojis")
        else:
            print("[DB] Emoji persistence disabled (SAVE_EMOJIS = False)")

        # Load messages (last MAX_MESSAGES_PER_CHANNEL per station)
        for station_key in chat_messages:
            cursor.execute(
                """
                SELECT * FROM chat_messages
                WHERE station = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (station_key, MAX_MESSAGES_PER_CHANNEL),
            )
            rows = cursor.fetchall()
            rows.reverse()  # oldest first

            msgs = []
            for row in rows:
                user_id = row["user_id"]
                user_data = user_profiles.get(user_id, {
                    "id": user_id,
                    "username": "Unknown",
                    "global_name": "Unknown",
                    "avatar_url": None,
                    "banner_url": None,
                    "accent_color": None,
                })

                # Parse JSON fields
                reactions = row.get("reactions")
                if isinstance(reactions, str):
                    reactions = json.loads(reactions) if reactions else {}
                elif reactions is None:
                    reactions = {}

                reaction_users = row.get("reaction_users")
                if isinstance(reaction_users, str):
                    reaction_users = json.loads(reaction_users) if reaction_users else {}
                elif reaction_users is None:
                    reaction_users = {}

                song_data = row.get("song_data")
                if isinstance(song_data, str):
                    song_data = json.loads(song_data) if song_data else None

                msgs.append({
                    "id": row["id"],
                    "user": user_data,
                    "content": row.get("content", ""),
                    "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["timestamp"] else "",
                    "last_update": row["last_update"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["last_update"] else "",
                    "station": row["station"],
                    "song_data": song_data,
                    "image_data": row.get("image_data"),
                    "reactions": reactions,
                    "reaction_users": reaction_users,
                })

            chat_messages[station_key] = msgs
            print(f"[DB] Loaded {len(msgs)} messages for {station_key}")

        conn.close()
        print("[DB] Chat data loaded successfully from database.")

        # Load user sessions (non-expired only)
        _db_delete_expired_sessions()
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM chat_user_sessions WHERE expires_at > NOW()")
            session_count = 0
            for row in cursor.fetchall():
                user_id = row["user_id"]
                profile = user_profiles.get(user_id)
                if profile:
                    user_sessions[row["session_token"]] = {
                        **profile,
                        "discord_access_token": row.get("discord_access_token"),
                        "expires_at": row["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["expires_at"] else "",
                        "via_activity": bool(row.get("via_activity", 0)),
                    }
                    session_count += 1
            conn.close()
            print(f"[DB] Loaded {session_count} active user sessions")
        except Exception as e:
            print(f"[DB] Error loading sessions: {e}")

        # Load last_seen_at for all users (restores "last seen X ago" after restart)
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT user_id, last_seen_at, last_station FROM chat_user_profiles WHERE last_seen_at IS NOT NULL"
            )
            seen_count = 0
            for row in cursor.fetchall():
                uid = row["user_id"]
                all_user_activity[uid] = row["last_seen_at"]
                if row.get("last_station"):
                    user_last_station[uid] = row["last_station"]
                seen_count += 1
            conn.close()
            print(f"[DB] Loaded last_seen_at for {seen_count} users")

            # Rebuild online_users from loaded data so get_online_data() can find them
            rebuilt = 0
            for uid, last_ts in all_user_activity.items():
                station = user_last_station.get(uid)
                if station and uid in user_profiles:
                    station_key = station.upper().replace("-", "").replace(" ", "")
                    if station_key not in online_users:
                        online_users[station_key] = {}
                    online_users[station_key][uid] = last_ts
                    rebuilt += 1
            print(f"[DB] Rebuilt online_users for {rebuilt} users")
        except Exception as e:
            print(f"[DB] Error loading last_seen: {e}")

    except Exception as e:
        print(f"[DB] Error loading chat data: {e}")
        print("[DB] Starting with empty in-memory chat data.")


# Create tables and load data on startup (in background to avoid blocking gunicorn)
def _init_chat_db():
    try:
        create_chat_tables()
        _load_chat_data_from_db()
    except Exception as e:
        print(f"[DB] Error during startup init: {e}")

threading.Thread(target=_init_chat_db, daemon=True, name="chat-db-init").start()

# Station display names mapping
STATION_NAMES = {
    "RADIOGAMING": "Radio GAMING",
    "RADIOGAMINGDARK": "Radio GAMING DARK",
    "RADIOGAMINGMARONFM": "Radio GAMING MARON FM",
}

# --- CUSTOM EMOJIS ENDPOINTS ---


@chat_api.route("/chat/emojis", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def get_custom_emojis():
    return jsonify(custom_emojis)


@chat_api.route("/chat/emojis/upload", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def upload_custom_emoji():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    data = request.json
    name = data.get("name", "custom").strip()[:20]
    image_data = data.get("image_data")

    if not image_data or not image_data.startswith("data:image/"):
        return jsonify({"error": "Invalid image"}), 400

    # Max 200KB for emojis
    if len(image_data) > 300 * 1024:
        return jsonify({"error": "Emoji too large (max 200KB)"}), 400

    user = user_sessions[token]
    emoji_id = f"custom_{secrets.token_hex(4)}"
    new_emoji = {
        "id": emoji_id,
        "name": name,
        "url": image_data,
        "creator_id": user["id"],
    }

    custom_emojis.append(new_emoji)
    if SAVE_EMOJIS:
        _db_save_emoji(new_emoji)
    # Keep only last 50 custom emojis
    if len(custom_emojis) > 50:
        removed = custom_emojis.pop(0)
        if SAVE_EMOJIS:
            _db_delete_emoji(removed["id"])

    return jsonify({"success": True, "emoji": new_emoji})


def normalize_station(name):
    if not name:
        return ""
    return name.upper().replace("-", "").replace(" ", "")


def safe_parse_datetime(dt_str):
    """Safely parse ISO datetime strings, handling 'Z' suffix."""
    if not dt_str:
        return datetime.min
    try:
        # Handle 'Z' by replacing with '+00:00' for older Python versions
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return datetime.min


def update_user_activity(user_id, station_key, playing_station=None):
    now = datetime.utcnow()
    if station_key not in online_users:
        online_users[station_key] = {}
    online_users[station_key][user_id] = now
    all_user_activity[user_id] = now
    final_station = playing_station if playing_station else station_key
    user_last_station[user_id] = final_station

    # Persist to DB (debounced: only write every 60 seconds per user)
    last_db_write = _last_seen_db_writes.get(user_id)
    if last_db_write is None or (now - last_db_write).total_seconds() >= 60:
        _last_seen_db_writes[user_id] = now
        _db_update_last_seen(user_id, now.strftime("%Y-%m-%d %H:%M:%S"), final_station)


def get_online_data(station_key):
    now = datetime.utcnow()

    # Check cache
    if station_key in online_users_cache:
        cache_entry = online_users_cache[station_key]
        if (now - cache_entry["timestamp"]).total_seconds() < CACHE_TTL_SECONDS:
            return cache_entry["count"], cache_entry["users"]

    # Get all users who ever listened to this station (within 24h)
    uids_for_station = []
    if station_key in online_users:
        uids_for_station = [
            uid
            for uid, ts in online_users[station_key].items()
            if (now - ts).total_seconds() < OFFLINE_THRESHOLD_SECONDS
        ]
        # Clean up very old entries from the dict
        online_users[station_key] = {
            uid: online_users[station_key][uid] for uid in uids_for_station
        }

    # Generate results
    results = []
    online_count = 0
    for uid in uids_for_station:
        if uid in user_profiles:
            last_ts = online_users[station_key][uid]
            diff = (now - last_ts).total_seconds()

            # Valid global activity check
            is_globally_active = diff < ONLINE_THRESHOLD_SECONDS

            # Check if this user is actually listening to THIS station
            user_playing = user_last_station.get(uid, "")
            is_listening_to_this = normalize_station(user_playing) == station_key

            is_online = is_globally_active and is_listening_to_this
            if is_online:
                online_count += 1

            p = user_profiles[uid].copy()
            station_val = user_last_station.get(uid, "Radio GAMING")
            p["current_station"] = STATION_NAMES.get(station_val, station_val)
            p["last_seen"] = last_ts.isoformat() + "Z"
            p["is_online"] = is_online
            p["is_anonymous"] = False
            results.append(p)

    # Sort: Online first, then by last seen
    results.sort(key=lambda x: (x["is_online"], x["last_seen"]), reverse=True)

    # Count anonymous listeners for this station and add to results
    anon_count = 0
    if station_key in anonymous_listeners:
        # Clean up expired anonymous listeners and count active ones
        active_anons = {}
        for anon_id, ts in anonymous_listeners[station_key].items():
            if (now - ts).total_seconds() < ONLINE_THRESHOLD_SECONDS:
                anon_count += 1
                active_anons[anon_id] = ts
                results.append(
                    {
                        "id": anon_id,
                        "username": "Anonymous Listener",
                        "global_name": "Anonymous Listener",
                        "avatar_url": "https://radio-gaming.stream/Images/Logos/Radio%20Gaming%20Logo%20with%20miodzix%20planet.png",
                        "banner_url": "https://radio-gaming.stream/Images/Logos/Radio%20Gaming%20Logo%20with%20miodzix%20planet.png",
                        "accent_color": "#7300ff",
                        "current_station": STATION_NAMES.get(station_key, station_key),
                        "last_seen": ts.isoformat() + "Z",
                        "is_online": True,
                        "is_anonymous": True,
                    }
                )
        anonymous_listeners[station_key] = active_anons

    total_online = online_count + anon_count

    # Re-sort with anonymous users included
    results.sort(key=lambda x: (x["is_online"], x["last_seen"]), reverse=True)

    # Store in cache
    online_users_cache[station_key] = {
        "count": total_online,
        "users": results,
        "timestamp": now,
    }

    return total_online, results


def get_online_users_list(station_key):
    count, users = get_online_data(station_key)
    return users


def get_online_count(station_key):
    count, users = get_online_data(station_key)
    return count


@chat_api.route("/")
def home():
    return jsonify({"service": "Discord Auth & Chat API", "status": "online"})


@chat_api.route("/discord/login")
@cross_origin(**CORS_OPTIONS)
def discord_login():
    if not DISCORD_CLIENT_ID:
        return jsonify({"error": "Discord OAuth not configured"}), 500
    state = secrets.token_urlsafe(32)
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
        f"&state={state}"
    )
    return jsonify({"oauth_url": oauth_url})


@chat_api.route("/discord/callback")
@cross_origin(**CORS_OPTIONS)
def discord_callback():
    code = request.args.get("code")
    frontend_url = os.environ.get(
        "FRONTEND_URL", "http://127.0.0.1:5500/WebAPP/index.html"
    )
    if not code:
        return redirect(f"{frontend_url}?auth_error=no_code")

    try:
        token_response = http_requests.post(
            f"{DISCORD_API_URL}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_json = token_response.json()
        if "access_token" not in token_json:
            return redirect(f"{frontend_url}?auth_error=token_exchange_failed")

        user_response = http_requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {token_json['access_token']}"},
        )
        user_data = user_response.json()

        session_token = secrets.token_urlsafe(64)
        avatar = user_data.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user_data['id']}/{avatar}.png"
            if avatar
            else f"https://cdn.discordapp.com/embed/avatars/{int(user_data.get('discriminator', 0)) % 5}.png"
        )

        profile = {
            "id": user_data["id"],
            "username": user_data["username"],
            "global_name": user_data.get("global_name", user_data["username"]),
            "avatar_url": avatar_url,
            "banner_url": (
                f"https://cdn.discordapp.com/banners/{user_data['id']}/{user_data['banner']}.png?size=600"
                if user_data.get("banner")
                else None
            ),
            "accent_color": user_data.get("accent_color"),
        }

        # Store safe profile for common use
        user_profiles[user_data["id"]] = profile
        _db_save_profile(profile)

        user_sessions[session_token] = {
            **profile,
            "discord_access_token": token_json["access_token"],
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
        }
        _db_save_session(session_token, user_sessions[session_token])
        return redirect(f"{frontend_url}?auth_token={session_token}")
    except Exception as e:
        return redirect(f"{frontend_url}?auth_error=server_error")


@chat_api.route("/discord/user")
@cross_origin(**CORS_OPTIONS)
def get_user():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    return jsonify({"authenticated": True, "user": user_sessions[token]})


@chat_api.route("/discord/logout", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def discord_logout():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]

    # Remove session from memory
    if token in user_sessions:
        del user_sessions[token]

    # Remove session from database (async via worker thread)
    _db_delete_session(token)

    return jsonify({"success": True, "message": "Logged out"})


@chat_api.route("/discord/check-guild/<guild_id>")
@cross_origin(**CORS_OPTIONS)
def check_guild(guild_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    session = user_sessions[token]

    # Use session cache if available and not expired (5 min cache)
    now = datetime.utcnow()
    guilds_cache = session.get("guilds_cache")
    if guilds_cache and guilds_cache.get("expires_at") > now:
        guilds = guilds_cache.get("guilds", [])
    else:
        discord_token = session.get("discord_access_token")
        if not discord_token:
            return jsonify({"in_guild": False, "error": "No Discord token"}), 200

        try:
            guilds_response = http_requests.get(
                f"{DISCORD_API_URL}/users/@me/guilds?limit=200",
                headers={"Authorization": f"Bearer {discord_token}"},
                timeout=10,
            )

            if guilds_response.status_code == 429:
                return (
                    jsonify({"in_guild": False, "error": "Rate limited by Discord"}),
                    200,
                )

            if guilds_response.status_code != 200:
                return (
                    jsonify(
                        {
                            "in_guild": False,
                            "error": f"Discord API error: {guilds_response.status_code}",
                        }
                    ),
                    200,
                )

            guilds = guilds_response.json()
            if not isinstance(guilds, list):
                return (
                    jsonify(
                        {
                            "in_guild": False,
                            "error": "Unexpected Discord response format",
                        }
                    ),
                    200,
                )

            # Update cache
            session["guilds_cache"] = {
                "guilds": guilds,
                "expires_at": now + timedelta(minutes=5),
            }
        except Exception as e:
            return (
                jsonify(
                    {"in_guild": False, "error": f"Failed to fetch guilds: {str(e)}"}
                ),
                200,
            )

    # Search in the (now potentially cached) guilds list
    matched_guild = next((g for g in guilds if str(g.get("id")) == str(guild_id)), None)

    if matched_guild:
        icon_hash = matched_guild.get("icon")
        icon_url = (
            f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png?size=128"
            if icon_hash
            else None
        )
        return jsonify(
            {
                "in_guild": True,
                "guild_name": matched_guild.get("name"),
                "guild_icon": icon_url,
            }
        )

    return jsonify({"in_guild": False})


@chat_api.route("/chat/history/<station>")
@cross_origin(**CORS_OPTIONS)
def get_chat_history(station):
    station_key = station.upper().replace("-", "").replace(" ", "")
    if station_key not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    # Track activity if token provided
    auth_header = request.headers.get("Authorization")
    playing_header = request.headers.get("X-Playing-Station")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token in user_sessions:
            update_user_activity(
                user_sessions[token]["id"], station_key, playing_header
            )

    online_count, online_users_list = get_online_data(station_key)

    # Only return user list if specifically requested via ?full_users=1
    # This reduces payload size for every poll/history load
    include_full_users = request.args.get("full_users") == "1"

    return jsonify(
        {
            "station": station_key,
            "messages": chat_messages[station_key][-50:],
            "online_count": online_count,
            "online_users": online_users_list if include_full_users else None,
            "server_time": datetime.utcnow().isoformat() + "Z",
        }
    )


@chat_api.route("/chat/heartbeat", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def anonymous_heartbeat():
    """Track anonymous (not logged in) listeners per station."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    anon_id = data.get("anon_id", "").strip()
    station = data.get("station", "").upper().replace("-", "").replace(" ", "")

    if not anon_id or len(anon_id) > 64:
        return jsonify({"error": "Invalid anon_id"}), 400
    if station not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    now = datetime.utcnow()
    if station not in anonymous_listeners:
        anonymous_listeners[station] = {}
    anonymous_listeners[station][anon_id] = now

    # Invalidate cache so the new count is reflected
    if station in online_users_cache:
        del online_users_cache[station]

    return jsonify({"ok": True})


@chat_api.route("/chat/claim-anon", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def claim_anonymous():
    """Remove an anonymous listener when they log in via Discord."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    anon_id = data.get("anon_id", "").strip()
    if not anon_id:
        return jsonify({"error": "Invalid anon_id"}), 400

    removed = False
    for station_key in list(anonymous_listeners.keys()):
        if anon_id in anonymous_listeners[station_key]:
            del anonymous_listeners[station_key][anon_id]
            removed = True
            # Invalidate cache for this station
            if station_key in online_users_cache:
                del online_users_cache[station_key]

    return jsonify({"ok": True, "removed": removed})

@chat_api.route("/chat/poll/<station>")
@cross_origin(**CORS_OPTIONS)
def poll_messages(station):
    station_key = station.upper().replace("-", "").replace(" ", "")
    since = request.args.get("since", "")
    if station_key not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    # Track activity
    auth_header = request.headers.get("Authorization")
    playing_header = request.headers.get("X-Playing-Station")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token in user_sessions:
            update_user_activity(
                user_sessions[token]["id"], station_key, playing_header
            )

    messages = chat_messages[station_key]
    if since:
        since_time = safe_parse_datetime(since)
        if since_time != datetime.min:
            # Include messages that are either new (timestamp) or updated (last_update)
            messages = [
                m
                for m in messages
                if safe_parse_datetime(m.get("last_update", m["timestamp"]))
                > since_time
            ]

    online_count, online_users_list = get_online_data(station_key)

    # Global Mention Detection: Check other stations for mentions since 'since'
    other_mentions = []
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        if token in user_sessions and since:
            try:
                current_user = user_sessions[token]
                user_id = current_user["id"]
                username = current_user["username"].lower()
                global_name = (current_user.get("global_name") or "").lower()

                for s_key, msgs in chat_messages.items():
                    if s_key == station_key:
                        continue

                    for m in msgs:
                        m_time = safe_parse_datetime(
                            m.get("last_update", m["timestamp"])
                        )
                        if m_time > since_time:
                            content = m.get("content", "").lower()
                            is_met = False

                            # Mention patterns: @everyone, @here, @username, @global_name
                            patterns = [r"@everyone", r"@here"]
                            if username:
                                patterns.append(
                                    r"@" + re.escape(username) + r"(?![a-zA-Z0-9])"
                                )
                            if global_name:
                                patterns.append(
                                    r"@" + re.escape(global_name) + r"(?![a-zA-Z0-9])"
                                )

                            for p in patterns:
                                if re.search(p, content):
                                    is_met = True
                                    break

                            # If mentioned and not the author, add to other_mentions
                            if is_met and m["user"]["id"] != user_id:
                                m_copy = m.copy()
                                m_copy["station_id"] = s_key
                                m_copy["station_name"] = STATION_NAMES.get(s_key, s_key)
                                other_mentions.append(m_copy)
            except Exception as e:
                print(f"[POLL] Error checking mentions: {e}")

    # Only return user list if specifically requested via ?full_users=1
    include_full_users = request.args.get("full_users") == "1"

    return jsonify(
        {
            "messages": messages[-50:],
            "other_mentions": other_mentions,
            "online_count": online_count,
            "online_users": online_users_list if include_full_users else None,
            "server_time": datetime.utcnow().isoformat() + "Z",
        }
    )


# --- User Data Sync (listening history, favorites, stats) ---

# Allowed keys that can be synced to DB
SYNCABLE_KEYS = {"songHistory", "songFavorites", "listeningStats"}


def _do_save_user_data(user_id, data_key, data_value):
    """Save a user data entry to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_data (user_id, data_key, data_value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE data_value = VALUES(data_value)
        """,
        (user_id, data_key, data_value),
    )
    conn.commit()
    conn.close()


def _db_save_user_data(user_id, data_key, data_value):
    _db_enqueue(_do_save_user_data, user_id, data_key, data_value)


@chat_api.route("/user/data", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def get_user_data():
    """Get all synced data for the logged-in user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    user_id = user_sessions[token]["id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT data_key, data_value, updated_at FROM user_data WHERE user_id = %s",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row["data_key"]] = {
                "value": row["data_value"],
                "updated_at": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["updated_at"] else None,
            }

        return jsonify({"success": True, "data": result})

    except Exception as e:
        print(f"[DB] Error loading user data: {e}")
        return jsonify({"error": "Failed to load data"}), 500


@chat_api.route("/user/data", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def save_user_data():
    """Save one or more data keys for the logged-in user.
    Body: {"songHistory": [...], "songFavorites": [...], "listeningStats": {...}}
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    user_id = user_sessions[token]["id"]

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    saved_keys = []
    for key, value in data.items():
        if key not in SYNCABLE_KEYS:
            continue
        # Serialize to JSON string for DB storage
        json_value = json.dumps(value) if not isinstance(value, str) else value
        _db_save_user_data(user_id, key, json_value)
        saved_keys.append(key)

    return jsonify({"success": True, "saved": saved_keys})


@chat_api.route("/chat/send", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def send_message():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    data = request.json
    content = data.get("message", "").strip()[:200]
    station = data.get("station", "").upper().replace("-", "").replace(" ", "")
    image_data = data.get("image_data")  # base64 data URL

    # Validate image if present
    if image_data:
        if not isinstance(image_data, str) or not image_data.startswith("data:image/"):
            return jsonify({"error": "Invalid image format"}), 400
        # Check base64 size (~2.8MB for 2MB file)
        if len(image_data) > 2.8 * 1024 * 1024:
            return jsonify({"error": "Image too large (max 2MB)"}), 400

    # Content or image required
    if not content and not image_data:
        return jsonify({"error": "Invalid data"}), 400

    if station not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    user = user_sessions[token]
    now = datetime.utcnow()
    playing_header = request.headers.get("X-Playing-Station")
    update_user_activity(user["id"], station, playing_header)

    if (
        user["id"] in message_cooldowns
        and (now - message_cooldowns[user["id"]]).total_seconds()
        < MESSAGE_COOLDOWN_SECONDS
    ):
        return jsonify({"error": "Cooldown"}), 429

    message_cooldowns[user["id"]] = now
    msg_obj = {
        "id": secrets.token_hex(8),
        "user": user,
        "content": content,
        "timestamp": now.isoformat() + "Z",
        "last_update": now.isoformat() + "Z",
        "station": station,
        "song_data": data.get("song_data"),  # optional song embed
        "image_data": image_data,  # optional base64 image
        "reactions": {},  # emoji -> [user_ids]
        "reaction_users": {},  # user_id -> {username, avatar_url}
    }

    chat_messages[station].append(msg_obj)
    _db_save_message(msg_obj)
    if len(chat_messages[station]) > MAX_MESSAGES_PER_CHANNEL:
        chat_messages[station].pop(0)

    return jsonify({"success": True, "message": msg_obj})


@chat_api.route("/chat/delete", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def delete_message():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    data = request.json
    message_id = data.get("message_id", "")
    if not message_id:
        return jsonify({"error": "Missing message_id"}), 400

    user = user_sessions[token]
    user_id = user["id"]

    # Find and remove the message across all stations
    for station_key, msgs in chat_messages.items():
        for i, msg in enumerate(msgs):
            if msg["id"] == message_id:
                # Only the author can delete their own message
                if msg["user"]["id"] != user_id:
                    return jsonify({"error": "You can only delete your own messages"}), 403
                msgs.pop(i)
                _db_delete_message(message_id)
                return jsonify({"success": True, "deleted_id": message_id})

    return jsonify({"error": "Message not found"}), 404


@chat_api.route("/chat/react", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def react_to_message():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    if token not in user_sessions:
        return jsonify({"error": "Invalid session"}), 401

    data = request.json
    message_id = data.get("message_id", "")
    emoji = data.get("emoji", "").strip()

    if not message_id or not emoji:
        return jsonify({"error": "Missing message_id or emoji"}), 400

    # Limit emoji length (prevent abuse)
    # Increased to 40 to support custom_xxxxxxxx IDs
    if len(emoji) > 40:
        return jsonify({"error": "Invalid emoji"}), 400

    user = user_sessions[token]
    user_id = user["id"]

    # Find the message across all stations
    target_msg = None
    for station_key, msgs in chat_messages.items():
        for msg in msgs:
            if msg["id"] == message_id:
                target_msg = msg
                break
        if target_msg:
            break

    if not target_msg:
        return jsonify({"error": "Message not found"}), 404

    # Initialize reactions if missing (for old messages)
    if "reactions" not in target_msg:
        target_msg["reactions"] = {}
    if "reaction_users" not in target_msg:
        target_msg["reaction_users"] = {}

    # Toggle reaction
    if emoji not in target_msg["reactions"]:
        target_msg["reactions"][emoji] = []

    if user_id in target_msg["reactions"][emoji]:
        # Remove reaction
        target_msg["reactions"][emoji].remove(user_id)
        if not target_msg["reactions"][emoji]:
            del target_msg["reactions"][emoji]
        action = "removed"
    else:
        # Add reaction (max 20 different emojis per message)
        if emoji not in target_msg["reactions"] and len(target_msg["reactions"]) >= 20:
            return jsonify({"error": "Maximum reactions reached"}), 400
        target_msg["reactions"][emoji].append(user_id)
        action = "added"

    # Store user info for display
    target_msg["reaction_users"][user_id] = {
        "username": user.get("global_name") or user.get("username"),
        "avatar_url": user.get("avatar_url"),
    }

    # Mark message as updated so polling picks it up
    target_msg["last_update"] = datetime.utcnow().isoformat() + "Z"

    # Persist reaction changes to DB
    _db_save_message(target_msg)

    return jsonify(
        {
            "success": True,
            "action": action,
            "reactions": target_msg["reactions"],
            "reaction_users": target_msg["reaction_users"],
        }
    )


@chat_api.route("/music/itunes", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def search_itunes():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Missing query"}), 400
    try:
        url = f"https://itunes.apple.com/search?term={query}&media=music&limit=5"
        resp = http_requests.get(url, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chat_api.route("/music/deezer", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def search_deezer():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Missing query"}), 400
    try:
        url = f"https://api.deezer.com/search?q={query}&limit=5"
        resp = http_requests.get(url, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================
# DISCORD ACTIVITIES ENDPOINTS
# ========================


@chat_api.route("/discord/activity-token", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def discord_activity_token():
    """
    Token exchange endpoint for Discord Activities.
    The frontend (Embedded App SDK) calls authorize() which returns a 'code'.
    This code must be exchanged server-side for an access_token.
    Unlike regular OAuth2, Activities use grant_type='authorization_code'
    but WITHOUT a redirect_uri (Discord Activity SDK handles the PKCE flow).
    """
    data = request.json
    code = data.get("code") if data else None

    if not code:
        return jsonify({"error": "Missing code"}), 400

    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return jsonify({"error": "Discord OAuth not configured on server"}), 500

    try:
        token_response = http_requests.post(
            f"{DISCORD_API_URL}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_json = token_response.json()

        if "access_token" not in token_json:
            return (
                jsonify({"error": "Token exchange failed", "details": token_json}),
                400,
            )

        return jsonify({"access_token": token_json["access_token"]})

    except Exception as e:
        return jsonify({"error": f"Token exchange error: {str(e)}"}), 500


@chat_api.route("/discord/activity-login", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def discord_activity_login():
    """
    Creates a backend session from a Discord access_token obtained via the Embedded App SDK.
    This is the Activity equivalent of the OAuth2 callback — instead of being redirected,
    the SDK returns the access_token directly, which we use to fetch user data.
    Returns a session_token and user profile identical to the normal login flow.
    """
    data = request.json
    access_token = data.get("access_token") if data else None

    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400

    try:
        # Fetch user info from Discord using the provided access_token
        user_response = http_requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if user_response.status_code != 200:
            return (
                jsonify(
                    {
                        "error": "Failed to fetch user from Discord",
                        "status": user_response.status_code,
                    }
                ),
                401,
            )

        user_data = user_response.json()

        # Build user profile (same format as normal login)
        avatar = user_data.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user_data['id']}/{avatar}.png"
            if avatar
            else f"https://cdn.discordapp.com/embed/avatars/{int(user_data.get('discriminator', 0)) % 5}.png"
        )

        profile = {
            "id": user_data["id"],
            "username": user_data["username"],
            "global_name": user_data.get("global_name", user_data["username"]),
            "avatar_url": avatar_url,
            "banner_url": (
                f"https://cdn.discordapp.com/banners/{user_data['id']}/{user_data['banner']}.png?size=600"
                if user_data.get("banner")
                else None
            ),
            "accent_color": user_data.get("accent_color"),
        }

        # Store safe profile
        user_profiles[user_data["id"]] = profile
        _db_save_profile(profile)

        # Create session token (same structure as OAuth2 callback)
        import secrets as _secrets

        session_token = _secrets.token_urlsafe(64)
        user_sessions[session_token] = {
            **profile,
            "discord_access_token": access_token,
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
            "via_activity": True,  # Mark as Activity login for debugging
        }
        _db_save_session(session_token, user_sessions[session_token])

        return jsonify(
            {
                "success": True,
                "session_token": session_token,
                "user": profile,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Activity login error: {str(e)}"}), 500


app.register_blueprint(chat_api, url_prefix="/DiscordAuthChatApi")
app.register_blueprint(chat_api, name="chat_api_root")


@app.route("/")
def main_index():
    return "API Online"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
