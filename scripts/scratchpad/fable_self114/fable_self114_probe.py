#!/usr/bin/env python3
"""114 probe (scratchpad only): 105-router verdicts on all dev sets + token scan."""
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_self100_runner as R100
import fable_self105 as S105

STATE = SCRIPTS / "scratchpad" / "fable_self114" / "probe_state2"
if STATE.exists():
    shutil.rmtree(STATE)
agent = S105.Self105Agent(str(STATE))
agent.run_session()
s = agent.snapshot()
print("GATE:", {k: s[k] for k in ("n_taught", "n_entities", "n_quarantine",
                                  "n_forgotten", "turns", "sleeps")})

checked = agent.check_all()
print("exp99:", checked["correct"], "/40 hall=", len(checked["hallucinations"]))

rows = []
for qid, intent, text in R100.BLIND:
    ans = agent.answer_self(text)
    verdict, _ = R100.score(agent, qid, intent, ans, s)
    routed, _ = S105.route(text)
    rows.append(("100", qid, intent, routed, verdict, text))
    print(f"100 {qid}({intent}->{routed}): {verdict} Q={text}")

panel = json.loads((REPO / "artifacts" / "fable-self105panel-20260921"
                    / "panel.json").read_text(encoding="utf-8"))
for q in panel["questions"]:
    qid, group, intent, text = q["id"], q["group"], q["intent"], q["question"]
    cls = intent if group == "existing" else ("NEW" if group == "new" else "D0")
    ans = agent.answer_self(text)
    verdict, note = R100.score(agent, qid, cls, ans, s)
    routed, _ = S105.route(text)
    rows.append(("105", qid, f"{group}/{intent}", routed, verdict, text))
    print(f"105 {qid}({group}/{intent}->{routed}): {verdict} Q={text} :: {note}")

# token-collision scan for candidate guard words
cands = ["will", "would", "shall", "tomorrow", "next", "future", "predict",
         "soon", "eventually", "tonight", "suppose", "imagine", "pretend",
         "hypothetical", "standard", "standards", "source", "sources",
         "trust", "request", "somewhere", "gone", "keep", "still", "ever",
         "erase", "erased", "entirely", "they", "them", "their", "he",
         "him", "his", "she", "her", "fix", "correct", "able", "can"]
dev_texts = ([t for _, _, t in R100.BLIND]
             + [t["text"] for t in S105.S99.QUESTIONS]
             + [q["question"] for q in panel["questions"]])
print("=== collision scan (question ids containing each candidate token) ===")
import re
for w in cands:
    hits = []
    for src, qid, intent, routed, verdict, text in rows:
        _, toks = S105.normalise(text)
        if w in toks:
            hits.append(f"{src}:{qid}[{intent}/{verdict}]")
    for q in S105.S99.QUESTIONS:
        _, toks = S105.normalise(q["text"])
        if w in toks:
            hits.append(f"99:{q['id']}[CORRECT]")
    print(f"{w}: {len(hits)} :: {'; '.join(hits)}")
