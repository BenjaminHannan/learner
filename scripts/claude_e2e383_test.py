#!/usr/bin/env python3
"""CPU checks for scripts/claude_e2e383.py with stand-ins (no models). python -B scripts/claude_e2e383_test.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338b_agent as C38B  # noqa: E402
import claude_e2e383 as R  # noqa: E402

C38B.notebook_names = lambda loop: {"quill"}   # stand-in for the notebook's names (no fable_loop90 here)


class NB:
    def __init__(self):
        self.events = []


class Loop:
    def __init__(self, reply):
        self.nb, self.reply = NB(), reply

    def turn(self, text):
        return [self.reply(text)]


class Gen:
    def __init__(self, outs):
        self.outs = outs

    def sample_chat(self, msgs, n):
        return list(self.outs)


def main() -> int:
    ok = 0
    split = "I'm not sure. I worked it out a few times and got different answers."
    loop = Loop(lambda t: split if "?" in t else "Okay.")
    R.install_route383(loop, Gen(["Each friend pays 12 dollars, so the answer is 12."]))
    assert loop.turn("four friends split 48 dollars evenly, how much each?") == \
        ["Each friend pays 12 dollars, so the answer is 12."]; ok += 1
    assert loop.route383_stats["replaced_think_split"] == 1; ok += 1
    assert loop.turn("what's my sister's name?") == [split]; ok += 1          # about the user: honest line kept
    assert loop.turn("where does Quill live?") == [split]; ok += 1            # a notebook name: kept
    assert loop.route383_stats["people_kept"] == 2; ok += 1
    assert loop.turn("i like tea") == ["Okay."]; ok += 1                       # not a question, no abstain
    loop2 = Loop(lambda t: "I'm not sure.")
    R.install_route383(loop2, Gen(["I'll remember that, it's B.", "The answer is B."]))
    assert loop2.turn("Which gas do plants take in? A) oxygen B) carbon dioxide") == ["The answer is B."]; ok += 1
    assert loop2.route383_stats["G1"] == 1 and loop2.route383_stats["replaced_other"] == 1; ok += 1
    loop3 = Loop(lambda t: "I'm not sure.")
    R.install_route383(loop3, Gen(["I'll remember that."]))
    assert loop3.turn("why is the sky blue?") == ["I'm not sure."] and loop3.route383_stats["all_failed"] == 1; ok += 1
    print(f"claude_e2e383_test: {ok}/9 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
