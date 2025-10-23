#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <PubSubClient.h>

// ---------- Wi-Fi ----------
const char* WIFI_SSID = "";//Removed for privacy
const char* WIFI_PASS = "";//Removed for privacy

// ---------- Ubidots ----------
#define TOKEN ""//Removed for privacy
#define DEVICE_LABEL "esp32_weather"

const char* MQTT_BROKER = "industrial.api.ubidots.com";  // use stem.ubidots.com if on free STEM account
const int MQTT_PORT = 1883;

// ---------- Sensors ----------
#define SDA_PIN 21
#define SCL_PIN 22
#define UV_PIN 33
#define MQ135_PIN 35

Adafruit_BME280 bme;
WiFiClient ubidotsWiFiClient;
PubSubClient client(ubidotsWiFiClient);

// ---------- API ----------
const char* apiURL = "http://api.open-meteo.com/v1/forecast?latitude=43.25&longitude=-79.87&current_weather=true";

// ---------- Function Prototypes ----------
void setupWiFi();
void reconnectMQTT();
void publishToUbidots(float temp_local, float hum_local, float pres_local,
                       float uv, float mq,
                       float temp_api, int weathercode, const char* weatherDescription);
String getWeatherDescription(int code);

// ---------- Setup ----------
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========== ESP32 Weather Node ==========");
  setupWiFi();

  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setKeepAlive(60);

  // Initialize BME280
  Serial.println("Initializing BME280...");
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!bme.begin(0x76)) {
    Serial.println("❌ Could not find BME280 sensor! Check wiring!");
    while (1);
  }
  Serial.println("✅ BME280 Initialized Successfully!");
  Serial.println("========================================\n");
}

// ---------- Loop ----------
void loop() {
  if (!client.connected()) reconnectMQTT();
  client.loop();

  // --- Read local sensors ---
  float temperature_local = bme.readTemperature();
  float humidity_local = bme.readHumidity();
  float pressure_local = bme.readPressure() / 100.0F;

  int uvRaw = analogRead(UV_PIN);
  float uvVoltage = (uvRaw / 4095.0) * 3.3;

  int mqRaw = analogRead(MQ135_PIN);
  float mqVoltage = (mqRaw / 4095.0) * 3.3;

  Serial.println("\n===== LOCAL SENSOR DATA =====");
  Serial.printf("Temperature: %.2f °C\n", temperature_local);
  Serial.printf("Humidity: %.2f %%\n", humidity_local);
  Serial.printf("Pressure: %.2f hPa\n", pressure_local);
  Serial.printf("UV Voltage: %.3f V\n", uvVoltage);
  Serial.printf("MQ135 Voltage: %.3f V\n", mqVoltage);
  Serial.println("=============================");

  // --- Fetch API data ---
  float temperature_api = 0;
  int weathercode_api = 0;
  String weatherDescription = "Unknown";

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(apiURL);
    int httpCode = http.GET();
    if (httpCode == 200) {
      String payload = http.getString();
      StaticJsonDocument<1024> doc;
      DeserializationError error = deserializeJson(doc, payload);
      if (!error) {
        temperature_api = doc["current_weather"]["temperature"];
        weathercode_api = doc["current_weather"]["weathercode"];
        weatherDescription = getWeatherDescription(weathercode_api);

        Serial.println("\n===== API WEATHER DATA =====");
        Serial.printf("Temperature: %.2f °C\n", temperature_api);
        Serial.printf("Weather Code: %d (%s)\n", weathercode_api, weatherDescription.c_str());
        Serial.println("=============================");
      } else {
        Serial.print("JSON Parse Error: "); Serial.println(error.c_str());
      }
    } else {
      Serial.print("HTTP Error: "); Serial.println(httpCode);
    }
    http.end();
  }

  // --- Publish to Ubidots ---
  publishToUbidots(temperature_local, humidity_local, pressure_local,
                   uvVoltage, mqVoltage,
                   temperature_api, weathercode_api, weatherDescription.c_str());

  delay(5000); // Update every 5 seconds
}

// ---------- Wi-Fi ----------
void setupWiFi() {
  Serial.print("Connecting to WiFi: "); Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: "); Serial.println(WiFi.localIP());
}

// ---------- MQTT ----------
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to Ubidots MQTT...");
    String clientId = "ESP32_WeatherNode_" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), TOKEN, "")) {
      Serial.println("Connected!");
    } else {
      Serial.print("Failed, rc="); Serial.print(client.state());
      Serial.println(" retrying in 3s...");
      delay(3000);
    }
  }
}

// ---------- Publish ----------
void publishToUbidots(float temp_local, float hum_local, float pres_local,
                       float uv, float mq,
                       float temp_api, int weathercode, const char* weatherDescription) {
  if (!client.connected()) {
    reconnectMQTT();
  }

  // Limit float precision manually
  char payload[512];
  snprintf(payload, sizeof(payload),
           "{\"temperature_local\": {\"value\": %.2f}, "
           "\"humidity_local\": {\"value\": %.2f}, "
           "\"pressure_local\": {\"value\": %.2f}, "
           "\"uv_voltage\": {\"value\": %.3f}, "
           "\"mq_voltage\": {\"value\": %.3f}, "
           "\"temperature_api\": {\"value\": %.2f}, "
           "\"weathercode_api\": {\"value\": %d}, "
           "\"weather_description\": {\"value\": \"%s\"}}",
           temp_local, hum_local, pres_local,
           uv, mq,
           temp_api, weathercode, weatherDescription);

  char topic[150];
  snprintf(topic, sizeof(topic), "/v1.6/devices/%s", DEVICE_LABEL);

  Serial.println("\nPayload:");
  Serial.println(payload);

  client.setBufferSize(1024);  // Ensure buffer size large enough
  boolean success = client.publish(topic, payload);

  if (success) {
    Serial.println("📡 Data sent to Ubidots successfully!");
  } else {
    Serial.println("MQTT Publish failed! Checking connection...");
    if (!client.connected()) reconnectMQTT();
  }
}


// ---------- Map weather code to description ----------
String getWeatherDescription(int code) {
  switch(code) {
    case 0: return "Clear sky";
    case 1: return "Mainly clear";
    case 2: return "Partly cloudy";
    case 3: return "Overcast";
    case 45: case 48: return "Fog";
    case 51: case 53: case 55: return "Drizzle";
    case 56: case 57: return "Freezing drizzle";
    case 61: case 63: case 65: return "Rain";
    case 66: case 67: return "Freezing rain";
    case 71: case 73: case 75: return "Snowfall";
    case 77: return "Snow grains";
    case 80: case 81: case 82: return "Rain showers";
    case 85: case 86: return "Snow showers";
    case 95: return "Thunderstorm";
    case 96: case 99: return "Thunderstorm with hail";
    default: return "Unknown";
  }
}
