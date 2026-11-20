# Status

Where DrMarioComboFinder stands. Updated with every chunk of work; the rules are in `CLAUDE.md`.

## Next

1. **Pad 24+:** a plain beam 8000/12000 sweep of the 19+ seeds, screened with `pad_exact.py`, gave pad 23.
   Run the same sweep on more seeds (the 18s, 1-116, 260+) and at beam 16000 on N=154.
1. **Any 27+ / pad 24+ via speed and frame phase:** a 26 that is a sure glitch 2 hit at HI passed at LOW
   (fewer score cycles), in one of five plans (animation phase). Re-screen all 24+ candidates at speeds 0 and 1,
   and add an optional wait before the trigger pill to `play_plan.lua` so "maybe" combos can be retried at
   several phases. The engine searches only score HI; add speed to the search and screens.
1. **N=218** (24 at beam 8000) and the 22-seeds (3, 28, 53, 127, 217): deep re-search like N=154's.
1. **Other levels:** levels 12-14 give much bigger combos than level 10 (28-29 at beam 8000 on a few seeds).
   Levels 11 and 15-20 did worse on seeds 1-40. Seeds 1-100 re-searched at beam 8000 give 29 on three seeds
   (level 14 N=26 and N=4, level 13 N=4), none higher at beam 16000; no pad 25. Next: seeds 200+ on levels 13-14.

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
- **Records** (HI, music off, level 10 unless noted; proven in Mesen, videos checked):
  - no controller 2: 13 kills, 70,800 points, N=31 (2026-11-14);
  - player 2 pad values: 24 kills, 666,600 points, level 14 N=26 (2026-11-19; was 23 / 594,600 on level 10);
  - player 2 any value: 29 kills, 1,034,700 points, level 14 N=26 (2026-11-19; was 25 / 738,900 and 26 at LOW / 270,500, on level 10).
- **Exact pad check** (2026-11-15, `tools/pad_exact.py`): agreed with Mesen on 103/103 passing combos
  for glitch 1. It does not check glitch 2.
- **Glitch 2 check** (2026-11-16, `tools/sprite_check.py`, engine `pad=2`): four metasprite windows after
  each match call, measured with `DRM_TRACE=1` in `lua/play_plan.lua`. Classes each pill clear, maybe or
  hit; on 154 earlier Mesen tries no "clear" fired glitch 2 and every "hit" did.
- **Glitch 3 check** (2026-11-16, `lua/play_plan.lua`, `tools/prove.py`): after each pill, the virus
  counter tiles on screen must equal `$0324`. All records re-proved with g3 = 0.
- **Any screen** (2026-11-16, `tools/pad_exact.py ... any=1`): one chain per NMI plus the sprite check.
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
- Look at the stills: the any 24 first chosen passed g1/g2 but showed 29 viruses left with 19 on the
  board. That is how glitch 3 was found.
- Re-searching the best seeds with other settings found more than scanning new seeds.
- When picking a still from a video, check the score on screen against the log: the first kill can come
  within a few frames of the trigger pill spawning.
