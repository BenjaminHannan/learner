#!/usr/bin/env python3
"""blurt-5s: is learning from its OWN lucky hits special, or is fresh correct supervision enough?
(creative research thread, 2026-09-25; experiment 1 of the GPT-6 Pro review Ben relayed at 19:13 UTC)

Why: blurt-3 and blurt-3r (both PASS) showed that sleeping on the 1B's own checked lucky hits (arm W) roughly doubles
lucky guesses and raises puzzle coverage, while sleeping on already-known answers (C) does not. The reviewer's point:
W also sees correct answers on MORE, and harder, puzzles than C, so "self-made" and "more correct supervision" are
tangled. This separates them.

One change from blurt-3's W: for every newly won practice puzzle, the target is an exact-solver answer instead of the
model's own lucky hit (arm E). The prompts and the model's own greedy-correct examples are identical in W and E.
  Solver answer rule (fixed before the run): enumerate every expression tree the brute-force solver finds for the
  puzzle; render each with minimal brackets and " op " spacing; drop any that equals the model's own hit (spaces
  ignored) if another remains; pick the one whose length (no spaces) is closest to the model's hit; ties go to the
  alphabetically first. Mean target lengths of W and E are reported.
Arms: W (blurt-3 W), E (solver answers on the same won puzzles), C (own greedy-correct answers repeated to W's size).
Seeds 0, 1, 2. Fresh test: 240 puzzles (seed 785; 160 with 3 numbers, 80 with 4), overlap with practice and DEV
dropped; 30 samples each at the DEV-chosen temperature. Main measure: puzzles solved within 30 samples (coverage);
also coverage within 1, 5 and 10 samples, lucky samples, and a hand-grouped bootstrap 95% interval for W - E.

  python -B scripts/claude_blurt5s.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F [--train-seed 9]
  python -B scripts/claude_blurt5s.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402

PREC = {"+": 1, "-": 1, "*": 2, "/": 2}


def render(t, parent_op=None, right=False) -> str:
    """Minimal brackets. t is an int or (op, left, right)."""
    if isinstance(t, int):
        return str(t)
    op, a, b = t
    s = f"{render(a, op, False)} {op} {render(b, op, True)}"
    if parent_op is None:
        return s
    same_right = right and PREC[op] == PREC[parent_op]
    need = PREC[op] < PREC[parent_op] or (same_right and (parent_op in "-/" or op in "-/"))
    return f"({s})" if need else s


def all_solutions(nums, target) -> list[str]:
    target = Fraction(target)
    found = set()

    def rec(items):
        if len(items) == 1:
            if items[0][0] == target:
                found.add(render(items[0][1]))
            return
        for i, j in itertools.combinations(range(len(items)), 2):
            rest = [items[k] for k in range(len(items)) if k not in (i, j)]
            (va, ta), (vb, tb) = items[i], items[j]
            opts = [(va + vb, ("+", ta, tb)), (va - vb, ("-", ta, tb)), (vb - va, ("-", tb, ta)),
                    (va * vb, ("*", ta, tb))]
            if vb != 0:
                opts.append((va / vb, ("/", ta, tb)))
            if va != 0:
                opts.append((vb / va, ("/", tb, ta)))
            for v in opts:
                rec(rest + [v])
    rec([(Fraction(n), n) for n in nums])
    return sorted(s for s in found if B1.check(s, nums, int(target)))


def solver_target(p, own_hit: str) -> str:
    sols = all_solutions(p["nums"], p["target"])
    key = own_hit.replace(" ", "")
    other = [s for s in sols if s.replace(" ", "") != key] or sols
    n = len(key)
    return min(other, key=lambda s: (abs(len(s.replace(" ", "")) - n), s))


def coverage_stream(s, ps, n, temp, model=None):
    """Per puzzle: index (1-based) of the first correct sample among n, or 0; and the count of correct samples."""
    out = []
    for p in ps:
        bl = s.generate(p, n, temp, model)
        hits = [B1.check(t, p["nums"], p["target"]) for t in bl]
        out.append((hits.index(True) + 1 if any(hits) else 0, sum(hits)))
    return out


def summarize(stream, ks=(1, 5, 10, 30)):
    r = {f"cov@{k}": sum(1 for f, _ in stream if 0 < f <= k) for k in ks}
    r["lucky"] = sum(h for _, h in stream)
    return r


def boot_ci(ps, a_streams, b_streams, reps=2000, seed=0):
    """Hand-grouped bootstrap of mean coverage@30 difference (a - b), averaged over seeds."""
    groups = {}
    for i, p in enumerate(ps):
        groups.setdefault(tuple(p["nums"]), []).append(i)
    keys = sorted(groups)
    rng = random.Random(seed)
    solved = lambda st, idx: sum(1 for i in idx if st[i][0] > 0)  # noqa: E731
    diffs = []
    for _ in range(reps):
        idx = [i for k in (rng.choice(keys) for _ in keys) for i in groups[k]]
        da = sum(solved(st, idx) for st in a_streams) / len(a_streams)
        db = sum(solved(st, idx) for st in b_streams) / len(b_streams)
        diffs.append((da - db) / len(idx))
    diffs.sort()
    return round(diffs[int(0.025 * reps)] * 100, 2), round(diffs[int(0.975 * reps)] * 100, 2)


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    train, test = B2.puzzles(a.train_seed, a.n_train), B2.puzzles(a.test_seed, a.n_test)
    keys = {(tuple(p["nums"]), p["target"]) for p in train}
    if a.dev_puzzles:
        keys |= {(tuple(p["nums"]), p["target"]) for p in
                 (json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x)}
    n0 = len(test)
    test = [p for p in test if (tuple(p["nums"]), p["target"]) not in keys]
    res.update({"n_train": len(train), "n_test": len(test), "test_dropped_overlap": n0 - len(test), "temp": temp,
                "n_test_3num": sum(len(p["nums"]) == 3 for p in test)})
    base = coverage_stream(s, test, a.n, temp)
    res["base"] = summarize(base)
    print(f"[b5s] base {res['base']}", flush=True)
    own, wins = [], []
    for p in train:
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            own.append((p, g))
            continue
        hits = [t for t in s.generate(p, a.n, temp) if B1.check(t, p["nums"], p["target"])]
        if hits:
            wins.append((p, hits[0]))
    ewins = [(p, solver_target(p, h)) for p, h in wins]
    assert all(B1.check(e, p["nums"], p["target"]) for p, e in ewins)
    ex_w, ex_e = own + wins, own + ewins
    ex_c = (own * (len(ex_w) // max(1, len(own)) + 1))[:len(ex_w)] if own else []
    ln = lambda ex: round(sum(len(e.replace(" ", "")) for _, e in ex) / max(1, len(ex)), 2)  # noqa: E731
    res.update({"own": len(own), "wins": len(wins), "examples": len(ex_w), "mean_len_W_wins": ln(wins),
                "mean_len_E_wins": ln(ewins), "E_equal_to_own_hit": sum(e.replace(" ", "") == h.replace(" ", "")
                                                                        for (_, e), (_, h) in zip(ewins, wins))})
    print(f"[b5s] practice own {len(own)} wins {len(wins)}", flush=True)
    streams = {}
    for arm, ex in (("W", ex_w), ("E", ex_e), ("C", ex_c)):
        streams[arm] = []
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            if not ex:                      # no examples for this arm (only in tiny smoke runs): report, don't crash
                res[f"{arm}_seed{sd}"] = None
                continue
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            st = coverage_stream(s, test, a.n, temp, m)
            streams[arm].append(st)
            res[f"{arm}_seed{sd}"] = summarize(st)
            print(f"[b5s] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
    if not all(streams[k] for k in ("W", "E")):
        raise SystemExit("W or E had no examples")
    res["ci95_W_minus_E_cov30_pct"] = boot_ci(test, streams["W"], streams["E"])
    res["ci95_E_minus_base_cov30_pct"] = boot_ci(test, streams["E"], [base])
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "blurt5s_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    assert render(("*", ("+", 1, 2), 3)) == "(1 + 2) * 3" and render(("-", 8, ("-", 3, 1))) == "8 - (3 - 1)"
    assert render(("/", 8, ("*", 2, 2))) == "8 / (2 * 2)" and render(("+", 1, ("*", 2, 3))) == "1 + 2 * 3"
    for nums, t in (([3, 8, 1], 24), ([4, 6, 1, 1], 24), ([2, 5, 7], 19), ([1, 5, 5, 5], 24)):
        sols = all_solutions(nums, t)
        assert sols and all(B1.check(x, nums, t) for x in sols), (nums, t)
    p = {"nums": [3, 8, 1], "target": 24}
    e = solver_target(p, "3 * 8 * 1")
    assert B1.check(e, p["nums"], 24) and e.replace(" ", "") != "3*8*1", e
    assert all_solutions([1, 1, 1, 1], 24) == []
    print("selftest ok", all_solutions([1, 5, 5, 5], 24)[:3], e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--test-seed", type=int, default=785)
    ap.add_argument("--n-test", type=int, default=240)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
