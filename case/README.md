# Pocket case (RP2350-Zero + 1.8" TFT + SW3518S)

Parametric printable shell for the portable meter. **No light pipes, no button rods/caps.**

## Print

| File | Notes |
|------|--------|
| `pocket_bottom.stl` | Main shell with Zero / TFT / SW3518 bays |
| `pocket_lid.stl` | Lid with screen window + friction lip (print outer face down) |
| `pocket_preview_exploded.stl` | Visual only |

Regenerate:

```bash
/workspace/.cadvenv/bin/python case/generate_case.py
```

## Outer size

See `case_meta.json` -> `print_outer_mm` (generated). Typical ~**118 x 40 x 18 mm** with default tunables.

## Stock assumptions (dry-fit!)

| Part | Default (mm) | Notes |
|------|--------------|--------|
| Waveshare RP2350-Zero PCB | 23.5 x 18 x 1 | USB-C on short edge; access hole in -X wall |
| 1.8" ST7735 module outer | **34.0 x 55.0 x 3.6** | Common class; length varies ~47.5-58 -- tune `TFT_OUTER_*` |
| Screen window | **28 x 35** active-ish | Tune `TFT_WIN_*` / `TFT_WIN_OFF_X` |
| SW3518S dual-port bay | **50 x 30 x 12** | **Approximate** -- dry-fit and retune `SW_L/W/H` |
| Coin haptic | O10.2 x 2.8 deep | Under/near Zero |
| Buttons | O6.4 side holes | 6x6 tact, finger-direct (no rods) |

## Features

- Rounded corners
- USB-C access for the Zero
- TFT pocket + lid window / shallow bezel
- SW3518 rectangular bay with +X port face clearance
- I2C cable channel between Zero and SW3518
- Side tact holes (A/B)
- Haptic pocket + board rails
- Friction lip lid + 2x M2 screw bosses

## Print settings

PLA for fit check, PETG for daily · 0.2 mm · 3 walls · 15-20% · supports usually off

Tune `GAP`, `TFT_OUTER_*`, `TFT_WIN_*`, `SW_*`, `HAP_D` in `generate_case.py` after a dry-fit.


### SW3518S (user module)

Barrel-jack + stacked USB-A/C. Bay ~60×22×14 mm; USB out +X; barrel on +X end, USB on +Y side. Pad `SCK` is I2C SCL.

**Case port layout (v3):** DC barrel exits the **+X end** through a wide flared mouth; stacked USB-A/C exits the **+Y long side**. Zero USB-C stays on the opposite end.
