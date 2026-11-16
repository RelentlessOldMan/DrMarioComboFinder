"""Play candidate combos in Mesen (tools/prove.py) from the most kills down; Mesen is the final judge
(drm/glitch.py's NMI ranges are deliberately wide). Usage: try_many.py cands.jsonl tag [max] [p2=1]
Appends one JSON line per try to out/tries.jsonl."""
import json, sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
from prove import prove

cands = [json.loads(l) for l in open(sys.argv[1]) if '"kills"' in l]
tag, most = sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10
p2 = int(sys.argv[4]) if len(sys.argv) > 4 else 1
seen, done = set(), 0
for c in sorted(cands, key=lambda c: -c["kills"]):
    key = (c["n"], c["level"], c["plan"])
    if key in seen:
        continue
    seen.add(key)
    steps = [tuple(map(int, s.split(","))) for s in c["plan"].split()]
    r = prove(c["n"], c["level"], steps, "%s_%d" % (tag, done), p2=p2)
    r["plan"] = c["plan"]
    vals = [int(v, 16) for v in r.get("p2vals", "").split()]
    r["pad"] = all(v & 3 != 3 and v & 12 != 12 for v in vals)
    print(json.dumps(r), flush=True)
    open("out/tries.jsonl", "a").write(json.dumps(r) + "\n")
    done += 1
    if done >= most:
        break
