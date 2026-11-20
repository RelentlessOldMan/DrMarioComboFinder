"""Prove a combo in Mesen: play the plan with lua/play_plan.lua, then check every pill against drm/plan.py
(landing, field after the cascade, score) and that no glitch fired (g1: $49 changed inside a clear loop,
g2: metasprite pointer changed,
g3: virus counter drawn wrong). Each run takes about a minute.
Usage: prove.py N level "r,x r,x ..." name [speed=2] [music=2] [p2=0]
Writes plans/<name>.txt, out/<name>.jsonl, out/<name>.inputs; prints a JSON summary line."""
import json, os, subprocess, sys
sys.path.insert(0, ".")
from drm import board, plan
from drm.gen import SEED, advance, generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prove(n, level, steps, name, speed=2, music=2, p2=0, timeout=900):
    pfile = os.path.join(ROOT, "plans", name + ".txt")
    with open(pfile, "w") as f:
        f.writelines("%d %d\n" % s for s in steps)
    jfile, ifile = (os.path.join(ROOT, "out", name + e) for e in (".jsonl", ".inputs"))
    env = dict(os.environ, DRM_N=str(n), DRM_LEVEL=str(level), DRM_SPEED=str(speed), DRM_MUSIC=str(music),
               DRM_P2=str(p2), DRM_PLAN=pfile, DRM_OUT=jfile, DRM_INPUTS=ifile)
    r = subprocess.run([os.path.join(ROOT, "mesen", "Mesen.exe"), "--testRunner", "--enableStdout",
                        "--timeout=%d" % timeout, os.path.join(ROOT, "lua", "play_plan.lua"),
                        os.path.join(ROOT, "drmario.nes")], env=env, capture_output=True, text=True)
    msg = [l for l in r.stdout.splitlines() if l and not l.startswith(("[", "---", "Loading", "File CRC", "PRG"))]
    rows = [json.loads(l) for l in open(jfile)] if os.path.exists(jfile) else []
    hx = lambda s: [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]
    g = generate(advance(SEED, n), level)
    mem = board.new_mem(g["field"])
    res = {"name": name, "n": n, "level": level, "speed": speed, "music": music, "p2": p2, "pills": len(steps),
           "played": len(rows), "match": 0, "glitch": 0, "exit": r.returncode, "msg": msg[-3:]}
    for i, d in enumerate(rows):
        rot, x = steps[i]
        pid = g["reserve"][1 + i]
        lock = [m for rr, xx, m in plan.moves(mem, pid) if (rr, xx) == (rot, x)]
        if not lock:
            res["first_bad"] = i
            break
        mem, kills, _ = plan.play(mem, rot, x, pid)
        good = hx(d["lock"]) == lock[0][:128] and hx(d["after"]) == mem[:128] and d["dscore"] == board.combo_score(kills, speed)
        res["glitch"] += d["g1"] + d["g2"] + d.get("g3", 0)
        if not good:
            res["first_bad"] = i
            break
        res["match"] += 1
        res.update(last_kills=kills, last_points=d["dscore"], score=d["score"], frame=d["frame"], p2vals=d["p2vals"])
    res["ok"] = res["match"] == len(steps) and res["glitch"] == 0
    return res


if __name__ == "__main__":
    a = sys.argv
    kw = dict(s.split("=") for s in a[5:])
    steps = [tuple(map(int, s.split(","))) for s in a[3].split()]
    print(json.dumps(prove(int(a[1]), int(a[2]), steps, a[4], **{k: int(v) for k, v in kw.items()})))
