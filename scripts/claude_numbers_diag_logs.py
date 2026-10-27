#!/usr/bin/env python3
"""claude-numbers-diag (Helper T, 2026-09-28), part 2: what the saved runs say. Read-only, no torch.

  python -B scripts/claude_numbers_diag_logs.py [--out artifacts/claude-numbers-diag-20260928/logs.json]

Reads (never edits):
  artifacts/claude-rsn358u-20260927/runs/*/{train_log.jsonl,tests.json}   rsn-358u, 8 runs (4 loop, 4 plain)
  artifacts/claude-rsn358u2-20260928/runs/*/{train_log.jsonl,tests.json}  rsn-358u2, 4 loop re-runs
  artifacts/codex-numbers-20260927/diagnostics/fit-baseline-s9276193/probe_log.jsonl   (962 practice / 100 held-out probes)
  artifacts/codex-numbers-20260927/diagnostics/baseline-s9276191/numbers4.json         (the ONLY saved per-item outputs on the 300)
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import codex_numbers_20260927_labels as L  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "artifacts"


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def training_curves():
    out = {}
    for base in ("claude-rsn358u-20260927", "claude-rsn358u2-20260928"):
        for d in sorted((ROOT / base / "runs").iterdir()):
            log = jl(d / "train_log.jsonl")
            first = {}
            for r in log:
                for k in ("numbers3", "numbers4", "grids5", "sums4"):
                    v = r["exact_by_kind"].get(k)
                    if v is not None and v >= 0.99 and k not in first:
                        first[k] = r["step"]
            last = log[-1]["exact_by_kind"]
            tests = json.loads((d / "tests.json").read_text())["tests"]
            out[f"{base.split('-')[1]}/{d.name}"] = {
                "first_step_with_window_exact_ge_0.99": first,
                "final_window_train_exact": {k: last.get(k) for k in ("numbers3", "numbers4", "grids5", "sums4")},
                "test_of_300": {k: tests[k]["right"] for k in ("sums4", "grids5", "numbers4", "numbers5")}}
    return out


def loop_thinking():
    rows = collections.defaultdict(list)
    fixed = collections.defaultdict(lambda: collections.Counter())
    nets = 0
    for base in ("claude-rsn358u-20260927", "claude-rsn358u2-20260928"):
        for d in sorted((ROOT / base / "runs").iterdir()):
            if not d.name.startswith("loop"):
                continue
            nets += 1
            t = json.loads((d / "tests.json").read_text())["tests"]
            for k in ("sums4", "grids5", "numbers4", "numbers5"):
                rows[k].append({"mean_rounds": t[k]["mean_rounds"], "right": t[k]["right"], "any_round": t[k]["right_at_any_round"],
                                "max_stop": max(int(x) for x in t[k]["rounds_hist"])})
                if k == "numbers4":
                    for r, v in t[k]["fixed_rounds"].items():
                        fixed[k][int(r)] += v
    summary = {}
    for k, v in rows.items():
        summary[k] = {"nets": nets, "mean_rounds_range": [min(x["mean_rounds"] for x in v), max(x["mean_rounds"] for x in v)],
                      "latest_stop_seen": max(x["max_stop"] for x in v),
                      "right_at_own_stop_sum_over_nets": sum(x["right"] for x in v),
                      "right_at_any_of_48_rounds_sum_over_nets": sum(x["any_round"] for x in v),
                      "n_items_per_net": 300}
    summary["numbers4_right_at_fixed_rounds_sum_over_8_loop_nets"] = dict(sorted(fixed["numbers4"].items()))
    return summary


def fit_probe():
    rows = jl(ROOT / "codex-numbers-20260927/diagnostics/fit-baseline-s9276193/probe_log.jsonl")
    return [{"step": r["step"], "practice_numbers4_valid_of_962": r["scores"]["train_numbers4"]["valid"],
             "heldout_numbers4_valid_of_100": r["scores"]["dev_numbers4"]["valid"]} for r in rows]


def categorize(pred_row, nums, target, valid_set):
    """category, |value-target| (well-formed right-multiset only), min Hamming distance to any valid answer, numbers right"""
    k = len(nums)
    row = pred_row[:2 * k - 1]
    toks, ns = [], []
    for t in row:
        if E.VAL <= t < E.VAL + 100:
            toks.append(("n", t - E.VAL)); ns.append(t - E.VAL)
        elif t in E.OP_OF:
            toks.append(("o", E.OP_OF[t]))
        else:
            toks.append(("x", t))
    if any(kd == "x" for kd, _ in toks):
        return ("invalid_token", None, min(sum(a != b for a, b in zip(row, v)) for v in valid_set),
                sum((collections.Counter(ns) & collections.Counter(nums)).values()))
    depth, ok = 0, True
    for kind, _ in toks:
        depth += 1 if kind == "n" else -1
        if depth < 1:
            ok = False
    common = sum((collections.Counter(ns) & collections.Counter(nums)).values())
    ham = min(sum(a != b for a, b in zip(row, v)) for v in valid_set)
    if not ok or depth != 1:
        return "malformed_postfix", None, ham, common
    if sorted(ns) != sorted(nums):
        return "wrong_numbers", None, ham, common
    st = []
    for kind, v in toks:
        if kind == "n":
            st.append(Fraction(v)); continue
        y, x = st.pop(), st.pop()
        if v == "/" and y == 0:
            return "division_by_zero", None, ham, common
        st.append({"+": x + y, "-": x - y, "*": x * y, "/": (x / y if y else 0)}[v])
    d = abs(st[0] - target)
    return ("valid" if d == 0 else "wrong_value"), float(d), ham, common


def saved_outputs():
    d = json.loads((ROOT / "codex-numbers-20260927/diagnostics/baseline-s9276191/numbers4.json").read_text())
    panel = [json.loads(x) for x in Path(ROOT / "codex-numbers-20260927/panels/numbers4.jsonl").read_text().splitlines() if x]
    items = d["scores"]["items"]
    cats = collections.Counter()
    dists, hams, commons, hams_wf = [], [], [], []
    sk = collections.Counter()
    distinct_rounds, settle = [], []
    train4, _ = E.split_four(E.number_hands()[0])
    stored = {tuple(E.VAL + v if k == "n" else E.OPS[v] for k, v in E.to_postfix(s)) for _, _, s in train4}
    copies = 0
    for it, p in zip(items, panel):
        nums, target = p["meta"]["nums"], p["meta"]["target"]
        W = len(p["tokens"][0])
        valid_set = L.solutions_for(nums, target)
        pred = it["prediction"][2 * W:2 * W + 2 * len(nums) - 1]
        c, dist, ham, common = categorize(pred, nums, target, valid_set)
        cats[c] += 1
        if dist is not None:
            dists.append(dist)
        hams.append(ham); commons.append(common)
        if c in ("valid", "wrong_value"):
            hams_wf.append(ham)
        sk[tuple(t if t in E.OP_OF else 0 for t in pred)] += 1
        copies += tuple(pred) in stored
        rp = [tuple(r[2 * W:2 * W + 2 * len(nums) - 1]) for r in it["round_predictions"]]
        distinct_rounds.append(len(set(rp)))
        last_change = max((i for i in range(1, len(rp)) if rp[i] != rp[i - 1]), default=0)
        settle.append(last_change + 1)
    n = len(items)
    # control: one random well-formed answer with the RIGHT numbers per hand (seeded), same distance measure
    import itertools, random
    rr = random.Random(20260928)
    shapes = [s_ for s_ in itertools.product("no", repeat=7) if s_[0] == "n" and s_[1] == "n" and s_[-1] == "o"
              and s_.count("n") == 4 and all(sum(1 if c == "n" else -1 for c in s_[:i + 1]) >= 1 for i in range(7))
              and sum(1 if c == "n" else -1 for c in s_) == 1]
    rnd = {"within_1": 0, "within_2": 0, "within_3": 0, "sum": 0}
    for p_ in panel:
        nums = p_["meta"]["nums"]; vs = L.solutions_for(nums, p_["meta"]["target"])
        order = nums[:]; rr.shuffle(order); it_ = iter(order)
        row = [E.VAL + next(it_) if c == "n" else rr.choice(list(E.OPS.values())) for c in rr.choice(shapes)]
        h = min(sum(a != b for a, b in zip(row, v)) for v in vs)
        rnd["sum"] += h; rnd["within_1"] += h <= 1; rnd["within_2"] += h <= 2; rnd["within_3"] += h <= 3
    return {
        "control_random_wellformed_right_numbers_one_per_hand": {"mean_min_hamming": round(rnd["sum"] / n, 2), "within_1": rnd["within_1"], "within_2": rnd["within_2"], "within_3": rnd["within_3"]},
        "net": "baseline-s9276191 (width128, 20,000 steps, batch128; UNDERFIT: train numbers4 exact ~8%) - not the memorising nets; those outputs are not saved",
        "n": n, "categories_at_own_stop": dict(cats),
        "wrong_value_distance_from_24": {"n": len(dists), "median": statistics.median(dists) if dists else None,
                                         "min": min(dists) if dists else None, "within_1": sum(x <= 1 for x in dists),
                                         "within_3": sum(x <= 3 for x in dists), "values": sorted(dists)[:20]},
        "mean_numbers_of_4_that_match_the_hand": round(sum(commons) / n, 2),
        "answers_using_exactly_the_right_numbers": sum(c == 4 for c in commons),
        "min_hamming_of_7_tokens_to_nearest_valid_answer": {"mean_all": round(sum(hams) / n, 2),
                                                          "answers_within_1": sum(h <= 1 for h in hams),
                                                          "answers_within_2": sum(h <= 2 for h in hams),
                                                          "answers_within_3": sum(h <= 3 for h in hams)},
        "distinct_output_skeletons": len(sk), "commonest_skeleton_share": round(sk.most_common(1)[0][1] / n, 3),
        "outputs_identical_to_a_stored_practice_answer_of_another_hand": copies,
        "distinct_answers_over_48_rounds_mean": round(sum(distinct_rounds) / n, 2),
        "last_round_answer_changed_mean": round(sum(settle) / n, 2),
        "items_where_answer_never_changes_over_48_rounds": sum(x == 1 for x in distinct_rounds),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-numbers-diag-20260928/logs.json")
    a = ap.parse_args()
    res = {"training_curves_and_tests": training_curves(), "loop_thinking": loop_thinking(),
           "fit_run_probes_s9276193": fit_probe(), "saved_outputs_underfit_net": saved_outputs()}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
