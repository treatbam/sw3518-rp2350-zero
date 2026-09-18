#include "status_led.h"
#include "pins.h"
#include <Adafruit_NeoPixel.h>

namespace {
Adafruit_NeoPixel pixel(1, PIN_WS2812, NEO_GRB + NEO_KHZ800);

constexpr uint8_t kBright = 28;
constexpr uint8_t kBrightDim = 8;
constexpr uint32_t kPeriodMs = 1600;
constexpr uint32_t kOnMs = 100;
constexpr uint32_t kGapMs = 180;

bool tftOk = true;
bool lastOn = false;
uint8_t lastN = 0xFF;
uint8_t lastBright = 0xFF;
uint32_t lastColor = 0xFFFFFFFFu;

uint32_t pack(uint8_t r, uint8_t g, uint8_t b) { return pixel.Color(r, g, b); }

uint8_t blinkCount(uint8_t faults) {
  const bool noSw = (faults & STATUS_NO_SW3518) != 0;
  const bool noTft = (faults & STATUS_NO_TFT) != 0;
  if (noSw && noTft) return 3;
  if (noTft) return 2;
  if (noSw) return 1;
  return 0;
}

uint32_t colorFor(uint8_t n) {
  if (n == 0) return pack(0, 6, 22);    // dim cyan heartbeat — OK
  if (n == 1) return pack(48, 14, 0);   // orange — SW3518
  if (n == 2) return pack(36, 0, 36);   // magenta — TFT
  return pack(48, 0, 0);                // red — both
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
}  // namespace

void statusLedBegin() {
  tftOk = true;
  pixel.begin();
  pixel.setBrightness(kBright);
  pixel.clear();
  pixel.show();
  lastN = 0xFF;
}

void statusLedNoteTft(bool ok) { tftOk = ok; }

void statusLedShow(uint8_t faults, bool dim) {
  if (!tftOk) faults = (uint8_t)(faults | STATUS_NO_TFT);
  const uint8_t n = blinkCount(faults);
  const uint8_t bright = dim ? kBrightDim : kBright;
  const bool on = pulseOn(n, millis());
  const uint32_t c = on ? colorFor(n) : 0;
  if (on == lastOn && n == lastN && bright == lastBright && c == lastColor) return;
  lastOn = on;
  lastN = n;
  lastBright = bright;
  lastColor = c;
  pixel.setBrightness(bright);
  pixel.setPixelColor(0, c);
  pixel.show();
}
