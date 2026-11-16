"""Pad rule: in every match call of the trigger pill longer than LONG cycles (one an NMI can land in), every
clear loop must end at a pad-legal fieldPos_last. Usage: pad_rule.py min_kills out.jsonl scan.jsonl..."""
import json, sys
sys.path.insert(0, ".")
from drm import glitch
from tools.pad_analyze import trigger

LONG = 22000


def bad_ends(e):
    return [v for c in e["calls"] if c["cycles"] > LONG for v in c["ends"] if not glitch.pad_legal(v)]


if __name__ == "__main__":
    lo, out = int(sys.argv[1]), open(sys.argv[2], "w")
    seen, n_ok = set(), 0
    for f in sys.argv[3:]:
        for line in open(f):
            if not line.startswith('{"n"'):
                continue
            r = json.loads(line)
            if r.get("kills", 0) < lo or (r["n"], r["plan"]) in seen:
                continue
            seen.add((r["n"], r["plan"]))
            e = trigger(r["n"], r["level"], [tuple(map(int, s.split(","))) for s in r["plan"].split()])
            bad = bad_ends(e)
            if not bad:
                n_ok += 1
                out.write(json.dumps(r) + "\n")
                out.flush()
            print(r["n"], r["kills"], "PADOK" if not bad else " ".join("%02X" % v for v in bad), flush=True)
    print("checked", len(seen), "pad-rule ok", n_ok)
