#!/usr/bin/env python3
"""Exp 212 case-file builder (runs BEFORE the pilot; freezes turns).

Reads the pre-pilot screens (scratch) + panel sources, writes:
  artifacts/fable-selfgate212-20260922/case212-g.json (32 G-cases)
  artifacts/fable-selfgate212-20260922/case212-s.json (49 S-cases)
Only turns + expected classes are frozen here; all behaviour is verified
afterwards by the pilot and the registered runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfgate212-20260922"
SCR = ART / "scratch"

G_TURNS = [
    ("G01", "My favourite colour is teal."),
    ("G02", "Tired is my cat's name."),
    ("G03", "My favorite color is blue."),
    ("G04", "Milo is my hamster's name."),
    ("G05", "I feel happy today."),
    ("G06", "Mara feels happy."),
    ("G07", "Ben spoke quietly yesterday."),
    ("G08", "Oslo is better than Paris."),
    ("G09", "I dreamed last night."),
    ("G10", "Mara had a nightmare."),
    ("G11", "Sable is my sister's name."),
    ("G12", "My neighbour grows roses."),
    ("G13", "Mara feels sad."),
    ("G14", "Leo feels happy."),
    ("G15", "I feel tired."),
    ("G16", "Nora felt happy yesterday."),
    ("G17", "Paris is worse than Oslo."),
    ("G18", "Mara dreamed of flying."),
    ("G19", "Leo corrected the total."),
    ("G20", "I cannot sleep."),
    ("G21", "The source document arrived."),
    ("G22", "Teal is my favorite color."),
    ("G23", "My favourite song is Blue."),
    ("G24", "Nora feels happy."),
    ("G25", "I feel nervous."),
    ("G26", "Mara felt sad yesterday."),
    ("G27", "Ben said hi yesterday."),
    ("G28", "Yesterday Ben called Mara."),
    ("G29", "Worse than Paris is Oslo."),
    ("G30", "Pepper is the name of my cat."),
    ("G31", "Nora dreams nightly."),
    ("G32", "I know many facts."),
]

# (sid, source, selector) -- selector resolved against the panel sources.
S_SPEC = (
    [("S%02d" % (i + 1), "exp99", c) for i, c in enumerate(
        ["C1", "C2", "C3", "C5", "C6", "C8", "C10", "C11", "C14", "C15",
         "C16", "C18", "C21", "C24", "C26", "D1", "D2", "D3", "D5", "D7",
         "D8", "D9", "D10"])]
    + [("S%02d" % (i + 24), "exp100", c) for i, c in enumerate(
        ["Q01", "Q05", "Q11", "Q15", "Q29", "Q41", "Q51", "Q60"])]
    + [("S%02d" % (i + 32), "exp105", c) for i, c in enumerate(
        ["Q001", "Q009", "Q015", "Q021", "Q029", "Q031", "Q035", "Q039"])]
    + [("S%02d" % (i + 40), "exp187b", c) for i, c in enumerate(
        ["Q05", "Q10", "Q12", "U01"])]
    + [("S44", "extra", "Tell me about yourself."),
       ("S45", "extra", "Describe yourself."),
       ("S46", "extra", "You are clever."),
       ("S47", "extra", "You are brave."),
       ("S48", "extra", "I believe you are clever."),
       ("S49", "extra", "Nora baked you a pie.")]
)


def main() -> int:
    import fable_self99 as S99
    import fable_self100_runner as R100
    q99 = {q["id"]: q["text"] for q in S99.QUESTIONS}
    q100 = {str(qid): text for qid, _intent, text in R100.BLIND}
    pj = json.loads((ROOT / "artifacts" / "fable-self105panel-20260921"
                     / "panel.json").read_text(encoding="utf-8"))
    q105 = {q["id"]: q["question"] for q in pj["questions"]}
    cj = json.loads((ROOT / "artifacts" / "fable-selfq187b-20260922"
                     / "case187b.json").read_text(encoding="utf-8"))
    q187 = {c["id"]: c["turn"] for c in cj}

    g_cases, seen = [], set()
    for gid, turn in G_TURNS:
        assert turn not in seen, turn
        seen.add(turn)
        g_cases.append({"id": gid, "turn": turn,
                        "expected_class": "decline",
                        "expected_facts": []})
    assert len(g_cases) >= 30

    s_cases = []
    for sid, src, sel in S_SPEC:
        if src == "exp99":
            turn = q99[sel]
        elif src == "exp100":
            turn = q100[sel]
        elif src == "exp105":
            turn = q105[sel]
        elif src == "exp187b":
            turn = q187[sel]
        else:
            turn = sel
        s_cases.append({"id": sid, "src": f"{src}:{sel}", "turn": turn})
    assert len(s_cases) >= 40

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "case212-g.json").write_text(
        json.dumps(g_cases, indent=1, ensure_ascii=False), encoding="utf-8")
    (ART / "case212-s.json").write_text(
        json.dumps(s_cases, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(g_cases)} G-cases, {len(s_cases)} S-cases", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
