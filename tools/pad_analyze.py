"""For Mesen-proven combos (out/tries.jsonl), list the trigger pill's match calls: routine, cycles, and the
fieldPos_last of every clear loop, next to the values player 2 actually had to hold in Mesen.
Usage: pad_analyze.py [min_kills] [max_rows]"""
import json, sys
sys.path.insert(0, ".")
from drm import board, combo, glitch, plan
from drm.gen import SEED, advance, generate


def trigger(n, level, steps, speed=2):
    g = generate(advance(SEED, n), level)
    mem, score = board.new_mem(g["field"]), 0
    for i, (rot, x) in enumerate(steps[:-1]):
        mem, k, _ = plan.play(mem, rot, x, g["reserve"][1 + i])
        score += board.combo_score(k, speed)
    rot, x = steps[-1]
    lock = [m for r, xx, m in plan.moves(mem, g["reserve"][len(steps)]) if (r, xx) == (rot, x)][0]
    return combo.evaluate(list(lock), speed, score, True, "silent", True)


if __name__ == "__main__":
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    seen = set()
    for line in open("out/tries.jsonl"):
        r = json.loads(line)
        key = (r["n"], r["plan"])
        if not r.get("ok") or r.get("last_kills", 0) < lo or key in seen:
            continue
        seen.add(key)
        if len(seen) > rows:
            break
        e = trigger(r["n"], r["level"], [tuple(map(int, s.split(","))) for s in r["plan"].split()])
        print("n=%d kills=%d mesen=%s" % (r["n"], e["kills"], r["p2vals"]))
        k = 0
        for c in e["calls"]:
            k += c["kills"]
            print("  %s cyc=%6d kills->%2d ends=%s" % (c["routine"], c["cycles"], k, " ".join(
                "%02X%s" % (v, "" if glitch.pad_legal(v) else "!") for v in c["ends"])))
