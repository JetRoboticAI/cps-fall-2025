#ifndef _CameraWebServer_AP_H
#define _CameraWebServer_AP_H

#include "esp_camera.h"
#include <WiFi.h>

class CameraWebServer_AP
{
public:
  // Initialize camera and start AP mode web server
  void CameraWebServer_AP_Init(void);
  
  String wifi_name;

private:
  const char *ssid = "Group5";       // WiFi name
  const char *password = "";         // No password
};

#endif