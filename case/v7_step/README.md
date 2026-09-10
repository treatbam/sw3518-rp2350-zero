# v7 STEP rebuild

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
