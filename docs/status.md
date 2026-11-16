# Status

Where DrMarioComboFinder stands. Updated with every chunk of work; the rules are in `CLAUDE.md`.

## Next

1. **Pad 21+:** the exact pad check (`tools/pad_exact.py`) found pad-legal 21 and 22 kill combos on N=154,
   but in Mesen (2026-11-16) both fire glitch 2 (g2 = 60). `tools/sprite_check.py` now flags all 36 of the
   known pad-legal 21/22s as sure glitch 2 hits; a search with the engine's `pad=2` filter is running.
1. **Any 24+:** re-search the best seeds (N=154, N=198 and the other 21+ seeds in 117-259) with other
   settings (beam 4000, shape 0.35 look 3); that beat scanning new seeds so far.
1. **Other levels and speeds:** only level 10 HI has been searched hard. Level 7 gave nothing and level 16
   reached 20.

## Built

- **Level generation and RNG model** (2026-11-13, `drm/gen.py`): reproduces the virus layout and pill list
  for any RNG index; checked against Mesen dumps (`lua/pick_seed.lua`).
- **Placement rules and cascade model** (2026-11-13, `drm/board.py`, `drm/plan.py`): landings, clears,
  cascades, scoring; checked against locks recorded in Mesen.
- **Glitch timing model** (2026-11-14, `drm/glitch.py`, `drm/cpu6502.py`): runs the match routines on a
  6502 core and says whether an NMI can land in a clear loop; identical timing on all 410 probed calls.
- **C++ search engine** (2026-11-14, `engine/dm.cpp`): beam search over placements;
  agrees with `drm/` on 200/200 random games. `pad=1` keeps only combos whose long match calls end on
  pad-legal fieldPos_last values (cycle model fitted on 308 calls).
- **Mesen pipeline** (2026-11-14): `lua/play_plan.lua` plays a plan and logs inputs, `tools/prove.py` checks
  every pill and both glitches, `lua/replay.lua` + `tools/make_video.ps1` make the video.
- **Records** (level 10, HI, music off; proven in Mesen, videos checked):
  - no controller 2: 13 kills, 70,800 points, N=31 (2026-11-14);
  - player 2 pad values: 20 kills, 376,500 points, N=154 (2026-11-15);
  - player 2 any value: 23 kills, 594,600 points, N=198 (2026-11-14).
- **Exact pad check** (2026-11-15, `tools/pad_exact.py`): agreed with Mesen on 103/103 passing combos
  for glitch 1. It does not check glitch 2.
- **Glitch 2 check** (2026-11-16, `tools/sprite_check.py`, engine `pad=2`): four metasprite windows after
  each match call, measured with `DRM_TRACE=1` in `lua/play_plan.lua`. Classes each pill clear, maybe or
  hit; on 154 earlier Mesen tries no "clear" fired glitch 2 and every "hit" did.
- **Repo and versioning** (2026-11-16): `VERSION` (YYYY.M.D.N), bumped by `engine/build.bat` and printed by
  `dm.exe version`.

## Not built

- Human-playable patterns: the plans are placements played by a script at HI speed; nobody has checked
  which are reachable by hand.
- Two-player mode, and levels past 20 (see `RESEARCH.md`).

## Lessons

- Search on placements, not frames. Reachability is checked only for the winners, in Mesen.
- Whether player 2 can fix glitch 1 with pad values is set by the board, not luck: an NMI lands only in
  match calls longer than about 24,000 cycles, and the value needed is that call's chain end.
- A combo that passes the glitch 1 check can still fire glitch 2; only Mesen's g2 count settles it.
- Re-searching the best seeds with other settings found more than scanning new seeds.
- When picking a still from a video, check the score on screen against the log: the first kill can come
  within a few frames of the trigger pill spawning.
