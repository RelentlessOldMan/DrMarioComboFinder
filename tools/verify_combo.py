"""Check combos found by engine/dm.exe search: replay the plan with drm/plan.py (must give the same kill
count), then time every match routine of the trigger pill with drm/combo.py for each music profile and
player-2 mode. Usage: verify_combo.py found.jsonl [speed] [min_kills] > checked.jsonl

Modes: nop2 (no controller 2), pad (P2 holds fieldPos_last, standard-pad values only), any (any value)."""
import json, sys
sys.path.insert(0, ".")
from drm import board, combo, plan
from drm.gen import SEED, advance, generate

MODES = [("silent", False), ("music", False), ("silent", "pad"), ("music", "pad"), ("silent", True), ("music", True)]
NAMES = {False: "nop2", "pad": "pad", True: "any"}


def check(rec, speed):
    g = generate(advance(SEED, rec["n"]), rec["level"])
    steps = [tuple(map(int, s.split(","))) for s in rec["plan"].split()]
    mem, score = board.new_mem(g["field"]), 0
    for i, (rot, x) in enumerate(steps[:-1]):
        mem, k, _ = plan.play(mem, rot, x, g["reserve"][1 + i])
        score += board.combo_score(k, speed)
    rot, x = steps[-1]
    pid = g["reserve"][len(steps)]
    lock = [m for r, xx, m in plan.moves(mem, pid) if (r, xx) == (rot, x)][0]
    out = {"n": rec["n"], "level": rec["level"], "plan": rec["plan"], "speed": speed, "before": score}
    for profile, p2 in MODES:
        e = combo.evaluate(list(lock), speed, score, True, profile, p2)
        out["kills"], out["points"] = e["kills"], e["points"]
        out["%s_%s" % (profile, NAMES[p2])] = e["margin"] if e["safe"] else -1
        out["calls"] = [(c["routine"], c["kills"], c["cycles"]) for c in e["calls"]]
    assert out["kills"] == rec["kills"], (out["kills"], rec)
    return out


if __name__ == "__main__":
    speed = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    for line in open(sys.argv[1]):
        rec = json.loads(line)
        if "kills" not in rec or rec["kills"] < lo:
            continue
        r = check(rec, speed)
        r = {k: (v if v != float("inf") else 1e9) for k, v in r.items()}
        print(json.dumps(r), flush=True)
        print("n %d L%d kills %d points %d | %s" % (r["n"], r["level"], r["kills"], r["points"], " ".join(
            "%s_%s=%s" % (p, NAMES[q], "OK" if r["%s_%s" % (p, NAMES[q])] > 0 else "no") for p, q in MODES)), file=sys.stderr)
