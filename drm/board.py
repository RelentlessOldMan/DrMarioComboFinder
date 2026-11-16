"""Placement-level rules of NES Dr. Mario: lock a pill at a chosen spot, then resolve drops, matches
and cascades exactly as the game's pillPlaced steps do (ref/nostaljipi-disasm game_logic.asm:
checkDrop, checkHorMatch, checkVerMatch, updateField, virusDestroyed, scoreIncrease).

The board is the game's own RAM: mem[i] = byte at $0400+i for i in 0..255. Cells 0..127 are the
field (row*8+col, row 0 at the top); 128..255 is RAM the routines read past the field (normally FF).
No frames, gravity or inputs are simulated; `resolve` records which step each kill happens in so the
glitch check can be added on top.
"""
import os

EMPTY = 0xFF
TOP, BOTTOM, LEFT, RIGHT, SINGLE = 0x40, 0x50, 0x60, 0x70, 0x80
CLEARED, VIRUS, JUST_EMPTIED = 0xB0, 0xD0, 0xF0
SPAWN = (3, 4)  # row 0 columns the next pill appears in


def _load_multipliers(rom=os.path.join(os.path.dirname(__file__), "..", "drmario.nes")):
    """scoreMultiplier_table plus the ROM bytes after it (the index is not capped). 0 means 256 loops."""
    d = open(rom, "rb").read()
    i = d.find(bytes([1, 2, 4, 8, 16, 32, 32, 32, 32, 32, 32, 10, 3, 0]))
    assert i >= 0, "scoreMultiplier_table not found in ROM"
    return [b or 256 for b in d[i:i + 128]]


MULT = _load_multipliers()


def kill_score(k, speed):
    """Points for the k-th virus (0-based) killed since the pill locked. speed 0=LOW 1=MED 2=HI.
    Ignores the 6-digit BCD saturation of the real score."""
    return MULT[k] * (speed + 1) * 100


def combo_score(kills, speed):
    return sum(kill_score(k, speed) for k in range(kills))


def new_mem(field):
    return list(field) + [EMPTY] * 128


def lock(mem, row, col, vertical, c1, c2):
    """Write a pill. Horizontal: c1 at (row,col), c2 at (row,col+1). Vertical: c1 on top at (row-1,col),
    c2 at the bottom (row,col)."""
    p = row * 8 + col
    if vertical:
        mem[p - 8], mem[p] = TOP | c1, BOTTOM | c2
    else:
        mem[p], mem[p + 1] = LEFT | c1, RIGHT | c2


def check_drop(mem):
    """One checkDrop pass. Returns the number of halves moved."""
    moved = 0
    y = 127
    while True:
        if mem[y] >= JUST_EMPTIED:
            mem[y] = EMPTY
            t = (y - 8) & 0xFF
            above = mem[t]
            typ = above & 0xF0
            if above < 0x90 and typ != LEFT:
                if typ == RIGHT:
                    if mem[(y - 1) & 0xFF] >= JUST_EMPTIED:  # both cells under the horizontal pill empty
                        mem[y], mem[t] = mem[t], EMPTY
                        mem[(y - 1) & 0xFF], mem[(t - 1) & 0xFF] = mem[(t - 1) & 0xFF], EMPTY
                        moved += 2
                        y -= 1  # left half done too; the loop's own decrement follows
                else:
                    mem[y], mem[t] = above, EMPTY
                    moved += 1
        y -= 1
        if y < 0:
            return moved


def _kill(mem, p, kills):
    if mem[p] & 0xF0 == VIRUS:
        kills.append(p)
    mem[p] = (mem[p] & 0x0F) | CLEARED


def check_hor_match(mem, kills):
    matched = False
    pos = 0
    while True:
        tmp = pos
        if mem[pos] < JUST_EMPTIED:
            color = mem[pos] & 0x0F
            chain = 0
            while True:
                tmp += 1
                if tmp & 7 == 0 or mem[tmp] & 0x0F != color:
                    break
                chain += 1
            if chain >= 3:
                for q in range(pos, tmp):
                    _kill(mem, q, kills)
                matched = True
            pos = tmp
        else:
            pos += 1
        if pos & 7 == 0 or pos & 7 >= 6:
            if pos == 128:
                return matched
            if pos & 7:
                pos = (pos & 0x78) + 8
                if pos == 128:
                    return matched


def check_ver_match(mem, kills):
    matched = False
    pos = 0
    while True:
        tmp = pos
        if mem[pos] < JUST_EMPTIED:
            color = mem[pos] & 0x0F
            chain = 0
            while True:
                tmp = (tmp + 8) & 0xFF
                if tmp & 0xF8 == 0 or mem[tmp] & 0x0F != color:
                    break
                chain += 1
            if chain >= 3:
                q = pos
                while q != tmp:
                    _kill(mem, q, kills)
                    q = (q + 8) & 0xFF
                matched = True
            pos = tmp
        else:
            pos += 8
        if pos >= 104:  # lastRow_forMatch
            pos = (pos + 1) & 7
            if pos == 0:
                return matched


def update_field(mem):
    for p in range(127, -1, -1):
        v = mem[p]
        typ = v & 0xF0
        if typ == CLEARED:
            mem[p] = v | JUST_EMPTIED
        elif typ == TOP and mem[p + 8] & 0xF0 != BOTTOM:
            mem[p] = (v & 0x0F) | SINGLE
        elif typ == BOTTOM and mem[(p - 8) & 0xFF] & 0xF0 != TOP:
            mem[p] = (v & 0x0F) | SINGLE
        elif typ == LEFT and mem[p + 1] & 0xF0 != RIGHT:
            mem[p] = (v & 0x0F) | SINGLE
        elif typ == RIGHT and mem[(p - 1) & 0xFF] & 0xF0 != LEFT:
            mem[p] = (v & 0x0F) | SINGLE


def resolve(mem):
    """Run the pillPlaced steps after a lock until the field is still. Returns a list of cascade steps,
    each {"drops": passes before the match check, "hor": [virus cells killed], "ver": [...]}.
    The last entry has no kills. Kill order within the pill is hor then ver, step by step."""
    steps = []
    while True:
        passes = 0
        while check_drop(mem):
            passes += 1
        hor, ver = [], []
        m = check_hor_match(mem, hor)
        m = check_ver_match(mem, ver) or m
        steps.append({"drops": passes, "hor": hor, "ver": ver})
        update_field(mem)
        if not m:
            return steps


def placements(mem):
    """Every resting spot for a pill: (row, col, vertical) with the lower cell(s) supported.
    Reachability from the spawn point is not checked here."""
    out = []
    occ = lambda p: mem[p] != EMPTY
    for row in range(16):
        for col in range(8):
            p = row * 8 + col
            below = lambda q: q >= 120 or occ(q + 8)
            if col < 7 and not occ(p) and not occ(p + 1) and (below(p) or below(p + 1)):
                out.append((row, col, False))
            if row >= 1 and not occ(p) and not occ(p - 8) and below(p):
                out.append((row, col, True))
    return out


def lost(mem):
    return any(mem[c] != EMPTY for c in SPAWN)


def show(mem):
    ch = "yrb"
    rows = []
    for row in range(16):
        s = ""
        for col in range(8):
            v = mem[row * 8 + col]
            if v == EMPTY:
                s += "."
            elif v & 0xF0 == VIRUS:
                s += ch[v & 3].upper()
            else:
                s += ch[v & 3] if v & 3 < 3 else "?"
        rows.append(s)
    return "\n".join(rows)
