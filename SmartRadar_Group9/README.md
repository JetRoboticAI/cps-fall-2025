# Raspberry Pi-Based Smart Radar System and Cloud

This project implements a **radar-style distance and motion monitoring system** on a **Raspberry Pi**, integrating multiple sensors (ultrasonic, IR, servo, RGB LED, and buzzer) with the **Arduino IoT Cloud** for real-time visualization and control.

---

## Features

- **IR sensor** detects nearby objects and triggers ultrasonic distance measurement.  
- **Ultrasonic sensor (HC-SR04)** measures the distance to the nearest object.  
- **Servo motor** sweeps the ultrasonic sensor in a radar-like motion.  
- **RGB LED and buzzer** provide visual and audible alerts.  
- **Arduino IoT Cloud integration** sends live distance data and LED status to the cloud.  
- **Automatic recovery logic:** system resumes scanning once the area is clear beyond the set threshold.

---

## Hardware Requirements

| Component | Description |
|------------|--------------|
| Raspberry Pi 5 (or 4) | Main controller |
| HC-SR04 Ultrasonic Sensor | Distance measurement |
| IR Sensor Module | Motion/obstacle trigger |
| MG90S / SG90 Servo Motor | Rotating scan |
| RGB LED | Visual alert |
| Active Buzzer | Audible alert |
| Breadboard & Jumper Wires | Connections |

---

## Wiring Diagram (GPIO Pin Mapping)

| Component | Pin | GPIO | Notes |
|------------|-----|------|-------|
| IR Sensor | D0 | GPIO 17 | Object detection |
| Ultrasonic Trigger | TRIG | GPIO 23 | Output |
| Ultrasonic Echo | ECHO | GPIO 24 | Input (use 5V→3.3V level shifter) |
| RGB LED | R/G/B | GPIO 5 / 6 / 13 | Output |
| Buzzer | – | GPIO 22 | Active-low output |
| Servo | PWM | GPIO 12 | Hardware PWM supported |

---

## Software Overview

### Main Components
- **`project_ardiCloud.py`**  
  Core logic handling sensor input, servo sweep, alerts, and cloud synchronization.

- **`secrets.py`**  
  Contains Arduino IoT Cloud credentials (`DEVICE_ID`, `SECRET_KEY`).  
  **Do not share this file publicly.**

---

## Cloud Integration

This project uses the [`arduino_iot_cloud`](https://github.com/arduino/arduino-iot-cloud-py) Python library to connect the Raspberry Pi with **Arduino IoT Cloud**.

### Registered Cloud Variables
| Variable | Type | Description |
|-----------|------|-------------|
| `distance` | Float | Real-time distance (cm) |

These variables are visible and updatable in your Arduino Cloud dashboard.

---

## Installation

1. **Enable GPIO and pigpio on Raspberry Pi**
   ```bash
   sudo apt update
   sudo apt install python3-gpiozero python3-pigpio python3-rpi.gpio
   sudo systemctl enable pigpiod
   sudo systemctl start pigpiod
2. **Install dependencies**
    ```bash
    pip install arduino-iot-cloud
3. **Create the `secrets.py` file**
    ```bash
    DEVICE_ID  = "your-device-id"
    SECRET_KEY = "your-secret-key"
4. **Run the system**
    ```bash
    python3 project_ardiCloud.py
## Example Output
    Radar: scanning. After IR triggers, the system latches until ultrasonic > 120 cm, then resumes.
    IR triggered → stop rotation, enter ultrasonic wait-for-clear...
    Distance: 45.25 cm
    Distance: 46.87 cm
    Cleared consecutively; resuming rotation and IR.
