#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <math.h>
#include <string.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

#include "pins.h"
#include "sw3518.h"

// --- colors (RGB565) ---
static constexpr uint16_t COL_BLACK = 0x0000;
static constexpr uint16_t COL_WHITE = 0xFFFF;
static constexpr uint16_t COL_GREEN = 0x07E0;
static constexpr uint16_t COL_CYAN = 0x07FF;
static constexpr uint16_t COL_YELLOW = 0xFFE0;
static constexpr uint16_t COL_MAGENTA = 0xF81F;
static constexpr uint16_t COL_ORANGE = 0xFD20;
static constexpr uint16_t COL_DARKGREY = 0x7BEF;
static constexpr uint16_t COL_LIGHTGREY = 0xC618;
static constexpr uint16_t COL_DIM = 0x4208;

static constexpr int kW = 128;
static constexpr int kH = 160;
static constexpr int kStatusBarH = 12;
static constexpr uint32_t kUiMs = 200;
static constexpr uint32_t kNightIdleMs = 90000;
static constexpr float kLoadMa = 50.0f;
static constexpr int kBlFull = 255;
static constexpr int kBlDim = 64;
static constexpr uint32_t kLongPressMs = 800;
static constexpr uint32_t kDebounceMs = 30;
static constexpr size_t kHistMax = 96;
static constexpr uint32_t kSessionEndDebounceMs = 1500;

enum class Page : uint8_t { Main = 0, UsbC = 1, UsbA = 2, Session = 3, Count = 4 };

Adafruit_ST7735 tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST);
GFXcanvas16 canvas(kW, kH);
SW3518 charger;

Page page = Page::Main;
SW3518::Snapshot snap;
SW3518::Protocol lastProtocol = SW3518::Protocol::None;
uint32_t protoFlashUntil = 0;
uint32_t lastUiMs = 0;
uint32_t lastActivityMs = 0;
uint32_t lastHistPushMs = 0;
bool nightDim = false;
int blLevel = kBlFull;
bool chargerOk = false;

float histC[kHistMax] = {};
float histA[kHistMax] = {};
size_t histCount = 0;
uint32_t histPeriodMs = 250;

struct Session {
  bool active = false;
  uint32_t startMs = 0;
  uint32_t lastSampleMs = 0;
  uint32_t chargedMs = 0;
  double mwh = 0;
  float peakW = 0;
  float peakA = 0;
  float peakC_A = 0;
  float peakA_A = 0;
  float peakC_W = 0;
  float peakA_W = 0;
  float peakC_W_A = 0;
  float peakA_W_A = 0;
  uint16_t peakVoutMv = 0;
} session;

// --- haptic (non-blocking PWM burst) ---
static uint32_t hapticUntil = 0;
static uint8_t hapticDuty = 0;

static void hapticPulse(uint16_t ms = 45, uint8_t duty = 200) {
  hapticDuty = duty;
  hapticUntil = millis() + ms;
  analogWrite(PIN_HAPTIC, duty);
}

static void hapticService() {
  if (hapticUntil && (int32_t)(millis() - hapticUntil) >= 0) {
    analogWrite(PIN_HAPTIC, 0);
    hapticUntil = 0;
    hapticDuty = 0;
  }
}

static void setBacklight(int level) {
  if (level < 0) level = 0;
  if (level > 255) level = 255;
  blLevel = level;
  analogWrite(PIN_TFT_BL, level);
}

static void touchActivity() {
  lastActivityMs = millis();
  if (nightDim) {
    nightDim = false;
    setBacklight(kBlFull);
  }
}

static void gfxText(Adafruit_GFX& g, int16_t x, int16_t y, const char* s, uint16_t fg,
                    uint16_t bg, uint8_t size, bool centerX = false, bool right = false) {
  g.setTextSize(size);
  g.setTextColor(fg, bg);
  g.setTextWrap(false);
  const int16_t tw = (int16_t)(strlen(s) * 6 * size);
  if (centerX) x = x - tw / 2;
  else if (right) x = x - tw;
  g.setCursor(x, y);
  g.print(s);
}

static float sessionAvgW() {
  if (session.chargedMs < 50 || session.mwh <= 0) return 0.f;
  return static_cast<float>(session.mwh * 3600.0 / session.chargedMs);
}

static void formatDuration(uint32_t ms, char* out, size_t n) {
  const uint32_t s = ms / 1000, m = s / 60, h = m / 60;
  if (h > 0)
    snprintf(out, n, "%luh%02lum", (unsigned long)h, (unsigned long)(m % 60));
  else if (m > 0)
    snprintf(out, n, "%lum%02lus", (unsigned long)m, (unsigned long)(s % 60));
  else
    snprintf(out, n, "%lus", (unsigned long)s);
}

static void clearSession() {
  session = Session{};
  histCount = 0;
  histPeriodMs = 250;
  memset(histC, 0, sizeof(histC));
  memset(histA, 0, sizeof(histA));
  hapticPulse(80, 220);
}

static void updateSession(uint32_t now) {
  static uint32_t loadLostMs = 0;
  const bool load = snap.ia_ma > kLoadMa || snap.ic_ma > kLoadMa;

  if (load) {
    loadLostMs = 0;
    if (session.startMs == 0) {
      session.startMs = now;
      session.lastSampleMs = now;
      session.chargedMs = 0;
      session.mwh = 0;
      session.peakW = session.peakA = session.peakC_A = session.peakA_A = 0;
      session.peakC_W = session.peakA_W = 0;
      session.peakC_W_A = session.peakA_W_A = 0;
      session.peakVoutMv = 0;
    } else if (!session.active) {
      session.lastSampleMs = now;
    } else {
      const uint32_t dt = now - session.lastSampleMs;
      const float dt_h = dt / 3600000.0f;
      session.mwh += snap.power_total_w * 1000.0f * dt_h;
      session.chargedMs += dt;
      session.lastSampleMs = now;
    }
    session.active = true;

    if (snap.power_total_w > session.peakW) session.peakW = snap.power_total_w;
    const float aTot = (snap.ia_ma + snap.ic_ma) / 1000.0f;
    if (aTot > session.peakA) session.peakA = aTot;
    const float cA = snap.ic_ma / 1000.0f;
    const float aA = snap.ia_ma / 1000.0f;
    if (cA > session.peakC_A) session.peakC_A = cA;
    if (aA > session.peakA_A) session.peakA_A = aA;
    if (snap.power_c_w > session.peakC_W) {
      session.peakC_W = snap.power_c_w;
      session.peakC_W_A = cA;
    }
    if (snap.power_a_w > session.peakA_W) {
      session.peakA_W = snap.power_a_w;
      session.peakA_W_A = aA;
    }
    if (snap.vout_mv > session.peakVoutMv) session.peakVoutMv = snap.vout_mv;
  } else if (session.active) {
    if (!loadLostMs) loadLostMs = now;
    if (session.lastSampleMs && now > session.lastSampleMs) {
      const uint32_t dt = now - session.lastSampleMs;
      session.mwh += snap.power_total_w * 1000.0f * (dt / 3600000.0f);
      session.chargedMs += dt;
      session.lastSampleMs = now;
    }
    if (now - loadLostMs >= kSessionEndDebounceMs) {
      session.active = false;
    }
  }
}

static void downsampleHist() {
  const size_t half = kHistMax / 2;
  for (size_t i = 0; i < half; i++) {
    histC[i] = (histC[2 * i] + histC[2 * i + 1]) * 0.5f;
    histA[i] = (histA[2 * i] + histA[2 * i + 1]) * 0.5f;
  }
  histCount = half;
  histPeriodMs *= 2;
}

static void pushHistory() {
  if (histCount >= kHistMax) downsampleHist();
  histC[histCount] = snap.power_c_w;
  histA[histCount] = snap.power_a_w;
  histCount++;
}

static void drawSparkline(Adafruit_GFX& g, int x, int y, int w, int h, const float* data,
                          uint16_t color, size_t count) {
  g.drawRect(x, y, w, h, COL_DARKGREY);
  if (count < 2 || w < 4 || h < 4) return;
  float mx = 0.1f;
  for (size_t i = 0; i < count; i++) {
    if (data[i] > mx) mx = data[i];
  }
  int prevX = x + 1, prevY = y + h - 2;
  const size_t denom = count > 1 ? count - 1 : 1;
  for (size_t i = 0; i < count; i++) {
    const int px = x + 1 + (int)((w - 3) * i / denom);
    const int py = y + h - 2 - (int)((h - 4) * (data[i] / mx));
    if (i > 0) g.drawLine(prevX, prevY, px, py, color);
    prevX = px;
    prevY = py;
  }
}

// Small chip + slash: SW3518 not on I2C (overlay; pages stay normal)
static void drawUnlinkedIcon(int x, int y) {
  // IC body
  canvas.drawRect(x, y, 10, 8, COL_ORANGE);
  canvas.fillRect(x + 1, y + 1, 8, 6, COL_BLACK);
  // pin stubs
  canvas.drawFastVLine(x + 2, y - 1, 2, COL_ORANGE);
  canvas.drawFastVLine(x + 5, y - 1, 2, COL_ORANGE);
  canvas.drawFastVLine(x + 8, y - 1, 2, COL_ORANGE);
  canvas.drawFastVLine(x + 2, y + 7, 2, COL_ORANGE);
  canvas.drawFastVLine(x + 5, y + 7, 2, COL_ORANGE);
  canvas.drawFastVLine(x + 8, y + 7, 2, COL_ORANGE);
  // slash
  canvas.drawLine(x, y + 7, x + 9, y, COL_ORANGE);
  canvas.drawLine(x, y + 8, x + 9, y + 1, COL_ORANGE);
}

static void clearSnapshot() {
  snap = SW3518::Snapshot{};
  lastProtocol = SW3518::Protocol::None;
}

static void drawStatusBar() {
  canvas.fillRect(0, 0, kW, kStatusBarH, COL_BLACK);
  canvas.drawFastHLine(0, kStatusBarH - 1, kW, COL_DIM);

  gfxText(canvas, 2, 2, "CHG", COL_CYAN, COL_BLACK, 1);

  // Short crumbs so the live pip never overflows on 128px
  const char* crumbs[] = {"M", "C", "A", "S"};
  int active = (int)page;
  if (active < 0) active = 0;
  if (active > 3) active = 3;

  int x = 28;
  for (int i = 0; i < 4; i++) {
    const bool on = (i == active);
    gfxText(canvas, x, 2, crumbs[i], on ? COL_WHITE : COL_DARKGREY, COL_BLACK, 1);
    const int tw = (int)strlen(crumbs[i]) * 6;
    if (on) canvas.drawFastHLine(x, 10, tw, COL_CYAN);
    x += tw + 8;
  }

  if (!chargerOk) {
    // CHG label already drawn; retint + unlink chip icon (top-right)
    gfxText(canvas, 2, 2, "CHG", COL_ORANGE, COL_BLACK, 1);
    drawUnlinkedIcon(kW - 14, 2);
  } else {
    const bool live = snap.ia_ma > kLoadMa || snap.ic_ma > kLoadMa;
    canvas.fillCircle(kW - 6, 5, 3, live ? COL_GREEN : COL_DIM);
  }
}

static void drawLoadShareBar(int y) {
  const float pc = snap.power_c_w;
  const float pa = snap.power_a_w;
  const float tot = pc + pa;
  const int w = kW - 8;
  canvas.drawRect(4, y, w, 6, COL_DARKGREY);
  if (tot < 0.05f) {
    gfxText(canvas, 4, y - 10, "C/A share --", COL_DARKGREY, COL_BLACK, 1);
    return;
  }
  int wc = (int)(w * (pc / tot) + 0.5f);
  if (wc < 0) wc = 0;
  if (wc > w) wc = w;
  if (wc > 0) canvas.fillRect(4, y, wc, 6, COL_YELLOW);
  if (wc < w) canvas.fillRect(4 + wc, y, w - wc, 6, COL_MAGENTA);
  char buf[28];
  snprintf(buf, sizeof(buf), "C %.0f%%  A %.0f%%", 100.f * pc / tot, 100.f * pa / tot);
  gfxText(canvas, 4, y - 10, buf, COL_LIGHTGREY, COL_BLACK, 1);
}

static void drawMain() {
  drawStatusBar();
  const bool charging = snap.ia_ma > kLoadMa || snap.ic_ma > kLoadMa;
  const bool flash = millis() < protoFlashUntil;
  const char* proto = SW3518::protocolName(snap.protocol);

  // Header row under status bar
  gfxText(canvas, 4, 14, charging ? "LIVE" : "IDLE", charging ? COL_GREEN : COL_LIGHTGREY,
          COL_BLACK, 1);
  if (flash) canvas.fillRect(kW / 2 - 40, 14, 80, 10, COL_YELLOW);
  gfxText(canvas, kW / 2, 14, proto, flash ? COL_BLACK : COL_YELLOW,
          flash ? COL_YELLOW : COL_BLACK, 1, true);

  char buf[40];
  // Size-3 total watts (fits ~"100.0W" on 128px)
  snprintf(buf, sizeof(buf), "%.1fW", snap.power_total_w);
  gfxText(canvas, kW / 2, 28, buf, COL_WHITE, COL_BLACK, 3, true);

  // Tight Vin/Vout + C/A amp row
  snprintf(buf, sizeof(buf), "Vin%.1f", snap.vin_mv / 1000.0f);
  gfxText(canvas, 4, 56, buf, COL_LIGHTGREY, COL_BLACK, 1);
  snprintf(buf, sizeof(buf), "Vout%.2f", snap.vout_mv / 1000.0f);
  gfxText(canvas, 66, 56, buf, COL_LIGHTGREY, COL_BLACK, 1);

  gfxText(canvas, 4, 68, "C", COL_YELLOW, COL_BLACK, 1);
  snprintf(buf, sizeof(buf), "%.2fA", snap.ic_ma / 1000.0f);
  gfxText(canvas, 14, 68, buf, COL_WHITE, COL_BLACK, 1);
  gfxText(canvas, 66, 68, "A", COL_MAGENTA, COL_BLACK, 1);
  snprintf(buf, sizeof(buf), "%.2fA", snap.ia_ma / 1000.0f);
  gfxText(canvas, 76, 68, buf, COL_WHITE, COL_BLACK, 1);

  // Load-share tucked close under amps
  drawLoadShareBar(86);

  // Compact footer / session strip, then tall sparklines
  if (session.startMs != 0 || session.mwh > 0.01) {
    char dur[16];
    formatDuration(session.chargedMs, dur, sizeof(dur));
    snprintf(buf, sizeof(buf), "%s pk%.0fW avg%.0fW", dur, session.peakW, sessionAvgW());
    gfxText(canvas, 4, 98, buf, COL_LIGHTGREY, COL_BLACK, 1);
    snprintf(buf, sizeof(buf), "%.0fmWh", session.mwh);
    gfxText(canvas, 4, 108, buf, COL_DARKGREY, COL_BLACK, 1);
  } else {
    gfxText(canvas, 4, 100, "A=next B=ses B-long=clr", COL_DIM, COL_BLACK, 1);
  }

  // Leftover height -> taller C/A sparklines (y=118..158)
  drawSparkline(canvas, 4, 118, 56, 40, histC, COL_YELLOW, histCount);
  drawSparkline(canvas, 68, 118, 56, 40, histA, COL_MAGENTA, histCount);
}

static void drawPort(bool usbC) {
  drawStatusBar();
  const uint16_t accent = usbC ? COL_YELLOW : COL_MAGENTA;
  const float amps = (usbC ? snap.ic_ma : snap.ia_ma) / 1000.0f;
  const float watts = usbC ? snap.power_c_w : snap.power_a_w;
  const float peakA = usbC ? session.peakC_A : session.peakA_A;
  const float peakW = usbC ? session.peakC_W : session.peakA_W;

  gfxText(canvas, 4, 14, usbC ? "USB-C" : "USB-A", accent, COL_BLACK, 1);
  gfxText(canvas, kW / 2, 14, SW3518::protocolName(snap.protocol), COL_LIGHTGREY, COL_BLACK, 1,
          true);

  char buf[32];
  // Large watts
  snprintf(buf, sizeof(buf), "%.2fW", watts);
  gfxText(canvas, kW / 2, 28, buf, COL_WHITE, COL_BLACK, 3, true);

  // V / A row
  snprintf(buf, sizeof(buf), "%.2fV", snap.vout_mv / 1000.0f);
  gfxText(canvas, 4, 56, buf, COL_LIGHTGREY, COL_BLACK, 1);
  snprintf(buf, sizeof(buf), "%.2fA", amps);
  gfxText(canvas, 68, 56, buf, COL_WHITE, COL_BLACK, 1);

  // Peaks + charged on one compact line each
  snprintf(buf, sizeof(buf), "pk %.2fA %.1fW", peakA, peakW);
  gfxText(canvas, 4, 70, buf, COL_LIGHTGREY, COL_BLACK, 1);

  char dur[16];
  formatDuration(session.chargedMs, dur, sizeof(dur));
  snprintf(buf, sizeof(buf), "chg %s", dur);
  gfxText(canvas, 4, 82, buf, COL_DARKGREY, COL_BLACK, 1);

  // Remaining bottom ~50px sparkline
  drawSparkline(canvas, 4, 96, kW - 8, 58, usbC ? histC : histA, accent, histCount);
}

static void drawSession() {
  drawStatusBar();
  gfxText(canvas, 4, 14, "SESSION", COL_CYAN, COL_BLACK, 1);

  char buf[40], dur[16];
  if (session.startMs != 0 || session.mwh > 0.01) {
    formatDuration(session.chargedMs, dur, sizeof(dur));
  } else {
    snprintf(dur, sizeof(dur), "--");
  }
  gfxText(canvas, kW - 4, 14, dur, COL_WHITE, COL_BLACK, 1, false, true);

  // Compact PEAK / AVG / ENERGY grid
  const float wh = session.mwh / 1000.0f;
  gfxText(canvas, 4, 28, "PEAK", COL_DARKGREY, COL_BLACK, 1);
  gfxText(canvas, 46, 28, "AVG", COL_DARKGREY, COL_BLACK, 1);
  gfxText(canvas, 88, 28, "Wh", COL_DARKGREY, COL_BLACK, 1);

  snprintf(buf, sizeof(buf), "%.1f", session.peakW);
  gfxText(canvas, 4, 40, buf, COL_WHITE, COL_BLACK, 2);
  snprintf(buf, sizeof(buf), "%.1f", sessionAvgW());
  gfxText(canvas, 46, 40, buf, COL_WHITE, COL_BLACK, 2);
  snprintf(buf, sizeof(buf), "%.2f", wh);
  gfxText(canvas, 88, 40, buf, COL_ORANGE, COL_BLACK, 1);

  snprintf(buf, sizeof(buf), "Vpk %.2f", session.peakVoutMv / 1000.0f);
  gfxText(canvas, 4, 60, buf, COL_LIGHTGREY, COL_BLACK, 1);

  // C and A spark bands with room (no clip at y=160)
  snprintf(buf, sizeof(buf), "C pk %.1fW @%.2fA", session.peakC_W, session.peakC_W_A);
  gfxText(canvas, 4, 74, buf, COL_YELLOW, COL_BLACK, 1);
  drawSparkline(canvas, 4, 86, kW - 8, 28, histC, COL_YELLOW, histCount);

  snprintf(buf, sizeof(buf), "A pk %.1fW @%.2fA", session.peakA_W, session.peakA_W_A);
  gfxText(canvas, 4, 118, buf, COL_MAGENTA, COL_BLACK, 1);
  drawSparkline(canvas, 4, 130, kW - 8, 28, histA, COL_MAGENTA, histCount);
}

static void setPage(Page p) {
  if (p == page) return;
  page = p;
  hapticPulse(25, 160);
  touchActivity();
}

static void nextPage() {
  uint8_t i = (uint8_t)page;
  i = (i + 1) % (uint8_t)Page::Count;
  setPage(static_cast<Page>(i));
}

static void prevPage() {
  uint8_t i = (uint8_t)page;
  i = (i == 0) ? ((uint8_t)Page::Count - 1) : (i - 1);
  setPage(static_cast<Page>(i));
}

static void drawFrame() {
  canvas.fillScreen(COL_BLACK);
  switch (page) {
    case Page::Main: drawMain(); break;
    case Page::UsbC: drawPort(true); break;
    case Page::UsbA: drawPort(false); break;
    case Page::Session: drawSession(); break;
    default: drawMain(); break;
  }
  tft.drawRGBBitmap(0, 0, canvas.getBuffer(), kW, kH);
}

// --- simple button grammar (no OneButton dep) ---
struct Btn {
  int pin;
  bool stable = true;  // HIGH = released (pullup)
  bool rawPrev = true;
  uint32_t lastChange = 0;
  uint32_t pressStart = 0;
  bool longFired = false;
};

static Btn btnA{PIN_BTN_A};
static Btn btnB{PIN_BTN_B};

static void serviceBtn(Btn& b, void (*onShort)(), void (*onLong)()) {
  const bool raw = digitalRead(b.pin);  // HIGH = up
  const uint32_t now = millis();
  if (raw != b.rawPrev) {
    b.rawPrev = raw;
    b.lastChange = now;
  }
  if ((now - b.lastChange) < kDebounceMs) {
    // still debounce edge, but allow long-press while held
  } else if (raw != b.stable) {
    b.stable = raw;
    if (!b.stable) {
      b.pressStart = now;
      b.longFired = false;
      touchActivity();
    } else {
      if (!b.longFired && (now - b.pressStart) >= kDebounceMs) {
        if (onShort) onShort();
      }
    }
  }
  if (!b.stable && !b.longFired && (now - b.pressStart) >= kLongPressMs) {
    b.longFired = true;
    if (onLong) onLong();
  }
}

static void onAShort() { nextPage(); }
static void onALong() { hapticPulse(120, 255); }
static void onBShort() {
  // jump Session if not there; else prev
  if (page != Page::Session) setPage(Page::Session);
  else prevPage();
}
static void onBLong() {
  clearSession();
  setPage(Page::Main);
}

static void initDisplay() {
  pinMode(PIN_TFT_BL, OUTPUT);
  setBacklight(kBlFull);

  // earlephilhower SPI0: default SCK=18 MOSI=19 matches our map
  SPI.setSCK(PIN_TFT_SCK);
  SPI.setTX(PIN_TFT_MOSI);
#if defined(WOKWI_SIM) && WOKWI_SIM
  SPI.setRX(12);  // write-only TFT; free GP15 for DC
#endif
  SPI.begin(true);

  tft.initR(ST7735_INIT_TAB);
  tft.setRotation(0);  // 128 wide x 160 tall portrait
  tft.fillScreen(COL_BLACK);
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("sw3518-rp2350-zero");

  pinMode(PIN_BTN_A, INPUT_PULLUP);
  pinMode(PIN_BTN_B, INPUT_PULLUP);
  pinMode(PIN_HAPTIC, OUTPUT);
  digitalWrite(PIN_HAPTIC, LOW);
  analogWrite(PIN_HAPTIC, 0);

  initDisplay();
  canvas.fillScreen(COL_BLACK);
  gfxText(canvas, kW / 2, kH / 2 - 6, "SW3518 Zero", COL_CYAN, COL_BLACK, 1, true);
  tft.drawRGBBitmap(0, 0, canvas.getBuffer(), kW, kH);

  chargerOk = charger.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
  Serial.printf("SW3518 %s @0x%02X SDA=%d SCL=%d\n", chargerOk ? "OK" : "MISSING",
                (unsigned)SW3518::kAddr, PIN_I2C_SDA, PIN_I2C_SCL);

  lastActivityMs = millis();
  hapticPulse(30, 180);
}

void loop() {
  const uint32_t now = millis();
  hapticService();

  serviceBtn(btnA, onAShort, onALong);
  serviceBtn(btnB, onBShort, onBLong);

  static uint32_t lastProbeMs = 0;
  if (!chargerOk) {
    if (now - lastProbeMs >= 1000) {
      lastProbeMs = now;
      chargerOk = charger.probe();
      if (chargerOk) {
        charger.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
      } else {
        clearSnapshot();
      }
    }
  }

  if (now - lastUiMs >= kUiMs) {
    lastUiMs = now;
    if (chargerOk) {
      if (charger.readSnapshot(snap)) {
        if (snap.protocol != lastProtocol) {
          lastProtocol = snap.protocol;
          protoFlashUntil = now + 2000;
          hapticPulse(35, 180);
        }
        updateSession(now);
        if (now - lastHistPushMs >= histPeriodMs) {
          lastHistPushMs = now;
          pushHistory();
        }
      } else {
        chargerOk = false;
        clearSnapshot();
      }
    }
    drawFrame();
  }

  // night dim
  if (!nightDim && (now - lastActivityMs) > kNightIdleMs) {
    nightDim = true;
    setBacklight(kBlDim);
  }
}
