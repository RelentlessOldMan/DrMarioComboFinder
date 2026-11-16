"""Run the combo search over a range of seeds. Usage: scan_seeds.py N0 N1 level [depth] [beam]"""
import sys
sys.path.insert(0, ".")
from drm import plan
from drm.gen import SEED, advance, generate

n0, n1, level = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
depth = int(sys.argv[4]) if len(sys.argv) > 4 else 10
beam = int(sys.argv[5]) if len(sys.argv) > 5 else 20
for n in range(n0, n1):
    g = generate(advance(SEED, n), level)
    kills, pl, k = plan.search(g["field"], g["reserve"], 1, depth, beam)
    print(n, kills, k, " ".join("%d,%d" % p for p in pl[:k + 1]), flush=True)
