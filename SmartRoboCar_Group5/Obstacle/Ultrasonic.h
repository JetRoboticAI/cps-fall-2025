#ifndef _DeviceDriverSet_ULTRASONIC_H_
#define _DeviceDriverSet_ULTRASONIC_H_

#include <Arduino.h>

// Class for controlling ultrasonic sensor
class DeviceDriverSet_ULTRASONIC {
public:
  // Initialize ultrasonic sensor: set trigger as output, echo as input
  void DeviceDriverSet_ULTRASONIC_Init(void);
  
  // Test sensor function: measure distance and print via Serial
  void DeviceDriverSet_ULTRASONIC_Test(void);
  
  // Get measured distance and store in the output parameter
  // Parameter: ULTRASONIC_Get (out) - pointer to store distance in cm
  void DeviceDriverSet_ULTRASONIC_Get(uint16_t *ULTRASONIC_Get /*out*/);

private:
  // Pin definitions and maximum measurable distance
  #define TRIG_PIN 13        // Trigger pin of the ultrasonic sensor
  #define ECHO_PIN 12        // Echo pin of the ultrasonic sensor
  #define MAX_DISTANCE 200   // Maximum measurable distance in centimeters
};

#endif