"""Replay each probed checkHorMatch/checkVerMatch call (RAM dumped at entry by lua/timing_probe.lua) in
drm/cpu6502.py and compare the cycle offset of every logged event with Mesen's, up to the first NMI."""
import json
import sys

sys.path.insert(0, ".")
from drm.cpu6502 import CPU, load_prg

ENTRY = {"H": 0x91FB, "V": 0x9469}
WATCH = {0x925F: "A", 0x94C5: "A", 0x92A0: "D", 0x9503: "D", 0x8FF4: "S", 0x901B: "s", 0x92DA: "h", 0x952F: "v"}

prg = load_prg()
ok = bad = 0
for line in open(sys.argv[1] if len(sys.argv) > 1 else "out/timing2.jsonl"):
    d = json.loads(line)
    ev = d["ev"].split()
    calls = [i for i, e in enumerate(ev) if e[0] in "HV"]
    for ci, i in enumerate(calls):
        t0 = int(ev[i][1:])
        want = []
        for e in ev[i + 1:]:
            if e[0] in "HVN":
                break
            want.append((e[0], int(e[1:].split(":")[0]) - t0))
            if e[0] in "hv":
                break
        cpu = CPU(prg)
        cpu.ram[:] = bytes.fromhex(d["dumps"][ci])
        hits, total = cpu.call(ENTRY[ev[i][0]], WATCH)
        got = sorted((WATCH[a], c) for a, cs in hits.items() for c in cs)
        got = sorted(got, key=lambda x: x[1])[:len(want)]
        if got == want:
            ok += 1
        else:
            bad += 1
            if bad <= 5:
                print("trial", d["trial"], ev[i][0], "\n want", want[:12], "\n got ", got[:12])
print("match", ok, "mismatch", bad)
