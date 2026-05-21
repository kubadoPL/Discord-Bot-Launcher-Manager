import os
import random
import time
import threading
import json
import uuid
import collections
from queue import Queue
import urllib.parse
import requests as http_requests  # renamed to avoid conflict with flask.request

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

# ─── Gemini AI Integration ────────────────────────────────────────────────────

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Default API key from environment variable
GEMINI_DEFAULT_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_DEFAULT_KEY:
    print("[FormBot] WARNING: GEMINI_API_KEY env var not set. AI mode requires manual key input.")
else:
    print(f"[FormBot] GEMINI_API_KEY loaded from env ({GEMINI_DEFAULT_KEY[:8]}...)")

# Cache scanned questions per form URL (in-memory + file)
_SCAN_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_scan_cache.json")
_ai_scan_cache = {}  # { form_url: [scanned_questions_list] }

def _load_scan_cache():
    """Load scan cache from file on startup."""
    global _ai_scan_cache
    try:
        if os.path.exists(_SCAN_CACHE_FILE):
            with open(_SCAN_CACHE_FILE, "r", encoding="utf-8") as f:
                _ai_scan_cache = json.loads(f.read())
            print(f"[FormBot] Loaded scan cache: {len(_ai_scan_cache)} form(s)")
    except Exception as e:
        print(f"[FormBot] Could not load scan cache: {e}")

def _save_scan_cache():
    """Save scan cache to file."""
    try:
        with open(_SCAN_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(_ai_scan_cache, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[FormBot] Could not save scan cache: {e}")

_load_scan_cache()


def _ask_gemini_for_answers(questions_data, api_key, _emit_fn=None, weights=None):
    """Send all questions to Gemini and get a coherent set of answers using google-genai SDK."""
    from google import genai
    from google.genai import types

    if _emit_fn:
        _emit_fn("status", "AI: Przygotowywanie pytan dla Gemini...")

    # Build the prompt
    questions_text = ""
    for q in questions_data:
        questions_text += f"\nPytanie {q['num']} (typ: {q['type']}): {q['title']}\n"
        if q['type'] in ('radio', 'checkbox') and q.get('options'):
            for i, opt in enumerate(q['options']):
                questions_text += f"  {i}: {opt}\n"
            # Add weight hints if available
            if weights and q.get('title') in weights:
                q_weights = weights[q['title']]
                if isinstance(q_weights, dict):
                    hint_parts = []
                    total = sum(q_weights.values())
                    if total > 0:
                        for opt_label, w in q_weights.items():
                            pct = int(w / total * 100) if total > 0 else 0
                            if pct > 0:
                                hint_parts.append(f"{opt_label}: ~{pct}%")
                        if hint_parts:
                            questions_text += f"  WSKAZOWKA preferencji uzytkownka: {', '.join(hint_parts)}\n"
        elif q['type'] == 'matrix' and q.get('rows') and q.get('options'):
            questions_text += f"  Kolumny: {', '.join(f'{i}: {c}' for i, c in enumerate(q['options']))}\n"
            questions_text += f"  Wiersze: {', '.join(q['rows'])}\n"
            # Add matrix weight hints
            if weights and q.get('title') in weights:
                q_weights = weights[q['title']]
                if isinstance(q_weights, dict):
                    for row_name, row_w in q_weights.items():
                        if isinstance(row_w, dict):
                            total = sum(row_w.values())
                            if total > 0:
                                parts = [f"{col}: ~{int(v/total*100)}%" for col, v in row_w.items() if v > 0]
                                if parts:
                                    questions_text += f"  WSKAZOWKA dla wiersza '{row_name}': {', '.join(parts)}\n"
        elif q['type'] == 'text':
            questions_text += "  (pytanie otwarte - napisz wlasna, unikalna odpowiedz pasujaca do Twojej postaci)\n"

    # Random persona seed so AI creates different people each time
    # Try to get gender from weights if user set preferences
    persona_gender = None
    if weights:
        for q in questions_data:
            title = q.get('title', '')
            title_lower = title.lower()
            if any(g in title_lower for g in ['płeć', 'plec', 'gender']):
                q_weights = weights.get(title)
                if isinstance(q_weights, dict) and q_weights:
                    # Use weighted random based on slider values
                    labels = list(q_weights.keys())
                    w_vals = [max(0, q_weights[l]) for l in labels]
                    total = sum(w_vals)
                    if total > 0:
                        chosen_label = random.choices(labels, weights=w_vals, k=1)[0]
                        chosen_lower = chosen_label.lower()
                        if 'kobieta' in chosen_lower or 'female' in chosen_lower:
                            persona_gender = "kobieta"
                        elif 'mężczyzna' in chosen_lower or 'mezczyzna' in chosen_lower or 'male' in chosen_lower:
                            persona_gender = "mezczyzna"
                        # else: "Inna" / "Nie chce podawać" -> keep random
                break
    if not persona_gender:
        persona_gender = random.choice(["mezczyzna", "kobieta"])
    persona_age = random.choice(["18-24", "25-34", "35-44", "45-54", "55-64", "65+"])
    persona_job = random.choice(["student", "pracownik biurowy", "nauczyciel", "informatyk", "sprzedawca", "kierowca", "lekarz", "emeryt", "bezrobotny", "przedsiebiorca", "pracownik fizyczny", "freelancer"])

    has_hints = weights is not None and len(weights) > 0
    hints_note = ""
    if has_hints:
        hints_note = "\n4. Przy niektorych pytaniach sa WSKAZOWKI preferencji uzytkownika (np. '~30% opcja A'). Staraj sie kierowac tymi wskazowkami jako sugestiami statystycznymi - nie musisz ich sluchac jesli nie pasuja do Twojej postaci, ale traktuj je jako silne sugestie co uzytkownik preferuje."

    prompt = f"""Jestes prawdziwa osoba wypelniajaca ankiete. Twoja postac to: {persona_gender}, wiek {persona_age} lat, zawod: {persona_job}. Rozwin te cechy i odpowiadaj SPOJNIE.

WAZNE ZASADY:
1. Odpowiedzi musza byc logicznie spojne z Twoja postacia! Np. jesli masz 20 lat, nie mozesz byc emerytem. Jesli jestes emerytem, musisz miec 60+ lat.
2. Na pytania tekstowe (otwarte) pisz WLASNE, UNIKALNE, NATURALNE odpowiedzi - tak jak napisalby prawdziwy czlowiek. NIE pisz ogolnikow typu "Brak uwag" czy "Nie wiem". Napisz cos konkretnego, osobistego, co pasuje do Twojej postaci. 1-2 zdania wystarczy.
3. Odpowiedzi tekstowe powinny brzmiec naturalnie, z drobnymi niedoskonalosciami jak w prawdziwej ankiecie.{hints_note}

Oto pytania:
{questions_text}

Odpowiedz WYLACZNIE prawidlowym JSON-em (bez markdown, bez komentarzy), w formacie:
{{
  "1": <odpowiedz na pytanie 1>,
  "2": <odpowiedz na pytanie 2>,
  ...
}}

Formaty odpowiedzi:
- radio: numer opcji (0-based), np. 2
- checkbox: lista numerow opcji, np. [0, 2]
- matrix: obiekt z wierszami jako klucze i numerem kolumny jako wartosc, np. {{"Wiersz1": 1, "Wiersz2": 3}}
- text: KROTKI string z unikalna odpowiedzia w JEDNEJ LINII (BEZ znakow nowej linii!), np. "Moim zdaniem komunikacja moglaby byc lepsza"

UWAGA: Odpowiadaj TYLKO jako JSON, bez zadnych dodatkowych znakow! Kazda wartosc tekstowa musi byc w jednej linii!"""

    if _emit_fn:
        _emit_fn("status", "AI: Wysylanie do Gemini...")

    # Models to try in order
    models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
    ]
    backoff_times = [3, 5, 10, 15, 20]

    client = genai.Client(api_key=api_key)

    last_error = None
    for attempt, model in enumerate(models):
        try:
            if _emit_fn:
                _emit_fn("status", f"AI: Wysylanie do {model}...")
            print(f"[FormBot] AI: Trying model {model} (attempt {attempt + 1}/{len(models)})...")

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=16384,
                    response_mime_type="application/json",
                ),
            )

            ai_text = response.text or ""

            # Save raw response to file for debugging
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_response_debug.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(ai_text)
            print(f"[FormBot] AI: Raw response saved to {debug_path}")

            # Clean up - remove markdown code fences if present
            ai_text = ai_text.strip()
            if ai_text.startswith("```"):
                ai_text = ai_text.split("\n", 1)[1] if "\n" in ai_text else ai_text[3:]
            if ai_text.endswith("```"):
                ai_text = ai_text[:-3]
            ai_text = ai_text.strip()

            # Parse JSON
            try:
                ai_answers = json.loads(ai_text)
            except json.JSONDecodeError as je:
                print(f"[FormBot] AI: JSON parse failed: {je}")
                if _emit_fn:
                    _emit_fn("status", "AI: Naprawiam format odpowiedzi...")
                ai_text_fixed = ai_text.replace('\r\n', ' ').replace('\r', '').replace('\n', ' ')
                ai_answers = json.loads(ai_text_fixed)

            if _emit_fn:
                _emit_fn("status", f"AI: ✅ Otrzymano odpowiedzi na {len(ai_answers)} pytan (model: {model})")

            print(f"[FormBot] AI answers ({model}): {json.dumps(ai_answers, ensure_ascii=False, indent=2)}")
            return ai_answers

        except Exception as e:
            last_error = e
            err_str = str(e)
            is_retryable = any(s in err_str for s in ["429", "500", "503", "RESOURCE_EXHAUSTED", "overloaded", "unavailable"])
            print(f"[FormBot] AI error with {model}: {err_str[:120]}")

            if is_retryable and attempt < len(models) - 1:
                wait = backoff_times[attempt]
                next_model = models[attempt + 1]
                if _emit_fn:
                    _emit_fn("status", f"AI: ⏳ Blad {model}, czekam {wait}s... (nastepny: {next_model})")
                time.sleep(wait)
                continue
            if _emit_fn:
                _emit_fn("status", f"AI: ❌ {err_str[:60]}")
            break

    # All models failed - check if it was quota-related
    is_quota = any(s in str(last_error) for s in ["429", "RESOURCE_EXHAUSTED", "quota"])
    print(f"[FormBot] AI ERROR: {last_error}")

    if is_quota and _emit_fn:
        # Ask user for new key
        _emit_fn("need_key", "Limit API wyczerpany na wszystkich modelach. Wpisz nowy klucz API aby kontynuowac.")
        print("[FormBot] AI: Waiting for new API key from user (max 120s)...")

        # Wait for new key via global pending dict
        import time as _time
        request_id = id(_emit_fn)  # unique per request
        _pending_ai_keys[request_id] = None
        deadline = _time.time() + 120
        while _time.time() < deadline:
            if _pending_ai_keys.get(request_id) is not None:
                new_key = _pending_ai_keys.pop(request_id)
                print(f"[FormBot] AI: Received new API key, retrying...")
                _emit_fn("status", "AI: Nowy klucz otrzymany, ponawiam...")
                return _ask_gemini_for_answers(questions_data, new_key, _emit_fn, weights=weights)
            _time.sleep(1)
        _pending_ai_keys.pop(request_id, None)
        _emit_fn("status", "AI: ❌ Timeout - nie otrzymano nowego klucza, uzywam losowych odpowiedzi")
    elif _emit_fn:
        _emit_fn("status", f"AI: ❌ {str(last_error)[:80]} — uzywam losowych odpowiedzi")
    return None

# Global dict for pending API key exchanges
_pending_ai_keys = {}





# ─── Browser Queue ─────────────────────────────────────────────────────────────
# Tracks who is waiting for the browser so we can show queue position to users.

class BrowserQueue:
    """Managed queue that tracks waiting users and lets them know their position."""

    def __init__(self):
        self._lock = threading.Lock()          # protects internal state
        self._semaphore = threading.Semaphore(1)  # only 1 browser at a time
        self._waiters = collections.OrderedDict()  # id -> {"user": ..., "event_queue": ...}
        self._current_user = None              # user label of whoever holds the browser
        self._current_activity = ""            # what the active user is doing

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
            self._current_activity = "Uruchamianie..."
            # Remove ourselves from waiters
            self._waiters.pop(waiter_id, None)

        # Notify remaining waiters of updated positions
        self._broadcast_positions()

    def release(self):
        """Release the browser for the next waiter."""
        with self._lock:
            self._current_user = None
            self._current_activity = ""
        self._semaphore.release()
        self._broadcast_positions()

    def set_activity(self, text):
        """Update what the active user is currently doing."""
        with self._lock:
            self._current_activity = text

    def _broadcast_positions(self):
        """Send queue position updates to all waiting users."""
        with self._lock:
            waiter_ids = list(self._waiters.keys())
            current = self._current_user
            activity = self._current_activity

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
                            "current_activity": activity or "",
                        },
                    })
                except Exception:
                    pass

    @property
    def current_user(self):
        with self._lock:
            return self._current_user

    @property
    def current_activity(self):
        with self._lock:
            return self._current_activity

    @property
    def queue_size(self):
        with self._lock:
            return len(self._waiters)

    def get_status(self):
        """Return a snapshot of the queue state."""
        with self._lock:
            return {
                "busy": self._current_user is not None,
                "current_user": self._current_user or "",
                "current_activity": self._current_activity or "",
                "waiting": len(self._waiters),
            }


browser_queue = BrowserQueue()


@app.route("/")
def home():
    html = HOME_PAGE_HTML
    if GEMINI_DEFAULT_KEY:
        html = html.replace("{{AI_KEY_PLACEHOLDER}}", "Domyslny klucz z env (zostaw puste)")
        html = html.replace("{{AI_KEY_HINT}}", "&#9989; Domyslny klucz zaladowany z GEMINI_API_KEY. Mozesz nadpisac wpisujac wlasny.")
        html = html.replace("{{HAS_DEFAULT_KEY}}", "true")
    else:
        html = html.replace("{{AI_KEY_PLACEHOLDER}}", "Wklej klucz API Gemini...")
        html = html.replace("{{AI_KEY_HINT}}", "Klucz mozna uzyskac na <a href='https://aistudio.google.com/apikey' target='_blank' style='color:#7c3aed; text-decoration:underline;'>aistudio.google.com/apikey</a>")
        html = html.replace("{{HAS_DEFAULT_KEY}}", "false")
    return render_template_string(html)


@app.route("/queue-status")
@cross_origin()
def queue_status():
    """Return current queue status as JSON."""
    return jsonify(browser_queue.get_status())


@app.route("/update-ai-key", methods=["POST"])
@cross_origin()
def update_ai_key():
    """Receive a new API key from user during quota exhaustion."""
    new_key = request.json.get("key", "").strip() if request.is_json else ""
    if not new_key:
        return jsonify({"error": "No key provided"}), 400
    # Set key for ALL pending requests
    for req_id in list(_pending_ai_keys.keys()):
        _pending_ai_keys[req_id] = new_key
    print(f"[FormBot] Received new API key from user (starts with {new_key[:8]}...)")
    return jsonify({"ok": True})


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
      max-width: 740px;
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
    .btn-secondary {
      padding: 14px 28px;
      background: rgba(255,255,255,0.85);
      border: 2px solid #0d9488;
      border-radius: 12px;
      color: #0d9488;
      font-size: 0.95rem;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.3s, background 0.3s;
      white-space: nowrap;
    }
    .btn-secondary:hover {
      transform: translateY(-1px);
      background: rgba(13, 148, 136, 0.08);
      box-shadow: 0 6px 25px rgba(13, 148, 136, 0.15);
    }
    .btn-secondary:active { transform: translateY(0); }
    .btn-secondary:disabled {
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

    /* ─── Preview / Sliders ──────────────────────────────────── */
    #preview-area { display: none; }
    #preview-area.active { display: block; }
    .preview-q-card {
      padding: 18px 20px;
      margin-bottom: 14px;
      background: rgba(240, 253, 250, 0.6);
      border-radius: 14px;
      border: 1px solid rgba(13, 148, 136, 0.1);
      animation: fadeSlideIn 0.35s ease;
    }
    .preview-q-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
    .preview-q-num {
      width: 32px; height: 32px;
      background: linear-gradient(135deg, #0d9488, #0891b2);
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 700;
      color: #fff;
      flex-shrink: 0;
    }
    .preview-q-title {
      font-weight: 600;
      font-size: 0.95rem;
      color: #1e293b;
      flex: 1;
    }
    .preview-q-type {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #94a3b8;
      padding: 3px 10px;
      background: rgba(13, 148, 136, 0.08);
      border-radius: 6px;
      font-weight: 600;
    }
    .slider-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(0,0,0,0.04);
    }
    .slider-row:last-child { border-bottom: none; }
    .slider-label {
      flex: 1;
      font-size: 0.88rem;
      color: #334155;
      min-width: 0;
      word-break: break-word;
    }
    .slider-control {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .slider-control input[type="range"] {
      width: 120px;
      height: 6px;
      -webkit-appearance: none;
      appearance: none;
      background: linear-gradient(90deg, #0d9488, #0891b2);
      border-radius: 3px;
      outline: none;
      opacity: 0.85;
      transition: opacity 0.2s;
    }
    .slider-control input[type="range"]:hover { opacity: 1; }
    .slider-control input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 18px; height: 18px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid #0d9488;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,0.15);
      transition: transform 0.15s;
    }
    .slider-control input[type="range"]::-webkit-slider-thumb:hover {
      transform: scale(1.15);
    }
    .slider-control input[type="range"]::-moz-range-thumb {
      width: 18px; height: 18px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid #0d9488;
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .slider-value {
      font-size: 0.82rem;
      font-weight: 600;
      color: #0d9488;
      min-width: 38px;
      text-align: right;
    }
    .preview-text-note {
      font-size: 0.85rem;
      color: #64748b;
      font-style: italic;
      padding: 6px 0;
    }
    .text-answers-area {
      padding: 4px 0;
    }
    .text-answers-label {
      font-size: 0.82rem;
      color: #64748b;
      margin-bottom: 8px;
    }
    .text-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 10px;
    }
    .text-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      background: rgba(13, 148, 136, 0.1);
      border: 1px solid rgba(13, 148, 136, 0.2);
      border-radius: 20px;
      font-size: 0.82rem;
      color: #0d9488;
      animation: fadeSlideIn 0.2s ease;
    }
    .text-chip-remove {
      width: 16px; height: 16px;
      border: none;
      background: rgba(13, 148, 136, 0.2);
      border-radius: 50%;
      color: #0d9488;
      font-size: 0.7rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
      padding: 0;
      line-height: 1;
    }
    .text-chip-remove:hover {
      background: rgba(220, 38, 38, 0.2);
      color: #dc2626;
    }
    .text-add-row {
      display: flex;
      gap: 8px;
    }
    .text-add-row input {
      flex: 1;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(13, 148, 136, 0.25);
      border-radius: 8px;
      font-size: 0.85rem;
      font-family: 'Inter', sans-serif;
      color: #1e293b;
      outline: none;
      transition: border-color 0.3s;
    }
    .text-add-row input:focus {
      border-color: #0d9488;
    }
    .text-add-row input::placeholder { color: #94a3b8; }
    .text-add-btn {
      padding: 8px 16px;
      background: linear-gradient(135deg, #0d9488, #0891b2);
      border: none;
      border-radius: 8px;
      color: #fff;
      font-size: 0.82rem;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.2s;
      white-space: nowrap;
    }
    .text-add-btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 3px 12px rgba(13, 148, 136, 0.25);
    }
    .matrix-row-group {
      margin-bottom: 12px;
      padding: 10px 14px;
      background: rgba(13, 148, 136, 0.03);
      border-radius: 10px;
      border-left: 3px solid rgba(13, 148, 136, 0.3);
    }
    .matrix-row-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: #0d9488;
      margin-bottom: 6px;
    }
    .btn-group {
      display: flex;
      gap: 10px;
      margin-top: 8px;
    }
    .btn-group .btn, .btn-group .btn-secondary { flex: 1; text-align: center; }
    .preview-actions {
      display: flex;
      gap: 10px;
      margin-top: 22px;
    }
    .preview-actions .btn { flex: 1; text-align: center; }
    .reset-link {
      display: inline-block;
      margin-top: 10px;
      font-size: 0.82rem;
      color: #94a3b8;
      cursor: pointer;
      text-decoration: underline;
      transition: color 0.2s;
    }
    .reset-link:hover { color: #0d9488; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">
      <h1>FormBot</h1>
      <p>Automatyczne wypelnianie formularzy</p>
    </div>

    <div class="card" id="url-card">
      <div class="input-group">
        <input type="text" id="url-input" placeholder="Wklej link do formularza (Google Forms / MS Forms)...">
      </div>
      <div id="queue-status-bar" style="display:none; margin-top:10px; padding:12px 16px; background:linear-gradient(135deg, rgba(251,191,36,0.12), rgba(245,158,11,0.08)); border:1px solid rgba(245,158,11,0.25); border-radius:10px; font-size:0.85rem; color:#92400e;">
        <div style="display:flex; align-items:center; gap:8px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span id="queue-status-text"></span>
        </div>
      </div>
      <div class="btn-group" style="margin-top: 12px;">
        <button class="btn-secondary" id="preview-btn" onclick="previewForm()">&#128269; Podglad arkusza</button>
        <button class="btn" id="start-btn" onclick="startFill()">&#9654; Start</button>
      </div>
      <div style="margin-top:14px; padding:14px 16px; background:linear-gradient(135deg, rgba(139,92,246,0.08), rgba(109,40,217,0.04)); border:1px solid rgba(139,92,246,0.2); border-radius:12px;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:0.9rem; font-weight:500; color:#5b21b6;">
            <input type="checkbox" id="ai-mode-toggle" onchange="toggleAiMode()" style="width:18px; height:18px; accent-color:#7c3aed;">
            &#129302; Tryb AI (Gemini)
          </label>
          <span style="font-size:0.75rem; color:#8b5cf6; background:rgba(139,92,246,0.12); padding:2px 8px; border-radius:6px;">spojne odpowiedzi</span>
        </div>
        <div id="ai-key-row" style="display:none; margin-top:8px;">
          <div style="display:flex; gap:6px; align-items:center;">
            <input type="password" id="gemini-api-key" placeholder="{{AI_KEY_PLACEHOLDER}}" style="flex:1; padding:10px 14px; border:1px solid rgba(139,92,246,0.25); border-radius:8px; font-size:0.85rem; font-family:'Inter',sans-serif; outline:none; background:rgba(255,255,255,0.9); color:#1e293b;">
            <button type="button" onclick="var k=document.getElementById('gemini-api-key'); var t=k.type==='password'?'text':'password'; k.type=t; this.textContent=t==='password'?'&#128065;':'&#128064;'" style="padding:8px 10px; border:1px solid rgba(139,92,246,0.25); border-radius:8px; background:rgba(139,92,246,0.08); cursor:pointer; font-size:1rem; line-height:1;" title="Pokaz/ukryj klucz">&#128065;</button>
          </div>
          <div style="font-size:0.72rem; color:#8b5cf6; margin-top:4px;">{{AI_KEY_HINT}}</div>
        </div>
      </div>
    </div>

    <!-- Preview area with sliders -->
    <div id="preview-area" class="card">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:18px;">
        <h2 style="font-size:1.15rem; color:#1e293b;">&#128196; Podglad formularza</h2>
        <span class="reset-link" onclick="resetAllSliders()">Resetuj suwaki</span>
      </div>
      <div id="preview-queue-bar" style="display:none; background:linear-gradient(135deg,#fbbf24,#f59e0b); color:#78350f; padding:12px 16px; border-radius:10px; margin-bottom:14px; font-size:0.88rem; font-weight:500; align-items:center; gap:10px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span id="preview-queue-text"></span>
      </div>
      <div id="preview-status" class="status-bar" style="display:none;">
        <div class="spinner" id="preview-spinner"></div>
        <span class="status-text" id="preview-status-text">Wczytywanie...</span>
      </div>
      <div id="preview-questions"></div>
      <div class="preview-actions" id="preview-actions" style="display:none;">
        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
          <button class="btn" onclick="startFillWithWeights()">&#9654; Wypelnij z ustawieniami</button>
          <div style="display:flex; align-items:center; gap:6px;">
            <label for="repeat-count" style="font-size:0.85rem; color:#64748b; white-space:nowrap;">Powtorz:</label>
            <input type="number" id="repeat-count" min="1" max="10" value="1" style="width:52px; padding:8px 6px; border:1px solid rgba(13,148,136,0.25); border-radius:8px; font-size:0.9rem; font-family:'Inter',sans-serif; text-align:center; outline:none; background:rgba(255,255,255,0.9); color:#1e293b;">
            <span style="font-size:0.78rem; color:#94a3b8;">max 10</span>
          </div>
        </div>
        <div id="repeat-progress" style="display:none; margin-top:10px; font-size:0.85rem; color:#0d9488; font-weight:600;"></div>
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

    <div style="text-align:center; margin: 20px 0 8px;">
      <button onclick="window.scrollTo({top:0,behavior:'smooth'})" style="padding:10px 28px; background:linear-gradient(135deg,#0d9488,#0891b2); border:none; border-radius:10px; color:#fff; font-size:0.88rem; font-weight:600; font-family:'Inter',sans-serif; cursor:pointer; transition:transform 0.15s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 4px 14px rgba(13,148,136,0.3)'" onmouseout="this.style.transform='';this.style.boxShadow=''">&#8593; Na g&oacute;re</button>
    </div>
    <div class="footer">FormBot &mdash; Copyright by K5 Studio 2026</div>
  </div>

  <script>
    // Global state for preview data and weights
    let previewData = null; // Array of {num, title, type, options: [...]}

    // ─── AI Mode ──────────────────────────────────────────────
    function toggleAiMode() {
      const on = document.getElementById('ai-mode-toggle').checked;
      document.getElementById('ai-key-row').style.display = on ? 'block' : 'none';
    }

    function isAiMode() {
      return document.getElementById('ai-mode-toggle').checked;
    }

    var _hasDefaultKey = {{HAS_DEFAULT_KEY}};
    function getGeminiKey() {
      return (document.getElementById('gemini-api-key').value || '').trim();
    }
    function hasDefaultKey() { return _hasDefaultKey; }
    function submitNewAiKey() {
      var inp = document.getElementById('new-ai-key-input');
      var key = (inp && inp.value || '').trim();
      if (!key || key.length < 10) { alert('Wklej prawidlowy klucz API!'); return; }
      fetch('/update-ai-key', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({key:key})})
        .then(function(r){return r.json();})
        .then(function(d){
          if(d.ok){
            inp.disabled=true;
            inp.parentElement.innerHTML='<span style="color:#059669; font-weight:600;">&#9989; Klucz wyslany! Ponawiam...</span>';
          }
        });
    }
    // ─── Queue status polling ──────────────────────────────
    function pollQueueStatus() {
      fetch('queue-status')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          const bar = document.getElementById('queue-status-bar');
          const text = document.getElementById('queue-status-text');
          if (d.busy) {
            bar.style.display = 'block';
            let msg = 'FormBot Zaj\u0119ty';
            if (d.current_activity) msg += ' \u2014 ' + d.current_activity;
            if (d.waiting > 0) msg += ' | W kolejce: ' + d.waiting;
            text.textContent = msg;
          } else {
            bar.style.display = 'none';
          }
        })
        .catch(function() {});
    }
    pollQueueStatus();
    setInterval(pollQueueStatus, 3000);

    // ─── Preview Form ──────────────────────────────────────
    function previewForm() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }

      const previewBtn = document.getElementById('preview-btn');
      const startBtn = document.getElementById('start-btn');
      const previewArea = document.getElementById('preview-area');
      const previewStatus = document.getElementById('preview-status');
      const previewQuestions = document.getElementById('preview-questions');
      const previewActions = document.getElementById('preview-actions');

      previewBtn.disabled = true;
      startBtn.disabled = true;
      previewArea.classList.add('active');
      previewStatus.style.display = 'flex';
      previewQuestions.innerHTML = '';
      previewActions.style.display = 'none';
      document.getElementById('preview-status-text').textContent = 'Wczytywanie formularza...';
      previewData = [];

      const encodedUrl = encodeURIComponent(url);
      const evtSource = new EventSource('preview-form?url=' + encodedUrl);

      evtSource.addEventListener('status', function(e) {
        document.getElementById('preview-status-text').textContent = e.data;
      });

      evtSource.addEventListener('queue', function(e) {
        const d = JSON.parse(e.data);
        const pqBar = document.getElementById('preview-queue-bar');
        const pqText = document.getElementById('preview-queue-text');
        pqBar.style.display = 'flex';
        document.getElementById('preview-status-text').textContent = 'Oczekiwanie w kolejce...';
        let qMsg = 'Pozycja w kolejce: ' + d.position + '/' + d.total_waiting;
        if (d.current_activity) qMsg += ' | Aktualnie: ' + d.current_activity;
        pqText.textContent = qMsg;
      });

      evtSource.addEventListener('queue_done', function(e) {
        document.getElementById('preview-queue-bar').style.display = 'none';
      });

      evtSource.addEventListener('question_preview', function(e) {
        const d = JSON.parse(e.data);
        previewData.push(d);
        renderPreviewQuestion(d);
      });

      evtSource.addEventListener('preview_done', function(e) {
        evtSource.close();
        previewStatus.style.display = 'none';
        previewActions.style.display = 'flex';
        previewBtn.disabled = false;
        startBtn.disabled = false;
      });

      evtSource.addEventListener('error_ev', function(e) {
        evtSource.close();
        document.getElementById('preview-status-text').textContent = 'Blad: ' + e.data;
        document.getElementById('preview-spinner').style.display = 'none';
        previewBtn.disabled = false;
        startBtn.disabled = false;
      });

      evtSource.onerror = function() {
        evtSource.close();
        document.getElementById('preview-status-text').textContent = 'Polaczenie przerwane';
        document.getElementById('preview-spinner').style.display = 'none';
        previewBtn.disabled = false;
        startBtn.disabled = false;
      };
    }

    function renderPreviewQuestion(q) {
      const container = document.getElementById('preview-questions');
      const card = document.createElement('div');
      card.className = 'preview-q-card';
      card.id = 'preview-q-' + q.num;

      let headerHtml = '<div class="preview-q-header">'
        + '<div class="preview-q-num">' + q.num + '</div>'
        + '<div class="preview-q-title">' + escHtml(q.title) + '</div>'
        + '<div class="preview-q-type">' + q.type + '</div>'
        + '</div>';

      let bodyHtml = '';
      if ((q.type === 'radio' || q.type === 'checkbox') && q.options && q.options.length > 0) {
        const groupId = 'group-q' + q.num;
        q.options.forEach(function(opt, idx) {
          const sliderId = 'slider-q' + q.num + '-opt' + idx;
          const defaultVal = Math.round(100 / q.options.length);
          bodyHtml += '<div class="slider-row">'
            + '<div class="slider-label">' + escHtml(opt) + '</div>'
            + '<div class="slider-control">'
            + '<input type="range" id="' + sliderId + '" min="0" max="100" value="' + defaultVal + '"'
            + ' oninput="balanceSliders(this)"'
            + ' data-group="' + groupId + '" data-count="' + q.options.length + '">'
            + '<span class="slider-value" id="' + sliderId + '-val">' + defaultVal + '%</span>'
            + '</div></div>';
        });
      } else if (q.type === 'matrix' && q.options && q.options.length > 0 && q.rows && q.rows.length > 0) {
        q.rows.forEach(function(row, rowIdx) {
          const groupId = 'group-q' + q.num + '-row' + rowIdx;
          bodyHtml += '<div class="matrix-row-group">';
          bodyHtml += '<div class="matrix-row-title">' + escHtml(row) + '</div>';
          q.options.forEach(function(opt, colIdx) {
            const sliderId = 'slider-q' + q.num + '-row' + rowIdx + '-opt' + colIdx;
            const defaultVal = Math.round(100 / q.options.length);
            bodyHtml += '<div class="slider-row">'
              + '<div class="slider-label">' + escHtml(opt) + '</div>'
              + '<div class="slider-control">'
              + '<input type="range" id="' + sliderId + '" min="0" max="100" value="' + defaultVal + '"'
              + ' oninput="balanceSliders(this)"'
              + ' data-group="' + groupId + '" data-count="' + q.options.length + '">'
              + '<span class="slider-value" id="' + sliderId + '-val">' + defaultVal + '%</span>'
              + '</div></div>';
          });
          bodyHtml += '</div>';
        });
      } else if (q.type === 'text') {
        bodyHtml = '<div class="text-answers-area" id="text-area-q' + q.num + '">'
          + '<div class="text-answers-label">Mozliwe odpowiedzi (losowa zostanie wybrana):</div>'
          + '<div class="text-chips" id="text-chips-q' + q.num + '"></div>'
          + '<div class="text-add-row">'
          + '<input type="text" id="text-input-q' + q.num + '" placeholder="Dodaj odpowiedz..."'
          + ' onkeydown="if(event.key===\'Enter\')addTextAnswer(' + q.num + ')">'
          + '<button class="text-add-btn" onclick="addTextAnswer(' + q.num + ')">+ Dodaj</button>'
          + '<button class="text-add-btn" style="background:linear-gradient(135deg,#dc2626,#ef4444);" onclick="clearTextAnswers(' + q.num + ')">Usun wszystkie</button>'
          + '</div></div>';
      } else {
        bodyHtml = '<div class="preview-text-note">Typ: ' + escHtml(q.type) + '</div>';
      }

      card.innerHTML = headerHtml + bodyHtml;
      container.appendChild(card);

      // For text questions, populate default chips after DOM insertion
      if (q.type === 'text' && q.text_answers) {
        q._answers = q.text_answers.slice(); // mutable copy
        renderTextChips(q.num);
      }
    }

    function renderTextChips(qNum) {
      const q = previewData.find(function(p) { return p.num === qNum; });
      if (!q || !q._answers) return;
      const container = document.getElementById('text-chips-q' + qNum);
      container.innerHTML = '';
      q._answers.forEach(function(ans, idx) {
        const chip = document.createElement('span');
        chip.className = 'text-chip';
        chip.innerHTML = escHtml(ans)
          + '<button class="text-chip-remove" onclick="removeTextAnswer(' + qNum + ',' + idx + ')">&times;</button>';
        container.appendChild(chip);
      });
    }

    function addTextAnswer(qNum) {
      const input = document.getElementById('text-input-q' + qNum);
      const val = input.value.trim();
      if (!val) return;
      const q = previewData.find(function(p) { return p.num === qNum; });
      if (!q) return;
      if (!q._answers) q._answers = [];
      q._answers.push(val);
      input.value = '';
      renderTextChips(qNum);
    }

    function removeTextAnswer(qNum, idx) {
      const q = previewData.find(function(p) { return p.num === qNum; });
      if (!q || !q._answers) return;
      q._answers.splice(idx, 1);
      renderTextChips(qNum);
    }

    function clearTextAnswers(qNum) {
      const q = previewData.find(function(p) { return p.num === qNum; });
      if (!q) return;
      q._answers = [];
      renderTextChips(qNum);
    }

    function balanceSliders(changedSlider) {
      const groupId = changedSlider.getAttribute('data-group');
      const allInGroup = document.querySelectorAll('input[data-group="' + groupId + '"]');
      const count = allInGroup.length;
      if (count <= 1) {
        changedSlider.value = 100;
        document.getElementById(changedSlider.id + '-val').textContent = '100%';
        return;
      }

      const newVal = parseInt(changedSlider.value);
      const remaining = 100 - newVal;

      // Sum of all OTHER sliders (before adjustment)
      let othersOldSum = 0;
      const others = [];
      allInGroup.forEach(function(s) {
        if (s !== changedSlider) {
          othersOldSum += parseInt(s.value);
          others.push(s);
        }
      });

      // Distribute 'remaining' proportionally among others
      if (othersOldSum === 0) {
        // All others are 0 — distribute evenly
        const each = Math.floor(remaining / others.length);
        let leftover = remaining - each * others.length;
        others.forEach(function(s) {
          const v = each + (leftover > 0 ? 1 : 0);
          if (leftover > 0) leftover--;
          s.value = v;
          document.getElementById(s.id + '-val').textContent = v + '%';
        });
      } else {
        // Proportional redistribution
        let distributed = 0;
        others.forEach(function(s, i) {
          const oldVal = parseInt(s.value);
          let newOtherVal;
          if (i === others.length - 1) {
            // Last one gets the remainder to ensure exact 100%
            newOtherVal = remaining - distributed;
          } else {
            newOtherVal = Math.round((oldVal / othersOldSum) * remaining);
          }
          newOtherVal = Math.max(0, Math.min(100, newOtherVal));
          distributed += newOtherVal;
          s.value = newOtherVal;
          document.getElementById(s.id + '-val').textContent = newOtherVal + '%';
        });
      }

      document.getElementById(changedSlider.id + '-val').textContent = newVal + '%';
    }

    function resetAllSliders() {
      if (!previewData) return;
      previewData.forEach(function(q) {
        if ((q.type === 'radio' || q.type === 'checkbox') && q.options) {
          const defaultVal = Math.round(100 / q.options.length);
          q.options.forEach(function(opt, idx) {
            const slider = document.getElementById('slider-q' + q.num + '-opt' + idx);
            if (slider) {
              slider.value = defaultVal;
              document.getElementById(slider.id + '-val').textContent = defaultVal + '%';
            }
          });
        } else if (q.type === 'matrix' && q.options && q.rows) {
          const defaultVal = Math.round(100 / q.options.length);
          q.rows.forEach(function(row, rowIdx) {
            q.options.forEach(function(opt, colIdx) {
              const slider = document.getElementById('slider-q' + q.num + '-row' + rowIdx + '-opt' + colIdx);
              if (slider) {
                slider.value = defaultVal;
                document.getElementById(slider.id + '-val').textContent = defaultVal + '%';
              }
            });
          });
        }
      });
    }

    function collectWeights() {
      // Build a weights object:
      // radio/checkbox: { "question_title": { "option_label": weight } }
      // matrix: { "question_title": { "row_title": { "col_label": weight } } }
      if (!previewData) return {};
      const weights = {};
      previewData.forEach(function(q) {
        if ((q.type === 'radio' || q.type === 'checkbox') && q.options && q.options.length > 0) {
          const qWeights = {};
          q.options.forEach(function(opt, idx) {
            const slider = document.getElementById('slider-q' + q.num + '-opt' + idx);
            qWeights[opt] = slider ? parseInt(slider.value) : 50;
          });
          weights[q.title] = qWeights;
        } else if (q.type === 'matrix' && q.options && q.rows) {
          const matrixWeights = {};
          q.rows.forEach(function(row, rowIdx) {
            const rowWeights = {};
            q.options.forEach(function(opt, colIdx) {
              const slider = document.getElementById('slider-q' + q.num + '-row' + rowIdx + '-opt' + colIdx);
              rowWeights[opt] = slider ? parseInt(slider.value) : 50;
            });
            matrixWeights[row] = rowWeights;
          });
          weights[q.title] = matrixWeights;
        } else if (q.type === 'text' && q._answers && q._answers.length > 0) {
          // Send text answers as array
          weights[q.title] = q._answers.slice();
        }
      });
      return weights;
    }

    // ─── Start fill with slider weights (supports repeat) ──
    function startFillWithWeights() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }
      const weights = collectWeights();
      let repeatCount = parseInt(document.getElementById('repeat-count').value) || 1;
      repeatCount = Math.max(1, Math.min(10, repeatCount));

      if (repeatCount === 1) {
        _doStartFill(url, weights);
        return;
      }

      // Run multiple fills sequentially
      const repeatProgress = document.getElementById('repeat-progress');
      repeatProgress.style.display = 'block';
      let currentRun = 0;

      function runNext() {
        currentRun++;
        if (currentRun > repeatCount) {
          repeatProgress.textContent = 'Wszystkie ' + repeatCount + ' rund zakonczone!';
          repeatProgress.style.color = '#16a34a';
          return;
        }
        repeatProgress.textContent = 'Runda ' + currentRun + '/' + repeatCount + '...';
        repeatProgress.style.color = '#0d9488';
        _doStartFill(url, weights, function() {
          // Small delay between runs
          setTimeout(runNext, 1500);
        });
      }

      runNext();
    }

    // ─── Start fill without weights (quick mode) ──────────
    function startFill() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }
      _doStartFill(url, null);
    }

    function _doStartFill(url, weights, onComplete) {
      const btn = document.getElementById('start-btn');
      const previewBtn = document.getElementById('preview-btn');
      const progArea = document.getElementById('progress-area');
      const resArea = document.getElementById('results-area');
      const eventLog = document.getElementById('event-log');
      const statusText = document.getElementById('status-text');
      const spinner = document.getElementById('spinner');
      const previewActionBtns = document.querySelectorAll('#preview-actions button');

      btn.disabled = true;
      previewBtn.disabled = true;
      previewActionBtns.forEach(function(b) { b.disabled = true; });
      progArea.classList.add('active');
      resArea.classList.remove('active');
      eventLog.innerHTML = '';
      statusText.className = 'status-text';
      statusText.textContent = 'Uruchamianie przegladarki...';
      spinner.style.display = 'block';

      let sseUrl = 'stream-fill?url=' + encodeURIComponent(url);
      if (weights && Object.keys(weights).length > 0) {
        sseUrl += '&weights=' + encodeURIComponent(JSON.stringify(weights));
      }
      if (isAiMode()) {
        var aiKey = getGeminiKey();
        if (!aiKey && !hasDefaultKey()) {
          alert('Wklej klucz API Gemini!\\nKlucz zaczyna sie od AIza... (nie URL strony)');
          btn.disabled = false; previewBtn.disabled = false;
          previewActionBtns.forEach(function(b) { b.disabled = false; });
          return;
        }
        if (aiKey && aiKey.startsWith('http')) {
          alert('To jest URL strony, nie klucz API!\\nWejdz na aistudio.google.com/apikey, skopiuj klucz (zaczyna sie od AIza...) i wklej go tutaj.');
          btn.disabled = false; previewBtn.disabled = false;
          previewActionBtns.forEach(function(b) { b.disabled = false; });
          return;
        }
        sseUrl += '&ai_mode=1&ai_key=' + encodeURIComponent(aiKey);
        statusText.textContent = 'AI: Przygotowywanie...';
      }
      const evtSource = new EventSource(sseUrl);

      function _finish() {
        btn.disabled = false;
        previewBtn.disabled = false;
        previewActionBtns.forEach(function(b) { b.disabled = false; });
        if (onComplete) onComplete();
      }

      evtSource.addEventListener('status', function(e) {
        statusText.textContent = e.data;
      });

      evtSource.addEventListener('queue', function(e) {
        const d = JSON.parse(e.data);
        const queueBar = document.getElementById('queue-bar');
        const queueText = document.getElementById('queue-text');
        queueBar.style.display = 'flex';
        statusText.textContent = 'Oczekiwanie w kolejce...';
        let qMsg = 'Pozycja w kolejce: ' + d.position + '/' + d.total_waiting;
        if (d.current_activity) qMsg += ' | Aktualnie: ' + d.current_activity;
        queueText.textContent = qMsg;
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
        const srcBadge = d.source === 'AI'
          ? '<span style="font-size:0.7rem; background:rgba(16,185,129,0.15); color:#059669; padding:1px 6px; border-radius:4px; margin-left:6px;">&#129302; AI</span>'
          : '<span style="font-size:0.7rem; background:rgba(245,158,11,0.15); color:#d97706; padding:1px 6px; border-radius:4px; margin-left:6px;">&#127922; Losowe</span>';
        div.innerHTML = '<div class="event-title">Odpowiedz Q' + d.num + srcBadge + '</div>'
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

      evtSource.addEventListener('need_key', function(e) {
        const div = document.createElement('div');
        div.className = 'event-item warn';
        div.innerHTML = '<div class="event-title">&#128274; Limit API wyczerpany</div>'
          + '<div class="event-detail">' + escHtml(e.data) + '</div>'
          + '<div style="margin-top:8px; display:flex; gap:6px;">'
          + '<input type="text" id="new-ai-key-input" placeholder="Wklej nowy klucz API (AIza...)" style="flex:1; padding:8px 12px; border:1px solid rgba(245,158,11,0.4); border-radius:8px; font-size:0.85rem; font-family:Inter,sans-serif;">'
          + '<button onclick="submitNewAiKey()" style="padding:8px 16px; background:linear-gradient(135deg,#7c3aed,#6d28d9); color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; font-size:0.85rem;">Wyslij</button>'
          + '</div>'
          + '<div style="font-size:0.7rem; color:#92400e; margin-top:4px;">Masz 2 min na wpisanie nowego klucza. Bez niego odpowiedzi beda losowe.</div>';
        eventLog.appendChild(div);
        eventLog.scrollTop = eventLog.scrollHeight;
      });

      evtSource.addEventListener('done', function(e) {
        evtSource.close();
        const d = JSON.parse(e.data);
        spinner.style.display = 'none';
        statusText.textContent = 'Gotowe! (' + d.questions_filled + ' pytan)';
        statusText.className = 'status-text done';
        showResults(d);
        _finish();
      });

      evtSource.addEventListener('error_ev', function(e) {
        evtSource.close();
        spinner.style.display = 'none';
        statusText.textContent = 'Blad: ' + e.data;
        statusText.className = 'status-text error';
        _finish();
      });

      evtSource.onerror = function() {
        evtSource.close();
        spinner.style.display = 'none';
        statusText.textContent = 'Polaczenie przerwane';
        statusText.className = 'status-text error';
        _finish();
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
      if (e.key === 'Enter') previewForm();
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


@app.route("/preview-form", methods=["GET"])
def preview_form():
    """SSE endpoint that reads form questions and streams them for preview."""
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
            event_queue.put({"event": "queue_done", "data": ""})
            _preview_form_questions(form_url, event_queue=event_queue)
        finally:
            browser_queue.release()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    def generate():
        while True:
            msg = event_queue.get()
            if msg is None:
                break
            event_type = msg.get("event", "status")
            data = msg.get("data", "")
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            yield f'event: {event_type}\ndata: {data}\n\n'

    return Response(generate(), mimetype='text/event-stream')


@app.route("/stream-fill", methods=["GET"])
def stream_fill():
    """SSE endpoint that streams live progress while filling the form."""
    form_url = request.args.get("url", "")
    if not form_url:
        def err_gen():
            yield 'event: error_ev\ndata: Podaj URL formularza\n\n'
        return Response(err_gen(), mimetype='text/event-stream')

    # Parse optional weights from query string
    weights_raw = request.args.get("weights", "")
    weights = None
    if weights_raw:
        try:
            weights = json.loads(weights_raw)
        except (json.JSONDecodeError, ValueError):
            weights = None

    # Parse optional AI mode
    ai_mode = request.args.get("ai_mode", "") == "1"
    ai_key = request.args.get("ai_key", "") or GEMINI_DEFAULT_KEY

    event_queue = Queue()
    user_label = request.remote_addr or "Uzytkownik"
    waiter_id = str(uuid.uuid4())

    def worker():
        browser_queue.acquire(user_label, waiter_id, event_queue=event_queue)
        try:
            # Tell the client they left the queue
            event_queue.put({"event": "queue_done", "data": ""})
            _perform_form_fill(form_url, event_queue=event_queue, weights=weights,
                             ai_mode=ai_mode, ai_key=ai_key)
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


def _weighted_choice(items_with_labels, weights_for_question):
    """
    Pick an item using user-defined weights.
    items_with_labels: list of (element, label_text) tuples
    weights_for_question: dict {label_text: weight_int} or None
    Returns the chosen (element, label_text) tuple.
    """
    if not weights_for_question:
        return random.choice(items_with_labels)

    # Build a weight list matching item order
    weight_list = []
    for _el, label in items_with_labels:
        w = weights_for_question.get(label, 50)
        weight_list.append(max(w, 0))

    total = sum(weight_list)
    if total == 0:
        # All weights are zero — fall back to uniform
        return random.choice(items_with_labels)

    # Weighted random selection
    r = random.uniform(0, total)
    cumulative = 0
    for i, w in enumerate(weight_list):
        cumulative += w
        if r <= cumulative:
            return items_with_labels[i]
    return items_with_labels[-1]  # fallback


# ─── AI Answer Handlers ──────────────────────────────────────────────────────

def _handle_radio_ai(question_el, ai_index):
    """Click radio by AI-selected index (0-based)."""
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    if not radios:
        return None
    idx = int(ai_index) if isinstance(ai_index, (int, float, str)) else 0
    idx = max(0, min(idx, len(radios) - 1))
    chosen = radios[idx]
    label = _get_input_label(question_el, chosen)
    try:
        chosen.click()
    except Exception:
        try:
            question_el.parent.execute_script("arguments[0].click();", chosen)
        except Exception:
            pass
    return label


def _handle_checkbox_ai(question_el, ai_indices):
    """Click checkboxes by AI-selected indices (list of 0-based)."""
    checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
    if not checkboxes:
        return []
    if not isinstance(ai_indices, list):
        ai_indices = [ai_indices]
    selected = []
    for idx in ai_indices:
        idx = int(idx)
        if 0 <= idx < len(checkboxes):
            cb = checkboxes[idx]
            label = _get_input_label(question_el, cb)
            try:
                cb.click()
            except Exception:
                try:
                    question_el.parent.execute_script("arguments[0].click();", cb)
                except Exception:
                    pass
            selected.append(label)
    return selected


def _handle_matrix_ai(question_el, ai_row_answers):
    """Fill matrix by AI answers: dict of row_title -> column_index (0-based)."""
    if not isinstance(ai_row_answers, dict) or not ai_row_answers:
        print(f"[FormBot] MATRIX AI: Invalid ai_row_answers: {type(ai_row_answers)}")
        return {}

    # Find all radio buttons in this matrix question (same approach as non-AI handler)
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    if not radios:
        print(f"[FormBot] MATRIX AI: No radio buttons found in matrix!")
        return {}

    # Collect aria-labels
    aria_labels = []
    for r in radios:
        aria = r.get_attribute("aria-label") or ""
        aria_labels.append(aria)

    # Find column headers
    column_headers = []
    try:
        header_cells = question_el.find_elements(By.CSS_SELECTOR, 'div[role="columnheader"], th')
        for cell in header_cells:
            text = cell.text.strip()
            if text:
                column_headers.append(text)
    except Exception:
        pass

    print(f"[FormBot] MATRIX AI: {len(radios)} radios, {len(column_headers)} columns: {column_headers[:5]}")

    # Group radios by row title
    rows = {}  # row_title -> list of (radio_element, col_name, col_index)
    if column_headers:
        for radio, aria in zip(radios, aria_labels):
            row_title = aria
            col_name = ""
            col_idx_in_row = -1
            for ci, col in enumerate(column_headers):
                if aria.endswith(col):
                    row_title = aria[: -len(col)].strip()
                    col_name = col
                    col_idx_in_row = ci
                    break
            if row_title not in rows:
                rows[row_title] = []
            rows[row_title].append((radio, col_name, col_idx_in_row))
    else:
        # Fallback: group by name attribute
        name_groups = {}
        for radio, aria in zip(radios, aria_labels):
            name = radio.get_attribute("name") or "unknown"
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append((radio, aria))
        for name, items in name_groups.items():
            row_title = items[0][1] if items else name
            rows[row_title] = [(r, a, i) for i, (r, a) in enumerate(items)]

    print(f"[FormBot] MATRIX AI: Found {len(rows)} rows: {list(rows.keys())[:5]}")

    # Now match AI answers to rows and click
    results = {}
    for row_title, radio_list in rows.items():
        # Find matching AI answer
        col_idx = ai_row_answers.get(row_title)
        if col_idx is None:
            # Try partial matching
            for key, val in ai_row_answers.items():
                if key in row_title or row_title in key:
                    col_idx = val
                    break

        if col_idx is None:
            print(f"[FormBot] MATRIX AI: No match for row '{row_title[:50]}'")
            continue

        col_idx = int(col_idx)
        if 0 <= col_idx < len(radio_list):
            radio_to_click = radio_list[col_idx][0]
            try:
                radio_to_click.click()
            except Exception:
                try:
                    question_el.parent.execute_script("arguments[0].click();", radio_to_click)
                except Exception:
                    pass
            col_label = radio_list[col_idx][1] if radio_list[col_idx][1] else str(col_idx)
            results[row_title] = col_label
            print(f"[FormBot] MATRIX AI: '{row_title[:40]}' -> col {col_idx} = {col_label}")
        else:
            print(f"[FormBot] MATRIX AI: col_idx {col_idx} out of range (0-{len(radio_list)-1}) for '{row_title[:40]}'")

    return results


def _handle_text_ai(question_el, ai_text):
    """Type AI-generated text character-by-character like a human."""
    inputs = question_el.find_elements(By.CSS_SELECTOR, 'input[type="text"], textarea, [role="textbox"]')
    if not inputs:
        inputs = question_el.find_elements(By.TAG_NAME, "input")
    if inputs:
        field = inputs[0]
        field.clear()
        for char in str(ai_text):
            field.send_keys(char)
            time.sleep(random.uniform(0.03, 0.09))
    return str(ai_text)


def _handle_radio_question(question_el, title, weights=None):
    """Handle a simple single-choice (radio) question. Returns chosen label."""
    # Try input[role=radio] (MS Forms) then div[role=radio] (Google Forms)
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    if not radios:
        return None

    # Build list of (element, label) pairs
    items = [(r, _get_input_label(question_el, r)) for r in radios]

    # Get weights for this question title
    q_weights = weights.get(title) if weights else None
    chosen, label_text = _weighted_choice(items, q_weights)

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


def _handle_checkbox_question(question_el, title, weights=None):
    """Handle a multi-select (checkbox) question. Returns list of chosen labels."""
    # Try input[role=checkbox] (MS Forms) then div[role=checkbox] (Google Forms)
    checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
    if not checkboxes:
        return None

    # Build list of (element, label) pairs
    items = [(cb, _get_input_label(question_el, cb)) for cb in checkboxes]
    q_weights = weights.get(title) if weights else None

    # Select random number of options (1 to min(3, total))
    count = random.randint(1, min(3, len(checkboxes)))

    chosen_labels = []
    remaining_items = list(items)

    for _ in range(count):
        if not remaining_items:
            break
        chosen_el, label_text = _weighted_choice(remaining_items, q_weights)
        chosen_labels.append(label_text)
        remaining_items = [(e, l) for e, l in remaining_items if e is not chosen_el]
        try:
            chosen_el.click()
        except Exception:
            try:
                parent = chosen_el.find_element(By.XPATH, "./ancestor::label")
                parent.click()
            except Exception:
                try:
                    driver = question_el.parent
                    driver.execute_script("arguments[0].click();", chosen_el)
                except Exception:
                    pass

    return chosen_labels


def _handle_matrix_question(question_el, title, weights=None):
    """
    Handle a matrix/grid question.
    Groups radio buttons by row (using aria-label prefix) and picks one per row.
    Returns dict of {row_title: chosen_column}.
    """
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
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

    # Get weights for this question title (per-row weights)
    # Structure: { row_title: { col_name: weight } }
    q_weights = weights.get(title) if weights else None

    # Pick one option per row using weighted selection
    result = {}
    for row_title, options in rows.items():
        # Look up row-specific weights
        row_weights = q_weights.get(row_title) if q_weights else None
        # Use _weighted_choice: options is list of (radio_el, col_name)
        chosen_radio, chosen_col = _weighted_choice(options, row_weights)
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


def _handle_text_question(question_el, title, weights=None):
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

    # Use custom answers from weights if provided, otherwise defaults
    custom_answers = None
    if weights and title in weights and isinstance(weights[title], list):
        custom_answers = weights[title]

    answers_pool = custom_answers if custom_answers else TEXT_ANSWERS
    answer = random.choice(answers_pool)
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


def _get_matrix_info(question_el):
    """Extract row titles and column names from a matrix question for preview.
    Returns (rows, columns) tuple where both are lists of strings.
    """
    columns = []
    row_titles = []

    # --- Column headers ---
    # Method 1: DOM structure (MS Forms uses div[role="columnheader"] or th)
    try:
        header_cells = question_el.find_elements(
            By.CSS_SELECTOR, 'div[role="columnheader"], th'
        )
        for cell in header_cells:
            text = cell.text.strip()
            if text:
                columns.append(text)
    except Exception:
        pass

    # Common extraction: group radios by name to get rows
    radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
    name_groups = collections.OrderedDict()
    aria_by_group = collections.OrderedDict()
    if radios:
        for radio in radios:
            name = radio.get_attribute("name") or "default"
            if name not in name_groups:
                name_groups[name] = []
                aria_by_group[name] = []
            name_groups[name].append(radio)
            aria_by_group[name].append(radio.get_attribute("aria-label") or "")

    groups_list = list(aria_by_group.values())
    num_cols = len(groups_list[0]) if groups_list else 0

    # Method 2: extract column names from aria-labels if DOM headers not found
    if not columns and len(groups_list) >= 2 and num_cols > 0:
        for col_idx in range(num_cols):
            labels = [g[col_idx] for g in groups_list if col_idx < len(g)]
            if len(labels) >= 2:
                suffix = labels[0]
                for lbl in labels[1:]:
                    common = []
                    for c1, c2 in zip(reversed(suffix), reversed(lbl)):
                        if c1 == c2:
                            common.append(c1)
                        else:
                            break
                    suffix = "".join(reversed(common))
                col_name = suffix.strip()
                columns.append(col_name if col_name else labels[0].strip())
            elif labels:
                columns.append(labels[0].strip())
    elif not columns and num_cols > 0 and groups_list:
        for label in groups_list[0]:
            if label.strip():
                columns.append(label.strip())

    # --- Row titles ---
    if columns and groups_list:
        # Strip column suffix from aria-labels to get row titles
        for name, arias in aria_by_group.items():
            if arias:
                row_label = arias[0]
                for col in columns:
                    if row_label.endswith(col):
                        row_label = row_label[: -len(col)].strip()
                        break
                row_titles.append(row_label if row_label else name)
    elif groups_list:
        # Fallback: use first part of aria-label
        for name, arias in aria_by_group.items():
            if arias:
                row_label = arias[0].rsplit(" ", 1)[0] if arias[0] else name
                row_titles.append(row_label)

    return row_titles, columns


def _get_option_labels(question_el, q_type):
    """Extract option labels from a question element for preview."""
    options = []
    if q_type == "radio":
        radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
        for r in radios:
            label = _get_input_label(question_el, r)
            options.append(label)
    elif q_type == "checkbox":
        checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
        for cb in checkboxes:
            label = _get_input_label(question_el, cb)
            options.append(label)
    # Matrix is handled separately via _get_matrix_info
    return options


def _preview_form_questions(form_url, event_queue=None):
    """Opens the form, reads all questions (including conditional ones) and their options.

    To discover conditional/branching questions that appear only after answering
    a previous question, this function clicks through options just like the fill
    function does, then re-scans the page for newly-revealed questions.
    """
    driver = None
    provider = _detect_provider(form_url)

    def _emit(event, data=""):
        if event_queue is not None:
            event_queue.put({"event": event, "data": data})

    try:
        _emit("status", f"Provider: {provider}")
        _emit("status", "Uruchamianie przegladarki...")
        driver = _create_driver()
        driver.set_page_load_timeout(60)

        _emit("status", "Ladowanie formularza...")
        driver.get(form_url)

        q_selector = QUESTION_SELECTORS.get(provider, QUESTION_SELECTORS["unknown"])
        _emit("status", "Czekanie na zaladowanie pytan...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, q_selector))
        )
        time.sleep(2)

        # Dynamic scanning — iterate ALL radio options to discover all conditional branches
        answered_ids = set()
        question_num = 0
        max_passes = 15

        for _pass in range(max_passes):
            questions = driver.find_elements(By.CSS_SELECTOR, q_selector)
            new_questions_found = False

            for question_el in questions:
                # Build unique key
                q_id = question_el.get_attribute("id") or ""
                try:
                    q_title_preview = question_el.text[:80]
                except Exception:
                    q_title_preview = ""
                q_key = q_id or q_title_preview

                if q_key in answered_ids:
                    continue

                new_questions_found = True
                answered_ids.add(q_key)
                question_num += 1

                # Scroll into view
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    question_el,
                )
                time.sleep(0.15)

                title = _get_question_title(question_el)
                q_type = _detect_question_type(question_el)
                options = _get_option_labels(question_el, q_type)

                browser_queue.set_activity(f"Podglad pytania {question_num}")
                _emit("status", f"Pytanie {question_num}: {title[:50]}...")

                preview_data = {
                    "num": question_num,
                    "title": title,
                    "type": q_type,
                    "options": options,
                }

                if q_type == "matrix":
                    row_titles, col_names = _get_matrix_info(question_el)
                    preview_data["options"] = col_names
                    preview_data["rows"] = row_titles
                elif q_type == "text":
                    preview_data["text_answers"] = list(TEXT_ANSWERS)

                _emit("question_preview", preview_data)

                # Click ALL options to discover every conditional branch
                if q_type == "radio":
                    try:
                        radios = question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
                        for radio_opt in radios:
                            try:
                                radio_opt.click()
                            except Exception:
                                try:
                                    driver.execute_script("arguments[0].click();", radio_opt)
                                except Exception:
                                    pass
                            time.sleep(0.25)
                    except Exception:
                        pass
                elif q_type == "checkbox":
                    try:
                        checkboxes = question_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
                        for cb_opt in checkboxes:
                            try:
                                cb_opt.click()
                            except Exception:
                                try:
                                    driver.execute_script("arguments[0].click();", cb_opt)
                                except Exception:
                                    pass
                            time.sleep(0.15)
                        # Uncheck all (so they don't interfere)
                        for cb_opt in checkboxes:
                            try:
                                if cb_opt.get_attribute("aria-checked") == "true":
                                    cb_opt.click()
                            except Exception:
                                pass
                    except Exception:
                        pass

                time.sleep(0.1)

            if not new_questions_found:
                break

            # Wait for conditional questions to appear
            time.sleep(0.6)
            _emit("status", f"Szukanie warunkowych pytan (przejscie {_pass + 1})...")
            browser_queue.set_activity(f"Skanowanie warunkowych pytan ({_pass + 1})")

        _emit("preview_done", {"total": question_num})

    except Exception as e:
        _emit("error_ev", str(e))

    finally:
        if driver:
            driver.quit()
        if event_queue is not None:
            event_queue.put(None)


def _perform_form_fill(form_url, event_queue=None, weights=None, ai_mode=False, ai_key=""):
    """Main function: opens the form, reads questions, fills random answers."""
    driver = None
    results = []
    provider = _detect_provider(form_url)

    def _emit(event, data=""):
        """Push an SSE event if streaming is active."""
        if event_queue is not None:
            event_queue.put({"event": event, "data": data})

    # ─── AI Mode: Pre-scan all questions, ask Gemini, then fill ───
    ai_answers = None
    if ai_mode and ai_key:
        # Check cache first
        scanned_questions = _ai_scan_cache.get(form_url)

        if scanned_questions:
            _emit("status", f"AI: Uzycie {len(scanned_questions)} pytan z cache")
            print(f"[FormBot] AI: Using cached scan ({len(scanned_questions)} questions)")
        else:
            _emit("status", "AI: Skanowanie pytan...")
            browser_queue.set_activity("AI: skanowanie pytan")

            try:
                scan_driver = _create_driver()
                scan_driver.set_page_load_timeout(60)
                scan_driver.get(form_url)

                q_selector = QUESTION_SELECTORS.get(provider, QUESTION_SELECTORS["unknown"])
                WebDriverWait(scan_driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, q_selector))
                )
                time.sleep(3)

                # Scan all questions (click through options to find conditional ones too)
                scanned_questions = []
                scanned_ids = set()
                scan_num = 0

                for _scan_pass in range(10):
                    questions = scan_driver.find_elements(By.CSS_SELECTOR, q_selector)
                    new_found = False

                    for q_el in questions:
                        q_id = q_el.get_attribute("id") or ""
                        try:
                            q_text = q_el.text[:80]
                        except Exception:
                            q_text = ""
                        q_key = q_id or q_text
                        if q_key in scanned_ids:
                            continue

                        new_found = True
                        scanned_ids.add(q_key)
                        scan_num += 1

                        title = _get_question_title(q_el)
                        q_type = _detect_question_type(q_el)
                        options = _get_option_labels(q_el, q_type)

                        q_data = {"num": scan_num, "title": title, "type": q_type, "options": options}

                        if q_type == "matrix":
                            row_titles, col_names = _get_matrix_info(q_el)
                            q_data["options"] = col_names
                            q_data["rows"] = row_titles

                        scanned_questions.append(q_data)
                        _emit("status", f"AI: Skanowanie Q{scan_num}: {title[:40]}...")

                        # Click through radio options to reveal conditional questions
                        if q_type == "radio":
                            try:
                                radios = q_el.find_elements(By.CSS_SELECTOR, '[role="radio"]')
                                for r_opt in radios:
                                    try:
                                        r_opt.click()
                                    except Exception:
                                        try:
                                            scan_driver.execute_script("arguments[0].click();", r_opt)
                                        except Exception:
                                            pass
                                    time.sleep(0.5)
                            except Exception:
                                pass

                    if not new_found:
                        break
                    time.sleep(1)

                scan_driver.quit()

                # Save to cache
                _ai_scan_cache[form_url] = scanned_questions
                _save_scan_cache()
                print(f"[FormBot] AI: Cached {len(scanned_questions)} questions for this form")

            except Exception as scan_err:
                print(f"[FormBot] AI scan error: {scan_err}")
                _emit("status", f"AI: Blad skanowania ({str(scan_err)[:60]}), uzywam losowych")

        # Ask Gemini (whether from cache or fresh scan)
        if scanned_questions:
            browser_queue.set_activity("AI: czekanie na Gemini")
            ai_answers = _ask_gemini_for_answers(scanned_questions, ai_key, _emit_fn=_emit, weights=weights)

            if ai_answers:
                _emit("status", f"AI: Otrzymano {len(ai_answers)} odpowiedzi, wypelnianie...")
            else:
                _emit("status", "AI: Brak odpowiedzi, uzywam losowych")

    # ─── Main fill ───
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
                browser_queue.set_activity(f"Wypelnianie pytania {question_num}")

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

                # Check if AI has an answer for this question
                ai_answer_for_q = None
                if ai_answers:
                    ai_answer_for_q = ai_answers.get(str(question_num))

                if q_type == "radio":
                    if ai_answer_for_q is not None:
                        answer = _handle_radio_ai(question_el, ai_answer_for_q)
                    else:
                        answer = _handle_radio_question(question_el, title, weights=weights)
                    result_entry["answer"] = answer
                    source = "AI" if ai_answer_for_q is not None else "Losowe"
                    print(f"[FormBot] Selected: {answer} ({source})")
                    _emit("answer", {"num": question_num, "answer": answer, "source": source})

                elif q_type == "checkbox":
                    if ai_answer_for_q is not None:
                        answers = _handle_checkbox_ai(question_el, ai_answer_for_q)
                    else:
                        answers = _handle_checkbox_question(question_el, title, weights=weights)
                    result_entry["answer"] = answers
                    source = "AI" if ai_answer_for_q is not None else "Losowe"
                    print(f"[FormBot] Selected: {answers} ({source})")
                    _emit("answer", {"num": question_num, "answer": answers, "source": source})

                elif q_type == "matrix":
                    if ai_answer_for_q is not None:
                        answers = _handle_matrix_ai(question_el, ai_answer_for_q)
                    else:
                        answers = _handle_matrix_question(question_el, title, weights=weights)
                    result_entry["answer"] = answers
                    source = "AI" if ai_answer_for_q is not None else "Losowe"
                    if answers:
                        for row, col in answers.items():
                            print(f"[FormBot]   {row} -> {col} ({source})")
                    _emit("answer", {"num": question_num, "answer": answers, "source": source})

                elif q_type == "text":
                    if ai_answer_for_q is not None:
                        answer = _handle_text_ai(question_el, str(ai_answer_for_q))
                    else:
                        answer = _handle_text_question(question_el, title, weights=weights)
                    result_entry["answer"] = answer
                    source = "AI" if ai_answer_for_q is not None else "Losowe"
                    print(f"[FormBot] Typed: {answer} ({source})")
                    _emit("answer", {"num": question_num, "answer": answer, "source": source})

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
