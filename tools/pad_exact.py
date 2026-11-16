"""Exact pad check: time every match call of the trigger pill with drm/glitch.py (silent profile) and
require that every chain an NMI can land in ends at a pad-legal fieldPos_last (safe_call p2="pad", sprite
margin ignored). Usage: pad_exact.py min_kills out.jsonl scan.jsonl...  (prints n kills verdict)"""
import json, sys
sys.path.insert(0, ".")
from drm import glitch
from tools.pad_analyze import trigger


def pad_hits(e, profile="silent"):
    """Values player 2 may have to hold, and whether all are pad-legal and each NMI touches one chain."""
    vals, ok = [], True
    for c in e["calls"]:
        ranges = glitch.nmi_ranges(c["cycles"], profile)
        for lo, hi in ranges:
            hit = [i for i, (a, d) in enumerate(c["wins"]) if a <= hi and d >= lo]
            vals += [c["ends"][i] for i in hit]
            if len(hit) > 1 or any(not glitch.pad_legal(c["ends"][i]) for i in hit):
                ok = False
    return ok, vals


if __name__ == "__main__":
    lo, out = int(sys.argv[1]), open(sys.argv[2], "w")
    seen = set()
    for f in sys.argv[3:]:
        for line in open(f):
            if not line.startswith('{"n"'):
                continue
            r = json.loads(line)
            if r.get("kills", 0) < lo or (r["n"], r["plan"]) in seen:
                continue
            seen.add((r["n"], r["plan"]))
            e = trigger(r["n"], r["level"], [tuple(map(int, s.split(","))) for s in r["plan"].split()])
            ok, vals = pad_hits(e)
            if ok:
                out.write(json.dumps(r) + "\n")
                out.flush()
            print(r["n"], r["kills"], "PADOK" if ok else "no", " ".join("%02X" % v for v in vals), flush=True)
