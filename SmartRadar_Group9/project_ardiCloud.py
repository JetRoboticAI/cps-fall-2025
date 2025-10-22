import time
import threading
import RPi.GPIO as GPIO
from gpiozero import OutputDevice, AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from arduino_iot_cloud import ArduinoCloudClient
from secrets import DEVICE_ID, SECRET_KEY

# ---- Create the Arduino Cloud client ----
client = ArduinoCloudClient(
    device_id=DEVICE_ID,
    username=DEVICE_ID,
    password=SECRET_KEY,
    sync_mode=True
)

# Register variables
client.register("distance", value=0.0) #distance (float)
client.register("led", value=False)  #led (boolean)

# Start the connection
client.start()

# ===== Pins =====
IR_PIN = 17            # IR DO (low = object present)
TRIG, ECHO = 23, 24    # Ultrasonic (ECHO needs 5V -> 3.3V level shifting/voltage divider)
RED, GREEN, BLUE = 5, 6, 13
BUZZ_PIN = 22          # Active buzzer, low level beeps
SERVO_PIN = 12         # Servo (pin that supports hardware PWM)

# ===== Params =====
THRESHOLD_CM = 120.0     # Clearance distance threshold
CLEAR_REQUIRED = 3       # Number of consecutive passes required (debounce against sporadic misreads)
MEAS_INTERVAL = 0.12     # Ultrasonic sampling interval
SOUND_SPEED = 343.0

# ===== GPIO setup =====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# IR
GPIO.setup(IR_PIN, GPIO.IN)

# Ultrasonic
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)

# RGB
GPIO.setup(RED, GPIO.OUT); GPIO.setup(GREEN, GPIO.OUT); GPIO.setup(BLUE, GPIO.OUT)

def led_off():   GPIO.output((RED, GREEN, BLUE), (0, 0, 0))
def led_green(): GPIO.output((RED, GREEN, BLUE), (0, 1, 0))
def led_red():   GPIO.output((RED, GREEN, BLUE), (1, 0, 0))

# Buzzer（active_low）
buzz = OutputDevice(BUZZ_PIN, active_high=False, initial_value=False)
def buzz_double():
    for _ in range(2):
        buzz.on();  time.sleep(0.18)
        buzz.off(); time.sleep(0.14)

# Servo (pigpio backend)
factory = PiGPIOFactory()
servo = AngularServo(
    SERVO_PIN, min_angle=0, max_angle=180,
    min_pulse_width=0.0005, max_pulse_width=0.0025,
    pin_factory=factory
)

def measure_distance(timeout=0.03):
    """HC-SR04 distance in cm; returns None if no echo"""
    GPIO.output(TRIG, False); time.sleep(0.000002)
    GPIO.output(TRIG, True);  time.sleep(0.00001)
    GPIO.output(TRIG, False)

    t0 = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time() - t0 > timeout: return None
    start = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - start > timeout: return None
    dur = time.time() - start
    return (dur * SOUND_SPEED / 2.0) * 100.0

# ===== Servo sweep thread =====
scan_enable = threading.Event(); scan_enable.set()
running = True

def sweep_thread():
    angle = 0.0
    step = 2.0       # Step angle
    dwell = 0.03     # Delay between steps
    direction = +1
    servo.angle = angle
    while running:
        if scan_enable.is_set():
            angle += step * direction
            if angle >= 180: angle, direction = 180, -1
            elif angle <= 0: angle, direction = 0, +1
            servo.angle = angle
            time.sleep(dwell)
        else:
            time.sleep(0.02)  # hold

def main():
    led_green()
    t = threading.Thread(target=sweep_thread, daemon=True); t.start()
    print("Radar: scanning. After IR triggers, the system latches until ultrasonic > 120 cm, then resumes.")

    ir_latched = False  # False = IR active; True = latched, ignore IR

    try:
        while True:
            if not ir_latched:
                # Only read IR when not latched
                s = GPIO.input(IR_PIN)
                if s == 0:  #  IR triggered: latch and handle
                    ir_latched = True
                    scan_enable.clear()  # Stop servo
                    led_red()
                    buzz_double()
                    print("IR triggered → stop rotation, enter ultrasonic wait-for-clear...")
                    # Immediately enter distance wait loop
                else:
                    time.sleep(0.02)
                    continue

            # ---- Latched state: only measure distance until "CLEAR_REQUIRED consecutive > THRESHOLD_CM" ----
            if ir_latched:
                clear_hits = 0
                while ir_latched:
                    time.sleep(0.2)
                    dist = measure_distance()
                    
                    client["distance"] = dist
                    client["led"] = True
                    client.update()
                    
                    if dist is not None:
                        print(f"距离: {dist:6.2f} cm")
                        if dist > THRESHOLD_CM:
                            clear_hits += 1
                            if clear_hits >= CLEAR_REQUIRED:
                                # Unlock; resume scanning and IR
                                
                                client["led"] = False
                                client.update()
                                
                                led_green()
                                scan_enable.set()
                                ir_latched = False
                                print("Cleared consecutively; resuming rotation and IR.")
                                time.sleep(0.2)
                                break
                        else:
                            clear_hits = 0  # Below threshold; reset counter
                    time.sleep(MEAS_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        global running
        running = False
        led_off()
        buzz.off()
        try: servo.detach()
        except Exception: pass
        GPIO.cleanup()
        print("Exit.")

if __name__ == "__main__":
    main()
