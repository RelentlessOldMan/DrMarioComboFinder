"""Glitch check for the big-combo bug: if the frame's NMI lands while a match routine is clearing a
colour chain (between `sta fieldPos_last` and the loop's last `cpy fieldPos_last`), getInputs overwrites
$49 and the clear runs on through RAM (horizontal) or never ends (vertical).

Each match routine (checkHorMatch, checkVerMatch) is run in drm/cpu6502.py on a game RAM image with the
current field, kill count, speed and score, which gives the exact cycle offsets of every clear loop
(cycle-exact against Mesen, tools/check_timing.py). NMIs are then placed on that timeline with the
measured ranges below, and a call is safe only if no possible NMI falls inside a clear loop.
"""
import os

from drm.cpu6502 import CPU, load_prg

FRAME = 29780.67            # CPU cycles per NTSC frame
# Timing ranges by music setting (tools/timing_stats.py on out/timing2, timing_m1, timing_m2), with margin:
#   start   = routine entry, cycles after the NMI
#   handler = NMI cost when it interrupts the routine
#   stretch = DMC sample DMA steals cycles (music only)
#   sprites = cycles after routine exit spanned by the metasprite updates (measured +1069..+5750 in
#             every setting). metaspriteUpdate keeps its data pointer in tmp47/48: an NMI there makes
#             getInputs overwrite tmp48 and the loop can spin forever (seen in Mesen). An NMI elsewhere in
#             the tail (exit to the $B662 wait loop, 6529..9880) only costs a lag frame.
PROFILES = {
    # Fever + Chill measured: start 5762..5945, handler 1925..2354, DMA up to ~1%, tail 6529..9880
    "music": {"start": (5740, 5980), "handler": (1900, 2420), "stretch": (1.0, 1.015), "sprites": (1000, 5850)},
    # music off measured: start 5762..5909, handler 1936..2050, no DMA, tail 6772..7305
    "silent": {"start": (5740, 5940), "handler": (1920, 2080), "stretch": (1.0, 1.0), "sprites": (1000, 5850)},
}

HOR, VER = 0x91FB, 0x9469
_ARM = (0x925F, 0x94C5)     # sta fieldPos_last
_DONE = (0x92A4, 0x9507)    # after the `lda fieldPos_last` that follows the clear loop (its last read of $49)

_prg = load_prg()
_template = bytes.fromhex(open(os.path.join(os.path.dirname(__file__), "ram_template.hex")).read().strip())


def ram_image(mem, kills, speed, score):
    """Game RAM for a P1 1-player level: field/beyond from mem, kill counter, speed, score (points)."""
    r = bytearray(_template)
    r[0x400:0x500] = bytes(mem[:256])
    r[0xAD] = kills & 0xFF
    r[0x8B] = speed
    digits = score // 10
    for i in range(6):
        r[0x729 + i] = digits % 10
        digits //= 10
    return r


def windows(ram, entry, ends=None):
    """Run one match routine. Returns ([(arm, done) cycle offsets], total cycles, ram after).
    ends (optional list) gets each clear loop's fieldPos_last, in window order."""
    cpu = CPU(_prg)
    cpu.ram[:] = ram
    hits, total = cpu.call(entry, _ARM + _DONE)
    arms = sorted((c, v) for a in _ARM for c, v in zip(hits[a], cpu.hit_a[a]))
    dones = sorted(c for a in _DONE for c in hits[a])
    if ends is not None:
        ends.extend(v for _, v in arms)
    return list(zip((c for c, _ in arms), dones)), total, cpu.ram


def pad_legal(v):
    """Can a standard NES pad hold buttons equal to v? Not with Left+Right (bits 0-1) or Up+Down (2-3)."""
    return v & 3 != 3 and v & 0x0C != 0x0C


def nmi_ranges(total, profile="music"):
    """Earliest/latest routine-cycle offset of each NMI that can happen before the routine ends."""
    pr = PROFILES[profile]
    start, handler, stretch = pr["start"], pr["handler"], pr["stretch"]
    out, j = [], 1
    while True:
        lo = (j * FRAME - start[1] - (j - 1) * handler[1]) / stretch[1]
        hi = (j * FRAME - start[0] - (j - 1) * handler[0]) / stretch[0]
        if lo > total:
            return out
        out.append((lo, hi))
        j += 1


def safe_call(wins, total, profile="music", p2=False, ends=None):
    """True if no possible NMI time falls inside any clear loop or the sprite update after the routine.
    Also returns the tightest margin (cycles to the nearest possible NMI; negative = can glitch).

    p2=True: player 2 holds the buttons whose bits equal the chain's fieldPos_last on that frame, so the
    NMI's getInputs writes $49 back unchanged (verified in Mesen, out/timing_p2fix.jsonl). Then an NMI may
    land in a clear loop, as long as its whole possible range touches only one chain (so the right
    buttons are known); the margin is then measured from the sprite update only.
    p2="pad": the same, and every chain an NMI can land in must end at a pad_legal fieldPos_last (ends)."""
    margin = float("inf")
    s0, s1 = PROFILES[profile]["sprites"]
    ranges = nmi_ranges(total + s1, profile)
    spans = [(total + s0, total + s1)] + ([] if p2 else list(wins))
    for a, d in spans:
        for lo, hi in ranges:
            if d < lo:
                margin = min(margin, lo - d)
            elif a > hi:
                margin = min(margin, a - hi)
            else:
                margin = min(margin, -1)
    if p2:
        for lo, hi in ranges:
            hit = [i for i, (a, d) in enumerate(wins) if a <= hi and d >= lo]
            if len(hit) > 1 or (p2 == "pad" and any(not pad_legal(ends[i]) for i in hit)):
                margin = min(margin, -1)
    return margin > 0, margin

