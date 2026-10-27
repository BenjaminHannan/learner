#!/usr/bin/env python3
"""Exp 166 dev-only pre-seal scan: run the me parser over every sealed input
turn of every registered suite. NOT a registered run; produces no artifacts."""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_fix166_me as M

texts = []


def add(src, t):
    if isinstance(t, str) and t.strip():
        texts.append((src, t))


import fable_loop129b_bench as B129
for p in [B129.DATA_EDIT200, B129.DATA_OLD, B129.DATA_NEW]:
    for line in p.read_text().splitlines():
        if line.strip():
            it = json.loads(line)
            for k in ("teach", "text", "sentence", "question", "q"):
                if isinstance(it.get(k), str):
                    add("G1bench:" + p.name, it[k])
            for s in it.get("teaches", []) + it.get("questions", []):
                add("G1bench:" + p.name, s if isinstance(s, str)
                    else s.get("text", ""))

import fable_bench113_run as B113
for tag, p in (("A", B113.DATA_A), ("B", B113.DATA_B)):
    for line in p.read_text().splitlines():
        if line.strip():
            it = json.loads(line)
            for k in ("teach", "text", "sentence", "question", "q"):
                if isinstance(it.get(k), str):
                    add("mbench:" + tag, it[k])

for r in json.loads((ROOT / "artifacts/fable-redteam136-20260922"
                     / "cases136.json").read_text()):
    add("rt136", r.get("text", ""))

import fable_redteam143_run as R143
s = json.loads(R143.CASES_PATH.read_text())
for c in s["cases"]:
    add("rt143", c.get("text", c.get("turn", "")))

sess = json.loads((ROOT / "artifacts/fable-session152-20260922"
                   / "sessions152.json").read_text())
for x in sess:
    for t in x.get("turns", x.get("events", [])):
        add("s152", t.get("text", t if isinstance(t, str) else ""))

import fable_redteam98_cases as RC

def walk(o, src):
    if isinstance(o, str):
        add(src, o)
    elif isinstance(o, dict):
        for v in o.values():
            walk(v, src)
    elif isinstance(o, (list, tuple)):
        for v in o:
            walk(v, src)

walk({k: v for k, v in vars(RC).items() if k.isupper()}, "p2")

for r in json.loads((ROOT / "artifacts/fable-loop102-20260921"
                     / "p4-innocent-30.json").read_text()):
    walk(r, "p4")

for c in json.loads((ROOT / "artifacts/fable-redteam110-20260921"
                     / "fable_redteam110_cases.json").read_text()):
    walk(c, "rt110")

import fable_redteam81_probe as P81
for seq_id, _desc, steps in P81.SEQS:
    for st in steps:
        add("rt81:" + seq_id, st.get("turn", ""))

for t in ["Mira's city is Lisbon.", "Please forget Mira city",
          "Mira's city is Paris.", "Who is Mira's city?",
          "WHO IS MIRA'S CITY?"]:
    add("q1", t)

fires = [(src, t) for src, t in texts
         if M.parse_me_teach(t) is not None or M.parse_me_ask(t) is not None]
print("scanned", len(texts), "fires", len(fires))
for src, t in fires:
    print("FIRE", src, repr(t))
# raw USER token in suite inputs (reply-rewrite blast radius check)
users = [(src, t) for src, t in texts if "USER" in t]
print("USER-token inputs:", len(users))
for src, t in users[:10]:
    print("USERIN", src, repr(t[:100]))
