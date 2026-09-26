#!/usr/bin/env python3
"""y1w: memory questions the notebook does not answer get answered from the user's own words (Answering-from-memory
thread, 2026-09-26). New file; imports the sealed 0.2c build and ep-382 without editing them. DRAFT until sealed.

The one change, on top of the 0.2c joined agent (claude_e2e02c.build_02c, lis-319 reader, sleep adapter):
the ep-382 memory store is on (heard rows only; STORE02C = store v3, as build_02c already wires it) and ep-382's
answer step runs on a question turn when the agent's final reply
  (a) abstains or asks to rephrase (382b's trigger), or
  (b) is turn310's ask-back ("Just to check: ...?"), which on a question turn means the reader misread the question
      as a statement to save.
The answer step is ep-382's own (SYSTEM382, 4 samples, 338 strict guard + G5, abstaining samples skipped, fail
closed). Two settings, fixed at the seal from the DEV diagnosis y1d (artifacts/claude-y1d-20260926):
  K_Y1W      rows recalled (20, as 382b)
  ORDER_Y1W  "rank" (store order, as 382b) or "time" (the recalled rows sorted oldest first)
When (b) is replaced, turn310's pending ask-back is dropped (loop.lis310_pending = None), so a later "yes" cannot
save the misread fact. lis-314's confirm-at-use ("I think you told me ..., is that right?") is never replaced: it
names a held fact for the very thing asked, and a "yes" to it is how that fact gets saved.
Nothing here writes the notebook (checked every turn, as 382).

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --arm claude_y1w_answer:build_y1w --name W ...
  python -B scripts/claude_y1w_answer.py --selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

K_Y1W = 20
ORDER_Y1W = "rank"
ASKBACK_PREFIX = "just to check:"


def askback_reply(reply: str) -> bool:
    return reply.strip().lower().startswith(ASKBACK_PREFIX) and reply.strip().endswith("?")


def _order(rows: list[dict]) -> list[dict]:
    if ORDER_Y1W == "time":
        return sorted(rows, key=lambda r: (min(r.get("turn_ids") or [0]), r.get("id", "")))
    return rows


def install_answer_y1w(loop, gen, store, k: int = K_Y1W, n: int | None = None) -> None:
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_e2e382 as E
    n = E.N382 if n is None else n
    inner = loop.turn
    loop.ep382_stats = {"turns": 0, "tried": 0, "tried_askback": 0, "no_rows": 0, "replaced": 0,
                        "replaced_askback": 0, "all_failed": 0, "abstained": 0,
                        "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}
    st = loop.ep382_stats

    def answer_y1w(text: str) -> list[str]:
        st["turns"] += 1
        ev0 = len(loop.nb.events)
        parts = inner(text)
        reply = " ".join(p for p in (parts or []) if p)
        if not (C38B.is_question(text) and len(loop.nb.events) == ev0
                and getattr(loop, "lis314_confirming", None) is None):
            return parts
        ask_back = askback_reply(reply) and getattr(loop, "lis310_pending", None) is not None
        if not (E.abstains(reply) or ask_back):
            return parts
        st["tried"] += 1
        st["tried_askback"] += int(ask_back)
        rows = _order(store.recall(E.query_of(text), k=k))
        if not rows:
            st["no_rows"] += 1
            E._log({"state": str(getattr(loop, "dir", "")), "outcome": "no_rows", "askback": ask_back})
            return parts
        fails = []
        known = C38._words([text] + [r["text"] for r in rows] + [r.get("said_at") or "" for r in rows])
        msgs = [{"role": "system", "content": E.SYSTEM382 + "\n\n" + E._rows_block(rows)},
                {"role": "user", "content": text}]
        for c in gen.sample_chat(msgs, n):
            c = C38.trim(c)
            g = C38.guard(c, text, known, strict=True) or ("G5" if E.g5_unsupported(c, known) else None)
            if g is not None:
                st[g] += 1
                fails.append(g)
                continue
            if E.abstains(c):
                st["abstained"] += 1
                fails.append("abstained")
                continue
            if len(loop.nb.events) != ev0:
                raise RuntimeError("y1w: answer phase wrote to the notebook")
            if ask_back:
                loop.lis310_pending = None          # the misread "fact" is not held for a later "yes"
                st["replaced_askback"] += 1
            st["replaced"] += 1
            loop.ep382_last_rows = [r["id"] for r in rows]
            E._log({"state": str(getattr(loop, "dir", "")), "outcome": "replaced", "askback": ask_back,
                    "rows": loop.ep382_last_rows, "fails": fails})
            return [c]
        st["all_failed"] += 1
        E._log({"state": str(getattr(loop, "dir", "")), "outcome": "all_failed", "askback": ask_back,
                "rows": [r["id"] for r in rows], "fails": fails})
        return parts

    answer_y1w.__name__ = "answer382"          # build_02c's layer list names the slot "answer382"
    loop.turn = answer_y1w


def build_y1w(state_dir, args):
    """build_02c with MEM02C = K_Y1W and ep-382's answer step swapped for install_answer_y1w, for this call only."""
    import claude_e2e02c as X
    import claude_e2e382 as E
    old_mem, old_install = X.MEM02C, E.install_answer382
    X.MEM02C = K_Y1W
    E.install_answer382 = install_answer_y1w
    try:
        loop = X.build_02c(state_dir, args)
    finally:
        X.MEM02C, E.install_answer382 = old_mem, old_install
    loop.layers330c = [("answer_y1w" if x == "answer382" else x) for x in loop.layers330c]
    loop.y1w = {"k": K_Y1W, "order": ORDER_Y1W}
    return loop


# ---------------------------------------------------------------- CPU checks (no models)
class _NB:
    def __init__(self):
        self.events = []


class _Loop:
    def __init__(self, reply):
        self.nb, self.reply = _NB(), reply
        self.lis314_confirming = None
        self.lis310_pending = None

    def turn(self, text):
        r = self.reply(self, text)
        return [r]


class _Gen:
    def __init__(self, outs):
        self.outs, self.seen = outs, []

    def sample_chat(self, msgs, n):
        self.seen.append(msgs)
        return list(self.outs)


def selftest() -> None:
    import tempfile
    import claude_e2e382 as E
    import claude_ep382_store_v2 as ST

    class BM25Store(ST.MemoryStore):
        def recall(self, query, **kw):
            return super().recall(query, mode="bm25", **kw)

    global ORDER_Y1W
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        st = BM25Store(d)

        def agent(lp, t):
            if t.startswith("ziggy's"):                       # a question misread as a statement: ask-back
                lp.lis310_pending = {"fact": {"owner": "Ziggy", "rel": "breed", "value": "beagle"}}
                return "Just to check: is Ziggy's breed beagle?"
            if t.startswith("how old"):
                return "I don't know."
            if t.startswith("what's my cat"):
                lp.lis314_confirming = {"owner": "me", "rel": "cat", "value": "Smudge"}
                return "I think you told me your cat is Smudge, is that right?"
            if t.startswith("tell me"):
                return "Sure, here is one."
            return "Saved."
        loop = _Loop(agent)
        gen = _Gen(["Ziggy is 4.", "Yes, Ziggy is a beagle."])
        install_answer_y1w(loop, gen, st)
        E.install_heard382(loop, st)
        for t in ["my beagle Ziggy turned 4 today", "my cat is Smudge", "i moved to Tarrow"]:
            loop.turn(t)
        assert len(st.rows) == 3; ok += 1
        assert loop.turn("how old is ziggy?") == ["Ziggy is 4."]; ok += 1               # (a) abstain replaced
        gen.outs = ["Yes, Ziggy is a beagle."]
        assert loop.turn("ziggy's a beagle, right?") == ["Yes, Ziggy is a beagle."]; ok += 1   # (b) ask-back replaced
        assert loop.lis310_pending is None and loop.ep382_stats["replaced_askback"] == 1; ok += 1
        out = loop.turn("what's my cat called?")                                          # confirm-at-use kept
        assert out == ["I think you told me your cat is Smudge, is that right?"], out; ok += 1
        loop.lis314_confirming = None
        assert loop.turn("tell me a joke?") == ["Sure, here is one."]; ok += 1              # a real answer is kept
        gen.outs = ["I don't know.", "Your sister Quill lives there."]                    # abstain + G2/G3 -> fail closed
        assert loop.turn("how old is my sister?") == ["I don't know."]; ok += 1
        # ask-back with the samples all failing: the ask-back stays and stays pending
        gen.outs = ["I don't know."]

        def agent2(lp, t):
            lp.lis310_pending = {"fact": {"owner": "Wren", "rel": "age", "value": "9"}}
            return "Just to check: is Wren's age 9?"
        loop.reply = agent2
        assert loop.turn("wren's 9 right?") == ["Just to check: is Wren's age 9?"] and loop.lis310_pending; ok += 1
        # order: time sorts recalled rows oldest first
        ORDER_Y1W = "time"
        rows = [{"id": "h2", "turn_ids": [5]}, {"id": "h1", "turn_ids": [2]}]
        assert [r["id"] for r in _order(rows)] == ["h1", "h2"]; ok += 1
        ORDER_Y1W = "rank"
        assert [r["id"] for r in _order(rows)] == ["h2", "h1"]; ok += 1
    print(f"selftest ok ({ok}/10)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
