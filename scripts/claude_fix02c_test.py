#!/usr/bin/env python3
"""CPU checks for scripts/claude_fix02c.py with stand-ins (no models). python -B scripts/claude_fix02c_test.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_chat338b_agent as C38B  # noqa: E402
import claude_fix02c as F  # noqa: E402

C38B.notebook_names = lambda loop: set()


class NB:
    def __init__(self):
        self.events = []


class Loop:
    def __init__(self, reply, d="."):
        self.nb, self.reply, self.dir = NB(), reply, d

    def turn(self, text):
        return [self.reply(text)]


class Gen:
    def __init__(self, outs):
        self.outs = outs

    def sample_chat(self, msgs, n):
        return list(self.outs)


class Store:
    def __init__(self, rows):
        self.rows = list(rows)

    def remember(self, text, **kw):
        self.rows.append(dict(kw, text=text, id=f"h{len(self.rows) + 1:07d}"))


def main() -> int:
    ok = 0
    # F1: the chat history keeps the reply the user actually saw
    with tempfile.TemporaryDirectory() as d:
        loop = Loop(lambda t: "Okay.", d)
        C38.install_chat338(loop, Gen([]))
        state, save = F.chat338_state(loop.turn)
        inner = loop.turn

        def outer(t):                                      # an outer layer replaces the chat layer's reply
            parts = inner(t)
            return ["Twelve, since 3 times 4 is 12."] if "?" in t else parts
        loop.turn = outer
        F.install_delivered02c(loop, state, save)
        loop.turn("what is 3 times 4?")
        assert state["history"][-1]["content"] == "Twelve, since 3 times 4 is 12."; ok += 1
        saved = json.loads((Path(d) / C38.STATE_NAME338).read_text(encoding="utf-8"))
        assert saved["history"][-1]["content"] == "Twelve, since 3 times 4 is 12."; ok += 1
        assert loop.delivered02c_stats["rewritten"] == 1; ok += 1
    # F2: the final answer after the last full stop is kept
    assert F.trim02c("First 3*4=12. Then add 5.\nThe answer is 17") == "First 3*4=12. Then add 5. The answer is 17"; ok += 1
    assert F.trim02c("Plants take in carbon dioxide. Answer: B") == "Plants take in carbon dioxide. Answer: B"; ok += 1
    assert F.trim02c("It is warm today. and then the") == "It is warm today."; ok += 1   # plain cut-off stays cut
    loop2 = Loop(lambda t: "I'm not sure.")
    F.install_route02c(loop2, Gen(["Each pays 48 / 4 = 12 dollars.\nThe answer is 12"]))
    assert loop2.turn("four friends split 48 dollars evenly, how much each?") == \
        ["Each pays 48 / 4 = 12 dollars. The answer is 12"]; ok += 1
    assert loop2.route383_stats["tail_kept"] == 1; ok += 1
    assert loop2.turn("what's my sister's name?") == ["I'm not sure."]; ok += 1        # about the user: kept
    # F3: the date carries over a restart
    st = Store([{"id": "h0000001", "source": "heard", "text": "DATE: 8 May 2023", "said_at": "8 May 2023"}])
    loop3 = Loop(lambda t: "Okay.")
    F.install_heard02c(loop3, st)
    loop3.turn("I started a pottery class.")
    assert st.rows[-1]["said_at"] == "8 May 2023" and st.rows[-1]["turn_ids"] == [2]; ok += 1
    # F4: report-only one-row support
    rows = [{"text": "Ana lives in Paris", "speaker": "user"}, {"text": "Bo lives in Rome", "speaker": "user"}]
    assert not F.one_row_supported("She lives in Rome.", "Where does Ana live?", rows); ok += 1
    assert F.one_row_supported("She lives in Paris.", "Where does Ana live?", rows); ok += 1
    print(f"claude_fix02c_test: {ok}/12 OK")
    return 0 if ok == 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())
