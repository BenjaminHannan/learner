#!/usr/bin/env python3
"""Joining ch-404 with another change to chat 338's system line (everyday-chat thread, 2026-09-26). New file only.

Why: claude_ch404_agent computes SYSTEM404 once, when it is imported, from SYSTEM338 as it was then, and puts it in
place of SYSTEM338 while ch-403's chat turn runs. A change that appends to SYSTEM338 later (Making things up's mu-403
arm P appends claude_mu403.VARIANT_LINE at build time, claude_mu403.build_sysline02c / claude_mu404.build_p) would be
dropped on the chat path while ch-404's turn runs. Raised by Making things up 15:13 UTC.

What: install_chat404_live is install_chat404 with one difference: at every chat turn SYSTEM404 is recomputed from the
SYSTEM338 in force outside that turn (the same one-phrase swap), so any appended line stays. With SYSTEM338 unchanged
it sends exactly what build_404 sends (selftest case 1), so ch-404's DEV probe and registered run carry over. A joined
build (0.2d, owner Month-end) that takes both ch-404 and mu-403's system line uses build_404_live instead of build_404.
ch-404g needs nothing: its greedy reply is rendered from the same messages as 338's samples.

  python3 -B scripts/claude_ch404_join.py --selftest      (CPU, no model)
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_ch404_agent as F  # noqa: E402
import claude_chat338_agent as C38  # noqa: E402


def live_system404(outside: str) -> str:
    if F.OLD_PHRASE not in outside:
        raise RuntimeError("404 join: SYSTEM338 in force has no 1-to-4-sentences phrase")
    return outside.replace(F.OLD_PHRASE, F.NEW_PHRASE)


def install_chat404_live(loop, gen, n: int = C38.N338) -> None:
    F.install_chat404(loop, gen, n)
    inner = loop.turn                       # ch-404's turn338 (its closure holds state and save)

    def turn338(text: str) -> list[str]:
        _ = (state, save)                   # keep the history cells visible to claude_fix02c.chat338_state (F1)
        F.SYSTEM404 = live_system404(C38.SYSTEM338)
        return inner(text)

    cells = dict(zip(inner.__code__.co_freevars, inner.__closure__ or ()))
    state, save = cells["state"].cell_contents, cells["save"].cell_contents
    loop.turn = turn338


def build_404_live(state_dir, args):
    """build_404 with install_chat404_live in the chat layer's place."""
    import claude_chat338b_agent as C38B
    import claude_e2e02c as E
    orig = C38B.install_chat338b
    C38B.install_chat338b = install_chat404_live
    try:
        loop = E.build_02c(state_dir, args)
    finally:
        C38B.install_chat338b = orig
    loop.layers330c = [("chat404live" if x == "chat338b" else x) for x in loop.layers330c]
    return loop


def selftest() -> None:
    import tempfile
    import claude_ch404_test as FT
    import claude_fix02c as FX
    ok = 0
    base, static = C38.SYSTEM338, F.SYSTEM404
    extra = " Only say what the user told you."          # stands in for an appended line such as VARIANT_LINE
    try:
        loop_s, seen_s = FT._install(F.install_chat404, FT.CLARIFY)
        loop_l, seen_l = FT._install(install_chat404_live, FT.CLARIFY)
        q = "how do i stop putting off chores?"
        assert loop_s.turn(q) == loop_l.turn(q) and seen_s == seen_l and seen_l[-1].startswith(static); ok += 1
        C38.SYSTEM338 = base + extra                     # appended after ch-404 was imported, as mu-403 does
        loop_l2, seen_l2 = FT._install(install_chat404_live, FT.CLARIFY)
        loop_l2.turn(q)
        assert seen_l2[-1].startswith(static + extra) and F.NEW_PHRASE in seen_l2[-1]; ok += 1
        loop_s2, seen_s2 = FT._install(F.install_chat404, FT.CLARIFY)
        F.SYSTEM404 = static
        loop_s2.turn(q)
        assert extra not in seen_s2[-1]; ok += 1         # the problem this file fixes, shown on build_404
        assert C38.SYSTEM338 == base + extra and C38.MAX_WORDS338 == 90; ok += 1
        state, _save = FX.chat338_state(loop_l2.turn)
        assert state.get("history") and state["history"][-2]["content"] == q; ok += 1
    finally:
        C38.SYSTEM338, F.SYSTEM404 = base, static
    print(f"ch-404 join selftest: {ok}/5 OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
