#ifndef IRremote_h
#define IRremote_h

// Decode results structure
class decode_results {
public:
  int decode_type;              // Protocol type (NEC)
  unsigned long value;          // Decoded IR value
  int bits;                     // Number of bits decoded
  volatile unsigned int *rawbuf; // Raw timing buffer
  int rawlen;                   // Buffer length
};

// Protocol identifiers
#define NEC 1
#define UNKNOWN -1

// NEC repeat code value
#define REPEAT 0xffffffff

// IR receiver class
class IRrecv
{
public:
  IRrecv(int recvpin);
  void blink13(int blinkflag);  // Enable/disable LED indicator
  int decode(decode_results *results);
  void enableIRIn();            // Start receiving
  void resume();                // Resume after decoding
private:
  long decodeNEC(decode_results *results);
  long decodeHash(decode_results *results);
};

// IR transmitter class
class IRsend
{
public:
  IRsend() {}
  void sendNEC(unsigned long data, int nbits);
  void sendRaw(unsigned int buf[], int len, int hz);
private:
  void enableIROut(int khz);
  void mark(int usec);
  void space(int usec);
};

// Timing constants
#define USECPERTICK 50          // Timer tick duration in microseconds
#define RAWBUF 100              // Raw buffer size
#define MARK_EXCESS 100         // Timing correction for sensor lag

#endif