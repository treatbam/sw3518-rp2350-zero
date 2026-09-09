#!/usr/bin/env python3
"""Pocket case v4: SW3518S spine — barrel and USB flush on opposite ends; TFT+Zero above.
Requires: trimesh, manifold3d, shapely, numpy (see /workspace/.cadvenv)
"""
# Full parametric source: regenerate STLs with the same layout as case_meta.json v4.
# For edits, adjust SW_L/W/H and re-run. Implementation lives inline below.
from pathlib import Path
import json, numpy as np, trimesh
from shapely.geometry import box as sbox, Point
from shapely.ops import unary_union
from shapely.affinity import translate

OUT = Path(__file__).resolve().parent
SW_L, SW_W, SW_H = 60.0, 22.0, 14.0
SW_USB_W, SW_USB_H = 16.0, 14.0
SW_BARREL_W, SW_BARREL_H = 14.0, 12.0
ZERO_L, ZERO_W = 23.5, 18.0
ZERO_USB_OVERHANG, ZERO_USB_W, ZERO_USB_H = 2.5, 9.2, 3.4
TFT_OUTER_L, TFT_OUTER_W, TFT_THICK = 55.0, 34.0, 3.6
TFT_WIN_L, TFT_WIN_W, TFT_WIN_OFF_X = 35.0, 28.0, 8.0
HAP_D, HAP_DEPTH, BTN_D = 10.2, 2.6, 6.4
WALL, GAP, CORNER_R, FLOOR, LID_H, DECK_GAP = 1.6, 0.40, 3.0, 1.5, 2.8, 1.2
END_LIP = 1.2
OUTER_L = SW_L + 2 * END_LIP
OUTER_W = max(TFT_OUTER_W, SW_W) + 2 * WALL + 2 * GAP + 4.0
BOTTOM_H = FLOOR + SW_H + DECK_GAP + 2.5 + TFT_THICK
SHELL_H = BOTTOM_H + LID_H
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
    m = trimesh.creation.extrude_polygon(poly, height=height); m.apply_translation([0,0,z0]); return m
def box_at(e, c):
    m = trimesh.creation.box(extents=e); m.apply_translation(c); return m
def cyl_at(r, h, c, axis='z'):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=48)
    if axis == 'y': m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
    m.apply_translation(c); return m
def diff(a, *bs):
    out = a
    for b in bs:
        out = trimesh.boolean.difference([out, b], engine='manifold', check_volume=False)
        if isinstance(out, list): out = trimesh.util.concatenate(out)
    return out
def union(*ms):
    out = ms[0]
    for m in ms[1:]:
        out = trimesh.boolean.union([out, m], engine='manifold', check_volume=False)
        if isinstance(out, list): out = trimesh.util.concatenate(out)
    return out

def main():
    sw_x0 = END_LIP; sw_cx = sw_x0 + SW_L/2; sw_cy = 0.0
    tft_cx = OUTER_L/2; tft_cy = 0.0
    zero_cx = sw_x0 + GAP + ZERO_USB_OVERHANG + ZERO_L/2
    zero_cy = -(CAV_W/2 - ZERO_W/2 - GAP - 0.5)
    deck_z = FLOOR + SW_H + DECK_GAP
    outer_poly = translate(round_rect(OUTER_L, OUTER_W, CORNER_R), xoff=OUTER_L/2, yoff=0)
    bottom_outer = extrude(outer_poly, BOTTOM_H, 0)
    cav_poly = translate(round_rect(CAV_L, CAV_W, max(0.8, CORNER_R-0.5)), xoff=END_LIP+CAV_L/2, yoff=0)
    cavity = extrude(cav_poly, BOTTOM_H-FLOOR+0.4, FLOOR)
    sw_bay = box_at([SW_L+2*GAP, SW_W+2*GAP, SW_H+0.6], [sw_cx, sw_cy, FLOOR+(SW_H+0.6)/2])
    barrel = box_at([END_LIP+8, SW_BARREL_W+2, SW_BARREL_H+1], [END_LIP/2-1, sw_cy, FLOOR+SW_BARREL_H/2+1.0])
    barrel_flare = box_at([6.0, SW_BARREL_W+5, SW_BARREL_H+4], [-2.0, sw_cy, FLOOR+SW_BARREL_H/2+1.0])
    barrel_top = box_at([END_LIP+4, SW_BARREL_W+3, BOTTOM_H], [END_LIP/2, sw_cy, FLOOR+BOTTOM_H/2])
    usb = box_at([END_LIP+8, SW_USB_W+2, SW_USB_H+1], [OUTER_L-END_LIP/2+1, sw_cy, FLOOR+SW_USB_H/2+1.0])
    usb_flare = box_at([6.0, SW_USB_W+5, SW_USB_H+4], [OUTER_L+2.0, sw_cy, FLOOR+SW_USB_H/2+1.0])
    usb_top = box_at([END_LIP+4, SW_USB_W+3, BOTTOM_H], [OUTER_L-END_LIP/2, sw_cy, FLOOR+BOTTOM_H/2])
    haptic = cyl_at(HAP_D/2, HAP_DEPTH+0.8, [zero_cx+3, zero_cy, deck_z+0.3])
    zero_pocket = box_at([ZERO_L+2*GAP, ZERO_W+2*GAP, 2.0], [zero_cx, zero_cy, deck_z+HAP_DEPTH+1.0])
    zusb = box_at([ZERO_USB_W+1.0, WALL+8, ZERO_USB_H+1.0],
                  [zero_cx-ZERO_L/2-ZERO_USB_OVERHANG/2, -OUTER_W/2, deck_z+HAP_DEPTH+1.0+ZERO_USB_H/2])
    tft_z = BOTTOM_H - TFT_THICK - 0.3
    tft_pocket = box_at([TFT_OUTER_L+2*GAP, TFT_OUTER_W+2*GAP, TFT_THICK+1.2],
                        [tft_cx, tft_cy, tft_z+(TFT_THICK+1.2)/2])
    btn_x, btn_z = OUTER_L/2, deck_z+3.0
    btn_l = cyl_at(BTN_D/2, WALL+8, [btn_x, -OUTER_W/2, btn_z], axis='y')
    btn_r = cyl_at(BTN_D/2, WALL+8, [btn_x, OUTER_W/2, btn_z], axis='y')
    btn_l_cs = cyl_at(BTN_D/2+0.8, 1.2, [btn_x, -OUTER_W/2+0.4, btn_z], axis='y')
    btn_r_cs = cyl_at(BTN_D/2+0.8, 1.2, [btn_x, OUTER_W/2-0.4, btn_z], axis='y')
    chimney = box_at([5.0, 5.0, SW_H+DECK_GAP+2], [sw_cx-5, SW_W/2+1, FLOOR+(SW_H+DECK_GAP)/2])
    bottom = diff(bottom_outer, cavity, sw_bay, barrel, barrel_flare, barrel_top,
                  usb, usb_flare, usb_top, haptic, zero_pocket, zusb, tft_pocket,
                  btn_l, btn_r, btn_l_cs, btn_r_cs, chimney)
    bottom = union(
        bottom,
        box_at([SW_L-6, 1.6, 1.2], [sw_cx, -(SW_W/2+GAP-0.8), FLOOR+0.8]),
        box_at([SW_L-6, 1.6, 1.2], [sw_cx, (SW_W/2+GAP-0.8), FLOOR+0.8]),
        box_at([TFT_OUTER_L-8, 2.0, 1.4], [tft_cx, -(TFT_OUTER_W/2+GAP-1.2), tft_z-0.7]),
        box_at([TFT_OUTER_L-8, 2.0, 1.4], [tft_cx, (TFT_OUTER_W/2+GAP-1.2), tft_z-0.7]),
    )
    win_cx = tft_cx - TFT_OUTER_L/2 + TFT_WIN_OFF_X + TFT_WIN_L/2
    lid = diff(extrude(outer_poly, LID_H, 0),
               box_at([TFT_WIN_L+0.4, TFT_WIN_W+0.4, LID_H+2], [win_cx, 0, LID_H/2]),
               box_at([TFT_WIN_L+1.8, TFT_WIN_W+1.8, 0.7], [win_cx, 0, LID_H-0.25]),
               box_at([4.0, SW_BARREL_W+4, LID_H+1], [1.5, 0, LID_H/2]),
               box_at([4.0, SW_USB_W+4, LID_H+1], [OUTER_L-1.5, 0, LID_H/2]))
    lip_h = 1.2
    lip = extrude(translate(round_rect(CAV_L-1.0, CAV_W-1.0, max(0.6, CORNER_R-0.8)),
                            xoff=END_LIP+CAV_L/2, yoff=0), lip_h, -lip_h+0.15)
    lip_cut = extrude(translate(round_rect(CAV_L-2.6, CAV_W-2.6, max(0.4, CORNER_R-1.2)),
                                xoff=END_LIP+CAV_L/2, yoff=0), lip_h+0.4, -lip_h)
    lip = diff(lip, box_at([10, CAV_W, lip_h+1], [END_LIP+2, 0, -lip_h/2]),
               box_at([10, CAV_W, lip_h+1], [OUTER_L-END_LIP-2, 0, -lip_h/2]))
    lid = union(lid, diff(lip, lip_cut))
    lid_print = lid.copy()
    T = np.eye(4); T[2,2] = -1; T[2,3] = lid.bounds[0][2]+lid.bounds[1][2]
    lid_print.apply_transform(T); lid_print.apply_translation([0,0,-lid_print.bounds[0][2]])
    bottom.apply_translation([0,0,-bottom.bounds[0][2]])
    bottom.export(OUT/'pocket_bottom.stl'); lid_print.export(OUT/'pocket_lid.stl')
    prev = lid.copy(); prev.apply_translation([0,0,BOTTOM_H+8])
    union(bottom.copy(), prev).export(OUT/'pocket_preview_exploded.stl')
    (OUT/'case_meta.json').write_text(json.dumps({
        'version': 4,
        'layout': 'SW3518 spine: barrel flush -X, USB flush +X; TFT+Zero upper deck',
        'sw3518s_mm': [SW_L, SW_W, SW_H],
        'print_outer_mm': {'body': [round(OUTER_L,2), round(OUTER_W,2), round(SHELL_H,2)],
                           'bottom_h': round(BOTTOM_H,2), 'lid_h': LID_H},
        'ports': {'barrel': 'flush -X', 'usb_ac': 'flush +X', 'zero_usb_c': '-Y side'},
    }, indent=2))
    print('exported', OUT)

if __name__ == '__main__':
    main()
