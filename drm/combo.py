"""Evaluate one pill: resolve the cascade with drm/board.py and time every match routine call with
drm/glitch.py. A pill is glitch-free when every checkHorMatch/checkVerMatch call is safe."""
from drm import board, glitch


def evaluate(mem, speed=2, score=0, timing=True, profile="music", p2=False):
    """mem: board RAM right after the pill locks (board.new_mem + board.lock). Resolves in place.
    Returns dict: kills, points, safe, margin (smallest NMI distance of any clear loop), calls."""
    kills, points, calls = 0, 0, []
    safe, margin = True, float("inf")
    while True:
        while board.check_drop(mem):
            pass
        matched = False
        for name, check, entry in (("hor", board.check_hor_match, glitch.HOR), ("ver", board.check_ver_match, glitch.VER)):
            if timing:
                ends = []
                wins, total, _ = glitch.windows(glitch.ram_image(mem, kills, speed, score + points), entry, ends)
            got = []
            matched = check(mem, got) or matched
            for _ in got:
                points += board.kill_score(kills, speed)
                kills += 1
            if timing and wins:
                ok, m = glitch.safe_call(wins, total, profile, p2, ends)
                safe &= ok
                margin = min(margin, m)
                calls.append({"routine": name, "kills": len(got), "cycles": total, "margin": m,
                              "wins": wins, "ends": ends})
        board.update_field(mem)
        if not matched:
            return {"kills": kills, "points": points, "safe": safe, "margin": margin, "calls": calls}
