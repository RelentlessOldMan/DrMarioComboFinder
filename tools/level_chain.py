"""Endless play: past level 24 the game replays level 24, each board generated from where the
previous level's generation left the RNG. Map state -> next state and find the cycles.
Assumes $0480-$048F are still FF at each level start (verified only for the first level)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from drm.gen import SEED, build_index, generate

idx = build_index()
nxt = {r: generate(r, 24)["rng_after"] for r in idx}
seen_cycle = {}
cycles = []
for r0 in idx:
    path, r = {}, r0
    while r not in path and r not in seen_cycle:
        path[r] = len(path); r = nxt[r]
    if r in path:  # new cycle
        cyc, c = [], r
        while True:
            cyc.append(c); seen_cycle[c] = len(cycles); c = nxt[c]
            if c == r: break
        cycles.append(cyc)
print("states", len(idx), "distinct next-states", len(set(nxt.values())))
for i, c in enumerate(sorted(cycles, key=len, reverse=True)):
    print("cycle %d: length %d boards, e.g. start index %d" % (i, len(c), idx[min(c, key=lambda s: idx[s])]))
