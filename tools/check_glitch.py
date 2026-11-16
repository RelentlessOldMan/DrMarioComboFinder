"""Check drm/glitch.py against the probe: rebuild each match call's RAM from only field, kill counter,
speed and score, predict whether an NMI can land in a clear loop, and compare with what Mesen did."""
import json
import sys

sys.path.insert(0, ".")
from drm import glitch

calls = same = 0
table = {}  # (predicted safe, observed glitch) -> count
profile = sys.argv[2] if len(sys.argv) > 2 else "music"
for line in open(sys.argv[1] if len(sys.argv) > 1 else "out/timing2.jsonl"):
    d = json.loads(line)
    ev = d["ev"].split()
    idx = [i for i, e in enumerate(ev) if e[0] in "HV"]
    for ci, i in enumerate(idx):
        full = bytes.fromhex(d["dumps"][ci])
        score = sum(full[0x729 + k] * 10 ** k for k in range(6)) * 10
        r = glitch.ram_image(full[0x400:0x500], full[0xAD], full[0x8B], score)
        entry = glitch.HOR if ev[i][0] == "H" else glitch.VER
        w1, t1, _ = glitch.windows(r, entry)
        w2, t2, _ = glitch.windows(full, entry)
        calls += 1
        same += (w1, t1) == (w2, t2)
        end = next(j for j in range(i + 1, len(ev)) if ev[j][0] in "hv")
        observed = any(e.startswith("N") and e.endswith(":armed") for e in ev[i:end])
        w = next((j for j in range(end, len(ev)) if ev[j][0] == "W"), None)  # tail logged in newer runs
        if w is not None:  # an NMI between a metasprite call's M and m, or a repaired tmp48 (X)
            inside = False
            for e in ev[end:w]:
                inside = {"M": True, "m": False}.get(e[0], inside)
                observed |= (e[0] == "N" and inside) or e[0] == "X"
        ok, margin = glitch.safe_call(w1, t1, profile)
        table[(ok, observed)] = table.get((ok, observed), 0) + 1
        if ok and observed:
            print("MISSED glitch: trial", d["trial"], ev[i][0], "margin", margin)
print("calls", calls, "template gives identical timing", same)
for k in sorted(table):
    print("predicted safe=%s observed glitch=%s: %d" % (k[0], k[1], table[k]))
