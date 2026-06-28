"""
DiscordAuthApi – Universal Discord OAuth2 Authentication API
============================================================
A reusable, multi-service authentication system.  Each *service* (passed
in the URL, e.g. ``/DiscordAuthApi/radiogaming/discord/login``) gets its
own set of database tables and its own Discord OAuth2 credentials pulled
from environment variables.

Environment variables per service (case-insensitive service name):
    DISCORDAUTH_<SERVICE>_CLIENT_ID
    DISCORDAUTH_<SERVICE>_CLIENT_SECRET
    DISCORDAUTH_<SERVICE>_REDIRECT_URI
    DISCORDAUTH_<SERVICE>_FRONTEND_URL

Shared database config is reused from api.config (same MySQL instance).
"""

import os
import sys
import secrets
import threading
from datetime import datetime, timedelta

# ── Path setup ────────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from flask import Flask, request, jsonify, redirect
from flask_cors import cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests as http_requests

from api.config import RESTRICT_CORS
from api.FunctionsModule import get_db_connection

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

CORS_OPTIONS = (
    {
        "origins": ["https://radio-gaming.stream", "https://k5studio.dev"],
        "allow_headers": ["Authorization", "Content-Type"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
    }
    if RESTRICT_CORS
    else {
        "origins": "*",
        "allow_headers": ["Authorization", "Content-Type"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
    }
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["120 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

DISCORD_API_URL = "https://discord.com/api/v10"

# ── In-memory caches (per service) ───────────────────────────────────────────
# service_key -> {session_token -> user_data}
_sessions = {}
# service_key -> {user_id -> profile}
_profiles = {}
# service_key -> {user_id -> datetime}  (online tracking)
_online_users = {}

ONLINE_THRESHOLD_SECONDS = 120
OFFLINE_THRESHOLD_SECONDS = 86400  # 24 h – prune after this

# Cache for online-users response to reduce CPU load per poll
_online_cache = {}   # service_key -> {"data": ..., "ts": datetime}
_CACHE_TTL = 10      # seconds

# ── Service credentials registry ─────────────────────────────────────────────
_service_configs = {}   # service_key -> {client_id, client_secret, redirect_uri, frontend_url}
_initialized_tables = set()  # service_keys whose DB tables have been created
_init_lock = threading.Lock()


def _norm_service(name: str) -> str:
    """Normalize a service name to uppercase, alphanumeric only."""
    return "".join(c for c in name.upper() if c.isalnum())


def _get_service_config(service_key: str) -> dict | None:
    """Load (and cache) Discord OAuth2 credentials for *service_key* from env."""
    if service_key in _service_configs:
        return _service_configs[service_key]

    prefix = f"DISCORDAUTH_{service_key}"
    client_id = os.environ.get(f"{prefix}_CLIENT_ID")
    client_secret = os.environ.get(f"{prefix}_CLIENT_SECRET")
    redirect_uri = os.environ.get(f"{prefix}_REDIRECT_URI")
    frontend_url = os.environ.get(f"{prefix}_FRONTEND_URL", "")

    if not client_id or not client_secret:
        return None

    cfg = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri or "",
        "frontend_url": frontend_url,
    }
    _service_configs[service_key] = cfg
    return cfg


# ── Database helpers ──────────────────────────────────────────────────────────

def _ensure_tables(service_key: str):
    """Create per-service tables if they don't exist yet."""
    if service_key in _initialized_tables:
        return
    with _init_lock:
        if service_key in _initialized_tables:
            return

        sk = service_key.lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        # User profiles
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `auth_{sk}_profiles` (
                user_id VARCHAR(64) PRIMARY KEY,
                username VARCHAR(128) NOT NULL,
                global_name VARCHAR(128),
                avatar_url TEXT,
                banner_url TEXT,
                accent_color INT,
                last_seen_at DATETIME,
                extra_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # Sessions
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `auth_{sk}_sessions` (
                session_token VARCHAR(128) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                discord_access_token TEXT,
                discord_refresh_token TEXT,
                expires_at DATETIME NOT NULL,
                via_activity TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_expires (expires_at)
            )
        """)

        # Generic per-user key-value data store
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `auth_{sk}_user_data` (
                user_id VARCHAR(64) NOT NULL,
                data_key VARCHAR(128) NOT NULL,
                data_value LONGTEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, data_key)
            )
        """)

        # Online activity log (optional analytics)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS `auth_{sk}_activity_log` (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                action VARCHAR(64) NOT NULL DEFAULT 'heartbeat',
                metadata_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user (user_id),
                INDEX idx_created (created_at)
            )
        """)

        conn.commit()
        conn.close()
        _initialized_tables.add(service_key)
        print(f"[DiscordAuthApi] Tables created for service: {service_key}")


def _save_profile_to_db(service_key: str, profile: dict):
    """Upsert user profile into the database."""
    sk = service_key.lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO `auth_{sk}_profiles`
            (user_id, username, global_name, avatar_url, banner_url, accent_color, last_seen_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username = VALUES(username),
            global_name = VALUES(global_name),
            avatar_url = VALUES(avatar_url),
            banner_url = VALUES(banner_url),
            accent_color = VALUES(accent_color),
            last_seen_at = VALUES(last_seen_at)
    """, (
        profile["id"],
        profile["username"],
        profile.get("global_name"),
        profile.get("avatar_url"),
        profile.get("banner_url"),
        profile.get("accent_color"),
        datetime.utcnow(),
    ))
    conn.commit()
    conn.close()


def _save_session_to_db(service_key: str, session_token: str, session_data: dict):
    """Persist a session to the database."""
    sk = service_key.lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO `auth_{sk}_sessions`
            (session_token, user_id, discord_access_token, discord_refresh_token, expires_at, via_activity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            discord_access_token = VALUES(discord_access_token),
            discord_refresh_token = VALUES(discord_refresh_token),
            expires_at = VALUES(expires_at)
    """, (
        session_token,
        session_data["id"],
        session_data.get("discord_access_token", ""),
        session_data.get("discord_refresh_token", ""),
        session_data.get("expires_at_dt", datetime.utcnow() + timedelta(days=7)),
        1 if session_data.get("via_activity") else 0,
    ))
    conn.commit()
    conn.close()


def _load_sessions_from_db(service_key: str):
    """Load active sessions from the database into memory."""
    sk = service_key.lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"""
            SELECT s.session_token, s.user_id, s.discord_access_token,
                   s.discord_refresh_token, s.expires_at, s.via_activity,
                   p.username, p.global_name, p.avatar_url, p.banner_url, p.accent_color
            FROM `auth_{sk}_sessions` s
            LEFT JOIN `auth_{sk}_profiles` p ON s.user_id = p.user_id
            WHERE s.expires_at > NOW()
        """)
        rows = cursor.fetchall()
        conn.close()

        if service_key not in _sessions:
            _sessions[service_key] = {}
        if service_key not in _profiles:
            _profiles[service_key] = {}

        for row in rows:
            profile = {
                "id": row["user_id"],
                "username": row["username"] or "Unknown",
                "global_name": row["global_name"] or row["username"] or "Unknown",
                "avatar_url": row["avatar_url"],
                "banner_url": row["banner_url"],
                "accent_color": row["accent_color"],
            }
            _profiles[service_key][row["user_id"]] = profile
            _sessions[service_key][row["session_token"]] = {
                **profile,
                "discord_access_token": row["discord_access_token"],
                "discord_refresh_token": row["discord_refresh_token"],
                "expires_at": row["expires_at"].isoformat() + "Z" if row["expires_at"] else None,
                "via_activity": bool(row["via_activity"]),
            }

        print(f"[DiscordAuthApi] Loaded {len(rows)} sessions for service: {service_key}")
    except Exception as e:
        print(f"[DiscordAuthApi] Failed to load sessions for {service_key}: {e}")


def _delete_session_from_db(service_key: str, session_token: str):
    """Remove a session from the database."""
    sk = service_key.lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM `auth_{sk}_sessions` WHERE session_token = %s", (session_token,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DiscordAuthApi] Failed to delete session: {e}")


# ── Helper: build Discord profile dict ────────────────────────────────────────

def _build_profile(user_data: dict) -> dict:
    """Build a safe profile dict from Discord API user data."""
    avatar = user_data.get("avatar")
    uid = user_data["id"]
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{uid}/{avatar}.png?size=256"
        if avatar
        else f"https://cdn.discordapp.com/embed/avatars/{int(user_data.get('discriminator', 0)) % 5}.png"
    )
    banner = user_data.get("banner")
    banner_url = (
        f"https://cdn.discordapp.com/banners/{uid}/{banner}.png?size=600"
        if banner
        else None
    )
    return {
        "id": uid,
        "username": user_data["username"],
        "global_name": user_data.get("global_name", user_data["username"]),
        "avatar_url": avatar_url,
        "banner_url": banner_url,
        "accent_color": user_data.get("accent_color"),
    }


# ── Online tracking helpers ───────────────────────────────────────────────────

def _update_activity(service_key: str, user_id: str):
    """Mark a user as active."""
    if service_key not in _online_users:
        _online_users[service_key] = {}
    _online_users[service_key][user_id] = datetime.utcnow()
    # Invalidate cache
    _online_cache.pop(service_key, None)


def _get_online_data(service_key: str):
    """Return (online_count, user_list) for a service."""
    now = datetime.utcnow()

    # Check cache
    cached = _online_cache.get(service_key)
    if cached and (now - cached["ts"]).total_seconds() < _CACHE_TTL:
        return cached["data"]

    users_activity = _online_users.get(service_key, {})
    profiles = _profiles.get(service_key, {})

    result = []
    online_count = 0

    # Clean up old entries while iterating
    active_uids = {}
    for uid, ts in users_activity.items():
        diff = (now - ts).total_seconds()
        if diff < OFFLINE_THRESHOLD_SECONDS:
            active_uids[uid] = ts
            is_online = diff < ONLINE_THRESHOLD_SECONDS
            if is_online:
                online_count += 1
            if uid in profiles:
                p = profiles[uid].copy()
                p["is_online"] = is_online
                p["last_seen"] = ts.isoformat() + "Z"
                result.append(p)

    _online_users[service_key] = active_uids

    # Sort: online first, then by last_seen descending
    result.sort(key=lambda x: (x["is_online"], x["last_seen"]), reverse=True)

    data = {"online_count": online_count, "users": result, "total_registered": len(profiles)}
    _online_cache[service_key] = {"data": data, "ts": now}
    return data


def _get_session(service_key: str, token: str) -> dict | None:
    """Return session data if valid, else None."""
    sessions = _sessions.get(service_key, {})
    session = sessions.get(token)
    if not session:
        return None
    # Check expiry
    exp = session.get("expires_at", "")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00")).replace(tzinfo=None)
            if exp_dt < datetime.utcnow():
                # Expired – clean up
                sessions.pop(token, None)
                _delete_session_from_db(service_key, token)
                return None
        except Exception:
            pass
    return session


# ══════════════════════════════════════════════════════════════════════════════
#                              ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@cross_origin(**CORS_OPTIONS)
def index():
    """List all registered services."""
    # Discover services from env
    services = []
    for key in os.environ:
        if key.startswith("DISCORDAUTH_") and key.endswith("_CLIENT_ID"):
            svc = key.replace("DISCORDAUTH_", "").replace("_CLIENT_ID", "")
            services.append(svc)
    return jsonify({
        "service": "Discord Auth API (Universal)",
        "status": "online",
        "registered_services": sorted(set(services)),
        "server_time": datetime.utcnow().isoformat() + "Z",
    })


# ── Discord OAuth2 Login ─────────────────────────────────────────────────────

@app.route("/<service>/discord/login")
@cross_origin(**CORS_OPTIONS)
def discord_login(service):
    """Generate a Discord OAuth2 authorization URL for the given service."""
    service_key = _norm_service(service)
    cfg = _get_service_config(service_key)
    if not cfg:
        return jsonify({"error": f"Service '{service}' is not configured. "
                        f"Set DISCORDAUTH_{service_key}_CLIENT_ID and DISCORDAUTH_{service_key}_CLIENT_SECRET env vars."}), 404

    _ensure_tables(service_key)

    state = secrets.token_urlsafe(32)
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={cfg['client_id']}"
        f"&redirect_uri={cfg['redirect_uri']}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
        f"&state={state}"
    )
    return jsonify({"oauth_url": oauth_url, "state": state})


# ── Discord OAuth2 Callback ──────────────────────────────────────────────────

@app.route("/<service>/discord/callback")
@cross_origin(**CORS_OPTIONS)
def discord_callback(service):
    """Handle the Discord OAuth2 callback – exchange code, create session, redirect."""
    service_key = _norm_service(service)
    cfg = _get_service_config(service_key)
    if not cfg:
        return jsonify({"error": f"Service '{service}' is not configured"}), 404

    _ensure_tables(service_key)

    code = request.args.get("code")
    frontend_url = cfg.get("frontend_url") or request.args.get("redirect", "")

    if not code:
        if frontend_url:
            return redirect(f"{frontend_url}?auth_error=no_code")
        return jsonify({"error": "Missing authorization code"}), 400

    try:
        # Exchange code for token
        token_response = http_requests.post(
            f"{DISCORD_API_URL}/oauth2/token",
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_json = token_response.json()

        if "access_token" not in token_json:
            if frontend_url:
                return redirect(f"{frontend_url}?auth_error=token_exchange_failed")
            return jsonify({"error": "Token exchange failed", "details": token_json}), 400

        # Fetch user info
        user_response = http_requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {token_json['access_token']}"},
            timeout=10,
        )
        user_data = user_response.json()

        profile = _build_profile(user_data)
        session_token = secrets.token_urlsafe(64)
        expires_at_dt = datetime.utcnow() + timedelta(days=7)

        session_data = {
            **profile,
            "discord_access_token": token_json["access_token"],
            "discord_refresh_token": token_json.get("refresh_token", ""),
            "expires_at": expires_at_dt.isoformat() + "Z",
            "expires_at_dt": expires_at_dt,
        }

        # Store in memory
        if service_key not in _sessions:
            _sessions[service_key] = {}
        if service_key not in _profiles:
            _profiles[service_key] = {}

        _sessions[service_key][session_token] = session_data
        _profiles[service_key][user_data["id"]] = profile

        # Persist to DB
        _save_profile_to_db(service_key, profile)
        _save_session_to_db(service_key, session_token, session_data)

        # Update online status
        _update_activity(service_key, user_data["id"])

        if frontend_url:
            return redirect(f"{frontend_url}?auth_token={session_token}")

        return jsonify({
            "success": True,
            "session_token": session_token,
            "user": profile,
            "expires_at": session_data["expires_at"],
        })

    except Exception as e:
        print(f"[DiscordAuthApi] Callback error for {service_key}: {e}")
        if frontend_url:
            return redirect(f"{frontend_url}?auth_error=server_error")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ── Discord Activity Token Exchange ───────────────────────────────────────────

@app.route("/<service>/discord/activity-token", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def discord_activity_token(service):
    """Exchange a Discord Activity SDK code for an access_token (server-side)."""
    service_key = _norm_service(service)
    cfg = _get_service_config(service_key)
    if not cfg:
        return jsonify({"error": f"Service '{service}' is not configured"}), 404

    data = request.json
    code = data.get("code") if data else None
    if not code:
        return jsonify({"error": "Missing code"}), 400

    try:
        token_response = http_requests.post(
            f"{DISCORD_API_URL}/oauth2/token",
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "grant_type": "authorization_code",
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        token_json = token_response.json()

        if "access_token" not in token_json:
            return jsonify({"error": "Token exchange failed", "details": token_json}), 400

        return jsonify({"access_token": token_json["access_token"]})

    except Exception as e:
        return jsonify({"error": f"Token exchange error: {str(e)}"}), 500


# ── Discord Activity Login (from access_token) ───────────────────────────────

@app.route("/<service>/discord/activity-login", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def discord_activity_login(service):
    """Create a backend session from a Discord access_token obtained via Activity SDK."""
    service_key = _norm_service(service)
    cfg = _get_service_config(service_key)
    if not cfg:
        return jsonify({"error": f"Service '{service}' is not configured"}), 404

    _ensure_tables(service_key)

    data = request.json
    access_token = data.get("access_token") if data else None
    if not access_token:
        return jsonify({"error": "Missing access_token"}), 400

    try:
        user_response = http_requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if user_response.status_code != 200:
            return jsonify({"error": "Failed to fetch user from Discord", "status": user_response.status_code}), 401

        user_data = user_response.json()
        profile = _build_profile(user_data)
        session_token = secrets.token_urlsafe(64)
        expires_at_dt = datetime.utcnow() + timedelta(days=7)

        session_data = {
            **profile,
            "discord_access_token": access_token,
            "expires_at": expires_at_dt.isoformat() + "Z",
            "expires_at_dt": expires_at_dt,
            "via_activity": True,
        }

        if service_key not in _sessions:
            _sessions[service_key] = {}
        if service_key not in _profiles:
            _profiles[service_key] = {}

        _sessions[service_key][session_token] = session_data
        _profiles[service_key][user_data["id"]] = profile

        _save_profile_to_db(service_key, profile)
        _save_session_to_db(service_key, session_token, session_data)
        _update_activity(service_key, user_data["id"])

        return jsonify({
            "success": True,
            "session_token": session_token,
            "user": profile,
            "expires_at": session_data["expires_at"],
        })

    except Exception as e:
        return jsonify({"error": f"Activity login error: {str(e)}"}), 500


# ── Get Current User ──────────────────────────────────────────────────────────

@app.route("/<service>/discord/user")
@cross_origin(**CORS_OPTIONS)
def get_user(service):
    """Return the current authenticated user's profile."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid or expired session"}), 401

    # Update activity
    _update_activity(service_key, session["id"])

    # Return safe profile (exclude discord tokens)
    safe = {k: v for k, v in session.items() if k not in ("discord_access_token", "discord_refresh_token", "expires_at_dt")}
    return jsonify({"authenticated": True, "user": safe})


# ── Check Guild Membership ────────────────────────────────────────────────────

@app.route("/<service>/discord/check-guild/<guild_id>")
@cross_origin(**CORS_OPTIONS)
def check_guild(service, guild_id):
    """Check if the authenticated user is in a specific Discord guild."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid session"}), 401

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
            return jsonify({"in_guild": False, "error": "Rate limited by Discord"}), 200
        if guilds_response.status_code != 200:
            return jsonify({"in_guild": False, "error": f"Discord API error: {guilds_response.status_code}"}), 200

        guilds = guilds_response.json()
        if not isinstance(guilds, list):
            return jsonify({"in_guild": False, "error": "Unexpected Discord response format"}), 200

        matched = next((g for g in guilds if str(g.get("id")) == str(guild_id)), None)

        if matched:
            icon_hash = matched.get("icon")
            icon_url = (
                f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png?size=128"
                if icon_hash else None
            )
            return jsonify({
                "in_guild": True,
                "guild_name": matched.get("name"),
                "guild_icon": icon_url,
            })

        return jsonify({"in_guild": False})

    except Exception as e:
        return jsonify({"in_guild": False, "error": f"Failed to fetch guilds: {str(e)}"}), 200


# ── Logout ────────────────────────────────────────────────────────────────────

@app.route("/<service>/discord/logout", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def logout(service):
    """Invalidate the current session."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    sessions = _sessions.get(service_key, {})
    removed = sessions.pop(token, None)

    if removed:
        _delete_session_from_db(service_key, token)

    return jsonify({"success": True, "logged_out": removed is not None})


# ── Online Users / Heartbeat ─────────────────────────────────────────────────

@app.route("/<service>/users/heartbeat", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def heartbeat(service):
    """Heartbeat endpoint – keeps the user online. Called periodically by frontend."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid session"}), 401

    _update_activity(service_key, session["id"])
    return jsonify({"success": True, "server_time": datetime.utcnow().isoformat() + "Z"})


@app.route("/<service>/users/online")
@cross_origin(**CORS_OPTIONS)
def get_online_users(service):
    """Return list of online users for the given service."""
    service_key = _norm_service(service)

    # Optionally track caller's activity
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        session = _get_session(service_key, token)
        if session:
            _update_activity(service_key, session["id"])

    data = _get_online_data(service_key)
    return jsonify({
        **data,
        "service": service_key,
        "server_time": datetime.utcnow().isoformat() + "Z",
    })


@app.route("/<service>/users/profile/<user_id>")
@cross_origin(**CORS_OPTIONS)
def get_user_profile(service, user_id):
    """Return a user's public profile."""
    service_key = _norm_service(service)
    profiles = _profiles.get(service_key, {})
    profile = profiles.get(user_id)

    if not profile:
        # Try loading from DB
        sk = service_key.lower()
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM `auth_{sk}_profiles` WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                profile = {
                    "id": row["user_id"],
                    "username": row["username"],
                    "global_name": row["global_name"],
                    "avatar_url": row["avatar_url"],
                    "banner_url": row["banner_url"],
                    "accent_color": row["accent_color"],
                }
                if service_key not in _profiles:
                    _profiles[service_key] = {}
                _profiles[service_key][user_id] = profile
        except Exception as e:
            print(f"[DiscordAuthApi] Failed to load profile from DB: {e}")

    if not profile:
        return jsonify({"error": "User not found"}), 404

    # Check online status
    activity = _online_users.get(service_key, {})
    last_seen = activity.get(user_id)
    is_online = False
    if last_seen:
        is_online = (datetime.utcnow() - last_seen).total_seconds() < ONLINE_THRESHOLD_SECONDS

    return jsonify({
        **profile,
        "is_online": is_online,
        "last_seen": last_seen.isoformat() + "Z" if last_seen else None,
    })


# ── User Data (key-value store per user) ──────────────────────────────────────

@app.route("/<service>/users/data", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def get_user_data(service):
    """Get user data (key-value pairs) for the authenticated user."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid session"}), 401

    user_id = session["id"]
    data_key = request.args.get("key")
    sk = service_key.lower()

    _ensure_tables(service_key)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if data_key:
            cursor.execute(
                f"SELECT data_key, data_value FROM `auth_{sk}_user_data` WHERE user_id = %s AND data_key = %s",
                (user_id, data_key),
            )
        else:
            cursor.execute(
                f"SELECT data_key, data_value FROM `auth_{sk}_user_data` WHERE user_id = %s",
                (user_id,),
            )
        rows = cursor.fetchall()
        conn.close()

        result = {row["data_key"]: row["data_value"] for row in rows}
        return jsonify({"user_id": user_id, "data": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/<service>/users/data", methods=["POST"])
@cross_origin(**CORS_OPTIONS)
def set_user_data(service):
    """Set user data (key-value pairs) for the authenticated user."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid session"}), 401

    user_id = session["id"]
    data = request.json
    if not data or "key" not in data or "value" not in data:
        return jsonify({"error": "Missing 'key' and 'value' in request body"}), 400

    sk = service_key.lower()
    _ensure_tables(service_key)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO `auth_{sk}_user_data` (user_id, data_key, data_value)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE data_value = VALUES(data_value)
        """, (user_id, data["key"], str(data["value"])))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "key": data["key"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/<service>/users/data", methods=["DELETE"])
@cross_origin(**CORS_OPTIONS)
def delete_user_data(service):
    """Delete a user data key for the authenticated user."""
    service_key = _norm_service(service)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header.split(" ")[1]
    session = _get_session(service_key, token)
    if not session:
        return jsonify({"error": "Invalid session"}), 401

    user_id = session["id"]
    data_key = request.args.get("key")
    if not data_key:
        return jsonify({"error": "Missing 'key' query parameter"}), 400

    sk = service_key.lower()
    _ensure_tables(service_key)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM `auth_{sk}_user_data` WHERE user_id = %s AND data_key = %s",
            (user_id, data_key),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()

        return jsonify({"success": True, "deleted": deleted})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── All Registered Users (admin / stats) ──────────────────────────────────────

@app.route("/<service>/users/all")
@cross_origin(**CORS_OPTIONS)
def get_all_users(service):
    """Return all registered user profiles for a service (paginated)."""
    service_key = _norm_service(service)
    sk = service_key.lower()
    _ensure_tables(service_key)

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    offset = (page - 1) * per_page

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"SELECT COUNT(*) as total FROM `auth_{sk}_profiles`")
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"SELECT * FROM `auth_{sk}_profiles` ORDER BY last_seen_at DESC LIMIT %s OFFSET %s",
            (per_page, offset),
        )
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            u = {
                "id": row["user_id"],
                "username": row["username"],
                "global_name": row["global_name"],
                "avatar_url": row["avatar_url"],
                "banner_url": row["banner_url"],
                "accent_color": row["accent_color"],
                "last_seen_at": row["last_seen_at"].isoformat() + "Z" if row["last_seen_at"] else None,
                "created_at": row["created_at"].isoformat() + "Z" if row.get("created_at") else None,
            }
            # Check in-memory online status
            activity = _online_users.get(service_key, {})
            last_act = activity.get(row["user_id"])
            u["is_online"] = (
                last_act is not None
                and (datetime.utcnow() - last_act).total_seconds() < ONLINE_THRESHOLD_SECONDS
            )
            users.append(u)

        return jsonify({
            "service": service_key,
            "total": total,
            "page": page,
            "per_page": per_page,
            "users": users,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Service Info ──────────────────────────────────────────────────────────────

@app.route("/<service>/info")
@cross_origin(**CORS_OPTIONS)
def service_info(service):
    """Return service status, user count, online count."""
    service_key = _norm_service(service)
    cfg = _get_service_config(service_key)
    if not cfg:
        return jsonify({"error": f"Service '{service}' is not configured"}), 404

    _ensure_tables(service_key)

    # Get online data
    online_data = _get_online_data(service_key)

    # Get total registered from DB
    sk = service_key.lower()
    total_registered = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `auth_{sk}_profiles`")
        total_registered = cursor.fetchone()[0]
        conn.close()
    except Exception:
        pass

    return jsonify({
        "service": service_key,
        "status": "online",
        "configured": True,
        "online_count": online_data["online_count"],
        "total_registered": total_registered,
        "has_redirect_uri": bool(cfg.get("redirect_uri")),
        "has_frontend_url": bool(cfg.get("frontend_url")),
        "server_time": datetime.utcnow().isoformat() + "Z",
    })


# ══════════════════════════════════════════════════════════════════════════════
#                          STARTUP – load existing sessions
# ══════════════════════════════════════════════════════════════════════════════

def _startup_load():
    """Discover configured services from env and load their sessions from DB."""
    for key in os.environ:
        if key.startswith("DISCORDAUTH_") and key.endswith("_CLIENT_ID"):
            svc = key.replace("DISCORDAUTH_", "").replace("_CLIENT_ID", "")
            svc_key = _norm_service(svc)
            cfg = _get_service_config(svc_key)
            if cfg:
                _ensure_tables(svc_key)
                _load_sessions_from_db(svc_key)


# Run startup in background to not block app creation
_startup_thread = threading.Thread(target=_startup_load, daemon=True)
_startup_thread.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
