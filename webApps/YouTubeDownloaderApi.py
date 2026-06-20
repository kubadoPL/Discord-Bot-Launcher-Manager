"""
YouTubeDownloaderApi.py — YouTube to MP3/MP4 Download Service
===============================================================
A Flask app that provides a REST API for downloading YouTube videos as MP3 or MP4.
Uses yt-dlp for extraction and ffmpeg for conversion.

Auto-discovered by webAppsLauncher.py → mounted at /YouTubeDownloaderApi/
Frontend served at /YouTubeDownloaderApi/ (index.html)
API endpoints under /YouTubeDownloaderApi/api/...
"""

import os
import sys
import threading
import time
import uuid
import shutil
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from queue import Queue

from flask import Flask, request, jsonify, send_file, send_from_directory, make_response
from flask_cors import cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from api.config import RESTRICT_CORS
from api.FunctionsModule import get_db_connection, create_service_stats_table

app = Flask(
    __name__,
    static_folder=os.path.join(parent_dir, "api", "templates", "ytdownloader"),
    static_url_path="/static",
)

_CORS_ORIGINS = (
    ["https://k5studio.dev", "https://k5-studio.dev", "https://radio-gaming.stream"]
    if RESTRICT_CORS
    else "*"
)
CORS_OPTIONS = {
    "origins": _CORS_ORIGINS,
    "allow_headers": ["Content-Type"],
    "methods": ["GET", "POST", "OPTIONS"],
}

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

# ─── Global Persistent Stats (saved to DB, same pattern as MSForms) ────────────
YTDL_SERVICE_NAME = "ytdownloader"
_global_stats_queue = Queue()
_global_stats_cache = {}  # In-memory cache of global stats
_global_stats_cache_lock = threading.Lock()


def _global_stats_worker():
    """Background thread that increments stats in the database."""
    while True:
        task = _global_stats_queue.get()
        if task is None:
            break
        stat_name, amount = task
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO service_stats (service_name, stat_name, value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE value = value + %s
                """,
                (YTDL_SERVICE_NAME, stat_name, amount, amount),
            )
            conn.commit()
            conn.close()
            with _global_stats_cache_lock:
                _global_stats_cache[stat_name] = _global_stats_cache.get(stat_name, 0) + amount
        except Exception as e:
            print(f"[YTDownloader Stats] Error saving {stat_name}: {e}")
        finally:
            _global_stats_queue.task_done()


_global_stats_thread = threading.Thread(target=_global_stats_worker, daemon=True, name="ytdl-global-stats")
_global_stats_thread.start()


def _increment_stat(stat_name, amount=1):
    """Enqueue a global stat increment."""
    _global_stats_queue.put((stat_name, amount))


def _load_global_stats():
    """Fetch all global stats from DB (startup only)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT stat_name, value FROM service_stats WHERE service_name = %s",
            (YTDL_SERVICE_NAME,),
        )
        rows = cursor.fetchall()
        conn.close()
        return {row["stat_name"]: row["value"] for row in rows}
    except Exception as e:
        print(f"[YTDownloader Stats] Error loading: {e}")
        return {}


def _init_stats():
    try:
        create_service_stats_table()
        loaded = _load_global_stats()
        with _global_stats_cache_lock:
            _global_stats_cache.update(loaded)
        print(f"[YTDownloader] Stats ready. Current: {loaded}")
    except Exception as e:
        print(f"[YTDownloader] Warning: Could not init stats: {e}")


threading.Thread(target=_init_stats, daemon=True, name="ytdl-stats-init").start()


# ─── Online Users Tracking ─────────────────────────────────────────────────────
_online_users = {}  # session_id -> last_heartbeat_timestamp
_online_lock = threading.Lock()
ONLINE_TIMEOUT = 30  # seconds


def _cleanup_online():
    now = time.time()
    with _online_lock:
        stale = [sid for sid, ts in _online_users.items() if now - ts > ONLINE_TIMEOUT]
        for sid in stale:
            del _online_users[sid]


def _get_online_count():
    _cleanup_online()
    with _online_lock:
        return len(_online_users)


# ─── Download Storage ─────────────────────────────────────────────────────────
DOWNLOAD_DIR = os.path.join(script_dir, "yt_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Track active downloads: job_id -> {status, progress, title, filename, format, error, created_at}
_jobs = {}
_jobs_lock = threading.Lock()

# Auto-cleanup: delete files older than 10 minutes
CLEANUP_INTERVAL = 120  # seconds
FILE_MAX_AGE = 600  # seconds (10 min)


def _cleanup_loop():
    """Background thread: periodically remove old downloads."""
    while True:
        try:
            now = time.time()
            # Clean up files
            if os.path.exists(DOWNLOAD_DIR):
                for fname in os.listdir(DOWNLOAD_DIR):
                    fpath = os.path.join(DOWNLOAD_DIR, fname)
                    if os.path.isfile(fpath):
                        age = now - os.path.getmtime(fpath)
                        if age > FILE_MAX_AGE:
                            try:
                                os.remove(fpath)
                            except Exception:
                                pass

            # Clean up old job entries
            with _jobs_lock:
                expired = [
                    jid
                    for jid, j in _jobs.items()
                    if now - j.get("created_at", now) > FILE_MAX_AGE * 2
                ]
                for jid in expired:
                    _jobs.pop(jid, None)

        except Exception:
            pass
        time.sleep(CLEANUP_INTERVAL)


threading.Thread(target=_cleanup_loop, daemon=True).start()


def _sanitize_filename(name):
    """Remove characters that are unsafe for filenames."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip('. ')
    return name[:200] if name else "download"


# ─── Cookie Support (shared with StreamerApi if available) ────────────────────
COOKIE_FILE_PATH = os.path.join(script_dir, "streamer_data", "cookies.txt")


def _get_cookie_opts():
    """Return cookiefile dict if cookies.txt exists."""
    if os.path.isfile(COOKIE_FILE_PATH):
        return {"cookiefile": COOKIE_FILE_PATH}
    return {}


# ─── API Routes ───────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the frontend."""
    return send_from_directory(
        os.path.join(parent_dir, "api", "templates", "ytdownloader"),
        "index.html",
    )


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static frontend files (CSS, JS)."""
    static_dir = os.path.join(parent_dir, "api", "templates", "ytdownloader")
    return send_from_directory(static_dir, filename)


@app.route("/api/info", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def get_video_info():
    """Get video metadata (title, thumbnail, duration, formats) without downloading."""
    data = request.get_json(silent=True)
    if not data or not data.get("url"):
        return jsonify({"error": "Missing 'url' parameter"}), 400

    url = data["url"].strip()

    # Basic URL validation
    if not (
        "youtube.com" in url
        or "youtu.be" in url
        or "music.youtube.com" in url
    ):
        return jsonify({"error": "Only YouTube URLs are supported"}), 400

    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            **_get_cookie_opts(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if "entries" in info:
            info = info["entries"][0]

        # Extract available qualities
        formats_list = []
        seen_res = set()
        for fmt in info.get("formats", []):
            if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
                height = fmt.get("height")
                if height and height not in seen_res:
                    seen_res.add(height)
                    formats_list.append({
                        "quality": f"{height}p",
                        "height": height,
                        "ext": fmt.get("ext", "mp4"),
                    })

        # Sort by quality descending
        formats_list.sort(key=lambda x: x["height"], reverse=True)

        # If no combined formats, check video-only formats
        if not formats_list:
            for fmt in info.get("formats", []):
                if fmt.get("vcodec") != "none":
                    height = fmt.get("height")
                    if height and height not in seen_res:
                        seen_res.add(height)
                        formats_list.append({
                            "quality": f"{height}p",
                            "height": height,
                            "ext": "mp4",
                        })
            formats_list.sort(key=lambda x: x["height"], reverse=True)

        duration = info.get("duration", 0)
        duration_str = ""
        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            if mins >= 60:
                hours = mins // 60
                mins = mins % 60
                duration_str = f"{hours}:{mins:02d}:{secs:02d}"
            else:
                duration_str = f"{mins}:{secs:02d}"

        return jsonify({
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": duration,
            "duration_formatted": duration_str,
            "uploader": info.get("uploader", "Unknown"),
            "view_count": info.get("view_count", 0),
            "formats": formats_list,
            "url": url,
        })

    except Exception as e:
        error_msg = str(e)
        if "Sign in" in error_msg or "bot" in error_msg.lower():
            error_msg = "YouTube is blocking this request. Try again later."
        return jsonify({"error": f"Failed to fetch video info: {error_msg}"}), 500


@app.route("/api/download", methods=["POST"])
@limiter.limit("10 per minute")
@cross_origin(**CORS_OPTIONS)
def start_download():
    """Start an async download job. Returns a job_id to poll status."""
    data = request.get_json(silent=True)
    if not data or not data.get("url"):
        return jsonify({"error": "Missing 'url' parameter"}), 400

    url = data["url"].strip()
    fmt = data.get("format", "mp3")  # "mp3" or "mp4"
    quality = data.get("quality", "720")  # for mp4: "360", "480", "720", "1080"

    if fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Format must be 'mp3' or 'mp4'"}), 400

    if not ("youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url):
        return jsonify({"error": "Only YouTube URLs are supported"}), 400

    # Track stats
    _increment_stat("downloads_started")
    if fmt == "mp3":
        _increment_stat("mp3_started")
    else:
        _increment_stat("mp4_started")

    job_id = str(uuid.uuid4())[:8]

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "title": "",
            "filename": "",
            "format": fmt,
            "error": None,
            "created_at": time.time(),
            "downloaded_bytes": 0,
            "total_bytes": 0,
        }

    # Run download in background thread
    threading.Thread(
        target=_download_worker,
        args=(job_id, url, fmt, quality),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id, "status": "starting"})


def _download_worker(job_id, url, fmt, quality):
    """Background worker: download and convert the video."""
    import yt_dlp

    try:
        # Progress callback
        def progress_hook(d):
            with _jobs_lock:
                if job_id not in _jobs:
                    return
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    if total > 0:
                        _jobs[job_id]["progress"] = int((downloaded / total) * 90)
                    _jobs[job_id]["status"] = "downloading"
                    _jobs[job_id]["downloaded_bytes"] = downloaded
                    _jobs[job_id]["total_bytes"] = total
                elif d.get("status") == "finished":
                    _jobs[job_id]["progress"] = 90
                    _jobs[job_id]["status"] = "converting"

        # First pass: get title for filename
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            **_get_cookie_opts(),
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            if "entries" in info:
                info = info["entries"][0]

        title = info.get("title", "download")
        uploader = info.get("uploader", "")
        if uploader and uploader.endswith(" - Topic"):
            uploader = uploader[:-8]

        clean_title = _sanitize_filename(title)

        with _jobs_lock:
            _jobs[job_id]["title"] = title

        output_base = os.path.join(DOWNLOAD_DIR, f"{job_id}_{clean_title}")

        if fmt == "mp3":
            output_file = f"{output_base}.mp3"
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_base + ".%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "progress_hooks": [progress_hook],
                **_get_cookie_opts(),
            }
        else:
            # MP4
            output_file = f"{output_base}.mp4"
            height = int(quality) if quality.isdigit() else 720
            ydl_opts = {
                "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
                "outtmpl": output_base + ".%(ext)s",
                "merge_output_format": "mp4",
                "postprocessors": [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "progress_hooks": [progress_hook],
                **_get_cookie_opts(),
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the output file (extension might vary)
        found_file = None
        if os.path.exists(output_file):
            found_file = output_file
        else:
            # Search for any file with the job_id prefix
            for fname in os.listdir(DOWNLOAD_DIR):
                if fname.startswith(f"{job_id}_"):
                    candidate = os.path.join(DOWNLOAD_DIR, fname)
                    if fmt == "mp3" and fname.endswith(".mp3"):
                        found_file = candidate
                        break
                    elif fmt == "mp4" and fname.endswith(".mp4"):
                        found_file = candidate
                        break
            # Fallback: any matching file
            if not found_file:
                for fname in os.listdir(DOWNLOAD_DIR):
                    if fname.startswith(f"{job_id}_"):
                        found_file = os.path.join(DOWNLOAD_DIR, fname)
                        break

        if found_file and os.path.exists(found_file):
            with _jobs_lock:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["progress"] = 100
                _jobs[job_id]["filename"] = os.path.basename(found_file)
            # Track successful conversion stats
            _increment_stat("downloads_completed")
            if fmt == "mp3":
                _increment_stat("mp3_converted")
            else:
                _increment_stat("mp4_converted")
        else:
            with _jobs_lock:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = "Output file not found after conversion"
            _increment_stat("downloads_failed")

    except Exception as e:
        error_msg = str(e)
        if "Sign in" in error_msg:
            error_msg = "YouTube is blocking this request. Try again later."
        with _jobs_lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = error_msg
        _increment_stat("downloads_failed")


@app.route("/api/status/<job_id>", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def get_job_status(job_id):
    """Poll download job status."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "title": job["title"],
        "format": job["format"],
        "error": job["error"],
        "filename": job.get("filename", ""),
        "downloaded_bytes": job.get("downloaded_bytes", 0),
        "total_bytes": job.get("total_bytes", 0),
    })


@app.route("/api/file/<job_id>", methods=["GET"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def download_file(job_id):
    """Download the completed file."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "File not ready"}), 400

    filepath = os.path.join(DOWNLOAD_DIR, job["filename"])
    if not os.path.exists(filepath):
        return jsonify({"error": "File expired or not found"}), 404

    # Build a clean download filename (without the job_id prefix)
    clean_name = job["filename"]
    if clean_name.startswith(f"{job_id}_"):
        clean_name = clean_name[len(f"{job_id}_"):]

    # Sanitize filename — remove characters that break Content-Disposition header
    # Keep only safe chars: alphanumeric, spaces, hyphens, underscores, dots, parens
    clean_name = re.sub(r'[^\w\s\-\.\(\)]', '', clean_name)
    # Collapse multiple spaces/underscores
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    if not clean_name:
        clean_name = f"download.{job['format']}"

    # Track file download stat
    if job["format"] == "mp3":
        _increment_stat("mp3_downloaded")
    else:
        _increment_stat("mp4_downloaded")

    mimetype = "audio/mpeg" if job["format"] == "mp3" else "video/mp4"

    # Stream file with send_file, then override Content-Disposition with sanitized name
    response = send_file(
        filepath,
        mimetype=mimetype,
    )
    response.headers['Content-Disposition'] = f'attachment; filename="{clean_name}"'
    return response


# ─── Stats & Online Endpoints ─────────────────────────────────────────────────


@app.route("/api/stats", methods=["GET"])
@cross_origin(**CORS_OPTIONS)
def api_stats():
    """Return global stats and online count."""
    with _global_stats_cache_lock:
        global_stats = dict(_global_stats_cache)
    return jsonify({
        "global": global_stats,
        "online": _get_online_count(),
    })


@app.route("/api/heartbeat", methods=["POST"])
@limiter.limit("60 per minute")
@cross_origin(**CORS_OPTIONS)
def heartbeat():
    """Register a heartbeat from a connected client."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("sid", "")
    if not session_id:
        return jsonify({"error": "no sid"}), 400
    with _online_lock:
        _online_users[session_id] = time.time()
    return jsonify({"online": _get_online_count()})


@app.route("/api/track-visit", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def track_visit():
    """Track a page visit. Body: {is_new: true/false}"""
    data = request.get_json(silent=True) or {}
    _increment_stat("total_visits")
    if data.get("is_new"):
        _increment_stat("unique_visitors")
    return jsonify({"ok": True})


@app.route("/api/track-fetch", methods=["POST"])
@limiter.limit("30 per minute")
@cross_origin(**CORS_OPTIONS)
def track_fetch():
    """Track a video info fetch."""
    _increment_stat("videos_fetched")
    return jsonify({"ok": True})
