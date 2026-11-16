"""Glitch 2 check for a trigger pill. After each match routine exits, the game runs four metasprite updates;
an NMI inside one changes their data pointer (tmp48). Windows measured in Mesen (out/trace_k20, trace_k22:
134 calls, cycles after routine exit). Their lengths depend on the sprite animation frame, so each window has
a sure part (inside it on every frame seen) and an edge (inside it on some). Per call:
  clear = no possible NMI time touches any window, hit = every possible NMI time is inside a sure part,
  maybe = otherwise (only Mesen can tell).
Usage: sprite_check.py N level "r,x r,x ..." [profile]"""
import sys
sys.path.insert(0, ".")
from drm import glitch
from tools.pad_analyze import trigger

# (earliest start, latest start, earliest end, latest end) of each window, cycles after routine exit
WINDOWS = [(1069, 1141, 1791, 1930), (1839, 1977, 2578, 2779), (2626, 2826, 3358, 3615), (4173, 4429, 5488, 5744)]


def call_class(total, profile="silent"):
    """'clear', 'maybe' or 'hit' for one match call of `total` cycles, and the NMI offsets checked."""
    worst = "clear"
    for lo, hi in glitch.nmi_ranges(total + WINDOWS[-1][3], profile):
        a, b = lo - total, hi - total          # possible NMI times, cycles after routine exit
        if b < WINDOWS[0][0] or a > WINDOWS[-1][3]:
            continue
        for s0, s1, e0, e1 in WINDOWS:
            if a >= s1 and b <= e0:
                return "hit", (a, b)
            if b >= s0 and a <= e1:
                worst = "maybe"
    return worst, None


def sprite_class(e, profile="silent"):
    """Worst class over all match calls of the pill, and the calls that are not clear."""
    order = {"clear": 0, "maybe": 1, "hit": 2}
    worst, bad = "clear", []
    for c in e["calls"]:
        k, _ = call_class(c["cycles"], profile)
        if k != "clear":
            bad.append((c["routine"], c["cycles"], k))
        if order[k] > order[worst]:
            worst = k
    return worst, bad


if __name__ == "__main__":
    n, level = int(sys.argv[1]), int(sys.argv[2])
    steps = [tuple(map(int, s.split(","))) for s in sys.argv[3].split()]
    print(*sprite_class(trigger(n, level, steps), sys.argv[4] if len(sys.argv) > 4 else "silent"))
