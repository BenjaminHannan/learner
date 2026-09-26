#!/usr/bin/env python3
"""mu-403 builders (DRAFT, not sealed; "Making things up about you" thread, 2026-09-26). New file only.

The pilot (scripts/claude_mu403_pilot.py, on mu-402's arm-B chats) picks ONE of these as mu-403's single change;
the other is the FAIL fallback. Both keep mu-402's rig (claude_mu402.build_null02c: NullReader, per-turn seeds) and
touch the chat layer (338b) only. Whether 0.2c's sleep adapter is loaded is decided by SLEEP02C_ADAPTER, as in
mu-402, and both arms of a run get the same setting (the one mu-402's verdict leaves on the chat path).

  build_ground02c   grounded pick: chat 338b's writer is wrapped in claude_pick403.PickGen with the 1B's own
                    "does this reply assume something about the user?" margin (claude_mu403_ground.GroundScorer,
                    on trimmed samples). Same samples, least-assuming first; 338's guards still take the first that
                    passes. Creative 333d, think 299b and everything else keep the unwrapped writer.
  build_sysline02c  system line: chat 338's system prompt gets one extra sentence (VARIANT_LINE below, the same
                    one the pilot tries). Nothing else changes.

Control arm for either: claude_mu402:build_null02c.

  python3 -B scripts/claude_mu403.py --selftest      (CPU, no model)
"""
from __future__ import annotations

import atexit
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

VARIANT_LINE = (" Only say things about the user that they actually told you in this chat. Do not guess their "
                "feelings, plans, situation or past; if something matters and you don't know it, ask.")
TOTALS403 = {"calls": 0, "scored": 0, "reordered": 0, "top_changed": 0}
_PICKERS: list = []
_PRINTED: list = []


def _report():
    for p in _PICKERS:
        for k in TOTALS403:
            TOTALS403[k] += p.stats[k]
    if _PICKERS:
        print(f"mu403: pick totals over {len(_PICKERS)} builds = {TOTALS403}", flush=True)


def make_ground(gen):
    import claude_chat338_agent as C38
    import claude_mu403_ground as G
    sc = G.GroundScorer(gen.g)
    return lambda msgs, cands: sc.margins(msgs, [C38.trim(c) for c in cands])


def build_ground02c(state_dir, args):
    import claude_chat338b_agent as C38B
    import claude_mu402 as M402
    import claude_pick403 as P
    if not getattr(C38B.install_chat338b, "_pick403", None):
        P.on_layer(C38B, "install_chat338b", make_ground, "ground")
        atexit.register(_report)
    loop = M402.build_null02c(state_dir, args)
    _PICKERS.append(loop.pick403["ground"])
    loop.layers330c = list(loop.layers330c) + ["pick403:ground@chat338b"]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"mu403: grounded pick on chat 338b only; layers = {loop.layers330c}", flush=True)
    return loop


def build_sysline02c(state_dir, args):
    import claude_chat338_agent as C38
    import claude_mu402 as M402
    if not C38.SYSTEM338.endswith(VARIANT_LINE):
        C38.SYSTEM338 = C38.SYSTEM338 + VARIANT_LINE
    loop = M402.build_null02c(state_dir, args)
    loop.layers330c = list(loop.layers330c) + ["sysline403@chat338"]
    if not _PRINTED:
        _PRINTED.append(1)
        print(f"mu403: system line added to chat 338; layers = {loop.layers330c}", flush=True)
    return loop


def selftest() -> None:
    import types
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_pick403 as P
    ok = 0
    orig = C38B.install_chat338b
    seen = {}
    C38B.install_chat338b = lambda loop, gen, n=4: seen.setdefault("chat", gen)
    try:
        undo = P.on_layer(C38B, "install_chat338b", lambda gen: (lambda m, c: [0.0] * len(c)), "ground")
        shared = types.SimpleNamespace(g="one_b", sample_chat=lambda msgs, n: ["b", "a"])
        loop = types.SimpleNamespace()
        C38B.install_chat338b(loop, shared)
        assert isinstance(seen["chat"], P.PickGen) and seen["chat"].gen is shared; ok += 1
        assert seen["chat"].sample_chat([], 2) == ["b", "a"]; ok += 1                      # ties keep draw order
        undo()
    finally:
        C38B.install_chat338b = orig
    assert C38B.install_chat338b is orig and not getattr(orig, "_pick403", None); ok += 1
    base = C38.SYSTEM338
    try:
        C38.SYSTEM338 = base + VARIANT_LINE
        assert C38.SYSTEM338.endswith(VARIANT_LINE) and C38.SYSTEM338.count(VARIANT_LINE) == 1; ok += 1
    finally:
        C38.SYSTEM338 = base
    assert C38.trim("Hi there.") == "Hi there."; ok += 1
    print(f"mu403 selftest {ok}/5 ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
