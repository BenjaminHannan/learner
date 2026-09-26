#!/usr/bin/env python3
"""brd-11: does brd-9's result (three nights of the model's own checked hits) hold on FRESH puzzles in a wider number
world, with plain sampling, and does a stronger night search (the textbook fix for nights that stop improving) add
more? Creative research thread, 2026-09-26; problem 7.

World (wider than brd-5..9, whose 3-number world is used up): 3 numbers from 1-13 with a target from 5-60, and
4 numbers from 1-13 with target 24; solvable (claude_blurt1.solve); every puzzle used by brd-5..9 practice, DEV or test
panels is excluded. Same prompt and exact checker as brd-9 (claude_blurt1.puzzle_prompt / check).
Recipe IDENTICAL to brd-9 except the world: claude_blurt2.Solver (rule-kept sampling: RuleKeeper allows only legal
formulas over the given numbers; disclosed test scaffolding, as in brd-5..9), exact checker, first hit per miss,
retrain from base on everything kept, 3 epochs, LoRA r16 lr 2e-4 batch 8. Training target: the model's own expression
plus EOS, prompt tokens masked (claude_blurt2.train_lora); nothing added.

Per arm and LoRA seed s (0/1/2), three nights; each night has 400 NEW practice puzzles (the same in every arm):
- practise: greedy reply; if wrong, n_miss samples at temperature T, first checked hit kept; misses give nothing.
- sleep: a fresh LoRA from base on everything kept so far (all earlier nights too), 3 epochs (brd-9's recipe).
Arms (ONE change each, against its own comparator):
- R: n_miss = 30 (brd-9's recipe). Claim: R3 vs base (the replication).
- S: n_miss = 120, a stronger night search on the misses only. Claim: S3 vs R3. It asks whether more search at night
  (expert iteration's fix for nights that stop improving) finds hits on HARDER puzzles that then teach more; a gain
  from merely more examples is limited because R and S practise the same puzzles and keep at most one hit each.
Test: a fixed panel (30 samples each) for base, night 1 and night 3 of every arm and seed. Harm: Fix sleep's 300
general items (claude_dl1_nights.harm_panel), greedy, for base and night 3 of every arm and seed.

  python -B scripts/claude_brd11.py --model M --out DIR --test-puzzles T [--temp 1.0]
  python -B scripts/claude_brd11.py --dev --model M --out F.json      (DEV luck, DEV seed only)
  python -B scripts/claude_brd11.py --make-panel OUT
  python -B scripts/claude_brd11.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402

NIGHTS = 3
ROOT = Path(__file__).resolve().parent.parent
OLD_FILES = ["artifacts/claude-blurt1-dev-20260925/puzzles.jsonl"] + \
    [f"artifacts/claude-brd{k}-20260926/test_puzzles.jsonl" for k in (5, 6, 7, 8, 9)] + \
    ["artifacts/claude-brd9-20260926/transfer_puzzles.jsonl"]
NIGHT_SEEDS = (9101, 9102, 9103)
TEST_SEED = 9150
DEV_SEED = 9199


def keys_of(ps):
    return {(tuple(p["nums"]), p["target"]) for p in ps}


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def old_keys():
    """every puzzle brd-5..9 used: practice puzzles(9, 1200), the DEV panel, the test panels and brd-9's transfer set
    (test panels are never trained on, so no night may practise them)"""
    k = keys_of(B2.puzzles(9, 1200))
    for f in OLD_FILES:
        k |= keys_of(read_jsonl(ROOT / f))
    return k


def wide(seed, n, banned=(), n3=None):
    """n puzzles: two in three have 3 numbers (1-13, target 5-60), the rest 4 numbers (1-13, target 24); or exactly n3
    three-number ones when n3 is given. Solvable, distinct, none in banned."""
    rng, out, seen = random.Random(seed), [], set(banned)
    want3 = n3 if n3 is not None else None
    while len(out) < n:
        c3 = sum(len(p["nums"]) == 3 for p in out)
        if want3 is None:
            k = 3 if len(out) % 3 else 4
        else:
            k = 3 if c3 < want3 else 4
        nums = sorted(rng.randint(1, 13) for _ in range(k))
        target = rng.randint(5, 60) if k == 3 else 24
        key = (tuple(nums), target)
        if key in seen or B1.solve(nums, target) is None:
            continue
        seen.add(key)
        out.append({"id": f"pz-w{seed}-{len(out) + 1:03d}", "nums": nums, "target": target})
    return out


def nights():
    out, seen = [], old_keys()
    for sd in NIGHT_SEEDS:
        ps = wide(sd, 400, seen)
        seen |= keys_of(ps)
        out.append(ps)
    return out


def gather(s, ps, n_miss, temp, model=None):
    ex, rows = [], []
    for p in ps:
        g = s.answer(p, model)
        if B1.check(g, p["nums"], p["target"]):
            ex.append((p, g))
            rows.append({"puzzle": p, "kind": "own", "answer": g})
            continue
        hits = [t for t in s.generate(p, n_miss, temp, model) if B1.check(t, p["nums"], p["target"])]
        if hits:
            ex.append((p, hits[0]))
        rows.append({"puzzle": p, "kind": "win" if hits else "miss", "answer": hits[0] if hits else None})
    return ex, rows


def counts(rows):
    return {k: sum(r["kind"] == k for r in rows) for k in ("own", "win", "miss")}


def coverage(s, ps, n, temp, model=None):
    out = []
    for p in ps:
        hits = [B1.check(t, p["nums"], p["target"]) for t in s.generate(p, n, temp, model)]
        out.append((hits.index(True) + 1 if any(hits) else 0, sum(hits)))
    return out


def summ(st, ps):
    r = {f"cov@{k}": sum(1 for f, _ in st if 0 < f <= k) for k in (1, 5, 10, 30)}
    r["lucky"] = sum(h for _, h in st)
    r["cov@30_3num"] = sum(1 for (f, _), p in zip(st, ps) if f > 0 and len(p["nums"]) == 3)
    r["cov@30_4num"] = sum(1 for (f, _), p in zip(st, ps) if f > 0 and len(p["nums"]) == 4)
    return r


def boot_ci(ps, a_streams, b_streams, reps=2000, seed=0):
    """hand-grouped bootstrap of the mean cov@30 difference (a - b) in points, averaged over seeds (as claude_blurt5s)"""
    groups = {}
    for i, p in enumerate(ps):
        groups.setdefault(tuple(p["nums"]), []).append(i)
    keys, rng, diffs = sorted(groups), random.Random(seed), []
    for _ in range(reps):
        idx = [i for k in (rng.choice(keys) for _ in keys) for i in groups[k]]
        da = sum(sum(1 for i in idx if st[i][0] > 0) for st in a_streams) / len(a_streams)
        db = sum(sum(1 for i in idx if st[i][0] > 0) for st in b_streams) / len(b_streams)
        diffs.append((da - db) / len(idx))
    diffs.sort()
    return round(diffs[int(0.025 * reps)] * 100, 2), round(diffs[int(0.975 * reps)] * 100, 2)


def dev(a):
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    ps = wide(DEV_SEED, a.dev_items, n3=a.dev_items // 2)
    res = {"temp": a.temp, "n": a.n}
    st = coverage(s, ps, a.n, a.temp)
    greedy = [B1.check(s.answer(p), p["nums"], p["target"]) for p in ps]
    res["dev"] = summ(st, ps) | {"items": len(ps), "greedy_right": sum(greedy),
                                 "greedy_right_3num": sum(g for g, p in zip(greedy, ps) if len(p["nums"]) == 3)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    test = read_jsonl(a.test_puzzles)
    ns = nights()
    dkeys = keys_of(wide(DEV_SEED, a.dev_items, n3=a.dev_items // 2))
    assert not (keys_of(test) & (set().union(*map(keys_of, ns)) | dkeys | old_keys())), "panel overlaps"
    harm = D1.harm_panel()[:a.n_harm]
    res = {"temp": a.temp, "n_test": len(test), "n_test_3num": sum(len(p["nums"]) == 3 for p in test)}
    base = coverage(s, test, a.n, a.temp)
    res["base"] = summ(base, test)
    res["base_unreached"] = len(test) - res["base"]["cov@30"]
    res["bar_pass"] = 0.2 * res["base_unreached"]
    base_harm = D1.harm_scores(s, s.model, harm)
    res["base_harm_right"] = sum(base_harm)
    print(f"[brd11] base {res['base']} harm right {res['base_harm_right']}", flush=True)
    streams, log = {}, {}
    for arm, n_miss in (("R", 30), ("S", a.s_miss)):
        ex1, rows1 = gather(s, ns[0], n_miss, a.temp)
        res[f"{arm}_night1_practice"] = counts(rows1)
        log[f"{arm}_night1"] = rows1
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            ex, m = list(ex1), None
            for k in range(1, NIGHTS + 1):
                if k > 1:
                    ex_k, rows_k = gather(s, ns[k - 1], n_miss, a.temp, m)
                    ex += ex_k
                    res[f"{arm}_night{k}_practice_seed{sd}"] = counts(rows_k)
                    log[f"{arm}_night{k}_seed{sd}"] = rows_k
                    del m
                    if s.dev == "cuda":
                        s.torch.cuda.empty_cache()
                m = B2.train_lora(s, list(ex), a.epochs, sd)
                if k in (1, NIGHTS):
                    st = coverage(s, test, a.n, a.temp, m)
                    streams.setdefault(f"{arm}{k}", []).append(st)
                    res[f"{arm}{k}_seed{sd}"] = summ(st, test) | {"examples": len(ex)}
                if k == NIGHTS:
                    res[f"{arm}{k}_seed{sd}"]["harm"] = D1.flips(base_harm, D1.harm_scores(s, m, harm))
                print(f"[brd11] {arm} seed {sd} night {k}: {res.get(f'{arm}{k}_seed{sd}', 'trained')}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
            (out / "practice.json").write_text(json.dumps(log), encoding="utf-8")
    for name, x, y in (("R3_minus_base", "R3", None), ("S3_minus_R3", "S3", "R3"), ("R3_minus_R1", "R3", "R1"),
                       ("S3_minus_S1", "S3", "S1"), ("S3_minus_base", "S3", None), ("R1_minus_base", "R1", None)):
        res[f"ci95_{name}_cov30_pct"] = boot_ci(test, streams[x], streams[y] if y else [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd11_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    ps = wide(1, 30)
    assert len(ps) == 30 and len(keys_of(ps)) == 30
    assert all(B1.solve(p["nums"], p["target"]) is not None for p in ps)
    assert all(len(p["nums"]) == 3 and 5 <= p["target"] <= 60 or len(p["nums"]) == 4 and p["target"] == 24 for p in ps)
    assert sum(len(p["nums"]) == 3 for p in wide(2, 20, n3=5)) == 5
    ns = nights()
    got = set().union(*map(keys_of, ns))
    assert [len(x) for x in ns] == [400] * 3 and len(got) == 1200 and not got & old_keys()
    assert B1.check(B1.extract_expr("Sure: (13 - 1) * 2 = 24"), [1, 2, 13], 24)
    assert summ([(1, 2), (0, 0)], [{"nums": [1, 2, 3]}, {"nums": [1, 2, 3, 4]}])["cov@30_3num"] == 1
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--s-miss", type=int, default=120)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--dev-items", type=int, default=40)
    ap.add_argument("--make-panel", default="")
    ap.add_argument("--n3", type=int, default=80)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.dev:
        dev(a)
    elif a.make_panel:
        banned = old_keys() | set().union(*map(keys_of, nights()))
        banned |= keys_of(wide(DEV_SEED, a.dev_items, n3=a.dev_items // 2))
        Path(a.make_panel).write_text("".join(json.dumps(p) + "\n" for p in wide(TEST_SEED, 240, banned, n3=a.n3)),
                                      encoding="utf-8")
    else:
        run(a)


if __name__ == "__main__":
    main()
