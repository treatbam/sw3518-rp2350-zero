#pragma once

// Optional analog read of a SW3518-module current-sense *test pad*.
//
// iSmartWare DS014: CSPA/CSNA and CSPC/CSNC are HIGH-SIDE shunts on VBUS
// (abs max 22 V). Do NOT tie those nets to a GPIO.
//
// Only wire this ADC if a DMM from the pad to module GND stays well under
// ~0.3 V at 5 V idle AND at load. Then it may be a true low-side millivolt
// node. Otherwise leave PIN_ISENSE unconnected.
//
// Hardware: pad --[1k]-- GP26, BAT54S clamp to 3V3/GND, share GND.

static const int PIN_ISENSE = 26;  // ADC0, Zero front-left
// milliohms of the shunt this pad sits across. Typical RCS in the datasheet
// is 5 mOhm per port. Set 0 to display millivolts only.
static const float ISENSE_MOHM = 5.0f;
static const float ISENSE_WARN_MV = 400.0f;

struct IsenseReading {
  float mv = 0;
  float amps = 0;
  bool plausible = true;  // false → pad looks like VBUS, not a shunt drop
};

void isenseBegin();
IsenseReading isenseRead();
