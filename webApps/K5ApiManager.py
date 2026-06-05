import os
import sys
import time as _time

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Add parent directory to sys.path so 'api' becomes importable
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Now safely import
from flask import Flask, request, jsonify
from api.FunctionsModule import (
    get_running_bots,
    get_discord_user_profile,
    get_roblox_username,
    get_roblox_avatar,
    get_db_connection,
    require_api_key,
    create_service_stats_table,
)

from flask import render_template
import json


from functools import wraps
import base64
import requests

from flask_cors import CORS, cross_origin
from flask_caching import Cache
from datetime import datetime
from api.config import RESTRICT_CORS

_CORS_ORIGINS = ["https://radio-gaming.stream", "https://k5studio.dev"] if RESTRICT_CORS else "*"

app = Flask(__name__, template_folder=parent_dir + "/api/templates")

cache = Cache(app, config={"CACHE_TYPE": "simple"})

# ─── Server Uptime ─────────────────────────────────────────────────────────────
_server_start_time = _time.time()


@app.route("/")
def main_page():
    return render_template("/k5api.html")


@app.route("/running_bots")
def running_bots():
    bots = get_running_bots()
    return jsonify(bots)


@app.route("/api_key_info", methods=["GET"])
@require_api_key
def api_key_info():
    api_key = request.headers.get("X-API-Key")
    hashed_key = api_key

    print(f"[REQUEST] GET /api_key_info - api_key: {api_key}")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, owner, created_at FROM api_keys WHERE key_value = %s", (hashed_key,)
    )
    key_info = cursor.fetchone()
    conn.close()

    if key_info:
        print(f"[SUCCESS] Found API key info for: {api_key}")
        return jsonify({"api_key_info": key_info})
    else:
        print("[ERROR] API key not found.")
        return jsonify({"error": "API key not found"}), 404


@app.route("/get_balance", methods=["GET"])
def get_balance():
    user_id = request.args.get("user_id")
    print(f"[REQUEST] GET /get_balance - user_id: {user_id}")

    if not user_id:
        print("[ERROR] Missing user_id in request.")
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for user_id: {user_id}")
    cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    conn.close()

    if user:
        print(f"[SUCCESS] Retrieved balance: {user['balance']} for user_id: {user_id}")
        discord_profile = get_discord_user_profile(user_id)
        return jsonify({"balance": user["balance"], "discord_profile": discord_profile})
    else:
        print("[ERROR] User not found.")
        return jsonify({"error": "User not found"}), 404


@app.route("/update_balance", methods=["POST"])
@require_api_key
def update_balance():
    data = request.json
    if data is None:
        return jsonify({"error": "Missing or invalid JSON body"}), 400
    user_id = data.get("user_id")
    amount = data.get("amount")

    print(f"[REQUEST] POST /update_balance - user_id: {user_id}, amount: {amount}")

    if not user_id or amount is None:
        print("[ERROR] Missing user_id or amount in request.")
        return jsonify({"error": "Missing user_id or amount"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for user_id: {user_id} by {amount}")
    cursor.execute(
        "UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id)
    )
    conn.commit()
    conn.close()

    print("[SUCCESS] Balance updated successfully.")
    return jsonify({"message": "Balance updated successfully"})


# Roblox support
@app.route("/roblox/get_balance", methods=["GET"])
def get_roblox_balance():
    roblox_id = request.args.get("roblox_id")
    print(f"[REQUEST] GET /roblox/get_balance - roblox_id: {roblox_id}")

    if not roblox_id:
        print("[ERROR] Missing roblox_id in request.")
        return jsonify({"error": "Missing roblox_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    print(f"[DB QUERY] Fetching balance for roblox_id: {roblox_id}")
    cursor.execute("SELECT balance FROM users WHERE roblox_id = %s", (roblox_id,))
    user = cursor.fetchone()

    conn.close()

    if user:
        print(
            f"[SUCCESS] Retrieved balance: {user['balance']} for roblox_id: {roblox_id}"
        )
        robloxprofile = {
            "username": get_roblox_username(roblox_id),
            "avatar_url": get_roblox_avatar(roblox_id),
            "id": roblox_id,
        }
        return jsonify({"balance": user["balance"], "discord_profile": robloxprofile})
    else:
        print("[ERROR] Roblox user not found.")
        return jsonify({"error": "Roblox user not found"}), 404


@app.route("/roblox/update_balance", methods=["POST"])
@require_api_key
def update_roblox_balance():
    data = request.json
    if data is None:
        return jsonify({"error": "Missing or invalid JSON body"}), 400
    roblox_id = data.get("roblox_id")
    amount = data.get("amount")

    print(
        f"[REQUEST] POST /roblox/update_balance - roblox_id: {roblox_id}, amount: {amount}"
    )

    if not roblox_id or amount is None:
        print("[ERROR] Missing roblox_id or amount in request.")
        return jsonify({"error": "Missing roblox_id or amount"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"[DB QUERY] Updating balance for roblox_id: {roblox_id} by {amount}")
    cursor.execute(
        "UPDATE users SET balance = balance + %s WHERE roblox_id = %s",
        (amount, roblox_id),
    )
    conn.commit()
    conn.close()

    print("[SUCCESS] Roblox balance updated successfully.")
    return jsonify({"message": "Roblox balance updated successfully"})


@app.route("/spotify/token", methods=["GET"])
@cross_origin(origins=_CORS_ORIGINS)
@cache.cached(timeout=3000, query_string=False)
def get_spotify_token():
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

    token_url = "https://accounts.spotify.com/api/token"
    credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        created_at = datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )  # ISO 8601 UTC time
        return jsonify(
            {
                "access_token": token_data["access_token"],
                "expires_in": token_data["expires_in"],
                "created_at": created_at,
            }
        )
    else:
        return (
            jsonify(
                {
                    "error": "Failed to retrieve Spotify token",
                    "details": response.json(),
                }
            ),
            response.status_code,
        )


@app.route("/giphy/token", methods=["GET"])
@cross_origin(origins=_CORS_ORIGINS)
@cache.cached(timeout=3000, query_string=False)
def get_giphy_token():
    GIPHY_TOKEN = os.environ.get("GIPHY_TOKEN")

    if GIPHY_TOKEN:
        created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return jsonify(
            {
                "access_token": GIPHY_TOKEN,
                "expires_in": 3600,  # Static value for consistency
                "created_at": created_at,
            }
        )
    else:
        return (
            jsonify({"error": "GIPHY_TOKEN not found in environment"}),
            500,
        )


@app.route("/youtube/token", methods=["GET"])
@cross_origin(origins=_CORS_ORIGINS)
@cache.cached(timeout=3000, query_string=False)
def get_youtube_token():
    YOUTUBE_DATA_TOKEN = os.environ.get("YOUTUBE_DATA_TOKEN")

    if YOUTUBE_DATA_TOKEN:
        created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        return jsonify(
            {
                "access_token": YOUTUBE_DATA_TOKEN,
                "expires_in": 3600,  # Static value for consistency
                "created_at": created_at,
            }
        )
    else:
        return (
            jsonify({"error": "YOUTUBE_DATA_TOKEN not found in environment"}),
            500,
        )


@app.route("/roblox/download_asset", methods=["GET"])
def download_any_roblox_asset():
    asset_id = request.args.get("id")
    if not asset_id:
        return jsonify({"error": "Missing asset ID"}), 400

    asset_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"

    try:
        response = requests.get(asset_url, stream=True)
        # if response.status_code != 200:
        # return jsonify({"error": f"Asset not found (status {response.status_code})"}), 404

        # Try to get content type and set basic file extensions
        content_type = response.headers.get("Content-Type", "application/octet-stream")

        # Mapping of known types to extensions
        extension_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "audio/ogg": "ogg",
            "text/plain": "txt",
            "application/json": "json",
            "application/octet-stream": "rbxasset",  # Safe fallback
        }

        extension = extension_map.get(content_type, "rbxasset")
        filename = f"{asset_id}.{extension}"

        return (
            response.content,
            200,
            {
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except Exception as e:
        return jsonify({"error": "Failed to fetch asset", "details": str(e)}), 500


@app.route("/steam/workshop-stats", methods=["GET"])
@cross_origin()
@cache.cached(timeout=600, query_string=True)
def steam_workshop_stats():
    """Fetch Steam Workshop item stats (subscribers, favorites, views).
    Usage: /steam/workshop-stats?ids=2961836726,2908364654
    """
    ids_param = request.args.get("ids", "")
    file_ids = [fid.strip() for fid in ids_param.split(",") if fid.strip()]

    if not file_ids:
        return jsonify({"error": "Missing 'ids' query parameter"}), 400

    # Build POST data for Steam API
    post_data = {"itemcount": len(file_ids)}
    for i, fid in enumerate(file_ids):
        post_data[f"publishedfileids[{i}]"] = fid

    try:
        resp = requests.post(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=post_data,
            timeout=10,
        )
        steam_data = resp.json()

        items = []
        for detail in steam_data.get("response", {}).get("publishedfiledetails", []):
            items.append({
                "publishedfileid": detail.get("publishedfileid"),
                "title": detail.get("title"),
                "subscriptions": detail.get("subscriptions", 0),
                "favorited": detail.get("favorited", 0),
                "views": detail.get("views", 0),
                "lifetime_subscriptions": detail.get("lifetime_subscriptions", 0),
                "lifetime_favorited": detail.get("lifetime_favorited", 0),
            })

        return jsonify({"items": items})

    except Exception as e:
        return jsonify({"error": "Failed to fetch Steam Workshop stats", "details": str(e)}), 500


@app.route("/api/uptime")
@cross_origin()
def api_uptime():
    """Return server uptime in seconds, formatted string, and start timestamp."""
    uptime_sec = _time.time() - _server_start_time
    days = int(uptime_sec // 86400)
    hours = int((uptime_sec % 86400) // 3600)
    minutes = int((uptime_sec % 3600) // 60)
    secs = int(uptime_sec % 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return jsonify({
        "uptime_seconds": round(uptime_sec, 1),
        "uptime_formatted": " ".join(parts),
        "started_at": _server_start_time,
        "started_at_iso": datetime.utcfromtimestamp(_server_start_time).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


@app.route("/api/running-services")
@cross_origin()
@cache.cached(timeout=30)
def api_running_services():
    """Return the count of currently running Discord bots and web services."""
    bots = get_running_bots()
    # Count web service .py files in the webApps directory
    webapps_dir = os.path.join(script_dir)
    web_services = [f for f in os.listdir(webapps_dir) if f.endswith(".py")]
    return jsonify({
        "bots_count": len(bots),
        "web_services_count": len(web_services),
        "bots": [b.get("username", "unknown") for b in bots],
        "web_services": [f.replace(".py", "") for f in web_services],
    })


# ─── Roblox Game Stats Proxy ──────────────────────────────────────────────────

@app.route("/api/game-stats")
@cross_origin(origins=_CORS_ORIGINS)
@cache.cached(timeout=60, query_string=True)
def api_game_stats():
    """Proxy Roblox games API to avoid CORS. Accepts ?universeIds=id1,id2,..."""
    universe_ids = request.args.get("universeIds", "").strip()
    if not universe_ids:
        return jsonify({"error": "Missing universeIds"}), 400

    try:
        resp = requests.get(
            f"https://games.roblox.com/v1/games?universeIds={universe_ids}",
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Discord Webhook Config (from env vars) ───────────────────────────────────
# Env vars format: WEBHOOK_<GUILD_ID>=<webhook_url>
# Example: WEBHOOK_637696690853511184=https://discord.com/api/webhooks/...

_WEBHOOK_GUILDS = []
for key, val in os.environ.items():
    if key.startswith("WEBHOOK_"):
        guild_id = key.replace("WEBHOOK_", "")
        _WEBHOOK_GUILDS.append({"id": guild_id, "requireGuildMembership": True})


@app.route("/api/webhooks")
@cross_origin(origins=_CORS_ORIGINS)
def api_webhooks():
    """Return list of guilds with webhooks (without exposing URLs)."""
    return jsonify({"guilds": _WEBHOOK_GUILDS})


@app.route("/api/share", methods=["POST"])
@cross_origin(origins=_CORS_ORIGINS)
def api_share():
    """Proxy webhook message so webhook URLs stay server-side."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing body"}), 400

    guild_id = data.get("guild_id", "")
    payload = data.get("payload")
    if not guild_id or not payload:
        return jsonify({"error": "Missing guild_id or payload"}), 400

    webhook_url = os.environ.get(f"WEBHOOK_{guild_id}")
    if not webhook_url:
        return jsonify({"error": "Unknown guild"}), 404

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        return jsonify({"ok": True, "status": resp.status_code}), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Global Service Stats ──────────────────────────────────────────────────────
# Ensures the service_stats table exists on startup
create_service_stats_table()


@app.route("/stats/<service_name>", methods=["GET"])
@cross_origin()
def get_all_service_stats(service_name):
    """Return all stats for a given service.
    Usage: GET /stats/k5portfolio
    """
    service_name = service_name.lower().strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT stat_name, value, updated_at, created_at FROM service_stats WHERE service_name = %s",
        (service_name,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"service": service_name, "stats": {}, "message": "No stats found for this service"})

    stats = {}
    for row in rows:
        stats[row["stat_name"]] = {
            "value": row["value"],
            "updated_at": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["updated_at"] else None,
            "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["created_at"] else None,
        }

    return jsonify({"service": service_name, "stats": stats})


@app.route("/stats/<service_name>/<stat_name>", methods=["GET"])
@cross_origin()
def get_service_stat(service_name, stat_name):
    """Return a single stat for a service.
    Usage: GET /stats/k5portfolio/totalvisits
    """
    service_name = service_name.lower().strip()
    stat_name = stat_name.lower().strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT value, updated_at, created_at FROM service_stats WHERE service_name = %s AND stat_name = %s",
        (service_name, stat_name),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "service": service_name,
            "stat": stat_name,
            "value": row["value"],
            "updated_at": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["updated_at"] else None,
            "created_at": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if row["created_at"] else None,
        })
    else:
        return jsonify({"error": "Stat not found", "service": service_name, "stat": stat_name}), 404


@app.route("/stats/<service_name>/<stat_name>", methods=["POST"])
@require_api_key
def update_service_stat(service_name, stat_name):
    """Create or update a stat for a service.
    Usage: POST /stats/k5portfolio/totalvisits
    Body JSON:
      {"value": 100}          -> sets the stat to exactly 100
      {"increment": 1}        -> adds 1 to the current value (creates with 1 if new)
      {"increment": -5}       -> subtracts 5 from the current value
    """
    service_name = service_name.lower().strip()
    stat_name = stat_name.lower().strip()

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing or invalid JSON body"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if "value" in data:
        # Absolute set
        new_value = float(data["value"])
        cursor.execute(
            """
            INSERT INTO service_stats (service_name, stat_name, value)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE value = %s
            """,
            (service_name, stat_name, new_value, new_value),
        )
        conn.commit()
        conn.close()
        return jsonify({"service": service_name, "stat": stat_name, "value": new_value, "action": "set"})

    elif "increment" in data:
        # Relative increment (or decrement if negative)
        increment = float(data["increment"])
        cursor.execute(
            """
            INSERT INTO service_stats (service_name, stat_name, value)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE value = value + %s
            """,
            (service_name, stat_name, increment, increment),
        )
        conn.commit()

        # Fetch the new value to return
        cursor.execute(
            "SELECT value FROM service_stats WHERE service_name = %s AND stat_name = %s",
            (service_name, stat_name),
        )
        row = cursor.fetchone()
        conn.close()
        return jsonify({
            "service": service_name,
            "stat": stat_name,
            "value": row["value"] if row else increment,
            "action": "increment",
            "increment": increment,
        })

    else:
        conn.close()
        return jsonify({"error": "Body must contain 'value' or 'increment'"}), 400


@app.route("/stats/<service_name>/<stat_name>", methods=["DELETE"])
@require_api_key
def delete_service_stat(service_name, stat_name):
    """Delete a specific stat for a service.
    Usage: DELETE /stats/k5portfolio/totalvisits
    """
    service_name = service_name.lower().strip()
    stat_name = stat_name.lower().strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM service_stats WHERE service_name = %s AND stat_name = %s",
        (service_name, stat_name),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        return jsonify({"message": "Stat deleted", "service": service_name, "stat": stat_name})
    else:
        return jsonify({"error": "Stat not found"}), 404


def run_api():
    port = int(os.environ.get("PORT", 80))  # Get the port from environment variable
    print(f"[INFO] Starting API server on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
