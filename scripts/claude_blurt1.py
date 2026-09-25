#!/usr/bin/env python3
"""blurt-1: how often does MiniCPM5-1B get lucky? (creative research thread, 2026-09-25)

Ben (00:39 UTC): "The point is to emulate the part of the brain that says random stuff then gets filtered out ...
It's stupid where it comes up with solutions, but gets lucky when its right. The point is for us to maximize the
number of times it gets lucky." He chose to test the blurt-then-judge engine on both ideas and puzzles.

This file is the measurement only (no judge, no training): N blurts per task from the base 1B, thinking off.
  puzzles: number puzzles (use each given number once with + - * / and brackets to hit the target), made by code
           with a brute-force solvability check; an exact checker marks every blurt right or wrong.
  ideas:   one short idea per blurt for a DEV creative request (artifacts/claude-cre333e-dev-20260924); a blind
           judge labels them afterwards.

  python -B scripts/claude_blurt1.py make   --out DIR --n 60 --seed 1           puzzles.jsonl (DEV seed 1)
  python -B scripts/claude_blurt1.py puzzle --model M --puzzles F --out F --n 30 [--temp 1.0]
  python -B scripts/claude_blurt1.py ideas  --model M --dev DIR --out F --n 30 [--limit 10] [--temp 1.1]
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import random
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OPS = ["+", "-", "*", "/"]


def _combine(a, b):
    out = [(a[0] + b[0], f"({a[1]}+{b[1]})"), (a[0] - b[0], f"({a[1]}-{b[1]})"),
           (b[0] - a[0], f"({b[1]}-{a[1]})"), (a[0] * b[0], f"({a[1]}*{b[1]})")]
    if b[0] != 0:
        out.append((a[0] / b[0], f"({a[1]}/{b[1]})"))
    if a[0] != 0:
        out.append((b[0] / a[0], f"({b[1]}/{a[1]})"))
    return out


def solve(nums, target):
    """One solution expression or None (brute force over all pairings)."""
    def rec(items):
        if len(items) == 1:
            return items[0][1] if items[0][0] == target else None
        for i, j in itertools.combinations(range(len(items)), 2):
            rest = [items[k] for k in range(len(items)) if k not in (i, j)]
            for v in _combine(items[i], items[j]):
                s = rec(rest + [v])
                if s:
                    return s
        return None
    return rec([(Fraction(n), str(n)) for n in nums])


def make(a):
    rng, out, seen = random.Random(a.seed), [], set()
    while len(out) < a.n:
        k = 3 if len(out) % 3 else 4              # two thirds 3-number puzzles (the 1B scored 0/180 on 4-number ones)
        nums = sorted(rng.randint(1, 9 if k == 3 else 13) for _ in range(k))
        target = 24 if k == 4 else rng.randint(5, 40)
        key = (tuple(nums), target)
        if key in seen:
            continue
        sol = solve(nums, target)
        if sol is None:
            continue
        seen.add(key)
        out.append({"id": f"pz-s{a.seed}-{len(out) + 1:03d}", "nums": nums, "target": target, "solution": sol})
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "puzzles.jsonl").write_text("".join(json.dumps(p) + "\n" for p in out), encoding="utf-8")
    print(f"made {len(out)} puzzles (seed {a.seed})")


def check(expr: str, nums, target) -> bool:
    expr = expr.strip().rstrip(".").replace("×", "*").replace("x", "*").replace("÷", "/")
    expr = expr.split("=")[0].strip()
    if not expr or not re.fullmatch(r"[\d+\-*/() .]+", expr):
        return False
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return False
    used = []

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            used.append(n.value)
            return Fraction(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            x, y = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return x + y
            if isinstance(n.op, ast.Sub):
                return x - y
            if isinstance(n.op, ast.Mult):
                return x * y
            if y == 0:
                raise ZeroDivisionError
            return x / y
        raise ValueError("bad node")
    try:
        val = ev(tree)
    except (ValueError, ZeroDivisionError):
        return False
    return sorted(used) == sorted(nums) and val == target


def puzzle_prompt(p) -> list[dict]:
    ns = ", ".join(str(n) for n in p["nums"])
    return [{"role": "user", "content": f"Use each of the numbers {ns} exactly once, with + - * / and brackets, to make "
                                        f"{p['target']}. Reply with only the expression, nothing else."}]


def extract_expr(t: str) -> str:
    t = t.replace("`", "").replace("$", "").replace("\\times", "*").replace("\\div", "/")
    for line in t.splitlines():
        m = re.search(r"[\d(][\d+\-*/()×x÷ .]*[\d)]", line)
        if m and any(o in m.group(0) for o in "+-*/×x÷"):
            return m.group(0)
    return ""


class Blurter:
    def __init__(self, model_dir, temp, max_new):
        import claude_cre333b_agent as CB
        self.g = CB.Gen333b(model_dir)
        self.temp, self.max_new = temp, max_new

    def sample(self, msgs, n):
        g = self.g
        s = g.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = g.tok(s, return_tensors="pt").to(g.dev)
        with g.torch.no_grad():
            out = g.model.generate(**ids, max_new_tokens=self.max_new, do_sample=True, temperature=self.temp,
                                   top_p=1.0, num_return_sequences=n, pad_token_id=g.tok.eos_token_id)
        cut = ids["input_ids"].shape[1]
        return [g.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]


def puzzle(a):
    b = Blurter(a.model, a.temp, 40)
    rows = []
    for p in [json.loads(x) for x in Path(a.puzzles).read_text().splitlines() if x]:
        bl = b.sample(puzzle_prompt(p), a.n)
        hits = [check(extract_expr(t), p["nums"], p["target"]) for t in bl]
        rows.append({"id": p["id"], "blurts": bl, "hits": hits})
        print(f"[blurt1/puzzle] {p['id']} hits {sum(hits)}/{a.n}", flush=True)
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    tot = sum(sum(r["hits"]) for r in rows)
    print(f"puzzles {len(rows)}: lucky blurts {tot}/{len(rows) * a.n}, solved at least once "
          f"{sum(1 for r in rows if any(r['hits']))}/{len(rows)}")


SYSTEM_IDEA = ("You are a playful, imaginative assistant. Blurt ONE quick, specific idea for the user's request, in one "
               "or two sentences. Be bold and unusual; a wild guess is fine. No lists, no questions, no preamble.")


def ideas(a):
    b = Blurter(a.model, a.temp, 60)
    items = [json.loads(x) for x in (Path(a.dev) / "items.jsonl").read_text().splitlines() if x]
    items = [it for it in items if it["kind"] == "creative"][: a.limit or None]
    rows = []
    for it in items:
        msgs = [{"role": "system", "content": SYSTEM_IDEA}] + [{"role": "user", "content": t} for t in it["turns"]] + \
               [{"role": "user", "content": it["last"]}]
        bl = [re.sub(r"\s+", " ", t)[:400] for t in b.sample(msgs, a.n)]
        rows.append({"item_id": it["item_id"], "blurts": bl})
        print(f"[blurt1/ideas] {it['item_id']}", flush=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make", "puzzle", "ideas"])
    ap.add_argument("--model", default="")
    ap.add_argument("--puzzles", default="")
    ap.add_argument("--dev", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--temp", type=float, default=1.0)
    a = ap.parse_args()
    {"make": make, "puzzle": puzzle, "ideas": ideas}[a.cmd](a)


if __name__ == "__main__":
    main()
