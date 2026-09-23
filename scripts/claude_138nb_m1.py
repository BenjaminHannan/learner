#!/usr/bin/env python3
"""Merge 138nb -- M1 arm runner for invpanel138nb (TEST-ONLY, run once per
arm after the seal, scored with the panel's own sealed score_panel.py).

Runs panel.jsonl items (setup turns then the question, one fresh agent
per item, sleep_threshold 100000, state in a fresh temp dir) on one arm
(n = 138n, nb = 138nb) and writes rows in the panel's base-row format:
id, setup_replies, question_reply, stored_after_setup_actual,
stored_after_question_actual, question_wrote (true/false).

Prints and writes ids and counts only, never item text. Rows hold item
text and stay outside the repo; only counts and ids are copied in.

usage:
  claude_138nb_m1.py run --arm n|nb --items PANEL --out ROWS.jsonl --work DIR
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

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def facts_hash(nb) -> str:
    blob = json.dumps({"facts": nb.facts,
                       "retracted": sorted(getattr(nb, "retracted", [])),
                       "superseded": sorted(getattr(nb, "superseded", []))},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def stored(nb) -> list:
    import fable_loop90_agent as L90
    return sorted(list(map(list, map(str, x)))
                 for x in L90.notebook_triples(nb))


def cmd_run(arm: str, items: str, out: str, work: str) -> int:
    if arm == "n":
        import claude_loop138n_agent as AG
        cfg0, build = (copy.deepcopy(AG.DEFAULT_CONFIG138N),
                       AG.build_agent138n)
    else:
        import claude_loop138nb_agent as AG
        cfg0, build = (copy.deepcopy(AG.DEFAULT_CONFIG138NB),
                       AG.build_agent138nb)
    workp = Path(work)
    workp.mkdir(parents=True, exist_ok=True)
    rows = []
    n_qw = 0
    with open(items, encoding="utf-8") as f:
        lines = [x for x in f.read().splitlines() if x.strip()]
    print(f"items={len(lines)} arm={arm}", flush=True)
    for line in lines:
        it = json.loads(line)
        iid = str(it["id"])
        setup = [str(s) for s in it["setup"]]
        q = str(it["question"])
        d = Path(tempfile.mkdtemp(prefix=f"m1-{arm}-", dir=str(workp)))
        cfg = copy.deepcopy(cfg0)
        cfg["state_dir"] = str(d)
        cfg["sleep_threshold"] = 100000
        loop = build(cfg)
        srep = []
        for t in setup:
            srep.append(" ".join(loop.turn(t)))
        after_setup = stored(loop.nb)
        h0 = facts_hash(loop.nb)
        qrep = " ".join(loop.turn(q))
        qw = facts_hash(loop.nb) != h0
        after_q = stored(loop.nb)
        n_qw += int(qw)
        rows.append({"id": iid, "setup_replies": srep,
                     "question_reply": qrep,
                     "stored_after_setup_actual": after_setup,
                     "stored_after_question_actual": after_q,
                     "question_wrote": qw})
        shutil.rmtree(d, ignore_errors=True)
    Path(out).write_text("\n".join(json.dumps(r, ensure_ascii=False)
                                   for r in rows) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} question_writes={n_qw}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=["n", "nb"], required=True)
    r.add_argument("--items", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--work", required=True)
    a = ap.parse_args(argv)
    return cmd_run(a.arm, a.items, a.out, a.work)


if __name__ == "__main__":
    sys.exit(main())
