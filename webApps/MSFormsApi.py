import os
import random
import time
import threading

from flask import Flask, jsonify, request, render_template_string
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

# Global lock to ensure only one Selenium instance runs at a time (saves memory)
scraping_lock = threading.Lock()


@app.route("/")
def home():
    return render_template_string(
        """
    <!doctype html>
    <html>
      <head><title>MS Forms Bot</title></head>
      <body>
        <h1>Forms Auto-filler. Use /fill-form or /fill-form/&lt;URL&gt; to run.</h1>
      </body>
    </html>
    """
    )


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
    with scraping_lock:
        return _perform_form_fill(target_url)


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
    # Try MS Forms selector first, then Google Forms, then generic heading
    for selector in [
        'div[data-automation-id="questionTitle"]',
        'div[role="heading"]',
        'span[class*="title"]',
        'h2', 'h3',
    ]:
        try:
            title_el = question_el.find_element(By.CSS_SELECTOR, selector)
            text = title_el.text.strip()
            if text:
                return text
        except Exception:
            continue
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


def _perform_form_fill(form_url):
    """Main function: opens the form, reads questions, fills random answers."""
    driver = None
    results = []
    provider = _detect_provider(form_url)

    try:
        print(f"[FormBot] Provider detected: {provider}")
        print(f"[FormBot] Initializing Chrome driver...")
        driver = _create_driver()
        driver.set_page_load_timeout(60)

        print(f"[FormBot] Navigating to form: {form_url}")
        driver.get(form_url)

        # Wait for the form to load using provider-specific selector
        q_selector = QUESTION_SELECTORS.get(provider, QUESTION_SELECTORS["unknown"])
        t_selector = TITLE_SELECTORS.get(provider, TITLE_SELECTORS["unknown"])
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

                elif q_type == "checkbox":
                    answers = _handle_checkbox_question(question_el, title)
                    result_entry["answer"] = answers
                    print(f"[FormBot] Selected: {answers}")

                elif q_type == "matrix":
                    answers = _handle_matrix_question(question_el, title)
                    result_entry["answer"] = answers
                    if answers:
                        for row, col in answers.items():
                            print(f"[FormBot]   {row} -> {col}")

                elif q_type == "text":
                    answer = _handle_text_question(question_el, title)
                    result_entry["answer"] = answer
                    print(f"[FormBot] Typed: {answer}")

                else:
                    print(f"[FormBot] [WARN] Unknown question type, skipping.")

                results.append(result_entry)
                time.sleep(0.5)

            if not new_questions_found:
                # No new questions appeared - we're done
                break

            # Wait a moment for any conditional questions to appear after answers
            time.sleep(1.5)
            print(f"[FormBot] Re-scanning for new conditional questions (pass {_pass + 1})...")

        # ── Submit or print results ──────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"[FormBot] FORM FILL COMPLETE - {len(results)} questions processed.")
        print(f"{'='*60}")

        if ALLOW_SEND:
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
                    time.sleep(3)
                except Exception as click_err:
                    # Fallback: JS click
                    print(f"[FormBot] Normal click failed ({click_err}), trying JS click...")
                    try:
                        driver.execute_script("arguments[0].click();", submit_btn)
                        print("[FormBot] [OK] Form submitted via JS click!")
                        time.sleep(3)
                    except Exception as js_err:
                        print(f"[FormBot] [FAIL] JS click also failed: {js_err}")
            else:
                print("[FormBot] [FAIL] Could not find submit button on the page.")
        else:
            print("[FormBot] ALLOW_SEND=False - NOT submitting. Printing results:")
            for r in results:
                print(f"  Q{r['question_number']}: {r['title']}")
                print(f"    Type: {r['type']}")
                print(f"    Answer: {r['answer']}")
                print()

    except Exception as e:
        error_msg = str(e)
        print(f"[FormBot] ERROR: {error_msg}")
        last_url = "Unknown"
        try:
            if driver:
                last_url = driver.current_url
        except Exception:
            pass
        return jsonify({"error": error_msg, "last_url": last_url}), 500

    finally:
        if driver:
            print(f"[FormBot] Quitting driver...")
            driver.quit()

    return jsonify(
        {
            "status": "submitted" if ALLOW_SEND else "dry_run",
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
