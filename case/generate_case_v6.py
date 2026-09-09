#!/usr/bin/env python3
"""Pocket case v6 sandwich (caliper-driven draft).

Stack (Z up):
  1) base — SOLID glove block to PCB underside (wells/ports only; no stilts) + flush dual USB/−X & barrel/+X
  2) mid_plate — clamps SW3518 (PCB-up) and carries RP2350-Zero; permanent mid-side USB notch
  3) lid — independent TFT + A/B tray (detachable; flex SPI/I2C)

Derek calipers (2026-09-09): PCB 57×22; caps Ø6.5 / 18 Z; inductor 12.5² / 9 Z;
barrel body 13×11×11, +4 past edge; USB A+C +2 past edge; USB-A ~8 H.
Tunable: barrel OD/collar, mount insets, Zero USB stick-out.

Requires: trimesh, manifold3d, shapely, numpy (/workspace/.cadvenv)
"""
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent

# --- calipers / stock ---
SW_L, SW_W, SW_PCB_T = 57.0, 22.0, 1.6
CAP_D, CAP_H = 6.5, 18.0
CAP_CLEAR = 0.5
CAP_BORE_D = 7.25  # glove fit for Ø6.5 caps (~0.75 diametral; PETG ~7.0–7.25)
IND_XY, IND_H = 12.5, 9.0
IND_CLEAR = 0.5
IND_BORE = 12.9  # glove pocket for 12.5² (~0.4 per side)
HS_XY, HS_H, HS_CLEAR = 7.0, 7.0, 0.5  # SW3518 IC heatsink keepout
HS_BORE = 7.4  # glove pocket for 7² heatsink
BARREL_L, BARREL_W, BARREL_H = 13.0, 11.0, 11.0
BARREL_PAST = 4.0  # past PCB edge
BARREL_OD, BARREL_COLLAR_OD = 8.0, 10.2  # tunable
USB_PAST = 2.0
USB_HOUSE_W, USB_HOUSE_H = 13.2, 12.2
USB_A_H, USB_C_H = 8.0, 3.6
USB_A_W, USB_C_W = 12.4, 9.2
MOUNT_INSET, MOUNT_D = 2.8, 2.2  # ~2–3 mm from photos
ZERO_L, ZERO_W, ZERO_T = 23.5, 18.0, 1.0
ZERO_USB_STICK = 9.0  # notch depth from outer wall, tunable
ZERO_USB_W, ZERO_USB_H = 9.2, 3.4
TFT_L, TFT_W, TFT_T = 55.0, 34.0, 3.6
TFT_WIN_L, TFT_WIN_W, TFT_WIN_OFF_X = 35.0, 28.0, 8.0
BTN_D, BTN_CS = 4.2, 6.8
HAP_D, HAP_DEPTH = 10.2, 2.6

WALL, GAP, CORNER_R = 1.6, 0.40, 3.0
FLOOR = 1.8
WELL_PAD = 1.0  # extra floor under wells
MID_T = 2.4
LID_H = 2.8
LIP_H = 1.2
DECK_AIR = 1.5  # flex/air between mid and lid

WELL_Z = max(CAP_H + CAP_CLEAR, IND_H + IND_CLEAR, HS_H + HS_CLEAR, BARREL_H + 1.0)  # caps 18 still win
BASE_SOLID_H = FLOOR + WELL_PAD + WELL_Z  # PCB underside
BASE_H = BASE_SOLID_H + SW_PCB_T + 1.2  # + rim
END_LIP = max(BARREL_PAST, USB_PAST) + 0.8  # ~4.8
OUTER_L = SW_L + 2 * END_LIP
OUTER_W = max(TFT_W, SW_W) + 2 * WALL + 2 * GAP + 2.0  # room for Zero beside
CAV_L = OUTER_L - 2 * WALL
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
    sw_cx = OUTER_L / 2
    sw_cy = 0.0
    outer_poly = translate(round_rect(OUTER_L, OUTER_W, CORNER_R), xoff=OUTER_L / 2, yoff=0)


    # ----- BASE -----
    # Solid block up to PCB underside: glove negatives only (no open cavity / stilts).
    pcb_bottom_z = FLOOR + WELL_PAD + WELL_Z
    mid_z0 = pcb_bottom_z + SW_PCB_T + 0.2
    # Rim above PCB for registration (short walls), solid fill below
    base_solid_h = pcb_bottom_z  # top face = PCB underside
    rim_h = SW_PCB_T + 1.2
    base_outer = extrude(outer_poly, base_solid_h + rim_h, 0)

    # Glove-fit wells (open from top of solid down)
    cap_well_h = CAP_H  # 18 mm
    ind_well_h = IND_H + 0.3
    hs_well_h = HS_H + 0.3
    # Wells must reach the top of the solid so PCB drops in; deepen from top
    def well_from_top(shape_maker, depth):
        # top of solid at z=base_solid_h; well extends down `depth`
        z_c = base_solid_h - depth / 2
        return shape_maker(z_c, depth)

    wells = [
        cyl_at(CAP_BORE_D / 2, cap_well_h + 0.2,
               [sw_cx + 4.0, sw_cy - 6.5, base_solid_h - cap_well_h / 2]),
        cyl_at(CAP_BORE_D / 2, cap_well_h + 0.2,
               [sw_cx + 18.0, sw_cy + 6.5, base_solid_h - cap_well_h / 2]),
        box_at([IND_BORE, IND_BORE, ind_well_h + 0.2],
               [sw_cx + 14.0, sw_cy - 5.0, base_solid_h - ind_well_h / 2]),
        box_at([HS_BORE, HS_BORE, hs_well_h + 0.2],
               [sw_cx - 12.0, sw_cy + 2.5, base_solid_h - hs_well_h / 2]),
    ]

    # PCB outline pocket in the rim (board drops flush onto solid top)
    pcb_pocket = box_at(
        [SW_L + 2 * GAP, SW_W + 2 * GAP, rim_h + 0.4],
        [sw_cx, sw_cy, base_solid_h + rim_h / 2],
    )

    # Port tunnels through solid (USB -X, barrel +X)
    barrel_z = base_solid_h - BARREL_H / 2 - 0.5
    barrel_cut = box_at(
        [END_LIP + BARREL_L + 4, BARREL_W + 1.0, BARREL_H + 1.2],
        [OUTER_L - END_LIP / 2, sw_cy, barrel_z],
    )
    barrel_cyl = cyl_at(BARREL_OD / 2 + 0.3, END_LIP + BARREL_PAST + 8,
                        [OUTER_L - END_LIP / 2 + 1, sw_cy, barrel_z], axis='x')
    barrel_collar = cyl_at(BARREL_COLLAR_OD / 2 + 0.25, 3.0,
                           [OUTER_L - END_LIP - 1.0, sw_cy, barrel_z], axis='x')

    usb_z_c = base_solid_h - 1.5 - USB_C_H / 2
    usb_house = box_at(
        [END_LIP + 12, USB_HOUSE_W + 1.0, USB_HOUSE_H + 1.0],
        [END_LIP / 2, sw_cy, base_solid_h - (USB_HOUSE_H + 1) / 2],
    )
    usb_c = box_at([END_LIP + 14, USB_C_W + 0.8, USB_C_H + 0.6],
                   [END_LIP / 2, sw_cy, usb_z_c])
    usb_a = box_at([END_LIP + 14, USB_A_W + 0.6, USB_A_H + 0.6],
                   [END_LIP / 2, sw_cy, usb_z_c - USB_C_H / 2 - 0.6 - USB_A_H / 2])

    # Mount holes through solid (no stilts)
    mount_holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mount_holes.append(cyl_at(MOUNT_D / 2, base_solid_h + rim_h + 2,
                                  [hx, hy, (base_solid_h + rim_h) / 2]))

    # I2C channel on +Y through rim / top edge (SDA/SCK)
    cable_ch = box_at([10.0, WALL + 4, rim_h + 2.0],
                      [sw_cx + 6.0, OUTER_W / 2 - WALL / 2, base_solid_h + rim_h / 2])

    # Optional lightening? No — solid glove block as Derek asked.

    base = diff(
        base_outer, pcb_pocket, *wells,
        barrel_cut, barrel_cyl, barrel_collar,
        usb_house, usb_c, usb_a,
        cable_ch, *mount_holes,
    )

    # ----- MID PLATE -----
    mid_outer = extrude(outer_poly, MID_T, 0)
    # opening over SW3518 body except clamp rim
    sw_open = box_at([SW_L - 6, SW_W - 4, MID_T + 2], [sw_cx, sw_cy, MID_T / 2])
    # Zero pocket on +Y side of mid plate
    zero_cx = sw_cx - 8
    zero_cy = CAV_W / 2 - ZERO_W / 2 - GAP - 0.5
    zero_pocket = box_at([ZERO_L + 2 * GAP, ZERO_W + 2 * GAP, MID_T + 1], [zero_cx, zero_cy, MID_T / 2])
    haptic = cyl_at(HAP_D / 2, HAP_DEPTH, [zero_cx + 2, zero_cy, MID_T - 0.2])
    # Permanent Zero USB notch on +Y (matches Zero pocket)
    zusb = box_at(
        [ZERO_USB_W + 1.2, ZERO_USB_STICK + WALL + 2, ZERO_USB_H + 1.0],
        [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2, MID_T / 2],
    )
    # screw holes aligned to SW mounts
    mid_holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mid_holes.append(cyl_at(MOUNT_D / 2 + 0.1, MID_T + 2, [hx, hy, MID_T / 2]))
    # I2C/SPI cable pass-through
    flex = box_at([10.0, 4.0, MID_T + 2], [sw_cx + 12, zero_cy - ZERO_W / 2 - 1, MID_T / 2])

    mid = diff(mid_outer, sw_open, zero_pocket, haptic, zusb, flex, *mid_holes)
    # clamp rim lips (internal) so plate isn't just a ring with no meat — add bars
    clamp = [
        box_at([SW_L - 2, 2.2, 1.2], [sw_cx, -(SW_W / 2 + 0.2), 0.4]),
        box_at([SW_L - 2, 2.2, 1.2], [sw_cx, (SW_W / 2 + 0.2), 0.4]),
    ]
    mid = union(mid, *clamp)

    # Same Zero USB notch must exist in BASE wall for assembled access
    base = diff(
        base,
        box_at(
            [ZERO_USB_W + 1.2, ZERO_USB_STICK + WALL + 2, ZERO_USB_H + 1.2],
            [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2, mid_z0 + MID_T / 2],
        ),
    )

    # ----- LID (independent TFT + buttons) -----
    lid = extrude(outer_poly, LID_H, 0)
    win_cx = OUTER_L / 2 - TFT_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2
    btn_a = (OUTER_L * 0.82, 7.5)
    btn_b = (OUTER_L * 0.82, -7.5)
    lid = diff(
        lid,
        box_at([TFT_WIN_L + 0.4, TFT_WIN_W + 0.4, LID_H + 2], [win_cx, 0, LID_H / 2]),
        box_at([TFT_WIN_L + 1.8, TFT_WIN_W + 1.8, 0.7], [win_cx, 0, LID_H - 0.25]),
        # TFT recess on underside (print flipped later)
        box_at([TFT_L + 2 * GAP, TFT_W + 2 * GAP, 1.6], [OUTER_L / 2, 0, 0.7]),
        cyl_at(BTN_D / 2, LID_H + 2, [btn_a[0], btn_a[1], LID_H / 2]),
        cyl_at(BTN_D / 2, LID_H + 2, [btn_b[0], btn_b[1], LID_H / 2]),
        cyl_at(BTN_CS / 2, 0.9, [btn_a[0], btn_a[1], LID_H - 0.35]),
        cyl_at(BTN_CS / 2, 0.9, [btn_b[0], btn_b[1], LID_H - 0.35]),
        # port relief
        box_at([5.0, USB_HOUSE_W + 3, LID_H + 1], [2.0, 0, LID_H / 2]),
        box_at([5.0, BARREL_W + 3, LID_H + 1], [OUTER_L - 2.0, 0, LID_H / 2]),
    )
    # friction posts for lid-as-tray (4 posts) — mate to mid plate holes later
    posts = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        posts.append(cyl_at(1.4, 2.0, [OUTER_L / 2 + sx * 20, sy * 12, -0.9]))
    lid = union(lid, *posts)

    lip = extrude(
        translate(round_rect(CAV_L - 1.0, CAV_W - 1.0, max(0.6, CORNER_R - 0.8)), xoff=OUTER_L / 2, yoff=0),
        LIP_H, -LIP_H + 0.15,
    )
    lip_cut = extrude(
        translate(round_rect(CAV_L - 2.6, CAV_W - 2.6, max(0.4, CORNER_R - 1.2)), xoff=OUTER_L / 2, yoff=0),
        LIP_H + 0.4, -LIP_H,
    )
    lid = union(lid, diff(lip, lip_cut))

    # print orientation: lid outer face down
    lid_print = lid.copy()
    T = np.eye(4)
    T[2, 2] = -1
    T[2, 3] = lid.bounds[0][2] + lid.bounds[1][2]
    lid_print.apply_transform(T)
    lid_print.apply_translation([0, 0, -lid_print.bounds[0][2]])

    base.apply_translation([0, 0, -base.bounds[0][2]])
    mid.apply_translation([0, 0, -mid.bounds[0][2]])

    base.export(OUT / 'v6_base.stl')
    mid.export(OUT / 'v6_mid_plate.stl')
    lid_print.export(OUT / 'v6_lid.stl')

    # exploded preview
    mid_p = mid.copy(); mid_p.apply_translation([0, 0, BASE_H + 6])
    lid_p = lid.copy(); lid_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 14])
    union(base.copy(), mid_p, lid_p).export(OUT / 'v6_preview_exploded.stl')

    shell_h = BASE_H + MID_T + DECK_AIR + LID_H
    meta = {
        'version': '6.0-draft',
        'stack': ['base (carved Z wells)', 'mid_plate (SW clamp + Zero)', 'lid (TFT+A/B tray)'],
        'calipers': {
            'pcb': [SW_L, SW_W],
            'caps_d_h': [CAP_D, CAP_H],
            'inductor_xy_h': [IND_XY, IND_H],
            'barrel_lwh': [BARREL_L, BARREL_W, BARREL_H],
            'heatsink_xy_h': [HS_XY, HS_H],
            'barrel_past_edge': BARREL_PAST,
            'usb_past_edge': USB_PAST,
            'usb_a_h': USB_A_H,
        },
        'tunable': {
            'barrel_od_collar': [BARREL_OD, BARREL_COLLAR_OD],
            'mount_inset_d': [MOUNT_INSET, MOUNT_D],
            'zero_usb_stick': ZERO_USB_STICK,
            'well_xy_note': 'XY from module photos; glove bores Ø7.25×18 caps, 12.9² inductor, 7.4² HS',
            'fit': 'glove — PETG leave ~0.2–0.4 diametral; PLA can go tighter',
        },
        'print_outer_mm': {
            'footprint': [round(OUTER_L, 2), round(OUTER_W, 2)],
            'base_h': round(BASE_H, 2),
            'mid_t': MID_T,
            'lid_h': LID_H,
            'approx_assembled_h': round(shell_h, 2),
            'well_z': round(WELL_Z, 2),
        },
        'ports': {
            'barrel': 'flush +X',
            'usb_ac': 'dual-tier flush -X (A over C)',
            'zero_usb_c': 'permanent mid-side notch through base+mid',
        },
    }
    (OUT / 'v6_case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported v6 →', OUT)
    for name, m in [('base', base), ('mid', mid), ('lid', lid_print)]:
        print(f'  {name}: extents={np.round(m.extents,2).tolist()} watertight={m.is_watertight} vol={m.volume:.0f}')


if __name__ == '__main__':
    main()
