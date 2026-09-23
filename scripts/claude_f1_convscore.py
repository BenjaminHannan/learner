#!/usr/bin/env python3
"""Exp F1 convbench-f0 mechanical comparison (no grading, no judge).

New file only. Compares the two registered arm outputs turn by turn:
  artifacts/claude-f1-20260923/run/conv292t.jsonl (arm A)
  artifacts/claude-f1-20260923/run/convf1.jsonl   (arm B)
Writes artifacts/claude-f1-20260923/run/changed-lines.jsonl with EVERY
changed reply line: {dialog_id, turn_index, armA, armB} where armA is the
292t text and armB the F1 text. Quoting agent replies is fine; benchmark
user turns are never read here (only dialog/turn ids) and never printed.

Also checks M2 store parity: per-turn notebook_events counts and
stored_triples must be identical between arms (any diff listed by id).
Prints integer counts only.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_f1_convscore.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "artifacts/claude-f1-20260923/run"
A = RUN / "conv292t.jsonl"
B = RUN / "convf1.jsonl"
OUT = RUN / "changed-lines.jsonl"


def load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()]


def main() -> int:
    ra = load(A)
    rb = load(B)
    ka = {(r.get("dialog_id"), r.get("turn_index")): r for r in ra}
    kb = {(r.get("dialog_id"), r.get("turn_index")): r for r in rb}
    ids = sorted(set(ka) | set(kb), key=lambda k: (str(k[0]), k[1]))
    n_changed = n_store = n_ev = n_miss = 0
    changed = []
    store_ids = []
    ev_ids = []
    for k in ids:
        a, b = ka.get(k), kb.get(k)
        if a is None or b is None:
            n_miss += 1
            continue
        if str(a.get("reply", "")) != str(b.get("reply", "")):
            n_changed += 1
            changed.append({"dialog_id": k[0], "turn_index": k[1],
                            "armA": str(a.get("reply", "")),
                            "armB": str(b.get("reply", ""))})
        if a.get("stored_triples") != b.get("stored_triples"):
            n_store += 1
            store_ids.append(f"{k[0]}#{k[1]}")
        if len(a.get("notebook_events", [])) != len(b.get("notebook_events", [])):
            n_ev += 1
            ev_ids.append(f"{k[0]}#{k[1]}")
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                           for r in changed), encoding="utf-8")
    res = {"n_turns": len(ids), "n_changed_lines": n_changed,
           "n_store_diff_turns": n_store, "store_ids": store_ids,
           "n_event_count_diff_turns": n_ev, "ev_ids": ev_ids,
           "n_join_miss": n_miss}
    (RUN / "convscore.json").write_text(json.dumps(res, indent=1),
                                        encoding="utf-8")
    print(f"turns={len(ids)} changed_lines={n_changed} "
          f"store_diff={n_store} ev_diff={n_ev} join_miss={n_miss}")
    print(f"wrote {OUT} + {RUN / 'convscore.json'}")
    for s in store_ids:
        print("STORE-DIFF:", s)
    for s in ev_ids:
        print("EV-DIFF:", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
