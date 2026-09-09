#!/usr/bin/env python3
"""Pocket case for SW3518 + Waveshare RP2350-Zero + 1.8\" ST7735.

Parametric printable shell:
  - RP2350-Zero pocket (~18 x 23.5 mm PCB) with USB-C access
  - 1.8\" ST7735 module pocket (tunable outer + screen window)
  - SW3518S bay (~60 x 22 x 14): barrel OUT +X end (flared), USB-A/C OUT +Y side
  - 2x side 6x6 tact button holes (no push rods)
  - ~10 mm coin haptic pocket under/near Zero
  - I2C cable channel Zero <-> SW3518
  - Friction lid lip + optional M2 screw bosses

No light pipes / button rods.
Requires: /workspace/.cadvenv with trimesh, manifold3d, shapely, numpy
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent

# --- tunable stock refs (mm) ---
# Waveshare RP2350-Zero PCB ~18 x 23.5 x 1; USB-C hangs off one short edge
ZERO_L, ZERO_W = 23.5, 18.0
ZERO_USB_OVERHANG = 2.5  # USB-C past PCB edge
ZERO_USB_W, ZERO_USB_H = 9.2, 3.4

# Common 1.8\" ST7735 module outer; active area ~28 x 35 — tune after dry-fit
TFT_OUTER_L = 55.0   # module length along case X (range ~47.5–58)
TFT_OUTER_W = 34.0
TFT_THICK = 3.6
TFT_WIN_L = 35.0     # screen window (active-ish)
TFT_WIN_W = 28.0
TFT_WIN_OFF_X = 8.0  # window inset from TFT pocket -X (connector/flex end)

# SW3518S barrel-jack + stacked USB-A/C module (user photo / common DIY board)
# Published variants ~49-65 L x 17-22 W x ~12 H; barrel versions often ~57x22.
# Sized with clearance for electrolytics + stacked A-over-C. Dry-fit still wise.
SW_L, SW_W, SW_H = 60.0, 22.0, 14.0
# Orientation in case: board length along X; barrel faces +X (case end);
# stacked USB-A/C faces +Y (long side) for easy plugs.
SW_USB_FACE_W, SW_USB_FACE_H = 16.0, 14.0   # stacked A-over-C mouth
SW_BARREL_SLOT_W = 14.0                     # wide mouth for DC plug + fingers
SW_BARREL_SLOT_H = 12.0
SW_BARREL_FLARE = 6.0                       # outer flare depth past wall

HAP_D, HAP_DEPTH = 10.2, 2.8
BTN_D = 6.4          # 6x6 tact hole (slight clearance)
BTN_Z = None         # filled after FLOOR known

WALL, GAP, CORNER_R = 1.6, 0.35, 3.0
FLOOR = 1.6
LID_H = 2.8
CHANNEL_W, CHANNEL_H = 6.0, 4.0

# Layout along X (length): Zero+TFT zone, then cable channel, then SW3518 bay
ZONE_TFT_L = max(TFT_OUTER_L, ZERO_L + ZERO_USB_OVERHANG + 4.0) + 2 * GAP
ZONE_CH_L = 8.0
ZONE_SW_L = SW_L + 2 * GAP

CAV_L = ZONE_TFT_L + ZONE_CH_L + ZONE_SW_L
CAV_W = max(TFT_OUTER_W, SW_W + 8.0, ZERO_W) + 2 * GAP + 2.0  # +8 for side USB stack
OUTER_L = CAV_L + 2 * WALL
OUTER_W = CAV_W + 2 * WALL

# Bottom tall enough for SW3518 bay + TFT ledge near top
BOTTOM_H = FLOOR + SW_H + 1.2  # ~14.8
SHELL_H = BOTTOM_H + LID_H

# M2 screw bosses (optional; friction lip is primary)
BOSS_R_OUTER, BOSS_R_INNER, BOSS_H = 3.2, 1.05, 4.0


def round_rect(length, width, radius):
    l2, w2 = length / 2, width / 2
    r = min(radius, l2 - 0.05, w2 - 0.05)
    return unary_union([
        sbox(-l2 + r, -w2 + r, l2 - r, w2 - r),
        sbox(-l2 + r, -w2, l2 - r, w2),
        sbox(-l2, -w2 + r, l2, w2 - r),
        Point(-l2 + r, -w2 + r).buffer(r),
        Point(l2 - r, -w2 + r).buffer(r),
        Point(-l2 + r, w2 - r).buffer(r),
        Point(l2 - r, w2 - r).buffer(r),
    ])


def extrude(poly, height, z0=0.0):
    mesh = trimesh.creation.extrude_polygon(poly, height=height)
    mesh.apply_translation([0, 0, z0])
    return mesh


def box_at(extents, center):
    m = trimesh.creation.box(extents=extents)
    m.apply_translation(center)
    return m


def cyl_at(r, h, center, axis='z'):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=48)
    if axis == 'y':
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    elif axis == 'x':
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation(center)
    return m


def diff(a, *bs):
    out = a
    for b in bs:
        out = trimesh.boolean.difference([out, b], engine='manifold', check_volume=False)
        if isinstance(out, list):
            out = trimesh.util.concatenate(out)
    return out


def union(*ms):
    out = ms[0]
    for m in ms[1:]:
        out = trimesh.boolean.union([out, m], engine='manifold', check_volume=False)
        if isinstance(out, list):
            out = trimesh.util.concatenate(out)
    return out


def main():
    # Coordinate system: X along length (Zero USB-C at -X), Y width, Z up.
    # Cavity starts at x=WALL.
    x0 = WALL
    tft_zone_cx = x0 + ZONE_TFT_L / 2
    ch_cx = x0 + ZONE_TFT_L + ZONE_CH_L / 2
    sw_cx = x0 + ZONE_TFT_L + ZONE_CH_L + ZONE_SW_L / 2

    # Zero sits in TFT zone near -X; USB-C faces -X wall
    zero_cx = x0 + GAP + ZERO_USB_OVERHANG + ZERO_L / 2
    zero_cy = 0.0

    # TFT module pocket centered in TFT zone (slightly toward +X if Zero USB needs room)
    tft_cx = x0 + ZONE_TFT_L / 2
    tft_cy = 0.0

    # Screen window relative to TFT pocket
    win_cx = tft_cx - TFT_OUTER_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2

    btn_z = FLOOR + 6.0
    btn_x = tft_cx  # side buttons beside TFT/Zero area

    outer_poly = translate(round_rect(OUTER_L, OUTER_W, CORNER_R), xoff=OUTER_L / 2, yoff=0)
    bottom_outer = extrude(outer_poly, BOTTOM_H, 0)

    # Main open cavity (stops below lid seat)
    cav_poly = translate(
        round_rect(CAV_L, CAV_W, max(0.8, CORNER_R - 0.5)),
        xoff=WALL + CAV_L / 2, yoff=0,
    )
    cavity = extrude(cav_poly, BOTTOM_H - FLOOR + 0.5, FLOOR)

    # --- feature cuts ---
    # Zero USB-C access through -X wall
    usb_cut = box_at(
        [WALL + 6, ZERO_USB_W + 0.8, ZERO_USB_H + 0.8],
        [WALL / 2, zero_cy, FLOOR + HAP_DEPTH + 1.2 + ZERO_USB_H / 2],
    )
    # Extra outer flare so the connector seats
    usb_flare = box_at(
        [4.0, ZERO_USB_W + 1.6, ZERO_USB_H + 1.4],
        [-1.0, zero_cy, FLOOR + HAP_DEPTH + 1.2 + ZERO_USB_H / 2],
    )

    # Haptic pocket under/near Zero (into floor)
    haptic = cyl_at(
        HAP_D / 2, HAP_DEPTH + 1.0,
        [zero_cx + 2.0, zero_cy, FLOOR - HAP_DEPTH / 2 + 0.25],
    )

    # Zero board shelf / pocket outline (shallow recess above haptic)
    zero_pocket = box_at(
        [ZERO_L + 2 * GAP, ZERO_W + 2 * GAP, 2.2],
        [zero_cx, zero_cy, FLOOR + HAP_DEPTH + 1.1],
    )

    # TFT module bay: open from mid-height so module sits on ledges
    tft_ledge_z = BOTTOM_H - TFT_THICK - 0.4
    tft_pocket = box_at(
        [TFT_OUTER_L + 2 * GAP, TFT_OUTER_W + 2 * GAP, TFT_THICK + 1.5],
        [tft_cx, tft_cy, tft_ledge_z + (TFT_THICK + 1.5) / 2],
    )

    # SW3518 rectangular bay (deep). Shift board slightly toward -Y so USB stack
    # has room to face +Y wall without crowding the opposite wall.
    sw_cy = -2.0
    sw_bay = box_at(
        [SW_L + 2 * GAP, SW_W + 2 * GAP, SW_H + 0.8],
        [sw_cx, sw_cy, FLOOR + (SW_H + 0.8) / 2],
    )
    # DC barrel OUT the +X case end — large flared mouth (not a pinhole)
    barrel_z = FLOOR + 6.5
    barrel_inner = box_at(
        [WALL + 8, SW_BARREL_SLOT_W, SW_BARREL_SLOT_H],
        [OUTER_L - WALL / 2, sw_cy, barrel_z],
    )
    barrel_flare = box_at(
        [SW_BARREL_FLARE + 2, SW_BARREL_SLOT_W + 4.0, SW_BARREL_SLOT_H + 3.0],
        [OUTER_L + SW_BARREL_FLARE / 2 - 1.0, sw_cy, barrel_z],
    )
    # U-notch from top of wall so a straight DC plug seats without fighting the lid lip
    barrel_unotch = box_at(
        [WALL + SW_BARREL_FLARE + 4, SW_BARREL_SLOT_W + 2.0, BOTTOM_H],
        [OUTER_L - 1.0, sw_cy, FLOOR + BOTTOM_H / 2],
    )
    # Stacked USB-A/C OUT the +Y long side — generous window
    usb_win = box_at(
        [SW_USB_FACE_W + 2.0, WALL + 10, SW_USB_FACE_H],
        [sw_cx + SW_L * 0.28, OUTER_W / 2, FLOOR + SW_USB_FACE_H / 2 + 1.2],
    )
    usb_win_flare = box_at(
        [SW_USB_FACE_W + 4.0, 4.0, SW_USB_FACE_H + 2.0],
        [sw_cx + SW_L * 0.28, OUTER_W / 2 + 1.5, FLOOR + SW_USB_FACE_H / 2 + 1.2],
    )

    # I2C cable channel Zero <-> SW3518
    channel = box_at(
        [ZONE_CH_L + 2.0, CHANNEL_W, CHANNEL_H],
        [ch_cx, 0.0, FLOOR + CHANNEL_H / 2 + 0.5],
    )

    # Side tact button holes (6x6), no rods — finger presses the switch directly
    btn_l = cyl_at(BTN_D / 2, WALL + 8, [btn_x, -OUTER_W / 2, btn_z], axis='y')
    btn_r = cyl_at(BTN_D / 2, WALL + 8, [btn_x, OUTER_W / 2, btn_z], axis='y')
    # Shallow exterior countersink so the switch sits flush-ish
    btn_l_cs = cyl_at(BTN_D / 2 + 0.8, 1.2, [btn_x, -OUTER_W / 2 + 0.4, btn_z], axis='y')
    btn_r_cs = cyl_at(BTN_D / 2 + 0.8, 1.2, [btn_x, OUTER_W / 2 - 0.4, btn_z], axis='y')

    bottom = diff(
        bottom_outer, cavity, usb_cut, usb_flare, haptic, zero_pocket,
        tft_pocket, sw_bay, barrel_inner, barrel_flare, barrel_unotch,
        usb_win, usb_win_flare, channel, btn_l, btn_r, btn_l_cs, btn_r_cs,
    )

    # Rails under TFT / Zero so boards don't sit on the haptic
    rail_w, rail_h = 1.8, 1.2
    rail_y = (ZERO_W / 2 + GAP) - 0.2
    rail_z = FLOOR + HAP_DEPTH + 0.2
    bottom = union(
        bottom,
        box_at([ZERO_L - 2, rail_w, rail_h], [zero_cx, -rail_y, rail_z + rail_h / 2]),
        box_at([ZERO_L - 2, rail_w, rail_h], [zero_cx, rail_y, rail_z + rail_h / 2]),
    )

    # TFT side ledges (keep module from dropping into SW bay height)
    ledge_t = 1.4
    bottom = union(
        bottom,
        box_at([TFT_OUTER_L - 4, ledge_t, 1.6],
               [tft_cx, -(TFT_OUTER_W / 2 + GAP - ledge_t / 2), tft_ledge_z - 0.8]),
        box_at([TFT_OUTER_L - 4, ledge_t, 1.6],
               [tft_cx, (TFT_OUTER_W / 2 + GAP - ledge_t / 2), tft_ledge_z - 0.8]),
    )

    # Optional M2 screw bosses near corners of TFT zone
    boss_pts = [
        (x0 + 6.0, -CAV_W / 2 + 5.0),
        (x0 + ZONE_TFT_L - 4.0, CAV_W / 2 - 5.0),
    ]
    for bx, by in boss_pts:
        boss = cyl_at(BOSS_R_OUTER, BOSS_H, [bx, by, FLOOR + BOSS_H / 2])
        hole = cyl_at(BOSS_R_INNER, BOSS_H + 2, [bx, by, FLOOR + BOSS_H / 2])
        bottom = union(bottom, diff(boss, hole))

    # --- lid ---
    lid_outer = extrude(outer_poly, LID_H, 0)
    lid = diff(
        lid_outer,
        # Screen window
        box_at([TFT_WIN_L + 0.4, TFT_WIN_W + 0.4, LID_H + 2], [win_cx, 0.0, LID_H / 2]),
        # Shallow outer bezel recess
        box_at([TFT_WIN_L + 1.8, TFT_WIN_W + 1.8, 0.7], [win_cx, 0.0, LID_H - 0.25]),
        # Zero USB-C top relief at -X
        box_at([3.0, ZERO_USB_W + 1.0, 1.6], [1.2, 0.0, LID_H - 0.4]),
        # Barrel mouth top relief at +X
        box_at([4.0, SW_BARREL_SLOT_W + 3.0, LID_H + 1], [OUTER_L - 1.5, -2.0, LID_H / 2]),
        # Side USB window top relief (+Y)
        box_at([SW_USB_FACE_W + 3.0, 4.0, LID_H + 1],
               [WALL + ZONE_TFT_L + ZONE_CH_L + ZONE_SW_L * 0.65, OUTER_W / 2 - 1.0, LID_H / 2]),
    )

    # Friction lip
    lip_h = 1.3
    lip = extrude(
        translate(round_rect(CAV_L - 1.0, CAV_W - 1.0, max(0.6, CORNER_R - 0.8)),
                  xoff=WALL + CAV_L / 2, yoff=0),
        lip_h, -lip_h + 0.15,
    )
    lip_cut = extrude(
        translate(round_rect(CAV_L - 2.6, CAV_W - 2.6, max(0.4, CORNER_R - 1.2)),
                  xoff=WALL + CAV_L / 2, yoff=0),
        lip_h + 0.4, -lip_h,
    )
    # Clear lip over SW bay / USB so it seats
    lip = diff(
        lip,
        box_at([ZONE_SW_L + 2, CAV_W - 1.5, lip_h + 1], [sw_cx, 0, -lip_h / 2]),
        box_at([8, ZERO_USB_W + 2, lip_h + 1], [x0 + 2, 0, -lip_h / 2]),
    )
    lid = union(lid, diff(lip, lip_cut))

    # M2 clearance holes in lid above bosses
    for bx, by in boss_pts:
        lid = diff(lid, cyl_at(BOSS_R_INNER + 0.15, LID_H + lip_h + 2,
                               [bx, by, LID_H / 2 - lip_h / 2]))

    # Print orientation: lid outer face down
    lid_print = lid.copy()
    T = np.eye(4)
    T[2, 2] = -1
    T[2, 3] = lid.bounds[0][2] + lid.bounds[1][2]
    lid_print.apply_transform(T)
    lid_print.apply_translation([0, 0, -lid_print.bounds[0][2]])
    bottom.apply_translation([0, 0, -bottom.bounds[0][2]])

    bottom.export(OUT / 'pocket_bottom.stl')
    lid_print.export(OUT / 'pocket_lid.stl')

    prev = lid.copy()
    prev.apply_translation([0, 0, BOTTOM_H + 8])
    union(bottom.copy(), prev).export(OUT / 'pocket_preview_exploded.stl')

    bb = bottom.bounds
    outer_dims = [
        round(float(bb[1][0] - bb[0][0]), 2),
        round(float(bb[1][1] - bb[0][1]), 2),
        round(float(SHELL_H), 2),
    ]
    meta = {
        'version': 1,
        'project': 'sw3518-rp2350-zero',
        'stock_ref_mm': {
            'rp2350_zero_pcb': [ZERO_L, ZERO_W, 1.0],
            'rp2350_zero_usb_c': [ZERO_USB_OVERHANG, ZERO_USB_W, ZERO_USB_H],
            'tft_module_outer': [TFT_OUTER_L, TFT_OUTER_W, TFT_THICK],
            'tft_window': [TFT_WIN_L, TFT_WIN_W],
            'sw3518s_bay_approx': [SW_L, SW_W, SW_H],
            'haptic_coin_d': HAP_D,
            'tact_button': '6x6mm holes, no rods',
        },
        'print_outer_mm': {
            'body': outer_dims,
            'bottom_h': round(BOTTOM_H, 2),
            'lid_h': round(LID_H, 2),
            'wall': WALL,
            'corner_r': CORNER_R,
        },
        'layout': {
            'x_order': ['zero_usb_c', 'tft_plus_zero', 'i2c_channel', 'sw3518_bay_ports'],
            'buttons': 'side tact holes at TFT zone',
            'lid': 'friction lip + 2x M2 bosses',
        },
        'assumptions': [
            'SW3518S bay 50x30x12 mm is approximate — dry-fit and retune SW_L/W/H',
            'TFT outer 34.0 x 55.0 mm (common 1.8\" class; modules vary 47.5–58 length)',
            'Screen window ~28 x 35 active-ish; tune TFT_WIN_* / TFT_WIN_OFF_X',
            'RP2350-Zero ~18 x 23.5 mm PCB with USB-C on short edge',
        ],
        'omitted': ['light_pipes', 'button_rods', 'button_caps'],
        'tune': ['GAP', 'TFT_OUTER_L', 'TFT_OUTER_W', 'TFT_WIN_L', 'TFT_WIN_W',
                 'TFT_WIN_OFF_X', 'SW_L', 'SW_W', 'SW_H', 'HAP_D'],
    }
    (OUT / 'case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported', OUT)
    print('outer_mm', outer_dims)


if __name__ == '__main__':
    main()
