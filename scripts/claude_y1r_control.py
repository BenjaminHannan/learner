#!/usr/bin/env python3
"""y1r control row: shuffled pairs (Answering-from-memory thread, 2026-09-26). New file; claude_y1r_retriever.py stays
as sealed. Rule: artifacts/claude-y1r-20260926/ADDENDUM-1-review.md (the Thread manager's review, 19:39 UTC).

Each query is moved to another pair from a different chat (a seeded shuffle with no query left in its own chat);
positives and negatives stay where they are. The control MiniLM is then trained with claude_y1r_retriever.py train,
same recipe, on these pairs. It sees the same questions and the same turns, but which turn answers which question is
random. If it gains on LoCoMo as much as y1r, y1r's gain is adaptation to the text format, not learning what a
question points to. Report only.

  python -B scripts/claude_y1r_control.py shuffle --pairs PAIRS.jsonl --out CONTROL.jsonl [--seed 4037]
  python -B scripts/claude_y1r_control.py --selftest
Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SEED = 4037


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def shuffle(prs: list[dict], seed: int = SEED, tries: int = 1000) -> tuple[list[dict], dict]:
    rng = random.Random(seed)
    for _ in range(tries):
        order = list(range(len(prs)))
        rng.shuffle(order)
        if all(prs[i]["dialog_id"] != prs[j]["dialog_id"] for i, j in enumerate(order)):
            out = [p | {"query": prs[j]["query"], "control_from": [prs[j]["dialog_id"], prs[j]["k"]]}
                   for p, j in zip(prs, order)]
            return out, {"pairs": len(out), "own_chat_queries": 0}
    raise RuntimeError("no shuffle without a query in its own chat")


def selftest() -> None:
    prs = [{"dialog_id": f"d{i // 2}", "k": i, "query": f"q{i}", "pos": [f"p{i}"], "neg": [f"n{i}"]} for i in range(10)]
    out, c = shuffle(prs)
    assert c == {"pairs": 10, "own_chat_queries": 0}
    assert sorted(p["query"] for p in out) == sorted(p["query"] for p in prs)
    assert [p["pos"] for p in out] == [p["pos"] for p in prs] and [p["neg"] for p in out] == [p["neg"] for p in prs]
    assert all(int(p["query"][1:]) // 2 != int(p["dialog_id"][1:]) for p in out)
    assert shuffle(prs)[0] == out                                      # seeded
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shuffle")
    s.add_argument("--pairs", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args()
    out, c = shuffle(load(a.pairs), a.seed)
    Path(a.out).write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in out), encoding="utf-8")
    print(json.dumps(c))


if __name__ == "__main__":
    main()
