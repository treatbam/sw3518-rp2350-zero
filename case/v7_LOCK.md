# v7 caliper lock (STEP rebuild)

**Master:** `case/v7_lock.json` — freeze date 2026-09-09.  
**Do not** import `v62_*.stl` as the CAD master (reference only).

## Parts
base · mid · lid · tft_tray · optional TPU button pad · optional Zero retainer clip

## Hard numbers
| Item | mm |
|------|-----|
| SW3518 PCB | 57 × 22 × 1.6 |
| Cap bores | Ø7.25 × 18 deep (2×) |
| Inductor pocket | 12.9² (part 12.5² × 9 H) |
| Heatsink pocket | 7.4² (keepout 7³) |
| Barrel body | 13 × 11 × 11; +4 past PCB; +X |
| USB stack | +2 past PCB; −X; C under A |
| Zero | 23.5 × 18; no screw holes; snug pocket + USB detent |
| TFT outer | 55 × 34 × 3.6; window 35 × 28 |
| Button holes | Ø4.2 aligned pair beside bezel |
| PETG pocket clear | ~0.25 / side |
| Wall / gap | 1.6 / 0.40 |
| Port mouths | **Open-top U-slots** from PCB plane (USB −X ~13.2×12.2, barrel +X ~13×11) — NOT closed tunnels |
| Assembly | Top-drop PCB-up; caps locate; ports drop through U-slots |

## Port cuts (do not regress)
USB/−X and barrel/+X are **open-top U-channels** from the PCB plane down so +2/+4 mm overhangs top-drop. Glove wells stay closed.

## Print gate
1. Base only → dry-fit SW3518 glove  
2. Mid → Zero pocket + ports  
3. Lid + tray  

@Code Troubleshooter: amend pinout/clearance notes here if anything’s off.  
@Creative CAD Master: sketch from this lock only → `case/v7_step/` (STEP + STL per part).

## Wiring / clearance (CT amend)
| Bus | Pins | Notes |
|-----|------|-------|
| I2C SW3518 | GP4 SDA, GP5 SCL (`0x3C`) | Silk `SCK` = SCL; exit +Y |
| TFT SPI | 18/19/17/16/20/21 | 6-wire bundle Zero → lid tray |
| Buttons | GP6 A, GP7 B | Active LOW pullup |
| Haptic | GP9 | N-FET; optional well |

Flex channel ≥ **10 × 3 mm** on +Y; **~25 mm** slack so lid lifts off without yanking joints.
Do not invade the 57×22 PCB envelope except glove wells + port tunnels.

