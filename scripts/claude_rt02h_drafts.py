#!/usr/bin/env python3
"""rt-02h prototype, step 1 (Plain-English puzzles thread, 2026-09-26; dev only, not registered): the plain 1B writes its
own chat messages, and code labels them. These drafts are training data for a small yes/no head on the 1B's inner state
("is this message asking for a number puzzle?"). The 1B already copies the numbers and target out well once it is told
a message is a puzzle; see artifacts/claude-rt02g-20260926/WITHDRAWN-rt02g.md.

Rules: every text here is written by the 1B (every LoRA scale 0), never by Claude. The prompts below are instructions to
the 1B, not training text. Labels come from which prompt produced the draft, checked by code:
  pos   asked to write a puzzle request; kept if its whole numbers are exactly the puzzle's numbers + target and it
        does not state a worked sum (claude_rt02e.states_sum)
  neg   asked to write an everyday message that mentions the same numbers; kept if it has 4-5 whole numbers
  hard  asked to share a solution, check a sum or ask a plain sum; kept if it has 4-5 whole numbers
Only drafts with 4-5 whole numbers are kept, because only those ever reach the reader. Puzzles use seed 4810, which is
not a TEST seed (4797, 4799) or a dev/practice seed (4880, 4881); the same numbers feed pos, neg and hard drafts, so
the head must learn what is asked, not which numbers appear. Never reads any TEST panel.

  HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 python -B scripts/claude_rt02h_drafts.py --model BASE --out FILE.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED = 4810
POS = [
    "Write one short chat message asking a friend to combine {L} with + - * / (each number used once) to make {T}. "
    "Write only the message.",
    "Write one short, casual text asking for help: how can {L} make {T} using add, subtract, multiply or divide? "
    "Write only the message.",
    "Write a one-line message asking someone to reach {T} using the numbers {L}, each exactly once. Write only the message.",
    "Write a short message challenging a friend to get {T} out of {L} with any arithmetic. Write only the message.",
    "Write a short question asking for an expression that uses {L} once each and equals {T}. Write only the message.",
    "Write a very short text, typed quickly like a teenager, asking how to make {T} from {L}. Write only the message.",
]
TOPICS = ["your kids' ages", "a meeting schedule", "hotel room numbers", "a recipe", "your team's scores",
          "a shopping list", "a door or lock code", "prices at a shop", "test marks", "a bus timetable", "a workout plan",
          "seats at a concert", "a birthday party", "your pets", "saving money", "chapters you must read", "your garden",
          "a board game night"]
NEG = ("Write one short chat message to a friend about {topic}. It must mention these numbers: {A}. "
       "Do not ask for any maths. Write only the message.")
HARD = [
    "Write one short chat message telling a friend you solved a number puzzle: you made {T} from {L}. "
    "Write only the message.",
    "Write one short chat message asking a friend whether {E} really equals {V}. Write only the message.",
    "Write one short chat message asking what {S} adds up to. Write only the message.",
]


def lst(nums):
    return ", ".join(map(str, nums[:-1])) + " and " + str(nums[-1])


def prompts():
    import claude_blurt2 as B2
    rng = random.Random(SEED)
    ps = B2.puzzles(SEED, 96)          # the same puzzles' numbers appear in pos, neg and hard drafts
    out = []
    for i, p in enumerate(ps[:96]):
        nums = list(p["nums"])
        rng.shuffle(nums)
        out.append(("pos", i % len(POS), POS[i % len(POS)].format(L=lst(nums), T=p["target"]), p))
    for i, p in enumerate(ps[:54]):
        nums = list(p["nums"])
        rng.shuffle(nums)
        topic = TOPICS[i % len(TOPICS)]
        out.append(("neg", topic, NEG.format(topic=topic, A=", ".join(map(str, nums + [p["target"]]))), p))
    for i, p in enumerate(ps[54:84]):
        nums = list(p["nums"])
        k = i % len(HARD)
        if k == 1:
            a, b, c = nums[:3]
            e, v = f"{a} + {b} * {c}", a + b * c
            out.append(("hard", k, HARD[1].format(E=e, V=v), p))
        elif k == 2:
            s = " + ".join(map(str, nums + [rng.randint(1, 9)] * (4 - len(nums)))) if len(nums) < 4 else " + ".join(map(str, nums))
            out.append(("hard", k, HARD[2].format(S=s), p))
        else:
            out.append(("hard", k, HARD[0].format(T=p["target"], L=lst(nums)), p))
    return out


def label(kind, text, p) -> bool:
    import claude_rt02e as RE
    import claude_rt02g as G
    if not G.pre_gate(text):
        return False
    if kind == "pos":
        return Counter(G.message_ints(text)) == Counter(list(p["nums"]) + [p["target"]]) and not RE.states_sum(text)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()
    import torch
    import claude_cre333b_agent as C
    g = C.Gen333b(a.model, max_new=70)
    out = Path(a.out)
    done = {json.loads(x)["pi"] for x in out.read_text().splitlines()} if out.exists() else set()
    t0 = time.time()
    for pi, (kind, style, prompt, p) in enumerate(prompts()):
        if pi in done:
            continue
        torch.manual_seed(SEED * 1000 + pi)
        rows = []
        for s in g.sample(prompt, a.n):
            rows.append({"pi": pi, "kind": kind, "style": style, "nums": p["nums"], "target": p["target"],
                         "text": s, "keep": label(kind, s, p)})
        with out.open("a", encoding="utf-8") as f:
            f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(pi, kind, sum(r["keep"] for r in rows), round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
