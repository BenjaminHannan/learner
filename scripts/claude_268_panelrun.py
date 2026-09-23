#!/usr/bin/env python3
"""Exp 268 panel runner: run nhoppanel268 items ONCE on one arm.

New file only. CPU only. Never the repo-root notebook (fresh temp
state_dir per item). Row format mirrors the panel's own run_base.py
exactly (same keys, same order) so the sealed score_panel.py accepts it.
Writes rows OUTSIDE the sealed panel folder; never modifies the panel.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_268_panelrun.py <agent_py> <config> \\
    <panel.jsonl> <rows_out.jsonl> [label]
"""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_panel", str(Path(agent_py)))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_panel"] = mod
    spec.loader.exec_module(mod)
    return mod


def run_item(build, cfg_base: dict, item: dict) -> dict:
    state_dir = tempfile.mkdtemp(prefix="n268-panel-")
    try:
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = state_dir
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        setup_replies: list[str] = []
        for turn in item["setup"]:
            out = loop.turn(turn)
            setup_replies.append(" ".join(out) if out else "")
        stored_after_setup = len(loop.nb.facts)
        qout = loop.turn(item["question"])
        question_reply = " ".join(qout) if qout else ""
        try:
            stage = getattr(getattr(loop, "ears", None), "last_stage", "")
        except Exception:  # noqa: BLE001
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
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def main() -> int:
    agent_py, config, panel_p, out_p = sys.argv[1:5]
    label = sys.argv[5] if len(sys.argv) > 5 else ""
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent268", "build_agent138m"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no build_agent found")
    cfg_base = json.loads(Path(config).read_text(encoding="utf-8"))
    items = [json.loads(line) for line in
             Path(panel_p).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    rows: list[dict] = []
    for item in items:
        row = run_item(build, cfg_base, item)
        rows.append(row)
        print(f"[{label}] {row['id']} setup_n="
              f"{row['stored_after_setup_actual']} "
              f"stage={row['question_stage']!r} "
              f"wrote={row['question_wrote']}", flush=True)
    with open(out_p, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[{label}] Wrote {out_p} ({len(rows)} rows)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
