# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
# Code source: https://learn.adafruit.com/adafruit-optical-fingerprint-sensor/circuitpython
# In this case our team only used the function name and structures since adafruit_fingerprint does not provide a method for local file fingerprint recognition (it only support RAM-level find).
# So adafruit_fingerprint was only included in the enroll and delete part.
# For find part, we used pyfingerprint library to implement local file fingerprint recognition instead.
import os
import re
import glob
# Fingerprint template folder (next to this script)
HERE = os.path.dirname(__file__)
FP_DIR = os.path.join(HERE, "fingerprints")
os.makedirs(FP_DIR, exist_ok=True)

import time
import steppingmotor
import lcd16x2
import board
from digitalio import DigitalInOut, Direction

import adafruit_fingerprint

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

import serial
uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)

finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

##################################################


def get_fingerprint():
    """
    Capture a finger and compare it against templates in ./fingerprints
    using the sensor's own matcher via PyFingerprint.

    We temporarily close the global Adafruit/pyserial port so PyFingerprint
    can use the UART exclusively, then restore it afterwards.
    """
    global finger, uart
    try:
        from pyfingerprint.pyfingerprint import PyFingerprint
    except Exception as e:
        print("PyFingerprint not installed. Install it and retry. Error:", e)
        return False

    THRESHOLD = 50  # set to 150 if you prefer a stricter match

    # 0) Sanity: templates folder
    if not os.path.isdir(FP_DIR):
        lcd16x2.lcd_print("No folder found", "Create first")
        return False

    files = sorted(f for f in os.listdir(FP_DIR) if f.lower().endswith(".bin"))
    if not files:
        lcd16x2.lcd_print("No .bins found", "Enroll first")
        return False

    # 1) Close the Adafruit serial so we can open the port with PyFingerprint
    try:
        uart.close()
    except Exception:
        pass

    pf = None
    best_name, best_score = None, -1
    try:
        # 2) Open the sensor with PyFingerprint on the same UART
        pf = PyFingerprint('/dev/serial0', 57600, 0xFFFFFFFF, 0x00000000)
        if pf.verifyPassword() is False:
            print("Sensor password verify failed")
            return False

        # 3) Capture live image and convert to CharBuffer1
        lcd16x2.lcd_print("Waiting for", " image...")
        while True:
            if pf.readImage():
                lcd16x2.lcd_print("got it", "")
                break
            print(".", end="", flush=True)
            time.sleep(0.05)

        pf.convertImage(0x01)

        # 4) Compare against each saved template (upload into CharBuffer2)
        for fname in files:
            fpath = os.path.join(FP_DIR, fname)
            try:
                with open(fpath, "rb") as fh:
                    tmpl_bytes = fh.read()
                # PyFingerprint expects a list[int]
                pf.uploadCharacteristics(0x02, list(tmpl_bytes))
                score = pf.compareCharacteristics()
                if score > best_score:
                    best_score = score
                    best_name = os.path.splitext(fname)[0]
            except Exception as e:
                print(f"\nSkip {fname}: {e}")
                continue

        # ----- END LOGIC: decide after checking ALL files -----
        if best_name is None or best_score < THRESHOLD:
            lcd16x2.lcd_print("No match found.", "Access denied.")
            return False

        lcd16x2.lcd_print(f'"{best_name}" found', f'confidence: "{best_score}"')
        lcd16x2.lcd_print("Unlocking...", "")
        steppingmotor.rotate_unlock()

        # Optional: compatibility fields for your main print
        try:
            finger.finger_id = -1
            finger.confidence = best_score
        except Exception:
            pass
        return True

    except Exception as e:
        print("Error in folder-based matching:", e)
        return False

    finally:
        # 5) Re-open Adafruit UART so the rest of your program keeps working
        try:
            if not uart.is_open:
                uart.open()
        except Exception:
            pass
        try:
            finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        except Exception:
            pass



def enroll_finger():
    """Enroll with a NAME and save the template to ./fingerprints/<name>.bin (no sensor flash)."""
    # Ask for a name (Linux-safe filename)
    raw = input("Enter a name for this fingerprint: ").strip()
    if not raw:
        lcd16x2.lcd_print("Name cannot", " be empty.")
        return False
    # Sanitize to a safe filename (letters, numbers, _ - . only)
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)
    path_tmp = os.path.join(FP_DIR, f".{name}.bin.tmp")
    path_final = os.path.join(FP_DIR, f"{name}.bin")

    # ---- First image ----
    lcd16x2.lcd_print("Place finger", " on sensor...")
    while True:
        i = finger.get_image()
        if i == adafruit_fingerprint.OK:
            lcd16x2.lcd_print(" Image taken", "")
            break
        if i == adafruit_fingerprint.NOFINGER:
            print(".", end="", flush=True)
            time.sleep(0.05)
            continue
        if i == adafruit_fingerprint.IMAGEFAIL:
            lcd16x2.lcd_print("\nImaging error", "")
            return False
        print("\nOther error")
        return False

    lcd16x2.lcd_print("Templating", "first image...")
    i = finger.image_2_tz(1)
    if i != adafruit_fingerprint.OK:
        if i == adafruit_fingerprint.IMAGEMESS:
            print("Image too messy")
        elif i == adafruit_fingerprint.FEATUREFAIL:
            print("Could not identify features")
        elif i == adafruit_fingerprint.INVALIDIMAGE:
            print("Image invalid")
        else:
            print("Other error")
        return False
    lcd16x2.lcd_print("OK", "Remove finger")
    time.sleep(0.8)
    # Wait until finger is lifted
    while finger.get_image() != adafruit_fingerprint.NOFINGER:
        time.sleep(0.05)

    # ---- Second image ----
    lcd16x2.lcd_print("Place same", " finger again...")
    while True:
        i = finger.get_image()
        if i == adafruit_fingerprint.OK:
            lcd16x2.lcd_print("Image taken", "")
            break
        if i == adafruit_fingerprint.NOFINGER:
            print(".", end="", flush=True)
            time.sleep(0.05)
            continue
        if i == adafruit_fingerprint.IMAGEFAIL:
            print("\nImaging error")
            return False
        print("\nOther error")
        return False

    lcd16x2.lcd_print("Templating", " second image...")
    i = finger.image_2_tz(2)
    if i != adafruit_fingerprint.OK:
        if i == adafruit_fingerprint.IMAGEMESS:
            print("Image too messy")
        elif i == adafruit_fingerprint.FEATUREFAIL:
            print("Could not identify features")
        elif i == adafruit_fingerprint.INVALIDIMAGE:
            print("Image invalid")
        else:
            print("Other error")
        return False
    print("OK")

    # ---- Create model in sensor RAM (do NOT store to flash) ----
    lcd16x2.lcd_print("Creating ", "model")
    i = finger.create_model()
    if i != adafruit_fingerprint.OK:
        if i == adafruit_fingerprint.ENROLLMISMATCH:
           lcd16x2.lcd_print("Prints did ", "not match")
        else:
            print("Other error")
        return False
    print("Created")

    # ---- Download characteristics and save atomically to disk ----
    try:
        # Pull template bytes from CharBuffer1
        tmpl_bytes = bytes(finger.get_fpdata(sensorbuffer="char", slot=1))
        # Atomic write: write to temp, then rename
        with open(path_tmp, "wb") as f:
            f.write(tmpl_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(path_tmp, path_final)
        print(f'Stored template as "{path_final}"')
        return True
    except Exception as e:
        # Clean up temp file if something went wrong
        try:
            if os.path.exists(path_tmp):
                os.remove(path_tmp)
        except Exception:
            pass
        print("Failed to save template:", e)
        return False

def delete_model_updated():
    """
    Delete a fingerprint template by NAME from ./fingerprints and
    also remove any saved snapshot images (<name>_*.pgm).
    Returns adafruit_fingerprint.OK on success.
    """

    raw = input("Enter the name to delete: ").strip()
    if not raw:
        lcd16x2.lcd_print("Name cannot be empty.", "")
        return adafruit_fingerprint.BADLOCATION

    # Linux-safe filename
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)
    path_bin = os.path.join(FP_DIR, f"{name}.bin")

    if not os.path.exists(path_bin):
        lcd16x2.lcd_print(f'"{name}" not found', " in fingerprints")
        return adafruit_fingerprint.BADLOCATION

    try:
        # Remove the template file
        os.remove(path_bin)

        # Remove any associated PGM snapshots: "<name>_*.pgm"
        pgm_pattern = os.path.join(FP_DIR, f"{name}_*.pgm")
        removed_pgm = False
        for pgm in glob.glob(pgm_pattern):
            try:
                os.remove(pgm)
                removed_pgm = True
            except Exception:
                # Ignore failures deleting individual snapshots
                pass

        if removed_pgm:
            print(f'Deleted "{name}" template and snapshots from fingerprints/')
        else:
            print(f'Deleted "{name}" template from fingerprints/')

        return adafruit_fingerprint.OK

    except Exception as e:
        print("Failed to delete:", e)
        return adafruit_fingerprint.FLASHERR


##################################################


while True:
    print("----------------")
    try:
        rt = finger.read_templates()
        if rt != adafruit_fingerprint.OK:
            print("Note: could not read sensor template table (using folder-based templates).")
    except Exception:
        print("Note: sensor template table not available (using folder-based templates).")
    print("Fingerprint templates:", getattr(finger, "templates", []))
    time.sleep(3)
    lcd16x2.lcd_print("e) enroll print", "f) find print")
    time.sleep(3)
    lcd16x2.lcd_print("d) delete print", "q) quit program")
    c = input("> ").strip().lower()

    if c == "e":
        enroll_finger()  # updated: no numeric slot
    if c == "f":
        if get_fingerprint():
            continue
        else:
            lcd16x2.lcd_print("Finger not found", "")
    if c == "d":
        lcd16x2.lcd_print("Enter name", " to delete:")
        if delete_model_updated() == adafruit_fingerprint.OK:
            lcd16x2.lcd_print("Deleted!", "")
        else:
            lcd16x2.lcd_print("Failed to delete", "")
    if c == "q":
        lcd16x2.lcd_print("Quit successful", "")
        break

