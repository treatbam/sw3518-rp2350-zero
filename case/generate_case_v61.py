#!/usr/bin/env python3
"""Pocket instrument v6.1 — field-meter form language.

Stack:
  1) base — SOLID glove block (wells/ports only; waistline + thumb flat + sight groove)
  2) mid_plate — instrument deck + bayonet lugs; Zero pocket; flex at SDA hinge line
  3) lid — chamfered bezel face; rear snap-clip TFT cartridge; A/B flexure islands;
           bayonet ring; flush Zero USB service flap (plug + fingernail)

Calipers / glove fit from v6. Flex entry at +Y SDA edge (no twist under bayonet load).
Requires: trimesh, manifold3d, shapely, numpy
"""
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import translate, rotate as srotate

OUT = Path(__file__).resolve().parent

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
ZERO_USB_STICK, ZERO_USB_W, ZERO_USB_H = 11.0, 12.0, 8.0  # flap sized for plug + fingernail
TFT_L, TFT_W, TFT_T = 55.0, 34.0, 3.6
TFT_WIN_L, TFT_WIN_W, TFT_WIN_OFF_X = 35.0, 28.0, 8.0
BTN_D = 4.2
HAP_D, HAP_DEPTH = 10.2, 2.6

WALL, GAP, CORNER_R = 1.6, 0.40, 3.2
FLOOR, WELL_PAD = 1.8, 1.0
MID_T, LID_H, CART_H = 2.6, 3.2, 2.2
DECK_AIR = 1.2
WELL_Z = max(CAP_H, IND_H + 0.5, HS_H + 0.5, BARREL_H + 1.0)
BASE_SOLID_H = FLOOR + WELL_PAD + WELL_Z
RIM_H = SW_PCB_T + 1.0
BASE_H = BASE_SOLID_H + RIM_H
END_LIP = max(BARREL_PAST, USB_PAST) + 0.8
OUTER_L = SW_L + 2 * END_LIP
OUTER_W = max(TFT_W, SW_W) + 2 * WALL + 2 * GAP + 2.0
CAV_L, CAV_W = OUTER_L - 2 * WALL, OUTER_W - 2 * WALL
WAIST = 0.6  # inset for waistline reveal
THUMB_FLAT = 1.2


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

    # Soft outer profile with -Y thumb flat
    body = round_rect(OUTER_L, OUTER_W, CORNER_R)
    # thumb flat: clip -Y side
    body = body.difference(sbox(-OUTER_L, -OUTER_W / 2 - 1, OUTER_L, -OUTER_W / 2 + THUMB_FLAT))
    outer_poly = translate(body, xoff=OUTER_L / 2, yoff=0)
    # waistline: slightly smaller upper band on base rim
    waist_poly = translate(round_rect(OUTER_L - 2 * WAIST, OUTER_W - 2 * WAIST - THUMB_FLAT * 0.3, CORNER_R - 0.3),
                           xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.15)

    # ===== BASE (solid glove) =====
    base_core = extrude(outer_poly, BASE_SOLID_H, 0)
    rim = extrude(waist_poly, RIM_H, BASE_SOLID_H)
    base_outer = union(base_core, rim)

    # Sight groove along +Y top edge (points at I2C channel)
    sight = box_at([OUTER_L * 0.55, 1.2, 1.0], [sw_cx, OUTER_W / 2 - 0.4, BASE_SOLID_H + RIM_H - 0.3])

    wells = [
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 4.0, sw_cy - 6.5, BASE_SOLID_H - CAP_H / 2]),
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 18.0, sw_cy + 6.5, BASE_SOLID_H - CAP_H / 2]),
        box_at([IND_BORE, IND_BORE, IND_H + 0.4], [sw_cx + 14.0, sw_cy - 5.0, BASE_SOLID_H - (IND_H + 0.2) / 2]),
        box_at([HS_BORE, HS_BORE, HS_H + 0.4], [sw_cx - 12.0, sw_cy + 2.5, BASE_SOLID_H - (HS_H + 0.2) / 2]),
    ]
    pcb_pocket = box_at([SW_L + 2 * GAP, SW_W + 2 * GAP, RIM_H + 0.4],
                        [sw_cx, sw_cy, BASE_SOLID_H + RIM_H / 2])

    barrel_z = BASE_SOLID_H - BARREL_H / 2 - 0.5
    barrel_bits = [
        box_at([END_LIP + BARREL_L + 4, BARREL_W + 1.0, BARREL_H + 1.2],
               [OUTER_L - END_LIP / 2, sw_cy, barrel_z]),
        cyl_at(BARREL_OD / 2 + 0.3, END_LIP + BARREL_PAST + 8,
               [OUTER_L - END_LIP / 2 + 1, sw_cy, barrel_z], axis='x'),
        cyl_at(BARREL_COLLAR_OD / 2 + 0.25, 3.0,
               [OUTER_L - END_LIP - 1.0, sw_cy, barrel_z], axis='x'),
    ]
    usb_z_c = BASE_SOLID_H - 1.5 - USB_C_H / 2
    usb_bits = [
        box_at([END_LIP + 12, USB_HOUSE_W + 1.0, USB_HOUSE_H + 1.0],
               [END_LIP / 2, sw_cy, BASE_SOLID_H - (USB_HOUSE_H + 1) / 2]),
        box_at([END_LIP + 14, USB_C_W + 0.8, USB_C_H + 0.6], [END_LIP / 2, sw_cy, usb_z_c]),
        box_at([END_LIP + 14, USB_A_W + 0.6, USB_A_H + 0.6],
               [END_LIP / 2, sw_cy, usb_z_c - USB_C_H / 2 - 0.6 - USB_A_H / 2]),
    ]
    # 45° lead-in chamfers approximated as wider mouth boxes at outer face
    usb_lead = box_at([2.5, USB_HOUSE_W + 3.0, USB_HOUSE_H + 2.5],
                      [1.0, sw_cy, BASE_SOLID_H - (USB_HOUSE_H + 1) / 2])
    barrel_lead = box_at([2.5, BARREL_W + 3.0, BARREL_H + 2.5],
                         [OUTER_L - 1.0, sw_cy, barrel_z])

    mounts = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mounts.append(cyl_at(MOUNT_D / 2, BASE_H + 2, [hx, hy, BASE_H / 2]))

    # I2C / flex hinge channel on +Y (SDA edge) — bayonet pivot line
    hinge_ch = box_at([14.0, WALL + 5, RIM_H + 3.0],
                      [sw_cx + 6.0, OUTER_W / 2 - 0.5, BASE_SOLID_H + RIM_H / 2])

    base = diff(base_outer, pcb_pocket, sight, hinge_ch, *wells, *barrel_bits, *usb_bits,
                usb_lead, barrel_lead, *mounts)

    # ===== MID PLATE (instrument deck + bayonet) =====
    mid_outer = extrude(outer_poly, MID_T, 0)
    # raised datum rail under lid
    rail = extrude(translate(round_rect(CAV_L - 3, CAV_W - 3, CORNER_R - 1), xoff=OUTER_L / 2, yoff=0),
                   0.8, MID_T)
    mid = union(mid_outer, rail)

    sw_open = box_at([SW_L - 6, SW_W - 4, MID_T + 2], [sw_cx, sw_cy, MID_T / 2])
    zero_cx = sw_cx - 8
    zero_cy = CAV_W / 2 - ZERO_W / 2 - GAP - 0.5
    zero_pocket = box_at([ZERO_L + 2 * GAP, ZERO_W + 2 * GAP, MID_T + 1.5], [zero_cx, zero_cy, MID_T / 2])
    haptic = cyl_at(HAP_D / 2, HAP_DEPTH, [zero_cx + 2, zero_cy, MID_T - 0.2])

    # Bayonet lugs (4) — lid twists ~15° to lock
    lug_r, lug_w, lug_h = 2.2, 6.0, 1.4
    lugs = []
    for ang in (20, 110, 200, 290):
        rad = np.deg2rad(ang)
        lx = sw_cx + 22 * np.cos(rad)
        ly = 12 * np.sin(rad)
        lug = box_at([lug_w, lug_r * 2, lug_h], [lx, ly, MID_T + lug_h / 2])
        lugs.append(lug)
    mid = union(mid, *lugs)

    # Service flap pocket on +Y for Zero USB (through mid + will match lid flap)
    flap_cut = box_at([ZERO_USB_W + 2, ZERO_USB_STICK + 2, ZERO_USB_H + 1.5],
                      [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2, MID_T / 2])
    # Flex pass at hinge line (+Y SDA), not twisted by bayonet
    flex = box_at([12.0, 5.0, MID_T + 3], [sw_cx + 6.0, OUTER_W / 2 - 3.0, MID_T / 2])

    mid_holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mid_holes.append(cyl_at(MOUNT_D / 2 + 0.1, MID_T + 4, [hx, hy, MID_T / 2]))

    mid = diff(mid, sw_open, zero_pocket, haptic, flap_cut, flex, *mid_holes)
    # clamp bars
    mid = union(mid,
                box_at([SW_L - 2, 2.0, 1.0], [sw_cx, -(SW_W / 2 + 0.2), 0.4]),
                box_at([SW_L - 2, 2.0, 1.0], [sw_cx, (SW_W / 2 + 0.2), 0.4]))

    # Matching Zero USB tunnel through base wall at mid height
    base = diff(base, box_at([ZERO_USB_W + 2, ZERO_USB_STICK + 3, ZERO_USB_H + 2],
                             [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2,
                              mid_z0 + MID_T / 2]))

    # ===== LID (bezel + cartridge + flexures + bayonet slots + service flap) =====
    lid_face = extrude(outer_poly, LID_H, 0)
    # chamfer approx: cut outer top edge
    chamfer = extrude(translate(round_rect(OUTER_L + 2, OUTER_W + 2, CORNER_R), xoff=OUTER_L / 2, yoff=0),
                      0.9, LID_H - 0.5)
    chamfer = diff(chamfer, extrude(translate(round_rect(OUTER_L - 2.4, OUTER_W - 2.4 - THUMB_FLAT * 0.2, CORNER_R - 0.4),
                                              xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.1), 1.2, LID_H - 0.6))
    lid = diff(lid_face, chamfer)

    win_cx = OUTER_L / 2 - TFT_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2
    # screen window
    lid = diff(lid,
               box_at([TFT_WIN_L + 0.3, TFT_WIN_W + 0.3, LID_H + 2], [win_cx, 0, LID_H / 2]),
               box_at([TFT_WIN_L + 2.0, TFT_WIN_W + 2.0, 0.6], [win_cx, 0, LID_H - 0.2]))

    # A/B tactile islands with flexure slots (printed leaf springs)
    for bx, by in [(OUTER_L * 0.82, 8.0), (OUTER_L * 0.82, -8.0)]:
        island = cyl_at(5.5, 0.7, [bx, by, LID_H + 0.2])
        lid = union(lid, island)
        # annular flexure groove
        groove = diff(cyl_at(5.0, 0.8, [bx, by, LID_H - 0.3]),
                      cyl_at(2.2, 1.0, [bx, by, LID_H - 0.3]))
        # leave two bridges
        bridge = box_at([2.5, 11, 1.0], [bx, by, LID_H - 0.3])
        groove = diff(groove, bridge)
        lid = diff(lid, groove)
        lid = diff(lid, cyl_at(BTN_D / 2, LID_H + 2, [bx, by, LID_H / 2]))

    # Bayonet slots (mate to mid lugs) — elongated arcs approximated as boxes at lock angles
    for ang in (20, 110, 200, 290):
        rad = np.deg2rad(ang)
        lx = sw_cx + 22 * np.cos(rad)
        ly = 12 * np.sin(rad)
        # entry slot then lock detent
        slot = box_at([8.0, 2.6, 1.6], [lx, ly, 0.6])
        lid = diff(lid, slot)

    # Service flap: living-hinge style recess + fingernail scoop (not raw notch)
    flap_x = zero_cx - ZERO_L / 2 - 1.0
    flap_y = OUTER_W / 2 - 1.0
    # main plug clearance through lid edge
    lid = diff(lid, box_at([ZERO_USB_W + 1.5, 6.0, ZERO_USB_H],
                           [flap_x, flap_y - 2.0, LID_H / 2]))
    # fingernail scoop on outer face
    scoop = cyl_at(4.0, 1.2, [flap_x, OUTER_W / 2 - 0.2, LID_H - 0.3], axis='x')
    lid = diff(lid, scoop)
    # living hinge thinned strip
    hinge = box_at([ZERO_USB_W + 3, 0.6, 0.5], [flap_x, flap_y - 5.5, 0.4])
    lid = diff(lid, hinge)

    # ===== TFT CARTRIDGE (separate part — snap-clips into lid from below) =====
    cart_outer = box_at([TFT_L + 3.0, TFT_W + 3.0, CART_H], [OUTER_L / 2, 0, CART_H / 2])
    cart = diff(cart_outer,
                box_at([TFT_L + 2 * GAP, TFT_W + 2 * GAP, TFT_T + 0.8],
                       [OUTER_L / 2, 0, CART_H / 2]),
                box_at([TFT_WIN_L, TFT_WIN_W, CART_H + 1], [win_cx, 0, CART_H / 2]))
    # 4 leaf clips
    clips = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        cx = OUTER_L / 2 + sx * (TFT_L / 2 + 0.2)
        cy = sy * (TFT_W / 2 + 0.2)
        arm = box_at([1.2, 4.0, 1.8], [cx, cy, CART_H + 0.6])
        hook = box_at([2.2, 1.2, 0.8], [cx + sx * 0.6, cy, CART_H + 1.6])
        clips.append(union(arm, hook))
    cart = union(cart, *clips)

    # Recess in lid underside for cartridge
    lid = diff(lid, box_at([TFT_L + 3.4, TFT_W + 3.4, 1.8], [OUTER_L / 2, 0, 0.7]))

    # Port reliefs on lid ends
    lid = diff(lid,
               box_at([5.0, USB_HOUSE_W + 3, LID_H + 1], [2.0, 0, LID_H / 2]),
               box_at([5.0, BARREL_W + 3, LID_H + 1], [OUTER_L - 2.0, 0, LID_H / 2]))

    # print lid outer-face down
    lid_print = lid.copy()
    T = np.eye(4); T[2, 2] = -1; T[2, 3] = lid.bounds[0][2] + lid.bounds[1][2]
    lid_print.apply_transform(T)
    lid_print.apply_translation([0, 0, -lid_print.bounds[0][2]])

    base.apply_translation([0, 0, -base.bounds[0][2]])
    mid.apply_translation([0, 0, -mid.bounds[0][2]])
    cart.apply_translation([0, 0, -cart.bounds[0][2]])

    base.export(OUT / 'v61_base.stl')
    mid.export(OUT / 'v61_mid_plate.stl')
    lid_print.export(OUT / 'v61_lid.stl')
    cart.export(OUT / 'v61_tft_cartridge.stl')

    mid_p = mid.copy(); mid_p.apply_translation([0, 0, BASE_H + 8])
    lid_p = lid.copy(); lid_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 16])
    cart_p = cart.copy(); cart_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 22])
    union(base.copy(), mid_p, lid_p, cart_p).export(OUT / 'v61_preview_exploded.stl')

    meta = {
        'version': '6.1-draft',
        'form': 'pocket instrument / field meter',
        'parts': ['v61_base', 'v61_mid_plate', 'v61_lid', 'v61_tft_cartridge'],
        'features': [
            'solid glove base with Ø7.25×18 cap bores',
            'waistline + -Y thumb flat + +Y sight groove',
            'mid instrument rail + 15° bayonet lugs',
            'flex at SDA/+Y hinge line (no twist under bayonet)',
            'lid bezel + rear snap TFT cartridge',
            'A/B printed flexure islands',
            'Zero USB flush service flap (plug + fingernail scoop)',
        ],
        'print_outer_mm': {
            'footprint': [round(OUTER_L, 2), round(OUTER_W, 2)],
            'base_h': round(float(base.extents[2]), 2),
            'mid_t': MID_T,
            'lid_h': LID_H,
        },
        'ports': {'usb_ac': 'flush -X', 'barrel': 'flush +X', 'zero_usb': '+Y service flap'},
    }
    (OUT / 'v61_case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported v6.1 →', OUT)
    for name, m in [('base', base), ('mid', mid), ('lid', lid_print), ('cart', cart)]:
        print(f'  {name}: extents={np.round(m.extents,2).tolist()} watertight={m.is_watertight} vol={m.volume:.0f}')


if __name__ == '__main__':
    main()
