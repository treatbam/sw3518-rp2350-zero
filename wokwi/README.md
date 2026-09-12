# Wokwi simulation (portable UI)

Official Wokwi **does not support RP2350 / Pico 2** yet (`wokwi-pi-pico` is RP2040 only).
This folder is a **sim twin**: Raspberry Pi Pico + the same GP map as `include/pins.h`,
with `-DWOKWI_SIM=1` so SW3518 readings are canned (no I2C charger chip in the diagram).

## Parts
- Pico (stand-in for RP2350-Zero)
- ST7735 128×160 (`chip-st7735` custom chip)
- Buttons A/B on GP6/GP7
- LED on GP9 = haptic stand-in

## Run
```bash
pio run -e pico-wokwi
```
Open the repo in VS Code with the **Wokwi** extension, open `diagram.json`, start sim.

Or from repo root (after build):
```bash
# firmware paths are in ../wokwi.toml
```

Hardware flash still uses `env:rp2350-zero` — do **not** flash the `pico-wokwi` UF2 to a real Zero.
