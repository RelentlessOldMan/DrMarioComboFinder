"""Cross-check engine/dm.exe against drm/: level generation and random play (landings, cascades, kills).
Usage: check_engine.py [trials] [pills]"""
import os, random, subprocess, sys
sys.path.insert(0, ".")
from drm import board, plan
from drm.gen import SEED, advance, generate

trials = int(sys.argv[1]) if len(sys.argv) > 1 else 200
pills = int(sys.argv[2]) if len(sys.argv) > 2 else 40
rnd = random.Random(1)
hx = lambda m: "".join("%02X" % v for v in m)
bad = cascades = kills = 0
for t in range(trials):
    n, level = rnd.randrange(1, 32767), rnd.randrange(0, 21)
    g = generate(advance(SEED, n), level)
    mem = board.new_mem(g["field"])
    steps, want = [], []
    for i in range(pills):
        pid = g["reserve"][1 + i]
        opts = []
        for rot, x, m in plan.moves(mem, pid):
            m2, k, st = plan.play(mem, rot, x, pid)
            if not board.lost(m2):
                opts.append((k, rot, x, m2, st))
        if not opts:
            break
        hits = [o for o in opts if len(o[4]) > 1]
        k, rot, x, mem, st = rnd.choice(hits) if hits and rnd.random() < 0.6 else rnd.choice(opts)
        cascades += len(st) > 2
        kills += k
        steps.append("%d,%d" % (rot, x))
        want.append((k, hx(mem[:128])))
    out = subprocess.run([os.path.join("engine", "dm.exe"), "play", "n=%d" % n, "level=%d" % level, "plan=" + " ".join(steps)],
                         capture_output=True, text=True).stdout.split("\n")
    ok = out[0] == "field " + hx(g["field"]) and out[1] == "reserve " + hx(g["reserve"])
    for i, (k, after) in enumerate(want):
        f = out[2 + i].split()
        ok &= int(f[3]) == k and f[5] == after
    if not ok:
        bad += 1
        print("MISMATCH n=%d level=%d plan=%s" % (n, level, " ".join(steps)))
print("%d/%d games match (%d multi-step cascades, %d kills)" % (trials - bad, trials, cascades, kills))
