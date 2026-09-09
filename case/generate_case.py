#!/usr/bin/env python3
"""Pocket case v5.1: SW3518S spine — tight barrel/−X, dual-tier USB/+X; TFT+Zero deck; lid A/B.
No Zero USB-C side cut (flash with lid off). Internal-only ledges (no through-wall bars).
Requires: trimesh, manifold3d, shapely, numpy (see /workspace/.cadvenv)
"""
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent

# Module / board stock (dry-fit and retune)
SW_L, SW_W, SW_H = 60.0, 22.0, 14.0
BARREL_BODY_D, BARREL_COLLAR_D = 8.0, 10.2
USB_HOUSE_W, USB_HOUSE_H = 13.2, 12.2  # stacked A/C housing (Y×Z)
USB_C_W, USB_C_H = 9.2, 3.6
USB_A_W, USB_A_H = 12.4, 5.0
ZERO_L, ZERO_W = 23.5, 18.0
TFT_OUTER_L, TFT_OUTER_W, TFT_THICK = 55.0, 34.0, 3.6
TFT_WIN_L, TFT_WIN_W, TFT_WIN_OFF_X = 35.0, 28.0, 8.0
HAP_D, HAP_DEPTH = 10.2, 2.6
BTN_D, BTN_CS_D = 4.2, 6.8
BTN_A = (52.0, 7.5)
BTN_B = (52.0, -7.5)
MOUNT_INSET = 2.5
MOUNT_HOLE_D = 2.2

WALL, GAP, CORNER_R, FLOOR = 1.6, 0.35, 3.0, 1.5
DECK_GAP, DECK_PLATE, LID_H = 0.8, 2.4, 2.8
END_LIP = 1.0
OUTER_L = SW_L + 2 * END_LIP  # 62
OUTER_W = 37.9
BOTTOM_H = FLOOR + SW_H + DECK_GAP + DECK_PLATE + TFT_THICK  # 22.3
SHELL_H = BOTTOM_H + LID_H - 1.05  # assembled with lip nest ≈ 25.1
CAV_L = OUTER_L - 2 * END_LIP
CAV_W = OUTER_W - 2 * WALL


def round_rect(length, width, radius):
    l2, w2 = length / 2, width / 2
    r = min(radius, l2 - 0.05, w2 - 0.05)
    return unary_union([
        sbox(-l2 + r, -w2 + r, l2 - r, w2 - r),
        sbox(-l2 + r, -w2, l2 - r, w2),
        sbox(-l2, -w2 + r, l2, w2 - r),
        Point(-l2 + r, -w2 + r).buffer(r), Point(l2 - r, -w2 + r).buffer(r),
        Point(-l2 + r, w2 - r).buffer(r), Point(l2 - r, w2 - r).buffer(r),
    ])


def extrude(poly, height, z0=0.0):
    m = trimesh.creation.extrude_polygon(poly, height=height)
    m.apply_translation([0, 0, z0])
    return m


def box_at(e, c):
    m = trimesh.creation.box(extents=e)
    m.apply_translation(c)
    return m


def cyl_at(r, h, c, axis='z'):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=48)
    if axis == 'x':
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    elif axis == 'y':
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation(c)
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
    sw_x0 = END_LIP
    sw_cx = sw_x0 + SW_L / 2
    sw_cy = 0.0
    tft_cx = OUTER_L / 2
    zero_cx = sw_x0 + GAP + 1.0 + ZERO_L / 2
    zero_cy = -(CAV_W / 2 - ZERO_W / 2 - GAP - 0.5)
    deck_z = FLOOR + SW_H + DECK_GAP
    tft_z = BOTTOM_H - TFT_THICK - 0.3

    outer_poly = translate(round_rect(OUTER_L, OUTER_W, CORNER_R), xoff=OUTER_L / 2, yoff=0)
    bottom_outer = extrude(outer_poly, BOTTOM_H, 0)
    cav_poly = translate(
        round_rect(CAV_L, CAV_W, max(0.8, CORNER_R - 0.5)),
        xoff=END_LIP + CAV_L / 2, yoff=0,
    )
    cavity = extrude(cav_poly, BOTTOM_H - FLOOR + 0.4, FLOOR)

    sw_bay = box_at(
        [SW_L + 2 * GAP, SW_W + 2 * GAP, SW_H + 0.6],
        [sw_cx, sw_cy, FLOOR + (SW_H + 0.6) / 2],
    )

    # Tight barrel on -X: body + collar recess (axis along X)
    barrel_z = FLOOR + 6.5
    barrel_body = cyl_at(BARREL_BODY_D / 2 + 0.25, END_LIP + 10, [END_LIP / 2 - 1.0, sw_cy, barrel_z], axis='x')
    barrel_collar = cyl_at(BARREL_COLLAR_D / 2 + 0.2, 3.5, [END_LIP + 0.5, sw_cy, barrel_z], axis='x')
    # Clearance chimney so jack isn't capped by deck
    barrel_clear = box_at(
        [END_LIP + 6, BARREL_COLLAR_D + 1.5, BOTTOM_H - barrel_z + 2],
        [END_LIP / 2, sw_cy, (barrel_z + BOTTOM_H) / 2],
    )

    # Dual-tier USB on +X: C below, A above (housing envelope + tier mouths)
    usb_z0 = FLOOR + 2.0
    usb_house = box_at(
        [END_LIP + 10, USB_HOUSE_W + 1.0, USB_HOUSE_H + 1.0],
        [OUTER_L - END_LIP / 2 + 1.0, sw_cy, usb_z0 + (USB_HOUSE_H + 1.0) / 2],
    )
    usb_c = box_at(
        [END_LIP + 12, USB_C_W + 0.8, USB_C_H + 0.6],
        [OUTER_L - END_LIP / 2 + 1.0, sw_cy, usb_z0 + 1.2 + USB_C_H / 2],
    )
    usb_a = box_at(
        [END_LIP + 12, USB_A_W + 0.6, USB_A_H + 0.6],
        [OUTER_L - END_LIP / 2 + 1.0, sw_cy, usb_z0 + 1.2 + USB_C_H + 0.8 + USB_A_H / 2],
    )
    usb_clear = box_at(
        [END_LIP + 6, USB_HOUSE_W + 2.0, BOTTOM_H - usb_z0],
        [OUTER_L - END_LIP / 2, sw_cy, (usb_z0 + BOTTOM_H) / 2],
    )

    haptic = cyl_at(HAP_D / 2, HAP_DEPTH + 0.8, [zero_cx + 3, zero_cy, deck_z + 0.3])
    zero_pocket = box_at(
        [ZERO_L + 2 * GAP, ZERO_W + 2 * GAP, 2.0],
        [zero_cx, zero_cy, deck_z + HAP_DEPTH + 1.0],
    )
    # NO Zero USB-C side cut (v5.1) — flash with lid off
    tft_pocket = box_at(
        [TFT_OUTER_L + 2 * GAP, TFT_OUTER_W + 2 * GAP, TFT_THICK + 1.2],
        [tft_cx, 0.0, tft_z + (TFT_THICK + 1.2) / 2],
    )

    # Cap clearance wells under deck (electrolytics on SW3518)
    cap1 = cyl_at(4.0, 3.5, [sw_cx - 18, sw_cy + 6, FLOOR + SW_H - 1.0])
    cap2 = cyl_at(4.0, 3.5, [sw_cx - 18, sw_cy - 6, FLOOR + SW_H - 1.0])
    cap3 = cyl_at(3.5, 3.0, [sw_cx + 16, sw_cy + 5, FLOOR + SW_H - 1.0])

    # I2C / cable chimney between Zero and SW bay (internal, not through long wall)
    chimney = box_at(
        [5.0, 4.0, SW_H + DECK_GAP + 1.5],
        [sw_cx - 8, SW_W / 2 + GAP + 1.5, FLOOR + (SW_H + DECK_GAP) / 2],
    )

    # Mount holes for SW3518 corners (blind bosses later)
    holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        holes.append(cyl_at(MOUNT_HOLE_D / 2, FLOOR + 1.2, [hx, hy, FLOOR / 2]))

    bottom = diff(
        bottom_outer, cavity, sw_bay,
        barrel_body, barrel_collar, barrel_clear,
        usb_house, usb_c, usb_a, usb_clear,
        haptic, zero_pocket, tft_pocket,
        cap1, cap2, cap3, chimney, *holes,
    )

    # Internal-only ledges: keep Y well inside outer wall (clearance ≥ WALL)
    # Outer half-width 18.95; inner cavity half ≈ CAV_W/2 = 17.35; ledge near |Y|≈15–16
    ledge_y = SW_W / 2 + GAP - 0.2  # ~10.9 — seat under SW
    # Actually seat rails along SW long edges inside bay:
    sw_rail_y = SW_W / 2 + GAP - 0.9  # inside bay wall
    tft_rail_y = min(TFT_OUTER_W / 2 + GAP - 1.0, CAV_W / 2 - WALL - 0.5)
    # Clamp so rails never reach outer skin
    max_inner_y = CAV_W / 2 - 0.8  # ≥0.8mm inside cavity face → ≥ WALL+0.8 from outer
    sw_rail_y = min(sw_rail_y, max_inner_y)
    tft_rail_y = min(tft_rail_y, max_inner_y)

    rails = [
        box_at([SW_L - 6, 1.6, 1.2], [sw_cx, -sw_rail_y, FLOOR + 0.8]),
        box_at([SW_L - 6, 1.6, 1.2], [sw_cx, sw_rail_y, FLOOR + 0.8]),
        box_at([TFT_OUTER_L - 8, 2.0, 1.4], [tft_cx, -tft_rail_y, tft_z - 0.7]),
        box_at([TFT_OUTER_L - 8, 2.0, 1.4], [tft_cx, tft_rail_y, tft_z - 0.7]),
    ]
    # Low deck shelf strips under Zero/TFT (internal)
    deck_shelf = box_at(
        [CAV_L - 4, CAV_W - 2 * WALL - 1.0, 1.2],
        [END_LIP + CAV_L / 2, 0.0, deck_z - 0.4],
    )
    # Punch deck shelf with SW bay / chimney so it doesn't bridge wrongly
    deck_shelf = diff(
        deck_shelf,
        box_at([SW_L + 2 * GAP + 1, SW_W + 2 * GAP + 1, 3], [sw_cx, sw_cy, deck_z]),
    )

    # Mount bosses (rings) around holes — internal
    bosses = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        bosses.append(cyl_at(3.2, 2.0, [hx, hy, FLOOR + 1.0]))
    bosses = [diff(b, cyl_at(MOUNT_HOLE_D / 2, 3.0, b.centroid)) for b in bosses]

    bottom = union(bottom, *rails, deck_shelf, *bosses)

    # --- Lid: screen window + A/B beside screen; port relief at ends ---
    win_cx = tft_cx - TFT_OUTER_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2
    lid = diff(
        extrude(outer_poly, LID_H, 0),
        box_at([TFT_WIN_L + 0.4, TFT_WIN_W + 0.4, LID_H + 2], [win_cx, 0, LID_H / 2]),
        box_at([TFT_WIN_L + 1.8, TFT_WIN_W + 1.8, 0.7], [win_cx, 0, LID_H - 0.25]),
        box_at([4.0, BARREL_COLLAR_D + 2, LID_H + 1], [1.5, 0, LID_H / 2]),
        box_at([4.0, USB_HOUSE_W + 2, LID_H + 1], [OUTER_L - 1.5, 0, LID_H / 2]),
        cyl_at(BTN_D / 2, LID_H + 2, [BTN_A[0], BTN_A[1], LID_H / 2]),
        cyl_at(BTN_D / 2, LID_H + 2, [BTN_B[0], BTN_B[1], LID_H / 2]),
        cyl_at(BTN_CS_D / 2, 0.9, [BTN_A[0], BTN_A[1], LID_H - 0.35]),
        cyl_at(BTN_CS_D / 2, 0.9, [BTN_B[0], BTN_B[1], LID_H - 0.35]),
    )

    lip_h = 1.2
    lip = extrude(
        translate(round_rect(CAV_L - 1.0, CAV_W - 1.0, max(0.6, CORNER_R - 0.8)),
                  xoff=END_LIP + CAV_L / 2, yoff=0),
        lip_h, -lip_h + 0.15,
    )
    lip_cut = extrude(
        translate(round_rect(CAV_L - 2.6, CAV_W - 2.6, max(0.4, CORNER_R - 1.2)),
                  xoff=END_LIP + CAV_L / 2, yoff=0),
        lip_h + 0.4, -lip_h,
    )
    lip = diff(
        lip,
        box_at([10, CAV_W, lip_h + 1], [END_LIP + 2, 0, -lip_h / 2]),
        box_at([10, CAV_W, lip_h + 1], [OUTER_L - END_LIP - 2, 0, -lip_h / 2]),
    )
    lid = union(lid, diff(lip, lip_cut))

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

    meta = {
        'version': '5.1',
        'fixes': [
            'Removed Zero USB-C side cut (was the random corner bite); flash with lid off',
            'Ledges internal only — no bars through long side walls',
        ],
        'layout': 'SW3518 flush ends; snug barrel circle + dual-tier USB; lid A/B; no side USB cut',
        'sw3518': {
            'pcb': [SW_L, SW_W, SW_H],
            'barrel_body_d': BARREL_BODY_D,
            'barrel_collar_d': BARREL_COLLAR_D,
            'usb_housing': [USB_HOUSE_W, USB_HOUSE_H],
            'mount_holes_inset': MOUNT_INSET,
            'cap_wells': True,
        },
        'print_outer_mm': {
            'body': [round(OUTER_L, 2), round(OUTER_W, 2), round(BOTTOM_H + LID_H - 1.05, 2)],
            'bottom_h': round(BOTTOM_H, 2),
            'lid_h': LID_H,
        },
        'ports': {
            'barrel': 'tight circular -X',
            'usb': 'dual-tier A/C +X',
        },
        'lid_buttons': {'A': list(BTN_A), 'B': list(BTN_B), 'hole_d': BTN_D},
    }
    (OUT / 'case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported', OUT)
    print('bottom extents', bottom.extents, 'watertight', bottom.is_watertight)
    print('lid extents', lid_print.extents, 'watertight', lid_print.is_watertight)


if __name__ == '__main__':
    main()
