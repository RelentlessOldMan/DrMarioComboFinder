"""Replay the locks recorded by lua/rules_check.lua through drm/board.py. Usage: check_rules.py <dump.jsonl>"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from drm.board import resolve, combo_score, show

def hx(s):
    return [int(s[i:i + 2], 16) for i in range(0, len(s), 2)]

good = bad = 0
for line in open(sys.argv[1]):
    d = json.loads(line)
    mem = hx(d["lock"]) + hx(d["beyond"])
    steps = resolve(mem)
    kills = sum(len(s["hor"]) + len(s["ver"]) for s in steps)
    ok_field = mem[:128] == hx(d["final"])
    ok_kills = kills == d["mult"]
    ok_score = combo_score(kills, d["speed"]) == d["dscore"]
    if ok_field and ok_kills and ok_score:
        good += 1
    else:
        bad += 1
        if bad <= 3:
            print("trial", d["trial"], "field", ok_field, "kills", kills, d["mult"], "score", combo_score(kills, d["speed"]), d["dscore"])
            a, b = show(hx(d["lock"])).split("\n"), show(mem).split("\n")
            c = show(hx(d["final"])).split("\n")
            for x, y, z in zip(a, b, c):
                print("  %s   %s   %s" % (x, y, z))
print("%d match, %d differ; cascade steps seen: %s" % (good, bad, "n/a"))
