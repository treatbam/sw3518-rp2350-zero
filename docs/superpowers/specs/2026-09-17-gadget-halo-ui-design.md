# Gadget halo UI — SW3518 RP2350-Zero

Date: 2026-09-17  
Status: draft for user review  
Device: Waveshare RP2350-Zero, 1.4″ 128×128 ST7735S, two lid buttons, haptic, no Wi-Fi.

## Goal

Make the pocket meter feel like a charger-brick gadget (Anker/Ugreen), not a cramped four-page scope. Watts stay honest. Motion is in the ring, color, and haptic. This brick never has both USB-C and USB-A loaded at once.

## Personality

Bright halo around a large watt number. Green → yellow → hot orange as load climbs. Protocol flash stays a yellow chip. ASCII-only 5×7 GFX text. Full RGB565 canvas 128×128 (32 KB).

## Non-goals

- Wi-Fi, MQTT, BLE, web (GEEK)
- True efficiency (no input current)
- Settings page / power-ceiling picker
- USB-C and USB-A zoom pages
- C/A load-share bar (two-port lie)
- Auto-jump between port pages
- Arcade boot videos, page-slide chrome, particle FX
- Case CAD changes

## Pages (three)

Header crumbs: `CHG  M  S  T` plus live pip (or unlink icon if I2C down). No C/A crumbs.

| Crumb | Page | Job |
|-------|------|-----|
| **M** | Main | Halo + watts + live port |
| **S** | Session | PEAK / AVG / Wh / duration / Vpk |
| **T** | Timeline | Filled watts-vs-time for this session |

A-short cycles M → S → T → M. Page enum order is `Main, Session, Timeline` so B-short from Session goes to **Main** (previous), not Timeline.

### Main

- Status bar as above.
- Halo ring, 100 W = full circle. If live watts or session peak exceed 100 W, full-scale becomes `max(100, peakW)` for the rest of the session (does not shrink until clear).
- Center: eased `xx.xW`.
- LIVE/IDLE, protocol name (yellow invert flash 2 s on change), port badge `C` or `A` or `--`.
- One V/A line for the **active** port only (current > 50 mA). If neither, show Vin / Vout.
- Footer: `12m  1.23Wh  pk65` when session has data; else a short hint `A:page B:ses holdB:clr`.
- Unlinked: orange `CHG` + chip icon; ring empty; pages still work.

Port badge: `C` if `ic_ma` is the larger load, `A` if `ia_ma` is larger, `--` if idle. Never draw both amps on Main.

### Session

Keep the compact PEAK / AVG / Wh grid, Vpk, duration. Drop the two spark bands (those live on T). Use the bright palette (cyan labels, hot orange Wh).

### Timeline

One series: total watts vs session time, filled area, yellow/orange stroke, dashed vertical at peak sample. Caption: duration, `pk`, live port + protocol. Empty state: `no session`. History buffer remains the existing session hist (store **total W**, not dual C/A traces). Rebin/downsample behavior stays.

## Motion

- I2C snapshot ~200 ms (unchanged).
- Face redraw ~50 ms (≈20 Hz). Display watts and ring angle **ease** toward the latest snapshot (exponential, time-constant ~120 ms). Protocol text, port badge, and LIVE/IDLE snap on the sample.
- Color of the ring (and watt glow) from load fraction of current full-scale: low green, mid yellow, high hot orange. Bright (high saturation), not the old dim 0x07E0-on-black.
- Peak-hold: when a new session peak lands, show `pk HOLD` ~1.5 s and a tick on the ring. Haptic tick.
- Night dim: 90 s after last **button** or **plug** (load 0→1). Buttons or plug restore full backlight. Charging alone does not prevent dim.

## Haptic

| Event | Pulse |
|-------|--------|
| Plug (load appears) | Single punch ~40 ms |
| Unplug (after 1.5 s debounce) | Down-slide ~80 ms softer |
| Protocol change | Double-tap |
| New peak | Short tick |
| Page change | Existing light pulse |
| Clear session | Existing longer pulse |
| A-long | Wake backlight; light pulse (not a settings menu) |

No haptic when I2C is lost (avoid alarm spam).

## Buttons

Hardware stays two lid buttons.

| | Short | Long (~800 ms) |
|---|---|---|
| **A** | Next page M/S/T | Wake backlight + pulse |
| **B** | Jump Session; if already Session, previous page | Clear session in RAM **and** flash; haptic; go Main |

Glance path: no press required. Watts and ring run themselves.

## Persistence

Always on. No toggle.

- **Save:** session scalars only — `chargedMs`, `mwh`, `peakW`, `peakA`, `peakVoutMv`, port peak structs, `startMs` identity as needed, phase as Idle/Paused after restore. **Do not** persist the timeline sample buffer (T starts empty after reboot; S still shows totals).
- **When:** on unplug debounce (session becomes Idle with data), every 10 s while Running, and on clear (write empty record).
- **Where:** flash-backed EEPROM blob (Arduino-Pico EEPROM, versioned packed struct, magic + version). Fits in well under 4 KB without LittleFS.
- **Boot:** if magic/version match and there is data, `adoptPersisted()` so the clock does not bill the off-time.
- **Clear:** B-long wipes RAM and the blob.

Host tests: persist round-trip, adopt-does-not-integrate-gap, clear-wipes-blob (blob encode/decode in a portable helper, no Arduino in the test).

## Data / session

Existing `Session` + `Link`/`Phase` stay canonical. Changes:

- History is **one** `histW[]` (total watts), not `histC`/`histA`. Downsample unchanged.
- `onTick` unchanged in spirit (pause on `Link::Lost`, unplug debounce, no gap billing).
- UI must not integrate energy; only Session does.

## Architecture (firmware)

Do not dump this into a 1k-line `main.cpp`. Split:

| Unit | Owns |
|------|------|
| `sw3518` | I2C snapshot (exists) |
| `session` | energy, peaks, histW, persist encode/decode (exists; extend) |
| `ui` | halo, easing, pages M/S/T, palette, crumbs |
| `main` | pins, buttons, haptic, backlight, 50 ms / 200 ms ticks |

`ui` draws from: latest snapshot, eased display watts, Session, charger present, millis.

Interpolator lives in `ui` (not Session). Tests cover Session + persist only.

## Loop

```
50 ms:  haptic; buttons; ease toward last snap; drawFrame
200 ms: readSnapshot or probe; Session.onTick; maybe persist; protocol/peak/plug haptic edges
```

If snapshot fails: `Link::Lost`, clear live snap, pause session, unlink icon.

## Testing

- Keep `make -C tests test`.
- Add persist blob round-trip and “restore does not add off-time energy.”
- Add histW downsample still halves count / doubles period.
- No hardware-in-loop required for this spec.

## Risks

- ST7735 brightness is panel-limited; “brighter” is palette (not PWM-to-11). Backlight PWM stays 255 when awake.
- 20 Hz full-canvas blit is fine on RP2350 (32 KB SPI). If it stutters, drop to 15 Hz, keep easing.
- EEPROM wear: 10 s writes while charging are acceptable for hobby flash; only write if `dirty`.

## Locked decisions

1. Halo Main, filled Timeline, numbers Session.
2. Drop C/A pages, crumbs, and share bar.
3. Brighter gadget palette; 100 W halo, grows if exceeded.
4. Ease ring + watts; full haptic language above.
5. Keep A/B; no settings page.
6. Persist stats always; not the spark buffer.
7. Case files untouched.
