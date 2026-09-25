#!/usr/bin/env python3
"""gram-364 unit tests: v2 slot rendering, gram-360 behaviour kept elsewhere, scorer markers kept.
Prints "gram364 tests: N/N OK"."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_gram360_test as T360  # noqa: E402
import claude_gram364 as V  # noqa: E402

CHANGED = {                                   # gram-360 cases whose v2 rendering is meant to differ
    "tiko's other is cockatiel.": 'Your note about Tiko says "cockatiel".',
    "Just to check: is your employer warehouse?": "Just to check: is your employer a warehouse?",
}
CASES = [
    ("Saved: Taj's other is maths.", 'Saved: your note about Taj says "maths".'),
    ("Just to check: is tuva's other saturday?", 'Just to check: does your note about Tuva say "Saturday"?'),
    ("Saved: your other is Viv.", 'Saved: your note says "Viv".'),
    ("Just to check: is Saoirse's child me?", "Just to check: are you Saoirse's child?"),
    ("I think you told me uriah's cat is me, is that right?", "I think you told me you are Uriah's cat, is that right?"),
    ("Just to check: is uriah's hamster sprout?", "Just to check: is Uriah's hamster Sprout?"),
    ("Just to check: is your dog limping?", "Just to check: is your dog limping?"),
    ("Just to check: is your cat sick?", "Just to check: is your cat sick?"),
    ("Just to check: is hamster's other zadie?", 'Just to check: does your note about the hamster say "zadie"?'),
    ("Saved: your occupation is er nurse.", "Saved: your occupation is ER nurse."),
    ("Saved: your occupation is nurse.", "Saved: your occupation is nurse."),
    ("Just to check: is your pet bearded dragon?", "Just to check: is your pet a bearded dragon?"),
    ("Just to check: is your pet a gerbil?", "Just to check: is your pet a gerbil?"),
    ("Saved: sprout's pet is gerbil.", "Saved: Sprout's pet is a gerbil."),
    ("Just to check: is mum's garden Upwood Gardens?", "Just to check: is Mum's garden Upwood Gardens?"),
]


def main() -> int:
    ok = n = 0
    for src, want in [(s, CHANGED.get(s, w)) for s, w in T360.CASES] + CASES:
        n += 1
        got = V.realise364(src)
        if got == want:
            ok += 1
        else:
            print("FAIL", repr(src), "->", repr(got), "want", repr(want))
    # every slot's letters survive (the scorers compare lowercase words)
    for src, _ in CASES:
        n += 1
        a = set(w.strip("\"'?.,:").lower() for w in src.replace("_", " ").split())
        b = set(w.strip("\"'?.,:").lower() for w in V.realise364(src).split())
        lost = {w for w in a - b if w not in {"is", "other", "me", "i", "a", "an"} and not w.endswith("'s")}
        if lost:
            print("FAIL lost", src, lost)
        else:
            ok += 1
    print(f"gram364 tests: {ok}/{n} OK")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
