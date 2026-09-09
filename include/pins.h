#pragma once

// Default pin map — Waveshare RP2350-Zero + 1.8" SPI TFT + SW3518 + buttons + haptic.
// Change here; rebuild. Documented again in README.

// --- 1.8" ST7735 SPI (SPI0 defaults on Pico family: SCK=18, MOSI=19) ---
static const int PIN_TFT_SCK  = 18;
static const int PIN_TFT_MOSI = 19;
static const int PIN_TFT_CS   = 17;
static const int PIN_TFT_DC   = 16;
static const int PIN_TFT_RST  = 20;
static const int PIN_TFT_BL   = 21;  // backlight; PWM for night dim

// ST7735 init tab: BLACKTAB is common for 128x160 1.8" modules.
// Swap if colors/offsets look wrong: INITR_GREENTAB / INITR_REDTAB / INITR_18GREENTAB
#ifndef ST7735_INIT_TAB
#define ST7735_INIT_TAB INITR_BLACKTAB
#endif

// --- SW3518 I2C ---
// GP4/GP5 are I2C0 (Wire) on RP2350. (User shorthand "I2C1" = this bus.)
static const int PIN_I2C_SDA = 4;
static const int PIN_I2C_SCL = 5;
static const uint8_t SW3518_I2C_ADDR = 0x3C;

// --- Momentary buttons (active LOW, INPUT_PULLUP) ---
static const int PIN_BTN_A = 6;  // short = next page; long = haptic test
static const int PIN_BTN_B = 7;  // short = prev / jump Session; long = clear session
// Optional 3rd button (Mode) — leave unused or wire to free GPIO:
// static const int PIN_BTN_MODE = 8;

// --- Haptic motor via N-FET gate (active HIGH) ---
static const int PIN_HAPTIC = 9;
