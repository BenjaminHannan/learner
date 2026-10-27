#!/usr/bin/env python3
"""Exp 227 Step 0 census: identity questions on loop138i, fresh notebook."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

QUESTIONS = [
    "What is your name?",
    "What are you called?",
    "Do you have a name?",
    "What is your name called?",
    "What should I call you?",
    "Who made you?",
    "Who built you?",
    "Who created you?",
    "Who invented you?",
    "Who designed you?",
    "Who is your maker?",
    "Who is your creator?",
    "What are you?",
    "Are you a person?",
    "Are you a human?",
    "Are you a robot?",
    "Are you a machine?",
    "Are you a program?",
    "Are you software?",
    "How do you work?",
    "How do you learn?",
    "How do you learn new things?",
    "How do you remember things?",
    "How old are you?",
    "What is your age?",
    "Where do you live?",
    "Where are you from?",
    "Do you live anywhere?",
    "What is your home?",
    "Who taught you?",
    "What do you know?",
    "Do you know my name?",
    "Do you remember my name?",
    "What is my name?",
    "Who am I?",
    "What is Ben's name?",
    "Are you Ben?",
    "Do you have feelings?",
    "Do you dream?",
    "Can you learn my name?",
    "Who is Ben?",
    "Are you alive?",
    "Do you sleep?",
    "What can you do?",
    "What can you not do?",
]

def main() -> int:
    import fable_loop138i_agent as L138I
    import fable_loop138_agent as L138
    tmp = tempfile.mkdtemp(prefix="census227_")
    cfg = dict(L138I.DEFAULT_CONFIG138I)
    cfg["state_dir"] = tmp
    loop = L138I.build_agent138i(cfg)
    rows = []
    for q in QUESTIONS:
        before = set(loop.nb.facts)
        said = loop.turn(q)
        reply = " ".join(said)
        after = set(loop.nb.facts)
        routed = getattr(loop, "last_routed", None)
        intent = routed["intent"] if routed else None
        # also record route127 directly
        r127, _ = L138._route127(q)
        rows.append({"q": q, "reply": reply, "routed": intent,
                     "route127": r127,
                     "wrote": len(after - before) > 0})
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPTS / "fable_identity227_census_rows.json"
    Path(out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in rows:
        print(f"Q={r['q']}\n  route127={r['route127']} routed={r['routed']} wrote={r['wrote']}\n  A={r['reply']}\n")
    print(f"WROTE {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
