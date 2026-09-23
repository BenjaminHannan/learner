#!/usr/bin/env python3
"""run_base.py: run yesnopanel293 once on base 138nb, one item at a time."""
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
import claude_loop138nb_agent as NB  # noqa: E402

PANEL = Path(__file__).resolve().parent / "panel.jsonl"
OUT = Path(__file__).resolve().parent / "base138nb.jsonl"
CONFIG = Path(__file__).resolve().parents[2] / "artifacts" / "claude-merge138nb-20260923" / "loop138nb-config.json"


def triples(loop):
    rows = []
    for s, r, v in L90.notebook_triples(loop.nb):
        if s == "USER":
            s = "you"
        rows.append([s, r, v])
    rows.sort()
    return rows


def run_item(it):
    cfg = copy.deepcopy(json.loads(CONFIG.read_text(encoding="utf-8")))
    tmp = tempfile.mkdtemp(prefix="y293base-")
    cfg["state_dir"] = tmp
    cfg["sleep_threshold"] = 100000
    loop = NB.build_agent138nb(cfg)
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
        return {"id": it["id"], "setup_replies": setup_replies,
                "question_reply": qrep, "question_stage": qstage,
                "stored_after_setup_actual": s_setup,
                "stored_after_question_actual": s_q,
                "question_wrote": bool(qwrote)}
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass


def main():
    items = [json.loads(x) for x in PANEL.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(items) == 85, len(items)
    rows = []
    for it in items:
        rows.append(run_item(it))
        print(f"did {it['id']}", flush=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {OUT} {len(rows)} rows")


if __name__ == "__main__":
    main()
