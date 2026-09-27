#!/usr/bin/env python3
"""c1-dev: the binomial noise next to each C1 margin (everyday-chat thread, 2026-09-27). New file only, report only.

Asked by the Thread manager (00:34 UTC 09-27): C1's bar (margin >= -12 of 60) sits inside the noise of 60
conversations, so every margin is reported with how much chance alone moves it. Ties count 0 in the margin and are left
out here, as a sign test does. For each rival: decisive conversations n = wins + losses; two-sided sign-test p against
"equal"; the build's share of decisive conversations with its 95% Wilson interval; the margin range an equal pair lands
in 95% of the time over the same n; and the chance of meeting the bar for a talker that truly wins 40% of decisive
conversations (how weak the bar is as a harm check).
  python3 -B scripts/claude_c1dev_noise.py --marks RUN/marksC1.json --bar -12
  python3 -B scripts/claude_c1dev_noise.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def pmf(k: int, n: int, p: float) -> float:
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def cdf(k: int, n: int, p: float = 0.5) -> float:
    return sum(pmf(i, n, p) for i in range(0, min(k, n) + 1)) if k >= 0 else 0.0


def sign_p(wins: int, losses: int) -> float:
    n = wins + losses
    return 1.0 if n == 0 else min(1.0, 2 * cdf(min(wins, losses), n))


def wilson(wins: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = wins / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def equal_range(n: int) -> tuple[int, int]:
    """Smallest symmetric margin range an equal pair lands in with chance >= 95% over n decisive conversations."""
    lo = 0
    while cdf(lo, n) <= 0.025:
        lo += 1
    return (2 * lo - n, n - 2 * lo)


def meet_chance(n: int, bar: int, share: float) -> float:
    need = math.ceil((n + bar) / 2)                        # wins with 2*wins - n >= bar
    return 1.0 - cdf(need - 1, n, share)


def noise(wins: int, losses: int, bar: int) -> dict:
    n = wins + losses
    lo, hi = wilson(wins, n)
    return {"margin": wins - losses, "decisive": n, "sign_p_two_sided": round(sign_p(wins, losses), 4),
            "build_share": round(wins / n, 3) if n else None, "share_95": [round(lo, 3), round(hi, 3)],
            "equal_pair_margin_95": list(equal_range(n)) if n else None,
            "bar_met_by_a_40pct_talker": round(meet_chance(n, bar, 0.40), 3) if n else None}


def selftest() -> None:
    ok = 0
    assert abs(cdf(23, 60) - 0.046) < 0.001 and abs(1 - cdf(36, 60) - 0.046) < 0.001; ok += 1   # ADDENDUM-14's 4.6%
    assert sign_p(30, 30) == 1.0 and sign_p(23, 37) < 0.1 < sign_p(24, 36); ok += 1
    lo, hi = equal_range(60)
    assert lo == -hi and cdf((lo + 60) // 2 - 1, 60) <= 0.025 < cdf((lo + 60) // 2, 60); ok += 1
    assert abs(meet_chance(60, -12, 0.5) - (1 - cdf(23, 60))) < 1e-12; ok += 1
    r = noise(20, 30, -12)
    assert r["margin"] == -10 and r["decisive"] == 50 and r["share_95"][0] < 0.4 < r["share_95"][1]; ok += 1
    print(f"c1dev noise selftest: {ok}/5 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marks", default="")
    ap.add_argument("--bar", type=int, default=-12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if not a.marks:
        raise SystemExit(__doc__)
    m = json.loads(Path(a.marks).read_text(encoding="utf-8"))
    out = {name: noise(v["build_wins"], v["rival_wins"], a.bar) for name, v in m["rivals"].items()}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
