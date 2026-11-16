"""Pick untried candidates from scan files for tools/try_many.py: per (seed, kills) up to `each` plans
spread across the list, kills >= lo, skipping plans already in out/tries.jsonl.
Usage: batch_new.py lo each out.jsonl scan.jsonl..."""
import json, os, sys
lo, each, dst = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
tried = set()
if os.path.exists("out/tries.jsonl"):
    tried = {(r["n"], r["plan"]) for r in map(json.loads, open("out/tries.jsonl"))}
groups = {}
for f in sys.argv[4:]:
    for x in map(json.loads, open(f)):
        if x.get("kills", 0) >= lo and (x["n"], x["plan"]) not in tried:
            groups.setdefault((x["n"], x["kills"]), []).append(x)
out = []
for v in groups.values():
    step = max(1, len(v) // each)
    out += v[::step][:each]
out.sort(key=lambda x: -x["kills"])
open(dst, "w").writelines(json.dumps(x) + "\n" for x in out)
print(len(out), sorted({(x["n"], x["kills"]) for x in out}, key=lambda t: -t[1]))
