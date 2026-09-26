#!/usr/bin/env python3
"""brd-8: does a second round of practice help more when the SLEPT model collects its hits? (creative research
thread, 2026-09-26; problem 7, turning lucky hits into lasting skill; follow-up to brd-5/6/7)

Why: one night of sleep on the model's own checked hits (W) beat no sleep in brd-5, 6 and 7, but cleared +24 of 240
only once. Ben's loop is meant to repeat: tomorrow's practice is done by the model that slept tonight, so its lucky
hits land on harder puzzles. This tests whether that compounding is real.

Practice: A = puzzles(seed 9, 800)[:400] (brd-5's set), B = puzzles(seed 9, 800)[400:] (brd-6's second half).
Round 1 (shared): the base model practises A (greedy, then 30 rule-kept blurts at the DEV temperature on a miss,
first hit wins); M1 = LoRA on those examples (seed s, 3 epochs; brd-5's W).
Round 2, two arms, ONE change = which model practises B:
- ITER: M1 practises B.
- CTRL: the base model practises B (computed once).
Each arm then trains a fresh LoRA from the base model on (round-1 examples + its round-2 examples) for EXACTLY the
same number of example passes: 3 x (round-1 examples + CTRL's round-2 examples), the arm's examples shuffled and
repeated in turn to that length, one pass (claude_brd6.matched). So exposure is equal; only the source of round-2
hits differs. LoRA seeds 0/1/2 (M1 seed s feeds ITER seed s).
Test: a panel FIXED BEFORE REGISTRATION (artifacts/claude-brd8-20260926/test_puzzles.jsonl); 30 samples each.

  python -B scripts/claude_brd8.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F --test-puzzles T
  python -B scripts/claude_brd8.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_blurt5s as S5  # noqa: E402
import claude_brd6 as R6  # noqa: E402


def gather(s, ps, n, temp, model=None):
    """(examples, rows): greedy answer when right, else the first of n checked blurts; misses give nothing."""
    ex, rows = [], []
    for p in ps:
        g = s.answer(p, model)
        if B1.check(g, p["nums"], p["target"]):
            ex.append((p, g))
            rows.append({"puzzle": p, "kind": "own", "answer": g})
            continue
        hits = [t for t in s.generate(p, n, temp, model) if B1.check(t, p["nums"], p["target"])]
        if hits:
            ex.append((p, hits[0]))
        rows.append({"puzzle": p, "kind": "win" if hits else "miss", "answer": hits[0] if hits else None})
    return ex, rows


def counts(rows):
    return {k: sum(r["kind"] == k for r in rows) for k in ("own", "win", "miss")}


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    prac = B2.puzzles(a.train_seed, 2 * a.n_half)
    pa, pb = prac[:a.n_half], prac[a.n_half:]
    test = [json.loads(x) for x in Path(a.test_puzzles).read_text().splitlines() if x.strip()]
    keys = {(tuple(p["nums"]), p["target"]) for p in prac}
    if a.dev_puzzles:
        keys |= {(tuple(p["nums"]), p["target"]) for p in
                 (json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x.strip())}
    assert not any((tuple(p["nums"]), p["target"]) in keys for p in test), "panel overlaps practice or DEV"
    res.update({"n_test": len(test), "temp": temp, "n_test_3num": sum(len(p["nums"]) == 3 for p in test)})
    base = S5.coverage_stream(s, test, a.n, temp)
    res["base"] = S5.summarize(base)
    print(f"[brd8] base {res['base']}", flush=True)
    ex_a, rows_a = gather(s, pa, a.n, temp)
    ex_bc, rows_bc = gather(s, pb, a.n, temp)
    n_passes = a.epochs * (len(ex_a) + len(ex_bc))
    res.update({"round1": counts(rows_a), "round2_ctrl": counts(rows_bc), "passes_each": n_passes})
    print(f"[brd8] round1 {res['round1']} round2 CTRL {res['round2_ctrl']} passes {n_passes}", flush=True)
    log = {"round1": rows_a, "round2_ctrl": rows_bc}
    streams = {"ITER": [], "CTRL": []}
    for sd in [int(x) for x in a.lora_seeds.split(",")]:
        m1 = B2.train_lora(s, list(ex_a), a.epochs, sd)
        ex_bi, rows_bi = gather(s, pb, a.n, temp, m1)
        del m1
        if s.dev == "cuda":
            s.torch.cuda.empty_cache()
        res[f"round2_iter_seed{sd}"] = counts(rows_bi)
        log[f"round2_iter_seed{sd}"] = rows_bi
        print(f"[brd8] seed {sd} round2 ITER {res[f'round2_iter_seed{sd}']}", flush=True)
        for arm, exb in (("ITER", ex_bi), ("CTRL", ex_bc)):
            ex = R6.matched(ex_a + exb, n_passes, a.match_seed + sd)
            m = B2.train_lora(s, ex, 1, sd)
            st = S5.coverage_stream(s, test, a.n, temp, m)
            streams[arm].append(st)
            res[f"{arm}_seed{sd}"] = S5.summarize(st) | {"examples": len(ex_a) + len(exb)}
            print(f"[brd8] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
        (out / "practice.json").write_text(json.dumps(log), encoding="utf-8")
    res["ci95_ITER_minus_CTRL_cov30_pct"] = S5.boot_ci(test, streams["ITER"], streams["CTRL"])
    res["ci95_ITER_minus_base_cov30_pct"] = S5.boot_ci(test, streams["ITER"], [base])
    res["ci95_CTRL_minus_base_cov30_pct"] = S5.boot_ci(test, streams["CTRL"], [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd8_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    class Fake:
        def answer(self, p, model=None):
            return "1 + 2" if p["target"] == 3 else "9"

        def generate(self, p, n, temp, model=None):
            return ["1 * 2", "2 * 1"][:n] if p["target"] == 2 else ["9"] * n
    ps = [{"nums": [1, 2], "target": 3}, {"nums": [1, 2], "target": 2}, {"nums": [1, 2], "target": 7}]
    ex, rows = gather(Fake(), ps, 2, 1.5)
    assert [e[1] for e in ex] == ["1 + 2", "1 * 2"] and counts(rows) == {"own": 1, "win": 1, "miss": 1}
    p8 = B2.puzzles(9, 800)
    assert p8[:400] == B2.puzzles(9, 400) and len({(tuple(p["nums"]), p["target"]) for p in p8}) == 800
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-half", type=int, default=400)
    ap.add_argument("--test-puzzles", default="")
    ap.add_argument("--match-seed", type=int, default=801)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
