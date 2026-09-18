#!/usr/bin/env python3
"""Rough soldering pinout from include/pins.h + Waveshare RP2350-Zero wiki pinout."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1680, 1030
BG, CARD, INK, MUTED = (18, 18, 20), (32, 32, 36), (240, 240, 235), (140, 140, 145)
LINE = (70, 70, 76)

C = {
    "pwr": (220, 70, 70),
    "gnd": (90, 90, 95),
    "tft": (255, 160, 50),
    "i2c": (80, 210, 220),
    "btn": (240, 210, 70),
    "hap": (220, 90, 200),
    "led": (80, 200, 90),
    "adc": (120, 180, 255),
    "free": (55, 55, 60),
}

FRONT_L = [
    ("5V", "VIN", "pwr"),
    ("GND", "", "gnd"),
    ("3V3", "", "pwr"),
    ("29", "", "free"),
    ("28", "", "free"),
    ("27", "", "free"),
    ("26", "I-sense ADC", "adc"),
    ("15", "TFT DC", "tft"),
    ("14", "TFT BL", "tft"),
]
FRONT_R = [
    ("0", "", "free"),
    ("1", "TFT CS", "tft"),
    ("2", "TFT SCK", "tft"),
    ("3", "TFT MOSI", "tft"),
    ("4", "SW3518 SDA", "i2c"),
    ("5", "SW3518 SCL  (silk SCK)", "i2c"),
    ("6", "BTN A", "btn"),
    ("7", "BTN B", "btn"),
    ("8", "TFT RST", "tft"),
    ("9", "HAPTIC FET gate", "hap"),
    ("10", "", "free"),
    ("11", "", "free"),
    ("12", "", "free"),
    ("13", "", "free"),
]
BACK_R = [
    ("25", "", "free"),
    ("24", "", "free"),
    ("23", "", "free"),
    ("22", "", "free"),
    ("21", "", "free"),
    ("20", "", "free"),
    ("19", "", "free"),
    ("18", "", "free"),
    ("17", "", "free"),
    ("GND", "", "gnd"),
]


def font(px, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", px)
    except OSError:
        return ImageFont.load_default()


def rounded(d, box, fill, r=10):
    d.rounded_rectangle(box, radius=r, fill=fill)


def pad(d, xy, label, role, used, fonts):
    x, y = xy
    col = C[role]
    d.ellipse((x, y, x + 16, y + 16), fill=col, outline=(0, 0, 0))
    tag = label if label in ("5V", "GND", "3V3") else f"GP{label}" if label.isdigit() else label
    text = f"{tag}  {used}" if used else tag
    d.text((x + 22, y), text, font=fonts["sm"], fill=INK if used else MUTED)


def board(d, x, y, title, left, right, fonts, usb=True):
    rounded(d, (x, y, x + 220, y + 540), (25, 55, 130), 16)
    d.rounded_rectangle((x + 70, y - 8, x + 150, y + 28), radius=6, fill=(40, 40, 45), outline=(180, 180, 180))
    d.text((x + 88, y + 4), "USB-C", font=fonts["tiny"], fill=INK)
    d.text((x + 48, y + 36), title, font=fonts["sm"], fill=(200, 220, 255))
    if usb:
        d.rectangle((x + 40, y + 58, x + 78, y + 78), fill=(60, 60, 70))
        d.text((x + 44, y + 62), "BOOT", font=fonts["tiny"], fill=MUTED)
        d.rectangle((x + 142, y + 58, x + 180, y + 78), fill=(60, 60, 70))
        d.text((x + 148, y + 62), "RUN", font=fonts["tiny"], fill=MUTED)
    ly, ry = y + 90, y + 90
    if left:
        for lab, used, role in left:
            pad(d, (x - 130, ly), lab, role, used, fonts)
            d.line((x - 4, ly + 9, x + 8, ly + 9), fill=C[role], width=2)
            ly += 34
    if right:
        for lab, used, role in right:
            pad(d, (x + 228, ry), lab, role, used, fonts)
            d.line((x + 212, ry + 9, x + 226, ry + 9), fill=C[role], width=2)
            ry += 28 if len(right) > 10 else 34


def card(d, x, y, w, h, title, lines, color, fonts):
    rounded(d, (x, y, x + w, y + h), CARD, 12)
    d.rectangle((x, y, x + 8, y + h), fill=color)
    d.text((x + 18, y + 10), title, font=fonts["h"], fill=color)
    yy = y + 40
    for line in lines:
        d.text((x + 18, yy), line, font=fonts["sm"], fill=INK)
        yy += 22


def main():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    fonts = {
        "h": font(22, True),
        "sm": font(14, True),
        "tiny": font(11),
        "title": font(28, True),
    }
    d.text((40, 24), "sw3518-rp2350-zero  —  solder pinout (rough)", font=fonts["title"], fill=INK)
    d.text((40, 58), "From include/pins.h  ·  Zero pin order = Waveshare wiki  ·  USB-C at TOP", font=fonts["sm"], fill=MUTED)

    board(d, 190, 95, "FRONT  (USB / buttons)", FRONT_L, FRONT_R, fonts, usb=True)
    board(d, 1020, 95, "BACK  (chip / WS2812)", None, BACK_R, fonts, usb=True)
    rounded(d, (480, 600, 900, 658), (30, 50, 32), 8)
    d.text((494, 610), "WS2812 onboard GP16 DIN", font=fonts["sm"], fill=C["led"])
    d.text((494, 632), "do not solder TFT DC here", font=fonts["tiny"], fill=C["led"])

    card(
        d,
        40,
        680,
        370,
        320,
        "1.4in ST7735 TFT",
        [
            "VCC  ->  3V3",
            "GND  ->  GND",
            "SCK  ->  GP2    FRONT",
            "MOSI ->  GP3    FRONT",
            "CS   ->  GP1    FRONT",
            "DC   ->  GP15   FRONT  (not 16)",
            "RST  ->  GP8    FRONT",
            "BL   ->  GP14   FRONT",
            "No MISO. All front edge.",
        ],
        C["tft"],
        fonts,
    )
    card(
        d,
        430,
        680,
        370,
        320,
        "SW3518 I2C  0x3C",
        [
            "SDA  ->  GP4    FRONT",
            "SCL  ->  GP5    FRONT",
            "GND  ->  GND",
            "",
            "Module silk SCK = I2C SCL",
            "not SPI clock.",
            "Share GND with the Zero.",
            "I-sense pad: DMM vs GND first.",
            "If >0.3V do NOT wire to GPIO.",
            "OK millivolts: pad-1k-GP26.",
            "Do not feed charger VBUS",
            "into 3V3.",
        ],
        C["i2c"],
        fonts,
    )
    card(
        d,
        820,
        680,
        360,
        320,
        "Buttons A / B",
        [
            "A  GP6  -> switch -> GND",
            "B  GP7  -> switch -> GND",
            "",
            "INPUT_PULLUP, active LOW",
            "Short A = next page",
            "Short B = session",
            "Hold B = clear session",
        ],
        C["btn"],
        fonts,
    )
    card(
        d,
        1200,
        680,
        360,
        320,
        "Haptic  N-FET",
        [
            "GP9 -> ~100R -> FET gate",
            "FET source -> GND",
            "FET drain  -> motor -",
            "motor +    -> 3V3 or 5V",
            "diode across motor",
            "  (cathode to +)",
            "Do not drive motor",
            "from a GPIO.",
        ],
        C["hap"],
        fonts,
    )

    out = Path(__file__).resolve().parent / "wiring-solder-guide.png"
    im.save(out, "PNG")
    print("wrote", out)


if __name__ == "__main__":
    main()
