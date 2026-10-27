#!/usr/bin/env python3
"""gr-5 report line (ADDENDUM-gr5-1; Plain-English puzzles thread, 2026-09-26): the held-out dev squares split by
whether their 1B wrapper also wraps a training square. Practice data only; report only; it gates nothing.

A message's wrapper is its lines that hold no digit (the square's lines all hold digits). A held-out square is "shared"
when that wrapper text equals the wrapper of any training square, else "clean". The copy is claude_gr5.Copier5 with the
trained adapter, exactly as `claude_gr5.py dev` runs it.

  python -B scripts/claude_gr5_devclean.py --selftest
  python -B scripts/claude_gr5_devclean.py --model BASE --rows ROWS.jsonl --adapter ADAPTER.pt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr5 as G5  # noqa: E402


def wrapper(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not re.search(r"\d", ln)).strip()


def split(rows):
    train = {wrapper(r["text"]) for r in rows if r["split"] == "train" and r["grid"] is not None}
    dev = [r for r in rows if r["split"] == "dev" and r["grid"] is not None]
    return [("shared" if wrapper(r["text"]) in train else "clean", r) for r in dev]


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        rows = G5._load(G5.ROOT / "artifacts/claude-gr5-20260926/train/rows.jsonl")
        c = Counter(k for k, _ in split(rows))
        assert (c["clean"], c["shared"]) == (53, 19), c
        print("gr5 devclean selftest 1/1 (clean 53, shared 19)")
        return
    ap = argparse.ArgumentParser()
    for k in ("model", "rows", "adapter"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    items = split(G5._load(a.rows))
    cp = G5.Copier5(G5.load(a.model, a.adapter), plain=False)
    st = Counter()
    for kind, r in items:
        g = cp.copy(r["text"])["grid"]
        st[kind + "_n"] += 1
        st[kind + "_exact"] += int(g == r["grid"])
        st[kind + "_wrong"] += int(g is not None and g != r["grid"])
        st[kind + "_none"] += int(g is None)
    print(json.dumps(dict(sorted(st.items()))))


if __name__ == "__main__":
    main()
