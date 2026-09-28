#!/usr/bin/env python3
"""SL no-training reads (Lead 3: which signal says "this answer is wrong"; Lead 1: stop when the answer is unchanged).

Design and marks: artifacts/claude-dir-sl-20260928/DESIGN.md and PASSMARKS.md (Parts A and B).

    extract   (needs torch)  per-item records for one seed from saved checkpoints: the qualified source net and the
                             baseline loop's adapted k*.pt, on dev 9x9 mazes and fresh sums / grids. No training.
    judge     (pure python)  AUROC, coverage-versus-risk, unchanged-for-N stops and the PASSMARKS words from the records.
    selftest                 pure-python arithmetic checks, plus (if torch is importable) a check that the trace
                             reproduces the sealed harness's scores on a random-init net.

Record file, one per seed: {"seed", "fixed_depth", "nets": {"k0"|"k<rung>": {"maze"|"sums4"|"grids5": [item, ...]}},
"consistency": {...}}. Item fields (rounds/cap/right/right_fixed/changing/path_len match H12's doubt script):
  rounds  round the ruler's stop picks (48 if never; claude_fewex_bench.py:76-78); cap = rounds == 48
  right   answer at that round exactly right; right_fixed = answer at the fixed depth exactly right; right48 = round 48
  changing  full arg-max answers of rounds 46-48 not all identical
  q_stop / q_last  stop probability at the chosen round / at round 48
  margin  smallest top-two probability gap over the fill cells at the chosen round
  flips10  number of rounds in 39..48 whose full answer differs from the previous round
  move_last  |h48 - h47| / |h48| for this item
  eq48  the answer at the chosen round equals the round-48 answer (cells: full arg-max)
  s3_rounds / s3_right / s6_rounds / s6_right  the unchanged-for-3 / unchanged-for-6 stop and its answer's correctness
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
MAX_ROUNDS = 48
JUDGED = (64, 256, 1024, 4096, 16384)
BASELINE_RUNGS = (64, 256, 1024, 4096, 16384)
SIGNALS = ("q_stop", "q_last", "margin", "no_flips", "still")
KEEP = (0.9, 0.75, 0.5)
MIN_CLASS = 10
USEFUL_AUC, NOT_USEFUL_AUC = 0.70, 0.60
CAP_BAR, FAIL_SLACK = 150, 6
MIN_RIGHT = 31          # PASSMARKS-ADDENDUM-1: a rung where the net solves fewer than 31 of 300 cannot pass Part B


# ---- pure python arithmetic -----------------------------------------------------------------

def stable_round(preds, n):
    """First round t >= n (1-indexed) whose last n whole answers are identical; MAX_ROUNDS if none."""
    for t in range(n, MAX_ROUNDS + 1):
        if all(preds[t - 1 - j] == preds[t - 1] for j in range(1, n)):
            return t
    return MAX_ROUNDS


def flips_last10(preds):
    """Rounds in 39..48 whose whole answer differs from the previous round's."""
    return sum(preds[x] != preds[x - 1] for x in range(MAX_ROUNDS - 10, MAX_ROUNDS))


def confidences(rec):
    return {"q_stop": rec["q_stop"], "q_last": rec["q_last"], "margin": rec["margin"],
            "no_flips": -rec["flips10"], "still": -rec["move_last"]}


def auroc(conf, right):
    """P(a right answer is more confident than a wrong one), ties count half. None if either class has < MIN_CLASS."""
    pos = [c for c, r in zip(conf, right) if r]
    neg = [c for c, r in zip(conf, right) if not r]
    if len(pos) < MIN_CLASS or len(neg) < MIN_CLASS:
        return None
    order = sorted(range(len(conf)), key=lambda i: conf[i])
    rank = [0.0] * len(conf)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and conf[order[j + 1]] == conf[order[i]]:
            j += 1
        for k in range(i, j + 1):
            rank[order[k]] = (i + j) / 2 + 1
        i = j + 1
    rsum = sum(rank[k] for k in range(len(conf)) if right[k])
    return (rsum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def chance_se(n_wrong, n_right):
    """Standard error of an AUROC of a signal with no information."""
    return math.sqrt((n_wrong + n_right + 1) / (12 * n_wrong * n_right))


def coverage_risk(conf, right, fracs=KEEP):
    """Expected wrong among the most confident `frac` of items; tied groups are split proportionally."""
    n = len(conf)
    order = sorted(range(n), key=lambda i: -conf[i])
    out = {}
    for f in fracs:
        quota, kept, wrong = f * n, 0.0, 0.0
        i = 0
        while i < n and kept < quota - 1e-9:
            j = i
            while j + 1 < n and conf[order[j + 1]] == conf[order[i]]:
                j += 1
            grp = j - i + 1
            take = min(grp, quota - kept)
            gw = sum(not right[order[k]] for k in range(i, j + 1))
            wrong += gw * take / grp
            kept += take
            i = j + 1
        out[str(f)] = {"kept": round(kept, 1), "wrong_kept": round(wrong, 1)}
    return out


def rung_cell(items):
    """auroc / se / coverage-risk per signal for one (net, panel)."""
    right = [r["right"] for r in items]
    nw = sum(not x for x in right)
    cell = {"n": len(items), "wrong": nw, "eligible": nw >= MIN_CLASS and len(items) - nw >= MIN_CLASS, "signals": {}}
    for s in SIGNALS:
        conf = [confidences(r)[s] for r in items]
        a = auroc(conf, right)
        entry = {"auroc": None if a is None else round(a, 4)}
        if a is not None:
            entry["chance_se"] = round(chance_se(nw, len(items) - nw), 4)
            entry["coverage_risk"] = coverage_risk(conf, right)
        cell["signals"][s] = entry
    return cell


def rule_row(items, rule):
    if rule == "ruler":
        rounds, right = [r["rounds"] for r in items], [r["right"] for r in items]
    elif rule in ("s3", "s6"):
        rounds, right = [r[f"{rule}_rounds"] for r in items], [r[f"{rule}_right"] for r in items]
    elif rule == "fixed":
        rounds, right = [None] * len(items), [r["right_fixed"] for r in items]
    else:
        raise ValueError(rule)
    n = len(items)
    row = {"right": sum(right), "n": n}
    if rounds[0] is not None:
        row["cap_hits"] = sum(x == MAX_ROUNDS for x in rounds)
        row["mean_rounds"] = round(sum(rounds) / n, 3)
    return row


def ceil_two_thirds(n):
    return -(-2 * n // 3)


def judge_a(recs):
    """Word per signal from the maze rungs of both seeds (PASSMARKS Part A)."""
    words = {}
    for s in SIGNALS:
        per_seed = {}
        for seed, rec in recs.items():
            aucs = []
            for k in BASELINE_RUNGS:
                net = rec["nets"].get(f"k{k}")
                if not net:
                    continue
                a = rung_cell(net["maze"])["signals"][s]["auroc"]
                if a is not None:
                    aucs.append(a)
            per_seed[seed] = aucs
        useful = all(len(a) >= 3 and sum(x >= USEFUL_AUC for x in a) >= ceil_two_thirds(len(a)) for a in per_seed.values())
        not_useful = all(len(a) >= 1 and all(x <= NOT_USEFUL_AUC for x in a) for a in per_seed.values())
        if len(per_seed) < 2:
            word = "NOT SHOWN (needs both seeds)"
        else:
            word = "USEFUL" if useful else "NOT USEFUL" if not_useful else "NOT SHOWN"
        words[s] = {"word": word, "eligible_aurocs_by_seed": per_seed}
    return words


def judge_b(recs):
    """Word per rule (PASSMARKS Part B)."""
    out = {}
    for rule in ("ruler", "s3", "s6"):
        per_seed = {}
        for seed, rec in recs.items():
            rows = {}
            for k in JUDGED:
                net = rec["nets"].get(f"k{k}")
                if not net:
                    continue
                r, f = rule_row(net["maze"], rule), rule_row(net["maze"], "fixed")
                rows[str(k)] = {**r, "fixed_right": f["right"],
                                "pass": r["right"] >= MIN_RIGHT and r["right"] >= f["right"] - FAIL_SLACK and r["cap_hits"] <= CAP_BAR}
            per_seed[seed] = rows
        passing = {seed: sum(v["pass"] for v in rows.values()) for seed, rows in per_seed.items()}
        complete = len(per_seed) == 2 and all(len(rows) == len(JUDGED) for rows in per_seed.values())
        if not complete:
            word = "NOT SHOWN (missing rungs or seed)"
        elif all(p >= 4 for p in passing.values()):
            word = "CEILING MET"
        elif all(p <= 2 for p in passing.values()):
            word = "FAILS"
        else:
            word = "NOT SHOWN"
        out[rule] = {"word": word, "rungs_passing_by_seed": passing, "rungs": per_seed}
    return out


def check_consistency(recs):
    bad = [f"seed {seed} {k}" for seed, rec in recs.items()
           for k, v in rec.get("consistency", {}).items() if not v.get("ok")]
    return bad


def judge_cmd(pattern, out):
    recs = {}
    for seed in (0, 1):
        p = ROOT / pattern.format(seed=seed)
        if p.exists():
            recs[seed] = json.loads(p.read_text())
    if not recs:
        print("no record files found")
        return None
    bad = check_consistency(recs)
    result = {"validity": "INVALID: recomputed counts did not match the harness records at " + ", ".join(bad)
              if bad else "ok: every recomputed count matched the harness records",
              "seeds": sorted(recs)}
    print(result["validity"])
    if bad:
        if out:
            Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result
    result["part_a"] = judge_a(recs)
    result["part_b"] = judge_b(recs)
    result["cells"] = {f"s{seed}": {net: {panel: rung_cell(items) for panel, items in panels.items()}
                                    for net, panels in rec["nets"].items()} for seed, rec in recs.items()}
    result["rules"] = {f"s{seed}": {net: {panel: {rule: rule_row(items, rule) for rule in ("ruler", "fixed", "s3", "s6")}
                                         for panel, items in panels.items()}
                                   for net, panels in rec["nets"].items()} for seed, rec in recs.items()}
    print("== Part A (Lead 3): word per signal, judged on maze rungs", JUDGED)
    for s, w in result["part_a"].items():
        print(f"   {s}: {w['word']} | eligible AUROCs by seed {w['eligible_aurocs_by_seed']}")
    print("== Part B (Lead 1, ceiling only): word per rule")
    for rule, w in result["part_b"].items():
        print(f"   {rule}: {w['word']} | rungs passing {w['rungs_passing_by_seed']}")
    for seed in sorted(recs):
        print(f"== seed {seed}: rule rows of n (right | cap hits | mean rounds), then AUROC per signal")
        for net, panels in result["rules"][f"s{seed}"].items():
            for panel, rows in panels.items():
                cell = result["cells"][f"s{seed}"][net][panel]
                line = " ; ".join(f"{r} {v['right']} of {v['n']}" + (f" |{v['cap_hits']}|{v['mean_rounds']}" if "cap_hits" in v else "")
                                  for r, v in rows.items())
                aur = " ".join(f"{s}={cell['signals'][s]['auroc']}" for s in SIGNALS) if cell["eligible"] else \
                    f"not eligible ({cell['wrong']} wrong of {cell['n']})"
                print(f"   {net} {panel}: {line}\n      AUROC {aur}")
    if out:
        Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


# ---- extract (torch) --------------------------------------------------------------------------

def trace_items(net, items, depth, B, batch=32):
    """The ruler's own computation (claude_fewex_net.loop_rounds), keeping per-round answers, margins and state movement."""
    import torch
    N = B.N
    recs = []
    net.eval()
    with torch.no_grad():
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            t, s, _ = N.tensors(chunk)
            h_, w_ = t.shape[1:]
            e, (dr, dc) = net.embed(t, s)
            h = torch.zeros_like(e)
            preds, qs, mmin, move = [], [], [], []
            fill = s.view(s.shape[0], -1).bool()
            for _ in range(MAX_ROUNDS):
                hn = net.step(h, e, dr, dc)
                lg, q = net.read(hn)
                preds.append(lg.argmax(-1))
                qs.append(torch.sigmoid(q.float()))
                top = torch.softmax(lg.float(), -1).topk(2, dim=-1).values
                gap = (top[..., 0] - top[..., 1]).masked_fill(~fill, float("inf"))
                mmin.append(gap.min(1).values)
                move.append((hn - h).flatten(1).norm(dim=1) / hn.flatten(1).norm(dim=1).clamp_min(1e-12))
                h = hn
            P = torch.stack(preds, 1).tolist()          # [B, 48, T]
            Q = torch.stack(qs, 1).tolist()
            M = torch.stack(mmin, 1).tolist()
            V = torch.stack(move, 1).tolist()
            for j, it in enumerate(chunk):
                p, q = P[j], Q[j]
                r = next((x + 1 for x in range(2, MAX_ROUNDS) if q[x] > .5 and p[x] == p[x - 1] == p[x - 2]), MAX_ROUNDS)
                rows = lambda flat: [flat[a * w_:(a + 1) * w_] for a in range(h_)]
                ok = lambda rnd: bool(B.exact(it, rows(p[rnd - 1])))
                r3, r6 = stable_round(p, 3), stable_round(p, 6)
                recs.append({"i": i + j, "rounds": r, "cap": r == MAX_ROUNDS, "right": ok(r), "right_fixed": ok(depth),
                             "right48": ok(MAX_ROUNDS), "changing": not (p[-1] == p[-2] == p[-3]),
                             "path_len": it.meta.get("path_len"),
                             "q_stop": q[r - 1], "q_last": q[-1], "margin": M[j][r - 1],
                             "flips10": flips_last10(p),
                             "move_last": V[j][-1], "eq48": p[r - 1] == p[-1],
                             "s3_rounds": r3, "s3_right": ok(r3), "s6_rounds": r6, "s6_right": ok(r6)})
    return recs


def counts(recs):
    n = len(recs)
    return {"right": sum(r["right"] for r in recs), "fixed_right": sum(r["right_fixed"] for r in recs),
            "cap_hits": sum(r["cap"] for r in recs), "mean_rounds": sum(r["rounds"] for r in recs) / n}


def same(mine, h):
    return (mine["right"], mine["fixed_right"], mine["cap_hits"]) == (h["right"], h["fixed_right"], h["cap_hits"]) \
        and abs(mine["mean_rounds"] - h["mean_rounds"]) < 1e-9


def extract_cmd(source_dir, run_dir, adapt_json, seed, out, rungs, threads):
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net as base
    B.N = base
    torch.set_num_threads(threads)
    adapt = json.loads(Path(adapt_json).read_text())
    src = json.loads((Path(source_dir) / "source.json").read_text())
    depth = adapt["fixed_depth"]
    if (adapt["seed"], src["seed"], adapt["arm"]) != (seed, seed, "loop") or src["fixed_depth"] != depth:
        raise ValueError("seed, arm or fixed-depth identity mismatch between source.json, adapt.json and --seed")
    maze = D.panels()[0]["dev"][9]
    old = D.old_panels(D.SOURCE_SEED + 300)                     # the guard panels (claude_fewex_source_qualify.py:19)
    rec = {"seed": seed, "fixed_depth": depth, "nets": {}, "consistency": {}}
    nets = [("k0", Path(source_dir) / "source.pt")] + [(f"k{k}", Path(run_dir) / f"k{k}.pt") for k in rungs]
    for name, path in nets:
        if not path.exists():
            print(json.dumps({"phase": "sl_extract", "seed": seed, "net": name, "skipped": "checkpoint missing"}), flush=True)
            continue
        net = B.load_model(path, "loop")
        panels = {"maze": trace_items(net, maze, depth, B)}
        panels.update({k: trace_items(net, v, depth, B) for k, v in old.items()})
        rec["nets"][name] = panels
        ck = {}
        if name == "k0":
            ck["maze"] = {"ok": same(counts(panels["maze"]), adapt["rungs"]["0"]["9"]), "recomputed": counts(panels["maze"]),
                          "harness": {x: adapt["rungs"]["0"]["9"][x] for x in ("right", "fixed_right", "cap_hits", "mean_rounds")}}
            for kind in old:
                h = src["old"][kind]
                ck[kind] = {"ok": same(counts(panels[kind]), h), "recomputed": counts(panels[kind]),
                            "harness": {x: h[x] for x in ("right", "fixed_right", "cap_hits", "mean_rounds")}}
        else:
            h = adapt["rungs"][name[1:]]["9"]
            ck["maze"] = {"ok": same(counts(panels["maze"]), h), "recomputed": counts(panels["maze"]),
                          "harness": {x: h[x] for x in ("right", "fixed_right", "cap_hits", "mean_rounds")}}
        for panel, v in ck.items():
            rec["consistency"][f"{name}/{panel}"] = v
        print(json.dumps({"phase": "sl_extract", "seed": seed, "net": name,
                          "consistent": all(v["ok"] for v in ck.values()),
                          "maze_right": counts(panels["maze"])["right"]}), flush=True)
    Path(out).write_text(json.dumps(rec, sort_keys=True) + "\n")


# ---- selftest ---------------------------------------------------------------------------------

def _item(rounds, right, q=0.9, margin=0.5, flips=0, move=0.0, s3=None, s6=None, fixed=None):
    return {"rounds": rounds, "right": right, "right_fixed": right if fixed is None else fixed,
            "q_stop": q, "q_last": q, "margin": margin, "flips10": flips, "move_last": move,
            "s3_rounds": rounds if s3 is None else s3[0], "s3_right": right if s3 is None else s3[1],
            "s6_rounds": rounds if s6 is None else s6[0], "s6_right": right if s6 is None else s6[1]}


def selftest_pure():
    # stable_round: answers change until round 5, then constant
    preds = [[i] for i in range(4)] + [[9]] * 44
    assert stable_round(preds, 3) == 7 and stable_round(preds, 6) == 10, (stable_round(preds, 3), stable_round(preds, 6))
    assert stable_round([[i] for i in range(48)], 3) == 48
    assert flips_last10([[i] for i in range(48)]) == 10 and flips_last10([[1]] * 48) == 0
    assert flips_last10([[1]] * 38 + [[2]] + [[2]] * 9) == 1 and flips_last10([[1]] * 37 + [[2]] + [[2]] * 10) == 0
    assert stable_round([[1]] * 48, 3) == 3 and stable_round([[1]] * 48, 6) == 6
    # auroc: perfect, reversed, chance, ties, ineligible
    right = [True] * 12 + [False] * 12
    assert auroc(list(range(24, 12, -1)) + list(range(12, 0, -1)), right) == 1.0
    assert auroc(list(range(12)) + list(range(12, 24)), right) == 0.0
    assert auroc([1.0] * 24, right) == 0.5
    tied = [2.0] * 6 + [1.0] * 6 + [1.0] * 6 + [0.0] * 6            # right: 6 at 2.0, 6 at 1.0; wrong: 6 at 1.0, 6 at 0.0
    assert abs(auroc(tied, right) - 126 / 144) < 1e-12, auroc(tied, right)      # 72 wins + 18 half-ties + 36 wins
    assert auroc([1, 2, 3], [True, False, True]) is None
    assert abs(chance_se(25, 275) - 0.0605) < 5e-4, chance_se(25, 275)
    # coverage-risk: wrong ones are the least confident; keep the top 50% -> 0 wrong; ties split
    cr = coverage_risk(list(range(20, 0, -1)), [True] * 10 + [False] * 10)
    assert cr["0.5"] == {"kept": 10.0, "wrong_kept": 0.0} and cr["0.9"] == {"kept": 18.0, "wrong_kept": 8.0}, cr
    cr = coverage_risk([1.0] * 10, [True] * 5 + [False] * 5)
    assert cr["0.5"] == {"kept": 5.0, "wrong_kept": 2.5}, cr
    # rule rows and words on synthetic two-seed records
    good = []                                    # 24 wrong + 276 right: wrong ones have low q and margin, more flips, more movement
    for i in range(300):
        w = i < 24
        good.append(_item(20, not w, q=0.2 if w else 0.95, margin=0.1 if w else 0.8, flips=5 if w else 0, move=0.3 if w else 0.01,
                          s3=(10, not w), s6=(48, not w), fixed=not w))
    rec = {"seed": 0, "fixed_depth": 16, "nets": {f"k{k}": {"maze": good} for k in JUDGED}, "consistency": {}}
    recs = {0: rec, 1: rec}
    wa = judge_a(recs)
    assert all(v["word"] == "USEFUL" for v in wa.values()), wa
    wb = judge_b(recs)
    assert wb["ruler"]["word"] == "CEILING MET" and wb["s3"]["word"] == "CEILING MET", wb
    assert wb["s6"]["word"] == "FAILS" and wb["s6"]["rungs_passing_by_seed"] == {0: 0, 1: 0}, wb["s6"]
    noise = [_item(20, i >= 24, q=(i * 7 % 10) / 10, margin=(i * 3 % 10) / 10, flips=i % 4, move=(i * 11 % 10) / 10) for i in range(300)]
    nrec = {"seed": 0, "fixed_depth": 16, "nets": {f"k{k}": {"maze": noise} for k in JUDGED}, "consistency": {}}
    assert all(v["word"] in ("NOT USEFUL", "NOT SHOWN") for v in judge_a({0: nrec, 1: nrec}).values())
    one = judge_a({0: rec})
    assert all(v["word"].startswith("NOT SHOWN") for v in one.values())
    assert check_consistency({0: {"consistency": {"k0/maze": {"ok": False}}}}) == ["seed 0 k0/maze"]
    dead = [_item(3, False) for _ in range(300)]                           # a net that solves nothing and stops at round 3 passes nothing
    drec = {"seed": 0, "fixed_depth": 16, "nets": {f"k{k}": {"maze": dead} for k in JUDGED}, "consistency": {}}
    assert judge_b({0: drec, 1: drec})["ruler"]["rungs_passing_by_seed"] == {0: 0, 1: 0}
    # a rule that stops on the cap everywhere fails the cap half
    slow = [_item(48, True) for _ in range(300)]
    assert rule_row(slow, "ruler") == {"right": 300, "n": 300, "cap_hits": 300, "mean_rounds": 48.0}


def selftest_torch():
    """The trace must reproduce the sealed harness's counts (claude_fewex_bench.score) on a random-init net."""
    import random
    import torch
    import claude_fewex_bench as B
    import claude_fewex_data as D
    import claude_fewex_net as base
    B.N = base
    torch.manual_seed(3)
    net = base.Net("loop")
    rng = random.Random(5)
    items = D.panels()[0]["dev"][9][:8] + [D.latin_legend(rng, 5) for _ in range(4)]
    for panel in (items[:8], items[8:]):
        recs = trace_items(net, panel, 16, B, batch=4)
        want = B.score(net, panel, 16, batch=4)
        got = counts(recs)
        assert same(got, want), (got, want)
        for r in recs:
            assert 3 <= r["rounds"] <= MAX_ROUNDS and 0 <= r["flips10"] <= 10 and r["margin"] >= 0 and r["move_last"] >= 0
            assert r["s3_rounds"] >= 3 and r["s6_rounds"] >= 6
            assert r["eq48"] == (r["rounds"] == MAX_ROUNDS or r["eq48"])
    return True


def selftest():
    selftest_pure()
    try:
        import torch  # noqa: F401
    except ImportError:
        print(json.dumps({"selftest": "ok", "torch_part": "skipped (torch not importable)"}))
        return
    selftest_torch()
    print(json.dumps({"selftest": "ok", "torch_part": "ran"}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    e = sub.add_parser("extract")
    e.add_argument("--source-dir", required=True, help="qualified source folder (source.pt, source.json)")
    e.add_argument("--run-dir", required=True, help="baseline loop-s<seed>-pre folder with k<rung>.pt")
    e.add_argument("--adapt-json", required=True)
    e.add_argument("--seed", type=int, choices=(0, 1), required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--rungs", type=int, nargs="+", default=list(BASELINE_RUNGS))
    e.add_argument("--threads", type=int, default=1)
    j = sub.add_parser("judge")
    j.add_argument("--records", default="artifacts/claude-dir-sl-20260928/read/sl-records-s{seed}.json")
    j.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "extract":
        extract_cmd(a.source_dir, a.run_dir, a.adapt_json, a.seed, a.out, a.rungs, a.threads)
    else:
        judge_cmd(a.records, a.out)


if __name__ == "__main__":
    main()
