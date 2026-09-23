#!/usr/bin/env python3
"""Exp F1 convbench-f0 runner on both arms (292t and F1).

New file only. Mirrors scripts/claude_convf0_run.py (read-only, unchanged)
turn for turn, generalized to an arm table; the per-dialog loop, fresh
agent per dialog, event/triple recording, and output schema are identical.
CPU only. No agent code changes. Never prints benchmark user turns
(quoting agent replies is fine; this script prints ids/counts only).

Input: artifacts/claude-convbench-f0-20260923/dialogs.jsonl
  One JSON object per line with keys: dialog_id, turn_index,
  user_text (or user), kind, gold. Empty text stops with an error.

Output (one file per arm, same schema as convf0 base292.jsonl):
  artifacts/claude-f1-20260923/run/conv292t.jsonl
  artifacts/claude-f1-20260923/run/convf1.jsonl
  One JSON object per turn with: dialog_id, turn_index, reply,
  notebook_events (new loop.nb.events appended during this turn),
  stored_triples (notebook triples after this turn).

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_f1_convrun.py
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

BENCH = ROOT / "artifacts/claude-convbench-f0-20260923/dialogs.jsonl"
OUT292T = ROOT / "artifacts/claude-f1-20260923/run/conv292t.jsonl"
OUTF1 = ROOT / "artifacts/claude-f1-20260923/run/convf1.jsonl"


def get_text(item: dict) -> str:
    if "user_text" in item:
        return item["user_text"]
    if "user" in item:
        return item["user"]
    raise SystemExit("f1_convrun: turn missing user_text/user key")


def run_arm(build, base_cfg, order, by_dialog, tag):
    import fable_loop90_agent as L90
    rows: list[dict] = []
    for did in order:
        turns = by_dialog[did]
        cfg = copy.deepcopy(base_cfg)
        tmp = tempfile.mkdtemp(prefix=f"f1conv-{tag}-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        try:
            for it in turns:
                ti = it.get("turn_index")
                text = get_text(it)
                if not isinstance(text, str) or not text.strip():
                    raise SystemExit(
                        f"f1_convrun: empty text at {did} turn {ti}")
                ev_before = len(loop.nb.events)
                parts = loop.turn(text)
                reply = " ".join(parts) if parts else ""
                new_events = [dict(e) for e in list(loop.nb.events)[ev_before:]]
                triples = [[s, r, v] for (s, r, v)
                           in L90.notebook_triples(loop.nb)]
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
        print(f"[f1conv/{tag}] did {did} turns={len(turns)}", flush=True)
    return rows


def main() -> int:
    import claude_loop292t_agent as A292T
    import claude_loopf1_agent as AF1

    items = [json.loads(x) for x in BENCH.read_text(encoding="utf-8").splitlines() if x.strip()]
    order: list[str] = []
    by_dialog: dict[str, list[dict]] = {}
    for it in items:
        did = it.get("dialog_id")
        if not did:
            raise SystemExit("f1_convrun: turn missing dialog_id")
        if did not in by_dialog:
            by_dialog[did] = []
            order.append(did)
        by_dialog[did].append(it)

    base_cfg = copy.deepcopy(A292T.DEFAULT_CONFIG292T)
    for tag, build, out in (("292t", A292T.build_agent292t, OUT292T),
                            ("f1", AF1.build_agentf1, OUTF1)):
        rows = run_arm(build, base_cfg, order, by_dialog, tag)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                               for r in rows), encoding="utf-8")
        print(f"wrote {out} rows={len(rows)} dialogs={len(order)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
