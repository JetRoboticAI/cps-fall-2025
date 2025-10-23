# steppingmotor.py
# 28BYJ-48 + ULN2003 stepper, Pi 5 compatible (gpiozero + lgpio)
# Rotate 180° CW, wait, then 180° CCW when called.

import time
from gpiozero import DigitalOutputDevice

# BCM pins -> IN1..IN4 on ULN2003 (adjust if your wiring differs)
MOTOR_PINS = [18, 23, 24, 25]

# Single-coil full-step sequence (ABCD) matching your C example
CCW_SEQ = [0x01, 0x02, 0x04, 0x08]
CW_SEQ  = [0x08, 0x04, 0x02, 0x01]

# With this 4-step sequence the 28BYJ-48 has ≈512 periods per 360° → 180° = 256
CYCLES_PER_REV = 512
CYCLES_180 = CYCLES_PER_REV // 2  # 256

# Create output devices lazily so import has no side-effects
_devices = None

def _setup():
    global _devices
    if _devices is None:
        _devices = [DigitalOutputDevice(p, active_high=True, initial_value=False)
                    for p in MOTOR_PINS]

def _cleanup():
    global _devices
    if _devices:
        for d in _devices:
            try:
                d.off()
                d.close()
            except Exception:
                pass
        _devices = None

def _write_step(mask: int):
    for i, dev in enumerate(_devices):
        dev.value = 1 if (mask & (1 << i)) else 0

def move_one_period(direction: int, delay_ms: int):
    """
    One 4-phase period.
    direction: 1 = CW, 0 = CCW   (swap if your motor turns opposite)
    delay_ms: per-step delay; 3–6ms is typical
    """
    seq = CW_SEQ if direction == 1 else CCW_SEQ
    d = max(3, int(delay_ms)) / 1000.0
    for j in range(4):
        _write_step(seq[j])
        time.sleep(d)

def move_steps(direction: int, delay_ms: int, steps: int):
    for _ in range(steps):
        move_one_period(direction, delay_ms)
    # de-energize coils between motions
    _write_step(0)

def rotate_unlock(delay_ms: int = 3, open_pause_s: int = 10):
    """
    180° clockwise, wait, then 180° counter-clockwise.
    """
    _setup()
    try:
        move_steps(direction=1, delay_ms=delay_ms, steps=CYCLES_180)
        time.sleep(open_pause_s)
        move_steps(direction=0, delay_ms=delay_ms, steps=CYCLES_180)
        _write_step(0)
    finally:
        _cleanup()

if __name__ == "__main__":
    print("Test: 180° CW, wait 10s, 180° CCW")
    rotate_unlock()
