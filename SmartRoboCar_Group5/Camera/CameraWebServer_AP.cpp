#include "CameraWebServer_AP.h"
#include "camera_pins.h"
#include "esp_system.h"

// External function to start camera server (defined elsewhere)
void startCameraServer();

// Setup LED flash
void setupLedFlash(int pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void CameraWebServer_AP::CameraWebServer_AP_Init(void)
{
  Serial.setDebugOutput(true);
  
  // Camera configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  
  // Assign camera pins
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  
  // Camera settings
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;     // JPEG format for streaming
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_DRAM;   // No PSRAM, use internal DRAM
  config.frame_size = FRAMESIZE_SVGA;       // 800x600 resolution
  config.jpeg_quality = 12;                 // JPEG quality (0-63, lower is better)
  config.fb_count = 1;                      // Single frame buffer (no PSRAM)

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }

  // Get camera sensor
  sensor_t *s = esp_camera_sensor_get();
  
  // Set frame size to SVGA
  s->set_framesize(s, FRAMESIZE_SVGA);

  // Setup LED flash
  setupLedFlash(LED_GPIO_NUM);

  // Store WiFi name
  wifi_name = String(ssid);

  // Configure WiFi
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);

  // Start camera web server
  startCameraServer();

  // Print connection info
  Serial.println("============================");
  Serial.print("WiFi Name: ");
  Serial.println(ssid);
  Serial.print("Camera URL: http://");
  Serial.println(WiFi.softAPIP());
  Serial.println("============================");
}