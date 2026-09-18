#include "status_led.h"
#include "pins.h"
#include <Arduino.h>
#if !defined(CHARGER_PICOW)
#include <Adafruit_NeoPixel.h>
#endif

namespace {
constexpr uint32_t kPeriodMs = 1600;
constexpr uint32_t kOnMs = 100;
constexpr uint32_t kGapMs = 180;

bool tftOk = true;
bool lastOn = false;
uint8_t lastN = 0xFF;

uint8_t blinkCount(uint8_t faults) {
  const bool noSw = (faults & STATUS_NO_SW3518) != 0;
  const bool noTft = (faults & STATUS_NO_TFT) != 0;
  if (noSw && noTft) return 3;
  if (noTft) return 2;
  if (noSw) return 1;
  return 0;
}

bool pulseOn(uint8_t n, uint32_t now) {
  const uint32_t t = now % kPeriodMs;
  if (n == 0) return t < 80;
  for (uint8_t i = 0; i < n; i++) {
    const uint32_t a = (uint32_t)i * (kOnMs + kGapMs);
    if (t >= a && t < a + kOnMs) return true;
  }
  return false;
}

#if defined(CHARGER_PICOW)
void ledWrite(bool on) { digitalWrite(LED_BUILTIN, on ? HIGH : LOW); }
#else
Adafruit_NeoPixel pixel(1, PIN_WS2812, NEO_GRB + NEO_KHZ800);
uint8_t lastBright = 0xFF;
uint32_t lastColor = 0xFFFFFFFFu;
constexpr uint8_t kBright = 28;
constexpr uint8_t kBrightDim = 8;
uint32_t pack(uint8_t r, uint8_t g, uint8_t b) { return pixel.Color(r, g, b); }
uint32_t colorFor(uint8_t n) {
  if (n == 0) return pack(0, 6, 22);
  if (n == 1) return pack(48, 14, 0);
  if (n == 2) return pack(36, 0, 36);
  return pack(48, 0, 0);
}
#endif
}  // namespace

void statusLedBegin() {
  tftOk = true;
  lastN = 0xFF;
#if defined(CHARGER_PICOW)
  pinMode(LED_BUILTIN, OUTPUT);
  ledWrite(false);
#else
  pixel.begin();
  pixel.setBrightness(kBright);
  pixel.clear();
  pixel.show();
#endif
}

void statusLedNoteTft(bool ok) { tftOk = ok; }

void statusLedShow(uint8_t faults, bool dim) {
  if (!tftOk) faults = (uint8_t)(faults | STATUS_NO_TFT);
  const uint8_t n = blinkCount(faults);
  const bool on = pulseOn(n, millis());
#if defined(CHARGER_PICOW)
  (void)dim;
  if (on == lastOn && n == lastN) return;
  lastOn = on;
  lastN = n;
  ledWrite(on);
#else
  const uint8_t bright = dim ? kBrightDim : kBright;
  const uint32_t c = on ? colorFor(n) : 0;
  if (on == lastOn && n == lastN && bright == lastBright && c == lastColor) return;
  lastOn = on;
  lastN = n;
  lastBright = bright;
  lastColor = c;
  pixel.setBrightness(bright);
  pixel.setPixelColor(0, c);
  pixel.show();
#endif
}
