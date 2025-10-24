#include "DeviceDriverSet_ULTRASONIC.h"

// Initialize sensor pins
void DeviceDriverSet_ULTRASONIC::DeviceDriverSet_ULTRASONIC_Init(void) {
  pinMode(ECHO_PIN, INPUT);   // Set echo pin as input to receive signals
  pinMode(TRIG_PIN, OUTPUT);  // Set trigger pin as output to send signals
}

// Get current distance and store in the provided pointer
void DeviceDriverSet_ULTRASONIC::DeviceDriverSet_ULTRASONIC_Get(uint16_t *ULTRASONIC_Get /*out*/) {
  unsigned int duration;
  
  // Send 10us trigger pulse to start measurement
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);       // Short low pulse to ensure clean trigger
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);      // Trigger pulse duration
  digitalWrite(TRIG_PIN, LOW);
  
  // Read echo pulse duration (in microseconds) and convert to cm
  // Formula: duration / 58 ≈ distance (since sound travels ~0.034cm/us, round trip doubles it)
  duration = pulseIn(ECHO_PIN, HIGH);
  *ULTRASONIC_Get = duration / 58;
}

// Test function: measure distance and print result to Serial monitor
void DeviceDriverSet_ULTRASONIC::DeviceDriverSet_ULTRASONIC_Test(void) {
  unsigned int distance;
  
  // Same trigger sequence as Get function
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Calculate distance
  distance = pulseIn(ECHO_PIN, HIGH) / 58;
  
  // Print measurement result
  Serial.print("ULTRASONIC=");
  Serial.print(distance);
  Serial.println("cm");
}