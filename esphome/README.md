# ESPHome — SW3518 Pico W

Native Home Assistant device (ESPHome API, not the Arduino MQTT path). Same Pico W pinout as `env:picow`.

Arduino firmware in `src/` is unchanged. This folder is the rewrite for HA.

## Why ESPHome here

`env:picow` already publishes MQTT discovery. ESPHome adds OTA, the HA device API, and YAML for the TFT/buttons without a custom MQTT client. The SW3518 I2C protocol is a **local external component** (`components/sw3518`) — same registers as `src/sw3518.cpp`.

## VS Code

The stock ESPHome YAML schema does **not** know `sw3518:` — red squiggles on that key are normal. Compile anyway (`esphome run` / ESPHome extension **Upload**).

Run from this `esphome/` folder (or open `sw3518-picow.yaml`). The component is pulled from GitHub `treatbam/sw3518-rp2350-zero@main`. If you copied only the yaml into the HA add-on, that GitHub source is required; a lone `path: components` will fail.

## Flash

```bash
cd esphome
cp secrets.yaml.example secrets.yaml   # wifi_ssid / wifi_password
esphome run sw3518-picow.yaml
```

First upload: hold **BOOT**, plug USB, then run (UF2). Later updates are OTA.

HA: Settings → Devices → ESPHome → add `sw3518-picow` (encryption key is printed on first boot if you add `api.encryption`).

## Pins

See `docs/wiring-solder-guide-picow.png`. I2C **GP4/GP5** @ `0x3C`. TFT SPI0 **GP18/19/17/16/20**, BL **GP21**, buttons **GP6/GP7**, haptic **GP9**.

## UI

- **A short** — Main ↔ Session
- **B short** — Session
- **B hold** — reset session Wh integrator + haptic

Display is RGB565 16-bit (same as the RP2350 Arduino canvas). If the Pico W OOMs or the compile fails, add `color_palette: 8BIT` back under `display:`. If the image is shifted a few pixels, add `dimensions.offset_width` / `offset_height` (1.44″ ST7735 tabs vary).
