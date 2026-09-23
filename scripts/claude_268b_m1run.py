#!/usr/bin/env python3
"""Exp 268b M1 runner: run nhoppanel268b once on ONE arm, one item at a time.

New file only (the sealed scripts/claude_268b_panelrun.py writes the
invpanel row format without question_stage; this panel's sealed scorer
requires question_stage, so this runner emits the panel's exact
base-row format). CPU only. One arm per process (the 268 guard rebinds
a module global; never mix arms in one process). Fresh temp state dir
per item outside the repo, sleep_threshold 100000. Never prints item
text or replies (ids only).

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_268b_m1run.py <panel.json> <agent_py> <config> <out_rows> [label]

Row format matches the panel's REQUIRED_ROW_FIELDS exactly:
id, setup_replies, question_reply, question_stage (loop.ears.last_stage,
as the panel's own run_base.py records), stored_after_setup_actual,
stored_after_question_actual, question_wrote. USER subjects map to "you".
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
        "ag_m1_268b", str(SCRIPTS / Path(agent_py).name))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_m1_268b"] = mod
    spec.loader.exec_module(mod)
    return mod


def triples(loop):
    rows = []
    for s, r, v in L90.notebook_triples(loop.nb):
        if s == "USER":
            s = "you"
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
    for name in ("build_agent268b", "build_agent138nb"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known 268b/138nb build_* in agent module")
    base = copy.deepcopy(json.loads(Path(config).read_text(
        encoding="utf-8")))
    rows = []
    for it in items:
        cfg = copy.deepcopy(base)
        tmp = tempfile.mkdtemp(prefix="m1268b-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        try:
            setup_replies = []
            for t in it["setup"]:
                setup_replies.append(" ".join(loop.turn(t)))
            s_setup = triples(loop)
            qrep = " ".join(loop.turn(it["question"]))
            stage = getattr(getattr(loop, "ears", None), "last_stage", "")
            s_q = triples(loop)
            rows.append({"id": it["id"], "setup_replies": setup_replies,
                         "question_reply": qrep,
                         "question_stage": str(stage),
                         "stored_after_setup_actual": s_setup,
                         "stored_after_question_actual": s_q,
                         "question_wrote": bool(s_q != s_setup)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[{label}] did {it['id']}", flush=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                 for r in rows), encoding="utf-8")
    print(f"[{label}] WROTE {out} {len(rows)} rows", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
