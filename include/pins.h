#pragma once

// Default pin map — Waveshare RP2350-Zero + 1.4" 128x128 SPI TFT + SW3518 + buttons + haptic.
// Change here; rebuild. Documented again in README.

// --- 1.4"/1.44" ST7735S SPI 128x128 (SPI0 defaults on Pico family: SCK=18, MOSI=19) ---
static const int PIN_TFT_SCK  = 18;
static const int PIN_TFT_MOSI = 19;
static const int PIN_TFT_CS   = 17;
// GP16 is the onboard WS2812 (Waveshare RP2350-Zero schematic DIN, Pico SDK
// PICO_DEFAULT_WS2812_PIN). TFT DC lives on GP15 so it does not fight the LED.
static const int PIN_TFT_DC   = 15;
static const int PIN_TFT_RST  = 20;
static const int PIN_TFT_BL   = 21;  // backlight; PWM for night dim
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
// Optional 3rd button (Mode) — leave unused or wire to free GPIO:
// static const int PIN_BTN_MODE = 8;

// --- Haptic motor via N-FET gate (active HIGH) ---
static const int PIN_HAPTIC = 9;
