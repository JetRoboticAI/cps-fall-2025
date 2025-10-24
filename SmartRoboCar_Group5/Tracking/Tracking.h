#ifndef _Tracking_H_
#define _Tracking_H_
#include <arduino.h>
/*ITR20001 Detection*/
class DeviceDriverSet_ITR20001
{
public:
  bool DeviceDriverSet_ITR20001_Init(void);

  // Get analog reading from the left channel
  float DeviceDriverSet_ITR20001_getAnaloguexxx_L(void);

  // Get analog reading from the middle channel
  float DeviceDriverSet_ITR20001_getAnaloguexxx_M(void);

  // Get analog reading from the right channel
  float DeviceDriverSet_ITR20001_getAnaloguexxx_R(void);
#if _Test_DeviceDriverSet
  // Test function for debugging the sensor
  void DeviceDriverSet_ITR20001_Test(void);
#endif

private:
#define PIN_ITR20001xxxL A2
#define PIN_ITR20001xxxM A1
#define PIN_ITR20001xxxR A0
};

#endif
