#!/usr/bin/env python3
"""Creative's checked-hit supplier for other threads' sleep nights (creative research thread, 2026-09-26; agreed
with Sleep research under Ben's 12:48 UTC integration rule).

For each puzzle {"nums": [...], "target": T}: the frozen 1B (MiniCPM5-1B, thinking off) gives one greedy answer
and n rule-kept blurts at temperature temp (claude_blurt2.Solver + RuleKeeper: only legal expressions over exactly
the given numbers). The exact checker (claude_blurt1.check) keeps the right ones. Output, one JSON line per puzzle:
  {"puzzle": {...}, "greedy": str, "greedy_right": bool, "hits": [distinct right strings, first-found order],
   "first_hit": str | null, "n": n, "temp": temp, "source": "creative-blurt-1B", "checker": "claude_blurt1.check"}
Recipe evidence (brd-5/6/7 VERIFY files): train a night on ONE hit per puzzle (first_hit, or greedy when right),
many different puzzles, never padded by repeating a few. Nothing here trains or saves weights.

  python -B scripts/claude_blurt_supply.py --model M --puzzles IN.jsonl --out OUT.jsonl [--n 30 --temp 1.5]
  python -B scripts/claude_blurt_supply.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402


def supply_one(s, p, n=30, temp=1.5) -> dict:
    g = s.answer(p)
    hits = []
    for t in s.generate(p, n, temp):
        if B1.check(t, p["nums"], p["target"]) and t not in hits:
            hits.append(t)
    return {"puzzle": p, "greedy": g, "greedy_right": bool(B1.check(g, p["nums"], p["target"])), "hits": hits,
            "first_hit": hits[0] if hits else None, "n": n, "temp": temp, "source": "creative-blurt-1B",
            "checker": "claude_blurt1.check"}


def night_examples(rows) -> list:
    """One (puzzle, answer) per puzzle: greedy when right, else the first hit; puzzles with neither are skipped."""
    out = []
    for r in rows:
        a = r["greedy"] if r["greedy_right"] else r["first_hit"]
        if a:
            out.append((r["puzzle"], a))
    return out


def run(a):
    import claude_blurt2 as B2
    s = B2.Solver(a.model)
    ps = [json.loads(x) for x in Path(a.puzzles).read_text().splitlines() if x.strip()]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for i, p in enumerate(ps):
            f.write(json.dumps(supply_one(s, p, a.n, a.temp)) + "\n")
            f.flush()
            if (i + 1) % 20 == 0:
                print(f"[supply] {i + 1}/{len(ps)}", flush=True)


def selftest():
    class Fake:
        def answer(self, p):
            return "1 + 2"

        def generate(self, p, n, temp):
            return ["8 * 3 * 1", "8*3*1", "8 * 3 * 1", "8 + 3 + 1", "(8 - 1) * 3 + 3"][:n]
    p = {"nums": [1, 3, 8], "target": 24}
    r = supply_one(Fake(), p, 5, 1.5)
    assert not r["greedy_right"] and r["hits"] == ["8 * 3 * 1", "8*3*1"] and r["first_hit"] == "8 * 3 * 1", r
    assert night_examples([r]) == [(p, "8 * 3 * 1")]
    assert night_examples([dict(r, greedy_right=True)]) == [(p, "1 + 2")]
    assert night_examples([dict(r, hits=[], first_hit=None)]) == []
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--puzzles", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--temp", type=float, default=1.5)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
