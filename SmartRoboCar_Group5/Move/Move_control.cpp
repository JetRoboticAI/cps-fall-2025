#ifndef __Move_Control_
#define __Move_Control_

#include <Arduino.h>

// Motor driver class for controlling two motor groups (A and B)
class DeviceDriverSet_Motor {
public:
    // Initialize motor control pins (set as output)
    void init(void);
    
    // Control motor movement
    // Parameters:
    // - direction_A: Rotation direction of motor A (true for forward, false for backward, 3 for stop)
    // - speed_A: Speed of motor A (0-255, higher value means faster)
    // - direction_B: Rotation direction of motor B (same as direction_A)
    // - speed_B: Speed of motor B (same as speed_A)
    // - controlED: Enable motor operation (true to enable, false to disable)
    void control(boolean direction_A, uint8_t speed_A,
                 boolean direction_B, uint8_t speed_B,
                 boolean controlED);

private:
    // Motor control pin definitions
    #define PIN_MOTOR_PWMA 5    // PWM pin for motor A
    #define PIN_MOTOR_PWMB 6    // PWM pin for motor B
    #define PIN_MOTOR_AIN1 7    // Direction control pin for motor A
    #define PIN_MOTOR_BIN1 8    // Direction control pin for motor B
    #define PIN_MOTOR_STBY 3    // Standby pin (HIGH to enable motors, LOW to disable)

public:
    // Motor control constants
    #define SPEED_MAX 255       // Maximum PWM speed value
    #define DIR_FORWARD true    // Forward direction
    #define DIR_BACKWARD false  // Backward direction
    #define DIR_STOP 3          // Stop direction
    #define CONTROL_ENABLE true  // Enable motor control
    #define CONTROL_DISABLE false // Disable motor control
};

// Initialize motor pins as output
void DeviceDriverSet_Motor::init(void) {
    pinMode(PIN_MOTOR_PWMA, OUTPUT);
    pinMode(PIN_MOTOR_PWMB, OUTPUT);
    pinMode(PIN_MOTOR_AIN1, OUTPUT);
    pinMode(PIN_MOTOR_BIN1, OUTPUT);
    pinMode(PIN_MOTOR_STBY, OUTPUT);
}

// Implement motor control logic
void DeviceDriverSet_Motor::control(boolean direction_A, uint8_t speed_A,
                                    boolean direction_B, uint8_t speed_B,
                                    boolean controlED) {
    if (controlED == CONTROL_ENABLE) {
        digitalWrite(PIN_MOTOR_STBY, HIGH);  // Enable motor operation

        // Control motor A
        switch (direction_A) {
            case DIR_FORWARD:
                digitalWrite(PIN_MOTOR_AIN1, HIGH);
                analogWrite(PIN_MOTOR_PWMA, speed_A);
                break;
            case DIR_BACKWARD:
                digitalWrite(PIN_MOTOR_AIN1, LOW);
                analogWrite(PIN_MOTOR_PWMA, speed_A);
                break;
            case DIR_STOP:
                analogWrite(PIN_MOTOR_PWMA, 0);
                digitalWrite(PIN_MOTOR_STBY, LOW);
                break;
            default:  // Invalid direction, stop motor
                analogWrite(PIN_MOTOR_PWMA, 0);
                digitalWrite(PIN_MOTOR_STBY, LOW);
                break;
        }

        // Control motor B
        switch (direction_B) {
            case DIR_FORWARD:
                digitalWrite(PIN_MOTOR_BIN1, HIGH);
                analogWrite(PIN_MOTOR_PWMB, speed_B);
                break;
            case DIR_BACKWARD:
                digitalWrite(PIN_MOTOR_BIN1, LOW);
                analogWrite(PIN_MOTOR_PWMB, speed_B);
                break;
            case DIR_STOP:
                analogWrite(PIN_MOTOR_PWMB, 0);
                digitalWrite(PIN_MOTOR_STBY, LOW);
                break;
            default:  // Invalid direction, stop motor
                analogWrite(PIN_MOTOR_PWMB, 0);
                digitalWrite(PIN_MOTOR_STBY, LOW);
                break;
        }
    } else {
        digitalWrite(PIN_MOTOR_STBY, LOW);  // Disable motors
        return;
    }
}

// Motion control enumeration for smart robot car
enum SmartRobotCarMotion {
    FORWARD,        // Move forward
    BACKWARD,       // Move backward
    LEFT,           // Turn left (in place)
    RIGHT,          // Turn right (in place)
    LEFT_FORWARD,   // Move forward while turning left
    LEFT_BACKWARD,  // Move backward while turning left
    RIGHT_FORWARD,  // Move forward while turning right
    RIGHT_BACKWARD, // Move backward while turning right
    STOP            // Stop all movement
};

// Application structure to store current motion state
struct RobotApplication {
    SmartRobotCarMotion currentMotion;
};

// Global motor instance and application state
DeviceDriverSet_Motor robotMotor;
RobotApplication robotApp;

// Control robot motion based on specified direction and speed
// Parameters:
// - direction: Target motion direction (from SmartRobotCarMotion enum)
// - speed: Base speed for motors (0-SPEED_MAX)
static void controlRobotMotion(SmartRobotCarMotion direction, uint8_t speed) {
    switch (direction) {
        case FORWARD:
            robotMotor.control(DIR_FORWARD, speed, DIR_FORWARD, speed, CONTROL_ENABLE);
            break;
        case BACKWARD:
            robotMotor.control(DIR_BACKWARD, speed, DIR_BACKWARD, speed, CONTROL_ENABLE);
            break;
        case LEFT:
            robotMotor.control(DIR_FORWARD, speed, DIR_BACKWARD, speed, CONTROL_ENABLE);
            break;
        case RIGHT:
            robotMotor.control(DIR_BACKWARD, speed, DIR_FORWARD, speed, CONTROL_ENABLE);
            break;
        case LEFT_FORWARD:
            robotMotor.control(DIR_FORWARD, speed, DIR_FORWARD, speed/2, CONTROL_ENABLE);
            break;
        case LEFT_BACKWARD:
            robotMotor.control(DIR_BACKWARD, speed, DIR_BACKWARD, speed/2, CONTROL_ENABLE);
            break;
        case RIGHT_FORWARD:
            robotMotor.control(DIR_FORWARD, speed/2, DIR_FORWARD, speed, CONTROL_ENABLE);
            break;
        case RIGHT_BACKWARD:
            robotMotor.control(DIR_BACKWARD, speed/2, DIR_BACKWARD, speed, CONTROL_ENABLE);
            break;
        case STOP:
            robotMotor.control(DIR_STOP, 0, DIR_STOP, 0, CONTROL_ENABLE);
            break;
        default:
            break;  // Do nothing for invalid direction
    }
}

#endif  