#!/usr/bin/env python3
"""blurt-4: hindsight hits. A wrong guess still makes SOME number, so it is a correct answer to another puzzle.
(creative research thread, 2026-09-25; Ben 17:54 UTC "do you think you have some good work you can do")

Why (reviews/creative-research-2026-09-25/B-feedback-kinds.md): in Hindsight Experience Replay (Andrychowicz et al.
2017) distance-shaped rewards solved nothing, while replaying each failure as a success for the goal it actually
reached worked. Ben (16:11 UTC) rejected "22 is close to 24" as warmth; this uses the 22 exactly instead: a blurt that
makes 22 from the puzzle's numbers is an exact, checked answer to "make 22 from these numbers".

One change from blurt-3 (claude_blurt2.py loop --luck, arm W): sleep also practises hindsight hits.
  H = own right answers + first lucky hit per won puzzle (= blurt-3 W) + one hindsight hit per practice puzzle
      (the first complete legal blurt whose exact value v is a whole number 1-60 and v != target, relabelled as the
      puzzle "make v"; checked with the same exact checker).
  W = blurt-3 W, padded to H's size by repeating its own examples (more examples alone is not the change).
  P (placebo) = W's examples + the SAME hindsight blurts, relabelled with a WRONG target (v + 1, or v - 1 at 60), so
      H and P differ only in whether the relabelled answer is right.
Measure: lucky blurts on fresh test puzzles (30 each, the DEV temperature rule), as in blurt-3.

  python -B scripts/claude_blurt4.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F --train-seed 8
      --test-seed 783 --n-test 80
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402

VMAX = 60


def value(expr: str):
    """Exact value of a legal expression (Fraction), or None (division by zero, bad syntax)."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        return None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return Fraction(n.value)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(n.left), ev(n.right)
            if a is None or b is None:
                return None
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            return None if b == 0 else a / b
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            v = ev(n.operand)
            return None if v is None else -v
        return None
    return ev(tree)


def hindsight(p, blurts):
    """First complete legal blurt that misses but makes a whole number 1..VMAX: (relabelled puzzle, expr, v)."""
    for t in blurts:
        if not B2.complete(t, p["nums"]):
            continue
        v = value(t)
        if v is None or v.denominator != 1 or not 1 <= v <= VMAX or v == p["target"]:
            continue
        q = {"id": p["id"] + f"-h{int(v)}", "nums": p["nums"], "target": int(v)}
        if B1.check(t, q["nums"], q["target"]):
            return q, t, int(v)
    return None


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
    res.update({"n_train": len(train), "n_test": len(test), "test_dropped_overlap": n0 - len(test), "temp": temp})
    res["S0_test_before"] = B2.evaluate(s, test)
    res["L0_lucky_blurts"], res["L0_puzzles_hit"] = B2.luck(s, test, a.n, temp)
    print(f"[b4] before: test {res['S0_test_before']}/{len(test)}, luck {res['L0_lucky_blurts']}", flush=True)
    own, wins, hind, wrong_h, lucky, tried = [], [], [], [], 0, 0
    test_keys = {(tuple(p["nums"]), p["target"]) for p in test}
    for p in train:
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            own.append((p, g))
            continue
        bl = s.generate(p, a.n, temp)
        hits = [t for t in bl if B1.check(t, p["nums"], p["target"])]
        lucky, tried = lucky + len(hits), tried + len(bl)
        if hits:
            wins.append((p, hits[0]))
        h = hindsight(p, bl)
        if h and (tuple(h[0]["nums"]), h[0]["target"]) not in test_keys:   # never practise a test puzzle
            q, t, v = h
            hind.append((q, t))
            wt = v + 1 if v < VMAX else v - 1
            wrong_h.append(({"id": p["id"] + f"-x{wt}", "nums": p["nums"], "target": wt}, t))
    res.update({"train_reasoner_right": len(own), "train_missed": len(train) - len(own),
                "train_missed_then_lucky": len(wins), "lucky_blurts_on_misses": lucky, "blurts_on_misses": tried,
                "hindsight_hits": len(hind)})
    print(f"[b4] practice: own {len(own)}, wins {len(wins)}, hindsight {len(hind)}", flush=True)
    base = own + wins
    ex_h = base + hind
    ex_w = (base * (len(ex_h) // max(1, len(base)) + 1))[:len(ex_h)] if base else []
    ex_p = base + wrong_h
    res["examples_H"], res["examples_W"], res["examples_P"] = len(ex_h), len(ex_w), len(ex_p)
    seeds = [int(x) for x in a.lora_seeds.split(",")]
    for arm, ex in (("W", ex_w), ("H", ex_h), ("P", ex_p)):
        for sd in seeds:
            k = f"{arm}_seed{sd}"
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            res[f"S_{k}_test_after"] = B2.evaluate(s, test, m)
            res[f"L_{k}_lucky_blurts"], res[f"L_{k}_puzzles_hit"] = B2.luck(s, test, a.n, temp, m)
            print(f"[b4] {arm} seed {sd}: luck {res[f'L_{k}_lucky_blurts']}, test {res[f'S_{k}_test_after']}",
                  flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
        vals = [res[f"L_{arm}_seed{sd}_lucky_blurts"] for sd in seeds]
        res[f"L_{arm}_mean"] = round(sum(vals) / len(vals), 2)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "blurt4_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    assert value("(8-2)*4") == 24 and value("3/0") is None and value("7/2") == Fraction(7, 2)
    p = {"id": "t", "nums": [2, 4, 8], "target": 24}
    q, t, v = hindsight(p, ["(8-2", "8/4/2", "8+4*2"])     # 8/4/2 = 1 -> "make 1"; incomplete skipped
    assert (v, t, q["target"]) == (1, "8/4/2", 1) and B1.check(t, q["nums"], q["target"])
    assert hindsight(p, ["8*4-2*4"]) is None                  # not a legal use of the numbers
    assert hindsight({"id": "t", "nums": [3, 8], "target": 24}, ["3*8"]) is None   # a hit is not hindsight
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=8)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--test-seed", type=int, default=783)
    ap.add_argument("--n-test", type=int, default=80)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1")
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        run(a)


if __name__ == "__main__":
    main()
