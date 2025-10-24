#ifndef IRremoteint_h
#define IRremoteint_h

#if defined(ARDUINO) && ARDUINO >= 100
#include <Arduino.h>
#else
#include <WProgram.h>
#endif

// Timer configuration for Arduino Uno (uses Timer2)
#define IR_USE_TIMER2
#define TIMER_PWM_PIN 3         // PWM output pin for IR LED

#ifdef F_CPU
#define SYSCLOCK F_CPU
#else
#define SYSCLOCK 16000000       // Default 16MHz clock
#endif

#define ERR 0
#define DECODED 1

// Bit manipulation macros
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

// NEC protocol timing constants (in microseconds)
#define NEC_HDR_MARK    9000    // Header mark
#define NEC_HDR_SPACE   4500    // Header space
#define NEC_BIT_MARK    560     // Bit mark
#define NEC_ONE_SPACE   1600    // Logic 1 space
#define NEC_ZERO_SPACE  560     // Logic 0 space
#define NEC_RPT_SPACE   2250    // Repeat code space

// Timing tolerance (25%)
#define TOLERANCE 25
#define LTOL (1.0 - TOLERANCE/100.) 
#define UTOL (1.0 + TOLERANCE/100.) 

// Gap between transmissions
#define _GAP 5000
#define GAP_TICKS (_GAP/USECPERTICK)

// Timing check macros
#define TICKS_LOW(us) (int)(((us)*LTOL/USECPERTICK))
#define TICKS_HIGH(us) (int)(((us)*UTOL/USECPERTICK + 1))

// Receiver state machine states
#define STATE_IDLE     2
#define STATE_MARK     3
#define STATE_SPACE    4
#define STATE_STOP     5

// IR parameters structure for interrupt handler
typedef struct {
  uint8_t recvpin;              // Input pin number
  uint8_t rcvstate;             // Current state
  uint8_t blinkflag;            // LED blink enable flag
  unsigned int timer;           // Timer counter (50us ticks)
  unsigned int rawbuf[RAWBUF];  // Raw timing data
  uint8_t rawlen;               // Number of entries in buffer
} irparams_t;

extern volatile irparams_t irparams;

// IR signal definitions
#define MARK  0                 // IR LED on
#define SPACE 1                 // IR LED off

#define TOPBIT 0x80000000       // Top bit mask
#define NEC_BITS 32             // NEC uses 32 bits

// Timer2 configuration macros for Arduino Uno
#define TIMER_RESET
#define TIMER_ENABLE_PWM     (TCCR2A |= _BV(COM2B1))
#define TIMER_DISABLE_PWM    (TCCR2A &= ~(_BV(COM2B1)))
#define TIMER_ENABLE_INTR    (TIMSK2 = _BV(OCIE2A))
#define TIMER_DISABLE_INTR   (TIMSK2 = 0)
#define TIMER_INTR_NAME      TIMER2_COMPA_vect

// Timer2 PWM configuration for carrier frequency
#define TIMER_CONFIG_KHZ(val) ({ \
  const uint8_t pwmval = SYSCLOCK / 2000 / (val); \
  TCCR2A = _BV(WGM20); \
  TCCR2B = _BV(WGM22) | _BV(CS20); \
  OCR2A = pwmval; \
  OCR2B = pwmval / 3; \
})

// Timer2 configuration for receiving
#define TIMER_COUNT_TOP (SYSCLOCK * USECPERTICK / 1000000)
#if (TIMER_COUNT_TOP < 256)
#define TIMER_CONFIG_NORMAL() ({ \
  TCCR2A = _BV(WGM21); \
  TCCR2B = _BV(CS20); \
  OCR2A = TIMER_COUNT_TOP; \
  TCNT2 = 0; \
})
#else
#define TIMER_CONFIG_NORMAL() ({ \
  TCCR2A = _BV(WGM21); \
  TCCR2B = _BV(CS21); \
  OCR2A = TIMER_COUNT_TOP / 8; \
  TCNT2 = 0; \
})
#endif

// LED indicator definitions for Arduino Uno
#define BLINKLED       13
#define BLINKLED_ON()  (PORTB |= B00100000)
#define BLINKLED_OFF() (PORTB &= B11011111)

#endif