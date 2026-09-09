# sw3518-rp2350-zero

Portable **SW3518** USB charger meter on **Waveshare RP2350-Zero** with a **1.8″ SPI TFT (128×160 ST7735)**, two momentary buttons, and a small haptic motor.

This is the pocket / field sibling of [sw3518-GEEK](https://github.com/treatbam/sw3518-GEEK). **GEEK stays the Wi‑Fi / MQTT / radio bench unit** — this firmware has **no Wi‑Fi, MQTT, web, BLE, or radio**.

MIT licensed.

## Features (MVP)

| Page | Contents |
|------|----------|
| **MAIN** | Large total W (text size 3), tight Vin/Vout + C/A row, load-share, tall bottom sparklines |
| **C** | USB-C zoom (large W, V/A, peaks, ~50px sparkline) |
| **A** | USB-A zoom |
| **S** | Compact PEAK/AVG/ENERGY grid, then C/A spark bands |

- Status crumbs along the top (`M C A S`) + live/idle pip (short labels so nothing overflows 128px)
- Portrait **128x160** layouts tuned for density (not cramped GEEK leftovers); ASCII-only TFT strings
- Session tracking in RAM (charged ms while load present, mWh, peaks) — no NVS required for MVP
- Haptic pulse on protocol change, page enter, session clear, and A-long test
- Night dim: backlight PWM drops after ~90 s idle; any button wakes it

### Button grammar

| Button | Short | Long (~800 ms) |
|--------|-------|----------------|
| **A** (GP6) | Next page | Haptic test pulse |
| **B** (GP7) | Jump to Session (or prev if already there) | Clear session + haptic |

Optional third **Mode** button is reserved in comments in `include/pins.h` (unused in MVP).

## Default pin map

Edit `include/pins.h` (also summarized here).

| Function | GPIO | Notes |
|----------|------|--------|
| TFT SCK | **18** | SPI0 |
| TFT MOSI | **19** | SPI0 |
| TFT CS | **17** | |
| TFT DC | **16** | |
| TFT RST | **20** | |
| TFT BL | **21** | PWM night dim |
| I2C SDA | **4** | Wire / **I2C0** (RP2350 GP4/5) |
| I2C SCL | **5** | SW3518 addr **0x3C** |
| BTN_A | **6** | `INPUT_PULLUP`, active LOW |
| BTN_B | **7** | `INPUT_PULLUP`, active LOW |
| HAPTIC | **9** | Active HIGH → N‑FET gate |

> **I2C naming:** GP4/GP5 are **I2C0** (`Wire`) on RP2350. The “I2C1” label in planning docs meant “the charger I2C bus,” not the hardware I2C1 block (that would be GP6/7 and would collide with the buttons).

## Display / ST7735 init

Assumes a common **1.8″ 128×160** module driven by **Adafruit_ST7735**.

Default init tab:

```cpp
#define ST7735_INIT_TAB INITR_BLACKTAB
```

If the image is offset, mirrored, or colors look wrong, change the define in `include/pins.h` (or add `-DST7735_INIT_TAB=INITR_GREENTAB` in `platformio.ini`) and try:

- `INITR_BLACKTAB` (default)
- `INITR_GREENTAB` / `INITR_18GREENTAB`
- `INITR_REDTAB`

Rotation is portrait (`setRotation(0)` → 128×160). Flip with `1`/`2`/`3` in `initDisplay()` if your panel mounting differs.

A full RGB565 canvas (`128×160×2 ≈ 40 KB`) is used; RP2350 SRAM (~520 KB) is fine.

## BOM notes

- **Waveshare RP2350-Zero**
- **SW3518 / SW3518S** charger module with I2C (0x3C)
- **1.8″ SPI ST7735** 128×160 TFT
- **2×** momentary NO buttons to GND
- **Haptic / coin vibration motor** driven by an **N‑channel MOSFET** (logic-level gate from GP9), **flyback diode** across the motor, motor supply from 3V3 or 5V as appropriate for the motor (do **not** power the motor through the GPIO)

```
GP9 ──[series R ~100Ω optional]── FET gate
FET source ── GND
FET drain ── motor (−)
motor (+) ── 3V3/5V
diode cathode to motor (+), anode to drain
```

## PlatformIO

Uses **earlephilhower Arduino-Pico** via maxgerhardt’s PlatformIO platform:

```ini
[env:rp2350-zero]
platform = https://github.com/maxgerhardt/platform-raspberrypi.git
board = waveshare_rp2350_zero
framework = arduino
board_build.core = earlephilhower
monitor_speed = 115200
```

If `waveshare_rp2350_zero` is missing in your platform package, try the closest Waveshare RP2350 / Pico 2 board id (e.g. `rpipico2`) and keep the same core flag — then update this README.

```bash
cd sw3518-rp2350-zero
pio run
pio run -t upload
pio device monitor -b 115200
```

### Flash via UF2 (no picotool)

1. Hold **BOOT**, tap **RESET** (or plug USB while holding BOOT)
2. RP2350 appears as a USB mass-storage drive
3. Copy `.pio/build/rp2350-zero/firmware.uf2` onto the drive
4. Board reboots into the sketch

CDC serial is enabled (`ARDUINO_USB_CDC_ON_BOOT`) for `Serial` over the Zero’s USB.

## Driver

`include/sw3518.h` + `src/sw3518.cpp` are adapted from the GEEK project:

- Same register / ADC math (including A/C swap at ADC types 3/4)
- `Wire.begin` is portable: ESP32 uses `(sda,scl,hz)`; RP2040/RP2350 uses `setSDA` / `setSCL` + `begin` + `setClock`

## UI notes (128x160)

Layouts in `src/main.cpp` are tuned for the small portrait panel:

- **Status:** short crumbs `M C A S`, live pip on the right
- **Main:** size-3 watts, compact Vin/Vout/C/A, load-share close under amps, leftover height for taller C/A sparklines; idle hints as a small footer
- **Port (C/A):** large W, V/A row, peaks on one line, sparkline uses remaining bottom (~50px+)
- **Session:** compact PEAK/AVG/ENERGY grid, then C and A spark bands that finish above y=160 (no clip)
- TFT strings are ASCII-only (no em dashes)

Button grammar is unchanged (see table above).


## Your SW3518S module

Matched to the common **DC barrel + stacked USB-A / USB-C** board (I2C pads silk `SDA` / `SCK`):

- Case bay tuned to ~**60 × 22 × 14 mm** with USB face out and **barrel holes** on both long sides (use the side that matches your jack).
- Silkscreen **`SCK` = I2C SCL** (clock). Wire RP2350 `SCL` (GP5) to the pad labeled SCK, `SDA` (GP4) to SDA, and share GND.
- If your PCB measures different, edit `SW_L` / `SW_W` / `SW_H` in `case/generate_case.py` and re-run it.

## Pocket case

Printable shell under [`case/`](case/):

- Waveshare RP2350-Zero pocket + USB-C access
- 1.8" ST7735 module pocket + lid window (tunable)
- SW3518S dual-port bay (~50x30x12 mm approximate — dry-fit)
- Side 6x6 tact holes, coin haptic pocket, I2C cable channel
- Friction lid + optional M2 bosses

```bash
/workspace/.cadvenv/bin/python case/generate_case.py
```

See [`case/README.md`](case/README.md) and `case/case_meta.json` for outer dims and tunables.

## Layout

```
include/pins.h      pin map + ST7735 tab define
include/sw3518.h    charger driver API
src/sw3518.cpp      charger driver
src/main.cpp        UI, buttons, haptic, session
case/               pocket shell STLs + generator
platformio.ini
```

## License

MIT — see [LICENSE](LICENSE).
