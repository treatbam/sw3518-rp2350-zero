#pragma once

// Default pin map — Waveshare RP2350-Zero + 1.4" 128x128 SPI TFT + SW3518 + buttons + haptic.
// Change here; rebuild. Documented again in README.

// --- 1.4"/1.44" ST7735S SPI 128x128 ---
// All TFT GPIOs are on the Zero *front* castellated edge (USB-C at top).
// SPI0 is remapped off the back-pad defaults (GP18/19) onto GP2/GP3
// (Waveshare pinout: GP2 = SPI0 SCK, GP3 = SPI0 TX).
static const int PIN_TFT_SCK  = 2;
static const int PIN_TFT_MOSI = 3;
static const int PIN_TFT_CS   = 1;
static const int PIN_TFT_DC   = 15;  // front left; GP16 is the onboard WS2812
static const int PIN_TFT_RST  = 8;
static const int PIN_TFT_BL   = 14;  // PWM night dim
static const int PIN_WS2812   = 16;  // onboard WS2812B, GRB 800 kHz

// 128x128 panels need the 144 tab (sets 128 height + col/row start).
// Do not use INITR_BLACKTAB / INITR_GREENTAB here — those are 128x160 1.8".
// If the image is shifted a few pixels, try INITR_HALLOWING (also 128x128).
#ifndef ST7735_INIT_TAB
#define ST7735_INIT_TAB INITR_144GREENTAB
#endif

// --- SW3518 I2C ---
// GP4/GP5 are I2C0 (Wire) on RP2350. (User shorthand "I2C1" = this bus.)
static const int PIN_I2C_SDA = 4;
static const int PIN_I2C_SCL = 5;
static const uint8_t SW3518_I2C_ADDR = 0x3C;

// --- Momentary buttons on case LID beside screen (active LOW, INPUT_PULLUP) ---
static const int PIN_BTN_A = 6;  // short = next page; long = haptic test
static const int PIN_BTN_B = 7;  // short = prev / jump Session; long = clear session
// Optional 3rd button (Mode) — GP8 is TFT RST; use GP10+ if needed.
// static const int PIN_BTN_MODE = 10;

// --- Haptic motor via N-FET gate (active HIGH) ---
static const int PIN_HAPTIC = 9;

// Optional analog I-sense — see include/isense.h (meter the pad vs GND first).
// static const int PIN_ISENSE = 26;  // ADC0, defined in isense.h
