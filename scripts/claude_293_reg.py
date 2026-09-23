#!/usr/bin/env python3
"""Exp 293 regression runner: run a sealed panel's items on ONE arm.

New file only. CPU only. Fresh temp state_dir per item outside the repo,
sleep_threshold 100000. Records reply, triples after setup/question, and
a question-wrote flag. The panel files are read, never modified.

Usage:
  uv run ... python -B scripts/claude_293_reg.py <panel.jsonl> <agent_py> <config> <out_rows> [label]
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

import fable_loop90_agent as L90  # noqa: E402 (read-only triples)


def load_agent(agent_py: str):
    spec = importlib.util.spec_from_file_location(
        "ag_reg_293", str(Path(agent_py).resolve()))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_reg_293"] = mod
    spec.loader.exec_module(mod)
    return mod


def triples(loop):
    rows = []
    for s, r, v in L90.notebook_triples(loop.nb):
        rows.append([s, r, v])
    rows.sort()
    return rows


def main() -> int:
    panel_p, agent_py, config, out = sys.argv[1:5]
    label = sys.argv[5] if len(sys.argv) > 5 else ""
    items = [json.loads(x) for x in Path(panel_p).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent293", "build_agent138nb"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known build_* in agent module")
    base = copy.deepcopy(json.loads(Path(config).read_text(
        encoding="utf-8")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    if Path(out).exists():
        Path(out).unlink()
    for it in items:
        cfg = copy.deepcopy(base)
        tmp = tempfile.mkdtemp(prefix="reg293-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        try:
            setup_replies = []
            for t in it["setup"]:
                setup_replies.append(" ".join(loop.turn(t)))
            s_setup = triples(loop)
            qrep = " ".join(loop.turn(it["question"]))
            s_q = triples(loop)
            row = {"id": it["id"], "family": it.get("family"),
                   "setup_replies": setup_replies, "question_reply": qrep,
                   "question_stage": str(getattr(loop.ears, "last_stage", "")),
                   "stored_after_setup_actual": s_setup,
                   "stored_after_question_actual": s_q,
                   "question_wrote": s_q != s_setup, "label": label}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(f"{it['id']} reply={qrep[:60]!r} wrote={row['question_wrote']}",
              flush=True)
    print(f"WROTE {len(items)} rows to {out}")


if __name__ == "__main__":
    main()
