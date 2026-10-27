#!/usr/bin/env python3
"""Exp 129 Step 0 probe: which teach/correct paths leak sentence punctuation.

Read-only vs existing modules (imports only, never edits). For each teach
path in loop102/113/113b/117/121 it feeds punctuated sentences through the
REAL parser/stage used on that path and reports whether the captured
subject/value keeps trailing sentence punctuation.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_fix129_probe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A
import fable_bench73_english_arm as B73
import fable_bench92_english_arm as B92

PATHS: list[tuple[str, str]] = [
    ("loop102-F3-correction/loop121-teach", "bench73 citizen + period"),
    ("loop102-F3-correction/loop121-teach", "bench73 capital + period"),
    ("loop102-F3-correction/loop121-teach", "bench73 official-language + period"),
    ("loop102-F3-correction/loop121-teach", "bench73 citizen + !"),
    ("loop102-F3-correction/loop121-teach", "bench73 citizen + ?"),
    ("loop102-F3-correction/loop121-teach", "bench73 citizen + trailing spaces"),
    ("loop102-F3-correction/loop121-teach", "bench73 apprentice_of + period (explicit-dot pattern)"),
    ("loop121-extra", "b92 employer + period"),
    ("loop121-extra", "b92 occupation + period"),
    ("loop121-extra", "b92 child + period"),
    ("loop96-chain-fake", "fake possessive + period"),
    ("loop96-chain-fake", "fake possessive + !"),
    ("loop96-chain-fake", "fake possessive + ?"),
]

SENTENCES: dict[str, str] = {
    "bench73 citizen + period": "AJ Lee is a citizen of Italy.",
    "bench73 capital + period": "The capital of Poland is Warsaw.",
    "bench73 official-language + period": "The official language of Spain is Spanish.",
    "bench73 citizen + !": "AJ Lee is a citizen of Italy!",
    "bench73 citizen + ?": "AJ Lee is a citizen of Italy?",
    "bench73 citizen + trailing spaces": "AJ Lee is a citizen of Italy.  ",
    "bench73 apprentice_of + period (explicit-dot pattern)":
        "Elowen Frostmere is the apprentice of Orson Vell.",
    "b92 employer + period": "Ada Lovelace is employed by Analytical Engines.",
    "b92 occupation + period": "Ada Lovelace works in the field of Mathematics.",
    "b92 child + period": "Ada Lovelace's child is Byron King.",
    "fake possessive + period": "Mira's city is Paris.",
    "fake possessive + !": "Mira's city is Paris!",
    "fake possessive + ?": "Mira's city is Paris?",
}


def check_bench73(sent: str) -> str:
    t = B73.hear_teach_template(sent)
    if t is None:
        return "NO-PARSE (no write)"
    leak = t[0][-1:] in ".!?;: " or t[2][-1:] in ".!?;: "
    return f"triple={t!r} -> {'LEAK' if leak else 'clean'}"


def check_b92(sent: str) -> str:
    t = B92.hear_teach92(sent)
    if t is None:
        return "NO-PARSE (no write)"
    leak = t[0][-1:] in ".!?;: " or t[2][-1:] in ".!?;: "
    return f"triple={t!r} -> {'LEAK' if leak else 'clean'}"


def check_fake(sent: str) -> str:
    acts = A.FakeEars().hear(sent)
    if len(acts) != 1 or acts[0].get("act") not in ("teach", "correct"):
        return f"{acts!r} -> NO-WRITE (clarify)"
    a = acts[0]
    leak = a["name"][-1:] in ".!?;:" or a["value"][-1:] in ".!?;:"
    return (f"name={a['name']!r} value={a['value']!r} -> "
            f"{'LEAK' if leak else 'clean'}")


def main() -> int:
    print("EXP129 STEP0: teach-path punctuation probe (old code, read-only)")
    for path, key in PATHS:
        sent = SENTENCES[key]
        if path.startswith("loop96"):
            res = check_fake(sent)
        elif path.startswith("loop121"):
            res = check_b92(sent)
        else:
            res = check_bench73(sent)
        print(f"- [{path}] {sent!r}\n    {res}")
    print("\nNOTE: loop113/113b/117/121 delegate non-'?' teach turns to the "
          "loop102 pre-filter + loop96 chain (Bench73Stage + FakeStage), so "
          "the three parsers above cover every teach path in all five loops.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
