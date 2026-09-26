#!/usr/bin/env python3
"""brd-5: does sleep widen coverage because it sees MANY DIFFERENT newly won puzzles? (creative research thread,
2026-09-26; the follow-up to tgt-5, artifacts/claude-tgt5-20260926/VERIFY-tgt5.md; Ben 01:42 UTC: "Ok do it then")

Why: in blurt-5s, sleeping on the model's own greedy-correct answers plus one lucky hit per newly won puzzle (W, 199
examples over ~200 distinct puzzles) widened coverage (77 -> 108-112 of 184), while the same 20 greedy-correct
answers repeated to W's size (C) collapsed it (11-14). tgt-5 showed C matches answers to targets as well as W, so
target matching does not explain the gap. C differs from W in two ways: it has few distinct puzzles, and none of
them are new wins. This separates breadth from newness.

ONE change from W: the number of distinct won puzzles. Arm N keeps W's 20-ish own greedy-correct examples exactly as
in W, but its win examples come from only K_N = 20 won puzzles (drawn with seed 798 from W's wins), each with the
same first lucky hit W uses, repeated in turn until N has exactly W's number of examples. Same prompts, recipe
(LoRA r16, 3 epochs, lr 2e-4, batch 8), temperature rule and test as W. C (blurt-5s C) is trained and scored as a
reference only.
Test: a panel FIXED BEFORE REGISTRATION (artifacts/claude-brd5-20260926/test_puzzles.jsonl: 240 puzzles, 160 with
3 numbers and 80 with 4, seed 798, overlap with practice seed 9 and the DEV panel already removed); 30 samples each.

  python -B scripts/claude_brd5.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F --test-puzzles T
  python -B scripts/claude_brd5.py --make-panel --dev-puzzles F --out-panel T
  python -B scripts/claude_brd5.py --selftest
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
import claude_blurt5s as S5  # noqa: E402


def banned_keys(train_seed, n_train, dev_puzzles):
    keys = {(tuple(p["nums"]), p["target"]) for p in B2.puzzles(train_seed, n_train)}
    if dev_puzzles:
        keys |= {(tuple(p["nums"]), p["target"]) for p in
                 (json.loads(x) for x in Path(dev_puzzles).read_text().splitlines() if x.strip())}
    return keys


def make_panel(banned, seed=798, n3=160, n4=80):
    """Fresh test panel: blurt-2 recipe, overlap dropped, then the first n3 3-number and n4 4-number puzzles."""
    pool = [p for p in B2.puzzles(seed, 3 * (n3 + n4)) if (tuple(p["nums"]), p["target"]) not in banned]
    three = [p for p in pool if len(p["nums"]) == 3][:n3]
    four = [p for p in pool if len(p["nums"]) == 4][:n4]
    assert len(three) == n3 and len(four) == n4
    return three + four


def narrow(own, wins, k, seed=798):
    """N: own as in W, then k randomly chosen wins repeated in turn to W's size."""
    total = len(own) + len(wins)
    pick = random.Random(seed).sample(wins, min(k, len(wins)))
    rep = [pick[i % len(pick)] for i in range(len(wins))] if pick else []
    ex = own + rep
    assert len(ex) == total
    return ex, pick


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    train = B2.puzzles(a.train_seed, a.n_train)
    test = [json.loads(x) for x in Path(a.test_puzzles).read_text().splitlines() if x.strip()]
    banned = banned_keys(a.train_seed, a.n_train, a.dev_puzzles)
    assert not any((tuple(p["nums"]), p["target"]) in banned for p in test), "panel overlaps practice or DEV"
    res.update({"n_train": len(train), "n_test": len(test), "temp": temp,
                "n_test_3num": sum(len(p["nums"]) == 3 for p in test)})
    base = S5.coverage_stream(s, test, a.n, temp)
    res["base"] = S5.summarize(base)
    print(f"[brd] base {res['base']}", flush=True)
    own, wins = [], []
    for p in train:
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            own.append((p, g))
            continue
        hits = [t for t in s.generate(p, a.n, temp) if B1.check(t, p["nums"], p["target"])]
        if hits:
            wins.append((p, hits[0]))
    ex_w = own + wins
    ex_n, pick = narrow(own, wins, a.k_narrow, a.narrow_seed)
    ex_c = (own * (len(ex_w) // max(1, len(own)) + 1))[:len(ex_w)] if own else []
    res.update({"own": len(own), "wins": len(wins), "examples": len(ex_w), "N_distinct_wins": len(pick),
                "N_distinct_puzzles": len({(tuple(p["nums"]), p["target"]) for p, _ in ex_n}),
                "W_distinct_puzzles": len({(tuple(p["nums"]), p["target"]) for p, _ in ex_w})})
    (out / "narrow_picks.jsonl").write_text("".join(json.dumps({"puzzle": p, "hit": h}) + "\n" for p, h in pick),
                                            encoding="utf-8")
    print(f"[brd] practice own {len(own)} wins {len(wins)}; N uses {len(pick)} wins", flush=True)
    streams = {}
    for arm, ex in (("W", ex_w), ("N", ex_n), ("C", ex_c)):
        streams[arm] = []
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            if not ex:
                res[f"{arm}_seed{sd}"] = None
                continue
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            st = S5.coverage_stream(s, test, a.n, temp, m)
            streams[arm].append(st)
            res[f"{arm}_seed{sd}"] = S5.summarize(st)
            print(f"[brd] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
    if not all(streams[k] for k in ("W", "N")):
        raise SystemExit("W or N had no examples")
    res["ci95_W_minus_N_cov30_pct"] = S5.boot_ci(test, streams["W"], streams["N"])
    res["ci95_W_minus_base_cov30_pct"] = S5.boot_ci(test, streams["W"], [base])
    res["ci95_N_minus_base_cov30_pct"] = S5.boot_ci(test, streams["N"], [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd5_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    own = [({"nums": [1, 2, 3], "target": 6}, "1 + 2 + 3")] * 3
    wins = [({"nums": [i, 2, 3], "target": i + 5}, f"{i} + 2 + 3") for i in range(1, 9)]
    ex, pick = narrow(own, wins, 2, 798)
    assert len(ex) == len(own) + len(wins) and len(pick) == 2 and ex[:3] == own
    assert set(map(str, ex[3:])) == set(map(str, pick)) and abs(ex[3:].count(pick[0]) - ex[3:].count(pick[1])) <= 1
    assert len(narrow(own, wins[:1], 20)[1]) == 1
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--k-narrow", type=int, default=20)
    ap.add_argument("--narrow-seed", type=int, default=798)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--make-panel", action="store_true")
    ap.add_argument("--out-panel", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.make_panel:
        ps = make_panel(banned_keys(a.train_seed, a.n_train, a.dev_puzzles))
        Path(a.out_panel).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_panel).write_text("".join(json.dumps(p) + "\n" for p in ps), encoding="utf-8")
        print("panel", len(ps), sum(len(p["nums"]) == 3 for p in ps))
    else:
        run(a)


if __name__ == "__main__":
    main()
