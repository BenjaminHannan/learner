#!/usr/bin/env python3
"""brd-6: at EQUAL training exposure, does sleeping on twice as many different won puzzles widen coverage more?
(creative research thread, 2026-09-26; follow-up to brd-5, artifacts/claude-brd5-20260926/VERIFY-brd5.md)

Why: brd-5 (registered INCONCLUSIVE) showed, at equal exposure, that 20 won puzzles repeated drop fresh coverage below
the untrained model while one hit on each of ~190 won puzzles raises it. This asks the same question upward: if
fewer distinct puzzles hurt, do MORE distinct puzzles help, with the number of training passes held fixed?

Practice: puzzles(seed 9, 800); its first 400 are exactly brd-5's practice set. Each practice puzzle gets the greedy
answer; a miss gets 30 blurts at the DEV-chosen temperature; the first hit wins it (brd-5 / blurt-5s recipe).
Arms (LoRA r16, lr 2e-4, batch 8, seeds 0/1/2):
- W4 = brd-5's W, unchanged: own + wins from the first 400 practice puzzles, 3 epochs.
- W8 = own + wins from all 800, trained for the SAME number of example passes as W4 (3 x len(W4)): the W8 examples
  are shuffled and repeated in turn up to that length, then trained as one pass (train_lora epochs=1). So every W8
  example is seen once or twice instead of three times; the optimizer steps are equal up to rounding.
ONE change from W4: the number of distinct practice puzzles behind the examples (about double), at equal exposure.
Test: a panel FIXED BEFORE REGISTRATION (artifacts/claude-brd6-20260926/test_puzzles.jsonl: 240 puzzles, 160 with
3 numbers and 80 with 4, seed 799, no overlap with the 800 practice puzzles or DEV); 30 samples each.

  python -B scripts/claude_brd6.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F --test-puzzles T
  python -B scripts/claude_brd6.py --make-panel --dev-puzzles F --out-panel T
  python -B scripts/claude_brd6.py --selftest
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
import claude_brd5 as R5  # noqa: E402


def matched(ex8, n_passes, seed):
    """ex8 shuffled and repeated in turn to exactly n_passes items (each example once or twice when n_passes < 2x)."""
    rng = random.Random(seed)
    out = []
    while len(out) < n_passes:
        e = list(ex8)
        rng.shuffle(e)
        out += e
    return out[:n_passes]


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    train = B2.puzzles(a.train_seed, a.n_train)
    test = [json.loads(x) for x in Path(a.test_puzzles).read_text().splitlines() if x.strip()]
    banned = R5.banned_keys(a.train_seed, a.n_train, a.dev_puzzles)
    assert not any((tuple(p["nums"]), p["target"]) in banned for p in test), "panel overlaps practice or DEV"
    res.update({"n_train": len(train), "n_test": len(test), "temp": temp,
                "n_test_3num": sum(len(p["nums"]) == 3 for p in test)})
    base = S5.coverage_stream(s, test, a.n, temp)
    res["base"] = S5.summarize(base)
    print(f"[brd6] base {res['base']}", flush=True)
    ex4, ex8, rows = [], [], []
    for i, p in enumerate(train):
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            e, kind = (p, g), "own"
        else:
            hits = [t for t in s.generate(p, a.n, temp) if B1.check(t, p["nums"], p["target"])]
            e, kind = ((p, hits[0]), "win") if hits else (None, "miss")
        rows.append({"puzzle": p, "kind": kind, "answer": e[1] if e else None})
        if e:
            ex8.append(e)
            if i < a.n_half:
                ex4.append(e)
    (out / "practice.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    n_passes = a.epochs * len(ex4)
    ex8m = matched(ex8, n_passes, a.match_seed)
    cnt = lambda k, lo, hi: sum(r["kind"] == k for r in rows[lo:hi])  # noqa: E731
    ln = lambda ex: round(sum(len(x.replace(" ", "")) for _, x in ex) / max(1, len(ex)), 2)  # noqa: E731
    res.update({"W4_examples": len(ex4), "W8_examples": len(ex8), "passes_each": n_passes,
                "W4_own": cnt("own", 0, a.n_half), "W4_wins": cnt("win", 0, a.n_half),
                "W8_own": cnt("own", 0, len(rows)), "W8_wins": cnt("win", 0, len(rows)),
                "W4_mean_len": ln(ex4), "W8_mean_len": ln(ex8),
                "W4_share_3num": round(sum(len(p["nums"]) == 3 for p, _ in ex4) / max(1, len(ex4)), 3),
                "W8_share_3num": round(sum(len(p["nums"]) == 3 for p, _ in ex8) / max(1, len(ex8)), 3),
                "W4_steps": a.epochs * -(-len(ex4) // 8), "W8_steps": -(-len(ex8m) // 8)})
    print(f"[brd6] W4 {len(ex4)} examples, W8 {len(ex8)} examples, {n_passes} passes each", flush=True)
    streams = {}
    for arm, ex, ep in (("W4", ex4, a.epochs), ("W8", ex8m, 1)):
        streams[arm] = []
        for sd in [int(x) for x in a.lora_seeds.split(",")]:
            if not ex:
                res[f"{arm}_seed{sd}"] = None
                continue
            m = B2.train_lora(s, list(ex), ep, sd)
            st = S5.coverage_stream(s, test, a.n, temp, m)
            streams[arm].append(st)
            res[f"{arm}_seed{sd}"] = S5.summarize(st)
            print(f"[brd6] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
    if not all(streams[k] for k in ("W4", "W8")):
        raise SystemExit("W4 or W8 had no examples")
    res["ci95_W8_minus_W4_cov30_pct"] = S5.boot_ci(test, streams["W8"], streams["W4"])
    res["ci95_W4_minus_base_cov30_pct"] = S5.boot_ci(test, streams["W4"], [base])
    res["ci95_W8_minus_base_cov30_pct"] = S5.boot_ci(test, streams["W8"], [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd6_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    ex8 = [(i, str(i)) for i in range(10)]
    m = matched(ex8, 15, 0)
    assert len(m) == 15 and set(m) == set(ex8) and all(1 <= m.count(e) <= 2 for e in ex8)
    assert B2.puzzles(9, 800)[:400] == B2.puzzles(9, 400)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-train", type=int, default=800)
    ap.add_argument("--n-half", type=int, default=400)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--match-seed", type=int, default=799)
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
        ps = R5.make_panel(R5.banned_keys(a.train_seed, a.n_train, a.dev_puzzles), seed=799)
        Path(a.out_panel).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_panel).write_text("".join(json.dumps(p) + "\n" for p in ps), encoding="utf-8")
        print("panel", len(ps), sum(len(p["nums"]) == 3 for p in ps))
    else:
        run(a)


if __name__ == "__main__":
    main()
