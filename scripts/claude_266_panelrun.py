#!/usr/bin/env python3
"""Exp 266 panel runner: run every chainpanel266 item ONCE on one arm.

Mirrors artifacts/claude-chainpanel266-20260923/run_base.py exactly (same
config handling, sleep_threshold 100000, one fresh temp state_dir per item
outside the repo, same row schema), but parametric in the arm so the 266
arm runs the identical path. Never reads or prints panel items beyond
what the sealed scorer itself prints; never writes into the panel dir.

usage: claude_266_panelrun.py --arm 138m|266 --out <rows.jsonl>
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PANEL = (ROOT / "artifacts" / "claude-chainpanel266-20260923"
         / "panel.jsonl")


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 266 blind-panel runner")
    ap.add_argument("--arm", required=True, choices=("138m", "266"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.arm == "138m":
        import claude_loop138m_agent as M
        base_cfg = copy.deepcopy(M.DEFAULT_CONFIG138M)
        base_cfg.update(json.loads(
            (ROOT / "artifacts" / "claude-merge138m-20260922"
             / "loop138m-config.json").read_text(encoding="utf-8")))
        build = M.build_agent138m
    else:
        import claude_loop266_agent as M
        base_cfg = copy.deepcopy(M.DEFAULT_CONFIG266)
        base_cfg.update(json.loads(
            (ROOT / "artifacts" / "claude-chain266-20260923"
             / "loop266-config.json").read_text(encoding="utf-8")))
        build = M.build_agent266
    import fable_loop90_agent as L90

    items = [json.loads(l) for l in
             PANEL.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(items) == 80, len(items)
    work = Path(tempfile.mkdtemp(prefix=f"c266-{args.arm}-"))
    rows = []
    try:
        for n, it in enumerate(items):
            d = work / f"i{n:03d}"
            d.mkdir()
            cfg = dict(base_cfg)
            cfg["state_dir"] = str(d)
            cfg["sleep_threshold"] = 100000
            loop = build(cfg)
            setup_replies = []
            for t in it["setup"]:
                setup_replies.append(" ".join(loop.turn(t)))
            stored_setup = [list(x) for x in L90.notebook_triples(loop.nb)]
            h0 = facts_hash(loop.nb)
            question_reply = " ".join(loop.turn(it["question"]))
            stored_q = [list(x) for x in L90.notebook_triples(loop.nb)]
            rows.append({"id": it["id"], "setup_replies": setup_replies,
                         "question_reply": question_reply,
                         "stored_after_setup_actual": stored_setup,
                         "stored_after_question_actual": stored_q,
                         "question_wrote": h0 != facts_hash(loop.nb)})
            print(f"[{args.arm}] {it['id']} done", flush=True)
            del loop
    finally:
        shutil.rmtree(work, ignore_errors=True)
    Path(args.out).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {args.out} {len(rows)} rows")


if __name__ == "__main__":
    sys.exit(main())
