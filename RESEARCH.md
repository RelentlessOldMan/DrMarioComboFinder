# Dr. Mario (NES) research notes

Collected 2026-11-13 from disassemblies, TASVideos, speedrun.com (via its API) and community repos.
Tags: **[DISASM]** read in the disassembly source (both disassemblies rebuild byte-identical ROMs, so
this is effectively primary); **[DISASM-inferred]** our reading of code paths, to confirm in the
emulator; **[TAS]** TASVideos submission texts; **[UNVERIFIED]** snippets / single weak source.

Local copies of the disassemblies are in `ref/` (no licenses on either repo, and the Nostaljipi one
contains `bin/drmario_chr.bin`, game graphics, so `ref/` must stay out of any public repo):
- `ref/nostaljipi-disasm/` - https://github.com/Nostaljipi/dr-mario-disassembly (ASM6f, Rev A, well commented)
- `ref/brianhuffman-disasm/` - https://github.com/brianhuffman/drmario (ca65, one file, builds PRG0 and Rev A)

---

## 1. Emulator choice

**Pick: Mesen 2 - MesenCE 2.2.1** (https://github.com/nesdev-org/MesenCE/releases/download/2.2.1/Mesen_2.2.1_Windows.zip).
Upstream SourMesen/Mesen2 was archived at 2.1.1 (July 2025); MesenCE is the maintained fork.

### Speedrun acceptance
- **SMB1 board** (speedrun.com/smb1, rules read via API): accepted NES emulators are Nestopia, NestopiaRTA,
  BizHawk (NesHawk core only), OpenEmu (Nestopia core), MesenRTA (threecreepio), **Mesen2-RTA (108Pi)**.
  Stock Mesen is banned only because mods can't verify run-ahead is off - the RTA builds exist for that.
  **FCEUX banned for new SMB1 runs since 2023-09-17** over accuracy.
  Mesen2-RTA 0.1.0: https://github.com/108Pi/Mesen2RTA/releases (a MesenCE fork; its diff touches HUD/timer/
  savestate/cheat code, not `LuaApi.cpp`/`TestRunner.cs` - unverified that Lua still works there).
- **Dr. Mario board** (speedrun.com/drmariones): no emulator list of its own; points to the shared NES rules doc
  (https://docs.google.com/document/d/1apP69VDIzUx-iVO_sj5YjTxBAE2ukHPa6kl33AOW9hA): "Mesen, Bizhawk/NEShawk,
  puNES, Nestopia and FCEUX are the most acceptable emulators, listed in order of accuracy".
- Published Dr. Mario TASes used FCEUX 2.1.0a (2009) and BizHawk 2.3.x (2018-19).

### Mesen 2 Lua / CLI (from source; docs https://www.mesen.ca/docs/apireference.html, `Core/Debugger/LuaApi.cpp`)
- Memory: `emu.read/write(addr, memType[, signed])`, `read16/write16`, debug memTypes with no side effects.
- Callbacks: `emu.addMemoryCallback(fn(addr,val), emu.callbackType.read|write|exec, start[, end])` (may return a
  value to override); `emu.addEventCallback(fn, emu.eventType.nmi|irq|startFrame|endFrame|reset|inputPolled|stateLoaded|...)`.
- Savestates: `emu.createSavestate()` -> string, `emu.loadSavestate(str)`. **Gotcha: only allowed inside an
  exec memory callback** on the main CPU (not from startFrame).
- Input: `emu.setInput({a=true,right=true,...}, port)` inside an `inputPolled` callback.
- Control: `emu.reset`, `emu.stop(exitCode)` (help text says `emu.exit`, but the function is `emu.stop`).
- Video: `emu.takeScreenshot()` (PNG bytes), `emu.getScreenBuffer()`. **No AVI from Lua/CLI** - AVI recorder is GUI only.
- Sandbox: `io`/`os`/`require`/sockets off by default (`AllowIoOsAccess`, `AllowNetworkAccess`);
  `ScriptTimeout` 1 s per callback. Probably settable via `--debug.scriptWindow.allowIoOsAccess=true` (untested)
  or once in the GUI.
- Headless: `Mesen.exe --testRunner script.lua rom.nes [--timeout=N]` - no audio/video/input, max speed, exit code
  = `emu.stop` value; -1 on load failure or timeout. **Default timeout 100 s.**
- Video plan: replay winners in GUI Mesen (AVI recorder, with audio), or dump `getScreenBuffer` frames to ffmpeg.

### Runner-up: BizHawk 2.11.1 (NesHawk)
Full Lua (`memory.*`, `joypad.set`, `savestate.*`, `memorysavestate.*`, `event.onmemorywrite/execute`, `client.speedmode`,
`movie.*`) and fully scripted video: `EmuHawk --movie=x.bk2 --dump-type=ffmpeg --dump-name=out.mkv --dump-length=N --dump-close rom.nes`.
No true headless mode, probably slower. Nestopia has no Lua. FCEUX 2.7.0 has good Lua but is the least accurate.

**Rule:** search and render in the same emulator; RNG depends on frame timing.

---

## 2. ROM revisions
- TASVideos uses **Dr. Mario (JU) PRG0**, SHA-1 `01DE1E04C396298358E86468BA96148066688194`.
- Rev A (PRG1) changes [DISASM, brianhuffman `REV_A` conditionals]: PPUMASK shadow at $FE written in NMI/reset/pause,
  cold boot fills page $07 with $FF, title checksum constant, music clamp. **No change found to RNG, virus
  generation or scoring.** Rev A's NMI is a few cycles longer, which could shift lag / glitch timing (speculative).
- Routine addresses differ (PRG0 vs Rev A), RAM addresses don't. E.g. LFSR step PRG0 $B771 / Rev A $B78B;
  add-virus PRG0 $9CFF / Rev A $9D19; game mode `levelIntro` = 8 in PRG0, 7 in Rev A.

---

## 3. RNG [DISASM]
- 2 bytes at **$17/$18** ($17 high). `r = ($17<<8)|$18`; step:
  `bit = ((r>>1) ^ (r>>9)) & 1;  r = (r>>1) | (bit<<15)` (x^15+x^7+1 family). **Period 32,767.**
- Seed **$8988** on power-on *and* soft reset.
- Stepped in exactly three places: (a) **once per frame on the level/speed options screen**, before the START check
  (so minimum 1 step); (b) once per pill in pill-list generation (128 steps); (c) inside add-virus.
  Not on the title screen, not during play, not between levels. 2P garbage columns use the frame counter $43.
  Sound noise has its own LFSR at $EB/$EC.
- Consequence: the first level is fully determined by (frames spent on the options screen since power-on/reset
  [+128 per attract demo, inferred], virus level). Later levels in a continuous run follow from the previous
  level's end RNG state - a fixed chain. TASers soft-reset to pick layouts [TAS].
- Speed (LOW/MED/HI) does not affect generation.

## 4. Level generation [DISASM]
Order in `initData_level`: pill list first (128 RNG steps), then viruses, one `addVirus` per frame.

### Pill list ("reserve")
- 128 entries at **$0780-$07FF**, written from index 127 down to 0.
- `id=0`; per pill: step RNG; `id = (id + ($17 & $0F)) mod 9`; store id. Not uniform - a running sum mod 9.
- id -> colours: left = id/3, right = id%3 (0=Yellow, 1=Red, 2=Blue).
- Shared by both players in 2P (separate counters $0327/$03A7). Counter `& $7F`: the sequence loops every 128 pills.
- [EMULATOR-verified 2026-11-13] first controlled pill is reserve[0] ($0780), next shown reserve[1]; pill counter $0327 = 2 at level start. RAM $0480-$048F read as FF during generation (beyond bytes). START timing: pressing START when the options loop has stepped N times gives index N exactly (6/6 seeds matched: lua/pick_seed.lua + tools/check_pick.py).

### Viruses (`addVirus`, Rev A $9D19)
- Count = 4*(level+1), max 84 (levels >20 capped).
- 1. Height: loop { step RNG; h = $17 & $0F } until h <= maxHeight[level].
  maxHeight (table $A3F8): levels 0-14 -> 9, 15-16 -> 10, 17-18 -> 11, 19+ -> 12 (i.e. bottom 10/11/12/13 rows).
  (tetris.wiki puts the steps one level later - trust the disassembly.)
- 2. Column: x = $18 & 7 (no extra step). pos = 8*(15-h)+x (0 = top-left, $7F bottom-right).
- 3. Colour: c = virusesLeftToAdd & 3. If c==3: step RNG, c = table[$18 & $0F] with
  table = `0,1,2,2,1,0,0,1,2,2,1,0,0,1,2,1` (each group of 4 = one of each colour + one random).
- 4. Scan forward from pos to the first empty cell ($FF). If pos hits 128, abandon; retry next frame with new draws.
- 5. Neighbour mask: OR colours exactly 2 cells away (up pos-16; down pos+16 if pos<112; left pos-2 if col>=2;
  right pos+2 if col<6). Y=1,R=2,B=4. If mask==7, pos++ and go to 4.
- 6. While colour in mask: colour = colour-1 wrapping (Y->B->R->Y).
- 7. Write $D0|colour, decrement count.
- 2P with equal levels: both players get the same field (per code comment, copy not traced).

### Distinct levels
At most **32,767 (layout, pill list) pairs per virus level**, all reachable at the first level by waiting
1..32,767 frames on the options screen. 21 selectable levels x 32,767 = ~688k boards. Nobody has published a
"best combo per seed" table that we found.

### Reimplementations (useful to cross-check ours)
- taotao54321, "NES Dr.Mario hand simulator" (Python): https://gist.github.com/taotao54321/4ec019a251fdd8f9759fa8a8b5439559
  `hand.py <level 0..20> <rand_idx 0..32766>`; checked line-by-line against the disassembly by our research agent.
- trangqngo/Dr-Mario-virus-generation (Python, NES/GB/SNES/N64): https://github.com/trangqngo/Dr-Mario-virus-generation
  + papers by Ngo & Williams: "Dr. Mario Virus Generation" (FDG '22) and "Entropy Lost" (https://www.pcgworkshop.com/archive/ngo2022entropylost.pdf).
- nightmareci's C port of the generator: https://tetrisconcept.net/threads/dr-mario-virus-placement.2037/
  (same thread: dmhero's seed-select mod).

---

## 5. Scoring and combos [DISASM]
- Score only in 1P. 6 digits at **$0729-$072E** (+ a fixed trailing 0 on screen); high score $0700-$0705.
- **Per virus**: points = base x M[k], base = 100/200/300 for LOW/MED/HI. k = viruses already killed since
  the current pill locked. **k resets only when a new pill locks**, so the multiplier runs over the whole cascade.
- M table (Rev A $A239 / PRG0 $A21F): `1 2 4 8 16 32 32 32 32 32 32`, i.e. 100,200,400,800,1600,3200,3200... at LOW.
- **No bounds check**: virus 12 -> x10, 13 -> x3, **14 -> x256** (byte $00, `dex` loop runs 256 times), 15 x1, 16 x2,
  17 x4, 18 x256, 19 x252, 20 x248, 21 x244, ... (reading the following ROM bytes).
- Clean (no-glitch) max per pill on HI: 11 viruses = 300 x 223 = 66,900; 13 viruses = 300 x 236 = 70,800 (derived, check in emulator).
- **Big combo / "remove" glitch** [TAS + DISASM]: on the 14th virus of a chain the 256-iteration add loop
  overruns the frame; the NMI's controller polling clobbers shared zero-page $48-$49 and the field processing is
  corrupted. Vertical final removal clears the whole column; horizontal clears that row and everything below.
  The game can hang until a P2 controller button is pressed. TASes use it to clear levels instantly
  (https://tasvideos.org/6518S, https://tasvideos.org/Forum/Posts/473412, https://tasvideos.org/2250S).
  TAS texts also say killing viruses 3-10 simultaneously can trigger it. Letters can appear in the score.
  **For us: a clean simulator is exact only up to 13 viruses per pill; past that, the emulator is the truth.**
- Score cap: no hard cap. Normalize decrements the top digit at 10, so after 9,999,999 it wraps to 9,0xx,xxx.
  Confirmed by CtrlAltDestroy's "Quest for Ten Million Points" (https://tasvideos.org/Forum/Posts/200553).
- 2P combo counter `comboCounter` ($8F / $030F) counts *match lines* (each 4+ group) across a pill's cascade;
  >=2 lines sends that much garbage (2-4) to the opponent.
- Records: Guinness - Will P. Nichols 2,922,600 (HI), 2011. Twin Galaxies MED 2,010,400 (2010) [UNVERIFIED].
  No documented "biggest legit chain" record found. No theoretical max-chain analysis found.

---

## 6. Levels past 20 [DISASM]
- Select stops at 20. After a 1P clear the level increments unless it's already 24, so **24 repeats forever** -
  no wrap, no crash, no kill screen. Levels 21-24 play exactly like 20 (84 viruses, max height 12; the
  "extra speed = level-20" write at $826D is dead code).
- Ending triggers when speed is HI and level becomes 21.
- Within a level: speed-up every 10 pills, capped at 49. HI's last index reads one past the table -> $00 -> 1 frame/row (reading).
- Different: PlayChoice-10 prototype places viruses higher on 23-24, level 25 has viruses in the top row
  [UNVERIFIED]. Game Boy version has a level-28 kill screen. The TASVideos level 0-255 speed thread is SNES.

---

## 7. RAM map [DISASM; agrees with https://datacrystal.tcrf.net/wiki/Dr._Mario/RAM_map]
Zero page: `$17/$18` RNG; `$43` frame counter; `$46` mode (0 toTitle, 1 options/demo, 2 toLevel, 3 initData_level,
4 level main loop, 5 player loses, levelIntro 8 PRG0 / 7 Rev A); `$58` current player (4=P1, 5=P2);
`$F5/$F6` buttons pressed P1/P2, `$F7/$F8` held. `$80-$AF` = working copy of the current player's block.

Player block P1 `$0300-$032F` (P2 `$0380-$03AF`, same layout):
| addr | meaning |
|---|---|
| $0300 | status (row being redrawn, $FF idle) |
| $0301/$0302 | falling pill colours (0Y 1R 2B) |
| $0305 | pill X (0-7) |
| $0306 | pill Y (0 = bottom, 15 = top) |
| $0307 | pill-placed step |
| $0309 | fail flag |
| $030A | speed-ups |
| $030B | speed setting 0/1/2 (Data Crystal's "$26-$85" is wrong) |
| $030F | combo counter (lines) |
| $0310/$0311 | pill count (BCD) |
| $0312 | gravity frame counter |
| $0313 | horizontal DAS counter |
| $0314 | match flag |
| $0316 | virus level |
| $0317 | nextAction |
| $031A/$031B | next pill colours |
| $0320 | speed index |
| $0324 | viruses left (BCD) |
| $0325 | rotation 0-3 |
| $0327 | pill reserve index |
| $0328 | viruses still to add |
| $032D | score multiplier index k |

Playfield P1 **$0400-$047F**, P2 $0500-$057F: index = row*8+col, row 0 at top. Cell = type<<4 | colour:
$4x top half, $5x bottom half, $6x left half, $7x right half, $8x single (loose) half, $9x/$Ax middle (unused),
$Bx cleared, $Dx virus, $Fx just emptied, $FF empty.

Other: $0700 high score; $0723 bypass speed-up flag, $0724 "pills stay mid-air" (prototype debug flags);
$0725 wins needed; $0727 players; $0728 levels over 20; $0729 score; $0740 anti-piracy flag (checksum of
$B900-$BDFF, crashes on pill land); $0741 demo recording; $0780-$07FF pill reserve.

---

## 8. Mechanics for a simulator [DISASM]
- Board 8x16. Spawn X=3, Y=15 (top row), rotation 0 (horizontal). Blocked spawn = loss. A half above the top row is dropped.
- **Gravity**: counter++ each frame; drop when counter > speedCounterTable[base + speedUps] (frames/row = value+1).
  base 15/25/31 for LOW/MED/HI. NTSC table (81 entries, Rev A $A7AF):
  `45 43 41 3F 3D 3B 39 37 35 33 31 2F 2D 2B 29 27 25 23 21 1F 1D 1B 19 17 15 13 12 11 10 0F 0E 0D 0C 0B 0A 09 09 08 08 07 07 06 06 05 05 05 05 05 05 05 05 05 05 05 05 04 04 04 04 04 03 03 03 03 03 02 02 02 02 02 01 01 01 01 01 01 01 01 01 01 00`.
  Start: LOW 40 frames/row, MED 20, HI 14. Speed-up every 10 pills (BCD low digit hits 0), cap 49; first
  speed-up lands on the 9th pill played [inferred].
- **Soft drop**: Down checked only every other frame (`frameCounter & 1`; TAS: "even frames"); 1 row per 2 frames; resets the gravity counter.
- **No lock delay**: locks on the first failed downward move.
- Within a frame: Y move, then X move, then rotate.
- **DAS**: press moves immediately; first repeat 16 frames after, then every 6 (PAL 13/5). Blocked move sets the
  counter to 15 (moves the first frame it's free). Left and Right both processed in one frame.
- **Rotation**: A: rot=(rot-1)&3, B: (rot+1)&3 (both if same frame). 2x2 box anchored bottom-left.
  To horizontal: if blocked, try X-1 (kick); if that works while Left is held, try another X-1 (TAS "double left",
  A+B+Left). To vertical: in place, no kick. Vertical pill occupies (x,y),(x,y+1).
- **Clear loop** after lock: resetCombo -> checkDrop (repeat until nothing falls) -> resetMatchFlag ->
  checkHorMatch -> checkVerMatch -> updateField; if matched, back to checkDrop. Horizontal scan marks $Bx (keeps
  colour); vertical scan on the same board, so crosses/L shapes clear both. Run = 4+ same colour.
  updateField turns orphaned halves into singles ($8x), cleared cells into just-emptied.
- **checkDrop**: scan bottom-right to top-left; any non-virus non-cleared piece over empty falls 1 row; horizontal
  pills only if both cells below are empty; vertical pills and singles fall as units. Repeat passes until stable.
  Each pass waits for the NMI to redraw the field (one row per frame), so ~16 frames per cascade row - timing only.
- Mario's throw animation precedes each pill; on LOW it advances every other frame (LOW slower; MED = HI) [TAS].

---

## 9. TASVideos (game page https://tasvideos.org/518G)
| movie | author(s) | goal | time | emulator | notes |
|---|---|---|---|---|---|
| 4058M (6518S) | poco_cpp, inari80000, tas_suki, 2019 | all levels 0-20 HI | 5:43.00, 20,614 f | BizHawk 2.3.2 | current; console-verified; soft-reset layout picking; remove glitch |
| 3909M (6272S) | poco_cpp, 2019 | all levels | 6:20.76 | BizHawk 2.3.0 | obsolete |
| 3819M (6123S) | poco_cpp, 2018 | all levels | 6:44.03 | BizHawk 2.3.0 | obsolete |
| 1290M (2250S) | CtrlAltDestroy, 2009 | level 20 HI | 1:12.83, 4,377 f | FCEUX 2.1.0a | Alternative class; P2 unfreeze |
Rejected: 417S, 418S (2004, FCEU), 6052S (0:22.96, documents remove-glitch directions + A+B+Left), 6122S (0:16.16).
"Fastest crash" 688 frames, TaoTao 2018 (FCEUX) - from the user's notes, not re-verified.

---

## 10. Other projects (for reference / cross-checking)
- dmwit (Daniel Wagner), mostly Haskell, BSD-3: **maryodel** (pure-Haskell NES Dr. Mario model + pathfinding + FCEUX
  Lua server, https://github.com/dmwit/maryodel), nurse-sveta (MCTS + NN AI), dasyuridia (drive the real game from an
  AI via FCEUX Lua), bokrifulse (FCEUX Lua maneuver trainer), nostramario (board from video), dr-mario-ngrams.
- meatfighter Dr. Mario AI (Java on Nintaco, LGPL; BFS over lock placements; reaches 24 forever): https://meatfighter.com/drmarioai
- struktured-labs/dr-mario-te: FPGA expectimax AI + "Dr. Mario Training Edition" ROM hack.
- mstan/DrMarioNesRecomp: static recompilation to C (possible fast exact engine!).
- Others: leerieo/DrMarioAi_ThesisProject, Jonny5-5/Dr-Mario-AI, cbpetersen/dr-mario-engine, fogleman/DrMario.
- Community: Dr. Mario Championship (DrMC, 2P versus, since 2017), a Dr. Mario Discord with a tools channel.

## Seed control and endless play (verified 2026-11-13)
- START timing picks the seed exactly. 16/16 test seeds across levels 0, 10 and 14–20 (N up to 32,766) matched `drm/gen.py` on every virus and all 128 pills (`lua/pick_seed.lua`, `tools/check_pick.py`).
- Neighbouring N often give the same virus board with different pills. The height-rejection loop pulls a shifted RNG stream back into sync.
- The RNG has only 4 call sites: the options loop, pill reserve, and addVirus x2. Player input never affects it, so N plus the start level fixes every board of the whole game.
- `p1_level` stops at lvCap (24). Each level past 20 starts `lvlsOver20` speed steps further along, so level 24 starts +4 steps. Endless play replays level 24.
- Level-24 chain (`tools/level_chain.py`): the 32,767 states map onto only 9,473 next-states, and **all of them end in a single cycle of 127 boards**. Endless play is the same 127 level-24 boards in a loop.
  - Assumes $0480–$048F are still FF at later level starts; this has only been checked at the first level.

## Placement rules simulator (verified 2026-11-13)
- `drm/board.py` copies checkDrop / checkHorMatch / checkVerMatch / updateField / scoreIncrease on the game's own RAM bytes. It has no frames, inputs or gravity timing.
- Verified against the game with `lua/rules_check.lua` + `tools/check_rules.py`: random boards (viruses, singles, floating halves and pills), a pill teleported above a random column and dropped. **430/430 locks matched** on final field, kill count ($AD) and score delta. Kills per lock ranged 0–7.
- Rules worth remembering:
  - Each pass drops every unsupported piece one row; a horizontal pill drops only if both cells under it are empty.
  - Matches are checked only once nothing moves.
  - Hor and ver are checked in the same step, and cells already cleared in that step still count for colour. So crosses work whichever end the shared cell is on.
  - Kill k of a pill pays MULT[k] x (speed+1) x 100. MULT is the ROM table, not capped: 1,2,4,8,16,32x6,10,3,256,1,2,4,256,252,248,244,242,241,240,241,242,244,248,252,256,21,24,32,256,...
  - The loss check is only "the spawn cells (row 0, cols 3-4) are occupied when the next pill is sent".
- Not yet modelled: whether a step overruns the frame (the glitch). Kills of 12+ are untested in the emulator.

## Glitch timing model (verified 2026-11-14)
- `drm/cpu6502.py` is a small cycle-counting 6502. It runs the game's own checkHorMatch / checkVerMatch / scoreIncrease from the PRG ROM on a RAM image. It is cycle-exact against Mesen (`tools/check_timing.py`: 382/410 calls exact; the rest are 16–94 cycles longer in Mesen, from DMC sample DMA in the music).
- The RAM image needs only the field, the kill counter ($AD), speed ($8B) and score; the rest comes from `drm/ram_template.hex`. This gives identical timing on all 410 calls.
- Measured (music Fever, `tools/timing_stats.py`):

  | Quantity | Measured |
  |---|---|
  | Frame | 29,775–29,787 cycles |
  | Match routine start after the NMI | 5,762–5,912 cycles |
  | NMI handler cost when it interrupts a routine | 1,925–2,282 cycles |
  | scoreIncrease | about 36 + 93 x MULT[k] cycles, so a x256 kill is about 23,800 cycles, nearly a whole frame |

- Two ways a big combo breaks:
  1. **An NMI inside a clear loop.** `$49` there is `fieldPos_last`, the field index just past the chain being cleared. The NMI's getInputs stores **player 2's raw held buttons** in `$49` (tmp49), so the loop stops at the wrong place: a horizontal clear runs on through $04xx, and a vertical one can loop forever. Window: `sta fieldPos_last` ($925F/$94C5) to the `lda fieldPos_last` after the loop ($92A2/$9505).
  2. **An NMI inside the sprite update after a long routine.** metaspriteUpdate keeps its data pointer in tmp47/48. getInputs stores **player 1's raw held buttons** in tmp48, and the loop can spin forever looking for its $80 end marker. Seen in Mesen: a hang in step 7 with the PC in $890A–$8937. Metasprite calls span +1,069..+5,750 cycles after the routine exits, in every music setting. An NMI elsewhere in the tail (exit to the $B662 wait loop, 6,529–9,880 cycles) should only cost a lag frame (not separately verified).
- In Mesen, restoring `$49` alone made all 68 such trials end exactly as `drm/board.py` predicts, so `$49` is the only damage.
- **Player 2 can make glitch 1 harmless.** If player 2 holds the buttons whose bits equal that chain's `fieldPos_last` (A=$80, B=$40, Select=$20, Start=$10, Up=8, Down=4, Left=2, Right=1) on the frame the NMI hits, getInputs writes the same value back. Verified in Mesen (`DRM_P2FIX=1`, `out/timing_p2fix.jsonl`): 40 NMIs landed inside clear loops, up to 5 in one pill, `$49` never changed, and every board resolved correctly. Caveats:
  - Values with both Left+Right (bits 0+1) or both Up+Down (bits 2+3) are possible in Mesen but not on a real d-pad.
  - The same trick for glitch 2 would need player 1 to hold the pointer's high byte ($A9–$B0). Only $A9 and $AA are possible on a real pad, so glitch 2 is avoided by timing instead.
  - Mesen runs this ROM as a Famicom: in Lua, player 2 is `emu.setInput(t, 0, 1)`, not port 1.
- Timing profiles (`tools/timing_stats.py`): with music off, the NMI range widens by about 115 cycles per NMI crossed (handler 1,936–2,050, no DMA). With music on, it widens by about 430 cycles per NMI plus up to 1.5% DMA stretch.
- `drm/glitch.py` puts every possible NMI on the routine's exact cycle timeline, using the ranges above with margins, and calls the call safe only if no NMI can hit a clear loop or the 10,500-cycle tail. Against Mesen it caught all 32 real hazards with none missed, and gave 4 false alarms (`tools/check_glitch.py`).
- `drm/combo.py` `evaluate()` resolves a lock with board.py and times every match call. It matches all 400 rules trials.
- What this means:
  - **Without player 2:** each x256-class kill (k=13, 17–29, 33, 37, ...) takes almost a whole frame, so each must have its own gap between NMIs, with the NMI in the short unarmed scan between chains. A full board scan has only about 4.4k (hor) / 5.3k (ver) unarmed cycles in total, which caps it at about 2 heavy kills with music and about 6 without.
  - **With player 2 holding the right buttons:** the glitch no longer limits combo size. Each NMI's possible range only has to touch one chain (so the right buttons are known), and the routine must end where no NMI can land in the sprite update (`glitch.safe_call(..., p2=True)`). Kills ($AD) count viruses, so the limit becomes how many viruses one pill can clear: 84 viruses at HI speed would be about 2.49M points.

## Plan, play, replay pipeline (verified 2026-11-14)
- `drm/plan.py` searches placements (rotate at the top, slide along rows 0-1, drop). `tools/find_combo.py` /
  `tools/scan_seeds.py` run it. The `shape` heuristic (score half-built one-colour lines that contain a
  virus) finds bigger chains: N=31 level 10 went from 4 to 6 kills with shape=0.05.
- The first pill played is reserve[1]. Rotation layouts: 0 = c1|c2, 1 = c2 over c1, 2 = c2|c1 (seen in
  play), 3 = c1 over c2 (assumed, not yet seen in a checked run).
- `lua/play_plan.lua` plays a plan and logs every input poll; `tools/check_play.py` compares each pill's
  landing, its post-cascade field, and its score with drm/plan.py. N=31 level 10, MED, Fever: 9/9 pills
  match, last pill clears 6 viruses for 12,600; total 13,200.
- `$0317` is written with 1 more than once per pill (again during the cascade), so the landing snapshot
  must take the first write only.
- N must leave time to set the level before START: N=5 at level 10 was missed (needs more RNG steps
  than the title screen gives).
- `lua/replay.lua` replays the log from power-on: same score (13,200 at frame 1,091), so the log is
  enough to reproduce a run. `tools/make_video.ps1` dumps frames (emu.getScreenBuffer) and encodes
  them with ffmpeg at 3x, no audio. Paths passed to Mesen must be absolute.

## C++ search engine and the no-player-2 record (verified 2026-11-14)
- `engine/dm.cpp` (build: `engine\build.bat`, VS2022, OpenMP) ports level generation, the board rules
  and the drop-only move model. `tools/check_engine.py` checks it against drm/ on random games. It is about
  250x faster than plan.py single-threaded, and about 5x more again with OpenMP.
- `dm search` is a beam search over placements. A state's value is: look x (best kills for the next pill)
  + shape x setup_value - waste x (viruses killed before the trigger) - height x (cells in rows 0-4).
  It prints every big combo it sees as a JSON line. Beam size is not monotonic: at level 10, depth 80,
  beam 2000 found 15/16/16 kills on seeds 100-102 but beam 10000 found 15/15/14. The heuristic is the limit.
- `tools/verify_combo.py` replays an engine plan with drm/plan.py and times the trigger with drm/combo.py
  under each music/player-2 mode.
- `tools/prove.py N level plan name [speed music p2]` plays a plan in Mesen (`lua/play_plan.lua`: sets
  level, speed and music on the options screen, steers with A/B and Left/Right together on even frames,
  optional player-2 fix) and checks every pill's landing, post-cascade field and score against drm/plan.py,
  and that no glitch fired (g1: $49 changed inside a clear loop; g2: the metasprite pointer changed).
- **No-player-2 cap: 13 kills.** Kill index 13 has MULT 256 (stored as 0), so its scoreIncrease takes about
  25.6k cycles; with the clear loop around it that cannot fit between two NMIs without player 2's help.
  13 kills at HI is 236 x 300 = 70,800 points from one pill.
- **Proven (no player 2):** N=31, level 10, HI, music off, 23 pills
  (`plans/n31_l10_k13.txt`); the last pill kills 13 for 70,800, final score 72,300, every pill matched,
  no glitch. Video: `out/record_nop2_k13.mp4`.
- **Proven with player 2 (pad-legal):** N=102, level 10, HI, music off, 74 pills (`plans/p2pad_k14.txt`).
  The last pill kills 14 for 147,600 (kill 14 is the first x256 one); final score 149,700. One NMI hit a
  clear loop; player 2 held $56 (B+Start+Down+Left, possible on a real pad) for that frame. Every pill
  matched, no glitch. Video: `out/record_p2pad_k14.mp4`.
- **Proven with player 2 (any value):** N=100, level 10, HI, music off, 70 pills (`plans/p2any_k15.txt`).
  The last pill kills 15 for 147,900; final score 150,300. Player 2 held $4F (Up+Down and Left+Right
  together, not possible on a real d-pad). Video: `out/record_p2any_k15.mp4`.
- Points per kill at HI: kills 15-17 add only 300/600/1,200, but kills 18-30 add about 72k-77k each,
  so after 14 the next target that matters is 18.
- Heuristic sweep (level 10, depth 80, beam 2000, seeds 100-107): no setting wins on every seed
  (best per seed ranged 12-18 across settings), so scans run several settings per seed
  (`tools/scan_big.sh`).
- **The timing model is a filter, not the judge.** `drm/glitch.py` widens each NMI's possible time to
  cover handler variation, so it rejects combos whose single real NMI time is safe. In Mesen (deterministic,
  cycle-accurate) many "unsafe" 19-22 kill combos play with no glitch, while some (N=106 19/20) really do
  glitch. So candidates are now played in Mesen from the most kills down (`tools/try_many.py`,
  `tools/batch_new.py`, results in `out/tries.jsonl`). A run with g1 = g2 = 0 and every pill matching is
  the proof; the input log replays it exactly.
- **Pad-legality is set by the board, not luck.** An NMI can land only in a match call longer than about
  24,000 cycles (it comes about 24k cycles after the call starts), and player 2 must then hold that chain's
  fieldPos_last = index just past the chain (row*8+col). Illegal ends: column 3 or 7 (Left+Right), or
  columns 4-7 on an odd row (Up+Down). In a long call with one chain, the value is fixed by the plan.
  Most 20+ kill combos needed $4F first, the end of the chain cleared in the long x256 call.
- Call cycles fit `5854 + 93.8*sum(MULT of the call's kills) + 154*kills + 542*chains` (308 calls timed by
  drm/glitch.py, residual sd 582, max 1359). `tools/pad_analyze.py` lists a combo's calls and chain ends.
- **Pad mode (`dm search ... pad=1`):** records only combos where every chain in a call predicted over
  20,000 cycles ends at a pad-legal value (`pad_ok` in engine/dm.cpp; `tools/pad_rule.py` is the Python
  version and agrees on 67/67). This is stricter than needed (it rejects the proven pad 19, where only
  the legal chain of a multi-chain call was hit), but its first batch gave pad-legal 20-kill passes on
  N=152 and N=154 in Mesen. Pad-mode scans: seeds 181-259 found no pad-safe 20+, seeds 1-99 found
  N=48 (pad-legal 20 in 22 pills, $50 $56 $59, `plans/p2pad_k20_n48.txt`).
- Scan yield (level 10, "shape=0.25 look=2", depth 80, beam 2000): of seeds 117-259, 11 had a combo of 18+,
  5 reached 21+, and 2 reached 22 (N=154, N=198). A focused re-search of N=198 (beam 4000, or shape 0.35) reached 23.
- Exact pad screening (`tools/pad_exact.py`) of the older scans predicted pad-legal 21 and 22 kill combos on N=154
  ($75 $44 $5A $51 and $75 $44 $5A $58). In Mesen every pill matched and g1 = 0 (player 2 fixed glitch 1 with pad
  values), but g2 = 60: the metasprite glitch fires, with music off and on. Glitch 2 cannot be fixed by player 2,
  so the pad check must also require the glitch 2 timing to be clear (which the record pad 20 has).

## Glitch 2 timing and glitch 3 (verified 2026-11-16)
- **Glitch 2 windows.** `DRM_TRACE=1` in `lua/play_plan.lua` logs CPU cycles of match routine entry/exit, NMIs
  and metaspriteUpdate ($88F6-$893A). Over 134 match calls (out/trace_k20, trace_k22) the game runs four
  metasprite updates after each match routine exits, at +1069..+1930, +1839..+2779, +2626..+3615 and
  +4173..+5744 cycles (earliest start .. latest end; the lengths move with the sprite animation frame). An NMI
  inside one fires glitch 2. `tools/sprite_check.py` classes each trigger pill clear / maybe / hit; on all 154
  earlier Mesen tries no "clear" fired glitch 2 and every "hit" did. All 36 pad-legal 21/22s from the old scans
  are "hit". The engine's `pad=2` adds a rough version (cycle model, predicted NMI well inside a window).
- **pad=2 search.** Seeds 117-259 (shape 0.25 look 2, beam 2000) gave no pad=2 combo of 20+. A deep re-search of
  the 19+ seeds (beam 4000, shape 0.15/0.25/0.35/0.5, look 2/3) gave 20 pad-legal 21s on N=154, all "clear";
  four played in Mesen, all passed. The same runs (unfiltered best) reached 26 on N=154, shape 0.25 look 3.
- **Glitch 3: virus counter drawn wrong.** The NMI draws the counter (VRAM $233B) when `vu_virusLeft` is set, the
  tens digit from p1_virusLeft ($0324) and the ones digit from currentP_virusLeft ($A4)
  (`drmario_prg_visual_nametable.asm` @renderVirusLeft). Every virus kill decrements $A4 and sets the flag; $0324
  is copied back once a frame (write at $90B6). If the cascade's last draw lands after a kill that crossed a
  tens boundary but before that frame's copy-back, the screen mixes old tens with new ones (19 left shows as
  29) and stays wrong until the next kill. RAM and the level-end check are fine; the screen is not. Seen on
  two any-value 24s (N=154) with g1 = g2 = 0. `play_plan.lua` now reports g3 (counter tiles differ from $0324
  after the cascade) and `prove.py` counts it as a glitch. All earlier records re-proved with g3 = 0.
- The N=154 26-kill combo fires glitches (g = 61) in Mesen; three of four 24-kill variants pass g1/g2 and one
  of them also passes g3 (the record).
- **Any 25.** Re-searching N=154 (beam 4000/6000/8000, shape 0.2/0.25/0.3, look 3/4; 10-25 s each) gave three 26s
  and two 25s. `tools/pad_exact.py ... any=1` (one chain per NMI, plus the sprite check) called both 26s sure
  glitch 2 hits and both 25s clear; on the five earlier any tries it agreed with Mesen's g2 every time. Both 25s
  passed in Mesen (g1 = g2 = g3 = 0): 25 kills, 738,900 (beam 8000, shape 0.3, look 3).
- **Pad 23.** A plain (no `pad=`) sweep of the eight 19+ seeds at beam 8000/12000, shape 0.15-0.35, look 3/4
  (160 searches, 10-40 s each) gave 2,800 combos of 22+ kills; `pad_exact.py` passed 14 (all N=154, 23 kills,
  sprite check clear, plus 132 pad 22s on N=152 that were not needed). All four tried passed in Mesen with
  g1 = g2 = g3 = 0: pad 23, 594,600. The `pad=2` engine filter is stricter than the exact check and missed it,
  so a wide plain search plus the exact screen is the better route. The any screen of the same sweep found no
  new 25+: the 26s (N=154) and 25s (N=151) are all sure glitch 2 hits.
- **Nudging does not work, speed does.** `tools/nudge.py` tries every one-pill change of a plan (later pills
  fixed, same earlier clears): on the five N=154 26s none of the 572 variants per plan kept 26 kills; the boards
  are packed too tightly. All five 26s share one cascade whose last checkVerMatch (18,780 cycles at HI) is a
  sure glitch 2 hit in both music profiles. The score routine runs inside the match routines and its cost
  grows with the points per kill, so the same call is 18,611 cycles at MED (still a hit) and 18,455 at LOW
  ("maybe"). In Mesen at LOW, four of the five plans fired glitch 2 (g2 = 58) and one (`low26_4`) passed,
  twice: 26 kills, 270,500, g1 = g2 = g3 = 0. The plans differ only in earlier pills, and the passing one
  reaches the trigger 26 frames later, so the sprite animation phase (which sets the window lengths) decides
  the "maybe" cases. Levers to try next: speed LOW/MED for every "maybe" or near-hit combo, and waiting a few
  frames before dropping the trigger pill to choose the animation phase.
- **Waiting before the trigger** (`DRM_WAIT=k` in `lua/play_plan.lua`: hold Down on the last pill only k frames
  after it spawns). N=218 gave pad 24 (666,600, values pad-legal, sprite check "maybe" at HI, sure hit at LOW
  and MED). In Mesen every wait from 0 to 50 frames fired glitch 2: g2 = 59-60 for most, 8 for waits 8, 9, 12,
  22, 26. So the phase changes how badly the sprite update is hit but did not clear it here.
- **Pad-value filter on N=154** (`pad=1`, beam 8000/16000, shape 0.15-0.35, look 3/4): no 22+ combo passes.
  The seed 1-260 sweep at beam 8000 found 22+ only on N=3, 28, 53, 127, 154, 217 and 218 (24).

### Records so far (level 10, HI, music off; each proven in Mesen, every pill matched, g1 = g2 = g3 = 0)
| Category | N | Pills | Kills | Points (last pill) | Player 2 held | Files |
|---|---|---|---|---|---|---|
| No controller 2 | 31 | 23 | 13 (cap) | 70,800 | - | best/nop2_13.plan, videos/nop2_13.mp4 |
| Player 2, pad-legal | 154 | 49 | 23 | 594,600 | $75 $44 $85 $76 | best/pad_23.plan, videos/pad_23.mp4 |
| Player 2, any value | 154 | 48 | 25 | 738,900 | $5D $44 $5E $5E $5A $85 $85 $76 $76 | best/any_25.plan, videos/any_25.mp4 |
| Player 2, any value, speed LOW | 154 | 33 | 26 | 270,500 | $46 $76 $76 $3E $5D $5A $75 $75 | best/any_26_low.plan, videos/any_26_low.mp4 |

Earlier records, kept in `best/` and `videos/`: pad 20 (N=154, 23 pills, 376,500, `pad_20`), pad 21 (N=154, 59 pills, 449,700, `pad_21`), any 23
(N=198, 63 pills, 594,600, `any_23`), any 24 (N=154, 33 pills, 666,600, `any_24`).
