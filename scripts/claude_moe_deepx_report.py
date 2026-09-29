#!/usr/bin/env python3
"""Words for the deep-expert comparison, from raw JSON only (no torch). Marks: artifacts/claude-moe-deepx-20260929/PASSMARKS.md.

  python3 -B scripts/claude_moe_deepx_report.py     # prints tables, writes REPORT.json next to PASSMARKS.md
MX rows come from the sealed run (artifacts/claude-moe-deep-20260929/eq-runs); X4 / X8 rows from
artifacts/claude-moe-deepx-20260929/eq-runs. Reuses the sealed report script's readers; no threshold is changed here.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_moe_deep_report as R  # noqa: E402

DX = R.ROOT / "artifacts" / "claude-moe-deepx-20260929"
ARMS = ("L8-E64-X4", "L8-E64-X8")
BAR, BAR_FEW = 8.0, 10.5


def rec(cfg, seed):
    d = (R.ART if cfg == R.MAIN else DX) / "eq-runs" / f"{cfg}-pre-s{seed}"
    return R.load(d / "adapt.json")


def gaps(a, b, fn):
    out = []
    for s in R.SEEDS:
        ca, cb = R.counts(rec(a, s), "dev"), R.counts(rec(b, s), "dev")
        out.append(None if ca is None or cb is None else fn(ca) - fn(cb))
    return out


def word(g, bar, up, down, none):
    done = [x for x in g if x is not None]
    if not done:
        return "NOT RUN"
    tag = "" if len(done) == len(g) else " (one seed: suggested)"
    if all(x >= bar for x in done):
        return up + tag
    if all(x <= -bar for x in done) if down else False:
        return down + tag
    if none == "PROVED WRONG" and all(x <= 0 for x in done):
        return none + tag
    return ("NOT SHOWN" if none == "PROVED WRONG" else "NOT SEPARABLE") + tag


def main():
    rep = {"rows": {}, "words": {}}
    for cfg in (R.MAIN,) + ARMS:
        for s in R.SEEDS:
            c = R.counts(rec(cfg, s), "dev")
            rep["rows"][f"{cfg}-s{s}"] = {"counts": c, "F_eq": R.r2(R.f_eq(c)), "F_few": R.r2(R.f_few(c)),
                                          "stop_failure_rungs": R.stop_failures(rec(cfg, s), "dev")}
            print(R.row(f"{cfg} s{s}", c))
    for a in ARMS:
        g = gaps(a, R.MAIN, R.f_eq)
        gf = gaps(a, R.MAIN, R.f_few)
        w = word(g, BAR, "HELPS", "HURTS", "PROVED WRONG")
        rep["words"][a] = {"gap_F_eq": [R.r2(x) for x in g], "gap_in_SD": [None if x is None else R.r2(x / R.NOISE_SD) for x in g],
                           "word": w, "gap_F_few": [R.r2(x) for x in gf], "few_word": word(gf, BAR_FEW, "HELPS", "HURTS", "NOT SEPARABLE")}
    g = gaps("L8-E64-X8", "L8-E64-X4", R.f_eq)
    rep["words"]["X8_minus_X4"] = {"gap_F_eq": [R.r2(x) for x in g], "word": word(g, BAR, "HELPS", "HURTS", "NOT SEPARABLE")}
    (DX / "REPORT.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep["words"], indent=1))


if __name__ == "__main__":
    main()
