#!/usr/bin/env python3
"""gr-1 step 1 (Plain-English puzzles thread, 2026-09-26): the plain 1B (every LoRA scale 0) writes the words people
put around a number square. The grid reader is trained on these words with code-built squares placed between them.
Every training word is the 1B's; code builds the squares and the labels. Nothing here is written by Claude except the
instructions to the 1B, and those are never training text. Never reads any TEST panel.

  HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 python -B scripts/claude_gr1_drafts.py --model BASE --out FILE.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED = 4860
PROMPTS = {
    "opener": [
        "Write one short chat message asking a friend to help fill in the blanks of a number square, where each row "
        "and each column must use every number once. Do not write the square itself. Write only the message.",
        "Write a casual text asking for help with a grid puzzle you are stuck on. Do not write the grid. Write only "
        "the message.",
        "Write one polite message asking someone to complete a Latin square puzzle that you will paste below. Do not "
        "write the puzzle. Write only the message.",
        "Write a very short, quickly typed message asking someone to solve the puzzle under it. Write only the message.",
        "Write a message from a parent asking for help with their child's number grid homework. Do not write the grid. "
        "Write only the message.",
    ],
    "closer": [
        "Write one short sentence thanking someone in advance for helping with a puzzle. Write only the sentence.",
        "Write one short question asking someone to show the finished grid. Write only the question.",
        "Write one short sentence saying the blanks are marked with underscores. Write only the sentence.",
    ],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=10)
    a = ap.parse_args()
    import torch
    import claude_cre333b_agent as C
    import claude_rt02h_drafts as D
    g = C.Gen333b(a.model, max_new=60)
    out = Path(a.out)
    t0 = time.time()
    k = 0
    for rnd in range(a.rounds):
        for kind, ps in PROMPTS.items():
            if kind == "closer" and rnd % 2:
                continue
            for pi, p in enumerate(ps):
                torch.manual_seed(SEED * 1000 + k)
                rows = []
                for s in g.sample(p, a.n):
                    t = D.first_para(s)
                    rows.append({"k": k, "kind": kind, "pi": pi, "text": t, "raw": s,
                                 "keep": bool(t) and not re.search(r"\d", t) and len(t) <= 400})
                with out.open("a", encoding="utf-8") as f:
                    f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
                print(k, kind, sum(r["keep"] for r in rows), round(time.time() - t0), flush=True)
                k += 1


if __name__ == "__main__":
    main()
