"""Setup search: choose where each pill of a known sequence goes so that one pill sets off as big a
cascade as possible. Works on placements only (drm/board.py); lua/play_plan.lua then plays the plan.

Pill moves are kept simple so the executor can always do them: rotate at the top, slide along the top
row, then drop straight down. A placement is (rot, x) and the landing row follows from the drop.
Rotation layouts (x = left or only column; c1, c2 = $0301, $0302): 0 horizontal c1|c2, 1 vertical
c2 over c1, 2 horizontal c2|c1, 3 vertical c1 over c2. 0 and 1 are seen in Mesen; 2 and 3 are assumed
mirrors and get checked by tools/check_play.py.
"""
from drm import board
from drm.gen import pill_colors

SPAWN_COL = 3


def cells(rot, x, row, c1, c2):
    """[(pos, byte)] of a pill whose lower (or only) row is `row`."""
    p = row * 8 + x
    if rot == 0:
        return [(p, board.LEFT | c1), (p + 1, board.RIGHT | c2)]
    if rot == 2:
        return [(p, board.LEFT | c2), (p + 1, board.RIGHT | c1)]
    if rot == 1:
        return [(p - 8, board.TOP | c2), (p, board.BOTTOM | c1)]
    return [(p - 8, board.TOP | c1), (p, board.BOTTOM | c2)]


def drop(mem, rot, x):
    """Landing row of (rot, x) dropped from the top, or None if the top-row slide is blocked."""
    vertical = rot % 2 == 1
    if x < 0 or x > (7 if vertical else 6):
        return None
    cols = [x] if vertical else [x, x + 1]
    # slide along rows 0-1 from the spawn columns (3-4) to x
    lo, hi = min(x, SPAWN_COL), max(cols[-1], SPAWN_COL + 1)
    if any(mem[r * 8 + c] != board.EMPTY for r in (0, 1) for c in range(lo, hi + 1)):
        return None
    row = 1 if vertical else 0
    while row < 15 and all(mem[(row + 1) * 8 + c] == board.EMPTY for c in cols):
        row += 1
    return row


def moves(mem, pid):
    """[(rot, x, mem_after_lock)] for every distinct placement of pill id pid."""
    c1, c2 = pill_colors(pid)
    rots = (0, 1) if c1 == c2 else (0, 1, 2, 3)
    out = []
    for rot in rots:
        for x in range(8):
            row = drop(mem, rot, x)
            if row is None:
                continue
            m = list(mem)
            for p, v in cells(rot, x, row, c1, c2):
                m[p] = v
            out.append((rot, x, m))
    return out


def play(mem, rot, x, pid):
    """Lock and resolve. Returns (mem_after, kills, steps)."""
    for r, xx, m in moves(mem, pid):
        if (r, xx) == (rot, x):
            steps = board.resolve(m)
            return m, sum(len(s["hor"]) + len(s["ver"]) for s in steps), steps
    raise ValueError("placement not available")


def viruses(mem):
    return sum(1 for v in mem[:128] if v & 0xF0 == board.VIRUS)


def _windows():
    out = []
    for r in range(16):
        for c in range(8):
            if c <= 4:
                out.append([r * 8 + c + i for i in range(4)])
            if r <= 12:
                out.append([(r + i) * 8 + c for i in range(4)])
    return out


WINDOWS = _windows()


def setup_value(mem):
    """How close the board is to many chains at once: every line of 4 cells holding one colour only,
    with at least one virus, scores (cells filled)^2. Rewards half-built chains a cascade can finish."""
    v = 0
    for w in WINDOWS:
        col, n, vir = -1, 0, False
        for p in w:
            x = mem[p]
            if x == board.EMPTY:
                continue
            c = x & 0x0F
            if col < 0:
                col = c
            elif c != col:
                break
            n += 1
            vir |= x & 0xF0 == board.VIRUS
        else:
            if vir and n >= 2:
                v += n * n
    return v


def search(field, reserve, first, depth, beam=60, waste=2.0, shape=0.0):
    """Beam search over pills reserve[first], reserve[first+1], ... Each state keeps its plan; a state's
    value is the best single-pill kill count so far, plus a lookahead of the best next-pill kill count,
    minus `waste` per virus killed by pills other than the best one, plus `shape` x setup_value. Returns the best (kills, plan, k)
    where plan is [(rot, x)] and k is the index in plan of the big pill."""
    start = board.new_mem(field)
    states = [(0.0, start, [], 0, -1, 0)]  # value, mem, plan, best kills, best index, total kills
    best = (0, [], -1)
    for d in range(depth):
        pid = reserve[(first + d) % 128]
        nxt = reserve[(first + d + 1) % 128]
        children = {}
        for _, mem, plan, bk, bi, tot in states:
            for rot, x, m in moves(mem, pid):
                steps = board.resolve(m)
                if board.lost(m):
                    continue
                k = sum(len(s["hor"]) + len(s["ver"]) for s in steps)
                nbk, nbi = (k, d) if k > bk else (bk, bi)
                ntot = tot + k
                if nbk > best[0]:
                    best = (nbk, plan + [(rot, x)], nbi)
                look = 0
                for _, _, m2 in moves(m, nxt):
                    steps2 = board.resolve(m2)
                    look = max(look, sum(len(s["hor"]) + len(s["ver"]) for s in steps2))
                value = max(nbk, look) - waste * (ntot - nbk) + 0.01 * look
                if shape:
                    value += shape * setup_value(m)
                key = bytes(m[:128])
                if key not in children or children[key][0] < value:
                    children[key] = (value, m, plan + [(rot, x)], nbk, nbi, ntot)
        states = sorted(children.values(), key=lambda s: -s[0])[:beam]
        if not states:
            break
    return best
