#!/usr/bin/env python3
"""lf-sz recount: reads only result.json files (and PASSMARKS.md's fixed numbers) and prints the marks. Pure python.
  python -B scripts/claude_lfsz_recount.py RUNS_DIR      (RUNS_DIR holds <arm>-s<seed>/result.json)
  python -B scripts/claude_lfsz_recount.py selftest      (a synthetic check of each reading)
"""
import json
import sys
from pathlib import Path

SEEDS = (9, 10)
WEIGHTS = {"loop8": 6386174, "loop2w": 6438814, "loop4w": 6334182}
LF8_T8 = {9: 559, 10: 561}
BAR_T, BAR_G, LOW_T, LOW_G, R_TOL = 105, 80, 50, 40, 53


def load(d):
    out = {}
    for arm in WEIGHTS:
        for s in SEEDS:
            p = Path(d) / f"{arm}-s{s}" / "result.json"
            if p.exists():
                out[(arm, s)] = json.loads(p.read_text())
    return out


def row(r):
    ph = r["phases"]
    g = lambda p, k: ph[p][k]["right"]
    G, S, M = g("after_mazes", "grids5"), g("after_mazes", "sums4"), g("after_mazes", "maze7")
    return dict(A=g("after_grids", "grids5"), B=g("after_sums", "sums4"), G=G, S=S, M=M, T=G + S + M,
                start0=all(v["right"] == 0 for v in ph["start"].values()), w=r["weights"], min=r.get("minutes"))


def read(rows):
    """rows[(arm, seed)] -> dict from row(); returns (verdict, detail)"""
    need = [(a, s) for a in WEIGHTS for s in SEEDS]
    miss = [k for k in need if k not in rows]
    if miss:
        return "INCOMPLETE", f"missing {miss}"
    bad_w = [k for k in need if rows[k]["w"] != WEIGHTS[k[0]]]
    if bad_w:
        return "INCONCLUSIVE", f"weights differ from PASSMARKS for {bad_w}"
    if not all(rows[k].get("start0", True) for k in need):
        return "INCONCLUSIVE", "a start (untrained) score is not 0 (PASSMARKS self-check 4)"
    fail = lambda arm: any(rows[(arm, s)]["A"] < 120 or rows[(arm, s)]["B"] < 120 for s in SEEDS)
    if fail("loop8"):
        return "INCONCLUSIVE", "V failed for loop8"
    ok = [a for a in ("loop2w", "loop4w") if not fail(a)]
    if not ok:
        return "INCONCLUSIVE", "V failed for both wide arms"
    mean = lambda a, k: sum(rows[(a, s)][k] for s in SEEDS) / len(SEEDS)
    B = max(ok, key=lambda a: (mean(a, "T"), mean(a, "G")))
    dT = {s: rows[("loop8", s)]["T"] - rows[(B, s)]["T"] for s in SEEDS}
    dG = {s: rows[("loop8", s)]["G"] - rows[(B, s)]["G"] for s in SEEDS}
    mT, mG = sum(dT.values()) / 2, sum(dG.values()) / 2
    if mT >= BAR_T and mG >= BAR_G and all(dT[s] > 0 and dG[s] > 0 for s in SEEDS):
        v = "DEPTH ADDS (suggested, 2 seeds)"
    elif all(dT[s] <= LOW_T and dG[s] <= LOW_G for s in SEEDS):
        v = "SIZE EXPLAINS"
    else:
        v = "NOT SHOWN"
    return v, f"B={B} dT={dT} mean {mT:.1f}; dG={dG} mean {mG:.1f}"


def selftest():
    def mk(T8, G8, T2, G2, T4, G4):
        rows = {}
        for arm, (T, G) in {"loop8": (T8, G8), "loop2w": (T2, G2), "loop4w": (T4, G4)}.items():
            for s in SEEDS:
                rows[(arm, s)] = dict(A=200, B=200, G=G, S=200, M=T - G - 200, T=T, w=WEIGHTS[arm])
        return rows
    assert read(mk(560, 180, 420, 90, 400, 80))[0].startswith("DEPTH ADDS")
    assert read(mk(560, 180, 540, 170, 400, 80))[0] == "SIZE EXPLAINS"
    assert read(mk(560, 180, 480, 130, 400, 80))[0] == "NOT SHOWN"
    assert read(mk(560, 180, 420, 90, 550, 175))[0] == "SIZE EXPLAINS"          # B is the better shallow arm
    r = mk(560, 180, 420, 90, 400, 80); r[("loop8", 9)]["A"] = 100
    assert read(r)[0] == "INCONCLUSIVE"
    print("lfsz recount selftest ok")


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    raw = load(sys.argv[1])
    rows = {k: row(v) for k, v in raw.items()}
    for k in sorted(rows):
        print(k, rows[k])
    for s in SEEDS:
        if ("loop8", s) in rows:
            print(f"R seed {s}: loop8 T {rows[('loop8', s)]['T']} vs lf-8 {LF8_T8[s]}, diff {rows[('loop8', s)]['T'] - LF8_T8[s]} (tol {R_TOL})")
    print(*read(rows), sep="  ")


if __name__ == "__main__":
    main()
