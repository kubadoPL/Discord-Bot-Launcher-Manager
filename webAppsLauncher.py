import os

# gevent monkey patching is OFF by default. With patch_all() every thread
# became a greenlet, so a blocking MySQL connect (C extension, not gevent-aware)
# or heavy JSON serialization froze the Icecast streaming loop in StreamerApi
# along with the HTTP handlers. The web dyno now runs gunicorn's gthread worker
# (see Procfile) and the streaming loop lives in a real OS thread.
# Set USE_GEVENT=1 to restore the old behaviour.
if os.environ.get("USE_GEVENT") == "1":
    from gevent import monkey

    monkey.patch_all()

import importlib.util
import sys

# Set the script and parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, ".."))

# Add script directory to sys.path so 'api' is importable
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Set working directory to project root
os.chdir(script_dir)
print("Working directory set to:", os.getcwd())


from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from flask import Flask, request, jsonify
from flask import render_template
from flask_cors import CORS

WEBAPPS_DIR = "webApps"

main_app = Flask(__name__, template_folder=script_dir + "/api/templates")

CORS(main_app)  # enable CORS only for radio-gaming.stream


# Security headers middleware
@main_app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@main_app.route("/")
def index():
    return render_template("/main.html")  # "Main app root"


def load_flask_app(filepath):
    module_name = os.path.basename(filepath)[:-3]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so other webApps can access the SAME instance
    # (e.g. StreamerApi needs DiscordAuthChatApi's live user_sessions)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return getattr(module, "app", None)



# gzip/br for JSON and text responses (status/queue/chat payloads shrink 4-6x).
# Optional: if flask-compress is missing we just serve uncompressed.
try:
    from flask_compress import Compress as _Compress
except ImportError:  # pragma: no cover
    _Compress = None
    print("[WARN] flask-compress not installed; responses will not be compressed")


def enable_compression(flask_app):
    if _Compress is None:
        return
    flask_app.config.setdefault("COMPRESS_MIN_SIZE", 1024)
    flask_app.config.setdefault("COMPRESS_LEVEL", 3)  # JSON: ~same size as 6 at half the CPU
    _Compress(flask_app)


enable_compression(main_app)

# When start_web.sh runs the streaming engine as its own process it sets
# STREAMER_UPSTREAM (http://127.0.0.1:PORT). StreamerApi is then NOT imported
# here; /StreamerApi/* is reverse-proxied to that process instead, so the
# Icecast feed never competes with these HTTP handlers for the GIL.
STREAMER_UPSTREAM = os.environ.get("STREAMER_UPSTREAM", "").rstrip("/")

apps = {}
for filename in os.listdir(WEBAPPS_DIR):
    if filename.endswith(".py"):
        name = filename[:-3]
        path = os.path.join(WEBAPPS_DIR, filename)
        if name == "StreamerApi" and STREAMER_UPSTREAM:
            from api.streamer_proxy import StreamerProxy
            apps[f"/{name}"] = StreamerProxy(STREAMER_UPSTREAM)
            print(f"[INFO] /StreamerApi proxied to {STREAMER_UPSTREAM} (engine runs in its own process)")
            continue
        app = load_flask_app(path)
        if app:
            enable_compression(app)
            apps[f"/{name}"] = app
        else:
            print(f"[ERROR] No Flask app found in {filename}")


application = DispatcherMiddleware(main_app, apps)


if __name__ == "__main__":
    run_simple(
        "0.0.0.0",
        int(os.environ.get("PORT", 5000)),
        application,
        use_reloader=True,
        threaded=True,
    )
