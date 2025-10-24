#include "IRremote.h"
#include "IRremoteInt.h"
#include <avr/interrupt.h>

volatile irparams_t irparams;

// Timing matching functions
int MATCH(int measured, int desired) {
  return measured >= TICKS_LOW(desired) && measured <= TICKS_HIGH(desired);
}

int MATCH_MARK(int measured_ticks, int desired_us) {
  return MATCH(measured_ticks, (desired_us + MARK_EXCESS));
}

int MATCH_SPACE(int measured_ticks, int desired_us) {
  return MATCH(measured_ticks, (desired_us - MARK_EXCESS));
}

// Send NEC format IR data
void IRsend::sendNEC(unsigned long data, int nbits)
{
  enableIROut(38);              // NEC uses 38kHz carrier
  mark(NEC_HDR_MARK);
  space(NEC_HDR_SPACE);
  
  // Send data bits
  for (int i = 0; i < nbits; i++) {
    if (data & TOPBIT) {
      mark(NEC_BIT_MARK);
      space(NEC_ONE_SPACE);
    } else {
      mark(NEC_BIT_MARK);
      space(NEC_ZERO_SPACE);
    }
    data <<= 1;
  }
  
  mark(NEC_BIT_MARK);
  space(0);
}

// Send raw IR data
void IRsend::sendRaw(unsigned int buf[], int len, int hz)
{
  enableIROut(hz);
  for (int i = 0; i < len; i++) {
    if (i & 1) {
      space(buf[i]);
    } else {
      mark(buf[i]);
    }
  }
  space(0);
}

// Generate IR mark (LED on with carrier)
void IRsend::mark(int time) {
  TIMER_ENABLE_PWM;
  if (time > 0) delayMicroseconds(time);
}

// Generate IR space (LED off)
void IRsend::space(int time) {
  TIMER_DISABLE_PWM;
  if (time > 0) delayMicroseconds(time);
}

// Enable IR output with specified carrier frequency
void IRsend::enableIROut(int khz) {
  TIMER_DISABLE_INTR;
  pinMode(TIMER_PWM_PIN, OUTPUT);
  digitalWrite(TIMER_PWM_PIN, LOW);
  TIMER_CONFIG_KHZ(khz);
}

// Initialize IR receiver
IRrecv::IRrecv(int recvpin)
{
  irparams.recvpin = recvpin;
  irparams.blinkflag = 0;
}

// Start IR receiving
void IRrecv::enableIRIn() {
  cli();
  TIMER_CONFIG_NORMAL();
  TIMER_ENABLE_INTR;
  TIMER_RESET;
  sei();

  irparams.rcvstate = STATE_IDLE;
  irparams.rawlen = 0;
  pinMode(irparams.recvpin, INPUT);
}

// Enable/disable LED blinking on IR activity
void IRrecv::blink13(int blinkflag)
{
  irparams.blinkflag = blinkflag;
  if (blinkflag)
    pinMode(BLINKLED, OUTPUT);
}

// Timer interrupt handler - collects raw IR timing data
ISR(TIMER_INTR_NAME)
{
  TIMER_RESET;
  uint8_t irdata = (uint8_t)digitalRead(irparams.recvpin);
  irparams.timer++;

  if (irparams.rawlen >= RAWBUF) {
    irparams.rcvstate = STATE_STOP;
  }

  switch(irparams.rcvstate) {
    case STATE_IDLE:
      if (irdata == MARK) {
        if (irparams.timer < GAP_TICKS) {
          irparams.timer = 0;
        } else {
          irparams.rawlen = 0;
          irparams.rawbuf[irparams.rawlen++] = irparams.timer;
          irparams.timer = 0;
          irparams.rcvstate = STATE_MARK;
        }
      }
      break;
      
    case STATE_MARK:
      if (irdata == SPACE) {
        irparams.rawbuf[irparams.rawlen++] = irparams.timer;
        irparams.timer = 0;
        irparams.rcvstate = STATE_SPACE;
      }
      break;
      
    case STATE_SPACE:
      if (irdata == MARK) {
        irparams.rawbuf[irparams.rawlen++] = irparams.timer;
        irparams.timer = 0;
        irparams.rcvstate = STATE_MARK;
      } else {
        if (irparams.timer > GAP_TICKS) {
          irparams.rcvstate = STATE_STOP;
        }
      }
      break;
      
    case STATE_STOP:
      if (irdata == MARK) {
        irparams.timer = 0;
      }
      break;
  }

  // LED indicator
  if (irparams.blinkflag) {
    if (irdata == MARK) {
      BLINKLED_ON();
    } else {
      BLINKLED_OFF();
    }
  }
}

// Resume receiving after decode
void IRrecv::resume() {
  irparams.rcvstate = STATE_IDLE;
  irparams.rawlen = 0;
}

// Main decode function
int IRrecv::decode(decode_results *results) {
  results->rawbuf = irparams.rawbuf;
  results->rawlen = irparams.rawlen;
  
  if (irparams.rcvstate != STATE_STOP) {
    return ERR;
  }
  
  if (decodeNEC(results)) {
    return DECODED;
  }
  
  // Fallback: hash decode for unknown signals
  if (decodeHash(results)) {
    return DECODED;
  }
  
  resume();
  return ERR;
}

// Decode NEC protocol
long IRrecv::decodeNEC(decode_results *results) {
  long data = 0;
  int offset = 1;

  // Check header mark
  if (!MATCH_MARK(results->rawbuf[offset], NEC_HDR_MARK)) {
    return ERR;
  }
  offset++;

  // Check for repeat code
  if (irparams.rawlen == 4 &&
      MATCH_SPACE(results->rawbuf[offset], NEC_RPT_SPACE) &&
      MATCH_MARK(results->rawbuf[offset+1], NEC_BIT_MARK)) {
    results->bits = 0;
    results->value = REPEAT;
    results->decode_type = NEC;
    return DECODED;
  }

  if (irparams.rawlen < 2 * NEC_BITS + 4) {
    return ERR;
  }

  // Check header space
  if (!MATCH_SPACE(results->rawbuf[offset], NEC_HDR_SPACE)) {
    return ERR;
  }
  offset++;

  // Decode data bits
  for (int i = 0; i < NEC_BITS; i++) {
    if (!MATCH_MARK(results->rawbuf[offset], NEC_BIT_MARK)) {
      return ERR;
    }
    offset++;

    if (MATCH_SPACE(results->rawbuf[offset], NEC_ONE_SPACE)) {
      data = (data << 1) | 1;
    } else if (MATCH_SPACE(results->rawbuf[offset], NEC_ZERO_SPACE)) {
      data <<= 1;
    } else {
      return ERR;
    }
    offset++;
  }

  results->bits = NEC_BITS;
  results->value = data;
  results->decode_type = NEC;
  return DECODED;
}

// Hash decode for unknown protocols
long IRrecv::decodeHash(decode_results *results) {
  if (results->rawlen < 6) {
    return ERR;
  }

  #define FNV_PRIME_32 16777619
  #define FNV_BASIS_32 2166136261

  long hash = FNV_BASIS_32;
  
  for (int i = 1; i+2 < results->rawlen; i++) {
    int value;
    unsigned int oldval = results->rawbuf[i];
    unsigned int newval = results->rawbuf[i+2];
    
    if (newval < oldval * 0.8) {
      value = 0;
    } else if (oldval < newval * 0.8) {
      value = 2;
    } else {
      value = 1;
    }
    
    hash = (hash * FNV_PRIME_32) ^ value;
  }
  
  results->value = hash;
  results->bits = 32;
  results->decode_type = UNKNOWN;
  return DECODED;
}