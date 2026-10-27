#!/usr/bin/env python3
"""H12 marks: reads the baseline and the H12 dev records and applies PASSMARKS.md.

    python -B scripts/claude_dir_h12_marks.py selftest
    python -B scripts/claude_dir_h12_marks.py judge [--out FILE]

No torch: it only reads `adapt.json` files (dev 9x9 counts). The page
artifacts/claude-dir-h12-stop-20260928/PASSMARKS.md wins if this script and the page ever disagree.
The holdout is never read here.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PAT = "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre/adapt.json"
H12_PAT = "artifacts/claude-dir-h12-stop-20260928/eq-runs/h12-pre-s{seed}/adapt.json"

RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FEW = (1, 4, 16, 64)
JUDGED = (64, 256, 1024, 4096, 16384)
N, CAP = 300, 48
FLOOR, SLACK, STOP_TOL, NEED_S1 = 31, 30, 6, 4      # PASSMARKS.md: S1 (a), (b); S2; rungs needed
BAR = {"F_eq": 7.0, "F_few": 8.5}                   # PASSMARKS.md, fixed before any H12 score
WEIGHTS = 1645726
EPS = 1e-9


def load(pattern, seed):
    return json.loads((ROOT / pattern.format(seed=seed)).read_text())


def p9(run, k):
    return run["rungs"][str(k)]["9"]


# ---- S1 / S2 -------------------------------------------------------------------------

def s1_rung(p, depth):
    """PASSMARKS S1 (a), (b), (c) on one judged rung of one run; returns (passes, detail)."""
    right, cap, mean = p["right"], p["cap_hits"], p["mean_rounds"]
    a = right >= FLOOR
    b = cap <= (N - right) + SLACK
    line = depth + (CAP - depth) * (N - right) / N
    c = mean <= line + EPS
    return a and b and c, {"a_right_ge_31": a, "b_cap_le": (N - right) + SLACK, "b_ok": b,
                           "c_rounds_le": round(line, 3), "c_ok": c,
                           "right": right, "cap_hits": cap, "mean_rounds": round(mean, 3)}


def s2_rung(p):
    return p["right"] >= p["fixed_right"] - STOP_TOL


def stop_marks(run):
    depth = run["fixed_depth"]
    rungs, n1, s2_ok = {}, 0, True
    for k in JUDGED:
        p = p9(run, k)
        ok1, detail = s1_rung(p, depth)
        ok2 = s2_rung(p)
        n1 += ok1
        s2_ok &= ok2
        rungs[str(k)] = dict(detail, S1=ok1, S2=ok2, fixed_right=p["fixed_right"])
    return {"rungs": rungs, "s1_rungs_passing": n1, "S1": n1 >= NEED_S1,
            "s2_rungs_passing": sum(r["S2"] for r in rungs.values()), "S2": s2_ok}


# ---- F_eq / F_few ---------------------------------------------------------------------

def f_score(run, key, rungs):
    return 100 * sum(p9(run, k)[key] for k in rungs) / (N * len(rungs))


def f_all(run):
    return {"F_eq": {"learned": f_score(run, "right", RUNGS), "fixed": f_score(run, "fixed_right", RUNGS)},
            "F_few": {"learned": f_score(run, "right", FEW), "fixed": f_score(run, "fixed_right", FEW)}}


def acc_word(deltas, bar):
    if all(d >= bar - EPS for d in deltas):
        return "HELPS"
    if all(d <= -bar + EPS for d in deltas):
        return "HURTS"
    return "NOT SEPARABLE FROM NOISE"


def accuracy(base, h12):
    """base, h12: {seed: run}. Deltas in points, control = higher of the baseline's two reads."""
    out = {}
    for name in ("F_eq", "F_few"):
        learned, body = [], []
        for s in (0, 1):
            fb, fh = f_all(base[s])[name], f_all(h12[s])[name]
            control = max(fb["learned"], fb["fixed"])
            learned.append(fh["learned"] - control)
            body.append(fh["fixed"] - fb["fixed"])
        out[name] = {"bar": BAR[name],
                     "delta_learned_by_seed": [round(x, 3) for x in learned],
                     "word": acc_word(learned, BAR[name]),
                     "body_delta_fixed16_by_seed": [round(x, 3) for x in body],
                     "body_word": acc_word(body, BAR[name])}
    return out


def verdict(s1, s2):
    """s1, s2: {seed: bool}. PASSMARKS 'Verdict words'."""
    if all(s1.values()) and all(s2.values()):
        return "STOP LEARNED"
    if all(s1.values()):
        return "FIRES BUT HURTS"
    if not any(s1.values()):
        return "WRONG"
    return "NOT SHOWN"


# ---- validity -------------------------------------------------------------------------

def validity(base, h12):
    """PASSMARKS V4 and V5, per seed. Returns (ok, list of failures)."""
    bad = []
    for s in (0, 1):
        b, h = base[s], h12[s]
        if (h.get("arm"), h.get("init"), h.get("seed")) != ("loop", "pre", s):
            bad.append(f"seed {s}: identity {h.get('arm')}/{h.get('init')}/{h.get('seed')}")
        if h.get("optimizer_updates_per_rung") != 2048:
            bad.append(f"seed {s}: optimizer_updates_per_rung {h.get('optimizer_updates_per_rung')}")
        for key in ("weights", "persistent_coefficients"):
            if h.get(key) != WEIGHTS:
                bad.append(f"seed {s}: {key} {h.get(key)}")
        for key in ("fixed_depth", "lr", "support_sha256"):
            if h.get(key) != b.get(key):
                bad.append(f"seed {s}: {key} differs from the baseline")
        cold_b, cold_h = b["rungs"]["0"]["9"], h["rungs"]["0"]["9"]
        for key in ("right", "fixed_right", "cap_hits"):
            if abs(cold_b[key] - cold_h[key]) > 1:
                bad.append(f"seed {s}: cold 9x9 {key} {cold_h[key]} vs baseline {cold_b[key]}")
        for kind in ("sums4", "grids5"):
            for key in ("right", "fixed_right"):
                if abs(b["old"]["before"][kind][key] - h["old"]["before"][kind][key]) > 1:
                    bad.append(f"seed {s}: old.before {kind} {key} differs by more than 1")
    return not bad, bad


# ---- noise behind the bars --------------------------------------------------------------

def noise(base):
    """Seed-to-seed dev spread of the baseline's learned-stop counts (PASSMARKS 'Bars')."""
    out = {}
    for name, ks in (("F_eq", RUNGS), ("F_few", FEW)):
        d = [p9(base[0], k)["right"] - p9(base[1], k)["right"] for k in ks]
        rms = math.sqrt(sum(x * x for x in d) / len(d))
        sd = rms / 3.0 / math.sqrt(len(ks))          # counts of 300 -> points, mean of len(ks) independent rungs
        var = 0.0
        for k in ks:
            pr = (p9(base[0], k)["right"] + p9(base[1], k)["right"]) / (2 * N)
            var += 100 ** 2 * 2 * pr * (1 - pr) / N
        out[name] = {"seed_diffs": d, "rms_counts": round(rms, 2), "sd_two_run_diff_points": round(sd, 2),
                     "binomial_only_points": round(math.sqrt(var) / len(ks), 2),
                     "twice_sd": round(2 * sd, 2), "bar_rounded_up_to_half": math.ceil(2 * sd / 0.5 - EPS) * 0.5}
    return out


# ---- report-only ------------------------------------------------------------------------

def report_only(run):
    rows = {}
    for k in (0,) + RUNGS:
        r = run["rungs"][str(k)]
        rows[str(k)] = {size: {key: (round(v[key], 2) if key == "mean_rounds" else v[key])
                               for key in ("right", "fixed_right", "mean_rounds", "cap_hits")}
                        for size, v in r.items()}
    e50 = next((k for k in RUNGS if p9(run, k)["right"] >= 150), None)
    sizes = {size: round(sum(run["rungs"][str(k)][size]["mean_rounds"] for k in JUDGED[1:]) / len(JUDGED[1:]), 2)
             for size in ("7", "9", "11")}
    old = {name: {kind: v["right"] for kind, v in run["old"][name].items()} for name in run["old"]}
    sleep = {k: {"old": {kind: v["right"] for kind, v in s["old"].items()},
                 "maze_dev_9": {key: (round(s["maze_dev"]["9"][key], 2) if key == "mean_rounds" else s["maze_dev"]["9"][key])
                                for key in ("right", "fixed_right", "mean_rounds", "cap_hits")}}
             for k, s in run["sleep"].items()}
    return {"rungs_all_sizes": rows, "E50": e50, "mean_rounds_by_size_k_ge_256": sizes,
            "old_kind_right_of_200": old, "sleep": sleep,
            "training_seconds": run.get("training_seconds"), "rung_seconds": run.get("rung_seconds")}


# ---- judge ------------------------------------------------------------------------------

def judge(base_pat, h12_pat, out=None):
    base = {s: load(base_pat, s) for s in (0, 1)}
    h12 = {s: load(h12_pat, s) for s in (0, 1)}
    ok, bad = validity(base, h12)
    result = {"validity": {"ok": ok, "failures": bad}, "baseline_reference": {}, "noise": noise(base)}
    for s in (0, 1):
        result["baseline_reference"][str(s)] = dict(stop_marks(base[s]), **{"F": f_all(base[s])})
    if not ok:
        result["verdict"] = "INVALID"
        result["note"] = "V4/V5 failed; nothing else is claimed"
    else:
        marks = {s: stop_marks(h12[s]) for s in (0, 1)}
        result["h12"] = {str(s): dict(marks[s], **{"F": f_all(h12[s])}) for s in (0, 1)}
        result["verdict"] = verdict({s: marks[s]["S1"] for s in (0, 1)}, {s: marks[s]["S2"] for s in (0, 1)})
        result["accuracy"] = accuracy(base, h12)
        result["report_only"] = {str(s): report_only(h12[s]) for s in (0, 1)}
    text = json.dumps(result, indent=2, sort_keys=True)
    if out:
        Path(out).write_text(text + "\n")
    print(text)
    return result


# ---- selftest ---------------------------------------------------------------------------

def _set(run, k, **kw):
    p = p9(run, k)
    p.update(kw)


def _good(run):
    """Turn a copy of a baseline run into a plainly working stop on every judged rung."""
    run = copy.deepcopy(run)
    for k in JUDGED:
        p = p9(run, k)
        right = max(p["right"], 200)
        p.update(right=right, fixed_right=right - 2, cap_hits=(N - right) + 5, mean_rounds=10.0)
    return run


def selftest():
    base = {s: load(BASE_PAT, s) for s in (0, 1)}
    # 1. the baseline reference numbers written in PASSMARKS.md
    got = {s: stop_marks(base[s]) for s in (0, 1)}
    assert (got[0]["s1_rungs_passing"], got[1]["s1_rungs_passing"]) == (0, 1), got
    assert [k for k, r in got[1]["rungs"].items() if r["S1"]] == ["1024"]
    assert (got[0]["s2_rungs_passing"], got[1]["s2_rungs_passing"]) == (5, 5)
    f = {s: f_all(base[s]) for s in (0, 1)}
    want = {0: (51.21, 49.83, 12.42, 11.83), 1: (51.67, 50.42, 14.75, 14.58)}
    for s in (0, 1):
        have = (f[s]["F_eq"]["learned"], f[s]["F_eq"]["fixed"], f[s]["F_few"]["learned"], f[s]["F_few"]["fixed"])
        assert all(abs(a - b) < 0.006 for a, b in zip(have, want[s])), (s, have)
    nz = noise(base)
    assert nz["F_eq"]["seed_diffs"] == [2, 0, 17, -47, -14, 42, -36, 25], nz
    assert nz["F_few"]["seed_diffs"] == [2, 0, 17, -47]
    assert abs(nz["F_eq"]["rms_counts"] - 28.2) < 0.06 and abs(nz["F_few"]["rms_counts"] - 25.0) < 0.06, nz   # PASSMARKS: 28.2, 25.0
    assert (nz["F_eq"]["sd_two_run_diff_points"], nz["F_few"]["sd_two_run_diff_points"]) == (3.33, 4.17), nz
    assert (nz["F_eq"]["binomial_only_points"], nz["F_few"]["binomial_only_points"]) == (0.84, 1.11), nz
    assert (nz["F_eq"]["bar_rounded_up_to_half"], nz["F_few"]["bar_rounded_up_to_half"]) == (BAR["F_eq"], BAR["F_few"]), nz
    # 2. S1 and S2 boundaries (depth 16)
    def one(right, cap, mean):
        return s1_rung({"right": right, "cap_hits": cap, "mean_rounds": mean}, 16)[0]
    assert one(31, 299 + 30 - 60, 47.9) is False            # cap bound fine, rounds bound not
    assert one(30, 0, 1.0) is False and one(31, 0, 1.0) is True            # floor of 31
    assert one(200, 130, 16 + 32 * 100 / 300) is True and one(200, 131, 10.0) is False   # cap <= (300-right)+30
    assert one(200, 100, 16 + 32 * 100 / 300 + 0.01) is False              # rounds bound
    assert s2_rung({"right": 94, "fixed_right": 100}) and not s2_rung({"right": 93, "fixed_right": 100})
    # 3. verdict words on synthetic variants
    ok, bad = validity(base, base)
    assert ok and not bad
    assert verdict({0: False, 1: False}, {0: True, 1: True}) == "WRONG"
    good = {s: _good(base[s]) for s in (0, 1)}
    m = {s: stop_marks(good[s]) for s in (0, 1)}
    assert all(m[s]["S1"] and m[s]["S2"] for s in (0, 1))
    assert verdict({s: m[s]["S1"] for s in m}, {s: m[s]["S2"] for s in m}) == "STOP LEARNED"
    hurt = copy.deepcopy(good)
    _set(hurt[1], 256, right=p9(hurt[1], 256)["fixed_right"] - 7)
    mh = {s: stop_marks(hurt[s]) for s in (0, 1)}
    assert mh[1]["S1"] and not mh[1]["S2"]
    assert verdict({s: mh[s]["S1"] for s in mh}, {s: mh[s]["S2"] for s in mh}) == "FIRES BUT HURTS"
    one_seed = {0: good[0], 1: base[1]}
    mo = {s: stop_marks(one_seed[s]) for s in (0, 1)}
    assert mo[0]["S1"] and not mo[1]["S1"]
    assert verdict({s: mo[s]["S1"] for s in mo}, {s: mo[s]["S2"] for s in mo}) == "NOT SHOWN"
    assert verdict({0: False, 1: False}, {0: False, 1: False}) == "WRONG"
    # 4. accuracy words: baseline vs itself is not separable; +bar in both seeds helps; one seed alone does not
    same = accuracy(base, base)
    assert same["F_eq"]["word"] == same["F_few"]["word"] == "NOT SEPARABLE FROM NOISE"
    assert acc_word([7.0, 7.0], 7.0) == "HELPS" and acc_word([7.0, 6.99], 7.0) == "NOT SEPARABLE FROM NOISE"
    assert acc_word([-7.0, -9.0], 7.0) == "HURTS" and acc_word([-7.0, 3.0], 7.0) == "NOT SEPARABLE FROM NOISE"
    up = copy.deepcopy(base)
    for s in (0, 1):
        for k in RUNGS:
            p = p9(up[s], k)
            p["right"] = min(N, p["right"] + 60)              # +20 points per rung, both seeds
    acc = accuracy(base, up)
    assert acc["F_eq"]["word"] == "HELPS" and acc["F_few"]["word"] == "HELPS", acc
    # control is the higher of the baseline's two reads: a baseline whose fixed read is higher raises the control
    swapped = copy.deepcopy(base)
    for s in (0, 1):
        for k in RUNGS:
            p = p9(swapped[s], k)
            p["fixed_right"], p["right"] = p["right"] + 30, p["right"]
    assert accuracy(swapped, base)["F_eq"]["delta_learned_by_seed"][0] < 0
    # 5. validity failures
    for mutate, text in ((lambda r: r.update(optimizer_updates_per_rung=2047), "updates"),
                         (lambda r: r.update(weights=WEIGHTS + 1), "weights"),
                         (lambda r: r.update(support_sha256="0" * 64), "support"),
                         (lambda r: r.update(fixed_depth=8), "depth"),
                         (lambda r: r["rungs"]["0"]["9"].update(cap_hits=290), "cold start"),
                         (lambda r: r["old"]["before"]["sums4"].update(right=150), "old kinds")):
        broken = copy.deepcopy(base)
        mutate(broken[0])
        ok, bad = validity(base, broken)
        assert not ok and bad, text
    print(json.dumps({"selftest": "ok", "baseline_S1_rungs": [got[0]["s1_rungs_passing"], got[1]["s1_rungs_passing"]],
                      "baseline_F_eq_dev": [round(f[s]["F_eq"]["learned"], 2) for s in (0, 1)],
                      "noise": {k: {x: v[x] for x in ("sd_two_run_diff_points", "bar_rounded_up_to_half")}
                                for k, v in nz.items()}}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "judge"))
    p.add_argument("--base", default=BASE_PAT)
    p.add_argument("--h12", default=H12_PAT)
    p.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        judge(a.base, a.h12, a.out)


if __name__ == "__main__":
    main()
