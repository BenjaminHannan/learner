#!/usr/bin/env python3
"""Run every chainpanel266 item once on the base (138m), one process at a time.

Base: scripts/claude_loop138m_agent.py build_agent138m with
artifacts/claude-merge138m-20260922/loop138m-config.json, sleep_threshold
100000, a fresh temp state_dir per item outside the repo.
Writes artifacts/claude-chainpanel266-20260923/base138m.jsonl rows:
id, setup_replies, question_reply, stored_after_setup_actual,
stored_after_question_actual, question_wrote.
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ART = Path(__file__).resolve().parent


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def main():
    import claude_loop138m_agent as M
    import fable_loop90_agent as L90

    items = [json.loads(l) for l in
             (ART / "panel.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()]
    base_cfg = copy.deepcopy(M.DEFAULT_CONFIG138M)
    base_cfg.update(json.loads(
        (ROOT / "artifacts" / "claude-merge138m-20260922"
         / "loop138m-config.json").read_text(encoding="utf-8")))
    work = Path(tempfile.mkdtemp(prefix="c266-base-"))
    rows = []
    try:
        for n, it in enumerate(items):
            d = work / f"i{n:03d}"
            d.mkdir()
            cfg = dict(base_cfg)
            cfg["state_dir"] = str(d)
            cfg["sleep_threshold"] = 100000
            loop = M.build_agent138m(cfg)
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
            print(f"[138m] {it['id']} {question_reply[:100]!r}", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    (ART / "base138m.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8")
    print(f"wrote {ART / 'base138m.jsonl'} {len(rows)} rows")


if __name__ == "__main__":
    main()
