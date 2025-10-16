# main.py — SafeAir v1 Central Logic (PIR + DHT11 + MQ-2 + Buzzer)
import json, time, os, signal, yaml, sys
from datetime import datetime
import RPi.GPIO as GPIO
import board, adafruit_dht

CONFIG_PATH = "config.yaml"

# ===== Global options =====
USE_ACTIVE_BUZZER = True
BUZZER_ACTIVE_HIGH = False

# ---------- 工具函数 ----------
def iso_utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def atomic_write_json(path, obj):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def safe_round(v, nd=1, default=None):
    if v is None:
        return default
    try:
        return round(float(v), nd)
    except Exception:
        return default

def safe_int(v, default=None):
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default

# ---------- 读取/清除 snooze 标志 ----------
def read_snooze(path) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return bool(json.load(f).get("snooze", False))
    except Exception:
        return False

def clear_snooze(path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"snooze": False}, f)
    except Exception:
        pass

# ---------- Buzzer 类 ----------
class Buzzer:
    def __init__(self, pin: int, active_high=True):
        self.pin = pin
        self.active_high = active_high
        self.pwm = None
        GPIO.setup(self.pin, GPIO.OUT)
        self.off()

    def _start_pwm(self, freq):
        if self.pwm is None:
            self.pwm = GPIO.PWM(self.pin, max(1, int(freq)))
            self.pwm.start(50)
        else:
            self.pwm.ChangeFrequency(max(1, int(freq)))
            self.pwm.ChangeDutyCycle(50)

    def _passive_beep(self, freq_hz, ms):
        if freq_hz <= 0:
            self.off()
            time.sleep(ms / 1000.0)
            return
        self._start_pwm(freq_hz)
        time.sleep(ms / 1000.0)
        self.off()

    def play_tune(self, notes):
        if USE_ACTIVE_BUZZER:
            for _freq, dur in notes:
                self.on()
                time.sleep(dur / 1000.0)
                self.off()
                time.sleep(0.05)
            self.off()
            return
        for freq, dur in notes:
            self._passive_beep(freq, dur)
        self.off()

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH if self.active_high else GPIO.LOW)

    def off(self):
        if self.pwm:
            self.pwm.stop()
            self.pwm = None
        GPIO.output(self.pin, GPIO.LOW if self.active_high else GPIO.HIGH)

# ---------- 旋律 ----------
TUNE_GAS = [
    (784, 350), (0, 150),
    (880, 350), (0, 150),
    (988, 350), (0, 250),
    (880, 350)
]

TUNE_URGENT = [
    (1568, 100), (0, 30),
    (1760, 100), (0, 30),
    (1865, 100), (0, 30),
    (1760, 100), (0, 30),
    (1568, 100), (0, 30),
    (1760, 250), (0, 100),
    (1865, 250)
]

# ---------- 主程序 ----------
def main():
    # 读取配置
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    pir_pin  = int(cfg["sensors"]["pir"]["pin"])
    dht_pin  = int(cfg["sensors"]["dht11"]["pin"])
    mq2_pin  = int(cfg["sensors"]["mq2"]["pin"])
    buz_pin  = int(cfg["actuators"]["buzzer"]["pin"])
    data_path = cfg["system"]["data_file"]
    interval  = float(cfg["system"]["write_interval_ms"]) / 1000.0

    # 让 mute.json 放在 data.json 同目录
    mute_path = os.path.join(os.path.dirname(data_path), "mute.json")

    # GPIO
    GPIO.setmode(GPIO.BCM)
    # 👉 和旧版一致：不强制上下拉，避免和模块板载电路冲突
    GPIO.setup(pir_pin, GPIO.IN)
    GPIO.setup(mq2_pin, GPIO.IN)

    buzzer = Buzzer(buz_pin, active_high=BUZZER_ACTIVE_HIGH)

    # DHT11：优先用正常模式，失败则回退 use_pulseio=False，并做预热
    try:
        dhtDevice = adafruit_dht.DHT11(getattr(board, f"D{dht_pin}"))
    except Exception:
        dhtDevice = adafruit_dht.DHT11(getattr(board, f"D{dht_pin}"), use_pulseio=False)
    time.sleep(2.0)  # 👉 预热

    # DHT 节流缓存（至少 2 秒读一次）
    last_dht_read = 0.0
    last_temp, last_hum = None, None

    def cleanup(*_):
        try: buzzer.off()
        except: pass
        try: GPIO.cleanup()
        except: pass
        try:
            if hasattr(dhtDevice, "exit"):
                dhtDevice.exit()
        except: pass
        sys.exit(0)

    signal.signal(signal.SIGINT,  cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("✅ SafeAir main loop started. (BCM numbering)")

    while True:
        # 原始读数
        raw_pir = int(GPIO.input(pir_pin))
        raw_mq2 = int(GPIO.input(mq2_pin))
        pir_motion = raw_pir
        mq2_state  = raw_mq2

        # ------- DHT11：≥2s 才读，一旦失败沿用上次 -------
        now = time.monotonic()
        temp, humidity = last_temp, last_hum
        if now - last_dht_read >= 2.0:
            try:
                _t = dhtDevice.temperature
                _h = dhtDevice.humidity
                if _t is not None and _h is not None:
                    temp, humidity = _t, _h
                    last_temp, last_hum = temp, humidity
            except Exception as e:
                # 常见校验错误，忽略即可
                # print("⚠️ DHT11 read failed:", e)
                pass
            finally:
                last_dht_read = now

        # ======== 核心：读取 snooze，并在 MQ-2==0 时自动清除 ========
        snoozed = read_snooze(mute_path)
        if mq2_state == 0 and snoozed:  # 👉 恢复旧版“0=有气体/报警后清除”
            clear_snooze(mute_path)
            snoozed = False

        # ======== 报警逻辑：恢复旧版极性 —— mq2==0 才报警 ========
        buzzer_on = False
        if mq2_state == 0 and not snoozed:
            buzzer_on = True
            if pir_motion == 1:
                buzzer.play_tune(TUNE_URGENT)
            else:
                buzzer.play_tune(TUNE_GAS)

            time.sleep(1.0)
        else:
            buzzer.off()

        # 写数据
        data = {
            "ts": iso_utc_now(),
            "sensors": {
                "pir": {"motion": int(pir_motion), "raw": raw_pir},
                "dht11": {
                    "temperature_c": safe_round(temp, 1, default=None),
                    "humidity_pct":  safe_int(humidity, default=None)
                },
                "mq2": {"state": int(mq2_state), "raw": raw_mq2}
            },
            "alarm": {
                "buzzer_on": bool(buzzer_on),
                "snoozed": bool(snoozed)
            }
        }
        atomic_write_json(data_path, data)
        # print(data)  # 需要在终端观察再打开

        time.sleep(max(0.2, interval))  # 👉 最小 0.2s，别太密

def cleanup_and_exit(buzzer, dhtDevice, code=0):
    try:
        if buzzer: buzzer.off()
    except: pass
    try:
        GPIO.cleanup()
    except: pass
    try:
        if dhtDevice and hasattr(dhtDevice, "exit"):
            dhtDevice.exit()
    except: pass
    sys.exit(code)

if __name__ == "__main__":
    main()
