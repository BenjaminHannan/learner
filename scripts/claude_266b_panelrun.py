#!/usr/bin/env python3
"""Exp 266b blind-panel runner: run every item of chainpanel266b (M1) or
chainpanel266 (M2 regression) ONCE on one arm (266 or 266b).

Created AFTER the 266b seal (like 266's panelrun): it contains no agent
logic and reads no panel content beyond feeding setup/question turns to
the loop. Each --panel branch mirrors that panel's sealed run_base.py
one-for-one (same config handling, sleep_threshold, fresh state_dir per
item outside the repo, same row schema); only the arm build differs, and
it never prints replies or item text (ids and counts only). Rows are
written OUTSIDE the repo panels (never into a sealed panel dir), so only
counts JSON (ids, families, counts) is ever published.

usage: claude_266b_panelrun.py --panel 266b|266 --arm 266|266b --out <rows.jsonl>
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


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def run_266b(panel: str, arm: str, out: str) -> None:
    """Mirror artifacts/claude-chainpanel266b-20260923/run_base.py."""
    import fable_loop90_agent as _L90  # noqa: F401 (parity import only)
    if arm == "266":
        import claude_loop266_agent as A
        build = A.build_agent266
        cfg_src = (ROOT / "artifacts" / "claude-chain266-20260923"
                   / "loop266-config.json")
    else:
        import claude_loop266b_agent as A
        build = A.build_agent266b
        cfg_src = (ROOT / "artifacts" / "claude-chain266b-20260923"
                   / "loop266b-config.json")
    base = json.loads(cfg_src.read_text(encoding="utf-8"))
    panel_path = (ROOT / "artifacts" / "claude-chainpanel266b-20260923"
                  / "panel.jsonl")
    items = [json.loads(l) for l in
             panel_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for it in items:
        cfg = dict(base)
        cfg["sleep_threshold"] = 100000
        cfg["state_dir"] = tempfile.mkdtemp(prefix=f"c266b-{arm}-")
        loop = build(cfg)
        setup_replies = [" ".join(loop.turn(t)) for t in it["setup"]]
        stored_setup = [[s, r, v] for _, s, r, v in loop.nb.nb._triples]
        q_reply = " ".join(loop.turn(it["question"]))
        stored_q = [[s, r, v] for _, s, r, v in loop.nb.nb._triples]
        rows.append({
            "id": it["id"],
            "setup_replies": setup_replies,
            "question_reply": q_reply,
            "stored_after_setup_actual": stored_setup,
            "stored_after_question_actual": stored_q,
            "question_wrote": stored_q != stored_setup,
        })
        print(f"[{panel}/{arm}] did {it['id']} "
              f"wrote={stored_q != stored_setup}", flush=True)
        del loop
    Path(out).write_text(
        "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {out} {len(rows)} rows")


def run_266(panel: str, arm: str, out: str) -> None:
    """Mirror artifacts/claude-chainpanel266-20260923/run_base.py."""
    import fable_loop90_agent as L90
    if arm == "266":
        import claude_loop266_agent as M
        default, build = (copy.deepcopy(M.DEFAULT_CONFIG266),
                          M.build_agent266)
        cfg_file = (ROOT / "artifacts" / "claude-chain266-20260923"
                    / "loop266-config.json")
    else:
        import claude_loop266b_agent as M
        default, build = (copy.deepcopy(M.DEFAULT_CONFIG266B),
                          M.build_agent266b)
        cfg_file = (ROOT / "artifacts" / "claude-chain266b-20260923"
                    / "loop266b-config.json")
    items = [json.loads(l) for l in
             (ROOT / "artifacts" / "claude-chainpanel266-20260923"
              / "panel.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()]
    base_cfg = default
    base_cfg.update(json.loads(cfg_file.read_text(encoding="utf-8")))
    work = Path(tempfile.mkdtemp(prefix=f"c266-{arm}-"))
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
            print(f"[{panel}/{arm}] did {it['id']}", flush=True)
            del loop
    finally:
        shutil.rmtree(work, ignore_errors=True)
    Path(out).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {out} {len(rows)} rows")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 266b blind-panel runner")
    ap.add_argument("--panel", required=True, choices=("266b", "266"))
    ap.add_argument("--arm", required=True, choices=("266", "266b"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.panel == "266b":
        run_266b(args.panel, args.arm, args.out)
    else:
        run_266(args.panel, args.arm, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
