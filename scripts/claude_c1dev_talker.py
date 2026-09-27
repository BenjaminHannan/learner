#!/usr/bin/env python3
"""c1-dev: 0.2d's talker alone, for a practice-chat check of row C1 (everyday-chat thread, 2026-09-27). New file only.

Why: the Thread manager (00:19 UTC 09-27) asked whether C1's no-harm bar (margin >= -12 of 60 against every rival,
02d ADDENDUM-14) is reachable at all with a plain 1B talker, before the build runs. Measured on the readable DEV
practice chats (artifacts/claude-chatdev-20260926), never on chatpanel404, which is TEST-ONLY and runs once.
Plan and marks: artifacts/claude-c1dev-20260927/PLAN.md.

What: build_talker02d(state_dir, args) is claude_e2e02d.Agent02d, unchanged, with two parts left out:
  - the reader (lis-320) is a null reader that saves nothing. On a chat whose earlier user turns fit in CTX_CHARS02D
    characters, the talker's input does not depend on the reader: the W block is every earlier user turn verbatim
    ("heard" rows), and saved facts ("note" rows) reach the talker only in the top-k case (claude_e2e02d.w_rows).
    selftest case 1 checks this against the 0.2d selftest's saving reader. A longer chat stops the arm (guard).
  - the reasoner (358b3): none. A number-square turn stops the arm (Agent02d._reason raises with REASONER02D unset).
    The DEV chats hold none (claude_puzzle_reader.read_latin finds 0 of 336 turns).
The talker is claude_e2e02d.Talker exactly as the build loads it: plain MiniCPM5-1B, greedy, thinking off, the 336
twin's system line, the W block in the system message (W_PLACE02D as committed), the last 6 exchanges, 160 new tokens.

  python -B scripts/claude_twinb_wrap.py scripts/claude_ch403_run.py run --panel-dir artifacts/claude-chatdev-20260926 \
      --arm claude_c1dev_talker:build_talker02d --name D --gen-model BASE --out OUT
  python3 -B scripts/claude_c1dev_talker.py --selftest        (CPU, stub talker, no model)
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_e2e02d as E  # noqa: E402


class NullReader:
    """Reads nothing and saves nothing (lis-320's place; see the docstring for why the talker input is unchanged)."""

    def read(self, turn, prev="", hist=None):
        return ({"act": "CHAT", "facts": []}, [], "", 0.0)


class TalkerOnly02d(E.Agent02d):
    def turn(self, text: str) -> list[str]:
        heard = sum(len(r["text"]) for r in self.store.rows if r.get("source") == "heard") + len(text)
        if heard > E.CTX_CHARS02D:
            raise SystemExit("c1dev: this chat is longer than CTX_CHARS02D; the reader would change the talker input")
        return super().turn(text)


def settings() -> str:
    return (f"c1dev: talker = claude_e2e02d.Talker; W_PLACE02D={E.W_PLACE02D}; MAX_NEW02D={E.MAX_NEW02D}; "
            f"HIST_PAIRS={E.HIST_PAIRS}; SLEEP02D={E.SLEEP02D or 'off'}; reader = none; reasoner = none")


def build_talker02d(state_dir, args):
    import claude_ep382_store_v4 as V4
    if E.SLEEP02D:
        raise SystemExit("c1dev: SLEEP02D is set; this check is the plain talker")
    agent = TalkerOnly02d(state_dir, NullReader(), E.talker_for(getattr(args, "gen_model", "")), None,
                          V4.MemoryStore(state_dir), int(getattr(args, "max_new", 0) or E.MAX_NEW02D))
    if not getattr(build_talker02d, "_said", False):
        print(settings(), flush=True)
        build_talker02d._said = True
    return agent


def selftest() -> None:
    import tempfile
    import claude_e2e336_twin as TW
    import claude_lis300_compiler as CMP
    import claude_y1f_layout as Y
    import claude_ep382_store_v4 as V4
    ok = 0
    rel = sorted(CMP.REL_NAMES)[0]

    class SavingReader:                                   # the 0.2d selftest's stub: saves "my dog is X" at 0.999
        def read(self, turn, prev="", hist=None):
            if "my dog is" in turn.lower():
                return ({"act": "ASSERT", "facts": [{"owner": "me", "rel": rel, "value": turn.rstrip(".").split()[-1],
                                                      "mode": "ASSERT"}]}, [0.999], "", 1.0)
            return ({"act": "CHAT", "facts": []}, [], "", 1.0)

    class StubTalker:
        hit_max = 0

        def __init__(self):
            self.seen = []

        def reply(self, system, msgs, max_new):
            self.seen.append((system, [dict(m) for m in msgs], max_new))
            return "ok " + msgs[-1]["content"][:12]

    chat = ["hi there", "my dog is Rex.", "any tips for a rainy weekend?", "and what should I cook tonight?"]

    def talk(agent_cls, reader, d):
        tk = StubTalker()
        ag = agent_cls(d, reader, tk, None, V4.MemoryStore(d))
        outs = [ag.turn(t) for t in chat]
        return tk, ag, outs

    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        tk_full, ag_full, out_full = talk(E.Agent02d, SavingReader(), t1)
        tk_null, ag_null, out_null = talk(TalkerOnly02d, NullReader(), t2)
        assert ag_full.nb.events and not ag_null.nb.events       # the saving reader did save a fact
        assert tk_full.seen == tk_null.seen and out_full == out_null; ok += 1
        s1, m1, n1 = tk_null.seen[0]
        assert s1 == TW.SYSTEM and m1 == [{"role": "user", "content": chat[0]}] and n1 == E.MAX_NEW02D; ok += 1
        s3, m3, _ = tk_null.seen[2]
        want = TW.SYSTEM + "\n\n" + Y.L1_HEAD + 'User said, "hi there"\nUser said, "my dog is Rex."\n'
        assert E.W_PLACE02D != "system" or s3 == want; ok += 1
        assert [m["role"] for m in m3] == ["user", "assistant", "user", "assistant", "user"] and m3[-1]["content"] == chat[2]
        ok += 1
    with tempfile.TemporaryDirectory() as t3:
        ag = TalkerOnly02d(t3, NullReader(), StubTalker(), None, V4.MemoryStore(t3))
        try:
            ag.turn("x" * (E.CTX_CHARS02D + 1))
            raise AssertionError("long chat accepted")
        except SystemExit:
            ok += 1
    with tempfile.TemporaryDirectory() as t4:
        ag = TalkerOnly02d(t4, NullReader(), StubTalker(), None, V4.MemoryStore(t4))
        try:
            ag.turn("Can you finish this number square?\n1 2 _\n_ 3 1\n3 _ 2")   # the 0.2d selftest's grid turn
            raise AssertionError("grid turn accepted without a reasoner")
        except SystemExit:
            ok += 1
    print(settings())
    print(f"c1dev talker selftest: {ok}/6 OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
