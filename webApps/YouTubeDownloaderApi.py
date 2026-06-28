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
import json
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
from api.config import RESTRICT_CORS, YTDL_PREFER_H264
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


# ─── Cookie Support (restore from DB, same as StreamerApi) ────────────────────
COOKIE_DIR = os.path.join(script_dir, "streamer_data")
os.makedirs(COOKIE_DIR, exist_ok=True)
COOKIE_FILE_PATH = os.path.join(COOKIE_DIR, "cookies.txt")


def _restore_cookies_from_db():
    """On startup, restore cookies.txt from database if local file is missing.
    Uses the same streamer_cookies table as StreamerApi."""
    if os.path.isfile(COOKIE_FILE_PATH):
        print("[YTDownloader Cookies] Local cookies.txt exists, skipping DB restore.")
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
            print(f"[YTDownloader Cookies] Restored cookies.txt from DB ({len(row[0])} bytes)")
        else:
            print("[YTDownloader Cookies] No cookies in DB.")
    except Exception as e:
        print(f"[YTDownloader Cookies] DB restore error: {e}")


# Restore cookies on module load (in background to not block startup)
threading.Thread(target=_restore_cookies_from_db, daemon=True, name="ytdl-cookie-restore").start()


def _get_cookie_opts():
    """Return cookiefile dict if cookies.txt exists."""
    if os.path.isfile(COOKIE_FILE_PATH):
        return {"cookiefile": COOKIE_FILE_PATH}
    return {}


def _get_base_ydl_opts():
    """Return base yt-dlp options with cookies and optimized player clients.
    Overrides the default authed client 'tv_downgraded' (which returns degraded
    formats — only 360p muxed for age-restricted videos) with full 'tv' client
    and other clients that return all DASH streams."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        **_get_cookie_opts(),
        "extractor_args": {
            "youtube": {
                # Use full 'tv' (not 'tv_downgraded') + web_safari + android_vr
                # to get all DASH format streams including higher resolutions
                "player_client": ["tv,web_safari,android_vr"],
            }
        },
    }
    return opts


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
    """Get video metadata. Auto-detects playlists and returns all entries."""
    data = request.get_json(silent=True)
    if not data or not data.get("url"):
        return jsonify({"error": "Missing 'url' parameter"}), 400

    url = data["url"].strip()

    # Basic URL validation
    is_youtube = "youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url
    is_spotify = "open.spotify.com" in url

    if not is_youtube and not is_spotify:
        return jsonify({"error": "Only YouTube and Spotify URLs are supported"}), 400

    # Spotify handling
    if is_spotify:
        try:
            return _handle_spotify_info(url)
        except Exception as e:
            return jsonify({"error": f"Failed to process Spotify link: {str(e)}"}), 500

    # Convert YouTube Music URLs to regular YouTube (Music API caps playlists)
    if "music.youtube.com" in url:
        url = url.replace("music.youtube.com", "www.youtube.com")

    # Strip si= tracking parameter (limits playlists to 100 items!)
    if "si=" in url:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        params.pop("si", None)
        url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    # Detect playlist URLs
    is_playlist = "?list=" in url or "&list=" in url or "/playlist" in url

    try:
        import yt_dlp

        if is_playlist:
            return _handle_playlist_info(url)
        else:
            return _handle_single_video_info(url)

    except Exception as e:
        error_msg = str(e)
        if "Sign in" in error_msg or "bot" in error_msg.lower():
            error_msg = "YouTube is blocking this request. Try again later."
        return jsonify({"error": f"Failed to fetch video info: {error_msg}"}), 500


def _scrape_spotify_tracks(url):
    """Extract track names from a Spotify playlist/album/track URL via scraping.
    Ported from StreamerApi._get_spotify_tracks().
    """
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
        elif "track" in url:
            target_url = url.replace(
                "open.spotify.com/track/", "open.spotify.com/embed/track/"
            )

        response = requests.get(
            target_url,
            headers={"User-Agent": "Mozilla/5.0 K5StudioYTDownloader/1.0"},
            timeout=15,
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

                # Get playlist/album title
                entity_title = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("state", {})
                    .get("data", {})
                    .get("entity", {})
                    .get("title", "")
                ) or (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("state", {})
                    .get("data", {})
                    .get("name", "")
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

                            duration_ms = t.get("duration", 0) or t.get("duration_ms", 0) or 0

                            tracks.append({
                                "name": name,
                                "artist": artists_str,
                                "full": f"{artists_str} - {name}" if artists_str else name,
                                "search": f"{name} {artists_str}" if artists_str else name,
                                "duration": duration_ms / 1000 if duration_ms else 0,
                            })
                    if tracks:
                        return entity_title, tracks
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
                full = f"{clean_artist} - {clean_name}"
                if full not in seen:
                    if not any(
                        x in full.lower()
                        for x in ["spotify", "log in", "sign up", "terms of"]
                    ):
                        tracks.append({
                            "name": clean_name,
                            "artist": clean_artist,
                            "full": full,
                            "search": f"{clean_name} {clean_artist}",
                            "duration": 0,
                        })
                        seen.add(full)
            if tracks:
                return "Spotify Playlist", tracks

    except Exception as e:
        print(f"Spotify Scrape Error: {e}")
    return "", []


def _handle_spotify_info(url):
    """Handle Spotify URLs: scrape tracks and return as playlist-type response."""
    entity_title, tracks = _scrape_spotify_tracks(url)

    if not tracks:
        return jsonify({"error": "Could not extract tracks from Spotify. The link may be private or invalid."}), 400

    # Determine if it's a single track or a collection
    is_single = "/track/" in url
    is_album = "/album/" in url

    if is_single and len(tracks) == 1:
        t = tracks[0]
        # For single tracks, resolve via YouTube search and return as single video
        import yt_dlp
        search_query = f"ytsearch1:{t['search']}"
        ydl_opts = {
            **_get_base_ydl_opts(),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        if info and "entries" in info and info["entries"]:
            video = info["entries"][0]
            return _handle_single_video_info(video.get("webpage_url", video.get("url", "")))

        return jsonify({"error": "Could not find this track on YouTube"}), 404

    # For playlists/albums, return as playlist type with YouTube search URLs
    videos = []
    total_duration = 0
    for i, t in enumerate(tracks):
        dur = t.get("duration", 0)
        total_duration += dur
        videos.append({
            "title": t["full"],
            "url": f"ytsearch1:{t['search']}",
            "thumbnail": "",
            "duration": dur,
            "duration_formatted": _format_duration(dur),
            "uploader": t.get("artist", ""),
        })

    total_mins = int(total_duration // 60)
    total_str = f"{total_mins // 60}h {total_mins % 60}m" if total_mins >= 60 else f"{total_mins}m"

    label = "Album" if is_album else "Playlist"

    return jsonify({
        "type": "playlist",
        "title": entity_title or f"Spotify {label}",
        "thumbnail": "",
        "uploader": "Spotify",
        "video_count": len(videos),
        "total_duration": total_duration,
        "total_duration_formatted": total_str,
        "videos": videos,
        "url": url,
        "source": "spotify",
    })



def _handle_playlist_info(url):
    """Extract playlist entries using flat extraction (fast, like StreamerApi)."""
    import yt_dlp

    ydl_opts = {
        **_get_base_ydl_opts(),
        "ignoreerrors": True,
        "extract_flat": "in_playlist",
        "playlist-end": 500,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return jsonify({"error": "Could not load playlist"}), 500

    entries = info.get("entries", [])
    if not entries:
        return jsonify({"error": "Playlist is empty or unavailable"}), 400

    videos = []
    for video in entries:
        if video is None:
            continue

        entry_url = video.get("url", "")
        title = video.get("title", "Unknown Title")

        # Build proper YouTube URL from ie_key/id (same as StreamerApi)
        if video.get("ie_key") == "Youtube":
            if entry_url and "youtube.com/watch" not in entry_url:
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"
        if not entry_url:
            vid_id = video.get("id", "")
            if vid_id:
                entry_url = f"https://www.youtube.com/watch?v={vid_id}"
            else:
                continue

        # Duration formatting
        duration = video.get("duration") or 0
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

        # Uploader / channel
        uploader = video.get("uploader") or video.get("channel") or ""
        if uploader.endswith(" - Topic"):
            uploader = uploader[:-8]

        videos.append({
            "title": title,
            "url": entry_url,
            "thumbnail": video.get("thumbnails", [{}])[-1].get("url", "") if video.get("thumbnails") else "",
            "duration": duration,
            "duration_formatted": duration_str,
            "uploader": uploader,
        })

    # Estimate total duration
    total_duration = sum(v["duration"] for v in videos if v["duration"])
    total_mins = int(total_duration // 60)
    total_str = f"{total_mins // 60}h {total_mins % 60}m" if total_mins >= 60 else f"{total_mins}m"

    return jsonify({
        "type": "playlist",
        "title": info.get("title", "Unknown Playlist"),
        "thumbnail": info.get("thumbnails", [{}])[-1].get("url", "") if info.get("thumbnails") else (videos[0]["thumbnail"] if videos else ""),
        "uploader": info.get("uploader") or info.get("channel") or "",
        "video_count": len(videos),
        "total_duration": total_duration,
        "total_duration_formatted": total_str,
        "videos": videos,
        "url": url,
    })


def _format_duration(duration):
    """Format seconds to human-readable duration string."""
    if not duration:
        return ""
    mins = int(duration // 60)
    secs = int(duration % 60)
    if mins >= 60:
        hours = mins // 60
        mins = mins % 60
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def _handle_single_video_info(url):
    """Extract single video metadata (original behavior)."""
    import yt_dlp

    ydl_opts = {
        **_get_base_ydl_opts(),
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if "entries" in info:
        info = info["entries"][0]

    def _extract_heights(video_info):
        """Extract unique video heights from format list."""
        flist = []
        seen = set()
        for fmt in video_info.get("formats", []):
            vcodec = fmt.get("vcodec") or "none"
            if vcodec != "none":
                height = fmt.get("height")
                if height and height not in seen:
                    seen.add(height)
                    flist.append({
                        "quality": f"{height}p",
                        "height": height,
                        "ext": fmt.get("ext", "mp4"),
                    })
        flist.sort(key=lambda x: x["height"], reverse=True)
        return flist, seen

    formats_list, seen_res = _extract_heights(info)

    # Retry for age-restricted videos: yt-dlp defaults to 'tv_downgraded' with cookies
    # which returns degraded formats (only 360p muxed). Try full player clients to get
    # DASH streams with all resolutions.
    if len(formats_list) <= 1:
        retry_clients = ["tv,android_vr,web_creator,ios"]
        try:
            retry_opts = {
                **_get_base_ydl_opts(),
                "noplaylist": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": retry_clients,
                    }
                },
            }
            with yt_dlp.YoutubeDL(retry_opts) as ydl2:
                info2 = ydl2.extract_info(url, download=False)
            if "entries" in info2:
                info2 = info2["entries"][0]

            retry_formats, retry_seen = _extract_heights(info2)
            if len(retry_formats) > len(formats_list):
                # Retry gave more formats — use it
                info = info2
                formats_list = retry_formats
                seen_res = retry_seen
                print(f"[YTDownloader] Retry with {retry_clients} found {len(formats_list)} qualities")
        except Exception as e:
            print(f"[YTDownloader] Retry extraction failed: {e}")

    duration = info.get("duration", 0)
    duration_str = _format_duration(duration)

    # Estimate file sizes
    all_formats = info.get("formats", [])
    best_audio_size = 0
    for fmt in all_formats:
        if fmt.get("acodec") != "none" and (fmt.get("vcodec") == "none" or fmt.get("vcodec") is None):
            fs = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if fs > best_audio_size:
                best_audio_size = fs
    if best_audio_size == 0 and duration:
        best_audio_size = int(duration * 128 * 1000 / 8)

    for fitem in formats_list:
        h = fitem["height"]
        best_size = 0
        for fmt in all_formats:
            if fmt.get("height") == h:
                fs = fmt.get("filesize") or fmt.get("filesize_approx") or 0
                if fs > best_size:
                    best_size = fs
        fitem["filesize_approx"] = best_size + best_audio_size if best_size else 0

    # Upload date
    upload_date_raw = info.get("upload_date", "")
    upload_date_formatted = ""
    if upload_date_raw and len(upload_date_raw) == 8:
        try:
            from datetime import datetime
            dt = datetime.strptime(upload_date_raw, "%Y%m%d")
            upload_date_formatted = dt.strftime("%b %d, %Y")
        except Exception:
            upload_date_formatted = upload_date_raw

    description_raw = info.get("description", "") or ""
    description_short = description_raw[:300]
    if len(description_raw) > 300:
        description_short += "..."

    return jsonify({
        "type": "video",
        "title": info.get("title", "Unknown"),
        "thumbnail": info.get("thumbnail", ""),
        "duration": duration,
        "duration_formatted": duration_str,
        "uploader": info.get("uploader", "Unknown"),
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "upload_date": upload_date_formatted,
        "description": description_short,
        "categories": info.get("categories", []),
        "formats": formats_list,
        "mp3_size_approx": best_audio_size,
        "url": url,
    })


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
    override_title = data.get("title", "").strip()  # optional: override filename

    if fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Format must be 'mp3' or 'mp4'"}), 400

    if not ("youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url or url.startswith("ytsearch")):
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
        args=(job_id, url, fmt, quality, override_title),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id, "status": "starting"})


def _sanitize_filename(title):
    """Sanitize a video title into a safe filename for the filesystem."""
    # Remove emoji and non-BMP Unicode characters (block chars, special symbols)
    clean = re.sub(r'[^\x00-\x7F]', '', title)
    # Keep only alphanumeric, spaces, hyphens, underscores, dots, parens
    clean = re.sub(r'[^\w\s\-\.\(\)]', '', clean)
    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Limit length (filesystems have path limits)
    clean = clean[:100]
    # Fallback if nothing left
    if not clean:
        clean = "download"
    return clean


def _download_worker(job_id, url, fmt, quality, override_title=""):
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
            **_get_base_ydl_opts(),
            "noplaylist": True,
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            if "entries" in info:
                info = info["entries"][0]

        title = override_title if override_title else info.get("title", "download")
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
                **_get_base_ydl_opts(),
                "format": "bestaudio/best",
                "outtmpl": output_base + ".%(ext)s",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    }
                ],
                "noplaylist": True,
                "progress_hooks": [progress_hook],
            }
        else:
            # MP4
            output_file = f"{output_base}.mp4"
            height = int(quality) if quality.isdigit() else 720

            if YTDL_PREFER_H264:
                # Prefer H.264+AAC = fast remux, no transcoding
                fmt_str = (
                    f"bestvideo[height<={height}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/best"
                )
            else:
                # Allow VP9/Opus = better compression, slower conversion
                fmt_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

            ydl_opts = {
                **_get_base_ydl_opts(),
                "format": fmt_str,
                "outtmpl": output_base + ".%(ext)s",
                "merge_output_format": "mp4",
                "postprocessors": [
                    {
                        "key": "FFmpegVideoConvertor",
                        "preferedformat": "mp4",
                    }
                ],
                "noplaylist": True,
                "progress_hooks": [progress_hook],
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
    """Return global stats, online count, and storage usage."""
    with _global_stats_cache_lock:
        global_stats = dict(_global_stats_cache)

    # Calculate current download directory usage
    storage_bytes = 0
    file_count = 0
    try:
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(fpath):
                storage_bytes += os.path.getsize(fpath)
                file_count += 1
    except OSError:
        pass

    # Heroku disk info
    try:
        disk = shutil.disk_usage(DOWNLOAD_DIR)
        disk_total = disk.total
        disk_free = disk.free
    except OSError:
        disk_total = 0
        disk_free = 0

    return jsonify({
        "global": global_stats,
        "online": _get_online_count(),
        "storage": {
            "used_bytes": storage_bytes,
            "file_count": file_count,
            "disk_total": disk_total,
            "disk_free": disk_free,
        },
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
