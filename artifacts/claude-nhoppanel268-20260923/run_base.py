#!/usr/bin/env python3
"""Run every nhoppanel268 item once on the 138m base (CPU, one at a time).

Base: scripts/claude_loop138m_agent.py build_agent138m with
  artifacts/claude-merge138m-20260922/loop138m-config.json,
  sleep_threshold 100000, one fresh temp state_dir per item outside the repo.

Row fields (base138m.jsonl, one row per item, same order as panel.jsonl):
  id, setup_replies (list[str], one reply per setup turn),
  question_reply (str), question_stage (loop.ears.last_stage after the
  question turn), stored_after_setup_actual (int: len(loop.nb.facts) after
  the setup turns), stored_after_question_actual (int: after the question
  turn), question_wrote (bool: the fact count grew on the question turn).

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-nhoppanel268-20260923/run_base.py
reads panel.jsonl next to itself, writes base138m.jsonl next to itself.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import claude_loop138m_agent as M  # noqa: E402

CONFIG_PATH = (REPO / "artifacts" / "claude-merge138m-20260922"
               / "loop138m-config.json")


def run_item(cfg_base: dict, item: dict) -> dict:
    state_dir = tempfile.mkdtemp(prefix="n268-base-")
    cfg = dict(cfg_base)
    cfg["state_dir"] = state_dir
    cfg["sleep_threshold"] = 100000
    loop = M.build_agent138m(cfg)
    setup_replies: list[str] = []
    for turn in item["setup"]:
        out = loop.turn(turn)
        setup_replies.append(" ".join(out) if out else "")
    stored_after_setup = len(loop.nb.facts)
    qout = loop.turn(item["question"])
    question_reply = " ".join(qout) if qout else ""
    try:
        stage = getattr(getattr(loop, "ears", None), "last_stage", "")
    except Exception:
        stage = ""
    stored_after_question = len(loop.nb.facts)
    return {
        "id": item["id"],
        "setup_replies": setup_replies,
        "question_reply": question_reply,
        "question_stage": stage if isinstance(stage, str) else str(stage),
        "stored_after_setup_actual": stored_after_setup,
        "stored_after_question_actual": stored_after_question,
        "question_wrote": stored_after_question > stored_after_setup,
    }


def main() -> int:
    panel_path = HERE / "panel.jsonl"
    items = [json.loads(line) for line in
             panel_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    cfg_base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for item in items:
        row = run_item(cfg_base, item)
        rows.append(row)
        print(f"{row['id']} setup_n={row['stored_after_setup_actual']} "
              f"stage={row['question_stage']!r} "
              f"q={row['question_reply'][:80]!r}", flush=True)
    out = HERE / "base138m.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
