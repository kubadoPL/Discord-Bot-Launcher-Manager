import os

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
os.chdir(parent_dir)  # Change working directory

print("Working directory set to:", os.getcwd())

from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from flask_cors import CORS

from flask import Flask, jsonify, render_template_string
from flask_caching import Cache


app = Flask(__name__)
CORS(app)  # enable CORS globally

cache = Cache(app, config={"CACHE_TYPE": "simple"})


@app.route("/")
def home():
    return render_template_string(
        """
    <!doctype html>
    <html>
      <head><title>Simple Page</title></head>
      <body>
        <h1>It works! paste to link /get-sum to see how many users stream radio gaming!</h1>
      </body>
    </html>
    """
    )


@app.route("/get-sum", methods=["GET"])
@cache.cached(timeout=30, query_string=True)
def get_sum():
    # Login credentials
    station = request.args.get("station")
    if not station:
        return jsonify({"error": "Missing station parameter"}), 400
    # print(f"[INFO] Processing station: {station.upper()}")
    EMAIL = os.environ.get("ZENOFM_EMAIL_" + station.upper())
    PASSWORD = os.environ.get("ZENOFM_PASSWORD_" + station.upper())

    if not EMAIL or not PASSWORD:
        return jsonify({"error": "Missing credentials for station: " + station}), 400

    # Optional: headless mode for production use
    options = Options()
    options.add_argument("--headless")  # Required
    options.add_argument("--no-sandbox")  # Required
    options.add_argument("--disable-gpu")  # Optional but common
    options.add_argument("--disable-dev-shm-usage")  # Optional

    options.add_argument("--blink-settings=imagesEnabled=false")  # No images

    # Don't specify path — chromedriver is in PATH
    service = Service()  # Auto-resolves chromedriver from PATH

    driver = webdriver.Chrome(service=service, options=options)

    total_sum = 0

    try:
        driver.get("https://tools.zeno.fm/login")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        print(EMAIL)
        driver.find_element(By.ID, "username").send_keys(EMAIL)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.ID, "kc-login").click()

        WebDriverWait(driver, 10).until(EC.url_contains("/accounts"))

        current_url = driver.current_url
        index = current_url.find("accounts/")
        accounts_part = current_url[index:] if index != -1 else ""

        driver.get(f"https://tools.zeno.fm/{accounts_part}analytics/live")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".td.vs-table--td"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        tds = soup.find_all("td", class_="td vs-table--td")

        i = 0
        while i < len(tds) - 1:
            country_td = tds[i].find("span")
            number_td = tds[i + 1].find("span")

            if country_td and number_td:
                number_text = number_td.get_text(strip=True)
                if number_text.isdigit():
                    total_sum += int(number_text)
            i += 2

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        driver.quit()

    return jsonify({"total_sum": total_sum})


def run_api():
    port = int(os.environ.get("PORT", 80))  # Get the port from environment variable
    print(f"[INFO] Starting API server on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
