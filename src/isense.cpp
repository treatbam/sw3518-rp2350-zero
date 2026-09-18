#include "isense.h"

#if defined(WOKWI_SIM) && WOKWI_SIM
void isenseBegin() {}
IsenseReading isenseRead() { return {}; }
#else

void isenseBegin() {
  analogReadResolution(12);
  pinMode(PIN_ISENSE, INPUT);
}

IsenseReading isenseRead() {
  IsenseReading r;
  uint32_t acc = 0;
  for (int i = 0; i < 32; i++) {
    acc += analogRead(PIN_ISENSE);
  }
  r.mv = (acc / 32.0f) * (3300.0f / 4095.0f);
  r.plausible = r.mv < ISENSE_WARN_MV;
  if (r.plausible && ISENSE_MOHM > 0.1f) {
    r.amps = r.mv / ISENSE_MOHM;
  }
  return r;
}

#endif
