#!/usr/bin/env python3
"""Run every chainpanel266b item once on base 266 and record the rows.

266 = scripts/claude_loop266_agent.py, build function and config as in
artifacts/claude-chain266-20260923 (config file loop266-config.json),
a fresh temp state_dir per item outside the repo, sleep_threshold 100000.
One process at a time (sequential loop). CPU only.

Row fields: id, setup_replies, question_reply, stored_after_setup_actual,
stored_after_question_actual, question_wrote.

Usage (run from the repo root):
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-chainpanel266b-20260923/run_base.py
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path("artifacts/claude-chainpanel266b-20260923")
PANEL = HERE / "panel.jsonl"
OUT = HERE / "base266.jsonl"
CONFIG = Path("artifacts/claude-chain266-20260923/loop266-config.json")

sys.path.insert(0, "scripts")
import claude_loop266_agent as A266


def triples(loop):
    return [[s, r, v] for _, s, r, v in loop.nb.nb._triples]


def main():
    base = json.loads(CONFIG.read_text(encoding="utf-8"))
    items = [json.loads(line) for line in PANEL.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    rows = []
    for it in items:
        cfg = dict(base)
        cfg["sleep_threshold"] = 100000
        cfg["state_dir"] = tempfile.mkdtemp(prefix="c266b-base-")
        loop = A266.build_agent266(cfg)
        setup_replies = [" ".join(loop.turn(t)) for t in it["setup"]]
        stored_setup = triples(loop)
        q_reply = " ".join(loop.turn(it["question"]))
        stored_q = triples(loop)
        rows.append({
            "id": it["id"],
            "setup_replies": setup_replies,
            "question_reply": q_reply,
            "stored_after_setup_actual": stored_setup,
            "stored_after_question_actual": stored_q,
            "question_wrote": stored_q != stored_setup,
        })
        print(f"did {it['id']} wrote={stored_q != stored_setup}", flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
