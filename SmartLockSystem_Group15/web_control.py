# web_control.py
from flask import Flask, request, redirect, url_for, render_template_string, flash
import importlib, builtins

import steppingmotor

import lcd16x2 as lcd

APP_SECRET = "change-me"
app = Flask(__name__)
app.secret_key = APP_SECRET

# ---- lazy loader that prevents CLI prompts on import ----
_fc = None
def load_fc():
    """Import fingerprint_controller without interactive prompts."""
    global _fc
    if _fc is not None:
        return _fc
    old_input = builtins.input
    try:
        # If fingerprint_controller starts a CLI on import,
        # feeding 'q' will make it exit immediately.
        builtins.input = lambda prompt="": "q"
        _fc = importlib.import_module("fingerprint_controller")
        print("fingerprint_controller imported")
    finally:
        builtins.input = old_input
    return _fc
# ---------------------------------------------------------

TEMPLATE = """
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Locker Control</title>
<style>
 body{font-family:sans-serif;margin:20px;max-width:720px}
 fieldset{margin:12px 0;padding:12px}
 button{padding:8px 14px;margin:4px 0}
 input[type=text]{padding:6px;width:60%}
 .ok{color:#0a0}.err{color:#a00}
</style>
</head><body>
<h1>Smart Locker – Web Control</h1>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul>
    {% for cat, msg in messages %}
      <li class="{{ 'ok' if cat=='success' else 'err' }}">{{ msg }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

<fieldset>
  <legend>Enroll fingerprint</legend>
  <form method="post" action="{{ url_for('enroll') }}">
    <label>Name: <input type="text" name="name" required></label>
    <div><button type="submit">Enroll (will prompt on sensor)</button></div>
  </form>
</fieldset>

<fieldset>
  <legend>Find / Unlock</legend>
  <form method="post" action="{{ url_for('scan') }}">
    <button type="submit">Scan & Match (place finger)</button>
  </form>
</fieldset>

<fieldset>
  <legend>Delete template</legend>
  <form method="post" action="{{ url_for('delete') }}">
    <label>Name: <input type="text" name="name" required></label>
    <div><button type="submit">Delete</button></div>
  </form>
</fieldset>

<fieldset>
  <legend>Motor</legend>
  <form method="post" action="{{ url_for('unlock_only') }}"><button>Rotate 180° / wait / back</button></form>
</fieldset>

<fieldset>
  <legend>LCD</legend>
  <form method="post" action="{{ url_for('lcdprint') }}">
    <div><input type="text" name="l1" placeholder="Line 1 (<=16 chars)"></div>
    <div><input type="text" name="l2" placeholder="Line 2 (<=16 chars)"></div>
    <div><button type="submit">Show on LCD</button></div>
  </form>
</fieldset>

</body></html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(TEMPLATE)

@app.route("/enroll", methods=["POST"])
def enroll():
    fc = load_fc()
    name = request.form.get("name","").strip()
    if not name:
        flash("Name required", "error"); return redirect(url_for("index"))

    # pass name to existing enroll_finger() which reads input()
    old_input = builtins.input
    builtins.input = lambda prompt="": name
    try:
        ok = fc.enroll_finger()
    finally:
        builtins.input = old_input

    if ok:
        flash(f'Enrolled "{name}"', "success")
        try: lcd and lcd.lcd_print("Enrolled", name)
        except Exception: pass
    else:
        flash("Enroll failed", "error")
    return redirect(url_for("index"))

@app.route("/scan", methods=["POST"])
def scan():
    fc = load_fc()
    try:
        ok = fc.get_fingerprint()
        if ok:
            flash("Match OK — unlocking", "success")
            try: lcd and lcd.lcd_print("Access OK","Unlocking")
            except Exception: pass
            try: steppingmotor and steppingmotor.rotate_unlock()
            except Exception: pass
        else:
            flash("No match / below threshold", "error")
            try: lcd and lcd.lcd_print("Denied","Try again")
            except Exception: pass
    except Exception as e:
        flash(f"Scan error: {e}", "error")
    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete():
    fc = load_fc()
    name = request.form.get("name","").strip()
    if not name:
        flash("Name required", "error"); return redirect(url_for("index"))

    old_input = builtins.input
    builtins.input = lambda prompt="": name
    try:
        rc = fc.delete_model_updated()
    finally:
        builtins.input = old_input

    if rc == fc.adafruit_fingerprint.OK:
        flash(f'Deleted "{name}"', "success")
    else:
        flash(f'Failed to delete "{name}" (code {rc})', "error")
    return redirect(url_for("index"))

@app.route("/unlock_only", methods=["POST"])
def unlock_only():
    try:
        steppingmotor and steppingmotor.rotate_unlock()
        flash("Motor cycle done", "success")
    except Exception as e:
        flash(f"Motor error: {e}", "error")
    return redirect(url_for("index"))

@app.route("/lcdprint", methods=["POST"])
def lcdprint():
    l1 = (request.form.get("l1") or "")[:16]
    l2 = (request.form.get("l2") or "")[:16]
    try:
        lcd and lcd.lcd_print(l1, l2)
        flash("LCD updated", "success")
    except Exception as e:
        flash(f"LCD error: {e}", "error")
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Starts immediately; no CLI prompts block startup
    app.run(host="0.0.0.0", port=8080, debug=False)
