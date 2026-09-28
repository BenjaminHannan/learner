#!/usr/bin/env python3
"""Marks for the keep-old-skills leads (Lead 0, blend, Lead 2). Pure python, no torch.

Implements artifacts/claude-dir-ks-20260928/PASSMARKS.md exactly. Reads the JSON records the
runner (claude_dir_ks_run.py) writes and prints / saves the verdicts. `selftest` checks the
logic on made-up records (both a passing and a failing pattern for every verdict).
Usage: python3 claude_dir_ks_marks.py report   |   python3 claude_dir_ks_marks.py selftest
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts" / "claude-dir-ks-20260928"
RULER = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
SEEDS, BRANCHES = (0, 1), (64, 16384)
CELLS = [(s, k) for s in SEEDS for k in BRANCHES]
KINDS = ("sums4", "grids5")
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FEW = (1, 4, 16, 64)
MAZE_BAR = 17            # 2 x binomial SE of 300 dev 9x9 items at p = 0.5 (8.7), rounded up
OLD_BAR = 20             # the distill test's bar, of 200
OLD_HALF = 100           # half of the pre-maze level (>= 190 of 200 by V1)
FRESH_SLACK = 20         # fresh old panel may be at most 20 below the fixed panel
ALPHAS = [round(i / 10, 1) for i in range(11)]


def margin(se):
    return max(6.0, 2.0 * se)


def maze_room(a_maze, p_maze):
    """How far below the adapted net's 9x9 count a treated net may sit (of 300)."""
    return max(0.10 * (a_maze - p_maze), MAZE_BAR)


# ---------------------------------------------------------------- Lead 0
def lead0(rec):
    """rec[(s,k)] = {"P","A","revert":{g:cell},"only":{g:cell}}; cell = {"sums4","grids5","maze9"}."""
    main_groups = ("E", "B0", "B1", "RD", "ST")
    out = {"cells": {}}
    for c in CELLS:
        r = rec[c]
        a = r["A"]
        room = maze_room(a["maze9"], r["P"]["maze9"])
        row = {}
        for g, cell in r["revert"].items():
            rs, rg = cell["sums4"] - a["sums4"], cell["grids5"] - a["grids5"]
            loss = a["maze9"] - cell["maze9"]
            row[g] = {"rec_sums4": rs, "rec_grids5": rg, "maze9_loss": loss,
                      "localised": rs >= OLD_BAR and rg >= OLD_BAR and loss <= room}
        out["cells"][f"s{c[0]}-k{c[1]}"] = {"room": room, "groups": row}
    winners = {g: [c for c in CELLS if out["cells"][f"s{c[0]}-k{c[1]}"]["groups"][g]["localised"]]
               for g in main_groups}
    best = max(winners, key=lambda g: len(winners[g]))
    entangled = all(
        not any(v["rec_sums4"] >= OLD_BAR and v["rec_grids5"] >= OLD_BAR
                and v["maze9_loss"] <= out["cells"][f"s{c[0]}-k{c[1]}"]["room"]
                for v in out["cells"][f"s{c[0]}-k{c[1]}"]["groups"].values()) for c in CELLS)
    out["winners"] = {g: len(v) for g, v in winners.items()}
    if len(winners[best]) >= 3:
        out["verdict"] = f"LOCALISED (group {best} in {len(winners[best])} of 4 cells)"
    elif entangled:
        out["verdict"] = "ENTANGLED (no group separates old-kind recovery from maze skill in any of 4 cells)"
    else:
        out["verdict"] = "MIXED, not shown either way"
    return out


# ---------------------------------------------------------------- blend
def blend(rec, sleeps, frows, plain):
    """rec[(s,k)] = blend record; sleeps = {(s,k,arm): [per-draw dict]} for R16 and R128;
    frows[s] = {k: {"blend9","unblended9"}} or None; plain[s] = {"few","eq"} committed dev fractions."""
    out = {"cells": {}}
    kept = []
    beat = []
    grid_any = []
    for c in CELLS:
        r = rec[c]
        p, a = r["P_full"], r["A_full"]
        room = maze_room(a["maze9"], p["maze9"])
        x = r["at_astar"]
        g_old = x["sums4"] >= OLD_HALF and x["grids5"] >= OLD_HALF
        g_maze = x["maze9"] >= a["maze9"] - room
        g_fresh = x["fresh_sums4"] >= x["sums4"] - FRESH_SLACK and x["fresh_grids5"] >= x["grids5"] - FRESH_SLACK
        kept.append(g_old and g_maze and g_fresh)
        r16 = sleeps[(c[0], c[1], "R16")]
        cmp_ok = True
        cmpd = {}
        for kd in KINDS:
            v = [d["old"][kd] for d in r16]
            se = st.stdev(v) / math.sqrt(len(v))
            bar = max(st.mean(v), a[kd]) + margin(se)
            cmpd[kd] = {"comparator": bar, "blend": x[kd]}
            cmp_ok &= x[kd] >= bar
        beat.append(cmp_ok)
        grid_any.append(any(cell["sums4"] >= OLD_HALF and cell["grids5"] >= OLD_HALF
                            and cell["maze9"] >= a["maze9"] - room for cell in r["grid"].values()))
        out["cells"][f"s{c[0]}-k{c[1]}"] = {"a_star": r["a_star"], "gates": {"old": g_old, "maze": g_maze, "fresh": g_fresh},
                                             "vs_R16": cmpd, "beats_R16": cmp_ok, "any_alpha_keeps": grid_any[-1]}
    f_ok, f_note = [], {}
    for s in SEEDS:
        fr = frows.get(s) if frows else None
        if not fr or any(fr.get(k) is None for k in RUNGS):
            f_ok.append(False)
            f_note[f"s{s}"] = "F rows not measured"
            continue
        few_b = st.mean(fr[k]["blend9"] for k in FEW) / 300
        few_u = st.mean(fr[k]["unblended9"] for k in FEW) / 300
        eq_b = st.mean(fr[k]["blend9"] for k in RUNGS) / 300
        eq_u = st.mean(fr[k]["unblended9"] for k in RUNGS) / 300
        ok = few_b >= max(0.9 * few_u, 0.08) and eq_b >= max(0.9 * eq_u, 0.40)
        f_ok.append(ok)
        f_note[f"s{s}"] = {"F_few_blend": few_b, "F_few_unblended": few_u, "F_eq_blend": eq_b,
                           "F_eq_unblended": eq_u, "plain_F_few": plain[s]["few"], "plain_F_eq": plain[s]["eq"], "ok": ok}
    out["F_rows"] = f_note
    core = sum(kept) >= 3
    comp = sum(beat) >= 3
    out["kept_cells"], out["beat_R16_cells"] = sum(kept), sum(beat)
    if core and comp and all(f_ok):
        out["verdict"] = "PASS"
    elif not any(grid_any):
        out["verdict"] = "PROVED WRONG (no alpha keeps old kinds and the maze gain in any of 4 cells)"
    else:
        why = [n for n, ok in (("gates in >=3 of 4 cells", core), ("beats R16 in >=3 of 4 cells", comp),
                               ("F_few and F_eq rows on both seeds", all(f_ok))) if not ok]
        out["verdict"] = "NOT SHOWN (missed: " + ", ".join(why) + ")"
    return out


# ---------------------------------------------------------------- Lead 2
def lead2(sleeps, plain_sleep64):
    """sleeps[(s,k,arm)] = list of 3 draw records; arms WF16 and R16 required."""
    out = {"cells": {}}
    d_by_kind = {kd: [] for kd in KINDS}
    n_above = {kd: 0 for kd in KINDS}
    maze_ok, fresh_ok = 0, []
    for c in CELLS:
        w, u = sleeps[(c[0], c[1], "WF16")], sleeps[(c[0], c[1], "R16")]
        cell = {}
        for kd in KINDS:
            wv, uv = [d["old"][kd] for d in w], [d["old"][kd] for d in u]
            d = st.mean(wv) - st.mean(uv)
            se = math.sqrt((st.variance(wv) + st.variance(uv)) / len(wv))
            d_by_kind[kd].append(d)
            n_above[kd] += d > margin(se)
            cell[kd] = {"d": d, "margin": margin(se), "above": d > margin(se),
                        "fresh_wf": st.mean(x["fresh_old"][kd] for x in w), "fixed_wf": st.mean(wv)}
            fresh_ok.append(cell[kd]["fresh_wf"] >= cell[kd]["fixed_wf"] - FRESH_SLACK)
        wm, um = [d["maze9"] for d in w], [d["maze9"] for d in u]
        se_m = math.sqrt((st.variance(wm) + st.variance(um)) / len(wm))
        cell["maze9"] = {"wf": st.mean(wm), "r16": st.mean(um), "ok": st.mean(wm) >= st.mean(um) - margin(se_m)}
        maze_ok += cell["maze9"]["ok"]
        out["cells"][f"s{c[0]}-k{c[1]}"] = cell
    mean_d = {kd: st.mean(v) for kd, v in d_by_kind.items()}
    plain_row = all(st.mean(d["maze9"] for d in sleeps[(s, 64, "WF16")]) >= plain_sleep64[s] + 30 for s in SEEDS)
    seed_mean = {s: {kd: st.mean(d_by_kind[kd][i] for i, c in enumerate(CELLS) if c[0] == s) for kd in KINDS} for s in SEEDS}
    out.update(mean_d=mean_d, cells_above=n_above, maze_ok_cells=maze_ok, plain_row=plain_row,
               fresh_ok=all(fresh_ok), seed_mean=seed_mean)
    if (all(mean_d[kd] >= OLD_BAR and n_above[kd] >= 3 for kd in KINDS) and maze_ok >= 3
            and plain_row and all(fresh_ok)):
        out["verdict"] = "PASS"
    elif all(seed_mean[s][kd] < 5 for s in SEEDS for kd in KINDS):
        out["verdict"] = "PROVED WRONG (weakest-first below +5 of 200 on both kinds in both seeds)"
    else:
        out["verdict"] = "NOT SHOWN"
    return out


# ---------------------------------------------------------------- IO
def _j(p):
    return json.loads(Path(p).read_text())


def load_all():
    lead0_rec = {(s, k): _j(A / "lead0" / f"s{s}-k{k}.json") for s, k in CELLS if (A / "lead0" / f"s{s}-k{k}.json").exists()}
    blend_rec = {(s, k): _j(A / "blend" / f"s{s}-k{k}.json") for s, k in CELLS if (A / "blend" / f"s{s}-k{k}.json").exists()}
    sleeps = {}
    for s, k in CELLS:
        for arm in ("R16", "R128", "WF16"):
            recs = [_j(A / "sleeps" / f"s{s}-k{k}-{arm}-d{d}.json") for d in range(3)
                    if (A / "sleeps" / f"s{s}-k{k}-{arm}-d{d}.json").exists()]
            if len(recs) == 3:
                sleeps[(s, k, arm)] = recs
    frows = {s: _j(A / "frows" / f"s{s}.json")["rungs"] for s in SEEDS if (A / "frows" / f"s{s}.json").exists()}
    frows = {s: {int(k): v for k, v in r.items()} for s, r in frows.items()}
    plain, plain_sleep64 = {}, {}
    for s in SEEDS:
        r = _j(RULER / f"plain-s{s}-pre" / "adapt.json")
        plain[s] = {"few": st.mean(r["rungs"][str(k)]["9"]["right"] for k in FEW) / 300,
                    "eq": st.mean(r["rungs"][str(k)]["9"]["right"] for k in RUNGS) / 300}
        plain_sleep64[s] = r["sleep"]["64"]["maze_dev"]["9"]["right"]
    return lead0_rec, blend_rec, sleeps, frows, plain, plain_sleep64


def report():
    l0, bl, sl, fr, plain, ps64 = load_all()
    res = {}
    if len(l0) == 4:
        res["lead0"] = lead0(l0)
    if len(bl) == 4 and all((s, k, "R16") in sl for s, k in CELLS):
        res["blend"] = blend(bl, sl, fr, plain)
    if all((s, k, a) in sl for s, k in CELLS for a in ("R16", "WF16")):
        res["lead2"] = lead2(sl, ps64)
    (A / "verdicts.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for name, v in res.items():
        print(name, "->", v["verdict"])
    return res


# ---------------------------------------------------------------- selftest
def _cell(s, g, m):
    return {"sums4": s, "grids5": g, "maze9": m}


def selftest():
    # Lead 0: pass pattern (group B1 separates) and fail pattern (nothing recovers).
    def l0_rec(sep):
        rec = {}
        for c in CELLS:
            rev = {g: _cell(0, 0, 0) for g in ("E", "B0", "B1", "RD", "ST", "ATT", "MLP")}
            if sep:
                rev["B1"] = _cell(60, 50, 250)
            rec[c] = {"P": _cell(200, 199, 0), "A": _cell(0, 0, 270), "revert": rev, "only": {}}
        return rec
    assert lead0(l0_rec(True))["verdict"].startswith("LOCALISED")
    assert lead0(l0_rec(False))["verdict"].startswith("ENTANGLED")
    mixed = l0_rec(True)
    for c in CELLS[:2]:
        mixed[c]["revert"]["B1"] = _cell(0, 0, 0)
    assert lead0(mixed)["verdict"].startswith("MIXED")

    # blend
    def sleeps_of(old_s, old_g, maze, arm, spread=2):
        return [{"old": {"sums4": old_s + i * spread, "grids5": old_g + i * spread},
                 "fresh_old": {"sums4": old_s, "grids5": old_g}, "maze9": maze + i * spread} for i in range(3)]
    def b_rec(good):
        r = {}
        for c in CELLS:
            at = {"sums4": 140, "grids5": 130, "maze9": 250, "fresh_sums4": 138, "fresh_grids5": 128} if good else \
                 {"sums4": 5, "grids5": 5, "maze9": 270, "fresh_sums4": 5, "fresh_grids5": 5}
            grid = {"0.5": {"sums4": 140, "grids5": 130, "maze9": 250}} if good else {"0.5": _cell(5, 5, 270)}
            r[c] = {"P_full": _cell(200, 199, 0), "A_full": _cell(0, 0, 270), "a_star": 0.5, "at_astar": at, "grid": grid}
        return r
    sl = {(s, k, "R16"): sleeps_of(10, 12, 200, "R16") for s, k in CELLS}
    fr_good = {s: {k: {"blend9": 150, "unblended9": 150} for k in RUNGS} for s in SEEDS}
    fr_bad = {s: {k: {"blend9": 20, "unblended9": 150} for k in RUNGS} for s in SEEDS}
    plain = {s: {"few": 0.03, "eq": 0.34} for s in SEEDS}
    assert blend(b_rec(True), sl, fr_good, plain)["verdict"] == "PASS"
    assert blend(b_rec(True), sl, fr_bad, plain)["verdict"].startswith("NOT SHOWN")
    assert blend(b_rec(True), sl, None, plain)["verdict"].startswith("NOT SHOWN")
    assert blend(b_rec(False), sl, fr_good, plain)["verdict"].startswith("PROVED WRONG")
    # a* misses but another alpha would have kept: not proved wrong
    miss = b_rec(False)
    for c in CELLS:
        miss[c]["grid"] = {"0.5": {"sums4": 140, "grids5": 130, "maze9": 250}}
    assert blend(miss, sl, fr_good, plain)["verdict"].startswith("NOT SHOWN")

    # lead 2
    def s2(gain, maze_wf=200):
        d = {}
        for c in CELLS:
            d[(c[0], c[1], "R16")] = sleeps_of(10, 12, 200, "R16")
            d[(c[0], c[1], "WF16")] = sleeps_of(10 + gain, 12 + gain, maze_wf, "WF16")
        return d
    ps = {0: 23, 1: 14}
    assert lead2(s2(40), ps)["verdict"] == "PASS"
    assert lead2(s2(1), ps)["verdict"].startswith("PROVED WRONG")
    assert lead2(s2(12), ps)["verdict"] == "NOT SHOWN"
    assert lead2(s2(40, maze_wf=100), ps)["verdict"] == "NOT SHOWN"
    print(json.dumps({"selftest": "ok"}))


if __name__ == "__main__":
    {"report": report, "selftest": selftest}[sys.argv[1]]()
