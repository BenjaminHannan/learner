#!/usr/bin/env python3
"""DEV-ONLY pre-seal follow-up checks for exp 158 (not a registered run)."""

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix158_qform as Q
import fable_loop150_agent as L150

ROOT = SCRIPTS.parent

qs = [l for l in (ROOT / "data/open/bench121/fable_edit121_4hop.jsonl")
      .read_text(encoding="utf-8").splitlines() if "capital" in l]
for line in qs:
    it = json.loads(line)
    q = it["id"] + " :: " + it["question"]
    cand, fired = Q.normalize_question_surface(it["question"])
    print(it["id"], "cand=", repr(cand), "fired=", fired)

import fable_redteam81_probe as P81
for seq_id, desc, steps in P81.SEQS:
    if seq_id == "D_q_vs_s":
        print("DESC:", desc)
        for st in steps:
            print("  turn=", repr(st["turn"]), "expect=", st["expect"],
                  "must=", st.get("must"), "nowrite=", st.get("nowrite"))

rep = json.loads((ROOT / "artifacts/fable-fix150-20260922/marks150/rt81-report.json")
                 .read_text(encoding="utf-8"))
for c in rep["cases"]:
    if c["id"].startswith("D_q_vs_s"):
        print("SEALED150", c["id"], c["verdict"], c["observed"][:150])

# Base ask-checks: candidate through BASE loop150 with item context.
C150 = copy.deepcopy(L150.DEFAULT_CONFIG150)


def base_ask(teaches, cand):
    tmp = tempfile.mkdtemp()
    c = dict(C150)
    c["state_dir"] = tmp
    c["sleep_threshold"] = 100000
    loop = L150.build_agent150(c)
    for t in teaches:
        loop.turn(t)
    acts = loop.ears.hear(cand)
    reply = " ".join(loop.turn(cand))
    return acts, reply


items = [json.loads(l) for l in
         (ROOT / "data/open/bench121/fable_edit121_4hop.jsonl")
         .read_text(encoding="utf-8").splitlines() if l.strip()]
for it in items:
    if "Beatles" in it["question"] or it["question"].startswith("In what city"):
        cand, _ = Q.normalize_question_surface(it["question"])
        teaches = [t["sentence_en"] for t in it["taught"]]
        acts, reply = base_ask(teaches, cand)
        acts0 = L150.build_agent150(
            dict(C150, state_dir=tempfile.mkdtemp(),
                 sleep_threshold=100000))
        for t in teaches:
            acts0.turn(t)
        reply0 = " ".join(acts0.turn(it["question"]))
        print(it["id"], "cand_acts=", acts)
        print("  cand_reply=", repr(reply[:120]))
        print("  orig_reply=", repr(reply0[:120]))
        print("  identical=", reply == reply0)
