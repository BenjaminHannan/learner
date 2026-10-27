#!/usr/bin/env python3
"""Exp 173b dev-only pre-seal scan: run the 173b parsers over every sealed
input turn of every registered suite. NOT a registered run; no artifacts."""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_fix173b_username as B
import fable_fix173_username as N

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

# 173b vs 173 statement fires
stmt_b = [(src, t) for src, t in texts
          if B.parse_name_statement_173b(t) is not None]
stmt_173 = [(src, t) for src, t in texts
            if N.parse_name_statement(t) is not None]
ques_b = [(src, t) for src, t in texts
          if N.parse_name_question(t) is not None]
print("scanned", len(texts), "stmt173b", len(stmt_b),
      "stmt173", len(stmt_173), "question", len(ques_b))
for src, t in stmt_b:
    print("STMT173B-FIRE", src, repr(t))
for src, t in stmt_173:
    if B.parse_name_statement_173b(t) is None:
        print("STMT173-ONLY", src, repr(t))
for src, t in ques_b:
    print("Q-FIRE", src, repr(t))
print("DIFF-NEW (173b fires where 173 does not):",
      sum(1 for src, t in stmt_b if N.parse_name_statement(t) is None))
for src, t in stmt_b:
    if N.parse_name_statement(t) is None:
        print("NEW-FIRE", src, repr(t))
users = [(src, t) for src, t in texts if "USER" in t]
print("USER-token inputs:", len(users))
# New probe + 173 probes parse check
for name, path in (("cases173", ROOT / "artifacts/fable-username173-20260922/cases173.json"),
                   ("cases173b", ROOT / "artifacts/fable-username173b-20260922/cases173b.json")):
    try:
        rows = json.loads(Path(path).read_text())
    except Exception as exc:  # noqa: BLE001
        print(name, "unreadable", repr(exc))
        continue
    print(name, len(rows))
