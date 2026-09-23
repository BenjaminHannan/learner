#!/usr/bin/env python3
"""run_base.py: run every panel item once on base 138n, one at a time."""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

SYS_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SYS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SYS_SCRIPTS))
import fable_loop90_agent as L90  # noqa: E402
import claude_loop138n_agent as N138  # noqa: E402

PANEL = Path(__file__).resolve().parent / "panel.jsonl"
OUT = Path(__file__).resolve().parent / "base138n.jsonl"
CONFIG = Path(__file__).resolve().parents[2] / "artifacts" / "claude-merge138n-20260922" / "loop138n-config.json"


def triples(loop):
    rows = []
    for s, r, v in L90.notebook_triples(loop.nb):
        if s == "USER":
            s = "you"
        rows.append([s, r, v])
    rows.sort()
    return rows


def run_item(it):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    tmp = tempfile.mkdtemp(prefix="inv138nb-base-")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = N138.build_agent138n(cfg)
    try:
        setup_replies = []
        for t in it["setup"]:
            rep = loop.turn(t)
            setup_replies.append(" ".join(rep))
        s_setup = triples(loop)
        qrep_list = loop.turn(it["question"])
        qrep = " ".join(qrep_list)
        s_q = triples(loop)
        qwrote = (s_q != s_setup)
        return {"id": it["id"], "setup_replies": setup_replies, "question_reply": qrep,
                "stored_after_setup_actual": s_setup, "stored_after_question_actual": s_q,
                "question_wrote": bool(qwrote)}
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


def main():
    items = [json.loads(x) for x in PANEL.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(items) == 70, len(items)
    rows = []
    for it in items:
        rows.append(run_item(it))
        print(f"did {it['id']}", flush=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {OUT} {len(rows)} rows")


if __name__ == "__main__":
    main()
