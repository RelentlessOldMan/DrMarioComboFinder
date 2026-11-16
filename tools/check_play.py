"""Compare a lua/play_plan.lua run with drm/plan.py: each pill's landing, the field after its cascade,
and its score. Usage: check_play.py N level plan.txt play.jsonl [speed]"""
import json, sys
sys.path.insert(0, ".")
from drm import plan, board
from drm.gen import SEED, advance, generate

n, level, pfile, jfile = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
speed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
hx = lambda s: [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]
g = generate(advance(SEED, n), level)
steps = [tuple(map(int, l.split()[:2])) for l in open(pfile) if l.strip()]
mem = board.new_mem(g["field"])
ok = 0
rows = [json.loads(l) for l in open(jfile)]
for i, d in enumerate(rows):
    rot, x = steps[i]
    pid = g["reserve"][1 + i]
    c1, c2 = plan.pill_colors(pid)
    lock = list(mem)
    for p, v in plan.cells(rot, x, plan.drop(mem, rot, x), c1, c2):
        lock[p] = v
    mem, kills, _ = plan.play(mem, rot, x, pid)
    good = (hx(d["lock"]) == lock[:128], hx(d["after"]) == mem[:128], d["dscore"] == board.combo_score(kills, speed))
    ok += all(good)
    print("pill %d %s rot %d x %d -> landed %s, cascade %s, score %s (%d kills, %d points)" % (
        i, "%d%d" % (c1, c2), rot, x, *("ok" if b else "DIFF" for b in good), kills, d["dscore"]))
    if not all(good):
        a, b = board.show(lock).split("\n"), board.show(hx(d["lock"]) + [255] * 128).split("\n")
        for u, v in zip(a, b):
            print("   %s   %s" % (u, v))
        break
print("%d/%d pills match" % (ok, len(rows)))
