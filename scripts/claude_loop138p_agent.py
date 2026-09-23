#!/usr/bin/env python3
"""Merge 138p -- 138m + 260 (openers) + 252c (corrections: 252b + 258 + 259).
New file only; every piece module is imported read-only and its OWN
functions/classes are reused. No existing file is edited.

138p = 138m (scripts/claude_loop138m_agent.py: 138l + 219/230/230b/230c +
         227/227b/227c + 224/224c + 233 + 234; classes Loop138mEars /
         Loop138mAgentLoop, reused as is)
     + 252c inner-ears stack (scripts/claude_fix252c_merge.py,
         claude_fix258_comment.py, claude_fix259_boundary.py,
         claude_fix252_correct.py + claude_fix252b_screen.py):
           Comment258 > Merge252c > Boundary259 > Correct252, outermost
           on the loop's inner ears (base swapped from 138k's plain 138j
           ears to 138m's 138l ears), plus Correct252LoopMixin on the loop
           (_prev252 memory + negate252 action through 154f's path)
     + 260 turn260 instance wrapper (scripts/claude_fix260_openers.py),
         outermost, outside 224/224c, with the opener-comma write guards.

ORDER (outermost first) and why -- see
design/v3/30-modes/138p-merge-muse.md:
  turn260 (260: stripped rest runs through the whole head as if typed
           alone; the original runs first, so 252c's own correction
           reading always wins when it acts; 260 never overrides a write)
  turn224c(turn224(class turn)) (224/224c: exact glued decline only)
  233 rewrite + 226 + 234 + NameLine230c + Identity227c (as on 138m)
  Correct252LoopMixin (wraps the 138m class turn; _prev252 sees the
           replies the user actually got)
  212 / 216 / 209 (as on 138m; 209's _act sits below 252's, so a 252
           removal never passes through it)
  Loop138jAgentLoop chain; inner ears Comment258 > Merge252c >
  Boundary259 > Correct252 > Loop138lEars(209 > 223 > layer C > 222/215).

Install order inside _build138p (the instance wrappers capture
loop.turn bound at install time, so every class swap comes first):
  138m classes -> 252 loop/ears swaps + 259 + glue + 258 -> 224 -> 224c
  -> 260 last. The 252b value screen is installed at import (as on 252c).
SrcGuardMixin228 stays first in the daemon; install_srcguard228() at import.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()  # 228 first, at import

import claude_fix252b_screen as F252B  # noqa: E402 (read-only; installs 252b)
import claude_fix252_correct as F252  # noqa: E402 (read-only)
import claude_fix252c_merge as F252C  # noqa: E402 (258 + glue + 259)
import claude_fix260_openers as F260  # noqa: E402 (openers, read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
import fable_loop224_agent as L224  # noqa: E402 (read-only)
import claude_loop224c_agent as L224C  # noqa: E402 (read-only)

F252B.install_screen252b()


def _build138p_plain(cfg):
    """138m classes without the 224/224c instance wrappers (those wrap
    last, after the 252c class swaps, so the 252 loop mixin stays inside
    the captured turn chain)."""
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", L138M._ORIG_BUILD)]):
        return L138K.build_agent138k(cfg)


def _build138p(cfg=None):
    """138m classes, then 252c, then 224/224c, then 260 (outermost)."""
    loop = _build138p_plain(cfg)
    F252.install_correct252(loop)  # 252 loop mixin + ears mixin first
    F252C.install_merge252c(loop)  # then 259 + glue + 258
    L224.install_decline224(loop)
    L224C.install_q1honest224c(loop)
    F260.install_openers260(loop)  # outermost
    return loop


def _with_138p(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build138p)]):
        return fn(*args, **kwargs)


NOTE138P = ("loop138p: loop138m + 252c corrections (252b + 258 + glue + 259, "
            "inner ears) + 260 turn openers/greetings (outermost)")


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


DEFAULT_CONFIG138P: dict = copy.deepcopy(L138M.DEFAULT_CONFIG138M)
DEFAULT_CONFIG138P["daemon"]["module"] = (
    "Loop138pDaemon (scripts/claude_loop138p_agent.py) over Loop138kDaemon "
    "with the 138m classes + 252c + 260")
DEFAULT_CONFIG138P["self"] = dict(DEFAULT_CONFIG138P.get("self", {}))
DEFAULT_CONFIG138P["self"]["rule260"] = (
    "260 (scripts/claude_fix260_openers.py): listed openers/greetings at the "
    "start of a turn (at most 2) are dropped when the head gives the rest a "
    "non-clarify reply; bare greetings get the head's reply to 'Hello.'; no "
    "stored subject may start with a listed opener + comma")
DEFAULT_CONFIG138P["fix252"] = (
    "Correct252EarsMixin outermost on the inner ears + Correct252LoopMixin "
    "on the loop (scripts/claude_fix252_correct.py)")
DEFAULT_CONFIG138P["fix252b"] = (
    "value_ok252 stopword check on non-letter-split pieces "
    "(scripts/claude_fix252b_screen.py)")
DEFAULT_CONFIG138P["fix258"] = (
    "Comment258EarsMixin outermost on the inner ears: trailing commentary "
    "clause removed on 252b denial/correction turns "
    "(scripts/claude_fix258_comment.py)")
DEFAULT_CONFIG138P["fix259"] = (
    "Boundary259EarsMixin on top of the 252 ears mixin: denied value ends "
    "at a clause boundary (scripts/claude_fix259_boundary.py)")
DEFAULT_CONFIG138P["fix252c"] = (
    "inner ears: Comment258 > Merge252c > Boundary259 > Correct252; glue: "
    "258's cut point counts as 259's boundary on the 154f route "
    "(scripts/claude_fix252c_merge.py)")
DEFAULT_CONFIG138P["exp260"] = {
    "base": "loop138m (scripts/claude_loop138m_agent.py)",
    "added": ["260 turn openers + greetings layer (outermost, instance)"],
    "instance": ["turn260(turn224c(turn224(class turn)))"],
}
DEFAULT_CONFIG138P["merge138p"] = {
    "base": "loop138m (scripts/claude_loop138m_agent.py)",
    "added": ["252c corrections (252b + 258 + glue + 259, inner ears)",
              "260 turn openers + greetings (outermost, instance)"],
    "loop_mro": ["Loop138pAgentLoop=Correct252_Loop138mAgentLoop",
                 "Correct252LoopMixin", "Loop138mAgentLoop", "... (138m)"],
    "instance": ["turn260(turn224c(turn224(class turn)))"],
    "inner_ears": ["Comment258", "Merge252c", "Boundary259", "Correct252",
                   "Loop138lEars(209 > 223 > layer C > 222/215 ...)"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("138p: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("138p: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("138p: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn260":
        raise RuntimeError("138p: turn260 not installed")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("138p: 224c not under turn260")
    inner = getattr(loop, "_inner138j_ears", None)
    for mix in ("Comment258EarsMixin", "Merge252cEarsMixin",
                "Boundary259EarsMixin", "Correct252EarsMixin"):
        if mix not in _mro_names(type(inner)):
            raise RuntimeError(f"138p: {mix} not on inner ears")
    if "Correct252LoopMixin" not in _mro_names(type(loop)):
        raise RuntimeError("138p: Correct252LoopMixin not on loop")
    import claude_fix252_correct as F252
    if F252.value_ok252.__name__ != "value_ok252b":
        raise RuntimeError("138p: 252b screen not installed")
    loop.notes.append(L138M.NOTE138M)
    loop.notes.append(NOTE138P)


def build_agent138p(cfg: dict | None = None):
    G228.install_srcguard228()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG138P, **(cfg or {}))
    loop = _with_138p(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes138pMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    138p-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        F252B.install_screen252b()
        _with_138p(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop138pDaemon(SrcGuardMixin228, Classes138pMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases (228 guard > 220 restart index >
    Loop138jDaemon) with SrcGuardMixin228 first and the 138p build mixin
    (138m classes + 252c + 224/224c + 260) ahead of the 220 mixin, as 138m's
    Classes138mMixin sits ahead of Loop138kDaemon."""


assert [c.__name__ for c in Loop138pDaemon.__mro__][:5] == [
    "Loop138pDaemon", "SrcGuardMixin228", "Classes138pMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)

    ap = argparse.ArgumentParser(description="Merge 138p (138m + 260 + 252c)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138P)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG138P)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop138pDaemon(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent138p(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
