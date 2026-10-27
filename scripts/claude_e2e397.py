#!/usr/bin/env python3
"""397: the copy-only answer trim on the joined agent's memory answers (benchmarks thread, 2026-09-26). New file only.

What: after ep-382's memory path (claude_e2e382.install_answer382) replaces a reply, the sealed bm-397 finaliser
(scripts/claude_bm397_finalize.py finalise) asks the same base 1B, greedily and with thinking off, for the shortest
answer made only of the reply's own words. Code keeps the reply unchanged when it abstains, when the output is
empty, or when the output uses any word more often than the reply does. Nothing else changes: replies from the
chat, route383, the notebook, the reasoner or anywhere else are never touched, so general and math answers are
untouched by construction. Nothing here writes the notebook (checked).
Why: bm-396 found the plain 1B's LoCoMo answers are about 8 words where 3 are needed (precision 23.7 vs Qwen3.5-2B's
54.5 at similar recall). bm-397 (artifacts/claude-bm397-20260926/) measures this finaliser on existing replies.

Placement: directly on top of answer382, below route383 (so a route383 reply is never trimmed). build_397e and
build_397b get there without editing any sealed build: while month-end's build runs, install_answer382 is wrapped
so that trim397 is installed right after it, and the original is restored afterwards (even on an error).

build_397e = build_383e (ER) + trim397.   build_397b = build_382b (E) + trim397.
Counters: loop.trim397_stats (turns, memory_answers, changed, and each kept reason).

  python -B scripts/claude_e2e397.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_bm397_finalize as F  # noqa: E402


def greedy397(g):
    """The bm-397 call (claude_bm390.generate) on an already-loaded model: g has .tok, .model, .dev, .torch."""
    def gen(system: str, user: str) -> str:
        import claude_bm390 as B
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        enc = g.tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                                        return_dict=True, return_tensors="pt").to(g.dev)
        n = int(enc["input_ids"].shape[1])
        pad = g.tok.pad_token_id if g.tok.pad_token_id is not None else g.tok.eos_token_id
        with g.torch.no_grad():
            out = g.model.generate(**enc, max_new_tokens=F.MAX_NEW397, do_sample=False, pad_token_id=pad)
        return B.strip_think(g.tok.decode(out[0][n:], skip_special_tokens=True))
    return gen


def install_trim397(loop, gen) -> None:
    """gen(system, user) -> text, greedy. Trims only turns whose reply came from answer382 this turn."""
    inner = loop.turn
    loop.trim397_stats = {"turns": 0, "memory_answers": 0, "changed": 0}

    def trim397(text: str) -> list[str]:
        st = loop.trim397_stats
        st["turns"] += 1
        before = dict(getattr(loop, "ep382_stats", {}) or {}).get("replaced", 0)
        parts = inner(text)
        after = (getattr(loop, "ep382_stats", {}) or {}).get("replaced", 0)
        live = [p for p in (parts or []) if p]
        if after == before or len(live) != 1:
            return parts
        st["memory_answers"] += 1
        ev1 = len(loop.nb.events)
        new, why = F.finalise(text, live[0], gen)
        if len(loop.nb.events) != ev1:
            raise RuntimeError("397: trim phase wrote to the notebook")
        st[why] = st.get(why, 0) + 1
        return [new] if why == "changed" else parts

    trim397.__name__ = "trim397"
    loop.turn = trim397


def _with_trim(build, state_dir, args):
    import claude_e2e382 as E382
    orig = E382.install_answer382

    def patched(loop, gen, store, *a, **kw):
        orig(loop, gen, store, *a, **kw)
        install_trim397(loop, greedy397(gen.g))

    E382.install_answer382 = patched
    try:
        loop = build(state_dir, args)
    finally:
        E382.install_answer382 = orig
    if not hasattr(loop, "trim397_stats"):
        raise RuntimeError("397: trim397 was not installed (no memory path in this build)")
    loop.layers330c = [x for y in loop.layers330c for x in ([y, "trim397"] if y == "answer382" else [y])]
    return loop


def build_397e(state_dir, args):
    import claude_e2e383 as E383
    return _with_trim(E383.build_383e, state_dir, args)


def build_397b(state_dir, args):
    import claude_e2e382 as E382
    return _with_trim(E382.build_382b, state_dir, args)


def selftest() -> None:
    ok, total = 0, 0

    def check(name: str, cond: bool) -> None:
        nonlocal ok, total
        total += 1
        ok += int(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}")

    class NB:
        events: list = []

    class Loop:
        def __init__(self, reply: str, memory: bool):
            self.nb = NB()
            self.ep382_stats = {"replaced": 0}
            self.reply, self.memory = reply, memory
            self.turn = self._turn

        def _turn(self, text: str) -> list[str]:
            if self.memory:
                self.ep382_stats["replaced"] += 1
            return [self.reply]

    q = "Where did Mara go in June?"
    lp = Loop("Mara went to the lake near Oslo in June.", True)
    install_trim397(lp, lambda s, u: "the lake near Oslo")
    check("memory answer trimmed", lp.turn(q) == ["the lake near Oslo"] and lp.trim397_stats["changed"] == 1)
    lp = Loop("Mara went to the lake near Oslo in June.", False)
    install_trim397(lp, lambda s, u: "the lake near Oslo")
    check("other replies untouched", lp.turn(q) == ["Mara went to the lake near Oslo in June."]
          and lp.trim397_stats["memory_answers"] == 0)
    lp = Loop("Mara went to the lake in June.", True)
    install_trim397(lp, lambda s, u: "Lake Tahoe")
    check("new words refused", lp.turn(q) == ["Mara went to the lake in June."] and lp.trim397_stats["not_copy"] == 1)
    lp = Loop("I don't know.", True)
    install_trim397(lp, lambda s, u: "know")
    check("abstaining reply kept", lp.turn(q) == ["I don't know."] and lp.trim397_stats["abstains"] == 1)
    lp = Loop("12 + 30 = 42. The answer is 42.", False)
    install_trim397(lp, lambda s, u: "12")
    check("math on another path untouched", lp.turn("What is 12 + 30?") == ["12 + 30 = 42. The answer is 42."])

    import claude_e2e382 as E382
    orig = E382.install_answer382

    class Args:
        pass

    def boom(state_dir, args):
        raise ValueError("x")
    try:
        _with_trim(boom, ".", Args())
    except ValueError:
        pass
    check("sealed install_answer382 restored after an error", E382.install_answer382 is orig)
    print(f"E2E397-SELFTEST {'PASS' if ok == total else 'FAIL'} {ok}/{total}")
    if ok != total:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
