#!/usr/bin/env python3
import os, time, subprocess, threading, json, collections, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import RPi.GPIO as GPIO
from flask import Flask, jsonify
from flask_cors import CORS

# Define GPIO pins
SND_PIN  = 25   # For sound sensor
LED_PIN  = 22   # For alarm LED
BUZZ_PIN = 23   # For alarm buzzer（1=buzzing，0=silent）
SERVO    = 12   # For servo motor

# Other constants for configs
ANGLES = [20, 60, 100, 140] # Servo angles to capture photos
PHOTO_DIR = "captures" # Directory to save photos
RES_W, RES_H = 2592, 1944
ROTATE = "180"
MOVE_SETTLE = 0.6
DEBOUNCE_MS = 20

# Email configs, need to set environment variables in OS as well
# Replace with your actual emails and password below
EMAIL_FROM = os.getenv("EMAIL_FROM", "emailfrom@email.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "emailfrompwd")  
EMAIL_TO   = "emailto@email.com"
SMTP_HOST  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.getenv("SMTP_PORT", "465"))

# Configure Flask app
app = Flask(__name__, static_url_path="/captures", static_folder=PHOTO_DIR)
CORS(app)

def ts(): return time.strftime("%H:%M:%S")

# Dict for shared states
state_lock = threading.Lock()
state = {
    "buzzer": 1,               # 0=silent, 1=buzzing
    "led": 0,                  # 0=LED OFF, 1=LED ON
    "last_event": "--:--:--", # Stringified timestamp of the last triggering event
    "last_photo_url": "", # URL path of the last captured photo
}
logs = collections.deque(maxlen=50) 
alarm_active = False # True if currently in alarm state

def log(level, msg):
    """
    Simple logger function
    """
    item = {"level": level, "msg": msg, "time": ts()}
    with state_lock:
        logs.append(item)
    print(f"[{item['time']}] {level}: {msg}", flush=True)

def send_email_async(subject, html_body):
    """
    Simple async email sender function
    """
    def _worker():
        try:
            if not EMAIL_FROM or not EMAIL_PASS:
                log("warn", "email not configured (EMAIL_FROM/EMAIL_PASS missing)")
                return
            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"]   = EMAIL_TO
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as smtp:
                smtp.login(EMAIL_FROM, EMAIL_PASS)
                smtp.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
            log("info", "email sent")
        except Exception as e:
            log("error", f"email send failed: {e}")
    threading.Thread(target=_worker, daemon=True).start()

# Initialize GPIO mode and pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN,  GPIO.OUT); GPIO.output(LED_PIN, 0)  # LED starts as OFF
GPIO.setup(BUZZ_PIN, GPIO.OUT); GPIO.output(BUZZ_PIN, 0) # Buzzer starts as silent
# Set the sound sensor to be pulled up so that the current will be predictable
GPIO.setup(SND_PIN,  GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(SERVO, GPIO.OUT)
# Set up pulse-width modulation for servo motor to 50Hz
pwm = GPIO.PWM(SERVO, 50)
pwm.start(0)

def set_outputs(buzzer=None, led=None):
    """
    Set buzzer and LED outputs (i.e. turn buzzer/LED on or off)
    """
    with state_lock:
        if buzzer is not None:
            GPIO.output(BUZZ_PIN, buzzer)  
            state["buzzer"] = int(buzzer)
        if led is not None:
            GPIO.output(LED_PIN, led)
            state["led"] = int(led)

def set_angle(angle):
    """
    Set the angle of the servo motor
    """
    angle = max(0, min(180, angle))
    duty = 2 + angle / 18.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.35)
    pwm.ChangeDutyCycle(0)

def shoot(angle):
    """
    Control the camera to take a photo at the given angle
    """
    ts_str = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    fname = f"{PHOTO_DIR}/{ts_str}_{angle}.jpg"

    cmd = [
        "rpicam-still", "-n",
        "-o", fname,
        "--timeout", "500",
        "--width", str(RES_W),
        "--height", str(RES_H),
        "--rotation", ROTATE,
    ]
    subprocess.run(cmd, check=True)
    url = f"/captures/{os.path.basename(fname)}"

    with state_lock:
        state["last_photo_url"] = url
        state["last_event"] = ts()
    log("info", f"photo saved: {url}")

def sweep_and_shoot():
    """
    Sweep the servo motor across predefined angles and let camera take photos.
    """
    set_angle(90); time.sleep(0.5)
    for a in ANGLES:
        log("info", f"move to {a}")
        set_angle(a)
        time.sleep(MOVE_SETTLE)
        try:
            shoot(a)
        except Exception as e:
            log("error", f"capture error: {e}")
    set_angle(90)

def start_buzzing():
    """
    Starts buzzing after the sound sensor is triggered (until "/api/reset" stops it)
    """
    set_outputs(buzzer=1, led=1) 
    log("info", "buzzer ON (continuous until reset)")

def stop_buzzing():
    """
    Stops buzzing (to be called when reset)
    """
    set_outputs(buzzer=0, led=0)
    log("info", "buzzer OFF (via reset)")

def on_edge(_):
    """
    Sound edge trigger: not in alarm (silent) -> start continuous buzzing + send email + take photo at the same time
    """
    global alarm_active
    # Sound detected will make GPIO.input to LOW (active low)
    if GPIO.input(SND_PIN) == 0:
        with state_lock:
            already = alarm_active
            if not alarm_active:
                alarm_active = True
                state["last_event"] = ts()
        if already:
            return  # If already in alarm state, ignore

        log("info", "sound detected - start continuous alarm")

        # Keep buzzing (until Reset)
        start_buzzing()

        # Send email (async)
        send_email_async(
            subject="G10 Alarm Detected",
            html_body=f"""
            <h3>G10 Alarm</h3>
            <p>Sound detected at <b>{time.strftime('%Y-%m-%d %H:%M:%S')}</b>.</p >
            <p>The buzzer is now ON until reset.</p >
            """
        )

        # Take photos with sweep
        threading.Thread(target=sweep_and_shoot, daemon=True).start()

def edge_worker():
    """
    Edge detection worker thread: set up edge detection on the sound sensor pin.
    """
    time.sleep(0.1)
    try:
        GPIO.remove_event_detect(SND_PIN)
    except Exception:
        pass
    try:
        GPIO.add_event_detect(SND_PIN, GPIO.BOTH, callback=on_edge, bouncetime=DEBOUNCE_MS)
        log("info", f"edge detection enabled on GPIO {SND_PIN}")
    except RuntimeError as e:
        log("error", f"edge detection failed: {e}; fallback to polling")
        # Fallback to polling method
        last = GPIO.input(SND_PIN)
        while True:
            v = GPIO.input(SND_PIN)
            if v != last:
                on_edge(None)
                last = v
            time.sleep(0.005)

# Define REST APIs
@app.route("/api/status")
def api_status():
    """
    Get current status of the home monitor in JSON format
    """
    with state_lock:
        data = {
            "buzzer": state["buzzer"],          
            "led": state["led"],                
            "last_event": state["last_event"],
            "last_photo_url": state["last_photo_url"],
            "alarm_active": alarm_active,       
            "logs": list(logs)[-10:],
        }
    return jsonify(data)

@app.route("/api/reset", methods=["POST"])
def api_reset():
    """
    Reset the alarm state: stop buzzing and turn off LED"""
    global alarm_active

    stop_buzzing()
    # reset alarm state
    with state_lock:
        alarm_active = False
        state["last_event"] = ts()
    log("info", "reset by API")
    # Return current status after reset to be used by frontend
    with state_lock:
        return jsonify({
            "ok": True,
            "time": ts(),
            "alarm_active": alarm_active,
            "buzzer": state["buzzer"],
            "led": state["led"],
            "last_event": state["last_event"]
        })

@app.route("/api/mock_trigger", methods=["POST"])
def api_mock_trigger():
    """
    Mock trigger the sound sensor (for testing purposes)
    """
    on_edge(None)
    return jsonify({"ok": True})

def main():
    log("info", "G10 HTTP node starting...")
    threading.Thread(target=edge_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            pwm.stop()
        except:
            pass
        # Cleanup GPIO before exit
        set_outputs(buzzer=0, led=0)
        GPIO.cleanup()
        log("info", "cleaned up.")
