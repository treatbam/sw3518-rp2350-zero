#!/usr/bin/env python3
"""v7 clean STEP rebuild — parametric from case/v7_lock.json only.

Does NOT import v62 STLs as master. Exports STEP + STL per part into case/v7_step/.
Print gate: base first (glove fit).
"""
from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "v7_lock.json"
OUT = ROOT / "v7_step"


def load_lock():
    return json.loads(LOCK_PATH.read_text())


def export_part(solid: cq.Workplane, name: str):
    import numpy as np
    import trimesh

    OUT.mkdir(parents=True, exist_ok=True)
    shape = solid.val()
    try:
        solids = shape.Solids()
        if len(solids) > 1:
            fused = solids[0]
            for s in solids[1:]:
                fused = fused.fuse(s)
            shape = fused
        shape = shape.fix()
    except Exception:
        pass
    step = OUT / f"v7_{name}.step"
    stl = OUT / f"v7_{name}.stl"
    cq.exporters.export(shape, str(step))
    # Tessellate via OCCT then write through trimesh (cleaner merges than raw CQ STL)
    verts, faces = shape.tessellate(0.04, 0.15)
    v = np.array([[p.x, p.y, p.z] for p in verts], dtype=float)
    f = np.array(faces, dtype=np.int64)
    tm = trimesh.Trimesh(vertices=v, faces=f, process=True)
    trimesh.repair.fix_normals(tm)
    tm.export(str(stl))
    bb = shape.BoundingBox()
    print(
        f"  {name}: {bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm "
        f"watertight={tm.is_watertight} volume_ok={tm.is_volume} -> {step.name} + {stl.name}"
    )
    return shape


def rounded_box(wp: cq.Workplane, length: float, width: float, height: float, radius: float):
    """Centered XY rounded rect extruded in +Z from current plane."""
    r = min(radius, length / 2 - 0.05, width / 2 - 0.05)
    return (
        wp.rect(length, width)
        .extrude(height)
        .edges("|Z")
        .fillet(r)
    )


def build_base(L: dict) -> cq.Workplane:
    sw = L["sw3518"]
    mat = L["material"]
    pcb_l, pcb_w, pcb_t = sw["pcb_l_w_t_mm"]
    wall = mat["wall_min_mm"]
    gap = mat["general_gap_mm"]
    tft_l, tft_w, _tft_t = L["tft_st7735_1_8"]["outer_l_w_t_mm"]

    barrel = sw["barrel"]
    usb = sw["usb_stack"]
    end_lip = max(barrel["past_pcb_edge_mm"], usb["past_pcb_edge_mm"]) + 0.8
    outer_l = pcb_l + 2 * end_lip
    outer_w = max(tft_w, pcb_w) + 2 * wall + 2 * gap + 2.0
    corner_r = 3.0

    floor = 1.8
    well_pad = 1.0
    caps = sw["caps"]
    ind = sw["inductor"]
    hs = sw["heatsink_keepout"]
    well_z = max(caps["bore_depth_mm"], ind["height_mm"] + 0.5, hs["height_mm"] + 0.5,
                 barrel["body_l_w_h_mm"][2] + 1.0)
    solid_h = floor + well_pad + well_z  # top of solid = PCB underside plane

    # Origin: PCB center at XY=0; Z=0 at bottom print face; solid_h is top (PCB underside).
    # Build outer profile with -Y thumb flat in 2D so fillets stay manifold.
    thumb = 1.6
    y_flat = -outer_w / 2 + thumb
    # Polygon: rounded-rect approx via points + later fillet only uncut corners is hard;
    # use rect extrude, fillet, THEN a soft thumb chamfer that doesn't break shell:
    # Hard-edged outer (no fillet) — PETG glove gate; keeps STL manifold under port booleans
    base = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(solid_h)
    )
    # Thumb flat on -Y
    base = base.cut(
        cq.Workplane("XY")
        .center(0, -outer_w / 2 + thumb / 2)
        .box(outer_l + 2, thumb + 0.02, solid_h + 2)
    )

    # Registration frame outside PCB footprint (lip above solid top)
    frame_h = pcb_t + 0.6
    frame_t = 1.2
    pcb_clear_l = pcb_l + 2 * gap
    pcb_clear_w = pcb_w + 2 * gap
    # Single ring via 2D extrude cut — cleaner than union+cut overlap
    frame = (
        cq.Workplane("XY")
        .workplane(offset=solid_h)
        .rect(pcb_clear_l + 2 * frame_t, pcb_clear_w + 2 * frame_t)
        .extrude(frame_h)
        .faces(">Z").workplane()
        .rect(pcb_clear_l, pcb_clear_w)
        .cutThruAll()
    )
    base = base.union(frame)

    # Glove wells — centers from PCB center (lock)
    # Cut from above top plane downward
    def cut_from_top(solid, cutter):
        return solid.cut(cutter)

    for xy in caps["xy_from_pcb_center_mm"]:
        well = (
            cq.Workplane("XY")
            .workplane(offset=solid_h + 0.1)
            .center(xy[0], xy[1])
            .circle(caps["bore_d_mm"] / 2)
            .extrude(-(caps["bore_depth_mm"] + 0.2))
        )
        base = cut_from_top(base, well)

    ind_xy = ind["pocket_xy_mm"]
    ind_c = ind["center_from_pcb_center_mm"]
    ind_cut = (
        cq.Workplane("XY")
        .workplane(offset=solid_h + 0.1)
        .center(ind_c[0], ind_c[1])
        .rect(ind_xy, ind_xy)
        .extrude(-(ind["height_mm"] + 0.4))
    )
    base = cut_from_top(base, ind_cut)

    hs_xy = hs["pocket_xy_mm"]
    hs_c = hs["center_from_pcb_center_mm"]
    hs_cut = (
        cq.Workplane("XY")
        .workplane(offset=solid_h + 0.1)
        .center(hs_c[0], hs_c[1])
        .rect(hs_xy, hs_xy)
        .extrude(-(hs["height_mm"] + 0.4))
    )
    base = cut_from_top(base, hs_cut)

    # Port tunnels
    barrel_h = barrel["body_l_w_h_mm"][2]
    barrel_w = barrel["body_l_w_h_mm"][1]
    barrel_z = solid_h - barrel_h / 2 - 0.5
    # +X barrel body pocket + OD tunnel
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=barrel_z - barrel_h / 2 - 0.6)
        .center(outer_l / 2 - end_lip / 2, 0)
        .box(end_lip + barrel["body_l_w_h_mm"][0] + 2, barrel_w + 1.0, barrel_h + 1.2)
    )
    base = base.cut(
        cq.Workplane("YZ")
        .workplane(offset=outer_l / 2 - end_lip - 2)
        .center(0, barrel_z)
        .circle(barrel["od_mm"] / 2 + 0.3)
        .extrude(end_lip + barrel["past_pcb_edge_mm"] + 10)
    )

    # -X USB stack housing + A/C openings (C under A)
    uh_w, uh_h = usb["housing_w_h_mm"]
    ua_w, ua_h = usb["usb_a_w_h_mm"]
    uc_w, uc_h = usb["usb_c_w_h_mm"]
    house_z_bot = solid_h - (uh_h + 1)
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=house_z_bot)
        .center(-(outer_l / 2 - end_lip / 2), 0)
        .box(end_lip + 12, uh_w + 1.0, uh_h + 1.0)
    )
    usb_c_z = solid_h - 1.5 - uc_h / 2
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=usb_c_z - uc_h / 2 - 0.3)
        .center(-(outer_l / 2 - end_lip / 2), 0)
        .box(end_lip + 14, uc_w + 0.8, uc_h + 0.6)
    )
    usb_a_z = usb_c_z - uc_h / 2 - 0.6 - ua_h / 2
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=usb_a_z - ua_h / 2 - 0.3)
        .center(-(outer_l / 2 - end_lip / 2), 0)
        .box(end_lip + 14, ua_w + 0.6, ua_h + 0.6)
    )

    # Simple outer lead-ins (one-height rectangles, not stepped doors)
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=house_z_bot - 0.5)
        .center(-(outer_l / 2 - 1.0), 0)
        .box(2.5, uh_w + 3.0, uh_h + 2.5)
    )
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=barrel_z - barrel_h / 2 - 1)
        .center(outer_l / 2 - 1.0, 0)
        .box(2.5, barrel_w + 3.0, barrel_h + 2.5)
    )

    # Mount holes through (4)
    inset = sw["mount_holes"]["inset_from_edges_mm"]
    hd = sw["mount_holes"]["hole_d_mm"]
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        hx = sx * (pcb_l / 2 - inset)
        hy = sy * (pcb_w / 2 - inset)
        base = base.cut(
            cq.Workplane("XY")
            .workplane(offset=-1)
            .center(hx, hy)
            .circle(hd / 2)
            .extrude(solid_h + frame_h + 4)
        )

    # Flex / I2C channel notch on +Y rim — match lock ≥10×3 path into mid
    flex_w, flex_h = L.get("wiring", {}).get("flex_channel_min_w_h_mm", [10.0, 3.0])
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=solid_h - 0.1)
        .center(6.0, outer_w / 2 - 1.0)
        .box(max(flex_w, 10.0) + 4.0, wall + 4.0, max(frame_h, flex_h) + 2.0)
    )

    return base


def build_mid(L: dict) -> cq.Workplane:
    sw = L["sw3518"]
    mat = L["material"]
    zero = L["rp2350_zero"]
    pcb_l, pcb_w, _pcb_t = sw["pcb_l_w_t_mm"]
    wall = mat["wall_min_mm"]
    gap = mat["general_gap_mm"]
    tft_l, tft_w, _ = L["tft_st7735_1_8"]["outer_l_w_t_mm"]
    barrel = sw["barrel"]
    usb = sw["usb_stack"]
    end_lip = max(barrel["past_pcb_edge_mm"], usb["past_pcb_edge_mm"]) + 0.8
    outer_l = pcb_l + 2 * end_lip
    outer_w = max(tft_w, pcb_w) + 2 * wall + 2 * gap + 2.0
    # mid_t must be ≥ flex channel height (lock ≥3.0)
    flex_w, flex_h = L.get("wiring", {}).get("flex_channel_min_w_h_mm", [10.0, 3.0])
    mid_t = max(3.2, flex_h + 0.2)
    click_h, click_t = 1.2, 0.9
    corner_r = 3.0
    thumb = 1.6

    mid = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(mid_t)
        .edges("|Z")
        .fillet(corner_r)
    )
    mid = mid.cut(
        cq.Workplane("XY")
        .center(0, -outer_w / 2 + thumb / 2 - 0.01)
        .box(outer_l + 2, thumb + 0.02, mid_t + 2)
    )

    # Click lip ring on top
    lip_out_l = outer_l - 1.2
    lip_out_w = outer_w - 1.2 - thumb * 0.2
    lip_in_l = lip_out_l - 2 * click_t
    lip_in_w = lip_out_w - 2 * click_t
    lip = (
        cq.Workplane("XY")
        .workplane(offset=mid_t)
        .rect(lip_out_l, lip_out_w)
        .extrude(click_h)
        .cut(
            cq.Workplane("XY")
            .workplane(offset=mid_t - 0.05)
            .rect(lip_in_l, lip_in_w)
            .extrude(click_h + 0.2)
        )
    )
    mid = mid.union(lip)

    # Full PCB opening
    mid = mid.cut(
        cq.Workplane("XY")
        .workplane(offset=-1)
        .rect(pcb_l - 4.0, pcb_w - 2.0)
        .extrude(mid_t + click_h + 4)
    )

    # Zero snug pocket
    zl, zw = zero["board_l_w_mm"]
    clear = zero["pocket_clearance_per_side_mm"]
    # Place Zero toward +Y, shifted -X a bit (USB toward +Y wall)
    zero_cx = -8.0
    zero_cy = (outer_w / 2 - wall) - (zw / 2 + clear) - 1.0
    mid = mid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(zero_cx, zero_cy)
        .rect(zl + 2 * clear, zw + 2 * clear)
        .extrude(mid_t + click_h + 2)
    )

    # USB-end detent lip under connector shell (+Y short edge of Zero)
    port_w, port_h = zero["usb_c"]["port_clear_w_h_mm"]
    stick = zero["usb_c"]["stickout_past_board_mm_tunable"]
    # clean rectangle port through +Y
    mid = mid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(zero_cx, outer_w / 2 - stick / 2)
        .box(port_w + 0.8, stick + 2.0, mid_t + click_h + 2)
    )
    # detent lip: thin bar under connector (keeps board from lifting toward +Y)
    detent = (
        cq.Workplane("XY")
        .workplane(offset=mid_t - 0.6)
        .center(zero_cx, zero_cy + zw / 2 + clear - 0.4)
        .box(port_w - 1.0, 0.8, 0.7)
    )
    mid = mid.union(detent)

    # Optional haptic well
    hap = L.get("haptic", {})
    if hap:
        mid = mid.cut(
            cq.Workplane("XY")
            .workplane(offset=mid_t - hap["well_depth_mm"])
            .center(zero_cx + 2.0, zero_cy)
            .circle(hap["coin_d_mm"] / 2)
            .extrude(hap["well_depth_mm"] + 0.2)
        )

    # Flex exit +Y — lock ≥10×3 mm through outer wall (full mid height)
    ch_w = max(flex_w, 10.0) + 2.0  # 12 mm wide
    ch_h = max(flex_h, 3.0)         # ≥3 mm tall
    # Place tunnel centered in mid thickness so aperture is full ch_h on +Y face
    z0 = (mid_t - ch_h) / 2
    mid = mid.cut(
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.05)
        .center(6.0, outer_w / 2 - 2.0)
        .box(ch_w, 8.0, ch_h + 0.1)
    )
    # Also clear click-lip over the same span so lid slack isn't pinched
    mid = mid.cut(
        cq.Workplane("XY")
        .workplane(offset=mid_t - 0.05)
        .center(6.0, outer_w / 2 - 2.0)
        .box(ch_w, 8.0, click_h + 0.2)
    )

    # Mount holes
    inset = sw["mount_holes"]["inset_from_edges_mm"]
    hd = sw["mount_holes"]["hole_d_mm"]
    for sx, sy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        mid = mid.cut(
            cq.Workplane("XY")
            .workplane(offset=-1)
            .center(sx * (pcb_l / 2 - inset), sy * (pcb_w / 2 - inset))
            .circle(hd / 2 + 0.1)
            .extrude(mid_t + click_h + 4)
        )

    return mid


def build_lid(L: dict) -> cq.Workplane:
    sw = L["sw3518"]
    mat = L["material"]
    tft = L["tft_st7735_1_8"]
    btn = L["buttons"]
    zero = L["rp2350_zero"]
    pcb_l, pcb_w, _ = sw["pcb_l_w_t_mm"]
    wall = mat["wall_min_mm"]
    gap = mat["general_gap_mm"]
    tft_l, tft_w, _tft_t = tft["outer_l_w_t_mm"]
    win_l, win_w = tft["window_l_w_mm"]
    win_off = tft["window_off_x_from_tft_origin_mm"]
    barrel = sw["barrel"]
    usb = sw["usb_stack"]
    end_lip = max(barrel["past_pcb_edge_mm"], usb["past_pcb_edge_mm"]) + 0.8
    outer_l = pcb_l + 2 * end_lip
    outer_w = max(tft_w, pcb_w) + 2 * wall + 2 * gap + 2.0
    lid_h = 3.2
    click_h, click_t = 1.2, 0.9
    corner_r = 3.0
    thumb = 1.6

    lid = (
        cq.Workplane("XY")
        .rect(outer_l, outer_w)
        .extrude(lid_h)
        .edges("|Z")
        .fillet(corner_r)
    )
    lid = lid.cut(
        cq.Workplane("XY")
        .center(0, -outer_w / 2 + thumb / 2 - 0.01)
        .box(outer_l + 2, thumb + 0.02, lid_h + 2)
    )

    # Soft top chamfer via cutting a larger rect near top
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=lid_h - 0.7)
        .rect(outer_l + 2, outer_w + 2)
        .extrude(1.0)
        .cut(
            cq.Workplane("XY")
            .workplane(offset=lid_h - 0.75)
            .rect(outer_l - 2.4, outer_w - 2.4 - thumb * 0.2)
            .extrude(1.2)
        )
    )

    # Scope bezel well + window (TFT centered on case; window offset within TFT)
    # TFT origin approx -tft_l/2 relative to case center X
    tft_origin_x = -tft_l / 2
    win_cx = tft_origin_x + win_off + win_l / 2
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=lid_h - 1.2)
        .center(win_cx, 0)
        .rect(win_l + 5.0, win_w + 4.0)
        .extrude(1.3)
    )
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(win_cx, 0)
        .rect(win_l + 0.3, win_w + 0.3)
        .extrude(lid_h + 2)
    )

    # Aligned A/B plain holes beside +X of window
    btn_x = win_cx + win_l / 2 + 9.0
    bd = btn["hole_d_mm"]
    for by in (6.0, -6.0):
        lid = lid.cut(
            cq.Workplane("XY")
            .workplane(offset=-0.5)
            .center(btn_x, by)
            .circle(bd / 2)
            .extrude(lid_h + 2)
        )

    # Underside click recess
    lip_out_l = outer_l - 0.6
    lip_out_w = outer_w - 0.6 - thumb * 0.15
    lip_in_l = lip_out_l - 2 * (click_t + 0.15)
    lip_in_w = lip_out_w - 2 * (click_t + 0.15)
    recess = (
        cq.Workplane("XY")
        .rect(lip_out_l, lip_out_w)
        .extrude(click_h + 0.3)
        .cut(
            cq.Workplane("XY")
            .workplane(offset=-0.05)
            .rect(lip_in_l, lip_in_w)
            .extrude(click_h + 0.5)
        )
    )
    lid = lid.cut(recess)

    # Tray pocket underside
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.05)
        .rect(tft_l + 3.4, tft_w + 3.4)
        .extrude(1.8)
    )
    # Two catch ledges on long edges
    for sy in (-1, 1):
        ledge = (
            cq.Workplane("XY")
            .workplane(offset=1.2)
            .center(0, sy * (tft_w / 2 + 0.15))
            .box(7.0, 2.4, 0.7)
        )
        lid = lid.union(ledge)

    # Clean Zero USB rectangle on +Y
    zero_cx = -8.0
    port_w, port_h = zero["usb_c"]["port_clear_w_h_mm"]
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(zero_cx, outer_w / 2 - 2.2)
        .box(port_w + 1.0, 5.0, lid_h + 2)
    )

    # End port reliefs
    uh_w, _uh_h = usb["housing_w_h_mm"]
    barrel_w = barrel["body_l_w_h_mm"][1]
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(-(outer_l / 2 - 2.0), 0)
        .box(5.0, uh_w + 3, lid_h + 2)
    )
    lid = lid.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(outer_l / 2 - 2.0, 0)
        .box(5.0, barrel_w + 3, lid_h + 2)
    )

    return lid


def build_tft_tray(L: dict) -> cq.Workplane:
    tft = L["tft_st7735_1_8"]
    mat = L["material"]
    gap = mat["general_gap_mm"]
    tft_l, tft_w, tft_t = tft["outer_l_w_t_mm"]
    win_l, win_w = tft["window_l_w_mm"]
    win_off = tft["window_off_x_from_tft_origin_mm"]
    cart_h = 2.2
    win_cx = -tft_l / 2 + win_off + win_l / 2

    tray = (
        cq.Workplane("XY")
        .rect(tft_l + 3.0, tft_w + 3.0)
        .extrude(cart_h)
    )
    tray = tray.cut(
        cq.Workplane("XY")
        .workplane(offset=0.4)
        .rect(tft_l + 2 * gap, tft_w + 2 * gap)
        .extrude(tft_t + 0.8)
    )
    tray = tray.cut(
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(win_cx, 0)
        .rect(win_l, win_w)
        .extrude(cart_h + 2)
    )
    # Two long-edge snaps
    for sy in (-1, 1):
        arm = (
            cq.Workplane("XY")
            .workplane(offset=cart_h)
            .center(0, sy * (tft_w / 2 + 0.15))
            .box(8.0, 1.7, 2.0)
        )
        hook = (
            cq.Workplane("XY")
            .workplane(offset=cart_h + 1.5)
            .center(0, sy * (tft_w / 2 + 0.15 + 0.5))
            .box(6.0, 2.2, 0.85)
        )
        tray = tray.union(arm).union(hook)
    return tray


def build_tpu_pad(L: dict) -> cq.Workplane:
    """Optional flat TPU button pad — two posts aligned to lid holes."""
    sw = L["sw3518"]
    mat = L["material"]
    tft = L["tft_st7735_1_8"]
    btn = L["buttons"]
    pcb_l, pcb_w, _ = sw["pcb_l_w_t_mm"]
    wall = mat["wall_min_mm"]
    gap = mat["general_gap_mm"]
    tft_l, tft_w, _ = tft["outer_l_w_t_mm"]
    win_l, win_w = tft["window_l_w_mm"]
    win_off = tft["window_off_x_from_tft_origin_mm"]
    barrel = sw["barrel"]
    usb = sw["usb_stack"]
    end_lip = max(barrel["past_pcb_edge_mm"], usb["past_pcb_edge_mm"]) + 0.8
    # same win_cx / btn_x as lid
    win_cx = -tft_l / 2 + win_off + win_l / 2
    btn_x = win_cx + win_l / 2 + 9.0
    pad = cq.Workplane("XY").center(btn_x, 0).box(10.0, 18.0, 1.0)
    for by in (6.0, -6.0):
        pad = pad.union(
            cq.Workplane("XY")
            .workplane(offset=1.0)
            .center(btn_x, by)
            .circle(btn["hole_d_mm"] / 2 - 0.3)
            .extrude(2.2)
        )
    return pad


def build_zero_clip(L: dict) -> cq.Workplane:
    """Optional simple retainer clip over Zero (bar + two hooks)."""
    zero = L["rp2350_zero"]
    zl, zw = zero["board_l_w_mm"]
    clear = zero["pocket_clearance_per_side_mm"]
    bar = cq.Workplane("XY").box(zl + 2 * clear + 2.0, 3.0, 1.2)
    for sx in (-1, 1):
        hook = (
            cq.Workplane("XY")
            .center(sx * (zl / 2 + clear + 0.2), 0)
            .box(1.4, 3.0, 3.0)
        )
        bar = bar.union(hook)
    return bar


def main():
    L = load_lock()
    print(f"v7 STEP from {LOCK_PATH.name} (frozen {L.get('frozen')})")
    OUT.mkdir(parents=True, exist_ok=True)

    parts = {
        "base": build_base(L),
        "mid": build_mid(L),
        "lid": build_lid(L),
        "tft_tray": build_tft_tray(L),
        "tpu_button_pad": build_tpu_pad(L),
        "zero_retainer_clip": build_zero_clip(L),
    }
    meta = {
        "version": "7.0-step",
        "lock": "case/v7_lock.json",
        "generator": "case/generate_v7_step.py",
        "parts": [],
    }
    for name, solid in parts.items():
        shape = export_part(solid, name)
        bb = shape.BoundingBox()
        meta["parts"].append({
            "name": name,
            "bbox_mm": [round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)],
            "step": f"v7_{name}.step",
            "stl": f"v7_{name}.stl",
        })

    (OUT / "v7_step_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    readme = """# v7 STEP rebuild

Built from `../v7_lock.json` only (no v62 STL master).

## Regen
```bash
/workspace/.cadvenv/bin/python case/generate_v7_step.py
```

## Print gate
1. `v7_base.stl` — SW3518 glove dry-fit
2. `v7_mid.stl` — Zero pocket + USB detent
3. `v7_lid.stl` + `v7_tft_tray.stl`
4. Optional: `v7_tpu_button_pad.stl`, `v7_zero_retainer_clip.stl`
"""
    (OUT / "README.md").write_text(readme)
    print("done →", OUT)


if __name__ == "__main__":
    main()
