#!/usr/bin/env python3
"""Exp 292 M5 runner: run mixpanel292 once on ONE arm, one item at a time.

New file only. Row contract mirrors the mixpanel292 spec (the same
contract as nhoppanel268b/yesnopanel293): id, setup_replies,
question_reply, question_stage (loop.ears.last_stage),
stored_after_setup_actual, stored_after_question_actual,
question_wrote. CPU only. One arm per process. Fresh temp state dir
per item outside the repo, sleep_threshold 100000. Never prints item
text or replies (ids only). Rows go to a tmpdir (never into the sealed
panel dir); only counts JSON (ids, families, counts) is published.

usage: claude_292_m5run.py <panel.jsonl> <agent_py> <config> <out_rows>
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
        "ag_m5_292", str(Path(agent_py).resolve()))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ag_m5_292"] = mod
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
    items = [json.loads(x) for x in Path(panel_p).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    mod = load_agent(agent_py)
    build = None
    for name in ("build_agent292", "build_agent291", "build_agent266b",
                 "build_agent268b", "build_agent293", "build_agent138nb"):
        if hasattr(mod, name):
            build = getattr(mod, name)
            break
    if build is None:
        raise SystemExit("no known build_* in agent module")
    base = copy.deepcopy(json.loads(Path(config).read_text(
        encoding="utf-8")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for it in items:
        cfg = copy.deepcopy(base)
        tmp = tempfile.mkdtemp(prefix="m292-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        try:
            setup_replies = [" ".join(loop.turn(t)) for t in it["setup"]]
            s_setup = triples(loop)
            qrep = " ".join(loop.turn(it["question"]))
            try:
                qstage = str(getattr(loop.ears, "last_stage", ""))
            except Exception:
                qstage = ""
            s_q = triples(loop)
            rows.append({"id": it["id"], "setup_replies": setup_replies,
                         "question_reply": qrep, "question_stage": qstage,
                         "stored_after_setup_actual": s_setup,
                         "stored_after_question_actual": s_q,
                         "question_wrote": bool(s_q != s_setup)})
        finally:
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
            try:
                del loop
            except Exception:
                pass
        print(f"[m5] did {it['id']}", flush=True)
    Path(out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                 for r in rows), encoding="utf-8")
    print(f"wrote {out} {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
