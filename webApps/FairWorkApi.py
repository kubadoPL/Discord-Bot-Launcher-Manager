"""
FairWorkApi – data store for the FairWork desktop app
=====================================================
FairWork (https://github.com/kubadoPL/FairWork) runs on the user's own PC: it
tracks time on a Discord voice channel, keeps the sessions in a local SQLite
file and shows the statistics itself. This API is only the optional copy of
those sessions: the app sends them here and can read them back (after a
reinstall, or on a second computer). There is no page, no login and no
tracking logic on the server.

Auth
----
Every install generates a random sync key and sends it as
``Authorization: Bearer <key>``. Only its SHA-256 is stored; the key *is* the
account – whoever has it can read and write that data set, nobody else can.

Routes (mounted under /FairWorkApi)
-----------------------------------
    POST   /sessions   {"sessions": [{uid, kind, started_at, last_seen_at, ended_at,
                        guild_id, channel_id}], "profile": {...}}   upsert by uid
                       kind is "work" (default) or "break" (deafened while working)
    GET    /sessions   -> {"sessions": [...]}
    DELETE /sessions   wipe everything stored for this key

Timestamps are unix seconds (UTC).

Environment
-----------
    FAIRWORK_MAX_USERS      max number of sync keys (default: 200)
    FAIRWORK_MAX_SESSIONS   max sessions kept per key (default: 50000)
"""

import os
import re
import sys
import hashlib
import threading

# ── Path setup ────────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from api.FunctionsModule import get_db_connection

# ── Config ────────────────────────────────────────────────────────────────────
MAX_USERS = int(os.environ.get("FAIRWORK_MAX_USERS", "200"))
MAX_SESSIONS = int(os.environ.get("FAIRWORK_MAX_SESSIONS", "50000"))
MAX_BATCH = 300
MAX_TS = 4102444800  # 2100-01-01, sanity bound for timestamps

# ── Flask App (no CORS on purpose: browsers have no business here) ────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_UID_RE = re.compile(r"^[0-9a-f]{32}$")
_ID_RE = re.compile(r"^\d{1,21}$")


# ── Database ──────────────────────────────────────────────────────────────────
_tables_ready = False
_tables_lock = threading.Lock()


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with _tables_lock:
        if _tables_ready:
            return
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `fairwork_owners` (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    key_hash CHAR(64) NOT NULL UNIQUE,
                    discord_user_id VARCHAR(32) NULL,
                    name VARCHAR(128) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync_at TIMESTAMP NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `fairwork_sessions` (
                    owner_id BIGINT NOT NULL,
                    uid CHAR(32) NOT NULL,
                    kind VARCHAR(8) NOT NULL DEFAULT 'work',
                    guild_id VARCHAR(32) NULL,
                    channel_id VARCHAR(32) NULL,
                    started_at BIGINT NOT NULL,
                    last_seen_at BIGINT NOT NULL,
                    ended_at BIGINT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (owner_id, uid),
                    INDEX idx_owner_started (owner_id, started_at)
                )
            """)
            conn.commit()
            # Tables created before breaks existed have no `kind` column yet.
            cursor.execute("SHOW COLUMNS FROM `fairwork_sessions` LIKE 'kind'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE `fairwork_sessions` ADD COLUMN kind VARCHAR(8) NOT NULL DEFAULT 'work' AFTER uid")
                conn.commit()
        finally:
            conn.close()
        _tables_ready = True


def _bearer_key():
    """The sync key from the Authorization header, or None if missing / malformed."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    key = header[7:].strip()
    return key if _KEY_RE.match(key) else None


def _owner_id(cursor, key, create):
    """Resolve a sync key to its owner row. Returns (owner_id | None, error | None)."""
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    cursor.execute("SELECT id FROM `fairwork_owners` WHERE key_hash = %s", (key_hash,))
    row = cursor.fetchone()
    if row:
        return row["id"], None
    if not create:
        return None, None
    cursor.execute("SELECT COUNT(*) AS n FROM `fairwork_owners`")
    if cursor.fetchone()["n"] >= MAX_USERS:
        return None, "server_full"
    cursor.execute("INSERT INTO `fairwork_owners` (key_hash) VALUES (%s)", (key_hash,))
    return cursor.lastrowid, None


def _clean_id(value):
    value = str(value) if value is not None else ""
    return value if _ID_RE.match(value) else None


def _clean_session(raw):
    """Validate one session from the client. Returns a tuple for SQL or None."""
    if not isinstance(raw, dict):
        return None
    uid = raw.get("uid")
    started, seen, ended = raw.get("started_at"), raw.get("last_seen_at"), raw.get("ended_at")
    if not isinstance(uid, str) or not _UID_RE.match(uid):
        return None
    for value in (started, seen):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < MAX_TS:
            return None
    if ended is not None and (isinstance(ended, bool) or not isinstance(ended, int) or not 0 < ended < MAX_TS):
        return None
    if seen < started or (ended is not None and ended < started):
        return None
    kind = "break" if raw.get("kind") == "break" else "work"
    return uid, kind, _clean_id(raw.get("guild_id")), _clean_id(raw.get("channel_id")), started, seen, ended


# ══════════════════════════════════════════════════════════════════════════════
#                              ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return jsonify({"service": "FairWork API", "status": "online", "role": "data store for the FairWork desktop app"})


@app.route("/sessions", methods=["POST"])
def push_sessions():
    """Store / update sessions (upsert by uid)."""
    key = _bearer_key()
    if not key:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
        return jsonify({"error": "bad_request"}), 400
    if len(data["sessions"]) > MAX_BATCH:
        return jsonify({"error": "batch_too_large", "max": MAX_BATCH}), 413

    sessions = [s for s in (_clean_session(raw) for raw in data["sessions"]) if s]
    rejected = len(data["sessions"]) - len(sessions)
    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    name = profile.get("name")
    name = name[:128] if isinstance(name, str) and name else None

    _ensure_tables()
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        owner_id, error = _owner_id(cursor, key, create=True)
        if error:
            return jsonify({"error": error}), 403

        if sessions:
            cursor.execute("SELECT COUNT(*) AS n FROM `fairwork_sessions` WHERE owner_id = %s", (owner_id,))
            if cursor.fetchone()["n"] + len(sessions) > MAX_SESSIONS + MAX_BATCH:
                return jsonify({"error": "storage_full"}), 403
            cursor.executemany("""
                INSERT INTO `fairwork_sessions`
                    (owner_id, uid, kind, guild_id, channel_id, started_at, last_seen_at, ended_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    kind = VALUES(kind), guild_id = VALUES(guild_id), channel_id = VALUES(channel_id),
                    started_at = VALUES(started_at), last_seen_at = VALUES(last_seen_at),
                    ended_at = VALUES(ended_at)
            """, [(owner_id,) + s for s in sessions])

        cursor.execute(
            "UPDATE `fairwork_owners` SET last_sync_at = NOW(), "
            "discord_user_id = COALESCE(%s, discord_user_id), name = COALESCE(%s, name) WHERE id = %s",
            (_clean_id(profile.get("discord_user_id")), name, owner_id),
        )
        conn.commit()
    finally:
        conn.close()
    # "kinds": this server stores work and break rows separately (the app waits for it).
    return jsonify({"ok": True, "stored": len(sessions), "rejected": rejected, "kinds": True})


@app.route("/sessions", methods=["GET"])
def pull_sessions():
    """Everything stored for this key."""
    key = _bearer_key()
    if not key:
        return jsonify({"error": "unauthorized"}), 401
    _ensure_tables()
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        owner_id, _ = _owner_id(cursor, key, create=False)
        rows = []
        if owner_id:
            cursor.execute(
                "SELECT uid, kind, guild_id, channel_id, started_at, last_seen_at, ended_at "
                "FROM `fairwork_sessions` WHERE owner_id = %s ORDER BY started_at LIMIT %s",
                (owner_id, MAX_SESSIONS + MAX_BATCH),
            )
            rows = cursor.fetchall()
    finally:
        conn.close()
    return jsonify({"sessions": [
        {
            "uid": r["uid"], "kind": r["kind"], "guild_id": r["guild_id"], "channel_id": r["channel_id"],
            "started_at": int(r["started_at"]), "last_seen_at": int(r["last_seen_at"]),
            "ended_at": int(r["ended_at"]) if r["ended_at"] is not None else None,
        }
        for r in rows
    ]})


@app.route("/sessions", methods=["DELETE"])
@limiter.limit("10 per minute")
def delete_sessions():
    """Forget everything stored for this key (the key itself too)."""
    key = _bearer_key()
    if not key:
        return jsonify({"error": "unauthorized"}), 401
    _ensure_tables()
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        owner_id, _ = _owner_id(cursor, key, create=False)
        if owner_id:
            cursor.execute("DELETE FROM `fairwork_sessions` WHERE owner_id = %s", (owner_id,))
            cursor.execute("DELETE FROM `fairwork_owners` WHERE id = %s", (owner_id,))
            conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "deleted": bool(owner_id)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
