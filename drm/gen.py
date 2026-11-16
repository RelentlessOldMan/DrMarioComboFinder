"""NES Dr. Mario level generation (RNG, pill reserve, viruses), from the disassembly.

References are to ref/nostaljipi-disasm (Rev A labels); PRG0 runs the same code.
Board index = row*8 + col, row 0 at the top (RAM $0400 + index). Colours 0=Y 1=R 2=B.
"""

SEED = 0x8988
PERIOD = 32767
EMPTY = 0xFF
VIRUS = 0xD0

# addVirus_maxHeight_basedOnLvl [$A3F8], indexed by the real level (0-34)
MAX_HEIGHT = [9] * 15 + [10, 10, 11, 11] + [12] * 16
# virusColor_random [$A807]
VIRUS_COLOR_RANDOM = [0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 1]
COLOR_BIT = [1, 2, 4, 0]  # virusPlacement_colorBits; colour nibble 3 (empty) adds nothing


def step(r):
    """One randomNumberGenerator call. r = ($17 << 8) | $18."""
    bit = ((r >> 9) ^ (r >> 1)) & 1
    return (r >> 1) | (bit << 15)


def advance(r, n):
    for _ in range(n):
        r = step(r)
    return r


def build_index():
    """state -> number of steps from SEED (0..PERIOD-1)."""
    idx, r = {}, SEED
    for i in range(PERIOD):
        idx[r] = i
        r = step(r)
    assert r == SEED
    return idx


def pill_reserve(r):
    """generatePillsReserve [$82B0]: 128 pill ids (0-8), RAM $0780 order. Returns (reserve, rng)."""
    res = [0] * 128
    pid = 0
    for x in range(127, -1, -1):
        r = step(r)
        pid = (pid + ((r >> 8) & 0x0F)) % 9
        res[x] = pid
    return res, r


def pill_colors(pid):
    return pid // 3, pid % 3  # colorCombination_left / _right


def add_viruses(r, level, beyond):
    """addVirus [$9D19] repeated until done. `beyond` = 16 RAM bytes at $0480-$048F, which the
    'two rows below' check reads for viruses in the bottom two rows (it has no bounds check).
    Returns (field[128], rng)."""
    field = [EMPTY] * 128
    mem = field + list(beyond)
    to_add = (min(level, 20) + 1) * 4
    maxh = MAX_HEIGHT[level]
    while to_add:
        while True:
            r = step(r)
            h = (r >> 8) & 0x0F
            if h <= maxh:
                break
        pos = 8 * (15 - h) + (r & 7)
        color = to_add & 3
        if color == 3:
            r = step(r)
            color = VIRUS_COLOR_RANDOM[r & 0x0F]
        placed = False
        while pos < 128:
            if mem[pos] != EMPTY:
                pos += 1
                continue
            mask = COLOR_BIT[mem[pos - 16] & 3]  # pos >= 24 always (max height 12)
            mask |= COLOR_BIT[mem[pos + 16] & 3]  # no bounds check: reads $0480-$048F
            if (pos & 7) >= 2:
                mask |= COLOR_BIT[mem[pos - 2] & 3]
            if (pos & 7) < 6:
                mask |= COLOR_BIT[mem[pos + 2] & 3]
            if mask == 7:
                pos += 1
                continue
            while COLOR_BIT[color] & mask:
                color = color - 1 if color > 0 else 2
            mem[pos] = VIRUS | color
            to_add -= 1
            placed = True
            break
        if not placed:
            continue  # reached the end of the field: try again next frame with fresh draws
    return mem[:128], r


def generate(start_rng, level, beyond=(EMPTY,) * 16):
    """Everything set up when START is pressed with the RNG at start_rng (after the options-loop step)."""
    reserve, r = pill_reserve(start_rng)
    field, r = add_viruses(r, level, beyond)
    return {"reserve": reserve, "field": field, "rng_after": r}


def show(field):
    ch = {0: "y", 1: "r", 2: "b"}
    rows = []
    for row in range(16):
        s = ""
        for col in range(8):
            v = field[row * 8 + col]
            s += "." if v == EMPTY else (ch[v & 3].upper() if v & 0xF0 == VIRUS else ch.get(v & 3, "?"))
        rows.append(s)
    return "\n".join(rows)


if __name__ == "__main__":
    import sys
    level = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    g = generate(advance(SEED, n), level)
    print(show(g["field"]))
    print("pills:", " ".join("%d%d" % pill_colors(p) for p in g["reserve"][:10]), "...")
