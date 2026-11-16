"""Minimal cycle-counting NMOS 6502 for running Dr. Mario's pure-logic routines (match checks, score
increase) on a RAM snapshot. 2 KB RAM mirrored to $1FFF, the 32 KB PRG at $8000, nothing else: I/O reads
return 0 and writes are ignored. Official opcodes only. Cycle counts include page-cross and branch
penalties, so call() returns the same cycle offsets Mesen reports.
"""
import os

ROM = os.path.join(os.path.dirname(__file__), "..", "drmario.nes")

# (mnemonic, mode, base cycles, +1 on page cross)
_OPS = {}


def _op(code, mn, mode, cyc, px=False):
    _OPS[code] = (mn, mode, cyc, px)


for mn, codes in {
    "ADC": [(0x69, "imm", 2), (0x65, "zp", 3), (0x75, "zpx", 4), (0x6D, "abs", 4), (0x7D, "absx", 4, 1),
            (0x79, "absy", 4, 1), (0x61, "indx", 6), (0x71, "indy", 5, 1)],
    "AND": [(0x29, "imm", 2), (0x25, "zp", 3), (0x35, "zpx", 4), (0x2D, "abs", 4), (0x3D, "absx", 4, 1),
            (0x39, "absy", 4, 1), (0x21, "indx", 6), (0x31, "indy", 5, 1)],
    "ASL": [(0x0A, "acc", 2), (0x06, "zp", 5), (0x16, "zpx", 6), (0x0E, "abs", 6), (0x1E, "absx", 7)],
    "BIT": [(0x24, "zp", 3), (0x2C, "abs", 4)],
    "BPL": [(0x10, "rel", 2)], "BMI": [(0x30, "rel", 2)], "BVC": [(0x50, "rel", 2)], "BVS": [(0x70, "rel", 2)],
    "BCC": [(0x90, "rel", 2)], "BCS": [(0xB0, "rel", 2)], "BNE": [(0xD0, "rel", 2)], "BEQ": [(0xF0, "rel", 2)],
    "BRK": [(0x00, "imp", 7)],
    "CMP": [(0xC9, "imm", 2), (0xC5, "zp", 3), (0xD5, "zpx", 4), (0xCD, "abs", 4), (0xDD, "absx", 4, 1),
            (0xD9, "absy", 4, 1), (0xC1, "indx", 6), (0xD1, "indy", 5, 1)],
    "CPX": [(0xE0, "imm", 2), (0xE4, "zp", 3), (0xEC, "abs", 4)],
    "CPY": [(0xC0, "imm", 2), (0xC4, "zp", 3), (0xCC, "abs", 4)],
    "DEC": [(0xC6, "zp", 5), (0xD6, "zpx", 6), (0xCE, "abs", 6), (0xDE, "absx", 7)],
    "EOR": [(0x49, "imm", 2), (0x45, "zp", 3), (0x55, "zpx", 4), (0x4D, "abs", 4), (0x5D, "absx", 4, 1),
            (0x59, "absy", 4, 1), (0x41, "indx", 6), (0x51, "indy", 5, 1)],
    "CLC": [(0x18, "imp", 2)], "SEC": [(0x38, "imp", 2)], "CLI": [(0x58, "imp", 2)], "SEI": [(0x78, "imp", 2)],
    "CLV": [(0xB8, "imp", 2)], "CLD": [(0xD8, "imp", 2)], "SED": [(0xF8, "imp", 2)],
    "INC": [(0xE6, "zp", 5), (0xF6, "zpx", 6), (0xEE, "abs", 6), (0xFE, "absx", 7)],
    "JMP": [(0x4C, "abs", 3), (0x6C, "ind", 5)],
    "JSR": [(0x20, "abs", 6)],
    "LDA": [(0xA9, "imm", 2), (0xA5, "zp", 3), (0xB5, "zpx", 4), (0xAD, "abs", 4), (0xBD, "absx", 4, 1),
            (0xB9, "absy", 4, 1), (0xA1, "indx", 6), (0xB1, "indy", 5, 1)],
    "LDX": [(0xA2, "imm", 2), (0xA6, "zp", 3), (0xB6, "zpy", 4), (0xAE, "abs", 4), (0xBE, "absy", 4, 1)],
    "LDY": [(0xA0, "imm", 2), (0xA4, "zp", 3), (0xB4, "zpx", 4), (0xAC, "abs", 4), (0xBC, "absx", 4, 1)],
    "LSR": [(0x4A, "acc", 2), (0x46, "zp", 5), (0x56, "zpx", 6), (0x4E, "abs", 6), (0x5E, "absx", 7)],
    "NOP": [(0xEA, "imp", 2)],
    "ORA": [(0x09, "imm", 2), (0x05, "zp", 3), (0x15, "zpx", 4), (0x0D, "abs", 4), (0x1D, "absx", 4, 1),
            (0x19, "absy", 4, 1), (0x01, "indx", 6), (0x11, "indy", 5, 1)],
    "TAX": [(0xAA, "imp", 2)], "TXA": [(0x8A, "imp", 2)], "DEX": [(0xCA, "imp", 2)], "INX": [(0xE8, "imp", 2)],
    "TAY": [(0xA8, "imp", 2)], "TYA": [(0x98, "imp", 2)], "DEY": [(0x88, "imp", 2)], "INY": [(0xC8, "imp", 2)],
    "ROL": [(0x2A, "acc", 2), (0x26, "zp", 5), (0x36, "zpx", 6), (0x2E, "abs", 6), (0x3E, "absx", 7)],
    "ROR": [(0x6A, "acc", 2), (0x66, "zp", 5), (0x76, "zpx", 6), (0x6E, "abs", 6), (0x7E, "absx", 7)],
    "RTI": [(0x40, "imp", 6)], "RTS": [(0x60, "imp", 6)],
    "SBC": [(0xE9, "imm", 2), (0xE5, "zp", 3), (0xF5, "zpx", 4), (0xED, "abs", 4), (0xFD, "absx", 4, 1),
            (0xF9, "absy", 4, 1), (0xE1, "indx", 6), (0xF1, "indy", 5, 1)],
    "STA": [(0x85, "zp", 3), (0x95, "zpx", 4), (0x8D, "abs", 4), (0x9D, "absx", 5), (0x99, "absy", 5),
            (0x81, "indx", 6), (0x91, "indy", 6)],
    "TXS": [(0x9A, "imp", 2)], "TSX": [(0xBA, "imp", 2)], "PHA": [(0x48, "imp", 3)], "PLA": [(0x68, "imp", 4)],
    "PHP": [(0x08, "imp", 3)], "PLP": [(0x28, "imp", 4)],
    "STX": [(0x86, "zp", 3), (0x96, "zpy", 4), (0x8E, "abs", 4)],
    "STY": [(0x84, "zp", 3), (0x94, "zpx", 4), (0x8C, "abs", 4)],
}.items():
    for c in codes:
        _op(c[0], mn, c[1], c[2], len(c) > 3)

_LEN = {"imp": 1, "acc": 1, "imm": 2, "zp": 2, "zpx": 2, "zpy": 2, "rel": 2, "indx": 2, "indy": 2,
        "abs": 3, "absx": 3, "absy": 3, "ind": 3}


def load_prg(rom=ROM):
    d = open(rom, "rb").read()
    return d[16:16 + 0x8000]


class CPU:
    def __init__(self, prg=None):
        self.prg = prg or load_prg()
        self.ram = bytearray(0x800)
        self.a = self.x = self.y = 0
        self.sp = 0xFD
        self.c = self.z = self.i = self.d = self.v = self.n = 0
        self.cycles = 0

    def rd(self, a):
        if a < 0x2000:
            return self.ram[a & 0x7FF]
        if a >= 0x8000:
            return self.prg[a - 0x8000]
        return 0

    def wr(self, a, v):
        if a < 0x2000:
            self.ram[a & 0x7FF] = v & 0xFF

    def push(self, v):
        self.ram[0x100 + self.sp] = v & 0xFF
        self.sp = (self.sp - 1) & 0xFF

    def pull(self):
        self.sp = (self.sp + 1) & 0xFF
        return self.ram[0x100 + self.sp]

    def p(self):
        return (self.n << 7) | (self.v << 6) | 0x20 | (self.d << 3) | (self.i << 2) | (self.z << 1) | self.c

    def setp(self, v):
        self.n, self.v, self.d, self.i, self.z, self.c = (v >> 7) & 1, (v >> 6) & 1, (v >> 3) & 1, (v >> 2) & 1, (v >> 1) & 1, v & 1

    def nz(self, v):
        v &= 0xFF
        self.n, self.z = v >> 7, int(v == 0)
        return v

    def call(self, addr, watch=(), limit=10_000_000):
        """JSR to addr and run until it returns. Returns ({watched pc: [cycle offsets]}, total cycles),
        cycle offsets counted from the first instruction of addr like Mesen's exec callbacks."""
        hits = {w: [] for w in watch}
        self.hit_a = {w: [] for w in watch}  # A at each hit (e.g. the value a watched sta stores)
        self.push(0xFF); self.push(0xFE)  # return to $FFFF, the stop sentinel
        sp_stop = self.sp
        pc, start = addr, self.cycles
        rd, wr = self.rd, self.wr
        while True:
            if pc in hits:
                hits[pc].append(self.cycles - start)
                self.hit_a[pc].append(self.a)
            op = rd(pc)
            mn, mode, cyc, px = _OPS[op]
            n = _LEN[mode]
            lo = rd(pc + 1) if n > 1 else 0
            hi = rd(pc + 2) if n > 2 else 0
            npc = pc + n
            ea = None
            if mode == "zp":
                ea = lo
            elif mode == "zpx":
                ea = (lo + self.x) & 0xFF
            elif mode == "zpy":
                ea = (lo + self.y) & 0xFF
            elif mode == "abs":
                ea = lo | (hi << 8)
            elif mode in ("absx", "absy"):
                base = lo | (hi << 8)
                ea = (base + (self.x if mode == "absx" else self.y)) & 0xFFFF
                if px and (ea ^ base) & 0xFF00:
                    cyc += 1
            elif mode == "indx":
                z = (lo + self.x) & 0xFF
                ea = self.ram[z] | (self.ram[(z + 1) & 0xFF] << 8)
            elif mode == "indy":
                base = self.ram[lo] | (self.ram[(lo + 1) & 0xFF] << 8)
                ea = (base + self.y) & 0xFFFF
                if px and (ea ^ base) & 0xFF00:
                    cyc += 1
            elif mode == "ind":
                ptr = lo | (hi << 8)
                ea = rd(ptr) | (rd((ptr & 0xFF00) | ((ptr + 1) & 0xFF)) << 8)

            def val():
                return lo if mode == "imm" else (self.a if mode == "acc" else rd(ea))

            def store(v):
                if mode == "acc":
                    self.a = v & 0xFF
                else:
                    wr(ea, v)

            if mn == "LDA": self.a = self.nz(val())
            elif mn == "LDX": self.x = self.nz(val())
            elif mn == "LDY": self.y = self.nz(val())
            elif mn == "STA": wr(ea, self.a)
            elif mn == "STX": wr(ea, self.x)
            elif mn == "STY": wr(ea, self.y)
            elif mn in ("ADC", "SBC"):
                m = val()
                if mn == "SBC":
                    m ^= 0xFF  # NES 2A03 has no decimal mode
                r = self.a + m + self.c
                self.v = int(((self.a ^ r) & (m ^ r) & 0x80) != 0)
                self.c = int(r > 0xFF)
                self.a = self.nz(r)
            elif mn == "AND": self.a = self.nz(self.a & val())
            elif mn == "ORA": self.a = self.nz(self.a | val())
            elif mn == "EOR": self.a = self.nz(self.a ^ val())
            elif mn in ("CMP", "CPX", "CPY"):
                r = {"CMP": self.a, "CPX": self.x, "CPY": self.y}[mn] - val()
                self.c = int(r >= 0)
                self.nz(r)
            elif mn == "BIT":
                m = val()
                self.z, self.n, self.v = int((self.a & m) == 0), m >> 7, (m >> 6) & 1
            elif mn in ("ASL", "LSR", "ROL", "ROR"):
                m = val()
                if mn == "ASL": self.c, r = m >> 7, m << 1
                elif mn == "LSR": self.c, r = m & 1, m >> 1
                elif mn == "ROL": r = (m << 1) | self.c; self.c = m >> 7
                else: r = (m >> 1) | (self.c << 7); self.c = m & 1
                store(self.nz(r))
            elif mn in ("INC", "DEC"):
                wr(ea, self.nz(rd(ea) + (1 if mn == "INC" else -1)))
            elif mn == "INX": self.x = self.nz(self.x + 1)
            elif mn == "INY": self.y = self.nz(self.y + 1)
            elif mn == "DEX": self.x = self.nz(self.x - 1)
            elif mn == "DEY": self.y = self.nz(self.y - 1)
            elif mn == "TAX": self.x = self.nz(self.a)
            elif mn == "TAY": self.y = self.nz(self.a)
            elif mn == "TXA": self.a = self.nz(self.x)
            elif mn == "TYA": self.a = self.nz(self.y)
            elif mn == "TSX": self.x = self.nz(self.sp)
            elif mn == "TXS": self.sp = self.x
            elif mn == "PHA": self.push(self.a)
            elif mn == "PLA": self.a = self.nz(self.pull())
            elif mn == "PHP": self.push(self.p() | 0x10)
            elif mn == "PLP": self.setp(self.pull())
            elif mn[0] == "B" and mode == "rel":
                f = {"BPL": not self.n, "BMI": self.n, "BVC": not self.v, "BVS": self.v, "BCC": not self.c,
                     "BCS": self.c, "BNE": not self.z, "BEQ": self.z}[mn]
                if f:
                    t = (npc + (lo - 256 if lo & 0x80 else lo)) & 0xFFFF
                    cyc += 1 + int((t ^ npc) & 0xFF00 != 0)
                    npc = t
            elif mn == "JMP": npc = ea
            elif mn == "JSR":
                r = npc - 1
                self.push(r >> 8); self.push(r)
                npc = ea
            elif mn == "RTS":
                if self.sp == sp_stop:
                    self.pull(); self.pull()
                    self.cycles += cyc
                    return hits, self.cycles - start
                lo2 = self.pull(); hi2 = self.pull()
                npc = ((hi2 << 8) | lo2) + 1
            elif mn == "RTI":
                self.setp(self.pull()); lo2 = self.pull(); hi2 = self.pull()
                npc = (hi2 << 8) | lo2
            elif mn in ("CLC", "SEC"): self.c = int(mn == "SEC")
            elif mn in ("CLI", "SEI"): self.i = int(mn == "SEI")
            elif mn in ("CLD", "SED"): self.d = int(mn == "SED")
            elif mn == "CLV": self.v = 0
            elif mn == "NOP": pass
            else:
                raise RuntimeError(f"unhandled {mn} at {pc:04X}")
            self.cycles += cyc
            pc = npc
            if self.cycles - start > limit:
                raise RuntimeError("cycle limit")
