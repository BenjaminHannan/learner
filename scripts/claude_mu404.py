#!/usr/bin/env python3
"""mu-403 / mu-404 builders on the real 0.2c stack WITH the lis-319 reader ("Making things up about you", 2026-09-26).
New file only; imports everything else read-only. Marks: artifacts/claude-mu403-20260926/PASSMARKS.md.

Why: mu-402 (VERIFY there) ran the chat path with no reader at all (NullReader) and found the sleep adapter adds only
a few made-up claims (not shown). In that rig the joined build made up LESS than the plain 1B. The one thing 0.2c had
and the rig did not: the notebook's facts about the user in every 1B chat and creative prompt
(claude_cre333_agent.context_facts keeps every "user"/"me" fact, up to 40, in "Facts the user has told you: ...").

Arms (all: build_02c as frozen, lis-319 reader via --model, sleep adapter NOT loaded (0.2d's chat path), torch and
random seeded per turn exactly as mu-402):
  build_r   R, control: build_02c unchanged.
  build_f   F = R with ONE change: context_facts returns nothing, so no 1B writer prompt (chat 338, creative 333d)
            gets notebook facts. The notebook, the reader, saves and template answers are untouched.   (mu-404)
  build_p   P = R with ONE change: the mu-403 fix chosen by claude_mu403_auc.py's pre-set bar
            (MU403_FIX below; "ground" = the 1B's self-check picks the least-assuming chat sample via
            claude_pick403 on chat 338b only; "sysline" = one extra sentence in chat 338's system prompt).   (mu-403)

Every arm wraps context_facts in the same counter (words-free): calls, calls with at least one fact, facts total.
It is printed at exit as "mu404: facts ..." (V-check: the panel must actually put facts in front of the 1B).

  python3 -B scripts/claude_mu404.py --selftest        (CPU, no model)
"""
from __future__ import annotations

import atexit
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MU403_FIX = "sysline"        # sealed 09-26: claude_mu403_auc.py AUC 0.537 < 0.65 (artifacts/claude-mu403-20260926/AUC.md)
FACTS404 = {"calls": 0, "with_facts": 0, "facts": 0, "blanked": 0}
_STATE = {"wrapped": False, "blank": False, "printed": False}


def _report():
    print(f"mu404: facts {FACTS404}", flush=True)


def wrap_context_facts(blank: bool) -> None:
    import claude_cre333_agent as C
    if _STATE["wrapped"]:
        if _STATE["blank"] != blank:
            raise RuntimeError("mu404: arms mixed in one process")
        return
    orig = C.context_facts

    def context_facts404(loop, text):
        got = orig(loop, text)
        FACTS404["calls"] += 1
        FACTS404["with_facts"] += 1 if got else 0
        FACTS404["facts"] += len(got)
        if blank:
            FACTS404["blanked"] += 1 if got else 0
            return []
        return got

    C.context_facts = context_facts404
    _STATE.update(wrapped=True, blank=blank)
    atexit.register(_report)


def _build(state_dir, args, tag):
    import claude_e2e02c as E
    import claude_mu402 as M402
    if E.READER02C != "r319":
        raise SystemExit("mu404: build_02c no longer uses the lis-319 reader path")
    if args.model == M402.NULL_MODEL:
        raise SystemExit("mu404: needs the real lis-319 reader (--model <dir>), not the NullReader")
    loop = E.build_02c(state_dir, args)
    M402.install_seed402(loop)
    loop.layers330c = list(loop.layers330c) + ["seed402", tag]
    if not _STATE["printed"]:
        _STATE["printed"] = True
        print(f"mu404: arm {tag}; adapter loaded = {getattr(loop, 'sleep02c', None) or 'none'}; "
              f"layers = {loop.layers330c}", flush=True)
    return loop


def build_r(state_dir, args):
    wrap_context_facts(blank=False)
    return _build(state_dir, args, "R404")


def build_f(state_dir, args):
    wrap_context_facts(blank=True)
    return _build(state_dir, args, "F404-nofacts")


def build_p(state_dir, args):
    import claude_mu403 as M3
    wrap_context_facts(blank=False)
    if MU403_FIX == "ground":
        import claude_chat338b_agent as C38B
        import claude_pick403 as P
        if not getattr(C38B.install_chat338b, "_pick403", None):
            P.on_layer(C38B, "install_chat338b", M3.make_ground, "ground")
            atexit.register(M3._report)
    elif MU403_FIX == "sysline":
        import claude_chat338_agent as C38
        if not C38.SYSTEM338.endswith(M3.VARIANT_LINE):
            C38.SYSTEM338 = C38.SYSTEM338 + M3.VARIANT_LINE
    else:
        raise SystemExit(f"mu404: MU403_FIX not set ({MU403_FIX!r}); seal it first")
    return _build(state_dir, args, f"P403-{MU403_FIX}")


def selftest() -> None:
    import types
    import claude_cre333_agent as C
    ok = 0
    orig = C.context_facts
    C.context_facts = lambda loop, text: [("user", "dog", "Pip")]
    try:
        wrap_context_facts(blank=True)
        assert C.context_facts(None, "hi") == []; ok += 1
        assert FACTS404 == {"calls": 1, "with_facts": 1, "facts": 1, "blanked": 1}; ok += 1
        wrap_context_facts(blank=True); ok += 1                                  # idempotent
        try:
            wrap_context_facts(blank=False)
            raise AssertionError("mixed arms accepted")
        except RuntimeError:
            ok += 1
    finally:
        C.context_facts = orig
    try:
        _build("/nonexistent", types.SimpleNamespace(model="NULL"), "x")
        raise AssertionError("NullReader accepted")
    except SystemExit:
        ok += 1
    print(f"mu404 selftest {ok}/5 ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        raise SystemExit(__doc__)
