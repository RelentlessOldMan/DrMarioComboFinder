"""Search one seed for its biggest single-pill combo. Usage: find_combo.py N level [depth] [beam]"""
import sys, time
sys.path.insert(0, ".")
from drm import plan, board, combo
from drm.gen import SEED, advance, generate, show

n, level = int(sys.argv[1]), int(sys.argv[2])
depth = int(sys.argv[3]) if len(sys.argv) > 3 else 25
beam = int(sys.argv[4]) if len(sys.argv) > 4 else 60
g = generate(advance(SEED, n), level)
t = time.time()
kills, pl, k = plan.search(g["field"], g["reserve"], 1, depth, beam)
print("N %d level %d: best pill %d kills %d (%.1fs)" % (n, level, k, kills, time.time() - t))
mem = board.new_mem(g["field"])
for i, (rot, x) in enumerate(pl[:k + 1]):
    pid = g["reserve"][1 + i]
    if i == k:
        c1, c2 = plan.pill_colors(pid)
        m = list(mem)
        for p, v in plan.cells(rot, x, plan.drop(mem, rot, x), c1, c2):
            m[p] = v
        print(board.show(m))
        r = combo.evaluate(m, speed=1)
        print("final pill:", r["kills"], "kills", r["points"], "points, glitch-safe", r["safe"], "margin", r["margin"])
    mem, kk, _ = plan.play(mem, rot, x, pid)
print("plan:", " ".join("%d,%d" % p for p in pl[:k + 1]))
