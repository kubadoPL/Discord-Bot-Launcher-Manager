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

import sys
sys.path.insert(0, os.path.join(parent_dir, "api"))
from FunctionsModule import get_db_connection, create_service_stats_table

app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})

# ─── Session Stats ────────────────────────────────────────────────────────────────
_session_stats_lock = threading.Lock()
_session_stats = {
    "forms_filled": 0,
    "forms_submitted": 0,
    "forms_failed": 0,
    "forms_previewed": 0,
    "questions_answered": 0,
    "ai_answers": 0,
    "random_answers": 0,
    "empty_answers": 0,
}

# ─── Global Persistent Stats (saved to DB) ─────────────────────────────────────
FORMS_SERVICE_NAME = "msforms"
_global_stats_queue = Queue()


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
                (FORMS_SERVICE_NAME, stat_name, amount, amount),
            )
            conn.commit()
            conn.close()
            print(f"[MSForms GlobalStats] Saved: {stat_name} +{amount}")
        except Exception as e:
            print(f"[MSForms GlobalStats] Error saving {stat_name}: {e}")
        finally:
            _global_stats_queue.task_done()


_global_stats_thread = threading.Thread(target=_global_stats_worker, daemon=True, name="msforms-global-stats")
_global_stats_thread.start()


def _increment_global_stat(stat_name, amount=1):
    """Enqueue a global stat increment to be processed in the background."""
    _global_stats_queue.put((stat_name, amount))


def _get_global_stats():
    """Fetch all global stats from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT stat_name, value FROM service_stats WHERE service_name = %s",
            (FORMS_SERVICE_NAME,),
        )
        rows = cursor.fetchall()
        conn.close()
        return {row["stat_name"]: row["value"] for row in rows}
    except Exception as e:
        print(f"[MSForms GlobalStats] Error loading: {e}")
        return {}


# Create service_stats table on startup (in background to avoid blocking gunicorn)
def _init_global_stats_table():
    try:
        create_service_stats_table()
        test_stats = _get_global_stats()
        print(f"[MSForms] Global stats table ready. Current stats: {test_stats}")
    except Exception as e:
        print(f"[MSForms] Warning: Could not create stats table: {e}")

threading.Thread(target=_init_global_stats_table, daemon=True, name="msforms-stats-init").start()

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

_PREVIEW_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_cache.json")
_preview_cache = {}  # { form_url: [preview_questions_list] }

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

def _load_preview_cache():
    """Load preview cache from file on startup."""
    global _preview_cache
    try:
        if os.path.exists(_PREVIEW_CACHE_FILE):
            with open(_PREVIEW_CACHE_FILE, "r", encoding="utf-8") as f:
                _preview_cache = json.loads(f.read())
            print(f"[FormBot] Loaded preview cache: {len(_preview_cache)} form(s)")
    except Exception as e:
        print(f"[FormBot] Could not load preview cache: {e}")

def _save_preview_cache():
    """Save preview cache to file."""
    try:
        with open(_PREVIEW_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(_preview_cache, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[FormBot] Could not save preview cache: {e}")

_load_scan_cache()
_load_preview_cache()


def _ask_gemini_for_answers(questions_data, api_key, _emit_fn=None, weights=None, settings=None):
    """Send all questions to Gemini and get a coherent set of answers using google-genai SDK."""
    from google import genai
    from google.genai import types
    import re as _re

    if _emit_fn:
        _emit_fn("status", "AI: Przygotowywanie pytan dla Gemini...")

    # Build the prompt
    questions_text = ""
    for q in questions_data:
        questions_text += f"\nPytanie {q['num']} (typ: {q['type']}): {q['title']}\n"
        if q['type'] in ('radio', 'checkbox') and q.get('options'):
            for i, opt in enumerate(q['options']):
                questions_text += f"  {i}: {opt}\n"
            # Add weight hints with strength indicators
            if weights and q.get('title') in weights:
                q_weights = weights[q['title']]
                if isinstance(q_weights, dict):
                    hint_parts = []
                    total = sum(q_weights.values())
                    if total > 0:
                        for opt_label, w in q_weights.items():
                            pct = int(w / total * 100) if total > 0 else 0
                            if pct >= 95:
                                hint_parts.append(f"{opt_label}: {pct}% OBOWIAZEK - MUSISZ wybrac ta opcje!")
                            elif pct >= 70:
                                hint_parts.append(f"{opt_label}: {pct}% PREFEROWANE")
                            elif pct > 0:
                                hint_parts.append(f"{opt_label}: ~{pct}%")
                        if hint_parts:
                            questions_text += f"  >>> WAGI UZYTKOWNIKA: {', '.join(hint_parts)}\n"
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
                                parts = []
                                for col, v in row_w.items():
                                    pct = int(v/total*100)
                                    if pct >= 95:
                                        parts.append(f"{col}: {pct}% OBOWIAZEK")
                                    elif pct > 0:
                                        parts.append(f"{col}: ~{pct}%")
                                if parts:
                                    questions_text += f"  >>> WAGI dla wiersza '{row_name}': {', '.join(parts)}\n"
        elif q['type'] == 'text':
            questions_text += "  (pytanie otwarte - napisz wlasna, unikalna odpowiedz pasujaca do Twojej postaci)\n"

    # ─── Build persona based on weights ─────────────────────────────────────
    persona_gender = None
    persona_age = None

    if weights:
        for q in questions_data:
            title = q.get('title', '')
            title_lower = title.lower()

            # Detect gender question
            if not persona_gender and any(g in title_lower for g in ['płeć', 'plec', 'gender']):
                q_weights = weights.get(title)
                if isinstance(q_weights, dict) and q_weights:
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

            # Detect age question and pick weighted age for persona
            if not persona_age and any(a in title_lower for a in ['wiek', 'age', 'lat', 'przedział wiekowy', 'przedzial wiekowy', 'ile masz lat']):
                q_weights = weights.get(title)
                if isinstance(q_weights, dict) and q_weights:
                    labels = list(q_weights.keys())
                    w_vals = [max(0, q_weights[l]) for l in labels]
                    total = sum(w_vals)
                    if total > 0:
                        chosen_age_label = random.choices(labels, weights=w_vals, k=1)[0]
                        nums = _re.findall(r'\d+', chosen_age_label)
                        if nums:
                            age_low = int(nums[0])
                            age_high = int(nums[1]) if len(nums) > 1 else age_low + 5
                            persona_age = f"{random.randint(age_low, min(age_high, age_low + 10))}"
                        else:
                            persona_age = chosen_age_label

    if not persona_gender:
        persona_gender = random.choice(["mezczyzna", "kobieta"])
    if not persona_age:
        persona_age = str(random.choice([19, 22, 25, 28, 31, 35, 40, 45, 50, 55, 60]))

    persona_job = random.choice(["student", "pracownik biurowy", "nauczyciel", "informatyk", "sprzedawca", "kierowca", "lekarz", "emeryt", "bezrobotny", "przedsiebiorca", "pracownik fizyczny", "freelancer"])
    # If persona is young, filter out incompatible jobs
    try:
        _age_num = int(persona_age.split('-')[0])
        if _age_num < 25:
            persona_job = random.choice(["student", "pracownik biurowy", "sprzedawca", "freelancer", "informatyk", "bezrobotny"])
        elif _age_num >= 60:
            persona_job = random.choice(["emeryt", "nauczyciel", "lekarz", "przedsiebiorca", "pracownik biurowy"])
    except (ValueError, IndexError):
        pass

    has_hints = weights is not None and len(weights) > 0
    hints_note = ""
    if has_hints:
        hints_note = "\n4. WAGI UZYTKOWNIKA SA OBOWIAZKOWE! Jesli przy pytaniu jest '>>> WAGI UZYTKOWNIKA' z napisem 'OBOWIAZEK', MUSISZ wybrac te opcje bez wzgledu na postac. Jesli waga mowi 'PREFEROWANE' (70%+), wybierz ta opcje w wiekszosci przypadkow. Pozostale wagi traktuj jako sugestie statystyczne. NIGDY nie ignoruj wag 100%! Dostosuj postac do wag, NIE wagi do postaci."

    # Custom prompt from user
    custom_prompt_raw = settings.get("custom_prompt", "") if settings else ""
    custom_prompt_section = ""
    if custom_prompt_raw and custom_prompt_raw.strip():
        custom_prompt_section = f"DODATKOWE INSTRUKCJE OD UZYTKOWNIKA (MUSISZ sie do nich zastosowac!):\n{custom_prompt_raw.strip()}\n\n"

    # Short answers mode
    short_answers_mode = settings.get("short_answers", False) if settings else False
    if short_answers_mode:
        text_instruction = "2. Na pytania tekstowe (otwarte) pisz KROTKIE odpowiedzi - jedno krotkie zdanie, bez rozpisywania sie. Pisz tak jak osoba ktora nie chce poswiecac duzo czasu na ankiete (np. 'Raczej jestem zadowolony', 'Nie mam uwag do tego tematu', 'Mogloby byc lepiej')."
    else:
        text_instruction = '2. Na pytania tekstowe (otwarte) pisz WLASNE, UNIKALNE, NATURALNE odpowiedzi - tak jak napisalby prawdziwy czlowiek. NIE pisz ogolnikow typu "Brak uwag" czy "Nie wiem". Napisz cos konkretnego, osobistego, co pasuje do Twojej postaci. 1-2 zdania wystarczy.'

    prompt = f"""Jestes prawdziwa osoba wypelniajaca ankiete. Twoja postac to: {persona_gender}, wiek {persona_age} lat, zawod: {persona_job}. Rozwin te cechy i odpowiadaj SPOJNIE.

WAZNE ZASADY:
1. Odpowiedzi musza byc logicznie spojne z Twoja postacia! Np. jesli masz 20 lat, nie mozesz byc emerytem. Jesli jestes emerytem, musisz miec 60+ lat.
{text_instruction}
3. Odpowiedzi tekstowe powinny brzmiec naturalnie, z drobnymi niedoskonalosciami jak w prawdziwej ankiecie.{hints_note}

{custom_prompt_section}NAJWAZNIEJSZE: Jesli widzisz '>>> WAGI UZYTKOWNIKA' z napisem 'OBOWIAZEK' przy pytaniu, MUSISZ wybrac wskazana opcje! To nie jest sugestia, to WYMAGANIE. Twoja postac musi sie dostosowac do wag, nie odwrotnie.

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

# ─── Online Users Tracking ─────────────────────────────────────────────────────
_online_users = {}  # session_id -> last_heartbeat_timestamp
_online_lock = threading.Lock()
ONLINE_TIMEOUT = 30  # seconds before a user is considered offline

def _cleanup_online():
    """Remove stale sessions."""
    now = time.time()
    with _online_lock:
        stale = [sid for sid, ts in _online_users.items() if now - ts > ONLINE_TIMEOUT]
        for sid in stale:
            del _online_users[sid]

def _get_online_count():
    _cleanup_online()
    with _online_lock:
        return len(_online_users)


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


@app.route("/heartbeat", methods=["POST"])
@cross_origin()
def heartbeat():
    """Register a heartbeat from a connected client."""
    data = request.json if request.is_json else {}
    session_id = data.get("sid", "")
    if not session_id:
        return jsonify({"error": "no sid"}), 400
    with _online_lock:
        _online_users[session_id] = time.time()
    return jsonify({"online": _get_online_count()})


@app.route("/online-count")
@cross_origin()
def online_count():
    """Return the number of currently online users."""
    return jsonify({"online": _get_online_count()})


@app.route("/api/stats")
@cross_origin()
def api_stats():
    """Return FormBot session (daily) and global (all-time) statistics."""
    with _session_stats_lock:
        stats_copy = dict(_session_stats)
    stats_copy["cached_forms"] = len(_preview_cache)

    global_stats = _get_global_stats()

    return jsonify({
        "session": stats_copy,
        "global": global_stats,
    })


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


# In-memory store for weights (to avoid URL length limits)
import uuid
_stored_weights = {}

@app.route("/store-weights", methods=["POST"])
@cross_origin()
def store_weights():
    """Store weights + settings server-side and return a token to reference them."""
    data = request.json if request.is_json else {}
    weights = data.get("weights", {})
    settings = data.get("settings", {})
    token = str(uuid.uuid4())[:8]
    _stored_weights[token] = {"weights": weights, "settings": settings}
    # Clean old tokens (keep max 50)
    if len(_stored_weights) > 50:
        oldest = list(_stored_weights.keys())[0]
        _stored_weights.pop(oldest, None)
    return jsonify({"token": token})


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
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.8); }
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
    /* ─── Settings Panel ─────────────────────────────────── */
    .settings-panel {
      margin-top: 14px;
      padding: 18px 20px;
      background: linear-gradient(135deg, rgba(13, 148, 136, 0.06), rgba(8, 145, 178, 0.04));
      border: 1px solid rgba(13, 148, 136, 0.18);
      border-radius: 14px;
    }
    .settings-panel h3 {
      font-size: 0.92rem;
      font-weight: 600;
      color: #0d9488;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .settings-panel h3 .settings-icon {
      font-size: 1.1rem;
    }
    .setting-toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 0;
      border-bottom: 1px solid rgba(13, 148, 136, 0.08);
    }
    .setting-toggle-row:last-child { border-bottom: none; }
    .setting-toggle-info {
      flex: 1;
      min-width: 0;
    }
    .setting-toggle-label {
      font-size: 0.88rem;
      font-weight: 500;
      color: #1e293b;
    }
    .setting-toggle-desc {
      font-size: 0.75rem;
      color: #64748b;
      margin-top: 2px;
    }
    .toggle-switch {
      position: relative;
      width: 44px;
      height: 24px;
      flex-shrink: 0;
      margin-left: 12px;
    }
    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background: #cbd5e1;
      border-radius: 24px;
      transition: background 0.3s;
    }
    .toggle-slider::before {
      content: '';
      position: absolute;
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background: white;
      border-radius: 50%;
      transition: transform 0.3s;
      box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }
    .toggle-switch input:checked + .toggle-slider {
      background: linear-gradient(135deg, #0d9488, #0891b2);
    }
    .toggle-switch input:checked + .toggle-slider::before {
      transform: translateX(20px);
    }
    .settings-divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(13,148,136,0.2), transparent);
      margin: 12px 0;
    }
    .timing-section h4 {
      font-size: 0.85rem;
      font-weight: 600;
      color: #475569;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .timing-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(0,0,0,0.04);
    }
    .timing-row:last-child { border-bottom: none; }
    .timing-label {
      flex: 1;
      font-size: 0.85rem;
      color: #334155;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .timing-label .timing-type-badge {
      font-size: 0.68rem;
      padding: 2px 7px;
      border-radius: 5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .timing-type-badge.radio-badge { background: rgba(99,102,241,0.12); color: #6366f1; }
    .timing-type-badge.checkbox-badge { background: rgba(16,185,129,0.12); color: #10b981; }
    .timing-type-badge.text-badge { background: rgba(245,158,11,0.12); color: #f59e0b; }
    .timing-type-badge.matrix-badge { background: rgba(239,68,68,0.12); color: #ef4444; }
    .timing-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }
    .timing-controls input[type="range"] {
      width: 90px;
      height: 5px;
      -webkit-appearance: none;
      appearance: none;
      background: linear-gradient(90deg, #0d9488, #0891b2);
      border-radius: 3px;
      outline: none;
      opacity: 0.8;
      transition: opacity 0.2s;
    }
    .timing-controls input[type="range"]:hover { opacity: 1; }
    .timing-controls input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 16px; height: 16px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid #0d9488;
      cursor: pointer;
      box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }
    .timing-controls input[type="range"]::-moz-range-thumb {
      width: 16px; height: 16px;
      border-radius: 50%;
      background: #fff;
      border: 2px solid #0d9488;
      cursor: pointer;
    }
    .timing-val {
      font-size: 0.78rem;
      font-weight: 600;
      color: #0d9488;
      min-width: 32px;
      text-align: right;
    }
    .settings-collapsed .settings-body { display: none; }
    .settings-toggle-btn {
      background: none;
      border: none;
      color: #0d9488;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.2s;
      font-family: 'Inter', sans-serif;
    }
    .settings-toggle-btn:hover {
      background: rgba(13, 148, 136, 0.1);
    }
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
      <!-- Settings Panel (under Start button) -->
      <div class="settings-panel" id="settings-panel">
        <div style="display:flex; align-items:center; justify-content:space-between;">
          <h3><span class="settings-icon">&#9881;</span> Ustawienia wypelniania</h3>
          <button class="settings-toggle-btn" onclick="toggleSettingsPanel()" id="settings-toggle-btn">&#9660; Rozwin</button>
        </div>
        <div class="settings-body" id="settings-body" style="display:none;">
          <!-- Toggle: Empty open questions -->
          <div class="setting-toggle-row">
            <div class="setting-toggle-info">
              <div class="setting-toggle-label">&#128683; Szansa na puste pytanie otwarte</div>
              <div class="setting-toggle-desc">~20-25% szans, ze pytanie otwarte zostanie puste (jakby ktos zignorowal)</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="setting-empty-chance">
              <span class="toggle-slider"></span>
            </label>
          </div>
          <!-- Toggle: Short answers -->
          <div class="setting-toggle-row">
            <div class="setting-toggle-info">
              <div class="setting-toggle-label">&#9999; Krotkie odpowiedzi na pytania otwarte</div>
              <div class="setting-toggle-desc">AI pisze krotkie odpowiedzi (jedno zdanie) zamiast dlugich, rozbudowanych</div>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" id="setting-short-answers">
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="settings-divider"></div>

          <!-- Custom AI Prompt -->
          <div style="padding:10px 0;">
            <div class="setting-toggle-label" style="margin-bottom:6px;">&#128172; Dodatkowe instrukcje dla AI</div>
            <div class="setting-toggle-desc" style="margin-bottom:8px;">Wpisz dodatkowe polecenia, np. "udawaj kogoś", "odpowiadaj sarcastycznie", "bierz pod uwage ze jestes z Warszawy". Puste = brak dodatkowych instrukcji.</div>
            <textarea id="setting-custom-prompt" rows="3" placeholder="Np. Udawaj kogoś, pisz z bledami..." style="width:100%; padding:10px 14px; border:1px solid rgba(13,148,136,0.25); border-radius:10px; font-size:0.85rem; font-family:'Inter',sans-serif; outline:none; background:rgba(255,255,255,0.9); color:#1e293b; resize:vertical; box-sizing:border-box; transition:border-color 0.3s;" onfocus="this.style.borderColor='#0d9488'" onblur="this.style.borderColor='rgba(13,148,136,0.25)'"></textarea>
          </div>

          <div class="settings-divider"></div>

          <!-- Timing sliders per question type -->
          <div class="timing-section">
            <h4>&#9201; Czas odpowiadania (per typ pytania)</h4>
            <div style="font-size:0.73rem; color:#94a3b8; margin-bottom:10px;">Bazowy czas + losowy offset (1-30s) dla naturalnych statystyk</div>

            <div class="timing-row">
              <div class="timing-label">
                <span class="timing-type-badge radio-badge">radio</span>
                Jednokrotny wybor
              </div>
              <div class="timing-controls">
                <input type="range" id="timing-radio" min="0" max="60" value="5" oninput="updateTimingVal(this)">
                <span class="timing-val" id="timing-radio-val">5s</span>
              </div>
            </div>

            <div class="timing-row">
              <div class="timing-label">
                <span class="timing-type-badge checkbox-badge">checkbox</span>
                Wielokrotny wybor
              </div>
              <div class="timing-controls">
                <input type="range" id="timing-checkbox" min="0" max="60" value="8" oninput="updateTimingVal(this)">
                <span class="timing-val" id="timing-checkbox-val">8s</span>
              </div>
            </div>

            <div class="timing-row">
              <div class="timing-label">
                <span class="timing-type-badge text-badge">text</span>
                Pytanie otwarte
              </div>
              <div class="timing-controls">
                <input type="range" id="timing-text" min="0" max="60" value="15" oninput="updateTimingVal(this)">
                <span class="timing-val" id="timing-text-val">15s</span>
              </div>
            </div>

            <div class="timing-row">
              <div class="timing-label">
                <span class="timing-type-badge matrix-badge">matrix</span>
                Macierz / tabela
              </div>
              <div class="timing-controls">
                <input type="range" id="timing-matrix" min="0" max="60" value="10" oninput="updateTimingVal(this)">
                <span class="timing-val" id="timing-matrix-val">10s</span>
              </div>
            </div>

            <div style="margin-top:8px;">
              <div class="timing-row">
                <div class="timing-label" style="font-weight:500; color:#475569;">
                  &#127922; Losowy offset
                </div>
                <div class="timing-controls">
                  <input type="range" id="timing-offset" min="0" max="30" value="10" oninput="updateTimingVal(this)">
                  <span class="timing-val" id="timing-offset-val">10s</span>
                </div>
              </div>
              <div style="font-size:0.7rem; color:#94a3b8;">Zakres losowego odchylenia dodawanego do bazowego czasu (0-30s)</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview area with sliders -->
    <div id="preview-area" class="card">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:18px;">
        <h2 style="font-size:1.15rem; color:#1e293b;">&#128196; Podglad formularza</h2>
        <div style="display:flex; gap:12px; align-items:center;">
          <span class="reset-link" onclick="previewForm(true)">&#128260; Odswiez</span>
          <span class="reset-link" onclick="resetAllSliders()">Resetuj suwaki</span>
        </div>
      </div>
      <div id="preview-queue-bar" style="display:none; background:linear-gradient(135deg,#fbbf24,#f59e0b); color:#78350f; padding:12px 16px; border-radius:10px; margin-bottom:14px; font-size:0.88rem; font-weight:500; align-items:center; gap:10px;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span id="preview-queue-text"></span>
      </div>
      <div id="preview-status" class="status-bar" style="display:none;">
        <div class="spinner" id="preview-spinner"></div>
        <span class="status-text" id="preview-status-text">Wczytywanie...</span>
      </div>
      <div id="preview-nav" style="display:none; position:sticky; top:0; z-index:10; background:linear-gradient(135deg,rgba(240,253,250,0.97),rgba(236,254,255,0.97)); backdrop-filter:blur(8px); border:1px solid rgba(13,148,136,0.15); border-radius:10px; padding:8px 12px; margin-bottom:12px; display:none; align-items:center; justify-content:space-between; gap:6px; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
        <div style="display:flex; gap:4px;">
          <button onclick="previewNavTo('first')" title="Pierwsze" style="padding:6px 10px; border:none; border-radius:7px; background:rgba(13,148,136,0.12); color:#0d9488; font-size:0.82rem; font-weight:700; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s;" onmouseover="this.style.background='rgba(13,148,136,0.22)'" onmouseout="this.style.background='rgba(13,148,136,0.12)'">&laquo; Start</button>
          <button onclick="previewNavTo('prev')" title="Poprzednie" style="padding:6px 12px; border:none; border-radius:7px; background:rgba(13,148,136,0.12); color:#0d9488; font-size:0.82rem; font-weight:700; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s;" onmouseover="this.style.background='rgba(13,148,136,0.22)'" onmouseout="this.style.background='rgba(13,148,136,0.12)'">&lsaquo; Poprz</button>
        </div>
        <div style="display:flex; flex-direction:column; align-items:center; min-width:60px;">
          <span id="preview-nav-counter" style="font-size:0.82rem; font-weight:600; color:#475569;">0/0</span>
          <span id="preview-nav-status" style="font-size:0.7rem; color:#0d9488; font-weight:500; max-width:200px; text-align:center; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;"></span>
        </div>
        <div style="display:flex; gap:4px;">
          <button onclick="previewNavTo('next')" title="Nastepne" style="padding:6px 12px; border:none; border-radius:7px; background:rgba(13,148,136,0.12); color:#0d9488; font-size:0.82rem; font-weight:700; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s;" onmouseover="this.style.background='rgba(13,148,136,0.22)'" onmouseout="this.style.background='rgba(13,148,136,0.12)'">Nast &rsaquo;</button>
          <button onclick="previewNavTo('last')" title="Ostatnie" style="padding:6px 10px; border:none; border-radius:7px; background:rgba(13,148,136,0.12); color:#0d9488; font-size:0.82rem; font-weight:700; cursor:pointer; font-family:'Inter',sans-serif; transition:background 0.15s;" onmouseover="this.style.background='rgba(13,148,136,0.22)'" onmouseout="this.style.background='rgba(13,148,136,0.12)'">Koniec &raquo;</button>
        </div>
      </div>
      <div id="preview-questions" style="max-height:70vh; overflow-y:auto; scroll-behavior:smooth;"></div>
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
    <!-- Server Stats Bar -->
    <div id="server-stats-bar" class="card" style="padding:16px 22px; margin-bottom:0; background:linear-gradient(135deg, rgba(13,148,136,0.06), rgba(8,145,178,0.04)); border:1px solid rgba(13,148,136,0.15);">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:1.05rem;">&#128300;</span>
          <span style="font-weight:600; font-size:0.85rem; color:#0d9488;">Statystyki serwera</span>
        </div>
        <div id="uptime-badge" style="display:inline-flex; align-items:center; gap:6px; padding:4px 12px; background:rgba(13,148,136,0.1); border:1px solid rgba(13,148,136,0.2); border-radius:20px; font-size:0.75rem; font-weight:600; color:#0d9488;">
          <span style="font-size:0.85rem;">&#9200;</span>
          Uptime: <span id="uptime-text">--</span>
        </div>
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(13,148,136,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#128196;</span>
          <span style="color:#64748b;">Formularze:</span>
          <strong id="stat-forms" style="color:#0d9488;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(16,185,129,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#9989;</span>
          <span style="color:#64748b;">Wyslane:</span>
          <strong id="stat-submitted" style="color:#059669;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(99,102,241,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#10067;</span>
          <span style="color:#64748b;">Pytania:</span>
          <strong id="stat-questions" style="color:#6366f1;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(139,92,246,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#129302;</span>
          <span style="color:#64748b;">AI odp.:</span>
          <strong id="stat-ai" style="color:#7c3aed;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(245,158,11,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#127922;</span>
          <span style="color:#64748b;">Losowe:</span>
          <strong id="stat-random" style="color:#d97706;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(220,38,38,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#10060;</span>
          <span style="color:#64748b;">Bledy:</span>
          <strong id="stat-failed" style="color:#dc2626;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(56,189,248,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#128269;</span>
          <span style="color:#64748b;">Podglady:</span>
          <strong id="stat-previewed" style="color:#0ea5e9;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(255,255,255,0.8); border:1px solid rgba(168,85,247,0.12); border-radius:10px; font-size:0.8rem;">
          <span style="font-size:0.95rem;">&#128451;</span>
          <span style="color:#64748b;">W cache:</span>
          <strong id="stat-cached" style="color:#a855f7;">0</strong>
        </div>
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; padding-top:8px; border-top:1px solid rgba(13,148,136,0.1);">
        <div style="display:flex; align-items:center; gap:6px; margin-right:4px;">
          <span style="font-size:0.75rem; font-weight:700; color:#0891b2; text-transform:uppercase; letter-spacing:0.5px;">&#127760; All-Time</span>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Formularze:</span>
          <strong id="gstat-forms" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Wyslane:</span>
          <strong id="gstat-submitted" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Pytania:</span>
          <strong id="gstat-questions" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">AI odp.:</span>
          <strong id="gstat-ai" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Bledy:</span>
          <strong id="gstat-failed" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Podglady:</span>
          <strong id="gstat-previewed" style="color:#0891b2;">0</strong>
        </div>
        <div class="stat-chip" style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(8,145,178,0.06); border:1px solid rgba(8,145,178,0.15); border-radius:10px; font-size:0.8rem;">
          <span style="color:#64748b;">Losowe:</span>
          <strong id="gstat-random" style="color:#0891b2;">0</strong>
        </div>
      </div>
    </div>
    <div class="footer" style="display:flex; align-items:center; justify-content:center; gap:14px; flex-wrap:wrap;">
      <span>FormBot &mdash; Copyright by K5 Studio 2026</span>
      <span id="online-badge" style="display:inline-flex; align-items:center; gap:5px; padding:3px 10px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.25); border-radius:20px; font-size:0.75rem; font-weight:600; color:#059669;">
        <span style="width:7px; height:7px; background:#10b981; border-radius:50%; display:inline-block; animation:pulse-dot 2s infinite;"></span>
        <span id="online-count-text">1</span> online
      </span>
    </div>
  </div>

  <script>
    // Global state for preview data and weights
    let previewData = null; // Array of {num, title, type, options: [...]}

    // ─── LocalStorage Persistence ─────────────────────────────
    function _saveToStorage(key, value) {
      try { localStorage.setItem('formbot_' + key, value); } catch(e) {}
    }
    function _loadFromStorage(key) {
      try { return localStorage.getItem('formbot_' + key) || ''; } catch(e) { return ''; }
    }
    function restoreFromLocalStorage() {
      var savedUrl = _loadFromStorage('last_url');
      var savedKey = _loadFromStorage('last_api_key');
      var savedPrompt = _loadFromStorage('custom_prompt');
      if (savedUrl) {
        document.getElementById('url-input').value = savedUrl;
      }
      if (savedKey) {
        document.getElementById('gemini-api-key').value = savedKey;
      }
      if (savedPrompt) {
        document.getElementById('setting-custom-prompt').value = savedPrompt;
      }
    }
    function saveCurrentInputs() {
      var url = (document.getElementById('url-input').value || '').trim();
      if (url) _saveToStorage('last_url', url);
      var key = (document.getElementById('gemini-api-key').value || '').trim();
      if (key) _saveToStorage('last_api_key', key);
      var cp = (document.getElementById('setting-custom-prompt').value || '').trim();
      _saveToStorage('custom_prompt', cp);
    }
    // Restore on page load
    document.addEventListener('DOMContentLoaded', restoreFromLocalStorage);
    // Auto-save API key on blur (when user leaves the field)
    document.addEventListener('DOMContentLoaded', function() {
      document.getElementById('gemini-api-key').addEventListener('blur', function() {
        var key = (this.value || '').trim();
        if (key) _saveToStorage('last_api_key', key);
      });
      document.getElementById('url-input').addEventListener('blur', function() {
        var url = (this.value || '').trim();
        if (url) _saveToStorage('last_url', url);
      });
    });

    // ─── Online Users Heartbeat ───────────────────────────────
    var _sessionId = _loadFromStorage('session_id');
    if (!_sessionId) {
      _sessionId = 'fb_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      _saveToStorage('session_id', _sessionId);
    }
    function sendHeartbeat() {
      fetch('heartbeat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sid: _sessionId})
      })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.online !== undefined) {
          var el = document.getElementById('online-count-text');
          if (el) el.textContent = d.online;
        }
      })
      .catch(function() {});
    }
    sendHeartbeat();
    setInterval(sendHeartbeat, 15000);

    // ─── Server Uptime & Stats ────────────────────────────────
    var _uptimeSeconds = 0;
    var _uptimeInterval = null;

    function fetchServerUptime() {
      // Uptime comes from K5ApiManager
      fetch('/K5ApiManager/api/uptime')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          _uptimeSeconds = d.uptime_seconds || 0;
          updateUptimeDisplay();
        })
        .catch(function() {});
    }

    function fetchFormBotStats() {
      // FormBot-specific stats (forms filled, questions, etc.)
      fetch('api/stats')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          // Session stats (this server run)
          var s = d.session || d;
          var el;
          el = document.getElementById('stat-forms');
          if (el) el.textContent = s.forms_filled || 0;
          el = document.getElementById('stat-submitted');
          if (el) el.textContent = s.forms_submitted || 0;
          el = document.getElementById('stat-questions');
          if (el) el.textContent = s.questions_answered || 0;
          el = document.getElementById('stat-ai');
          if (el) el.textContent = s.ai_answers || 0;
          el = document.getElementById('stat-random');
          if (el) el.textContent = s.random_answers || 0;
          el = document.getElementById('stat-failed');
          if (el) el.textContent = s.forms_failed || 0;
          el = document.getElementById('stat-previewed');
          if (el) el.textContent = s.forms_previewed || 0;
          el = document.getElementById('stat-cached');
          if (el) el.textContent = s.cached_forms || 0;
          // Global stats (all-time, from database)
          var g = d.global || {};
          console.log('[FormBot Stats] Session:', s, 'Global:', g);
          el = document.getElementById('gstat-forms');
          if (el) el.textContent = Math.floor(g.forms_filled || 0);
          el = document.getElementById('gstat-submitted');
          if (el) el.textContent = Math.floor(g.forms_submitted || 0);
          el = document.getElementById('gstat-questions');
          if (el) el.textContent = Math.floor(g.questions_answered || 0);
          el = document.getElementById('gstat-ai');
          if (el) el.textContent = Math.floor(g.ai_answers || 0);
          el = document.getElementById('gstat-failed');
          if (el) el.textContent = Math.floor(g.forms_failed || 0);
          el = document.getElementById('gstat-previewed');
          if (el) el.textContent = Math.floor(g.forms_previewed || 0);
          el = document.getElementById('gstat-random');
          if (el) el.textContent = Math.floor(g.random_answers || 0);
        })
        .catch(function() {});
    }

    function formatUptime(totalSec) {
      var d = Math.floor(totalSec / 86400);
      var h = Math.floor((totalSec % 86400) / 3600);
      var m = Math.floor((totalSec % 3600) / 60);
      var s = Math.floor(totalSec % 60);
      var parts = [];
      if (d > 0) parts.push(d + 'd');
      if (h > 0) parts.push(h + 'h');
      parts.push(m + 'm');
      parts.push(s + 's');
      return parts.join(' ');
    }

    function updateUptimeDisplay() {
      var el = document.getElementById('uptime-text');
      if (el) el.textContent = formatUptime(_uptimeSeconds);
    }

    // Fetch uptime + stats on load, then poll every 10s; tick uptime locally every 1s
    fetchServerUptime();
    fetchFormBotStats();
    setInterval(fetchServerUptime, 10000);
    setInterval(fetchFormBotStats, 10000);
    _uptimeInterval = setInterval(function() {
      _uptimeSeconds++;
      updateUptimeDisplay();
    }, 1000);


    // ─── Settings Panel ──────────────────────────────────────
    function toggleSettingsPanel() {
      const body = document.getElementById('settings-body');
      const btn = document.getElementById('settings-toggle-btn');
      if (body.style.display === 'none') {
        body.style.display = 'block';
        btn.innerHTML = '&#9650; Zwin';
      } else {
        body.style.display = 'none';
        btn.innerHTML = '&#9660; Rozwin';
      }
    }

    function updateTimingVal(slider) {
      var valEl = document.getElementById(slider.id + '-val');
      if (valEl) valEl.textContent = slider.value + 's';
    }

    function collectSettings() {
      return {
        empty_chance: document.getElementById('setting-empty-chance').checked,
        short_answers: document.getElementById('setting-short-answers').checked,
        custom_prompt: (document.getElementById('setting-custom-prompt').value || '').trim(),
        timing: {
          radio: parseInt(document.getElementById('timing-radio').value) || 5,
          checkbox: parseInt(document.getElementById('timing-checkbox').value) || 8,
          text: parseInt(document.getElementById('timing-text').value) || 15,
          matrix: parseInt(document.getElementById('timing-matrix').value) || 10,
          offset: parseInt(document.getElementById('timing-offset').value) || 10
        }
      };
    }

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
    function previewForm(forceRefresh) {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }
      saveCurrentInputs();

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
      _previewNavCurrent = 0;
      document.getElementById('preview-nav').style.display = 'none';

      const encodedUrl = encodeURIComponent(url);
      var qs = 'preview-form?url=' + encodedUrl;
      if (forceRefresh) qs += '&refresh=1';
      const evtSource = new EventSource(qs);

      evtSource.addEventListener('status', function(e) {
        document.getElementById('preview-status-text').textContent = e.data;
        var navStatus = document.getElementById('preview-nav-status');
        if (navStatus) navStatus.textContent = e.data;
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
        // Dedup by normalized title
        const normTitle = d.title.toLowerCase().replace(/\s+/g, ' ').trim();
        const isDupe = previewData.some(function(existing) {
          return existing.title.toLowerCase().replace(/\s+/g, ' ').trim() === normTitle;
        });
        if (isDupe) return; // skip duplicate
        d.num = previewData.length + 1; // renumber
        previewData.push(d);
        renderPreviewQuestion(d);
        updatePreviewNav();
      });

      evtSource.addEventListener('preview_done', function(e) {
        evtSource.close();
        previewStatus.style.display = 'none';
        previewActions.style.display = 'flex';
        previewBtn.disabled = false;
        startBtn.disabled = false;
        var navStatus = document.getElementById('preview-nav-status');
        if (navStatus) navStatus.textContent = '\u2705 Gotowe — ' + previewData.length + ' pytan';
      });

      evtSource.addEventListener('error_ev', function(e) {
        evtSource.close();
        document.getElementById('preview-spinner').style.display = 'none';
        document.getElementById('preview-status').style.display = 'none';
        var errDiv = document.createElement('div');
        errDiv.style.cssText = 'background:linear-gradient(135deg,rgba(239,68,68,0.08),rgba(220,38,38,0.04)); border:1px solid rgba(239,68,68,0.25); border-radius:12px; padding:16px 20px; margin-bottom:14px; display:flex; align-items:center; gap:12px;';
        errDiv.innerHTML = '<span style="font-size:1.4rem;">&#9888;&#65039;</span>'
          + '<div><div style="font-weight:600; color:#dc2626; font-size:0.92rem;">Blad</div>'
          + '<div style="color:#991b1b; font-size:0.82rem; margin-top:2px;">' + escHtml(e.data) + '</div></div>';
        document.getElementById('preview-questions').prepend(errDiv);
        previewBtn.disabled = false;
        startBtn.disabled = false;
      });

      evtSource.onerror = function() {
        evtSource.close();
        document.getElementById('preview-spinner').style.display = 'none';
        document.getElementById('preview-status').style.display = 'none';
        var errDiv = document.createElement('div');
        errDiv.style.cssText = 'background:linear-gradient(135deg,rgba(245,158,11,0.08),rgba(217,119,6,0.04)); border:1px solid rgba(245,158,11,0.25); border-radius:12px; padding:16px 20px; margin-bottom:14px; display:flex; align-items:center; gap:12px;';
        errDiv.innerHTML = '<span style="font-size:1.4rem;">&#128268;</span>'
          + '<div><div style="font-weight:600; color:#d97706; font-size:0.92rem;">Polaczenie przerwane</div>'
          + '<div style="color:#92400e; font-size:0.82rem; margin-top:2px;">Serwer zakonczyl polaczenie. Kliknij Podglad ponownie.</div></div>';
        document.getElementById('preview-questions').prepend(errDiv);
        previewBtn.disabled = false;
        startBtn.disabled = false;
        var navStatus = document.getElementById('preview-nav-status');
        if (navStatus && previewData.length > 0) navStatus.textContent = '\u26a0 Przerwano (' + previewData.length + ' pytan)';
      };
    }

    var _previewNavCurrent = 0;

    function updatePreviewNav() {
      var nav = document.getElementById('preview-nav');
      var counter = document.getElementById('preview-nav-counter');
      var total = previewData.length;
      if (total >= 2) {
        nav.style.display = 'flex';
        counter.textContent = (_previewNavCurrent + 1) + '/' + total;
      } else {
        nav.style.display = 'none';
      }
    }

    function previewNavTo(dir) {
      var cards = document.querySelectorAll('.preview-q-card');
      if (!cards.length) return;
      var total = cards.length;
      if (dir === 'first') _previewNavCurrent = 0;
      else if (dir === 'last') _previewNavCurrent = total - 1;
      else if (dir === 'prev') _previewNavCurrent = Math.max(0, _previewNavCurrent - 1);
      else if (dir === 'next') _previewNavCurrent = Math.min(total - 1, _previewNavCurrent + 1);
      var target = cards[_previewNavCurrent];
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.style.transition = 'box-shadow 0.3s, border-color 0.3s';
        target.style.boxShadow = '0 0 0 3px rgba(13,148,136,0.35)';
        target.style.borderColor = '#0d9488';
        setTimeout(function() {
          target.style.boxShadow = '';
          target.style.borderColor = '';
        }, 1200);
      }
      updatePreviewNav();
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
      saveCurrentInputs();
      const weights = collectWeights();
      const settings = collectSettings();
      let repeatCount = parseInt(document.getElementById('repeat-count').value) || 1;
      repeatCount = Math.max(1, Math.min(10, repeatCount));

      if (repeatCount === 1) {
        _doStartFill(url, weights, null, settings);
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
          // Longer delay between runs to avoid detection/rate limits
          var delay = Math.floor(10000 + Math.random() * 10000); // 10-20 seconds
          var secs = Math.ceil(delay / 1000);
          repeatProgress.textContent = 'Runda ' + currentRun + '/' + repeatCount + ' zakonczona. Czekanie ' + secs + 's...';
          repeatProgress.style.color = '#f59e0b';
          var countdown = setInterval(function() {
            secs--;
            if (secs <= 0) {
              clearInterval(countdown);
              runNext();
            } else {
              repeatProgress.textContent = 'Nastepna runda za ' + secs + 's...';
            }
          }, 1000);
        }, settings);
      }

      runNext();
    }

    // ─── Start fill without weights (quick mode) ──────────
    function startFill() {
      const url = document.getElementById('url-input').value.trim();
      if (!url) { alert('Wpisz URL formularza!'); return; }
      saveCurrentInputs();
      _doStartFill(url, null, null, collectSettings());
    }

    function _doStartFill(url, weights, onComplete, settings) {
      if (!settings) settings = collectSettings();
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

      // Helper to actually open SSE after URL is ready
      function _openSSE() {
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
        var evtSource = new EventSource(sseUrl);
        _attachSSEHandlers(evtSource, onComplete);
      }

      // Store weights + settings server-side (avoids URL length limit)
      var payload = {};
      if (weights && Object.keys(weights).length > 0) payload.weights = weights;
      if (settings) payload.settings = settings;

      if (Object.keys(payload).length > 0) {
        fetch('store-weights', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
          .then(function(r){return r.json();})
          .then(function(d){
            if(d.token) sseUrl += '&weights_token=' + d.token;
            _openSSE();
          })
          .catch(function(){
            // Fallback to inline
            if (weights && Object.keys(weights).length > 0) sseUrl += '&weights=' + encodeURIComponent(JSON.stringify(weights));
            if (settings) sseUrl += '&settings=' + encodeURIComponent(JSON.stringify(settings));
            _openSSE();
          });
      } else {
        _openSSE();
      }
    }

    function _attachSSEHandlers(evtSource, onComplete) {
      const eventLog = document.getElementById('event-log');
      const statusText = document.getElementById('status-text');
      const spinner = document.getElementById('spinner');
      const btn = document.getElementById('start-btn');
      const previewBtn = document.getElementById('preview-btn');
      const previewActionBtns = document.querySelectorAll('#preview-actions button');

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
          : (d.source === 'Puste'
            ? '<span style="font-size:0.7rem; background:rgba(156,163,175,0.15); color:#6b7280; padding:1px 6px; border-radius:4px; margin-left:6px;">&#128683; Puste</span>'
            : '<span style="font-size:0.7rem; background:rgba(245,158,11,0.15); color:#d97706; padding:1px 6px; border-radius:4px; margin-left:6px;">&#127922; Losowe</span>');
        var tagsHtml = '';
        if (d.tags && d.tags.length > 0) {
          d.tags.forEach(function(tag) {
            tagsHtml += '<span style="font-size:0.65rem; background:rgba(99,102,241,0.1); color:#6366f1; padding:1px 5px; border-radius:4px; margin-left:4px;">&#9881; ' + escHtml(tag) + '</span>';
          });
        }
        div.innerHTML = '<div class="event-title">Odpowiedz Q' + d.num + srcBadge + tagsHtml + '</div>'
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
        var doneMsg = 'Gotowe! (' + d.questions_filled + ' pytan';
        if (d.total_time) doneMsg += ', ' + d.total_time + 's laczenie';
        doneMsg += ')';
        statusText.textContent = doneMsg;
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

      // Timing statistics summary
      if (data.total_time || data.time_per_type) {
        var statsDiv = document.createElement('div');
        statsDiv.style.cssText = 'padding:16px 20px; margin-bottom:14px; background:linear-gradient(135deg, rgba(13,148,136,0.08), rgba(8,145,178,0.05)); border:1px solid rgba(13,148,136,0.2); border-radius:12px;';
        var statsHtml = '<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;"><span style="font-size:1.1rem;">&#9201;</span><span style="font-weight:600; font-size:0.92rem; color:#0d9488;">Statystyki czasowe</span></div>';
        statsHtml += '<div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:8px;">';
        statsHtml += '<div style="padding:6px 12px; background:rgba(255,255,255,0.8); border-radius:8px; font-size:0.82rem;"><span style="color:#64748b;">Laczny czas:</span> <strong style="color:#0d9488;">' + (data.total_time || 0) + 's</strong></div>';
        var mins = Math.floor((data.total_time || 0) / 60);
        var secs = Math.round((data.total_time || 0) % 60);
        if (mins > 0) {
          statsHtml += '<div style="padding:6px 12px; background:rgba(255,255,255,0.8); border-radius:8px; font-size:0.82rem;"><span style="color:#64748b;">Czyli:</span> <strong style="color:#0d9488;">' + mins + 'min ' + secs + 's</strong></div>';
        }
        statsHtml += '</div>';
        if (data.time_per_type) {
          var typeLabels = {radio:'Jednokrotny', checkbox:'Wielokrotny', text:'Otwarte', matrix:'Macierz'};
          var typeBadges = {radio:'radio-badge', checkbox:'checkbox-badge', text:'text-badge', matrix:'matrix-badge'};
          statsHtml += '<div style="display:flex; flex-wrap:wrap; gap:6px;">';
          for (var ttype in data.time_per_type) {
            var tt = data.time_per_type[ttype];
            var lbl = typeLabels[ttype] || ttype;
            var badgeCls = typeBadges[ttype] || '';
            statsHtml += '<div style="padding:6px 12px; background:rgba(255,255,255,0.8); border-radius:8px; font-size:0.78rem; display:flex; align-items:center; gap:6px;">';
            if (badgeCls) statsHtml += '<span class="timing-type-badge ' + badgeCls + '">' + ttype + '</span>';
            statsHtml += '<span style="color:#334155;">' + lbl + ':</span> ';
            statsHtml += '<strong style="color:#0d9488;">' + tt.count + 'x</strong> ';
            statsHtml += '<span style="color:#64748b;">avg ' + tt.avg + 's</span> ';
            statsHtml += '<span style="color:#94a3b8;">(\u03a3 ' + tt.total + 's)</span>';
            statsHtml += '</div>';
          }
          statsHtml += '</div>';
        }
        statsDiv.innerHTML = statsHtml;
        list.appendChild(statsDiv);
      }

      (data.results || []).forEach(function(r) {
        const answerText = r.answer == null ? '-' :
          (Array.isArray(r.answer) ? r.answer.join(', ') :
          (typeof r.answer === 'object' ? JSON.stringify(r.answer) : r.answer));
        const card = document.createElement('div');
        card.className = 'result-card';
        const srcBadge = r.source === 'AI'
          ? '<span style="font-size:0.65rem; background:rgba(16,185,129,0.15); color:#059669; padding:1px 5px; border-radius:4px; margin-left:6px; font-weight:600;">&#129302; AI</span>'
          : (r.source === 'Puste'
            ? '<span style="font-size:0.65rem; background:rgba(156,163,175,0.15); color:#6b7280; padding:1px 5px; border-radius:4px; margin-left:6px; font-weight:600;">&#128683; Puste</span>'
            : '<span style="font-size:0.65rem; background:rgba(245,158,11,0.15); color:#d97706; padding:1px 5px; border-radius:4px; margin-left:6px; font-weight:600;">&#127922; Losowe</span>');
        var timeBadge = '';
        if (r.time_seconds != null) {
          timeBadge = '<span style="font-size:0.65rem; background:rgba(13,148,136,0.1); color:#0d9488; padding:1px 5px; border-radius:4px; margin-left:4px; font-weight:600;">&#9201; ' + r.time_seconds + 's</span>';
        }
        var rTagsHtml = '';
        if (r.tags && r.tags.length > 0) {
          r.tags.forEach(function(tag) {
            rTagsHtml += '<span style="font-size:0.6rem; background:rgba(99,102,241,0.1); color:#6366f1; padding:1px 5px; border-radius:4px; margin-left:3px;">&#9881; ' + escHtml(tag) + '</span>';
          });
        }
        card.innerHTML = '<div class="result-num">' + r.question_number + '</div>'
          + '<div class="result-body">'
          + '<div class="result-q">' + escHtml(r.title) + srcBadge + timeBadge + rTagsHtml + '</div>'
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
    force_refresh = request.args.get("refresh", "") == "1"
    if not form_url:
        def err_gen():
            yield 'event: error_ev\ndata: Podaj URL formularza\n\n'
        return Response(err_gen(), mimetype='text/event-stream')

    # Track preview stat
    with _session_stats_lock:
        _session_stats["forms_previewed"] += 1
    _increment_global_stat("forms_previewed")

    # Check preview cache first (unless forced refresh)
    cached = _preview_cache.get(form_url) if not force_refresh else None
    if cached:
        print(f"[FormBot] Preview: using cache ({len(cached)} questions)")
        def cached_gen():
            yield 'event: status\ndata: Ladowanie z cache...\n\n'
            import time as _t
            for q in cached:
                yield f'event: question_preview\ndata: {json.dumps(q, ensure_ascii=False)}\n\n'
                _t.sleep(0.02)  # tiny delay for smooth rendering
            yield f'event: status\ndata: Zaladowano {len(cached)} pytan z cache\n\n'
            yield 'event: preview_done\ndata: ok\n\n'
        return Response(cached_gen(), mimetype='text/event-stream')

    event_queue = Queue()
    user_label = request.remote_addr or "Uzytkownik"
    waiter_id = str(uuid.uuid4())
    _preview_collected = []  # collect questions for caching

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
                # Collect preview questions for caching
                if event_type == "question_preview":
                    _preview_collected.append(data)
                data = json.dumps(data, ensure_ascii=False)
            yield f'event: {event_type}\ndata: {data}\n\n'
        # Save to cache after scan completes
        if _preview_collected:
            # Dedup before saving
            deduped = []
            seen = set()
            for q in _preview_collected:
                tkey = ' '.join(q.get('title', '').lower().split())
                if tkey in seen:
                    continue
                seen.add(tkey)
                deduped.append(q)
            for i, q in enumerate(deduped, 1):
                q['num'] = i
            _preview_cache[form_url] = deduped
            _save_preview_cache()
            print(f"[FormBot] Preview: cached {len(deduped)} questions")

    return Response(generate(), mimetype='text/event-stream')


@app.route("/stream-fill", methods=["GET"])
def stream_fill():
    """SSE endpoint that streams live progress while filling the form."""
    form_url = request.args.get("url", "")
    if not form_url:
        def err_gen():
            yield 'event: error_ev\ndata: Podaj URL formularza\n\n'
        return Response(err_gen(), mimetype='text/event-stream')

    # Parse optional weights + settings - try token first (avoids URL length limit), fallback to inline
    weights = None
    settings = None
    weights_token = request.args.get("weights_token", "")
    if weights_token and weights_token in _stored_weights:
        stored_data = _stored_weights.pop(weights_token)  # consume once
        if isinstance(stored_data, dict) and "weights" in stored_data:
            weights = stored_data.get("weights")
            settings = stored_data.get("settings")
        else:
            # Legacy format: just weights
            weights = stored_data
    else:
        weights_raw = request.args.get("weights", "")
        if weights_raw:
            try:
                weights = json.loads(weights_raw)
            except (json.JSONDecodeError, ValueError):
                weights = None
        settings_raw = request.args.get("settings", "")
        if settings_raw:
            try:
                settings = json.loads(settings_raw)
            except (json.JSONDecodeError, ValueError):
                settings = None

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
                             ai_mode=ai_mode, ai_key=ai_key, settings=settings)
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
    import unicodedata

    def _normalize(s):
        """Normalize text for comparison: NFKC + strip + collapse whitespace."""
        s = unicodedata.normalize("NFKC", s)
        return ' '.join(s.split()).strip()

    if not isinstance(ai_row_answers, dict) or not ai_row_answers:
        print(f"[FormBot] MATRIX AI: Invalid ai_row_answers: {type(ai_row_answers)}")
        return {}

    # Find all radio buttons in this matrix question
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
    if aria_labels:
        print(f"[FormBot] MATRIX AI: Sample aria-labels: {aria_labels[:3]}")

    # Group radios by row title
    rows = {}  # row_title -> list of (radio_element, col_name, col_index)
    if column_headers:
        for radio, aria in zip(radios, aria_labels):
            row_title = aria
            col_name = ""
            col_idx_in_row = -1
            for ci, col in enumerate(column_headers):
                # Try exact suffix match, then normalized
                if aria.endswith(col) or _normalize(aria).endswith(_normalize(col)):
                    row_title = aria[: -len(col)].strip() if aria.endswith(col) else _normalize(aria)[: -len(_normalize(col))].strip()
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

    # Build normalized AI answer keys for fuzzy matching
    ai_norm = {_normalize(k): (k, v) for k, v in ai_row_answers.items()}

    # Now match AI answers to rows and click
    results = {}
    for row_title, radio_list in rows.items():
        row_norm = _normalize(row_title)

        # Find matching AI answer: exact -> normalized -> partial
        col_idx = ai_row_answers.get(row_title)
        if col_idx is None and row_norm in ai_norm:
            col_idx = ai_norm[row_norm][1]
        if col_idx is None:
            # Try partial matching (normalized)
            for ai_key_norm, (orig_key, val) in ai_norm.items():
                if ai_key_norm in row_norm or row_norm in ai_key_norm:
                    col_idx = val
                    break

        if col_idx is None:
            print(f"[FormBot] MATRIX AI: No match for row '{row_title[:60]}'")
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
                        p_num_radios = len(question_el.find_elements(By.CSS_SELECTOR, '[role="radio"]'))
                        for pri in range(p_num_radios):
                            try:
                                driver.execute_script(
                                    "var radios = arguments[0].querySelectorAll('[role=\"radio\"]');"
                                    "if(radios[arguments[1]]) radios[arguments[1]].click();",
                                    question_el, pri
                                )
                            except Exception:
                                pass
                            time.sleep(0.4)
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(0.2)
                            # Scan for conditional questions after each click
                            try:
                                cond_questions = driver.find_elements(By.CSS_SELECTOR, q_selector)
                                for cq in cond_questions:
                                    try:
                                        ct = _get_question_title(cq)
                                    except Exception:
                                        continue
                                    cq_id = cq.get_attribute("id") or ""
                                    cq_key = cq_id or ct
                                    if cq_key in answered_ids or not ct or ct == "(unknown question)":
                                        continue
                                    answered_ids.add(cq_key)
                                    question_num += 1
                                    ctype = _detect_question_type(cq)
                                    copts = _get_option_labels(cq, ctype)
                                    cpd = {"num": question_num, "title": ct, "type": ctype, "options": copts}
                                    if ctype == "matrix":
                                        cr, cc = _get_matrix_info(cq)
                                        cpd["options"] = cc
                                        cpd["rows"] = cr
                                    elif ctype == "text":
                                        cpd["text_answers"] = list(TEXT_ANSWERS)
                                    _emit("question_preview", cpd)
                                    _emit("status", f"Warunkowe Q{question_num}: {ct[:40]}...")
                            except Exception:
                                pass
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


def _perform_form_fill(form_url, event_queue=None, weights=None, ai_mode=False, ai_key="", settings=None):
    """Main function: opens the form, reads questions, fills random answers."""
    if settings is None:
        settings = {}
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
                scanned_ids = set()      # tracks DOM elements for outer loop
                scanned_titles = set()   # tracks titles for inline dedup (all branches)
                scan_num = 0

                for _scan_pass in range(15):
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

                        title = _get_question_title(q_el)
                        q_type = _detect_question_type(q_el)
                        options = _get_option_labels(q_el, q_type)

                        # Skip if already found (same title = duplicate)
                        title_key = ' '.join(title.lower().split())
                        if title_key not in scanned_titles:
                            scan_num += 1
                            q_data = {"num": scan_num, "title": title, "type": q_type, "options": options}
                            if q_type == "matrix":
                                row_titles, col_names = _get_matrix_info(q_el)
                                q_data["options"] = col_names
                                q_data["rows"] = row_titles
                            scanned_questions.append(q_data)
                            scanned_titles.add(title_key)
                            _emit("status", f"AI: Skanowanie Q{scan_num}: {title[:40]}...")

                        # Click through EACH radio option to discover ALL conditional branches
                        if q_type == "radio":
                            try:
                                num_radios = len(q_el.find_elements(By.CSS_SELECTOR, '[role="radio"]'))
                                for ri in range(num_radios):
                                    # Use JavaScript to click by index - immune to stale element refs
                                    try:
                                        scan_driver.execute_script(
                                            "var radios = arguments[0].querySelectorAll('[role=\"radio\"]');"
                                            "if(radios[arguments[1]]) radios[arguments[1]].click();",
                                            q_el, ri
                                        )
                                    except Exception:
                                        pass
                                    time.sleep(0.6)
                                    # Scroll down to reveal new questions
                                    scan_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                    time.sleep(0.3)
                                    # Scan ALL questions on page for new conditionals
                                    try:
                                        cond_questions = scan_driver.find_elements(By.CSS_SELECTOR, q_selector)
                                        for cq in cond_questions:
                                            try:
                                                ct = _get_question_title(cq)
                                            except Exception:
                                                continue
                                            ct_key = ' '.join(ct.lower().split())
                                            if not ct or ct == "(unknown question)" or ct_key in scanned_titles:
                                                continue
                                            # Found new conditional question!
                                            scanned_titles.add(ct_key)
                                            scan_num += 1
                                            ctype = _detect_question_type(cq)
                                            copts = _get_option_labels(cq, ctype)
                                            cdata = {"num": scan_num, "title": ct, "type": ctype, "options": copts}
                                            if ctype == "matrix":
                                                cr, cc = _get_matrix_info(cq)
                                                cdata["options"] = cc
                                                cdata["rows"] = cr
                                            scanned_questions.append(cdata)
                                            _emit("status", f"AI: Warunkowe Q{scan_num}: {ct[:40]}...")
                                            print(f"[FormBot] AI scan: conditional Q{scan_num}: {ct[:60]}")
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        elif q_type == "checkbox":
                            try:
                                checkboxes = q_el.find_elements(By.CSS_SELECTOR, '[role="checkbox"]')
                                for cb_opt in checkboxes:
                                    try:
                                        cb_opt.click()
                                    except Exception:
                                        try:
                                            scan_driver.execute_script("arguments[0].click();", cb_opt)
                                        except Exception:
                                            pass
                                    time.sleep(0.3)
                                # Uncheck all
                                for cb_opt in checkboxes:
                                    try:
                                        if cb_opt.get_attribute("aria-checked") == "true":
                                            cb_opt.click()
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                    if not new_found:
                        break
                    time.sleep(1)

                scan_driver.quit()

                # Handle duplicate question titles by adding a suffix
                # (AI needs unique titles to generate separate answers for each)
                seen_titles = {}
                for sq in scanned_questions:
                    t_key = ' '.join(sq['title'].lower().split())
                    if t_key in seen_titles:
                        seen_titles[t_key] += 1
                        sq['original_title'] = sq['title']
                        sq['title'] = f"{sq['title']} ({seen_titles[t_key]})"
                        print(f"[FormBot] AI scan: duplicate renamed -> {sq['title'][:80]}")
                    else:
                        seen_titles[t_key] = 1

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
            ai_answers = _ask_gemini_for_answers(scanned_questions, ai_key, _emit_fn=_emit, weights=weights, settings=settings)

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
        _used_ai_nums = set()  # Track consumed AI answer numbers (for duplicate questions)

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

                # Start timing this question
                _q_start_time = time.time()

                # Collect active settings tags for this question
                _q_tags = []

                # Apply timing delay based on question type
                try:
                    timing = settings.get("timing", {}) if settings else {}
                    if isinstance(timing, dict):
                        base_time = int(timing.get(q_type, 5))
                        offset_max = int(timing.get("offset", 10))
                    else:
                        base_time = 5
                        offset_max = 10
                    if base_time > 0 or offset_max > 0:
                        delay = base_time + random.uniform(0, offset_max)
                        _q_tags.append(f"Opoznienie {delay:.1f}s")
                        if delay > 0.5:
                            _emit("status", f"Czekanie {delay:.1f}s (symulacja czytania Q{question_num})...")
                            time.sleep(delay)
                except Exception as e:
                    print(f"[FormBot] Timing error: {e}, using defaults")
                    delay = 5 + random.uniform(0, 10)
                    _q_tags.append(f"Opoznienie {delay:.1f}s")
                    time.sleep(delay)

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
                    "source": "Losowe",
                    "tags": [],  # settings applied to this question
                }

                # Collect remaining settings tags for this question
                if q_type == "text":
                    if settings.get("empty_chance"):
                        _q_tags.append("Szansa na puste")
                    if settings.get("short_answers"):
                        _q_tags.append("Krotkie odp.")
                result_entry["tags"] = _q_tags

                # Check if AI has an answer for this question
                ai_answer_for_q = None
                if ai_answers:
                    # Try by number first
                    ai_answer_for_q = ai_answers.get(str(question_num))
                    if ai_answer_for_q is not None and str(question_num) not in _used_ai_nums:
                        _used_ai_nums.add(str(question_num))
                    elif ai_answer_for_q is not None:
                        # This number was already used, try title match instead
                        ai_answer_for_q = None

                    # Fallback: match by title (handles conditional questions shifting numbers)
                    if ai_answer_for_q is None and scanned_questions:
                        fill_title_norm = ' '.join(title.lower().split())
                        for sq in scanned_questions:
                            sq_num_str = str(sq['num'])
                            if sq_num_str in _used_ai_nums:
                                continue  # Skip already used answers
                            # Check both title and original_title (for renamed duplicates)
                            sq_title = sq.get('title', '')
                            sq_orig = sq.get('original_title', sq_title)
                            sq_title_norm = ' '.join(sq_title.lower().split())
                            sq_orig_norm = ' '.join(sq_orig.lower().split())
                            if sq_title and (
                                sq_title_norm == fill_title_norm
                                or sq_orig_norm == fill_title_norm
                                or sq_title_norm in fill_title_norm
                                or fill_title_norm in sq_title_norm
                                or sq_orig_norm in fill_title_norm
                                or fill_title_norm in sq_orig_norm
                            ):
                                ai_answer_for_q = ai_answers.get(sq_num_str)
                                if ai_answer_for_q is not None:
                                    _used_ai_nums.add(sq_num_str)
                                    print(f"[FormBot] AI: Matched by title (fill Q{question_num} = scan Q{sq['num']})")
                                    break

                if q_type == "radio":
                    source = "Losowe"
                    answer = None
                    if ai_answer_for_q is not None:
                        answer = _handle_radio_ai(question_el, ai_answer_for_q)
                        if answer:
                            source = "AI"
                    if not answer:
                        answer = _handle_radio_question(question_el, title, weights=weights)
                    result_entry["answer"] = answer
                    result_entry["source"] = source
                    print(f"[FormBot] Selected: {answer} ({source})")
                    _emit("answer", {"num": question_num, "answer": answer, "source": source, "tags": _q_tags})

                elif q_type == "checkbox":
                    source = "Losowe"
                    answers = None
                    if ai_answer_for_q is not None:
                        answers = _handle_checkbox_ai(question_el, ai_answer_for_q)
                        if answers:
                            source = "AI"
                    if not answers:
                        answers = _handle_checkbox_question(question_el, title, weights=weights)
                    result_entry["answer"] = answers
                    result_entry["source"] = source
                    print(f"[FormBot] Selected: {answers} ({source})")
                    _emit("answer", {"num": question_num, "answer": answers, "source": source, "tags": _q_tags})

                elif q_type == "matrix":
                    source = "Losowe"
                    answers = None
                    if ai_answer_for_q is not None:
                        answers = _handle_matrix_ai(question_el, ai_answer_for_q)
                        if answers:
                            source = "AI"
                    if not answers:
                        # AI returned empty or no AI answer — fallback to random
                        if ai_answer_for_q is not None:
                            print(f"[FormBot] MATRIX AI returned empty, falling back to random")
                        answers = _handle_matrix_question(question_el, title, weights=weights)
                    result_entry["answer"] = answers
                    result_entry["source"] = source
                    if answers:
                        for row, col in answers.items():
                            print(f"[FormBot]   {row} -> {col} ({source})")
                    _emit("answer", {"num": question_num, "answer": answers, "source": source, "tags": _q_tags})

                elif q_type == "text":
                    # Check empty chance setting
                    empty_chance = settings.get("empty_chance", False) if settings else False
                    if empty_chance and random.random() < random.uniform(0.20, 0.25):
                        # Skip this text question (leave empty)
                        result_entry["answer"] = ""
                        result_entry["source"] = "Puste"
                        result_entry["tags"] = _q_tags
                        print(f"[FormBot] Skipped text Q{question_num} (empty chance)")
                        _emit("answer", {"num": question_num, "answer": "(pominięte - puste)", "source": "Puste", "tags": _q_tags})
                    elif ai_answer_for_q is not None:
                        answer = _handle_text_ai(question_el, str(ai_answer_for_q))
                        source = "AI"
                        result_entry["answer"] = answer
                        result_entry["source"] = source
                        print(f"[FormBot] Typed: {answer} ({source})")
                        _emit("answer", {"num": question_num, "answer": answer, "source": source, "tags": _q_tags})
                    else:
                        answer = _handle_text_question(question_el, title, weights=weights)
                        source = "Losowe"
                        result_entry["answer"] = answer
                        result_entry["source"] = source
                        print(f"[FormBot] Typed: {answer} ({source})")
                        _emit("answer", {"num": question_num, "answer": answer, "source": source, "tags": _q_tags})

                else:
                    print(f"[FormBot] [WARN] Unknown question type, skipping.")
                    _emit("warn", f"Q{question_num}: nieznany typ pytania")

                results.append(result_entry)

                # Record time spent on this question
                _q_elapsed = round(time.time() - _q_start_time, 1)
                result_entry["time_seconds"] = _q_elapsed
                print(f"[FormBot] Q{question_num} took {_q_elapsed}s")

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

        # Compute timing statistics
        total_time = sum(r.get("time_seconds", 0) for r in results)
        time_per_type = {}
        for r in results:
            qt = r.get("type", "unknown")
            if qt not in time_per_type:
                time_per_type[qt] = {"count": 0, "total": 0}
            time_per_type[qt]["count"] += 1
            time_per_type[qt]["total"] += r.get("time_seconds", 0)
        for qt in time_per_type:
            c = time_per_type[qt]["count"]
            time_per_type[qt]["avg"] = round(time_per_type[qt]["total"] / c, 1) if c > 0 else 0
            time_per_type[qt]["total"] = round(time_per_type[qt]["total"], 1)

        final_data = {
            "status": submit_status,
            "questions_filled": len(results),
            "results": results,
            "total_time": round(total_time, 1),
            "time_per_type": time_per_type,
        }

        # ─── Track session stats ──────────────────────────────
        with _session_stats_lock:
            _session_stats["forms_filled"] += 1
            _increment_global_stat("forms_filled")
            if submit_status == "submitted":
                _session_stats["forms_submitted"] += 1
                _increment_global_stat("forms_submitted")
            elif submit_status in ("submit_failed", "no_submit_button"):
                _session_stats["forms_failed"] += 1
                _increment_global_stat("forms_failed")
            _session_stats["questions_answered"] += len(results)
            _increment_global_stat("questions_answered", len(results))
            for r in results:
                src = r.get("source", "")
                if src == "AI":
                    _session_stats["ai_answers"] += 1
                    _increment_global_stat("ai_answers")
                elif src == "Puste":
                    _session_stats["empty_answers"] += 1
                    _increment_global_stat("empty_answers")
                else:
                    _session_stats["random_answers"] += 1
                    _increment_global_stat("random_answers")

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
