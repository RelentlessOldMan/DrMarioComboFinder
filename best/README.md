# Records

Level 10, speed HI, music off, NTSC PRG0. Each record has two files:

- `<name>.plan`: one line per pill, `rot x`: the rotation (0–3) and the column (0–7) the pill ends up in.
  The level starts at the RNG index in the table below (`lua/play_plan.lua`, `DRM_N`); the last line is the
  pill that sets off the combo.
- `<name>.inputs`: the exact run Mesen played, one line per frame: `frame p1 p2`, the frame
  number counted from power-on and both controllers' buttons in hex (A=80 B=40 Select=20 Start=10 Up=08
  Down=04 Left=02 Right=01). Player 2's values during the combo are what fix glitch 1. Replay it with
  `lua/replay.lua` (`DRM_INPUTS=<name>.inputs`).

| Name | RNG index | Pills | Kills | Points | Player 2 holds |
|---|---|---|---|---|---|
| `nop2_13` | 31 | 23 | 13 | 70,800 | – |
| `pad_20` | 154 | 23 | 20 | 376,500 | `$75 $5A $58` |
| `any_23` | 198 | 63 | 23 | 594,600 | `$4F $62 $76 $67 $67 $7E` |

Final scores on screen: 72,300, 377,100 and 595,200 (the combo plus a few small clears earlier on).
