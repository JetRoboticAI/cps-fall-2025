# **EchoGuard**

*A Sound-Triggered IoT Surveillance System on Raspberry Pi 4*

------

## 🧭 **Project Overview**

**EchoGuard** is a sound-activated IoT surveillance device built on **Raspberry Pi 4**.
 The system detects acoustic events using an **LM393 sound sensor**, triggers visual (LED) and audible (buzzer) alerts, rotates an **OV5647 camera** via an **SG90 servo**, captures images, and provides remote control through a **Flask + HTML web dashboard**.
 An email notification alerts the user to review captured photos.

------

## ⚙️ **System Architecture**

- **Trigger** → Sound detected by LM393 sensor (digital D0 output)
- **Processing Unit** → Raspberry Pi 4 running Flask server
- **Action** → Buzzer + LED + Camera (pan via servo) activated
- **Interface** → Web dashboard (manual reset, photo viewing)
- **Notification** → Optional email alert using SMTP

------

## 🧩 **Hardware Components**

| Module              | Model          | Power Domain  | GPIO / Connection | Description                    |
| ------------------- | -------------- | ------------- | ----------------- | ------------------------------ |
| Raspberry Pi 4B     | —              | 3.3 V / 5 V   | —                 | Main controller, Flask backend |
| Sound Sensor        | LM393          | 5 V           | **GPIO 25** (D0)  | Detects sound trigger          |
| LED Indicator       | —              | 3.3 V         | **GPIO 22**       | Visual alarm (active-high)     |
| Active Buzzer       | MH-FMD         | 5 V           | **GPIO 23**       | Audible alarm (active-high)    |
| Servo Motor (Pan)   | SG90           | External 5 V  | **GPIO 12 (PWM)** | Rotates camera horizontally    |
| Camera Module       | OV5647         | CSI Interface | —                 | Captures still images          |
| External 5 V Source | USB Power Bank | 5 V           | —                 | Isolated servo + buzzer power  |
| Breadboard (x2)     | —              | 3.3 V + 5 V   | Shared GND        | Logic / Power separation       |

------

## ⚡ **Power Supply Layout**

| Domain             | Source                       | Components Powered               | Notes                                  |
| ------------------ | ---------------------------- | -------------------------------- | -------------------------------------- |
| **3.3 V (Logic)**  | Pi 3.3 V pin (1)             | LM393 signal, LED                | Used for GPIO logic and sensing        |
| **5 V (Pi)**       | Pi 5 V pin (2 or 4)          | Camera, light buzzer (if needed) | Limited current (~1 A)                 |
| **5 V (External)** | USB power bank or adapter    | Servo motor, buzzer              | Shared GND with Pi, isolated +5 V rail |
| **GND (Common)**   | Any Pi GND pin (6, 9, 14...) | Shared ground rail               | Prevents floating logic levels         |

------

## 🧠 **Software Setup (Raspberry Pi OS 64-bit)**

### 1️⃣ Update packages and install dependencies:

```bash
sudo apt update && sudo apt install -y \
  python3 python3-pip python3-flask libcamera-apps
```

### 2️⃣ Install Python packages:

```bash
pip3 install flask-cors RPi.GPIO
```

### 3️⃣ Enable the camera (libcamera is default). Verify:

```bash
rpicam-still -n -o test.jpg
```

### 4️⃣ Clone or copy the backend and dashboard files:

```
smart_sound_backend.py
web.html
```

### 5️⃣ Configure email alert environment variables:

```bash
export EMAIL_FROM="your@gmail.com"
export EMAIL_PASS="your_app_password"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT=465
```

### 6️⃣ Run the server with GPIO privileges:

```bash
sudo -E python3 smart_sound_backend.py
```

### 7️⃣ Access the web dashboard:

- Open `web.html` in your browser.

- Set API base to:

  ```
  http://<pi_ip>:5000
  ```

- Click **Apply**, then **Reset / Capture / Stop** to test.

------

## 🧩 **Project Files**

| File                     | Description                                     |
| ------------------------ | ----------------------------------------------- |
| `smart_sound_backend.py` | Flask backend (GPIO control + REST API + email) |
| `web.html`               | Front-end dashboard for user interaction        |
| `panshoot.py`            | Servo camera test script                        |
| `flaskEm.py`             | Email alert integration test                    |
| `README.md`              | System setup and usage guide                    |

------

## 🧪 **Testing and Verification**

- Test LED and buzzer individually with:
   `pinctrl set 22 op dh` (LED ON)
   `pinctrl set 23 op dh` (Buzzer ON)
- Verify sound trigger via console log:
   `Detected! level=1`
- Observe camera rotation and photo capture sequence.
- Use dashboard buttons to manually reset alerts.

------

## 📬 **Authors**

**Team 10 — EchoGuard Project**

- Jewel Chen – Hardware Integration, Flask Backend
- Dylan Wang – Web Dashboard, Email Module
- Hongzhen Tan – Servo Control and Camera Interface
- Yangfei Wang – System Testing and Documentation

------

