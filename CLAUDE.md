# DrMarioComboFinder: notes for every session

Finds the biggest single-pill combos in NES Dr. Mario that do not break the game, by searching pill
placements outside the game and proving the winners in the Mesen 2 emulator. This file is the project's
shared brain: the standing rules, how to work, and where things are. Where the project stands and what
comes next is in [docs/status.md](docs/status.md). Both are in git, so every session on every machine gets
the same picture.

## The brain: what goes in it and what stays private

Claude Code loads this file at the start of every session, on every machine with a clone. Together with
`docs/status.md` it replaces any one session's memory: a session that knows only what is in git should be
able to carry on the work. So:

- **In the brain (this file, `docs/status.md`):** the project's standing rules and preferences, how to
  build and test, where things are, what is built, what is next, what was learned, what is unverified.
- **Never in the repo (brain, code, docs, commit messages):** anything about a particular machine or
  person (host names, IPs, user names, local paths, serial numbers, ports); credentials; rules about how
  one machine schedules jobs (facts about a job's own needs are fine).
- **Where private things live:** in each machine's own Claude memory or user settings. When another
  machine needs one, the user passes it over directly; it is never committed.
- **Keeping it current:** update `docs/status.md` with every chunk of work, and this file when a rule
  changes. If a session's private memory holds a project rule every session should know, move it here
  (without the private parts).

## What the project is for

- Find the **highest-scoring** and **highest virus-count** single-pill combos (one pill sets off the whole
  cascade) that "do not fuck up the game": no corrupted board, no freeze, no glitch firing.
- Big combos are dangerous because of two bugs (details in `RESEARCH.md`): **glitch 1**, an NMI during a
  clear loop writes player 2's buttons into `$49` (fieldPos_last); **glitch 2**, the metasprite pointer
  `tmp48` changes. Glitch 1 can be fixed by player 2 holding the right value; glitch 2 cannot and must be
  avoided by timing. **Glitch 3**: the virus counter is drawn wrong (old tens digit, new ones digit) after the
  cascade; it is a visible fault, so it also disqualifies a combo.
- The user never chose a player-2 rule, so there are **three leaderboards**: no controller 2 (hard cap
  13 kills), player 2 holding standard-pad values only, player 2 holding any value.
- **Search by placement, not by playing.** The search picks each pill's final spot and orientation, drops
  it, resolves clears and cascades, and scores. It never simulates frames, gravity or button presses;
  inputs are made only when a winner is played in Mesen.
- **Mesen is the judge.** A combo counts only when `tools/prove.py` plays it in Mesen with every pill
  matching the simulator and g1 = g2 = g3 = 0. Then record a video and check its final frame.
- **No ROMs or emulator in the repo, ever.** Never download a ROM. `*.nes`, `ref/` (disassemblies) and
  `mesen/` are gitignored; users bring their own.

## Working through a plan

When the user says "keep rolling", keep searching and proving (scan seeds, re-search the best seeds with
other settings, screen, prove in Mesen), recording each new record and updating `RESEARCH.md` and
`docs/status.md`, until the plan is done or truly blocked.

## Code rules

- Python 3.12, standard library only. C++17 for the engine (MSVC, OpenMP). Lua 5.4 for Mesen scripts.
- Match the surrounding code: short docstrings or header comments saying what a file does and its usage
  line, no type hints, compact style.
- `drm/` is the reference model (rebuilt from the disassembly); `engine/dm.cpp` is the fast copy and must
  agree with it (`tools/check_engine.py`).
- Repo files are UTF-8 with LF line endings (`.bat` keeps CRLF).

## Git

- Commit and push straight to `main`. Before committing: build the engine if `dm.cpp` changed, run
  `tools/check_engine.py`, and check no machine paths or names crept in.
- Records go in `best/` (plan + input log), `docs/img/` (stills, GIF) and `videos/` (MP4). Working output
  stays in `out/` and `plans/`, which are gitignored.

## Commands

    engine\build.bat                                     # bump VERSION, build engine/dm.exe (needs VS 2022)
    engine\dm.exe version
    python tools/check_engine.py                         # engine vs drm/, 200 random games
    engine\dm.exe search level=10 n0=150 n1=160 depth=80 beam=2000 shape=0.25 look=2 min=16 per=20 > scan.jsonl
    python tools/batch_new.py 19 4 out/batch.jsonl scan.jsonl   # pick untried candidates
    python tools/try_many.py out/batch.jsonl tag 8      # prove in Mesen, most kills first
    python tools/prove.py N level "r,x r,x ..." name p2=1
    powershell tools\make_video.ps1 out\name.inputs out\name.mp4

Job sizes: `check_engine.py` about 20 s. A `dm.exe search` at depth 80, beam 2000 takes minutes per seed
and uses all cores; beam 4000 roughly doubles that. One Mesen proof (`prove.py`) takes about a
minute on one core; a video about two minutes plus a large temporary raw-frame file (deleted after).

## Where things are

- `README.md`: what it does, the records, how it works.
- `RESEARCH.md`: everything learned about the game (RNG, generation, scoring, RAM, glitches, timing
  model), with the records table.
- `docs/status.md`: built, next, lessons.
- `drm/`: Python model (generation, board, placement search, 6502 core for glitch timing).
- `engine/`: C++ search engine. `lua/`: Mesen scripts (play a plan, replay, probes). `tools/`: pipeline
  and check scripts.
- `best/`: the record plans (one `rot x` per pill) and their input logs. `docs/img/`, `videos/`: media.
