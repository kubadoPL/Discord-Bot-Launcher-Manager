"""WebHostMost free-plan keep-alive.

WebHostMost deletes a free plan when its Client Area isn't visited for 45 days.
This app opens the Client Area every 2 days (and on demand at /status), reads the
"Time until suspension" timer and prints it to the logs.

The login form has an hCaptcha, so the app can't sign in with an e-mail and
password. It reuses the session of a browser where you are logged in instead:

    1. Log in at https://client.webhostmost.com with "Remember Me" ticked.
    2. Open DevTools > Network, reload clientarea.php, click the request and
       copy the whole "cookie" request header.
    3. Put that text in the WEBHOSTMOST_COOKIES environment variable.
    4. From the same request, copy the "user-agent" header into
       WEBHOSTMOST_USER_AGENT: the session may only work in that browser.

When the session expires, /status answers "session_expired" and the logs say so:
repeat the steps above.
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string
from flask_cors import cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from api.config import RESTRICT_CORS

_CORS_ORIGINS = ["https://radio-gaming.stream", "https://k5studio.dev"] if RESTRICT_CORS else "*"

BASE_URL = "https://client.webhostmost.com"
CLIENT_AREA_URL = BASE_URL + "/clientarea.php"
CHECK_EVERY_SECONDS = 2 * 24 * 60 * 60  # automatic check every 2 days
MIN_SECONDS_BETWEEN_CHECKS = 60  # /status opens the site at most once a minute
FIRST_CHECK_DELAY_SECONDS = 90  # let the dyno finish starting before Chrome launches

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["30 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

# Only one Chrome at a time (saves memory), and the last result for repeated calls
_check_lock = threading.Lock()
_last_result = None
_last_check_at = 0.0


@app.route("/")
def home():
    return render_template_string(
        """
    <!doctype html>
    <html>
      <head><title>WebHostMost keep-alive</title></head>
      <body>
        <h1>It works! Open /status to see the time until suspension.</h1>
      </body>
    </html>
    """
    )


@app.route("/status", methods=["GET"])
@limiter.limit("10 per minute")
@cross_origin(origins=_CORS_ORIGINS)
def status():
    """Checks the Client Area, or returns the last check if it ran under a minute ago."""
    result = check_suspension_timer()
    code = 200 if result.get("ok") else 502
    return jsonify(result), code


def check_suspension_timer(force=False):
    """Opens the Client Area and returns the timer. Reuses a result younger than a minute."""
    global _last_result, _last_check_at

    with _check_lock:
        age = time.time() - _last_check_at
        if not force and _last_result is not None and age < MIN_SECONDS_BETWEEN_CHECKS:
            return {**_last_result, "cached": True, "checked_seconds_ago": int(age)}

        result = _read_timer()
        _last_result = result
        _last_check_at = time.time()

    if result.get("ok"):
        print(f"[WebHostMost] Time until suspension: {result['time_until_suspension']}")
    else:
        print(f"[WebHostMost] ERROR: {result.get('error')}: {result.get('details', '')}")
    return {**result, "cached": False}


def _parse_cookie_header(header):
    """Turns 'name=value; name2=value2' into a list of (name, value) pairs.

    Also accepts the header copied with its 'cookie:' label or wrapped in quotes.
    """
    header = header.strip().strip("'\"").strip()
    if header.lower().startswith("cookie:"):
        header = header[len("cookie:"):].strip().strip("'\"")
    cookies = []
    for part in header.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name:
            cookies.append((name.strip(), value.strip()))
    return cookies


def _read_timer():
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cookie_header = os.environ.get("WEBHOSTMOST_COOKIES", "").strip()
    if not cookie_header:
        return {
            "ok": False,
            "error": "missing_cookies",
            "details": "Set WEBHOSTMOST_COOKIES (see the top of WebHostMostApi.py).",
            "checked_at": checked_at,
        }

    options = Options()
    for arg in (
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--blink-settings=imagesEnabled=false",
    ):
        options.add_argument(arg)
    # The session may be tied to the browser it was created in, so use that browser's
    # User-Agent when WEBHOSTMOST_USER_AGENT is set
    user_agent = os.environ.get("WEBHOSTMOST_USER_AGENT", "").strip() or (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("user-agent=" + user_agent)
    if sys.platform.startswith("linux"):
        # Low memory on the dyno; Chrome on Windows won't start with these
        options.add_argument("--no-zygote")
        options.add_argument("--single-process")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(), options=options)
        driver.set_page_load_timeout(45)

        # Cookies can only be set for the site that is open, so open it first
        driver.get(BASE_URL + "/robots.txt")
        loaded = []
        for name, value in _parse_cookie_header(cookie_header):
            try:
                driver.add_cookie({
                    "name": name,
                    "value": value,
                    "path": "/",
                    "domain": "client.webhostmost.com",
                    "secure": True,
                })
                loaded.append(name)
            except Exception as e:  # one bad cookie shouldn't stop the others
                print(f"[WebHostMost] Skipped cookie {name}: {type(e).__name__}: {e}")

        # Names only, never values: they give access to the account
        whmcs = [name for name in loaded if name.startswith("WHMCS")]
        print(f"[WebHostMost] Loaded {len(loaded)} cookies, WHMCS ones: {whmcs or 'none'}")

        driver.get(CLIENT_AREA_URL)

        if "/login" in driver.current_url:
            return {
                "ok": False,
                "error": "session_expired",
                "details": "WebHostMost asked to log in again. Refresh WEBHOSTMOST_COOKIES.",
                "whmcs_cookies_loaded": whmcs,
                "cookies_loaded": len(loaded),
                "custom_user_agent": bool(os.environ.get("WEBHOSTMOST_USER_AGENT", "").strip()),
                "page_url": driver.current_url,
                "checked_at": checked_at,
            }

        # The timer is filled in by the page's JavaScript, so wait for the numbers
        def timer_ready(d):
            days = d.find_elements(By.ID, "timer-days")
            return days and days[0].text.strip().isdigit()

        try:
            WebDriverWait(driver, 20).until(timer_ready)
        except Exception:
            return {
                "ok": False,
                "error": "timer_not_found",
                "details": "Logged in, but the 'Time until suspension' timer isn't on the page.",
                "page_url": driver.current_url,
                "checked_at": checked_at,
            }

        parts = {}
        for unit in ("days", "hours", "minutes", "seconds"):
            found = driver.find_elements(By.ID, "timer-" + unit)
            text = found[0].text.strip() if found else ""
            parts[unit] = int(text) if text.isdigit() else 0

        return {
            "ok": True,
            "time_until_suspension": "{days}d {hours}h {minutes}m {seconds}s".format(**parts),
            "parts": parts,
            "seconds_until_suspension": parts["days"] * 86400
            + parts["hours"] * 3600
            + parts["minutes"] * 60
            + parts["seconds"],
            "checked_at": checked_at,
        }

    except Exception as e:
        return {
            "ok": False,
            "error": "check_failed",
            "details": f"{type(e).__name__}: {e}",
            "checked_at": checked_at,
        }
    finally:
        if driver:
            driver.quit()


def _scheduler():
    """Checks shortly after start, then every 2 days for as long as the process runs."""
    time.sleep(FIRST_CHECK_DELAY_SECONDS)
    while True:
        try:
            check_suspension_timer(force=True)
        except Exception as e:  # never let the loop die
            print(f"[WebHostMost] Scheduled check crashed: {type(e).__name__}: {e}")
        time.sleep(CHECK_EVERY_SECONDS)


threading.Thread(target=_scheduler, daemon=True, name="webhostmost-keepalive").start()


def run_api():
    port = int(os.environ.get("PORT", 80))
    print(f"[INFO] Starting API server on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
