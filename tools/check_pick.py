"""Compare Mesen dumps from lua/pick_seed.lua against drm/gen.py. Usage: check_pick.py <dump.jsonl>"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from drm.gen import SEED, advance, generate, show, pill_colors

def hx(s):
    return [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]

ok = 0
rows = [json.loads(l) for l in open(sys.argv[1])]
for d in rows:
    if "error" in d:
        print(d); continue
    field, beyond, reserve = hx(d["field"]), hx(d["beyond"]), hx(d["reserve"])
    hits = []
    for off in range(-3, 4):
        g = generate(advance(SEED, d["n"] + off), d["level"], beyond)
        f_ok, r_ok = g["field"] == field, g["reserve"] == reserve
        rng_ok = "%04X" % g["rng_after"] == d["rng"]
        if f_ok or r_ok:
            hits.append((off, f_ok, r_ok, rng_ok))
    exact = any(h[0] == 0 and h[1] and h[2] for h in hits)
    ok += exact
    cur = "%02X%02X" % (d["cur"][:2] and int(d["cur"][:2], 16), int(d["cur"][2:], 16))
    print("n=%-5d %s hits=%s beyond=%s cur=%s next=%s idx=%d reserve[0..3]=%s" % (
        d["n"], "MATCH" if exact else "DIFF ", hits, d["beyond"], d["cur"], d["next"], d["reserve_idx"],
        " ".join("%d%d" % pill_colors(p) for p in reserve[:4])))
print("%d/%d exact" % (ok, len(rows)))
d = rows[0]
print(show(hx(d["field"])))
