# ESPHome — SW3518 Pico W

YAML and the `sw3518` component live at the **repo root** (ESPHome requires `components/<name>/` next to the yaml):

- [`../sw3518-picow.yaml`](../sw3518-picow.yaml)
- [`../components/sw3518/`](../components/sw3518/)

Arduino firmware in `src/` is unchanged.

## Why ESPHome here

`env:picow` already publishes MQTT discovery. ESPHome adds OTA, the HA device API, and YAML for the TFT/buttons without a custom MQTT client. The SW3518 I2C protocol is a **local external component** (`components/sw3518`) — same registers as `src/sw3518.cpp`.

## VS Code

Open the **repo root** (the folder with `platformio.ini` and `sw3518-picow.yaml`). The stock ESPHome schema still underlines `sw3518:` — that is normal. Compile anyway.

If you copy yaml into the HA add-on, copy the whole `components/sw3518/` tree next to it.

## Flash

```bash
# repo root (next to platformio.ini)
cp secrets.yaml.example secrets.yaml
esphome run sw3518-picow.yaml
```

First upload: hold **BOOT**, plug USB, then run (UF2). Later updates are OTA.

HA: Settings → Devices → ESPHome → add `sw3518-picow` (encryption key is printed on first boot if you add `api.encryption`).

## Pins

See `docs/wiring-solder-guide-picow.png`. I2C **GP4/GP5** @ `0x3C`. TFT SPI0 **GP18/19/17/20**, BL **GP21**, buttons **GP6/GP7**, haptic **GP9**.

No DC/A0/RS on the glass: ESPHome’s `ili9xxx` cannot drive 3-wire SPI. Use Arduino `pio run -e picow` (`PIN_TFT_DC = -1`). If the pin is labeled **A0** or **RS**, that *is* DC — GP16.

## UI

- **A short** — Main ↔ Session
- **B short** — Session
- **B hold** — reset session Wh integrator + haptic

Display is RGB565 16-bit (same as the RP2350 Arduino canvas). If the Pico W OOMs or the compile fails, add `color_palette: 8BIT` back under `display:`. If the image is shifted a few pixels, add `dimensions.offset_width` / `offset_height` (1.44″ ST7735 tabs vary).
