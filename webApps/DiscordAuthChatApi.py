import os
import sys
import secrets
from datetime import datetime, timedelta

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Add parent directory to sys.path so 'api' becomes importable
sys.path.append(parent_dir)

# Optional: change working directory
os.chdir(parent_dir)
print("Working directory set to:", os.getcwd())

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
import json

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True, origins=["*"])

# Initialize SocketIO for real-time chat
# Use 'gevent' for Heroku, or None to auto-detect
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=None)

# Discord OAuth2 Configuration
# IMPORTANT: The redirect URI must point to THIS API's /discord/callback endpoint!
# Set these in your environment variables:
#   DISCORD_CLIENT_ID - from Discord Developer Portal
#   DISCORD_CLIENT_SECRET - from Discord Developer Portal
#   DISCORD_REDIRECT_URI - must be: http://localhost:5000/discord/callback (for local dev)
#   FRONTEND_URL - where to redirect after login: http://127.0.0.1:5500/WebAPP/index.html
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.environ.get(
    "DISCORD_REDIRECT_URI", "http://localhost:5000/discord/callback"
)
DISCORD_API_URL = "https://discord.com/api/v10"

# In-memory storage for sessions and chat messages (use Redis/DB in production)
user_sessions = {}  # token -> user_info
chat_messages = {"RADIOGAMING": [], "RADIOGAMINGDARK": [], "RADIOGAMINGMARONFM": []}
MAX_MESSAGES_PER_CHANNEL = 100

# Rate limiting for chat
message_cooldowns = {}  # user_id -> last_message_timestamp
MESSAGE_COOLDOWN_SECONDS = 2


@app.route("/")
def home():
    return jsonify(
        {
            "service": "Discord Auth & Chat API",
            "version": "1.0.0",
            "endpoints": {
                "/discord/login": "Initiate Discord OAuth login",
                "/discord/callback": "OAuth callback handler",
                "/discord/user": "Get current user info (requires auth)",
                "/discord/logout": "Logout current user",
                "/chat/history/<station>": "Get chat history for a station",
                "/chat/send": "Send a message (requires auth)",
            },
            "websocket": {
                "connect": "WebSocket connection for real-time chat",
                "events": [
                    "join_station",
                    "leave_station",
                    "new_message",
                    "receive_message",
                ],
            },
        }
    )


@app.route("/discord/login")
def discord_login():
    """Initiate Discord OAuth2 login flow"""
    if not DISCORD_CLIENT_ID:
        return jsonify({"error": "Discord OAuth not configured"}), 500

    # Generate a state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Discord OAuth URL
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

    print(f"[DISCORD AUTH] Redirecting to Discord OAuth...")
    return jsonify({"oauth_url": oauth_url})


@app.route("/discord/callback")
def discord_callback():
    """Handle Discord OAuth2 callback"""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        print(f"[DISCORD AUTH ERROR] {error}")
        return redirect(
            f"{os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5500/WebAPP/index.html')}?auth_error={error}"
        )

    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    # Exchange code for access token
    token_url = f"{DISCORD_API_URL}/oauth2/token"
    token_data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        token_response = requests.post(token_url, data=token_data, headers=headers)
        token_json = token_response.json()

        if "access_token" not in token_json:
            print(f"[DISCORD AUTH ERROR] Token exchange failed: {token_json}")
            return redirect(
                f"{os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5500/WebAPP/index.html')}?auth_error=token_exchange_failed"
            )

        access_token = token_json["access_token"]

        # Get user info from Discord
        user_response = requests.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_response.json()

        if "id" not in user_data:
            print(f"[DISCORD AUTH ERROR] User fetch failed: {user_data}")
            return redirect(
                f"{os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5500/WebAPP/index.html')}?auth_error=user_fetch_failed"
            )

        # Generate session token
        session_token = secrets.token_urlsafe(64)

        # Build avatar URL
        avatar_url = None
        if user_data.get("avatar"):
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
        else:
            # Default Discord avatar
            default_avatar = int(user_data.get("discriminator", 0)) % 5
            avatar_url = (
                f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
            )

        # Store user session
        user_sessions[session_token] = {
            "id": user_data["id"],
            "username": user_data["username"],
            "discriminator": user_data.get("discriminator", "0"),
            "global_name": user_data.get("global_name", user_data["username"]),
            "avatar_url": avatar_url,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

        print(
            f"[DISCORD AUTH SUCCESS] User logged in: {user_data['username']} (ID: {user_data['id']})"
        )

        # Redirect back to frontend with session token
        frontend_url = os.environ.get(
            "FRONTEND_URL", "http://127.0.0.1:5500/WebAPP/index.html"
        )
        return redirect(f"{frontend_url}?auth_token={session_token}")

    except Exception as e:
        print(f"[DISCORD AUTH ERROR] Exception: {str(e)}")
        return redirect(
            f"{os.environ.get('FRONTEND_URL', 'http://127.0.0.1:5500/WebAPP/index.html')}?auth_error=server_error"
        )


@app.route("/discord/user")
def get_user():
    """Get current authenticated user info"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid authorization header"}), 401

    token = auth_header.split(" ")[1]

    if token not in user_sessions:
        return jsonify({"error": "Invalid or expired session"}), 401

    user = user_sessions[token]

    # Check if session expired
    if datetime.fromisoformat(user["expires_at"]) < datetime.utcnow():
        del user_sessions[token]
        return jsonify({"error": "Session expired"}), 401

    return jsonify(
        {
            "authenticated": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "global_name": user["global_name"],
                "avatar_url": user["avatar_url"],
            },
        }
    )


@app.route("/discord/logout", methods=["POST"])
def logout():
    """Logout current user"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing authorization header"}), 401

    token = auth_header.split(" ")[1]

    if token in user_sessions:
        user = user_sessions[token]
        print(f"[DISCORD AUTH] User logged out: {user['username']}")
        del user_sessions[token]

    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route("/chat/history/<station>")
def get_chat_history(station):
    """Get chat history for a specific station"""
    station_key = station.upper().replace("-", "").replace(" ", "")

    if station_key not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    return jsonify(
        {
            "station": station_key,
            "messages": chat_messages[station_key][-50:],  # Return last 50 messages
        }
    )


@app.route("/chat/send", methods=["POST"])
def send_message():
    """Send a chat message (REST fallback)"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authentication required"}), 401

    token = auth_header.split(" ")[1]

    if token not in user_sessions:
        return jsonify({"error": "Invalid or expired session"}), 401

    user = user_sessions[token]
    data = request.json

    if not data or "message" not in data or "station" not in data:
        return jsonify({"error": "Missing message or station"}), 400

    message_text = data["message"].strip()[:500]  # Limit message length
    station_key = data["station"].upper().replace("-", "").replace(" ", "")

    if station_key not in chat_messages:
        return jsonify({"error": "Invalid station"}), 400

    if not message_text:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Rate limiting
    user_id = user["id"]
    now = datetime.utcnow()

    if user_id in message_cooldowns:
        time_since_last = (now - message_cooldowns[user_id]).total_seconds()
        if time_since_last < MESSAGE_COOLDOWN_SECONDS:
            return (
                jsonify(
                    {
                        "error": f"Please wait {MESSAGE_COOLDOWN_SECONDS - time_since_last:.1f}s before sending another message"
                    }
                ),
                429,
            )

    message_cooldowns[user_id] = now

    # Create message object
    message = {
        "id": secrets.token_hex(8),
        "user": {
            "id": user["id"],
            "username": user["username"],
            "global_name": user["global_name"],
            "avatar_url": user["avatar_url"],
        },
        "content": message_text,
        "timestamp": now.isoformat(),
        "station": station_key,
    }

    # Store message
    chat_messages[station_key].append(message)

    # Limit stored messages
    if len(chat_messages[station_key]) > MAX_MESSAGES_PER_CHANNEL:
        chat_messages[station_key] = chat_messages[station_key][
            -MAX_MESSAGES_PER_CHANNEL:
        ]

    # Broadcast via WebSocket
    socketio.emit("receive_message", message, room=station_key)

    print(f"[CHAT] {user['username']} -> {station_key}: {message_text[:50]}...")

    return jsonify({"success": True, "message": message})


# WebSocket Events
@socketio.on("connect")
def handle_connect():
    print(f"[WEBSOCKET] Client connected: {request.sid}")
    emit("connected", {"status": "connected", "sid": request.sid})


@socketio.on("disconnect")
def handle_disconnect():
    print(f"[WEBSOCKET] Client disconnected: {request.sid}")


@socketio.on("authenticate")
def handle_authenticate(data):
    """Authenticate WebSocket connection"""
    token = data.get("token")

    if not token or token not in user_sessions:
        emit("auth_error", {"error": "Invalid token"})
        return

    user = user_sessions[token]
    print(f"[WEBSOCKET] User authenticated: {user['username']}")
    emit("authenticated", {"user": user})


@socketio.on("join_station")
def handle_join_station(data):
    """Join a station chat room"""
    station = data.get("station", "").upper().replace("-", "").replace(" ", "")

    if station not in chat_messages:
        emit("error", {"error": "Invalid station"})
        return

    join_room(station)
    print(f"[WEBSOCKET] Client {request.sid} joined room: {station}")
    emit("joined_station", {"station": station})


@socketio.on("leave_station")
def handle_leave_station(data):
    """Leave a station chat room"""
    station = data.get("station", "").upper().replace("-", "").replace(" ", "")

    if station in chat_messages:
        leave_room(station)
        print(f"[WEBSOCKET] Client {request.sid} left room: {station}")
        emit("left_station", {"station": station})


@socketio.on("new_message")
def handle_new_message(data):
    """Handle incoming chat message via WebSocket"""
    token = data.get("token")
    message_text = data.get("message", "").strip()[:500]
    station = data.get("station", "").upper().replace("-", "").replace(" ", "")

    if not token or token not in user_sessions:
        emit("error", {"error": "Authentication required"})
        return

    if station not in chat_messages:
        emit("error", {"error": "Invalid station"})
        return

    if not message_text:
        emit("error", {"error": "Message cannot be empty"})
        return

    user = user_sessions[token]
    user_id = user["id"]
    now = datetime.utcnow()

    # Rate limiting
    if user_id in message_cooldowns:
        time_since_last = (now - message_cooldowns[user_id]).total_seconds()
        if time_since_last < MESSAGE_COOLDOWN_SECONDS:
            emit("error", {"error": f"Please wait before sending another message"})
            return

    message_cooldowns[user_id] = now

    # Create message object
    message = {
        "id": secrets.token_hex(8),
        "user": {
            "id": user["id"],
            "username": user["username"],
            "global_name": user["global_name"],
            "avatar_url": user["avatar_url"],
        },
        "content": message_text,
        "timestamp": now.isoformat(),
        "station": station,
    }

    # Store message
    chat_messages[station].append(message)

    if len(chat_messages[station]) > MAX_MESSAGES_PER_CHANNEL:
        chat_messages[station] = chat_messages[station][-MAX_MESSAGES_PER_CHANNEL:]

    # Broadcast to all clients in the station room
    emit("receive_message", message, room=station)

    print(f"[CHAT WS] {user['username']} -> {station}: {message_text[:50]}...")


def run_api():
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting Discord Auth & Chat API server on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_api()
