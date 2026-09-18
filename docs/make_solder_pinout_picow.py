#!/usr/bin/env python3
"""Pico W 40-pin solder helper — CHARGER_PICOW pin map."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1400, 1100
BG, CARD, INK, MUTED = (18, 18, 20), (32, 32, 36), (240, 240, 235), (140, 140, 145)
C = {
    "pwr": (220, 70, 70),
    "gnd": (90, 90, 95),
    "tft": (255, 160, 50),
    "i2c": (80, 210, 220),
    "btn": (240, 210, 70),
    "hap": (220, 90, 200),
    "run": (180, 80, 80),
    "free": (55, 55, 60),
}

# USB at top. Left physical 1–20, right 40–21.
LEFT = [
    ("GP0", "", "free"),
    ("GP1", "", "free"),
    ("GND", "", "gnd"),
    ("GP2", "", "free"),
    ("GP3", "", "free"),
    ("GP4", "SW3518 SDA", "i2c"),
    ("GP5", "SW3518 SCL (silk SCK)", "i2c"),
    ("GND", "", "gnd"),
    ("GP6", "BTN A", "btn"),
    ("GP7", "BTN B", "btn"),
    ("GP8", "", "free"),
    ("GP9", "HAPTIC FET", "hap"),
    ("GND", "", "gnd"),
    ("GP10", "", "free"),
    ("GP11", "", "free"),
    ("GP12", "", "free"),
    ("GP13", "", "free"),
    ("GND", "", "gnd"),
    ("GP14", "", "free"),
    ("GP15", "", "free"),
]
RIGHT = [
    ("VBUS", "5V USB", "pwr"),
    ("VSYS", "", "pwr"),
    ("GND", "", "gnd"),
    ("3V3_EN", "", "free"),
    ("3V3", "TFT VCC", "pwr"),
    ("ADC_VREF", "", "free"),
    ("GP28", "", "free"),
    ("GND", "", "gnd"),
    ("GP27", "", "free"),
    ("GP26", "", "free"),
    ("RUN", "reset — not UI", "run"),
    ("GP22", "", "free"),
    ("GND", "", "gnd"),
    ("GP21", "TFT BL", "tft"),
    ("GP20", "TFT RST", "tft"),
    ("GP19", "TFT MOSI", "tft"),
    ("GP18", "TFT SCK", "tft"),
    ("GND", "", "gnd"),
    ("GP17", "TFT CS", "tft"),
    ("GP16", "", "free"),
]


def font(px, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", px)
    except OSError:
        return ImageFont.load_default()


def main():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    h = font(26, True)
    sm = font(13, True)
    tiny = font(11)
    d.text((40, 20), "sw3518 Pico W  —  solder pinout (40-pin, USB at TOP)", font=h, fill=INK)
    d.text((40, 54), "env:picow  ·  SPI0 defaults on the right rail  ·  do not use GP23–25 (Wi-Fi)", font=sm, fill=MUTED)

    bx, by, bw, bh = 430, 90, 200, 760
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=18, fill=(25, 55, 130))
    d.rounded_rectangle((bx + 55, by - 10, bx + 145, by + 22), radius=6, fill=(40, 40, 45), outline=(180, 180, 180))
    d.text((bx + 78, by - 2), "USB-C", font=tiny, fill=INK)
    d.text((bx + 48, by + 32), "Pico W", font=sm, fill=(200, 220, 255))

    ly = by + 58
    for name, used, role in LEFT:
        col = C[role]
        d.ellipse((bx - 22, ly, bx - 6, ly + 16), fill=col)
        label = f"{name}  {used}" if used else name
        d.text((bx - 210, ly), label, font=sm, fill=INK if used else MUTED)
        ly += 35

    ry = by + 58
    for name, used, role in RIGHT:
        col = C[role]
        d.ellipse((bx + bw + 6, ry, bx + bw + 22, ry + 16), fill=col)
        label = f"{name}  {used}" if used else name
        d.text((bx + bw + 28, ry), label, font=sm, fill=INK if used else MUTED)
        ry += 35

    def card(x, y, w, title, lines, color):
        d.rounded_rectangle((x, y, x + w, y + 210), radius=12, fill=CARD)
        d.rectangle((x, y, x + 8, y + 210), fill=color)
        d.text((x + 16, y + 10), title, font=font(18, True), fill=color)
        yy = y + 40
        for line in lines:
            d.text((x + 16, yy), line, font=sm, fill=INK)
            yy += 20

    card(40, 870, 320, "1.4in ST7735", [
        "VCC  3V3     GND  GND",
        "SCK  GP18    MOSI GP19",
        "CS   GP17    RST  GP20",
        "BL   GP21    (no DC pad = 3-wire)",
        "If you see A0 or RS, that is DC->GP16",
        "No MISO. Right-rail SPI0.",
    ], C["tft"])
    card(380, 870, 320, "SW3518 I2C 0x3C", [
        "SDA  GP4     SCL  GP5",
        "GND  GND  (silk SCK = SCL)",
        "Share GND. Not VBUS to 3V3.",
    ], C["i2c"])
    card(720, 870, 300, "Buttons + haptic", [
        "A  GP6 -- switch -- GND",
        "B  GP7 -- switch -- GND",
        "Haptic GP9 -> FET gate",
        "BOOT/RUN on Pico = flash/reset",
    ], C["btn"])
    card(1040, 870, 320, "HA MQTT", [
        "secrets.h  WIFI + MQTT_HOST",
        "pio run -e picow",
        "topics  picow/sw3518/#",
        "HA MQTT discovery auto",
        "Onboard LED = SW3518 missing",
    ], C["i2c"])

    out = Path(__file__).resolve().parent / "wiring-solder-guide-picow.png"
    im.save(out, "PNG")
    print("wrote", out)


if __name__ == "__main__":
    main()
