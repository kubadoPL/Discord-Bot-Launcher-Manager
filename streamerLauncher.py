"""Entry point for the streaming engine when it runs as its own process.

    gunicorn ... --bind 127.0.0.1:5055 streamerLauncher:application

Only StreamerApi is loaded here (no chat / downloader / K5 apps). Session and
admin checks fall back to the database because DiscordAuthChatApi's in-memory
session store lives in the web process. The web process proxies
/StreamerApi/* to this one (api/streamer_proxy.py) and fetches /public/status
for the radio tick, so nothing changes for the frontend.
"""
import importlib.util
import os
import sys

os.environ.setdefault("STREAMER_STANDALONE", "1")

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)
os.chdir(script_dir)

_path = os.path.join(script_dir, "webApps", "StreamerApi.py")
_spec = importlib.util.spec_from_file_location("StreamerApi", _path)
_module = importlib.util.module_from_spec(_spec)
sys.modules["StreamerApi"] = _module
_spec.loader.exec_module(_module)

app = _module.app

try:
    from flask_compress import Compress as _Compress
    app.config.setdefault("COMPRESS_MIN_SIZE", 1024)
    app.config.setdefault("COMPRESS_LEVEL", 3)
    _Compress(app)
except ImportError:  # pragma: no cover
    print("[WARN] flask-compress not installed; engine responses will not be compressed")

application = app
print("[INFO] StreamerApi engine process ready (standalone mode)")

if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple("127.0.0.1", int(os.environ.get("STREAMER_PORT", 5055)), application, threaded=True)
