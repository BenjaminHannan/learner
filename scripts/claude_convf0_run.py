#!/usr/bin/env python3
"""convbench-f0 baseline runner on base 292 (step F0).

New file only. Runs each dialog once, in order, with a fresh 292 agent
per dialog (build_agent292 + DEFAULT_CONFIG292, read-only imports).
CPU only. No agent code changes.

Input: artifacts/claude-convbench-f0-20260923/dialogs.jsonl
  One JSON object per line with keys: dialog_id, turn_index,
  user_text (or user), kind, gold.
  Empty text stops with an error (nonzero exit).

Output: artifacts/claude-convf0-20260923/run/base292.jsonl
  One JSON object per turn with: dialog_id, turn_index, reply,
  notebook_events (new loop.nb.events appended during this turn),
  stored_triples (L90.notebook_triples after this turn).

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_convf0_run.py
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

BENCH = ROOT / "artifacts/claude-convbench-f0-20260923/dialogs.jsonl"
OUT = ROOT / "artifacts/claude-convf0-20260923/run/base292.jsonl"


def get_text(item: dict) -> str:
    if "user_text" in item:
        return item["user_text"]
    if "user" in item:
        return item["user"]
    raise SystemExit("convf0_run: turn missing user_text/user key")


def main() -> int:
    import claude_loop292_agent as A292
    import fable_loop90_agent as L90

    items = [json.loads(x) for x in BENCH.read_text(encoding="utf-8").splitlines() if x.strip()]
    # Group by dialog_id preserving first-seen order; turns in file order.
    order: list[str] = []
    by_dialog: dict[str, list[dict]] = {}
    for it in items:
        did = it.get("dialog_id")
        if not did:
            raise SystemExit("convf0_run: turn missing dialog_id")
        if did not in by_dialog:
            by_dialog[did] = []
            order.append(did)
        by_dialog[did].append(it)

    base_cfg = copy.deepcopy(A292.DEFAULT_CONFIG292)
    rows: list[dict] = []
    for did in order:
        turns = by_dialog[did]
        cfg = copy.deepcopy(base_cfg)
        tmp = tempfile.mkdtemp(prefix="convf0-292-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = A292.build_agent292(cfg)
        try:
            for it in turns:
                ti = it.get("turn_index")
                text = get_text(it)
                if not isinstance(text, str) or not text.strip():
                    raise SystemExit(
                        f"convf0_run: empty text at {did} turn {ti}")
                ev_before = len(loop.nb.events)
                parts = loop.turn(text)
                reply = " ".join(parts) if parts else ""
                new_events = [dict(e) for e in list(loop.nb.events)[ev_before:]]
                triples = [[s, r, v] for (s, r, v) in L90.notebook_triples(loop.nb)]
                triples.sort()
                rows.append({
                    "dialog_id": did,
                    "turn_index": ti,
                    "reply": reply,
                    "notebook_events": new_events,
                    "stored_triples": triples,
                })
        finally:
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
            try:
                del loop
            except Exception:
                pass
        print(f"[convf0/292] did {did} turns={len(turns)}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                   encoding="utf-8")
    print(f"wrote {OUT} rows={len(rows)} dialogs={len(order)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
