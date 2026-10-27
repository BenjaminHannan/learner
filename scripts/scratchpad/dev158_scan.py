#!/usr/bin/env python3
"""DEV-ONLY pre-seal input scan for exp 158 (not a registered run).

Pure-function scan: which sealed inputs would normalize_question_surface
even PROPOSE a candidate (eligible). Prints them for base ask-checks.
"""

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix158_qform as Q

ROOT = SCRIPTS.parent
texts: dict[str, list[str]] = {}


def add(src, t):
    texts.setdefault(src, []).append(t)


for tag, p in (("edit200", "data/open/bench65/fable_edit_200.jsonl"),
               ("old", "data/open/bench103/fable_edit103_s2fresh_4hop.jsonl"),
               ("new121", "data/open/bench121/fable_edit121_4hop.jsonl")):
    for line in (ROOT / p).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        for t in it.get("taught", []):
            add(tag + ":teach", str(t.get("sentence_en", "")))
        add(tag + ":q", str(it.get("question", "")))

s152 = json.loads((ROOT / "artifacts/fable-session152-20260922/sessions152.json")
                  .read_text(encoding="utf-8"))
for s in s152:
    for t in s["turns"]:
        add("sess152:" + s["id"], str(t["text"]))

import fable_redteam98_cases as RC
for c in RC.CASES:
    for st in c["steps"]:
        if st["op"] == "send":
            add("rt98:" + c["id"], str(st["text"]))
p4 = json.loads((ROOT / "artifacts/fable-loop102-20260921/p4-innocent-30.json")
                .read_text(encoding="utf-8"))
for item in p4["sentences"]:
    for t in list(item.get("setup", [])) + [item["text"]]:
        add("p4:" + item["id"], str(t))
rt110 = json.loads((ROOT / "artifacts/fable-redteam110-20260921/fable_redteam110_cases.json")
                   .read_text(encoding="utf-8"))
for c in rt110:
    for st in c.get("steps", []):
        if isinstance(st, dict) and "text" in st:
            add("rt110:" + c["id"], str(st["text"]))
import fable_redteam81_probe as P81
for seq_id, _d, steps in P81.SEQS:
    for st in steps:
        add("rt81:" + seq_id, str(st["turn"]))
rt136 = ROOT / "artifacts/fable-redteam136-20260922"
for f in sorted(rt136.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    def walk(o, src):
        if isinstance(o, str) and len(o) < 300 and (" " in o or "?" in o):
            add(src, o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v, src)
        elif isinstance(o, list):
            for v in o:
                walk(v, src)
    walk(d, "rt136:" + f.name)

total = sum(len(v) for v in texts.values())
elig = [(s, t) for s, vs in texts.items() for t in vs
        if Q.eligibility_ok(t, *Q.normalize_question_surface(t))
        if Q.normalize_question_surface(t)[0] is not None]
print(f"scanned={total} eligible={len(elig)}")
seen = set()
for s, t in elig:
    if t not in seen:
        seen.add(t)
        print(f"ELIGIBLE [{s}] {t!r}")
