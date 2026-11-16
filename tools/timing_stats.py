"""Timing ranges from a timing_probe.lua run: NMI period, match-routine start offset after the NMI,
NMI handler cost when it interrupts a routine, and cycles Mesen adds over drm/cpu6502.py (DMA)."""
import json
import sys
from collections import Counter

sys.path.insert(0, ".")
from drm.cpu6502 import CPU, load_prg

prg = load_prg()
ENTRY, EXIT = {"H": 0x91FB, "V": 0x9469}, {"H": "h", "V": "v"}
for path in sys.argv[1:]:
    per, off, handler, extra = Counter(), Counter(), [], []
    for line in open(path):
        d = json.loads(line)
        ev = d["ev"].split()
        t = lambda e: int(e[1:].split(":")[0])
        ns = [t(e) for e in ev if e[0] == "N"]
        per.update(b - a for a, b in zip(ns, ns[1:]) if b - a < 40000)
        for ci, i in enumerate(k for k, e in enumerate(ev) if e[0] in "HV"):
            if ev[i - 1][0] == "N":
                off[t(ev[i]) - t(ev[i - 1])] += 1
            j = next(j for j in range(i + 1, len(ev)) if ev[j][0] == EXIT[ev[i][0]])
            nn = sum(e[0] == "N" for e in ev[i:j])
            cpu = CPU(prg)
            cpu.ram[:] = bytes.fromhex(d["dumps"][ci])
            hits, _ = cpu.call(ENTRY[ev[i][0]], (0x92DA, 0x952F))
            total = (hits[0x92DA] + hits[0x952F])[0]
            dt = t(ev[j]) - t(ev[i]) - total
            (handler.append(dt / nn) if nn else extra.append(dt))
    print(path)
    print("  NMI period", min(per), "..", max(per))
    print("  start offset", min(off), "..", max(off), dict(off.most_common(6)))
    print("  handler", min(handler, default=None), "..", max(handler, default=None), "n", len(handler))
    print("  DMA extra (no NMI)", min(extra), "..", max(extra), "nonzero", sum(1 for e in extra if e), "/", len(extra))
