#!/usr/bin/env python3
"""gr-3 step 1 (Plain-English puzzles thread, 2026-09-26): the plain 1B (every LoRA scale 0) writes chat messages that
share a small table of numbers. They teach gr-3's learned glance what a number table that is not a puzzle square looks
like. Every training word and number is the 1B's. The label is made by code: the size of the square that the reading
definition (claude_puzzle_reader.read_latin) finds in the message, or none. No label comes from what the 1B was asked
to write. Nothing here is written by Claude except the instructions to the 1B, and those are never training text.
Never reads any TEST panel.

  HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 python -B scripts/claude_gr3_drafts.py --model BASE --out FILE.jsonl
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

SEED = 4960
STYLES = [
    "Write a short chat message to a friend that shares {topic} as a small table of numbers, one row per line. Write "
    "only the message.",
    "Write a quick text that pastes a few rows of numbers about {topic}, with a short note before them. Write only the "
    "message.",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args()
    import torch
    import claude_cre333b_agent as C
    import claude_puzzle_reader as R
    import claude_rt02h_drafts as D
    g = C.Gen333b(a.model, max_new=160)
    out = Path(a.out)
    t0 = time.time()
    k = 0
    for topic in D.TOPICS:
        for si, st in enumerate(STYLES):
            torch.manual_seed(SEED * 1000 + k)
            rows = []
            for s in g.sample(st.format(topic=topic), a.n):
                t = s.strip()
                lines_with_digits = sum(bool(re.search(r"\d", ln)) for ln in t.splitlines())
                sq = R.read_latin(t)
                rows.append({"k": k, "topic": topic, "style": si, "text": t,
                             "keep": lines_with_digits >= 3 and len(t) <= 700,
                             "size": None if sq is None else sq["size"]})
            with out.open("a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            print(k, sum(r["keep"] for r in rows), round(time.time() - t0), flush=True)
            k += 1


if __name__ == "__main__":
    main()
