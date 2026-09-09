#!/usr/bin/env python3
"""Pocket instrument v6.2 — form pass on v6.1.

Form / mechanics upgrades (glove + caliper dims UNCHANGED):
  - Real ~15° bayonet cam arcs (entry → travel → detent), not box dogs
  - TFT cartridge: thicker PETG leaf arms + lead-in hooks + lid catch ledges
  - Deeper scope bezel well + asymmetric A/B field-meter cluster
  - Stronger waist / thumb flat / sight groove
  - Captive-slide Zero USB door (PETG-durable) instead of fragile living hinge

Requires: trimesh, manifold3d, shapely, numpy
"""
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent

# --- caliper / glove (LOCKED from v6 / v6.1) ---
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
MID_T, LID_H, CART_H = 2.6, 3.6, 2.2  # lid slightly taller for bezel well
DECK_AIR = 1.2
WELL_Z = max(CAP_H, IND_H + 0.5, HS_H + 0.5, BARREL_H + 1.0)
BASE_SOLID_H = FLOOR + WELL_PAD + WELL_Z
RIM_H = SW_PCB_T + 1.0
BASE_H = BASE_SOLID_H + RIM_H
END_LIP = max(BARREL_PAST, USB_PAST) + 0.8
OUTER_L = SW_L + 2 * END_LIP
OUTER_W = max(TFT_W, SW_W) + 2 * WALL + 2 * GAP + 2.0
CAV_L, CAV_W = OUTER_L - 2 * WALL, OUTER_W - 2 * WALL
WAIST = 1.1
THUMB_FLAT = 1.8

# Bayonet cam params
BAY_RX, BAY_RY = 22.0, 12.0  # elliptical radius (fits footprint)
BAY_LOCK_ANGS = (25, 115, 205, 295)  # lock positions (deg)
BAY_SWEEP = 15.0  # twist travel
BAY_LUG_W, BAY_LUG_T, BAY_LUG_H = 5.5, 2.0, 1.5
BAY_SLOT_W, BAY_SLOT_H = 2.6, 1.7


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


def rotate_about_z(mesh, deg, origin):
    m = mesh.copy()
    T = trimesh.transformations.rotation_matrix(np.deg2rad(deg), [0, 0, 1], point=origin)
    m.apply_transform(T)
    return m


def bay_xy(cx, cy, ang_deg):
    rad = np.deg2rad(ang_deg)
    return cx + BAY_RX * np.cos(rad), cy + BAY_RY * np.sin(rad)


def tangential_box(extents, cx, cy, ang_deg, z):
    """Box centered on bayonet ellipse, long axis tangential to path."""
    x, y = bay_xy(cx, cy, ang_deg)
    m = box_at(extents, [x, y, z])
    # tangent angle = ang + 90°
    return rotate_about_z(m, ang_deg + 90.0, [x, y, z])


def arc_cut(cx, cy, ang0, sweep, radial_w, tang_step_w, h, z, steps=None):
    """Union of tangential boxes sweeping an arc (cam slot / travel path)."""
    if steps is None:
        steps = max(10, int(abs(sweep) * 1.2))
    pieces = []
    for i in range(steps + 1):
        ang = ang0 + sweep * i / steps
        pieces.append(tangential_box([tang_step_w, radial_w, h], cx, cy, ang, z))
    return union(*pieces)


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
    bay_origin = [sw_cx, sw_cy, 0.0]

    body = round_rect(OUTER_L, OUTER_W, CORNER_R)
    body = body.difference(sbox(-OUTER_L, -OUTER_W / 2 - 1, OUTER_L, -OUTER_W / 2 + THUMB_FLAT))
    outer_poly = translate(body, xoff=OUTER_L / 2, yoff=0)
    waist_poly = translate(
        round_rect(OUTER_L - 2 * WAIST, OUTER_W - 2 * WAIST - THUMB_FLAT * 0.35, CORNER_R - 0.4),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.18)

    # ===== BASE (solid glove — wells LOCKED) =====
    base_core = extrude(outer_poly, BASE_SOLID_H, 0)
    rim = extrude(waist_poly, RIM_H, BASE_SOLID_H)
    base_outer = union(base_core, rim)

    sight = box_at([OUTER_L * 0.58, 1.6, 1.4],
                   [sw_cx, OUTER_W / 2 - 0.35, BASE_SOLID_H + RIM_H - 0.35])

    wells = [
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 4.0, sw_cy - 6.5, BASE_SOLID_H - CAP_H / 2]),
        cyl_at(CAP_BORE_D / 2, CAP_H + 0.2, [sw_cx + 18.0, sw_cy + 6.5, BASE_SOLID_H - CAP_H / 2]),
        box_at([IND_BORE, IND_BORE, IND_H + 0.4],
               [sw_cx + 14.0, sw_cy - 5.0, BASE_SOLID_H - (IND_H + 0.2) / 2]),
        box_at([HS_BORE, HS_BORE, HS_H + 0.4],
               [sw_cx - 12.0, sw_cy + 2.5, BASE_SOLID_H - (HS_H + 0.2) / 2]),
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
    usb_lead = box_at([2.5, USB_HOUSE_W + 3.0, USB_HOUSE_H + 2.5],
                      [1.0, sw_cy, BASE_SOLID_H - (USB_HOUSE_H + 1) / 2])
    barrel_lead = box_at([2.5, BARREL_W + 3.0, BARREL_H + 2.5],
                         [OUTER_L - 1.0, sw_cy, barrel_z])

    mounts = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mounts.append(cyl_at(MOUNT_D / 2, BASE_H + 2, [hx, hy, BASE_H / 2]))

    hinge_ch = box_at([14.0, WALL + 5, RIM_H + 3.0],
                      [sw_cx + 6.0, OUTER_W / 2 - 0.5, BASE_SOLID_H + RIM_H / 2])

    base = diff(base_outer, pcb_pocket, sight, hinge_ch, *wells, *barrel_bits, *usb_bits,
                usb_lead, barrel_lead, *mounts)

    # ===== MID PLATE =====
    mid_outer = extrude(outer_poly, MID_T, 0)
    rail = extrude(translate(round_rect(CAV_L - 3, CAV_W - 3, CORNER_R - 1),
                             xoff=OUTER_L / 2, yoff=0), 0.8, MID_T)
    mid = union(mid_outer, rail)

    sw_open = box_at([SW_L - 6, SW_W - 4, MID_T + 2], [sw_cx, sw_cy, MID_T / 2])
    zero_cx = sw_cx - 8
    zero_cy = CAV_W / 2 - ZERO_W / 2 - GAP - 0.5
    zero_pocket = box_at([ZERO_L + 2 * GAP, ZERO_W + 2 * GAP, MID_T + 1.5],
                         [zero_cx, zero_cy, MID_T / 2])
    haptic = cyl_at(HAP_D / 2, HAP_DEPTH, [zero_cx + 2, zero_cy, MID_T - 0.2])

    # Real bayonet lugs — tangential at LOCK angles (cams ride into these via arc slots)
    lugs = []
    for ang in BAY_LOCK_ANGS:
        lug = tangential_box([BAY_LUG_W, BAY_LUG_T, BAY_LUG_H],
                             sw_cx, sw_cy, ang, MID_T + BAY_LUG_H / 2)
        # small radial detent bump on outer face of lug
        x, y = bay_xy(sw_cx, sw_cy, ang)
        bump = tangential_box([1.6, 0.7, BAY_LUG_H * 0.7],
                              sw_cx, sw_cy, ang, MID_T + BAY_LUG_H / 2)
        # nudge bump slightly outward along radial by rebuilding at larger R — approximate via extra union
        lugs.append(union(lug, bump))
    mid = union(mid, *lugs)

    flap_cut = box_at([ZERO_USB_W + 2, ZERO_USB_STICK + 2, ZERO_USB_H + 1.5],
                      [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2, MID_T / 2])
    flex = box_at([12.0, 5.0, MID_T + 3], [sw_cx + 6.0, OUTER_W / 2 - 3.0, MID_T / 2])

    mid_holes = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sw_cx + sx * (SW_L / 2 - MOUNT_INSET)
        hy = sw_cy + sy * (SW_W / 2 - MOUNT_INSET)
        mid_holes.append(cyl_at(MOUNT_D / 2 + 0.1, MID_T + 4, [hx, hy, MID_T / 2]))

    mid = diff(mid, sw_open, zero_pocket, haptic, flap_cut, flex, *mid_holes)
    mid = union(mid,
                box_at([SW_L - 2, 2.0, 1.0], [sw_cx, -(SW_W / 2 + 0.2), 0.4]),
                box_at([SW_L - 2, 2.0, 1.0], [sw_cx, (SW_W / 2 + 0.2), 0.4]))

    base = diff(base, box_at([ZERO_USB_W + 2, ZERO_USB_STICK + 3, ZERO_USB_H + 2],
                             [zero_cx - ZERO_L / 2 - 1.0, OUTER_W / 2 - ZERO_USB_STICK / 2,
                              mid_z0 + MID_T / 2]))

    # ===== LID — deeper scope bezel + cam slots + asymmetric A/B =====
    lid_face = extrude(outer_poly, LID_H, 0)
    chamfer = extrude(translate(round_rect(OUTER_L + 2, OUTER_W + 2, CORNER_R),
                                xoff=OUTER_L / 2, yoff=0), 1.0, LID_H - 0.55)
    chamfer = diff(chamfer, extrude(translate(
        round_rect(OUTER_L - 2.8, OUTER_W - 2.8 - THUMB_FLAT * 0.25, CORNER_R - 0.5),
        xoff=OUTER_L / 2, yoff=THUMB_FLAT * 0.12), 1.3, LID_H - 0.7))
    lid = diff(lid_face, chamfer)

    win_cx = OUTER_L / 2 - TFT_L / 2 + TFT_WIN_OFF_X + TFT_WIN_L / 2

    # Deep scope bezel well (dark recess) then through-window
    bezel_well = box_at([TFT_WIN_L + 6.0, TFT_WIN_W + 5.0, 1.4],
                        [win_cx - 0.5, 0.4, LID_H - 0.55])
    # slight oval bias: widen toward +X instrument side
    bezel_well2 = box_at([TFT_WIN_L + 3.5, TFT_WIN_W + 3.0, 1.0],
                         [win_cx, 0.2, LID_H - 0.9])
    lid = diff(lid, bezel_well, bezel_well2)
    lid = diff(lid,
               box_at([TFT_WIN_L + 0.3, TFT_WIN_W + 0.3, LID_H + 2], [win_cx, 0, LID_H / 2]),
               box_at([TFT_WIN_L + 1.6, TFT_WIN_W + 1.6, 0.5], [win_cx, 0, LID_H - 1.5]))

    # A/B tight pair beside bezel (thumb-reachable, slight stagger — not corner-buried)
    # Sit on +X of screen window, stacked roughly along Y with small offset
    btn_specs = [
        ('A', win_cx + TFT_WIN_L / 2 + 8.5, 6.5, 5.4),
        ('B', win_cx + TFT_WIN_L / 2 + 9.5, -6.0, 5.0),
    ]
    for _name, bx, by, island_r in btn_specs:
        island = cyl_at(island_r, 0.75, [bx, by, LID_H + 0.25])
        lid = union(lid, island)
        groove = diff(cyl_at(island_r - 0.5, 0.85, [bx, by, LID_H - 0.35]),
                      cyl_at(2.0, 1.1, [bx, by, LID_H - 0.35]))
        # thicker PETG bridges (radial)
        bridge = box_at([island_r * 2.2, 2.8, 1.1], [bx, by, LID_H - 0.35])
        groove = diff(groove, bridge)
        lid = diff(lid, groove)
        lid = diff(lid, cyl_at(BTN_D / 2, LID_H + 2, [bx, by, LID_H / 2]))

    # Bayonet CAM slots: arc from (lock - sweep) entry → lock detent
    for ang_lock in BAY_LOCK_ANGS:
        ang_entry = ang_lock - BAY_SWEEP
        # travel path (slightly wider)
        travel = arc_cut(sw_cx, sw_cy, ang_entry, BAY_SWEEP,
                         radial_w=BAY_SLOT_W + 0.35, tang_step_w=2.4,
                         h=BAY_SLOT_H, z=0.55, steps=16)
        # wide mouth at entry
        mouth = tangential_box([4.0, BAY_SLOT_W + 1.0, BAY_SLOT_H + 0.2],
                               sw_cx, sw_cy, ang_entry, 0.55)
        # detent notch at lock (slightly tighter / radial step)
        detent = tangential_box([BAY_LUG_W + 0.6, BAY_SLOT_W + 0.15, BAY_SLOT_H],
                                sw_cx, sw_cy, ang_lock, 0.55)
        lid = diff(lid, travel, mouth, detent)

    # Captive-slide Zero USB door channel (PETG durable)
    flap_x = zero_cx - ZERO_L / 2 - 1.0
    flap_y = OUTER_W / 2 - 1.0
    # main plug clearance
    lid = diff(lid, box_at([ZERO_USB_W + 1.5, 6.0, ZERO_USB_H],
                           [flap_x, flap_y - 2.0, LID_H / 2]))
    # slide channel + fingernail scoop
    scoop = cyl_at(4.0, 1.2, [flap_x, OUTER_W / 2 - 0.2, LID_H - 0.3], axis='x')
    lid = diff(lid, scoop)
    # dovetail-ish retaining rails: undercut channel for separate door
    slide_pocket = box_at([ZERO_USB_W + 3.5, 7.5, 1.2],
                          [flap_x, flap_y - 3.0, LID_H - 0.5])
    lid = diff(lid, slide_pocket)
    # rail undercuts (retain door)
    rail_l = box_at([ZERO_USB_W + 4.0, 0.7, 0.55],
                    [flap_x, flap_y - 6.4, LID_H - 1.05])
    rail_r = box_at([ZERO_USB_W + 4.0, 0.7, 0.55],
                    [flap_x, flap_y + 0.2, LID_H - 1.05])
    lid = diff(lid, rail_l, rail_r)

    # Separate captive door (prints with lid stack)
    door = box_at([ZERO_USB_W + 2.8, 6.8, 1.0], [flap_x, flap_y - 3.0, 0.5])
    # rail tabs
    tab1 = box_at([ZERO_USB_W + 3.2, 0.9, 0.45], [flap_x, flap_y - 6.2, 0.15])
    tab2 = box_at([ZERO_USB_W + 3.2, 0.9, 0.45], [flap_x, flap_y + 0.0, 0.15])
    # nail divot
    door = diff(union(door, tab1, tab2),
                cyl_at(2.2, 0.8, [flap_x, flap_y - 1.0, 0.85], axis='x'))

    # ===== TFT CARTRIDGE — thicker arms + lead-in hooks =====
    cart_outer = box_at([TFT_L + 3.0, TFT_W + 3.0, CART_H], [OUTER_L / 2, 0, CART_H / 2])
    cart = diff(cart_outer,
                box_at([TFT_L + 2 * GAP, TFT_W + 2 * GAP, TFT_T + 0.8],
                       [OUTER_L / 2, 0, CART_H / 2]),
                box_at([TFT_WIN_L, TFT_WIN_W, CART_H + 1], [win_cx, 0, CART_H / 2]))
    clips = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        cx = OUTER_L / 2 + sx * (TFT_L / 2 + 0.15)
        cy = sy * (TFT_W / 2 + 0.15)
        # thicker PETG leaf (~1.7 mm)
        arm = box_at([1.7, 4.5, 2.0], [cx, cy, CART_H + 0.7])
        # hook with lead-in (stepped)
        hook = box_at([2.6, 1.4, 0.9], [cx + sx * 0.7, cy, CART_H + 1.85])
        lead = box_at([1.4, 1.4, 0.55], [cx + sx * 1.3, cy, CART_H + 2.15])
        clips.append(union(arm, hook, lead))
    cart = union(cart, *clips)

    # Lid recess + CATCH LEDGES for hooks to bite
    lid = diff(lid, box_at([TFT_L + 3.6, TFT_W + 3.6, 2.0], [OUTER_L / 2, 0, 0.85]))
    ledges = []
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        lx = OUTER_L / 2 + sx * (TFT_L / 2 + 0.15)
        ly = sy * (TFT_W / 2 + 0.15)
        # ledge hangs into pocket; hook snaps under it
        ledge = box_at([2.8, 3.2, 0.75], [lx + sx * 0.4, ly, 1.55])
        ledges.append(ledge)
    lid = union(lid, *ledges)

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
    door.apply_translation([0, 0, -door.bounds[0][2]])

    base.export(OUT / 'v62_base.stl')
    mid.export(OUT / 'v62_mid_plate.stl')
    lid_print.export(OUT / 'v62_lid.stl')
    cart.export(OUT / 'v62_tft_cartridge.stl')
    door.export(OUT / 'v62_usb_door.stl')

    mid_p = mid.copy(); mid_p.apply_translation([0, 0, BASE_H + 8])
    lid_p = lid.copy(); lid_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 16])
    cart_p = cart.copy(); cart_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 22])
    door_p = door.copy(); door_p.apply_translation([0, 0, BASE_H + MID_T + DECK_AIR + 28])
    union(base.copy(), mid_p, lid_p, cart_p, door_p).export(OUT / 'v62_preview_exploded.stl')

    meta = {
        'version': '6.2-draft',
        'form': 'pocket instrument / field meter',
        'parent': '6.1',
        'parts': ['v62_base', 'v62_mid_plate', 'v62_lid', 'v62_tft_cartridge', 'v62_usb_door'],
        'features': [
            'solid glove base with Ø7.25×18 cap bores (UNCHANGED from v6.1)',
            'stronger waistline + -Y thumb flat + +Y sight groove',
            'mid instrument rail + true ~15° bayonet cam arcs with detent',
            'flex at SDA/+Y hinge line (no twist under bayonet)',
            'deeper scope bezel well + asymmetric A/B flexure cluster',
            'TFT cartridge: 1.7mm leaf arms, lead-in hooks, lid catch ledges',
            'captive-slide Zero USB door (PETG) + fingernail scoop',
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
        'ports': {'usb_ac': 'flush -X', 'barrel': 'flush +X', 'zero_usb': '+Y captive slide door'},
        'regen': '/workspace/.cadvenv/bin/python case/generate_case_v62.py',
    }
    (OUT / 'v62_case_meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print('exported v6.2 →', OUT)
    for name, m in [('base', base), ('mid', mid), ('lid', lid_print),
                    ('cart', cart), ('door', door)]:
        print(f'  {name}: extents={np.round(m.extents,2).tolist()} '
              f'watertight={m.is_watertight} vol={m.volume:.0f}')


if __name__ == '__main__':
    main()
