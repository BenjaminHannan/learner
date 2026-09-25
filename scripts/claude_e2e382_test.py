#!/usr/bin/env python3
"""CPU checks for scripts/claude_e2e382.py with stand-ins (no models). python -B scripts/claude_e2e382_test.py"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_e2e382 as E  # noqa: E402
import claude_ep382_store_v2 as ST  # noqa: E402


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
        self.outs, self.seen = outs, []

    def sample_chat(self, msgs, n):
        self.seen.append(msgs)
        return list(self.outs)


class BM25Store(ST.MemoryStore):
    def recall(self, query, **kw):
        return super().recall(query, mode="bm25", **kw)


def main() -> int:
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        st = BM25Store(d)
        loop = Loop(lambda t: "I'm not sure. I don't think you've told me that yet." if "?" in t else "Okay.")
        gen = Gen(["You moved to Zorblat.", "You moved to Tarrow in May.", "I don't know."])
        E.install_answer382(loop, gen, st)
        E.install_heard382(loop, st)
        assert loop.turn("DATE: 8 May, 2023\nCONVERSATION:") == ["Okay."]
        assert loop.turn("i finally moved to Tarrow last week") == ["Okay."]
        assert [r["said_at"] for r in st.rows] == ["8 May, 2023", "8 May, 2023"]; ok += 1
        out = loop.turn("where did i move to?")
        assert out == ["You moved to Tarrow in May."], out; ok += 1          # G3 drops the made-up name first
        assert loop.ep382_stats["G3"] == 1 and loop.ep382_stats["replaced"] == 1; ok += 1
        assert "where did i move to?" not in gen.seen[-1][0]["content"]; ok += 1   # the question is not a row
        assert len(st.rows) == 3 and st.rows[-1]["turn_ids"] == [3]; ok += 1
        gen.outs = ["I don't know.", "Your sister Quill lives there."]
        before = loop.ep382_stats["all_failed"]
        out = loop.turn("who lives in Tarrow?")
        assert out == ["I'm not sure. I don't think you've told me that yet."], out
        assert loop.ep382_stats["all_failed"] == before + 1; ok += 1         # fail closed
        assert loop.turn("tell me a joke") == ["Okay."]; ok += 1             # not a question and no abstain
        gen.outs = ["Paris.", "Tarrow."]
        assert loop.turn("which town did i move to?") == ["Tarrow."]; ok += 1  # G5: one-word made-up answer dropped
        assert E.query_of("Based on the chat. Question: When did X go? Answer:") == "Question: When did X go?"; ok += 1
    with tempfile.TemporaryDirectory() as d:
        st = BM25Store(d)
        loop = Loop(lambda t: "I'm not sure.")
        E.install_answer382(loop, Gen(["x"]), st)
        loop.turn("what is my name?")
        assert loop.ep382_stats["no_rows"] == 1; ok += 1                    # empty store: nothing tried
    print(f"claude_e2e382_test: {ok}/10 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
