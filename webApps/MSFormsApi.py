import os
import random
import time
import threading
import json
import uuid
import collections
from queue import Queue

from flask import Flask, jsonify, request, render_template_string, Response
from flask_cors import cross_origin
from flask_caching import Cache

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set working directory to one level up from where bot.py is
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(script_dir, "..")
# os.chdir(parent_dir)  # Handled by launcher

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})

# ─── Config ───────────────────────────────────────────────────────────────────
ALLOW_SEND = True  # Set to True when you want to actually submit the form
HEADLESS = True  # Set to False to open Chrome visibly (debug mode)

# Placeholder texts for free-text questions
TEXT_ANSWERS = [
    "Brak uwag",
    "Nie mam zdania",
    "Nie wiem",
    "Trudno powiedzieć",
]

# ─── Browser Queue ─────────────────────────────────────────────────────────────
# Tracks who is waiting for the browser so we can show queue position to users.

class BrowserQueue:
    """Managed queue that tracks waiting users and lets them know their position."""

    def __init__(self):
        self._lock = threading.Lock()          # protects internal state
        self._semaphore = threading.Semaphore(1)  # only 1 browser at a time
        self._waiters = collections.OrderedDict()  # id -> {"user": ..., "event_queue": ...}
        self._current_user = None              # user label of whoever holds the browser

    def acquire(self, user_label, waiter_id, event_queue=None):
        """Block until the browser is free.  While waiting, push queue events."""
        # Register ourselves as a waiter
        with self._lock:
            self._waiters[waiter_id] = {"user": user_label, "event_queue": event_queue}

        # Notify everyone of updated positions
        self._broadcast_positions()

        # Try to acquire (blocks if someone else has it)
        while not self._semaphore.acquire(timeout=2):
            # While waiting, keep pushing position updates every 2s
            self._broadcast_positions()

        # We now hold the browser
        with self._lock:
            self._current_user = user_label
            # Remove ourselves from waiters
            self._waiters.pop(waiter_id, None)

        # Notify remaining waiters of updated positions
        self._broadcast_positions()

    def release(self):
        """Release the browser for the next waiter."""
        with self._lock:
            self._current_user = None
        self._semaphore.release()
        self._broadcast_positions()

    def _broadcast_positions(self):
        """Send queue position updates to all waiting users."""
        with self._lock:
            waiter_ids = list(self._waiters.keys())
            current = self._current_user

        for pos_idx, wid in enumerate(waiter_ids):
            with self._lock:
                info = self._waiters.get(wid)
            if info and info.get("event_queue"):
                try:
                    info["event_queue"].put({
                        "event": "queue",
                        "data": {
                            "position": pos_idx + 1,
                            "total_waiting": len(waiter_ids),
                            "current_user": current or "(nieznany)",
                        },
                    })
                except Exception:
                    pass

    @property
    def current_user(self):
        with self._lock:
            return self._current_user

    @property
    def queue_size(self):
        with self._lock:
            return len(self._waiters)


browser_queue = BrowserQueue()


@app.route("/")
def home():
    return render_template_string(HOME_PAGE_HTML)


HOME_PAGE_HTML = r"""
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FormBot - Auto-filler</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #e0f7f0 0%, #cce8f0 30%, #d4eef8 60%, #e8f4f0 100%);
      color: #2d3748;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      overflow-x: hidden;
    }
    body::before {
      content: '';
      position: fixed;
      top: -50%; left: -50%;
      width: 200%; height: 200%;
      background: radial-gradient(ellipse at 25% 15%, rgba(72, 199, 176, 0.12) 0%, transparent 50%),
                  radial-gradient(ellipse at 75% 85%, rgba(56, 178, 220, 0.08) 0%, transparent 50%);
      z-index: -1;
      animation: bgShift 20s ease-in-out infinite alternate;
    }
    @keyframes bgShift {
      0% { transform: translate(0, 0); }
      100% { transform: translate(-3%, 2%); }
    }
    .container {
      width: 100%;
      max-width: 680px;
      padding: 40px 20px;
    }
    .logo {
      text-align: center;
      margin-bottom: 40px;
    }
    .logo h1 {
      font-size: 2.4rem;
      font-weight: 700;
      background: linear-gradient(135deg, #0d9488, #0891b2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.5px;
    }
    .logo p {
      color: #64748b;
      font-size: 0.95rem;
      margin-top: 6px;
    }
    .card {
      background: rgba(255, 255, 255, 0.72);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(13, 148, 136, 0.15);
      border-radius: 16px;
      padding: 28px;
      margin-bottom: 20px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
      transition: border-color 0.3s, box-shadow 0.3s;
    }
    .card:hover {
      border-color: rgba(13, 148, 136, 0.3);
      box-shadow: 0 6px 32px rgba(0, 0, 0, 0.08);
    }
    .input-group {
      display: flex;
      gap: 10px;
    }
    .input-group input {
      flex: 1;
      padding: 14px 18px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(13, 148, 136, 0.25);
      border-radius: 12px;
      color: #1e293b;
      font-size: 0.95rem;
      font-family: 'Inter', sans-serif;
      outline: none;
      transition: border-color 0.3s, box-shadow 0.3s;
    }
    .input-group input:focus {
      border-color: #0d9488;
      box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
    }
    .input-group input::placeholder { color: #94a3b8; }
    .btn {
      padding: 14px 28px;
      background: linear-gradient(135deg, #0d9488, #0891b2);
      border: none;
      border-radius: 12px;
      color: #fff;
      font-size: 0.95rem;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.3s;
      white-space: nowrap;
    }
    .btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 25px rgba(13, 148, 136, 0.3);
    }
    .btn:active { transform: translateY(0); }
    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }
    /* Progress area */
    #progress-area { display: none; }
    #progress-area.active { display: block; }
    .status-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 20px;
    }
    .spinner {
      width: 22px; height: 22px;
      border: 3px solid rgba(13, 148, 136, 0.2);
      border-top-color: #0d9488;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status-text {
      font-size: 0.9rem;
      color: #64748b;
    }
    .status-text.done { color: #059669; }
    .status-text.error { color: #dc2626; }
    /* Event log */
    #event-log {
      max-height: 300px;
      overflow-y: auto;
      padding: 4px 0;
    }
    .event-item {
      padding: 10px 14px;
      margin-bottom: 6px;
      background: rgba(240, 253, 250, 0.7);
      border-radius: 10px;
      border-left: 3px solid #0d9488;
      font-size: 0.85rem;
      animation: fadeSlideIn 0.3s ease;
    }
    .event-item.answer { border-left-color: #059669; }
    .event-item.warn { border-left-color: #d97706; }
    .event-item.error-ev { border-left-color: #dc2626; }
    @keyframes fadeSlideIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .event-title { color: #1e293b; font-weight: 500; }
    .event-detail { color: #64748b; margin-top: 3px; }
    /* Results */
    #results-area { display: none; }
    #results-area.active { display: block; }
    .result-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 18px;
    }
    .result-header h2 { color: #1e293b; }
    .result-header .badge {
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .badge.success { background: rgba(5, 150, 105, 0.12); color: #059669; }
    .badge.fail { background: rgba(220, 38, 38, 0.1); color: #dc2626; }
    .result-card {
      padding: 14px 16px;
      margin-bottom: 8px;
      background: rgba(240, 253, 250, 0.6);
      border-radius: 10px;
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }
    .result-num {
      width: 30px; height: 30px;
      background: linear-gradient(135deg, #0d9488, #0891b2);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 700;
      color: #fff;
      flex-shrink: 0;
    }
    .result-body { flex: 1; }
    .result-q { font-weight: 500; color: #1e293b; font-size: 0.9rem; }
    .result-a { color: #059669; font-size: 0.85rem; margin-top: 4px; }
    .result-type { color: #94a3b8; font-size: 0.75rem; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
    .footer { text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 40px; padding-bottom: 30px; }
    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(13, 148, 136, 0.25); border-radius: 3px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">
      <h1>FormBot</h1>
      <p>Automatyczne wypelnianie formularzy</p>
    </div>

    <div class="card">
      <div class="input-group">
        <input type="text" id="url-input" placeholder="Wklej link do formularza (Google Forms / MS Forms)...">
        <button class="btn" id="start-btn" onclick="startFill()">Start</button>
      </div>
    </div>

    <div id="progress-area" class="card">
      <div id="queue-bar" style="display:none; background:linear-gradient(135deg,#fbbf24,#f59e0b); color:#78350f; padding:12px 16px; border-radius:10px; margin-bottom:14px; font-size:0.88rem; font-weight:500; display:flex; align-items:center; gap:10px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span id="queue-text"></span>
      </div>
      <div class="status-bar">
        <div class="spinner" id="spinner"></div>
        <span class="status-text" id="status-text">Laczenie...</span>
      </div>
      <div id="event-log"></div>
    </div>

    <div id="results-area" class="card">
      <div class="result-header">
        <h2 style="font-size:1.2rem;">Wyniki</h2>
        <span class="badge" id="result-badge"></span>
      </div>
      <div id="results-list"></div>
    </div>

    <div class="footer">FormBot &mdash; Copyright by K5 Studio 2026</div>
  </div>

  <script>
    function startFill() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }

      const btn = document.getElementById('start-btn');
      const progArea = document.getElementById('progress-area');
      const resArea = document.getElementById('results-area');
      const eventLog = document.getElementById('event-log');
      const statusText = document.getElementById('status-text');
      const spinner = document.getElementById('spinner');

      btn.disabled = true;
      progArea.classList.add('active');
      resArea.classList.remove('active');
      eventLog.innerHTML = '';
      statusText.className = 'status-text';
      statusText.textContent = 'Uruchamianie przegladarki...';
      spinner.style.display = 'block';

      const encodedUrl = encodeURIComponent(url);
      const evtSource = new EventSource('/stream-fill?url=' + encodedUrl);

      evtSource.addEventListener('status', function(e) {
        statusText.textContent = e.data;
      });

      evtSource.addEventListener('queue', function(e) {
        const d = JSON.parse(e.data);
        const queueBar = document.getElementById('queue-bar');
        const queueText = document.getElementById('queue-text');
        queueBar.style.display = 'flex';
        statusText.textContent = 'Oczekiwanie w kolejce...';
        queueText.textContent = 'Pozycja w kolejce: ' + d.position + '/' + d.total_waiting;
      });

      evtSource.addEventListener('queue_done', function(e) {
        document.getElementById('queue-bar').style.display = 'none';
      });

      evtSource.addEventListener('question', function(e) {
        const d = JSON.parse(e.data);
        const div = document.createElement('div');
        div.className = 'event-item';
        div.innerHTML = '<div class="event-title">Q' + d.num + ': ' + escHtml(d.title) + '</div>'
          + '<div class="event-detail">Typ: ' + d.type + '</div>';
        eventLog.appendChild(div);
        eventLog.scrollTop = eventLog.scrollHeight;
      });

      evtSource.addEventListener('answer', function(e) {
        const d = JSON.parse(e.data);
        const div = document.createElement('div');
        div.className = 'event-item answer';
        const answerText = Array.isArray(d.answer) ? d.answer.join(', ') : (typeof d.answer === 'object' && d.answer !== null ? JSON.stringify(d.answer) : d.answer);
        div.innerHTML = '<div class="event-title">Odpowiedz Q' + d.num + '</div>'
          + '<div class="event-detail">' + escHtml(String(answerText)) + '</div>';
        eventLog.appendChild(div);
        eventLog.scrollTop = eventLog.scrollHeight;
      });

      evtSource.addEventListener('warn', function(e) {
        const div = document.createElement('div');
        div.className = 'event-item warn';
        div.innerHTML = '<div class="event-title">Ostrzezenie</div><div class="event-detail">' + escHtml(e.data) + '</div>';
        eventLog.appendChild(div);
      });

      evtSource.addEventListener('done', function(e) {
        evtSource.close();
        const d = JSON.parse(e.data);
        spinner.style.display = 'none';
        statusText.textContent = 'Gotowe! (' + d.questions_filled + ' pytan)';
        statusText.className = 'status-text done';
        btn.disabled = false;
        showResults(d);
      });

      evtSource.addEventListener('error_ev', function(e) {
        evtSource.close();
        spinner.style.display = 'none';
        statusText.textContent = 'Blad: ' + e.data;
        statusText.className = 'status-text error';
        btn.disabled = false;
      });

      evtSource.onerror = function() {
        evtSource.close();
        spinner.style.display = 'none';
        statusText.textContent = 'Polaczenie przerwane';
        statusText.className = 'status-text error';
        btn.disabled = false;
      };
    }

    function showResults(data) {
      const resArea = document.getElementById('results-area');
      const badge = document.getElementById('result-badge');
      const list = document.getElementById('results-list');
      resArea.classList.add('active');
      list.innerHTML = '';

      if (data.status === 'submitted') {
        badge.className = 'badge success';
        badge.textContent = 'Wyslano';
      } else {
        badge.className = 'badge fail';
        badge.textContent = data.status;
      }

      (data.results || []).forEach(function(r) {
        const answerText = r.answer == null ? '-' :
          (Array.isArray(r.answer) ? r.answer.join(', ') :
          (typeof r.answer === 'object' ? JSON.stringify(r.answer) : r.answer));
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = '<div class="result-num">' + r.question_number + '</div>'
          + '<div class="result-body">'
          + '<div class="result-q">' + escHtml(r.title) + '</div>'
          + '<div class="result-type">' + r.type + '</div>'
          + '<div class="result-a">' + escHtml(String(answerText)) + '</div>'
          + '</div>';
        list.appendChild(card);
      });
    }

    function escHtml(s) {
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }

    // Allow Enter key to start
    document.getElementById('url-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') startFill();
    });
  </script>
</body>
</html>
"""


@app.route("/fill-form", methods=["GET"], defaults={"form_url": None})
@app.route("/fill-form/<path:form_url>", methods=["GET"])
@cross_origin()
def fill_form(form_url):
    if not form_url:
        return jsonify({"error": "Podaj URL formularza, np. /fill-form/https://docs.google.com/forms/d/e/.../viewform"}), 400
    target_url = form_url
    # Re-add query string if Flask stripped it
    if request.query_string:
        qs = request.query_string.decode("utf-8", errors="replace")
        if "?" in target_url:
            target_url += "&" + qs
        else:
            target_url += "?" + qs
    user_label = request.remote_addr or "API"
    waiter_id = str(uuid.uuid4())
    browser_queue.acquire(user_label, waiter_id)
    try:
        return _perform_form_fill(target_url)
    finally:
        browser_queue.release()


@app.route("/stream-fill", methods=["GET"])
def stream_fill():
    """SSE endpoint that streams live progress while filling the form."""
    form_url = request.args.get("url", "")
    if not form_url:
        def err_gen():
            yield 'event: error_ev\ndata: Podaj URL formularza\n\n'
        return Response(err_gen(), mimetype='text/event-stream')

    event_queue = Queue()
    user_label = request.remote_addr or "Uzytkownik"
    waiter_id = str(uuid.uuid4())

    def worker():
        browser_queue.acquire(user_label, waiter_id, event_queue=event_queue)
        try:
            # Tell the client they left the queue
            event_queue.put({"event": "queue_done", "data": ""})
            _perform_form_fill(form_url, event_queue=event_queue)
        finally:
            browser_queue.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    def generate():
        while True:
            msg = event_queue.get()  # Blocks until message
            if msg is None:
                break  # Sentinel - stream done
            event_type = msg.get("event", "status")
            data = msg.get("data", "")
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            yield f'event: {event_type}\ndata: {data}\n\n'

    return Response(generate(), mimetype='text/event-stream')


def _create_driver():
    """Create a Chrome driver. Runs headless when HEADLESS=True."""
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service()
    return webdriver.Chrome(service=service, options=options)


def _get_question_title(question_el):
    """Extract the question title text from a questionItem element."""
    # Try specific selectors first, then progressively more generic ones
    for selector in [
        'div[data-automation-id="questionTitle"]',
        'span.text-format-content',
        'div[role="heading"]',
        'span[class*="title"]',
        'legend',
        'label[class*="header"]',
        'h2', 'h3', 'h4',
    ]:
        try:
            title_el = question_el.find_element(By.CSS_SELECTOR, selector)
            text = title_el.text.strip()
            if text:
                return text
        except Exception:
            continue

    # Try aria-label on the question container itself
    aria = question_el.get_attribute("aria-label") or ""
    if aria.strip():
        return aria.strip()

    # Last resort: get the first meaningful line of text from the element,
    # excluding text that belongs to radio/checkbox options
    try:
        full_text = question_el.text.strip()
        if full_text:
            # Take the first line - usually the question title
            first_line = full_text.split("\n")[0].strip()
            if first_line and len(first_line) > 1:
                return first_line
    except Exception:
        pass

    return "(unknown question)"


def _handle_radio_question(question_el, title):
    """Handle a simple single-choice (radio) question. Returns chosen label."""
    # Try input[role=radio] (MS Forms) then div[role=radio] (Google Forms)
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    if not radios:
        return None

    chosen = random.choice(radios)
    label_text = _get_input_label(question_el, chosen)

    try:
        chosen.click()
    except Exception:
        try:
            parent = chosen.find_element(By.XPATH, "./ancestor::label")
            parent.click()
        except Exception:
            try:
                driver = question_el.parent
                driver.execute_script("arguments[0].click();", chosen)
            except Exception:
                pass

    return label_text


def _handle_checkbox_question(question_el, title):
    """Handle a multi-select (checkbox) question. Returns list of chosen labels."""
    # Try input[role=checkbox] (MS Forms) then div[role=checkbox] (Google Forms)
    checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
    if not checkboxes:
        return None

    # Select random number of options (1 to min(3, total))
    count = random.randint(1, min(3, len(checkboxes)))
    chosen_cbs = random.sample(checkboxes, count)
    chosen_labels = []

    for cb in chosen_cbs:
        label_text = _get_input_label(question_el, cb)
        chosen_labels.append(label_text)
        try:
            cb.click()
        except Exception:
            try:
                parent = cb.find_element(By.XPATH, "./ancestor::label")
                parent.click()
            except Exception:
                try:
                    driver = question_el.parent
                    driver.execute_script("arguments[0].click();", cb)
                except Exception:
                    pass

    return chosen_labels


def _handle_matrix_question(question_el, title):
    """
    Handle a matrix/grid question.
    Groups radio buttons by row (using aria-label prefix) and picks one per row.
    Returns dict of {row_title: chosen_column}.
    """
    radios = question_el.find_elements(By.CSS_SELECTOR, 'input[role="radio"]')
    if not radios:
        return None

    # Group radios by row using aria-label
    # aria-label format: "{Row Title} {Column Choice}"
    # We need to figure out which part is the row title and which is the column
    # Strategy: collect all aria-labels, find common suffixes (column names)

    aria_labels = []
    for r in radios:
        aria = r.get_attribute("aria-label") or ""
        aria_labels.append(aria)

    # Find the column names by looking for the table header row
    # Alternative: group by radio button name attribute or position
    # Best approach: find all column headers from the matrix table

    # Try to find column headers from the matrix structure
    column_headers = []
    try:
        # MS Forms matrix tables have column headers in specific elements
        header_cells = question_el.find_elements(
            By.CSS_SELECTOR, 'div[role="columnheader"], th'
        )
        for cell in header_cells:
            text = cell.text.strip()
            if text:
                column_headers.append(text)
    except Exception:
        pass

    # If we found column headers, use them to split aria-labels
    rows = {}  # row_title -> list of (radio_element, column_name)

    if column_headers:
        for radio, aria in zip(radios, aria_labels):
            row_title = aria
            col_name = ""
            for col in column_headers:
                if aria.endswith(col):
                    row_title = aria[: -len(col)].strip()
                    col_name = col
                    break
            if row_title not in rows:
                rows[row_title] = []
            rows[row_title].append((radio, col_name))
    else:
        # Fallback: group by name attribute
        name_groups = {}
        for radio, aria in zip(radios, aria_labels):
            name = radio.get_attribute("name") or "unknown"
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append((radio, aria))
        # Convert to rows dict
        for name, items in name_groups.items():
            row_title = items[0][1].rsplit(" ", 1)[0] if items else name
            rows[row_title] = [(r, a) for r, a in items]

    # Pick one random option per row
    result = {}
    for row_title, options in rows.items():
        chosen_radio, chosen_col = random.choice(options)
        result[row_title] = chosen_col
        try:
            chosen_radio.click()
        except Exception:
            try:
                parent = chosen_radio.find_element(By.XPATH, "./ancestor::label")
                parent.click()
            except Exception:
                pass
        time.sleep(0.1)  # Small delay between clicks

    return result


def _handle_text_question(question_el, title):
    """Handle a text input question. Returns the text entered."""
    text_input = None
    try:
        text_input = question_el.find_element(By.CSS_SELECTOR, "textarea")
    except Exception:
        try:
            text_input = question_el.find_element(
                By.CSS_SELECTOR, 'input[type="text"]'
            )
        except Exception:
            # Try any input that's not radio/checkbox
            try:
                inputs = question_el.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    role = inp.get_attribute("role") or ""
                    input_type = inp.get_attribute("type") or ""
                    if role not in ("radio", "checkbox") and input_type not in (
                        "radio",
                        "checkbox",
                        "hidden",
                    ):
                        text_input = inp
                        break
            except Exception:
                pass

    if text_input is None:
        return None

    answer = random.choice(TEXT_ANSWERS)
    try:
        text_input.clear()
        text_input.send_keys(answer)
    except Exception:
        pass

    return answer


def _get_input_label(question_el, input_el):
    """Try to get a human-readable label for an input element."""
    # Try aria-label first
    aria = input_el.get_attribute("aria-label")
    if aria:
        return aria

    # Try parent label text
    try:
        parent_label = input_el.find_element(By.XPATH, "./ancestor::label")
        return parent_label.text.strip()
    except Exception:
        pass

    # Try associated label via id
    input_id = input_el.get_attribute("id")
    if input_id:
        try:
            label = question_el.find_element(
                By.CSS_SELECTOR, f'label[for="{input_id}"]'
            )
            return label.text.strip()
        except Exception:
            pass

    return "(unknown option)"


def _detect_question_type(question_el):
    """
    Detect the type of a question element.
    Returns one of: 'radio', 'checkbox', 'matrix', 'text', 'unknown'
    """
    # Check for matrix first (has columnheader or table-like structure)
    try:
        col_headers = question_el.find_elements(
            By.CSS_SELECTOR, 'div[role="columnheader"], th'
        )
        if col_headers:
            return "matrix"
    except Exception:
        pass

    # Check for radio buttons (input or div with role=radio)
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    if radios:
        # Could be matrix without columnheader detection - check if there are
        # multiple radios with the same name grouping differently
        names = set()
        for r in radios:
            n = r.get_attribute("name")
            if n:
                names.add(n)
        if len(names) > 1:
            return "matrix"
        return "radio"

    # Check for checkboxes (input or div with role=checkbox)
    checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
    if checkboxes:
        return "checkbox"

    # Check for text input
    text_inputs = question_el.find_elements(By.CSS_SELECTOR, "textarea")
    if text_inputs:
        return "text"
    text_inputs = question_el.find_elements(
        By.CSS_SELECTOR, 'input[type="text"]'
    )
    if text_inputs:
        return "text"

    # Fallback: check for any non-hidden input
    inputs = question_el.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        role = inp.get_attribute("role") or ""
        input_type = inp.get_attribute("type") or ""
        if role not in ("radio", "checkbox") and input_type not in (
            "radio",
            "checkbox",
            "hidden",
        ):
            return "text"

    return "unknown"


def _detect_provider(url):
    """Detect the form provider from the URL."""
    if "forms.office.com" in url or "microsoft" in url:
        return "msforms"
    elif "docs.google.com/forms" in url or "google.com/forms" in url:
        return "google"
    else:
        return "unknown"


# Provider-specific selectors for finding question containers
QUESTION_SELECTORS = {
    "msforms": 'div[data-automation-id="questionItem"]',
    "google": 'div[jsmodel="CP1oW"]',
    "unknown": 'div[data-automation-id="questionItem"], div[jsmodel="CP1oW"]',
}

# Provider-specific selectors for question title text
TITLE_SELECTORS = {
    "msforms": 'div[data-automation-id="questionTitle"]',
    "google": 'div[role="heading"]',
    "unknown": 'div[data-automation-id="questionTitle"], div[role="heading"]',
}


def _perform_form_fill(form_url, event_queue=None):
    """Main function: opens the form, reads questions, fills random answers."""
    driver = None
    results = []
    provider = _detect_provider(form_url)

    def _emit(event, data=""):
        """Push an SSE event if streaming is active."""
        if event_queue is not None:
            event_queue.put({"event": event, "data": data})

    try:
        _emit("status", f"Provider: {provider}")
        print(f"[FormBot] Provider detected: {provider}")

        _emit("status", "Uruchamianie przegladarki...")
        print(f"[FormBot] Initializing Chrome driver...")
        driver = _create_driver()
        driver.set_page_load_timeout(60)

        _emit("status", "Ladowanie formularza...")
        print(f"[FormBot] Navigating to form: {form_url}")
        driver.get(form_url)

        # Wait for the form to load using provider-specific selector
        q_selector = QUESTION_SELECTORS.get(provider, QUESTION_SELECTORS["unknown"])
        t_selector = TITLE_SELECTORS.get(provider, TITLE_SELECTORS["unknown"])
        _emit("status", "Czekanie na zaladowanie pytan...")
        print(f"[FormBot] Waiting for form to load (selector: {q_selector})...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, q_selector))
        )
        time.sleep(3)  # Extra wait for JS rendering

        # Dynamic question processing - re-scan after each answer to catch
        # conditional/branching questions that appear after selecting an answer
        answered_ids = set()  # Track which questions we already answered
        question_num = 0
        max_passes = 10  # Safety limit to prevent infinite loops

        for _pass in range(max_passes):
            questions = driver.find_elements(By.CSS_SELECTOR, q_selector)
            new_questions_found = False

            for question_el in questions:
                # Build a unique key for this question element
                q_id = question_el.get_attribute("id") or ""
                try:
                    q_title_preview = question_el.text[:80]
                except Exception:
                    q_title_preview = ""
                q_key = q_id or q_title_preview

                if q_key in answered_ids:
                    continue  # Already processed

                new_questions_found = True
                answered_ids.add(q_key)
                question_num += 1

                # Scroll the question into view
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    question_el,
                )
                time.sleep(0.5)

                title = _get_question_title(question_el)
                q_type = _detect_question_type(question_el)

                print(f"\n[FormBot] === Question {question_num} ===")
                print(f"[FormBot] Title: {title}")
                print(f"[FormBot] Type: {q_type}")

                _emit("question", {"num": question_num, "title": title, "type": q_type})
                _emit("status", f"Pytanie {question_num}: {title[:50]}...")

                # DEBUG: dump inner HTML of unknown questions so we can fix selectors
                if q_type == "unknown" or title == "(unknown question)":
                    try:
                        inner = question_el.get_attribute("innerHTML")
                        print(f"[FormBot] DEBUG HTML (first 2000 chars):\n{inner[:2000]}")
                    except Exception:
                        pass

                result_entry = {
                    "question_number": question_num,
                    "title": title,
                    "type": q_type,
                    "answer": None,
                }

                if q_type == "radio":
                    answer = _handle_radio_question(question_el, title)
                    result_entry["answer"] = answer
                    print(f"[FormBot] Selected: {answer}")
                    _emit("answer", {"num": question_num, "answer": answer})

                elif q_type == "checkbox":
                    answers = _handle_checkbox_question(question_el, title)
                    result_entry["answer"] = answers
                    print(f"[FormBot] Selected: {answers}")
                    _emit("answer", {"num": question_num, "answer": answers})

                elif q_type == "matrix":
                    answers = _handle_matrix_question(question_el, title)
                    result_entry["answer"] = answers
                    if answers:
                        for row, col in answers.items():
                            print(f"[FormBot]   {row} -> {col}")
                    _emit("answer", {"num": question_num, "answer": answers})

                elif q_type == "text":
                    answer = _handle_text_question(question_el, title)
                    result_entry["answer"] = answer
                    print(f"[FormBot] Typed: {answer}")
                    _emit("answer", {"num": question_num, "answer": answer})

                else:
                    print(f"[FormBot] [WARN] Unknown question type, skipping.")
                    _emit("warn", f"Q{question_num}: nieznany typ pytania")

                results.append(result_entry)
                time.sleep(0.5)

            if not new_questions_found:
                # No new questions appeared - we're done
                break

            # Wait a moment for any conditional questions to appear after answers
            time.sleep(1.5)
            _emit("status", f"Szukanie nowych pytan (przejscie {_pass + 1})...")
            print(f"[FormBot] Re-scanning for new conditional questions (pass {_pass + 1})...")

        # -- Submit or print results --
        print(f"\n{'='*60}")
        print(f"[FormBot] FORM FILL COMPLETE - {len(results)} questions processed.")
        print(f"{'='*60}")

        submit_status = "dry_run"

        if ALLOW_SEND:
            _emit("status", "Wysylanie formularza...")
            submit_btn = None
            # Try multiple selectors to find the submit button
            selectors = [
                # MS Forms
                (By.CSS_SELECTOR, 'button[data-automation-id="submitButton"]'),
                # Google Forms - the submit button uses jsname="M2UYVd"
                (By.CSS_SELECTOR, 'div[role="button"][jsname="M2UYVd"]'),
                # Generic text-based fallbacks
                (By.XPATH, "//span[contains(., 'Prze')]/ancestor::div[@role='button']"),
                (By.XPATH, "//span[contains(., 'Wy')]/ancestor::div[@role='button']"),
                (By.XPATH, "//div[@role='button'][contains(., 'Prze')]"),
                (By.XPATH, "//div[@role='button'][contains(., 'Submit')]"),
                (By.XPATH, "//button[contains(., 'Prze')]"),
                (By.XPATH, "//button[contains(., 'Submit')]"),
                (By.XPATH, "//button[contains(., 'Send')]"),
            ]
            for by, selector in selectors:
                try:
                    submit_btn = driver.find_element(by, selector)
                    print(f"[FormBot] Found submit button with: {selector}")
                    break
                except Exception:
                    continue

            if submit_btn is None:
                # Last resort: find all buttons and pick the last one
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                if all_buttons:
                    submit_btn = all_buttons[-1]
                    print(f"[FormBot] Using last button on page as submit (text: {submit_btn.text})")

            if submit_btn:
                try:
                    # Scroll button into view
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        submit_btn,
                    )
                    time.sleep(1)
                    # Wait for clickable
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(submit_btn)
                    )
                    submit_btn.click()
                    print("[FormBot] [OK] Form submitted!")
                    submit_status = "submitted"
                    time.sleep(3)
                except Exception as click_err:
                    # Fallback: JS click
                    print(f"[FormBot] Normal click failed ({click_err}), trying JS click...")
                    try:
                        driver.execute_script("arguments[0].click();", submit_btn)
                        print("[FormBot] [OK] Form submitted via JS click!")
                        submit_status = "submitted"
                        time.sleep(3)
                    except Exception as js_err:
                        print(f"[FormBot] [FAIL] JS click also failed: {js_err}")
                        submit_status = "submit_failed"
            else:
                print("[FormBot] [FAIL] Could not find submit button on the page.")
                submit_status = "no_submit_button"
        else:
            print("[FormBot] ALLOW_SEND=False - NOT submitting. Printing results:")
            for r in results:
                print(f"  Q{r['question_number']}: {r['title']}")
                print(f"    Type: {r['type']}")
                print(f"    Answer: {r['answer']}")
                print()

        final_data = {
            "status": submit_status,
            "questions_filled": len(results),
            "results": results,
        }
        _emit("done", final_data)

    except Exception as e:
        error_msg = str(e)
        print(f"[FormBot] ERROR: {error_msg}")
        _emit("error_ev", error_msg)
        last_url = "Unknown"
        try:
            if driver:
                last_url = driver.current_url
        except Exception:
            pass
        if event_queue is None:
            return jsonify({"error": error_msg, "last_url": last_url}), 500

    finally:
        if driver:
            print(f"[FormBot] Quitting driver...")
            driver.quit()
        # Send sentinel to close SSE stream
        if event_queue is not None:
            event_queue.put(None)

    if event_queue is None:
        return jsonify(
            {
                "status": submit_status,
                "questions_filled": len(results),
                "results": results,
            }
        )


def run_api():
    port = int(os.environ.get("PORT", 80))
    print(f"[MSForms] Starting API server on port {port}...")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_api()
