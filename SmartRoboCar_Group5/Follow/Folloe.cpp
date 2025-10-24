/*
 * Ultrasonic Follow Robot
 * Description: Implements object following using HC-SR04 ultrasonic sensor
 */

#include <Arduino.h>

// Motor driver class
class MotorDriver {
public:
  // Initialize motor pins
  void init() {
    pinMode(PWMA, OUTPUT);
    pinMode(PWMB, OUTPUT);
    pinMode(AIN1, OUTPUT);
    pinMode(BIN1, OUTPUT);
    pinMode(STBY, OUTPUT);
    digitalWrite(STBY, LOW); // Disable motors initially
  }

  // Control motor movement
  // direction: true=forward, false=backward; speed: 0-255
  void move(bool direction, uint8_t speed) {
    digitalWrite(STBY, HIGH); // Enable motors
    
    if (direction) { // Forward
      digitalWrite(AIN1, HIGH);
      digitalWrite(BIN1, HIGH);
    } else { // Backward
      digitalWrite(AIN1, LOW);
      digitalWrite(BIN1, LOW);
    }
    
    analogWrite(PWMA, speed);
    analogWrite(PWMB, speed);
  }

  // Stop all motors
  void stop() {
    digitalWrite(STBY, LOW);
    analogWrite(PWMA, 0);
    analogWrite(PWMB, 0);
  }

private:
  // Motor pin definitions
  const int PWMA = 5;
  const int PWMB = 6;
  const int AIN1 = 7;
  const int BIN1 = 8;
  const int STBY = 3;
};

// Ultrasonic sensor class
class UltrasonicSensor {
public:
  // Initialize sensor pins
  void init() {
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
  }

  // Get distance in cm (returns 0 if out of range)
  uint16_t getDistance() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    // Calculate distance (343m/s = 0.0343cm/µs, round trip / 2)
    unsigned long duration = pulseIn(ECHO_PIN, HIGH, MAX_DURATION);
    return duration > 0 ? duration / 58 : 0; // 58µs/cm
  }

private:
  // Ultrasonic pin definitions
  const int TRIG_PIN = 13;
  const int ECHO_PIN = 12;
  const unsigned long MAX_DURATION = 40000; // ~200cm max
};

// Follow control class
class FollowController {
public:
  FollowController(MotorDriver& motor, UltrasonicSensor& sonar) 
    : motor(motor), sonar(sonar) {}

  // Set follow parameters
  void setParameters(uint16_t targetDist, uint16_t tolerance, uint8_t speed) {
    this->targetDist = targetDist;
    this->tolerance = tolerance;
    this->speed = speed;
  }

  // Main follow logic
  void update() {
    uint16_t distance = sonar.getDistance();
    
    // Check if distance is valid (not 0)
    if (distance == 0) {
      motor.stop();
      return;
    }

    // Decision logic based on distance
    if (distance > targetDist + tolerance) {
      motor.move(true, speed); // Too far - move forward
    } else if (distance < targetDist - tolerance) {
      motor.move(false, speed/2); // Too close - move back slowly
    } else {
      motor.stop(); // In range - stop
    }
  }

private:
  MotorDriver& motor;
  UltrasonicSensor& sonar;
  uint16_t targetDist = 30;  // Default target distance: 30cm
  uint16_t tolerance = 5;    // Default tolerance: ±5cm
  uint8_t speed = 120;       // Default motor speed
};

// Create objects
MotorDriver motor;
UltrasonicSensor sonar;
FollowController controller(motor, sonar);

void setup() {
  Serial.begin(9600);
  motor.init();
  sonar.init();
  
  // You can adjust parameters here (target distance, tolerance, speed)
  controller.setParameters(30, 5, 120); 
  Serial.println("Follow system initialized");
}

void loop() {
  controller.update();
  delay(100); // Update every 100ms
}