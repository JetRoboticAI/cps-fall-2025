# SafeAir
## 💡 Inspiration

We were inspired to develop **SafeAir** by the growing need for smarter and safer living environments.  
Invisible and odorless gases—such as carbon monoxide or methane—can cause severe health risks and even fatal accidents if not detected in time. However, many existing gas detectors are **single-purpose**, **expensive**, or **lack smart connectivity**, which limits their practicality in modern homes and workplaces.

Recognizing this gap, we set out to build an **affordable**, **connected**, and **intelligent** IoT-based safety system that not only detects harmful gases but also provides **real-time feedback**, **data visualization**, and **remote control** capabilities.

---

## 🌍 System Overview

**SafeAir** is an IoT-based environmental monitoring system built on **Raspberry Pi**, designed to keep indoor environments safe and connected.  
It integrates multiple digital sensors that monitor environmental conditions such as **motion**, **temperature**, **humidity**, and **gas concentration**, updating the readings continuously to a web-based dashboard.

By combining real-time data, visual alerts, and user interaction, SafeAir not only reacts to hazards but also empowers users to understand and prevent potential dangers before they escalate.

---

## 🔧 Hardware Components & System Workflow

### 🧩 Hardware Materials

The **SafeAir** system is built using the following hardware components:

| Component | Description | Function |
|------------|-------------|-----------|
| **Raspberry Pi 4B** | Central processing unit | Reads digital sensor inputs, runs the main logic, hosts the Flask web app |
| **Gas Sensor (MQ-2)** | Digital gas sensor | Detects harmful or flammable gases |
| **Temperature & Humidity Sensor (DHT11)** | Digital environmental sensor | Measures temperature (°C) and humidity (%) |
| **PIR Motion Sensor (HC-SR501)** | Digital motion sensor | Detects human presence or movement |
| **Active / Passive Buzzer** | Output actuator | Provides audible alerts when gas is detected |

All sensors provide **digital outputs**, making it simple and efficient for the Raspberry Pi to read their signals directly.

---

### ⚙️ Features & Workflow

The overall system workflow is illustrated below:
<img width="818" height="374" alt="Screenshot 2025-10-17 at 00 15 26" src="https://github.com/user-attachments/assets/7d01f484-f743-462f-83f6-a7394ada30e4" />


---

### 🧠 How It Works

1. **Sensors → Raspberry Pi**  
   - All sensors send **digital output signals** to the Raspberry Pi’s GPIO pins.  
   - The main Python program (`main.py`) continuously reads these signals.  

2. **Data Storage**  
   - The system writes all sensor data (motion, temperature, humidity, and gas state) into a JSON file (`data/data.json`), serving as real-time storage.  

3. **Web Application**  
   - Using **Flask**, the Raspberry Pi hosts a local web server that provides a user interface with three key features:  
     - 🧾 **View Data** – visualize real-time sensor readings in the browser  
     - 🔔 **Pop-out Notifications** – receive on-screen alerts when harmful gas is detected  
     - 🚨 **Control the Buzzer** – mute or stop the buzzer remotely from the webpage  

4. **Buzzer Control Logic**  
   - When the **MQ-2** sensor detects harmful gas, the Raspberry Pi activates the buzzer automatically.  
   - If **human motion** is also detected by the **PIR sensor**, a more urgent and distinct tune is played.  

---

> The Raspberry Pi acts as the central controller that collects sensor data, updates the JSON storage, runs the Flask web server, and manages the buzzer’s alert logic—all working together.


---

## 📁 Project File Structure

Below is the overall directory layout of the **SafeAir** project:

```bash
SafeAir/
│
├── data/                        # Stores generated data files
│   ├── data.json                # Main file continuously updated with live sensor readings
│   └── mute.json                # Stores the buzzer snooze/mute state (true/false)
│
├── venv/                        # Python virtual environment (optional)
│   └── ...                      # Created via `python -m venv venv`
│
├── web/                         # Flask-based web server
│   │
│   ├── static/                  # Frontend static resources
│   │   ├── css/                 # CSS stylesheets
│   │   │   ├── notify.css       # Styles for the alert modal
│   │   │   ├── style.css        # Main homepage styling
│   │   │   └── view.css         # Data view page styling
│   │   │
│   │   └── js/                  # JavaScript logic files
│   │       ├── main.js          # Homepage logic (polling, mute button, popup control)
│   │       └── view.js          # Logic for the data visualization page
│   │
│   ├── templates/               # Flask HTML templates
│   │   ├── main.html            # Homepage (robot face + mute button + alert modal)
│   │   └── view.html            # Data view page (displaying sensor data)
│   │
│   └── app.py                   # Flask backend (routes, APIs, and JSON file access)
│
├── config.yaml                  # Global configuration (sensor pin mapping, system interval, file paths)
│
└── main.py                      # Raspberry Pi main logic (sensor reading, buzzer control, JSON writing)
```

> 🧩 *This structure separates hardware logic (main.py) from the web interface (Flask app), so it is easier to maintain.*
## 🚀 How to Run

Follow these quick steps to get **SafeAir** running on your Raspberry Pi:

1. **Activate your Python virtual environment** (or create one if you don’t have it yet), then make sure it’s active.
2. **Install project dependencies** required by both the hardware loop (`main.py`) and the web app (`web/app.py`): Flask, Adafruit DHT library, PyYAML, and RPi.GPIO.
3. **Run the main program** (`main.py`) to verify everything works — you should see sensor values printing (temperature, humidity, gas state, motion) and the buzzer responding to gas detection.
4. **Start the web server** by going into the `web` folder and running the Flask app (`app.py`).
5. **Open the dashboard** in a browser at `http://localhost:1500` (example)
   You can now view live data, receive alerts, and mute the buzzer from the web interface.

> Tip: Keep both processes running — one terminal for `main.py` (sensor loop), and another for the Flask server — to see live updates while using the dashboard.


