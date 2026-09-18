#pragma once
#include <stdint.h>

// Onboard WS2812B (GP16). Fault language is blink *count*, not live/idle:
//   0 = OK (dim heartbeat)
//   1 = SW3518 missing
//   2 = TFT missing (only if noted; no MISO on this board so init cannot prove it)
//   3 = both
enum : uint8_t {
  STATUS_OK = 0,
  STATUS_NO_SW3518 = 1u << 0,
  STATUS_NO_TFT = 1u << 1,
};

void statusLedBegin();
void statusLedNoteTft(bool ok);
void statusLedShow(uint8_t faults, bool dim);
