#ifndef CAMERA_PINS_H
#define CAMERA_PINS_H

// Camera power and reset pins
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1

// Camera clock pin
#define XCLK_GPIO_NUM 15

// I2C pins for camera configuration
#define SIOD_GPIO_NUM 4
#define SIOC_GPIO_NUM 5

// Camera data pins (Y2-Y9)
#define Y2_GPIO_NUM 11
#define Y3_GPIO_NUM 9
#define Y4_GPIO_NUM 8
#define Y5_GPIO_NUM 10
#define Y6_GPIO_NUM 12
#define Y7_GPIO_NUM 18
#define Y8_GPIO_NUM 17
#define Y9_GPIO_NUM 16

// Camera sync pins
#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM 7
#define PCLK_GPIO_NUM 13

// LED flash pin
#define LED_GPIO_NUM 46

#endif