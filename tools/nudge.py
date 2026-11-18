"""Nudge a combo out of a glitch: the trigger pill's match-call timing depends on the board and score, so
moving one earlier pill can shift a glitching cascade into the clear. For every non-trigger pill and every
other placement of it, replay the plan (later pills keep their spots, every earlier pill must clear the same
number of viruses as before) and keep variants whose trigger still kills >= min_kills and passes the exact
screen (tools/pad_exact.py: pad values, or any=1, plus the sprite check).
Usage: nudge.py min_kills out.jsonl scan.jsonl... [any=1] [jobs=8]  (writes scan-style lines with "nudge")"""
import json, sys
from multiprocessing import Pool
sys.path.insert(0, ".")
from drm import board, plan
from drm.gen import SEED, advance, generate
from tools.pad_analyze import trigger
from tools.pad_exact import pad_hits
from tools.sprite_check import sprite_class


def replay(g, steps):
    """Per-pill kills of a plan, or None if a placement is not available."""
    mem, ks = board.new_mem(g["field"]), []
    for i, (rot, x) in enumerate(steps):
        try:
            mem, k, _ = plan.play(mem, rot, x, g["reserve"][1 + i])
        except ValueError:
            return None
        ks.append(k)
    return ks


def variants(r):
    """Every one-pill change of the plan, as (pill index, steps)."""
    g = generate(advance(SEED, r["n"]), r["level"])
    steps = [tuple(map(int, s.split(","))) for s in r["plan"].split()]
    mem, out = board.new_mem(g["field"]), []
    for i, (rot, x) in enumerate(steps[:-1]):
        for rr, xx, _ in plan.moves(mem, g["reserve"][1 + i]):
            if (rr, xx) != (rot, x):
                out.append((i, steps[:i] + [(rr, xx)] + steps[i + 1:]))
        mem, _, _ = plan.play(mem, rot, x, g["reserve"][1 + i])
    return out


def check(job):
    r, i, steps, lo, anyval, base = job
    g = generate(advance(SEED, r["n"]), r["level"])
    ks = replay(g, steps)
    if ks is None or ks[:-1] != base[:-1] or ks[-1] < lo:
        return None
    e = trigger(r["n"], r["level"], steps)
    ok, vals = pad_hits(e, anyval=anyval)
    spr = sprite_class(e)[0]
    return (ok and spr != "hit", ks[-1], i, spr, steps, vals)


if __name__ == "__main__":
    anyval = "any=1" in sys.argv
    jobs = int(next((a[5:] for a in sys.argv if a.startswith("jobs=")), 8))
    args = [a for a in sys.argv[1:] if a != "any=1" and not a.startswith("jobs=")]
    lo, out = int(args[0]), open(args[1], "w")
    seen, cands = set(), []
    for f in args[2:]:
        for line in open(f):
            if line.startswith('{"n"'):
                r = json.loads(line)
                if r.get("kills", 0) >= lo and (r["n"], r["plan"]) not in seen:
                    seen.add((r["n"], r["plan"])); cands.append(r)
    with Pool(jobs) as pool:
        for r in cands:
            g = generate(advance(SEED, r["n"]), r["level"])
            base = replay(g, [tuple(map(int, s.split(","))) for s in r["plan"].split()])
            work = [(r, i, s, lo, anyval, base) for i, s in variants(r)]
            n = 0
            for res in pool.imap_unordered(check, work, chunksize=4):
                if res is None:
                    continue
                n += 1
                ok, k, i, spr, steps, vals = res
                if ok:
                    out.write(json.dumps(dict(r, kills=k, plan=" ".join("%d,%d" % s for s in steps),
                                              nudge=i)) + "\n")
                    out.flush()
                print(r["n"], k, "pill", i, "PADOK" if ok else "no", spr,
                      " ".join("%02X" % v for v in vals), flush=True)
            print("# n=%d kills=%d: %d variants, %d keep the kills" % (r["n"], r["kills"], len(work), n), flush=True)
