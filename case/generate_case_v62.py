#!/usr/bin/env python3
"""Pocket instrument v6.2 — clean/simple form pass.

Derek brief: clean is paramount; simple > complex for the same goal.

Keeps:
  - Solid glove base (Ø7.25×18 caps, inductor/HS, ports — LOCKED)
  - Mid instrument deck, flex at SDA/+Y
  - Deeper scope bezel + A/B tight pair beside bezel
  - TFT rear tray with quiet snap (2 clips + catch ledges)

Sheds / cleanup:
  - Bayonet cams → perimeter click lip (no fastener)
  - Captive USB door → one clean Zero USB rectangle
  - Flexure spaghetti → plain A/B through-holes, aligned
  - Drop M2 countersink

Requires: trimesh, manifold3d, shapely, numpy
"""
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent

# --- caliper / glove (LOCKED) ---
SW_L, SW_W, SW_PCB_T = 57.0, 22.0, 1.6
CAP_D, CAP_H, CAP_BORE_D = 6.5, 18.0, 7.25
IND_XY, IND_H, IND_BORE = 12.5, 9.0, 12.9
HS_XY, HS_H, HS_BORE = 7.0, 7.0, 7.4
BARREL_L, BARREL_W, BARREL_H = 13.0, 11.0, 11.0
BARREL_PAST, BARREL_OD, BARREL_COLLAR_OD = 4.0, 8.0, 10.2
USB_PAST = 2.0
USB_HOUSE_W, USB_HOUSE_H = 13.2, 12.2
USB_A_H, USB_C_H, USB_A_W, USB_C_W = 8.0, 3.6, 12.4, 9.2
MOUNT_INSET, MOUNT_D = 2.8, 2.2
ZERO_L, ZERO_W = 23.5, 18.0
ZERO_USB_STICK, ZERO_USB_W, ZERO_USB_H = 11.0, 12.0, 8.0
TFT_L, TFT_W, TFT_T = 55.0, 34.0, 3.6
TFT_WIN_L, TFT_WIN_W, TFT_WIN_OFF_X = 35.0, 28.0, 8.0
BTN_D = 4.2
HAP_D, HAP_DEPTH = 10.2, 2.6

WALL, GAP, CORNER_R = 1.6, 0.40, 3.2
FLOOR, WELL_PAD = 1.8, 1.0
MID_T, LID_H, CART_H = 2.6, 3.4, 2.2
DECK_AIR = 1.2
WELL_Z = max(CAP_H, IND_H + 0.5, HS_H + 0.5, BARREL_H + 1.0)
BASE_SOLID_H = FLOOR + WELL_PAD + WELL_Z
RIM_H = SW_PCB_T + 1.0
BASE_H = BASE_SOLID_H + RIM_H
END_LIP = max(BARREL_PAST, USB_PAST) + 0.8
OUTER_L = SW_L + 2 * END_LIP
OUTER_W = max(TFT_W, SW_W) + 2 * WALL + 2 * GAP + 2.0
CAV_L, CAV_W = OUTER_L - 2 * WALL, OUTER_W - 2 * WALL
WAIST = 1.0
THUMB_FLAT = 1.6
CLICK_LIP_H, CLICK_LIP_T = 1.2, 0.9


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
    m = trimesh.creation.cylinder(radius=r, height=h, sections=40)
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
    sw_cx, sw_cy = OUTER_L / 2, 0.0
    mid_z0 = BASE_SOLID_H + SW_PCB_T + 0.2

    body = round_rect(OUTER_L, OUTER_W, CORNER_R)
    body = body.difference(sbox(-OUTER_L, -OUTER_W / 2 - 1, OUTER_L, -OUTER_W / 2 + THUMB_FLAT))
    outer_poly = translate(body, xoff=OUTER_L / 2, yoff=0)
    waist_poly = translate(
        round_rect(OUTER_L - 2 * WAIST, OUTER_W - 2 * WAIST - THUMB_FLAT * 0.3, CORNER_R - 0.35),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.15)

    # ===== BASE (solid glove — LOCKED wells; flat PCB plane, no invading walls) =====
    # One solid block to PCB underside. No waist rim bulkheads, no sight groove,
    # no I2C "mystery" pocket inside the board envelope.
    base = extrude(outer_poly, BASE_SOLID_H, 0)

    wells = [
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 4.0, sw_cy - 6.5, BASE_SOLID_H - CAP_H / 2]),
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 18.0, sw_cy + 6.5, BASE_SOLID_H - CAP_H / 2]),
        box_at([IND_BORE, IND_BORE, IND_H + 0.4],
               [sw_cx + 14.0, sw_cy - 5.0, BASE_SOLID_H - (IND_H + 0.2) / 2]),
        box_at([HS_BORE, HS_BORE, HS_H + 0.4],
               [sw_cx - 12.0, sw_cy + 2.5, BASE_SOLID_H - (HS_H + 0.2) / 2]),
    ]

    # Port tunnels only (keep under PCB plane; lead-ins at outer faces)
    barrel_z = BASE_SOLID_H - BARREL_H / 2 - 0.5
    barrel_bits = [
        box_at([END_LIP + BARREL_L + 4, BARREL_W + 1.0, BARREL_H + 1.2],
               [OUTER_L - END_LIP / 2, sw_cy, barrel_z]),
        cyl_at(BARREL_OD / 2 + 0.3, END_LIP + BARREL_PAST + 8,
               [OUTER_L - END_LIP / 2 + 1, sw_cy, barrel_z], axis='x'),
        cyl_at(BARREL_COLLAR_OD / 2 + 0.25, 3.0,
               [OUTER_L - END_LIP - 1.0, sw_cy, barrel_z], axis='x'),
        box_at([2.5, BARREL_W + 3.0, BARREL_H + 2.5], [OUTER_L - 1.0, sw_cy, barrel_z]),
    ]
    usb_z_c = BASE_SOLID_H - 1.5 - USB_C_H / 2
    usb_bits = [
        box_at([END_LIP + 12, USB_HOUSE_W + 1.0, USB_HOUSE_H + 1.0],
               [END_LIP / 2, sw_cy, BASE_SOLID_H - (USB_HOUSE_H + 1) / 2]),
        box_at([END_LIP + 14, USB_C_W + 0.8, USB_C_H + 0.6], [END_LIP / 2, sw_cy, usb_z_c]),
        box_at([END_LIP + 14, USB_A_W + 0.6, USB_A_H + 0.6],
               [END_LIP / 2, sw_cy, usb_z_c - USB_C_H / 2 - 0.6 - USB_A_H / 2]),
        box_at([2.5, USB_HOUSE_W + 3.0, USB_HOUSE_H + 2.5],
               [1.0, sw_cy, BASE_SOLID_H - (USB_HOUSE_H + 1) / 2]),
    ]
    mounts = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mounts.append(cyl_at(MOUNT_D / 2, BASE_SOLID_H + 2, [hx, hy, BASE_SOLID_H / 2]))

    # Tiny I2C exit on +Y outer wall ONLY (outside SW_W envelope) — not a floor pocket
    i2c_exit = box_at([8.0, WALL + 2.0, 3.0],
                      [sw_cx + 6.0, OUTER_W / 2 - WALL / 2, BASE_SOLID_H - 1.2])

    base = diff(base, *wells, *barrel_bits, *usb_bits, *mounts, i2c_exit)

    # Low registration frame OUTSIDE the 57×22 envelope (does not invade PCB)
    frame_h = 1.2
    frame_outer = extrude(outer_poly, frame_h, BASE_SOLID_H)
    frame_cut = box_at([SW_L + 2 * GAP + 0.6, SW_W + 2 * GAP + 0.6, frame_h + 0.4],
                       [sw_cx, sw_cy, BASE_SOLID_H + frame_h / 2])
    # Also clear end lips so port faces stay open through the frame
    end_clear_l = box_at([END_LIP + 1.0, SW_W + 4, frame_h + 0.6],
                         [END_LIP / 2, 0, BASE_SOLID_H + frame_h / 2])
    end_clear_r = box_at([END_LIP + 1.0, SW_W + 4, frame_h + 0.6],
                         [OUTER_L - END_LIP / 2, 0, BASE_SOLID_H + frame_h / 2])
    frame = diff(frame_outer, frame_cut, end_clear_l, end_clear_r)
    base = union(base, frame)

    # ===== MID PLATE — deck + click lip + one M2 boss =====
    mid = extrude(outer_poly, MID_T, 0)
    rail = extrude(translate(round_rect(CAV_L - 3, CAV_W - 3, CORNER_R - 1),
                             xoff=OUTER_L / 2, yoff=0), 0.7, MID_T)
    # perimeter click lip (lid seats over this)
    lip_outer = extrude(translate(
        round_rect(OUTER_L - 1.2, OUTER_W - 1.2 - THUMB_FLAT * 0.2, CORNER_R - 0.3),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.08), CLICK_LIP_H, MID_T)
    lip_inner = extrude(translate(
        round_rect(OUTER_L - 1.2 - 2 * CLICK_LIP_T,
                   OUTER_W - 1.2 - THUMB_FLAT * 0.2 - 2 * CLICK_LIP_T, CORNER_R - 0.6),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.08), CLICK_LIP_H + 0.2, MID_T - 0.05)
    click_lip = diff(lip_outer, lip_inner)
    mid = union(mid, rail, click_lip)

    sw_open = box_at([SW_L + 2 * GAP, SW_W + 2 * GAP, MID_T + CLICK_LIP_H + 2],
                     [sw_cx, sw_cy, (MID_T + CLICK_LIP_H) / 2])
    # RP2350-Zero: no mount holes — snug rectangular pocket + USB-end detent lip
    ZERO_CLEAR = 0.25  # PETG diametral-ish clearance per side
    zero_cx = sw_cx - 8
    zero_cy = CAV_W / 2 - ZERO_W / 2 - GAP - 0.5
    zero_pocket = box_at(
        [ZERO_L + 2 * ZERO_CLEAR, ZERO_W + 2 * ZERO_CLEAR, MID_T + CLICK_LIP_H + 1],
        [zero_cx, zero_cy, (MID_T + CLICK_LIP_H) / 2],
    )
    haptic = cyl_at(HAP_D / 2, HAP_DEPTH, [zero_cx + 2, zero_cy, MID_T - 0.2])

    # Clean Zero USB rectangle through +Y wall
    zero_usb = box_at(
        [ZERO_USB_W + 0.6, ZERO_USB_STICK + 2, ZERO_USB_H + 0.6],
        [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2, MID_T / 2],
    )
    # Detent lip under USB-C shell (clicks board toward +Y / USB end)
    # thin bar at USB end of pocket, proud into pocket ~0.6 mm
    usb_detent = box_at(
        [ZERO_USB_W * 0.85, 0.7, 0.9],
        [zero_cx - ZERO_L / 2 + 0.8, zero_cy, 0.45],
    )
    flex = box_at([12.0, 5.0, MID_T + CLICK_LIP_H + 2],
                  [sw_cx + 6.0, OUTER_W / 2 - 3.0, MID_T / 2])

    mid_holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mid_holes.append(cyl_at(MOUNT_D / 2 + 0.1, MID_T + 4, [hx, hy, MID_T / 2]))

    mid = diff(mid, sw_open, zero_pocket, haptic, zero_usb, flex, *mid_holes)
    mid = union(mid, usb_detent)

    base = diff(base, box_at([ZERO_USB_W + 1.5, ZERO_USB_STICK + 3, ZERO_USB_H + 2],
                             [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2,
                              mid_z0 + MID_T / 2]))

    # ===== LID — bezel, aligned A/B holes, click recess, clean USB rectangle =====
    lid = extrude(outer_poly, LID_H, 0)
    chamfer = extrude(translate(round_rect(OUTER_L + 2, OUTER_W + 2, CORNER_R),
                                xoff=OUTER_L / 2, yoff=0), 0.9, LID_H - 0.5)
    chamfer = diff(chamfer, extrude(translate(
        round_rect(OUTER_L - 2.6, OUTER_W - 2.6 - THUMB_FLAT * 0.2, CORNER_R - 0.45),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.1), 1.2, LID_H - 0.65))
    lid = diff(lid, chamfer)

    win_cx = OUTER_L / 2 - TFT_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2
    lid = diff(lid,
               box_at([TFT_WIN_L + 5.5, TFT_WIN_W + 4.5, 1.3], [win_cx - 0.3, 0.3, LID_H - 0.5]),
               box_at([TFT_WIN_L + 0.3, TFT_WIN_W + 0.3, LID_H + 2], [win_cx, 0, LID_H / 2]),
               box_at([TFT_WIN_L + 1.5, TFT_WIN_W + 1.5, 0.45], [win_cx, 0, LID_H - 1.4]))

    # A/B plain through-holes, aligned on one X beside bezel (no flexure islands)
    btn_x = win_cx + TFT_WIN_L / 2 + 9.0
    for by in (6.0, -6.0):
        lid = diff(lid, cyl_at(BTN_D / 2, LID_H + 2, [btn_x, by, LID_H / 2]))

    # Click recess on underside (mates mid lip)
    recess_outer = extrude(translate(
        round_rect(OUTER_L - 0.6, OUTER_W - 0.6 - THUMB_FLAT * 0.15, CORNER_R - 0.15),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.06), CLICK_LIP_H + 0.35, 0)
    recess_keep = extrude(translate(
        round_rect(OUTER_L - 0.6 - 2 * (CLICK_LIP_T + 0.15),
                   OUTER_W - 0.6 - THUMB_FLAT * 0.15 - 2 * (CLICK_LIP_T + 0.15),
                   CORNER_R - 0.55),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.06), CLICK_LIP_H + 0.5, -0.05)
    lid = diff(lid, diff(recess_outer, recess_keep))

    # One clean Zero USB rectangle (no stepped lead-in, no door, no M2)
    flap_x = zero_cx - ZERO_L / 2 - 1.0
    lid = diff(lid, box_at([ZERO_USB_W + 1.2, 5.0, LID_H + 2],
                           [flap_x, OUTER_W / 2 - 2.2, LID_H / 2]))

    # ===== TFT CARTRIDGE — two quiet side clips + catch ledges =====
    cart = diff(box_at([TFT_L + 3.0, TFT_W + 3.0, CART_H], [OUTER_L / 2, 0, CART_H / 2]),
                box_at([TFT_L + 2 * GAP, TFT_W + 2 * GAP, TFT_T + 0.8],
                       [OUTER_L / 2, 0, CART_H / 2]),
                box_at([TFT_WIN_L, TFT_WIN_W, CART_H + 1], [win_cx, 0, CART_H / 2]))
    clips = []
    for sy in (-1, 1):  # long edges only — simpler than 4-corner
        cx = OUTER_L / 2
        cy = sy * (TFT_W / 2 + 0.15)
        arm = box_at([8.0, 1.7, 2.0], [cx, cy, CART_H + 0.7])
        hook = box_at([6.0, 2.4, 0.85], [cx, cy + sy * 0.5, CART_H + 1.8])
        clips.append(union(arm, hook))
    cart = union(cart, *clips)

    lid = diff(lid, box_at([TFT_L + 3.4, TFT_W + 3.4, 1.9], [OUTER_L / 2, 0, 0.8]))
    for sy in (-1, 1):
        lid = union(lid, box_at([7.0, 2.6, 0.7],
                                [OUTER_L / 2, sy * (TFT_W / 2 + 0.15), 1.5]))

    lid = diff(lid,
               box_at([5.0, USB_HOUSE_W + 3, LID_H + 1], [2.0, 0, LID_H / 2]),
               box_at([5.0, BARREL_W + 3, LID_H + 1], [OUTER_L - 2.0, 0, LID_H / 2]))

    lid_print = lid.copy()
    T = np.eye(4); T[2, 2] = -1; T[2, 3] = lid.bounds[0][2] + lid.bounds[1][2]
    lid_print.apply_transform(T)
    lid_print.apply_translation([0, 0, -lid_print.bounds[0][2]])

    base.apply_translation([0, 0, -base.bounds[0][2]])
    mid.apply_translation([0, 0, -mid.bounds[0][2]])
    cart.apply_translation([0, 0, -cart.bounds[0][2]])

    base.export(OUT / 'v62_base.stl')
    mid.export(OUT / 'v62_mid_plate.stl')
    lid_print.export(OUT / 'v62_lid.stl')
    cart.export(OUT / 'v62_tft_cartridge.stl')

    # drop obsolete door if present
    door_path = OUT / 'v62_usb_door.stl'
    if door_path.exists():
        door_path.unlink()

    mid_p = mid.copy(); mid_p.apply_translation([0, 0, BASE_H + 8])
    lid_p = lid.copy(); lid_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 16])
    cart_p = cart.copy(); cart_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 22])
    union(base.copy(), mid_p, lid_p, cart_p).export(OUT / 'v62_preview_exploded.stl')

    meta = {
        'version': '6.2-cleanup',
        'form': 'pocket instrument / field meter',
        'brief': 'clean > clever; simple > complex for same goal',
        'parts': ['v62_base', 'v62_mid_plate', 'v62_lid', 'v62_tft_cartridge'],
        'features': [
            'solid glove base Ø7.25×18 / 12.9² / 7.4² (LOCKED); no walls in PCB envelope',
            'flat glove deck + thin outer registration frame (outside 57×22)',
            'thumb flat kept; sight groove / mystery rim pockets removed',
            'mid deck click lip only (no bayonet, no M2)',
            'flex at SDA/+Y hinge line',
            'deeper scope bezel + aligned A/B through-holes beside bezel',
            'TFT tray: 2 long-edge snaps + catch ledges',
            'one clean Zero USB rectangle (no door, no step)',
        ],
        'glove_locked': {
            'cap_bore_d': CAP_BORE_D, 'cap_h': CAP_H,
            'ind_bore': IND_BORE, 'hs_bore': HS_BORE,
        },
        'print_outer_mm': {
            'footprint': [round(OUTER_L, 2), round(OUTER_W, 2)],
            'base_h': round(float(base.extents[2]), 2),
            'mid_t': MID_T,
            'lid_h': LID_H,
        },
        'ports': {'usb_ac': 'flush -X', 'barrel': 'flush +X', 'zero_usb': '+Y clean lip'},
        'regen': '/workspace/.cadvenv/bin/python case/generate_case_v62.py',
    }
    (OUT / 'v62_case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported v6.2-clean →', OUT)
    for name, m in [('base', base), ('mid', mid), ('lid', lid_print), ('cart', cart)]:
        print(f'  {name}: extents={np.round(m.extents,2).tolist()} '
              f'watertight={m.is_watertight} vol={m.volume:.0f}')


if __name__ == '__main__':
    main()
