# sw3518-rp2350-zero

Portable **SW3518** USB charger meter on **Waveshare RP2350-Zero** with a **1.4″ SPI TFT (128×128 ST7735S)**, two momentary buttons, and a small haptic motor.

This is the pocket / field sibling of [sw3518-GEEK](https://github.com/treatbam/sw3518-GEEK). **GEEK stays the Wi‑Fi / MQTT / radio bench unit** — this firmware has **no Wi‑Fi, MQTT, web, BLE, or radio**.

MIT licensed.

## Features (MVP)

| Page | Contents |
|------|----------|
| **MAIN** | Large total W (text size 3), tight Vin/Vout + C/A row, load-share, compact C/A sparklines |
| **C** | USB-C zoom (large W, V/A, peaks, ~42px sparkline) |
| **A** | USB-A zoom |
| **S** | Compact PEAK/AVG/ENERGY grid, then C/A spark bands |

- Status crumbs along the top (`M C A S`) + live/idle pip (short labels so nothing overflows 128px)
- Square **128×128** layouts packed for the 1.4″ panel; ASCII-only TFT strings
- Session tracking in RAM (charged ms while load present, mWh, peaks) — no NVS required for MVP. I2C loss **pauses** energy (does not bill the outage). Host tests: `make -C tests test`.
- Haptic pulse on protocol change, page enter, session clear, and A-long test
- Night dim: backlight PWM drops after ~90 s idle; any button wakes it
- Onboard **WS2812** (GP16): blink *count* = what’s missing. 0 = OK (dim cyan heartbeat), **1 orange = SW3518 missing**, 2 magenta = TFT missing, 3 red = both. Night dim lowers brightness. TFT has no MISO on this pin map, so 2-blink cannot be proven and is reserved.

### Button grammar

| Button | Short | Long (~800 ms) |
|--------|-------|----------------|
| **A** (GP6) | Next page | Haptic test pulse |
| **B** (GP7) | Jump to Session (or prev if already there) | Clear session + haptic |

Optional third **Mode** button is reserved in comments in `include/pins.h` (unused in MVP).

## Default pin map

Soldering helper (Zero front/back + wire-to-part): [`docs/wiring-solder-guide.png`](docs/wiring-solder-guide.png). Regenerate with `python3 docs/make_solder_pinout.py`.

Edit `include/pins.h` (also summarized here).

| Function | GPIO | Notes |
|----------|------|--------|
| TFT SCK | **2** | SPI0 SCK, **front** edge |
| TFT MOSI | **3** | SPI0 TX, front edge |
| TFT CS | **1** | front edge |
| TFT DC | **15** | front left (GP16 is onboard WS2812) |
| TFT RST | **8** | front edge |
| TFT BL | **14** | PWM night dim, front left |
| WS2812 | **16** | Onboard RGB (Waveshare schematic DIN, `PICO_DEFAULT_WS2812_PIN`) |
| I2C SDA | **4** | Wire / **I2C0** (RP2350 GP4/5) |
| I2C SCL | **5** | SW3518 addr **0x3C** |
| BTN_A | **6** | `INPUT_PULLUP`, active LOW |
| BTN_B | **7** | `INPUT_PULLUP`, active LOW |
| HAPTIC | **9** | Active HIGH → N‑FET gate |
| I-sense (optional) | **26** | ADC0. **Meter the pad vs GND first.** If it is ~Vout, it is high-side CSN/CSP — do not connect. |

> **I2C naming:** GP4/GP5 are **I2C0** (`Wire`) on RP2350. The “I2C1” label in planning docs meant “the charger I2C bus,” not the hardware I2C1 block (that would be GP6/7 and would collide with the buttons).

## Analog I-sense pad (optional)

The SW3518 datasheet (iSmartWare DS014) puts **per-port current shunts on the high side of VBUS**: CSPA/CSNA (Type-A) and CSPC/CSNC (Type-C), typical **RCS = 5 mΩ**, abs max **22 V**. Combined port current is already on I2C (`ia_ma + ic_ma`).

A marketplace “current sensing reference / low-side / both ports” copper zone on the **back of the module** is **not** those pins unless you prove it:

1. DMM from the pad to **module GND**, charger at 5 V idle, then under load.
2. If you see **~5–20 V**, that is VBUS/CSN — **do not** tie it to the RP2350.
3. If you see **tens of millivolts** that scale with load, it may be a true low-side drop. Then: pad → **1 kΩ** → **GP26**, BAT54S clamp to 3V3/GND, share GND. Session page shows `Is x.xxA` (or `Is HI` if the ADC sees >0.4 V).

Calibrate `ISENSE_MOHM` in `include/isense.h` with `R = V_drop / I_known`.

## Display / ST7735 init

Assumes a **1.4″ / 1.44″ 128×128** ST7735S module driven by **Adafruit_ST7735**.

Default init tab (sets 128 height + column/row start — do **not** use the 1.8″ BLACKTAB/GREENTAB here):

```cpp
#define ST7735_INIT_TAB INITR_144GREENTAB
```

If the image is shifted a few pixels, try `INITR_HALLOWING` (also 128×128) in `include/pins.h`. Flip rotation with `1`/`2`/`3` in `initDisplay()` if the panel is mounted rotated.

A full RGB565 canvas (`128×128×2 = 32 KB`) is used; RP2350 SRAM (~520 KB) is fine.

## BOM notes

- **Waveshare RP2350-Zero**
- **SW3518 / SW3518S** charger module with I2C (0x3C)
- **1.4″ SPI ST7735S** 128×128 TFT
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

## UI notes (128×128)

Layouts in `src/main.cpp` are packed for the square 1.4″ panel (32px shorter than the old 1.8″ 160-tall UI):

- **Status:** short crumbs `M C A S`, live pip on the right
- **Main:** size-3 watts kept; Vin/Vout/C/A + load-share; one-line session footer; C/A sparklines ~28px
- **Port (C/A):** large W, V/A row, peaks on one line, sparkline ~42px
- **Session:** PEAK/AVG/ENERGY grid, then C and A spark bands that finish above y=128
- TFT strings are ASCII-only (no em dashes)

Button grammar is unchanged (see table above).



**Case port layout (v3):** DC barrel exits the **+X end** through a wide flared mouth; stacked USB-A/C exits the **+Y long side**. Zero USB-C stays on the opposite end.

## Your SW3518S module

Matched to the common **DC barrel + stacked USB-A / USB-C** board (I2C pads silk `SDA` / `SCK`):

- Case bay tuned to ~**60 × 22 × 14 mm** with - Silkscreen **`SCK` = I2C SCL** (clock). Wire RP2350 `SCL` (GP5) to the pad labeled SCK, `SDA` (GP4) to SDA, and share GND.
- If your PCB measures different, edit `SW_L` / `SW_W` / `SW_H` in `case/generate_case.py` and re-run it.




## Wokwi simulation

Wokwi has **no official RP2350 board** yet. This repo includes a **Pico (RP2040) sim twin** that reuses the same GPIO numbers and UI firmware:

```bash
pio run -e pico-wokwi
```

Then open `diagram.json` with the [Wokwi VS Code extension](https://docs.wokwi.com/vscode/getting-started) (see `wokwi.toml` + `wokwi/README.md`).

- ST7735 via custom chip `chip-st7735`
- Buttons A/B + haptic LED
- `-DWOKWI_SIM=1` feeds fake SW3518 snapshots (no real I2C charger in the sim)

Flash hardware with `env:rp2350-zero` only — not the Wokwi UF2.

## Pocket case (v5)

v5.1: **no side USB cut and no through-wall bars**. Flash the Zero with the lid off. Earlier “missing corner” / side bars were a Zero USB-C cut and ledges punching through the walls.

Module-specific details:
- **Barrel**: tight ~8 mm body + 10 mm collar recess (5.5×2.1 jack), flush on one end
- **USB**: dual-tier mouth (C below, A above) sized to the stacked connector, flush on the other end
- **4×** mounting bosses for the SW3518 corner holes
- Cap clearance wells for the electrolytics under the deck
- Lid A/B beside the screen; Zero USB-C mid-side for programming

Outer ~**62 × 38 × 25 mm**. Dry-fit and tell me if hole spacing or jack height is off.

## Pocket case (v4 — flush ends)

SW3518S is the **length spine**:
- **DC barrel** flush with one case end
- **Stacked USB-A/C** flush with the opposite end
- 1.8″ TFT + RP2350-Zero on an **upper deck** above the charger
- Zero USB-C exits a **side** opening for flashing

Outer ~**62.4 × 42.0 × 25.6 mm**.

Print `case/pocket_bottom.stl` + `case/pocket_lid.stl`. Pad silk `SCK` = I2C SCL.
**Buttons (v4.2):** on the **lid** beside the screen (A/B), not the long sides. Side wall holes removed. Wire 6×6 tacts under the lid to GP6/GP7.



## Wokwi simulation

Wokwi has **no official RP2350 board** yet. This repo includes a **Pico (RP2040) sim twin** that reuses the same GPIO numbers and UI firmware:

```bash
pio run -e pico-wokwi
```

Then open `diagram.json` with the [Wokwi VS Code extension](https://docs.wokwi.com/vscode/getting-started) (see `wokwi.toml` + `wokwi/README.md`).

- ST7735 via custom chip `chip-st7735`
- Buttons A/B + haptic LED
- `-DWOKWI_SIM=1` feeds fake SW3518 snapshots (no real I2C charger in the sim)

Flash hardware with `env:rp2350-zero` only — not the Wokwi UF2.

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
