#!/usr/bin/env python3
"""Exp 292 blind-panel runner: run every item of chainpanel266b,
nhoppanel268b or yesnopanel293 ONCE on one arm (291, 266b, 268b, 293
or 292). corrpanel291 runs separately with scripts/claude_corr252_run.py
unchanged (it takes --agent, so the same runner serves 291 and 292).

New file only. Each --panel branch mirrors that panel's sealed
run_base.py one-for-one (same config handling, sleep_threshold, fresh
state_dir per item outside the repo, same row schema); only the arm
build differs, and it never prints replies or item text (ids and counts
only). Rows are written OUTSIDE the repo panels (never into a sealed
panel dir), so only counts JSON (ids, families, counts) is ever
published. CPU only, one arm per process (the 268 guard rebinds a
module global; never mix arms in one process).

usage: claude_292_panelrun.py --panel chain266b|nhop268b|yesno293
                              --arm 291|266b|268b|293|292 --out <rows.jsonl>
"""
from __future__ import annotations

import argparse
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

ARMS = {
    "266b": ("claude_loop266b_agent", "build_agent266b",
             "artifacts/claude-chain266b-20260923/loop266b-config.json"),
    "268b": ("claude_loop268b_agent", "build_agent268b",
             "artifacts/claude-nhop268b-20260923/loop268b-config.json"),
    "293": ("claude_loop293_agent", "build_agent293",
            "artifacts/claude-yesno293-20260923/loop293-config.json"),
    "291": ("claude_loop291_agent", "build_agent291",
            "artifacts/claude-join291-20260923/loop291-config.json"),
    "292": ("claude_loop292_agent", "build_agent292",
            "artifacts/claude-merge292-20260923/loop292-config.json"),
}

PANELS = {
    "chain266b": "artifacts/claude-chainpanel266b-20260923/panel.jsonl",
    "nhop268b": "artifacts/claude-nhoppanel268b-20260923/panel.jsonl",
    "yesno293": "artifacts/claude-yesnopanel293-20260923/panel.jsonl",
}


def load_arm(arm: str):
    mod_name, build_name, cfg_rel = ARMS[arm]
    import importlib
    mod = importlib.import_module(mod_name)
    return getattr(mod, build_name), ROOT / cfg_rel


def run_chain266b(arm: str, out: str) -> None:
    """Mirror artifacts/claude-chainpanel266b-20260923/run_base.py."""
    build, cfg_src = load_arm(arm)
    base = json.loads(cfg_src.read_text(encoding="utf-8"))
    items = [json.loads(l) for l in
             (ROOT / PANELS["chain266b"]).read_text(
                 encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for it in items:
        cfg = dict(base)
        cfg["sleep_threshold"] = 100000
        cfg["state_dir"] = tempfile.mkdtemp(prefix=f"c292-{arm}-")
        loop = build(cfg)

        def triples(loop):
            return [[s, r, v] for _, s, r, v in loop.nb.nb._triples]

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
        print(f"[chain266b/{arm}] did {it['id']} "
              f"wrote={stored_q != stored_setup}", flush=True)
        del loop
    Path(out).write_text(
        "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {out} {len(rows)} rows")


def run_nhop_yesno(panel: str, arm: str, out: str) -> None:
    """Mirror nhoppanel268b / yesnopanel293 run_base.py files."""
    import fable_loop90_agent as L90
    build, cfg_src = load_arm(arm)
    items = [json.loads(x) for x in
             (ROOT / PANELS[panel]).read_text(
                 encoding="utf-8").splitlines() if x.strip()]

    def triples(loop):
        rows = []
        for s, r, v in L90.notebook_triples(loop.nb):
            if s == "USER":
                s = "you"
            rows.append([s, r, v])
        rows.sort()
        return rows

    rows = []
    for it in items:
        cfg = copy.deepcopy(json.loads(cfg_src.read_text(encoding="utf-8")))
        tmp = tempfile.mkdtemp(prefix=f"m292-{arm}-")
        cfg["state_dir"] = tmp
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        try:
            setup_replies = []
            for t in it["setup"]:
                rep = loop.turn(t)
                setup_replies.append(" ".join(rep))
            s_setup = triples(loop)
            qrep_list = loop.turn(it["question"])
            qrep = " ".join(qrep_list)
            try:
                qstage = str(getattr(loop.ears, "last_stage", ""))
            except Exception:
                qstage = ""
            s_q = triples(loop)
            qwrote = (s_q != s_setup)
            rows.append({"id": it["id"], "setup_replies": setup_replies,
                         "question_reply": qrep, "question_stage": qstage,
                         "stored_after_setup_actual": s_setup,
                         "stored_after_question_actual": s_q,
                         "question_wrote": bool(qwrote)})
        finally:
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass
            try:
                del loop
            except Exception:
                pass
        print(f"[{panel}/{arm}] did {it['id']}", flush=True)
    Path(out).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {out} {len(rows)} rows")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 292 blind-panel runner")
    ap.add_argument("--panel", required=True,
                    choices=("chain266b", "nhop268b", "yesno293"))
    ap.add_argument("--arm", required=True,
                    choices=("291", "266b", "268b", "293", "292"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.panel == "chain266b":
        run_chain266b(args.arm, args.out)
    else:
        run_nhop_yesno(args.panel, args.arm, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
