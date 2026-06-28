import os

# Apply gevent monkey patching before any other imports
if os.environ.get("PORT"):  # Only patch if running on Heroku/Production
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



apps = {}
for filename in os.listdir(WEBAPPS_DIR):
    if filename.endswith(".py"):
        name = filename[:-3]
        path = os.path.join(WEBAPPS_DIR, filename)
        app = load_flask_app(path)
        if app:
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
