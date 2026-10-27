#!/usr/bin/env python3
"""Marks of T2 (model-picked replay) and T1 (fresh-question replay) as code. Pure python, no torch.

Rules and reasons: artifacts/claude-dir-t2-selfpick-20260928/PASSMARKS.md and artifacts/claude-dir-t1-fresh-20260928/PASSMARKS.md
(sealed before any run). Constants below are the sealed numbers; change none after a score is seen.
  python3 scripts/claude_dir_t12_marks.py selftest
  python3 scripts/claude_dir_t12_marks.py report {t2|t1|both} [--root DIR]     (reads sleeps/*.json of each test folder)
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T2_DIR = "artifacts/claude-dir-t2-selfpick-20260928"
T1_DIR = "artifacts/claude-dir-t1-fresh-20260928"
KINDS = ("sums4", "grids5")
SEEDS, BRANCHES, DRAWS = (0, 1), (64, 16384), (0, 1, 2)
# sealed numbers (reasons in PASSMARKS.md section "Where each number comes from")
T2_BAR = {"sums4": 12, "grids5": 16}          # 3 x the largest R16 draw SD in the distill raw files (3.8, 5.3), rounded up
T1_BAR = {"sums4": 21, "grids5": 29}          # 3 x the largest R16 / D16 draw SD in the distill raw files (7.0, 9.5), rounded up
T1_SIZE = 50                                  # of 200, mean over the 4 cells: above every R16 / D16 cell mean measured (max 26.3)
MARGIN_FLOOR = 6                              # margin = max(6, 2 x SE) (Ben's rule)
CHOICE_NOISE_MULT = 2                         # T2: the gain must also be >= 2 x the mean |R16b - R16| (which-16 spread)
WRONG_BELOW = 5                               # proved wrong: seed mean gain < +5 of 200 on both kinds on both seeds
FRESH_SLACK = 20                              # fresh old panel >= fixed panel - 20 (not memorising the store)
PLAIN_SLEEP64_9X9 = {0: 14, 1: 9}             # committed plain practised net, sleep at k=64 (eq-runs/plain-s*-pre/adapt.json)
PLAIN_PLUS = 30                               # row a plain net cannot pass: loop 9x9 at k=64 >= plain + 30


def load(root, folder, arm):
    """{(seed, k): [record per draw 0..2]} for one arm; missing draws are simply absent."""
    out = {}
    for f in sorted((Path(root) / folder / "sleeps").glob(f"s*-k*-{arm}-d*.json")):
        r = json.loads(f.read_text())
        out.setdefault((r["seed"], r["k"]), {})[r["draw"]] = r
    return {c: [d[i] for i in DRAWS if i in d] for c, d in out.items()}


def series(recs, kind):
    if kind == "maze9":
        return [r["maze9"] for r in recs]
    if kind.startswith("fresh_"):
        return [r["fresh_old"][kind[6:]] for r in recs]
    return [r["old"][kind] for r in recs]


def mean(x):
    return sum(x) / len(x)


def var(x):
    return st.variance(x) if len(x) > 1 else 0.0


def margin(*groups):
    """max(6, 2 x SE) with SE = sqrt(sum of draw variances / 3) for a difference of two 3-draw means."""
    se = math.sqrt(sum(var(g) for g in groups) / 3)
    return max(MARGIN_FLOOR, 2 * se)


def complete(arms, cells):
    return all(len(arms[a].get(c, [])) == 3 for a in arms for c in cells)


def cells_all():
    return [(s, k) for s in SEEDS for k in BRANCHES]


def gain_rows(test, cmp_arms, kind, cells):
    """per cell: gain of `test` over the highest-mean comparator, and the margin for that pair"""
    rows = {}
    for c in cells:
        t = series(test[c], kind)
        best = max(cmp_arms, key=lambda a: mean(series(a[c], kind)))
        b = series(best[c], kind)
        rows[c] = {"gain": mean(t) - mean(b), "margin": margin(t, b), "test": mean(t), "cmp": mean(b)}
    return rows


def maze_rows(test, ref, cells):
    """F_few stand-in: k = 64 cells, loop 9x9 >= reference - margin AND >= plain sleep64 + 30 (plain cannot pass);
    F_eq stand-in: k = 16384 cells, loop 9x9 >= reference - margin."""
    out = {}
    for c in cells:
        t, r = series(test[c], "maze9"), series(ref[c], "maze9")
        ok = mean(t) >= mean(r) - margin(t, r)
        if c[1] == 64:
            ok = ok and mean(t) >= PLAIN_SLEEP64_9X9[c[0]] + PLAIN_PLUS
        out[c] = {"test": mean(t), "ref": mean(r), "margin": margin(t, r), "ok": ok}
    return out


def fresh_ok(test, cells):
    return all(mean(series(test[c], f"fresh_{k}")) >= mean(series(test[c], k)) - FRESH_SLACK for c in cells for k in KINDS)


def seed_mean_gain(rows, seed, kind):
    return mean([rows[kind][(seed, k)]["gain"] for k in BRANCHES])


def t2(root):
    arms = {a: load(root, T2_DIR, a) for a in ("R16", "R16b", "PICK", "HARD")}
    cells = cells_all()
    if not complete({a: arms[a] for a in ("R16", "R16b", "PICK")}, cells):
        return {"verdict": "VOID (an arm has fewer than 3 draws in a cell; no dead cell is replaced)"}
    rows = {k: gain_rows(arms["PICK"], [arms["R16"]], k, cells) for k in KINDS}
    noise = {k: mean([abs(mean(series(arms["R16b"][c], k)) - mean(series(arms["R16"][c], k))) for c in cells]) for k in KINDS}
    m1 = {}
    for k in KINDS:
        g = mean([rows[k][c]["gain"] for c in cells])
        m1[k] = {"mean_gain": g, "bar": T2_BAR[k], "choice_noise": noise[k],
                 "cells_above_margin": sum(rows[k][c]["gain"] > rows[k][c]["margin"] for c in cells),
                 "ok": g >= T2_BAR[k] and g >= CHOICE_NOISE_MULT * noise[k] and sum(rows[k][c]["gain"] > rows[k][c]["margin"] for c in cells) >= 3}
    mz = maze_rows(arms["PICK"], arms["R16"], cells)
    few = all(mz[c]["ok"] for c in cells if c[1] == 64)
    eq = all(mz[c]["ok"] for c in cells if c[1] == 16384)
    fr = fresh_ok(arms["PICK"], cells)
    wrong = all(seed_mean_gain(rows, s, k) < WRONG_BELOW for s in SEEDS for k in KINDS)
    passed = all(m1[k]["ok"] for k in KINDS) and fr and few and eq
    verdict = "PASS" if passed else ("PROVED WRONG" if wrong else "NOT SHOWN")
    ctrl = None
    if complete({"HARD": arms["HARD"]}, cells):
        crows = {k: gain_rows(arms["HARD"], [arms["R16"]], k, cells) for k in KINDS}
        ctrl = {k: {"HARD_mean_gain": mean([crows[k][c]["gain"] for c in cells]),
                    "PICK_mean_gain": m1[k]["mean_gain"]} for k in KINDS}
    return {"verdict": verdict, "M1": m1, "M2_fresh_ok": fr, "F_few_row_k64_ok": few, "F_eq_row_k16384_ok": eq,
            "maze_rows": {f"s{c[0]}-k{c[1]}": v for c, v in mz.items()}, "proved_wrong_rule": wrong,
            "control_HARD_vs_PICK": ctrl,
            "cells": {k: {f"s{c[0]}-k{c[1]}": v for c, v in rows[k].items()} for k in KINDS}}


def t1(root):
    arms = {a: load(root, T1_DIR, a) for a in ("FRESH", "D16", "K16")}
    arms["R16"] = load(root, T2_DIR, "R16")                # shared comparator, written by the T2 jobs
    cells = cells_all()
    if not complete(arms, cells):
        return {"verdict": "VOID (an arm has fewer than 3 draws in a cell; no dead cell is replaced)"}
    cmp_arms = [arms["R16"], arms["D16"], arms["K16"]]
    rows = {k: gain_rows(arms["FRESH"], cmp_arms, k, cells) for k in KINDS}
    signal, size = {}, {}
    for k in KINDS:
        g = mean([rows[k][c]["gain"] for c in cells])
        signal[k] = {"mean_gain": g, "bar": T1_BAR[k], "cells_above_margin": sum(rows[k][c]["gain"] > rows[k][c]["margin"] for c in cells)}
        signal[k]["ok"] = g >= T1_BAR[k] and signal[k]["cells_above_margin"] >= 3
        level = mean([rows[k][c]["test"] for c in cells])
        size[k] = {"mean_score": level, "bar": T1_SIZE, "ok": level >= T1_SIZE}
    mz = maze_rows(arms["FRESH"], arms["R16"], cells)
    few = all(mz[c]["ok"] for c in cells if c[1] == 64)
    eq = all(mz[c]["ok"] for c in cells if c[1] == 16384)
    fr = fresh_ok(arms["FRESH"], cells)
    sig = all(signal[k]["ok"] for k in KINDS)
    siz = all(size[k]["ok"] for k in KINDS)
    wrong = all(seed_mean_gain(rows, s, k) < WRONG_BELOW for s in SEEDS for k in KINDS)
    if sig and siz and fr and few and eq:
        verdict = "PASS"
    elif wrong:
        verdict = "PROVED WRONG"
    elif sig:
        verdict = "PARTIAL (a gain above the noise bar; " + ", ".join(
            n for n, ok in (("size row", siz), ("fresh-panel row", fr), ("F_few row", few), ("F_eq row", eq)) if not ok) + " missed)"
    else:
        verdict = "NOT SHOWN"
    single = {k: mean([mean(series(arms["FRESH"][c], k)) - mean(series(arms["K16"][c], k)) for c in cells]) for k in KINDS}
    return {"verdict": verdict, "SIGNAL": signal, "SIZE": size, "M2_fresh_ok": fr, "F_few_row_k64_ok": few, "F_eq_row_k16384_ok": eq,
            "maze_rows": {f"s{c[0]}-k{c[1]}": v for c, v in mz.items()}, "proved_wrong_rule": wrong,
            "report_only_FRESH_minus_K16_mean": single,
            "cells": {k: {f"s{c[0]}-k{c[1]}": v for c, v in rows[k].items()} for k in KINDS}}


# ------------------------------------------------------------------ selftest with synthetic records
def _write(root, folder, arm, values, fresh=None, maze=None):
    """values: {(seed,k): (sums draws, grids draws)}; fresh defaults to the same numbers; maze defaults to 200."""
    d = Path(root) / folder / "sleeps"
    d.mkdir(parents=True, exist_ok=True)
    for (s, k), (a, b) in values.items():
        for i in DRAWS:
            fs = (fresh or {}).get((s, k), (a, b))
            mz = (maze or {}).get((s, k), (200, 200, 200))
            (d / f"s{s}-k{k}-{arm}-d{i}.json").write_text(json.dumps(
                {"seed": s, "k": k, "arm": arm, "draw": i, "old": {"sums4": a[i], "grids5": b[i]},
                 "fresh_old": {"sums4": fs[0][i], "grids5": fs[1][i]}, "maze9": mz[i]}))


def selftest():
    cells = cells_all()

    def flat(v, w=None):
        return {c: ((v, v, v) if not w else (v, v, v), (v, v, v) if not w else (w, w, w)) for c in cells}

    def run(f, t2s=None, t1s=None):
        with tempfile.TemporaryDirectory() as tmp:
            for folder, arm, vals, kw in (t2s or []) + (t1s or []):
                _write(tmp, folder, arm, vals, **kw)
            return f(tmp)

    base = [(T2_DIR, "R16", flat(8, 8), {}), (T2_DIR, "R16b", flat(9, 9), {})]
    maze_ok = {c: (150, 150, 150) for c in cells}
    # T2 pass: PICK beats R16 by 30 / 30 in every cell, fresh close to fixed, maze kept
    r = run(t2, base + [(T2_DIR, "PICK", flat(38, 38), {"maze": maze_ok})], None)
    assert r["verdict"] == "NOT SHOWN" or r["verdict"] == "PASS"   # maze 150 vs R16 maze 200: F rows fail -> not pass
    assert r["verdict"] == "NOT SHOWN", r["verdict"]
    r = run(t2, [(T2_DIR, "R16", flat(8, 8), {"maze": maze_ok}), (T2_DIR, "R16b", flat(9, 9), {"maze": maze_ok}),
                 (T2_DIR, "PICK", flat(38, 38), {"maze": maze_ok})])
    assert r["verdict"] == "PASS", r
    # T2 proved wrong: PICK at or below R16 everywhere
    r = run(t2, base + [(T2_DIR, "PICK", flat(6, 6), {})])
    assert r["verdict"] == "PROVED WRONG", r["verdict"]
    # T2 gain in one cell only is not a pass and not proved wrong (seed means: 30/2 >= 5 on seed 0, but seed 1 below)
    v = flat(8, 8)
    vals = dict(v)
    vals[(0, 64)] = ((60, 60, 60), (60, 60, 60))
    vals[(0, 16384)] = ((60, 60, 60), (60, 60, 60))
    r = run(t2, base + [(T2_DIR, "PICK", vals, {})])
    assert r["verdict"] == "NOT SHOWN", r["verdict"]
    # which-16 noise above the gain blocks a pass (R16b is 25 away from R16)
    r = run(t2, [(T2_DIR, "R16", flat(8, 8), {"maze": maze_ok}), (T2_DIR, "R16b", flat(33, 33), {"maze": maze_ok}),
                 (T2_DIR, "PICK", flat(38, 38), {"maze": maze_ok})])
    assert r["verdict"] == "NOT SHOWN", r["verdict"]
    # VOID: a draw missing
    with tempfile.TemporaryDirectory() as tmp:
        _write(tmp, T2_DIR, "R16", flat(8, 8))
        _write(tmp, T2_DIR, "R16b", flat(9, 9))
        _write(tmp, T2_DIR, "PICK", flat(38, 38))
        next((Path(tmp) / T2_DIR / "sleeps").glob("s0-k64-PICK-d2.json")).unlink()
        assert t2(tmp)["verdict"].startswith("VOID")
    # T1: PASS needs signal + size + gates; a gain of 30 with a level of 38 is PARTIAL
    mk = {"maze": maze_ok}
    t1base = [(T2_DIR, "R16", flat(8, 8), mk), (T1_DIR, "D16", flat(12, 12), mk), (T1_DIR, "K16", flat(10, 10), mk)]
    r = run(t1, None, t1base + [(T1_DIR, "FRESH", flat(60, 60), mk)])
    assert r["verdict"] == "PASS", r
    r = run(t1, None, t1base + [(T1_DIR, "FRESH", flat(45, 45), mk)])
    assert r["verdict"].startswith("PARTIAL"), r["verdict"]
    r = run(t1, None, t1base + [(T1_DIR, "FRESH", flat(13, 13), mk)])   # gain over D16 (12) is +1: below 5 on both seeds
    assert r["verdict"] == "PROVED WRONG", r["verdict"]
    r = run(t1, None, t1base + [(T1_DIR, "FRESH", flat(22, 22), mk)])   # +10: neither signal nor wrong
    assert r["verdict"] == "NOT SHOWN", r["verdict"]
    # fair comparator: FRESH must beat the highest arm, not just R16 (K16 at 70 makes FRESH 60 a non-gain)
    t1hi = [(T2_DIR, "R16", flat(8, 8), mk), (T1_DIR, "D16", flat(12, 12), mk), (T1_DIR, "K16", flat(70, 70), mk)]
    r = run(t1, None, t1hi + [(T1_DIR, "FRESH", flat(60, 60), mk)])
    assert r["verdict"] == "PROVED WRONG", r["verdict"]
    # memorising guard: fresh-panel score far below the fixed panel blocks PASS
    fr = {c: ((5, 5, 5), (5, 5, 5)) for c in cells}
    r = run(t1, None, t1base + [(T1_DIR, "FRESH", flat(60, 60), {"maze": maze_ok, "fresh": fr})])
    assert r["verdict"].startswith("PARTIAL") and "fresh-panel" in r["verdict"], r["verdict"]
    # plain-net row: a k=64 9x9 of 20 (plain gets 14 and 9; needs plain + 30) fails the F_few row
    lowmaze = {c: ((20, 20, 20) if c[1] == 64 else (150, 150, 150)) for c in cells}
    t1lm = [(T2_DIR, "R16", flat(8, 8), {"maze": lowmaze}), (T1_DIR, "D16", flat(12, 12), mk), (T1_DIR, "K16", flat(10, 10), mk)]
    r = run(t1, None, t1lm + [(T1_DIR, "FRESH", flat(60, 60), {"maze": lowmaze})])
    assert r["F_few_row_k64_ok"] is False, r
    print("t12 marks selftest ok: 12 cases")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        selftest()
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        root = ROOT
        if "--root" in sys.argv:
            root = Path(sys.argv[sys.argv.index("--root") + 1])
        which = sys.argv[2]
        out = {}
        if which in ("t2", "both"):
            out["t2"] = t2(root)
        if which in ("t1", "both"):
            out["t1"] = t1(root)
        print(json.dumps(out, indent=1, default=str))
        return
    print(__doc__)


if __name__ == "__main__":
    main()
