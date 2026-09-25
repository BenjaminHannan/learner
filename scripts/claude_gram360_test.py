#!/usr/bin/env python3
"""gram-360 unit tests: slot rendering, untouched 1B parts, scorer markers kept. Prints "gram360 tests: N/N OK"."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_gram360 as G  # noqa: E402

CASES = [
    ("Saved: your city is vancouver.", "Saved: your city is Vancouver."),
    ("Just to check: is your running_buddy Viv?", "Just to check: is your running buddy Viv?"),
    ("Just to check: is she's age 84?", "Just to check: is her age 84?"),
    ("Just to check: is Her's father Tobias?", "Just to check: is her father Tobias?"),
    ("Just to check: is Ulla's children ['Sten', 'Viggo']?", "Just to check: are Ulla's children Sten and Viggo?"),
    ("I think you told me wyatt's age is 16, is that right?", "I think you told me Wyatt's age is 16, is that right?"),
    ("Whose boss is ulla, yours or someone else's?", "Whose boss is Ulla, yours or someone else's?"),
    ("Saved: your mother in law is Winona.", "Saved: your mother-in-law is Winona."),
    ("tiko's other is cockatiel.", "Cockatiel goes with Tiko."),
    ("I know 0 facts you taught me. I also hold 0 web row, which I do not believe.",
     "I know 0 facts you taught me. I also hold 0 web rows, which I do not believe."),
    ("Saved: Wendell's occupation is pastry chef.", "Saved: Wendell's occupation is pastry chef."),
    ("Just to check: is your employer warehouse?", "Just to check: is your employer warehouse?"),
    ("I don't know that one. I'd only be guessing.", "I don't know that one. I'd only be guessing."),
    ('I don\'t know that shape yet. Could you say it another way, like "Kim\'s boss is Lee."',
     'I don\'t know that shape yet. Could you say it another way, like "Kim\'s boss is Lee"?'),
    ("Saved: sprout's pet is gerbil.", "Saved: Sprout's pet is a gerbil."),
]


class _Loop:
    def __init__(self, parts_rule, parts_final):
        self.rule, self.final = parts_rule, parts_final

    def turn(self, text):
        return self.final


def main() -> int:
    ok = n = 0
    for src, want in CASES:
        n += 1
        got = G.realise(src)
        if got == want:
            ok += 1
        else:
            print("FAIL", repr(src), "->", repr(got), "want", repr(want))
    # 1B parts are never touched: only parts recorded from the rule agent change.
    n += 1
    loop = _Loop(None, None)
    rule_part, one_b = "Saved: your city is vancouver.", "i think vancouver is lovely."

    def inner_rule(text):
        return [rule_part]
    loop.turn = inner_rule
    G.record_inner360(loop)
    rec = loop.turn

    def outer(text):
        rec(text)
        return [rule_part, one_b]
    loop.turn = outer
    G.install_gram360(loop)
    out = loop.turn("my city is vancouver")
    if out == ["Saved: your city is Vancouver.", one_b]:
        ok += 1
    else:
        print("FAIL layer", out)
    print(f"gram360 tests: {ok}/{n} OK")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
