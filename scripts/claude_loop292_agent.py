#!/usr/bin/env python3
"""Merge 292 -- 291 + 266b (chain lift) + 268b (n-hop guard) + 293 (yes/no).

New file only; every piece module is imported read-only and its OWN
functions/classes are reused. No existing file is edited.

292 = 291 (scripts/claude_loop291_agent.py: 138nb + 252c corrections +
          260 openers + 291 glue; read-only installs reused below)
      + 266b lift outermost on the ears (scripts/claude_fix266b_detector.py
          ChainLift266bMixin, subclass of 266's lift; questions only,
          never writes; untaught multi-word bases pass through)
      + 268b guard on the n-hop frame (scripts/claude_fix268_nhopdir.py,
          unchanged; process-local rebind of compose_n_hop; backwards
          shapes about `start` fall through to 190/table; no writes)
      + 293 reader in the 154d slot (scripts/claude_fix293_yesno.py
          YesNo293Mixin, outermost loop reader; miss-clarify yes/no
          about plain names only; chain subjects pass through; no writes)

ORDER (outermost first) and why -- see
design/v3/30-modes/292-merge-muse.md:
  turn291 (291 glue R1, outermost instance wrapper)
  turn260 (260 openers; original runs first through the whole head)
  turn224c(turn224(class turn)) (exact-glued-decline rewrite only)
  Correct252LoopMixin (records _prev252; negate252 via 154f)
  YesNo293Mixin (293 yes/no reader; miss clarify only; 154d first)
  Label138nbMixin (138nb's own outermost class: 190-reverse label)
  233 rewrite + 226 + 234 + NameLine230c + Identity227c (as on 291)
  212 / 216 / 209 (as on 291; 209's _act below 252's)
  Loop138jAgentLoop chain; ears ChainLift266bMixin outermost;
  inner ears Comment258 > Merge252c > Boundary259 > Correct252 >
  Loop138nEars(221c > FirstName138n > 221b > 237 > 229 > Loop138lEars...).

Install order inside _build292 (the instance wrappers capture
loop.turn bound at install time, so every class swap comes first):
  292 classes (plain, no wrappers) -> 252 loop/ears swaps + 259 + glue
  + 258 -> 224 -> 224c -> 260 last -> 291 guards + turn291.
  The 252b value screen, 232c rule, 228 guard and 268 guard are
  process-global rebinds installed at import and at build (as on the
  piece arms).
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

import claude_fix268_nhopdir as G268  # noqa: E402 (268 guard, read-only)

G268.install_nhopdir268()  # 268 guard, at import (as on 268b)

import claude_fix138nb_label as LB138NB  # noqa: E402 (read-only)
import claude_fix252b_screen as F252B  # noqa: E402 (read-only; installs 252b)
import claude_fix252_correct as F252  # noqa: E402 (read-only)
import claude_fix252c_merge as F252C  # noqa: E402 (258 + glue + 259)
import claude_fix260_openers as F260  # noqa: E402 (openers, read-only)
import claude_fix266b_detector as F266B  # noqa: E402 (266b lift, read-only)
import claude_fix291_glue as G291  # noqa: E402 (291 glue, read-only)
import claude_fix293_yesno as F293  # noqa: E402 (293 reader, read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only, _Swap/_ORIG)
import claude_loop138n_agent as N138  # noqa: E402 (read-only, ears base)
import claude_loop138nb_agent as NB138  # noqa: E402 (base classes, read-only)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only, 232c rule)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
import fable_loop224_agent as L224  # noqa: E402 (read-only)
import claude_loop224c_agent as L224C  # noqa: E402 (read-only)

F252B.install_screen252b()


class Loop292Ears(G228.SrcGuardMixin228, F266B.ChainLift266bMixin,
                  NB138.Loop138nbEars):
    """291 ears with the 266b multi-word chain-subject lift outermost."""

    name = "loop292-merge-chainlift"


class Loop292AgentLoop(F293.YesNo293Mixin, NB138.Loop138nbAgentLoop):
    """291 loop with the 293 yes/no reader in the 154d slot (outermost)."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_E = _mro_names(Loop292Ears)
assert _E[:4] == ["Loop292Ears", "SrcGuardMixin228", "ChainLift266bMixin",
                  "ChainLift266Mixin"], _E
assert "Loop138nEars" in _E, _E  # NB138.Loop138nbEars is this alias
_L = _mro_names(Loop292AgentLoop)
assert _L[:3] == ["Loop292AgentLoop", "YesNo293Mixin",
                  "Loop138nbAgentLoop"], _L


def _build292_plain(cfg):
    """292 classes without the 224/224c instance wrappers (those wrap
    last, after the 252c class swaps, so the 252 loop mixin stays inside
    the captured turn chain)."""
    with M138._Swap([(L138J, "Loop138jEars", Loop292Ears),
                     (L138J, "Loop138jAgentLoop", Loop292AgentLoop),
                     (L138J, "build_agent138j", M138._ORIG_BUILD)]):
        return L138K.build_agent138k(cfg)


def _build292(cfg=None):
    """292 classes, then 252c, then 224/224c, then 260, then 291 glue."""
    loop = _build292_plain(cfg)
    F252.install_correct252(loop)  # 252 loop mixin + ears mixin first
    F252C.install_merge252c(loop)  # then 259 + glue + 258
    L224.install_decline224(loop)
    L224C.install_q1honest224c(loop)
    F260.install_openers260(loop)  # outermost turn chain...
    G291.install_guards291(loop)  # ...junk-subject guards outside 260,
    G291.install_turn291(loop)  # ...then the 291 turn wrapper outermost
    return loop


def _with_292(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", Loop292Ears),
                     (L138J, "Loop138jAgentLoop", Loop292AgentLoop),
                     (L138J, "build_agent138j", _build292)]):
        return fn(*args, **kwargs)


NOTE292 = ("loop292: loop291 + 266b multi-word chain-subject lift "
           "(scripts/claude_fix266b_detector.py, outermost ears) + 268 "
           "n-hop direction guard (scripts/claude_fix268_nhopdir.py) + "
           "293 yes/no reader (scripts/claude_fix293_yesno.py, 154d slot)")


DEFAULT_CONFIG292: dict = copy.deepcopy(NB138.DEFAULT_CONFIG138NB)
DEFAULT_CONFIG292["daemon"]["module"] = (
    "Loop292Daemon (scripts/claude_loop292_agent.py) over Loop138kDaemon "
    "with the 291 classes + 266b lift + 268 guard + 293 reader")
DEFAULT_CONFIG292["self"] = dict(DEFAULT_CONFIG292.get("self", {}))
DEFAULT_CONFIG292["self"]["rule260"] = (
    "260 (scripts/claude_fix260_openers.py): listed openers/greetings at the "
    "start of a turn (at most 2) are dropped when the head gives the rest a "
    "non-clarify reply; bare greetings get the head's reply to 'Hello.'; no "
    "stored subject may start with a listed opener + comma")
DEFAULT_CONFIG292["fix252"] = (
    "Correct252EarsMixin outermost on the inner ears + Correct252LoopMixin "
    "on the loop (scripts/claude_fix252_correct.py)")
DEFAULT_CONFIG292["fix252b"] = (
    "value_ok252 stopword check on non-letter-split pieces "
    "(scripts/claude_fix252b_screen.py)")
DEFAULT_CONFIG292["fix258"] = (
    "Comment258EarsMixin outermost on the inner ears: trailing commentary "
    "clause removed on 252b denial/correction turns "
    "(scripts/claude_fix258_comment.py)")
DEFAULT_CONFIG292["fix259"] = (
    "Boundary259EarsMixin on top of the 252 ears mixin: denied value ends "
    "at a clause boundary (scripts/claude_fix259_boundary.py)")
DEFAULT_CONFIG292["fix252c"] = (
    "inner ears: Comment258 > Merge252c > Boundary259 > Correct252; glue: "
    "258's cut point counts as 259's boundary on the 154f route "
    "(scripts/claude_fix252c_merge.py)")
DEFAULT_CONFIG292["self"]["rule266b"] = (
    "266b multi-word chain-subject lift "
    "(scripts/claude_fix266b_detector.py): a ?-turn with a possessive-chain "
    "subject over a one- to three-word notebook name is placeholder-probed "
    "(dry, write-free; exactly one one-hop ask frame for the placeholder) "
    "and served from 'What/Who is <chain>'s R?'; untaught multi-word bases "
    "never lift; all other turns pass through byte-identical; never writes")
DEFAULT_CONFIG292["self"]["rule268b"] = (
    "268 n-hop direction guard (scripts/claude_fix268_nhopdir.py): "
    "compose_n_hop frames whose question is backwards-shaped about the "
    "start return None so 190/table layers answer; forward unchanged")
DEFAULT_CONFIG292["self"]["rule293"] = (
    "293 yes/no reader (scripts/claude_fix293_yesno.py YesNo293Mixin, "
    "outermost read-only rule over the loop): Does-have / Has-got / "
    "Does-live-in / Does-work-at-for / Does-come-from / Was-born-in / Is "
    "with multi-word names / Is-of-forms; Yes on match, No only on "
    "single-valued keys, else honest IDK; chain subjects pass through; "
    "never writes")
DEFAULT_CONFIG292["exp260"] = {
    "base": "loop291 (scripts/claude_loop292_agent.py builds 291 first)",
    "added": ["266b multi-word chain-subject lift outermost ears stage",
              "268 question-side direction guard around compose_n_hop",
              "293 yes/no reader in the 154d slot",
              "291 glue (scripts/claude_fix291_glue.py: 229 skips "
              "opener-led statements; opener-led teach subjects clarify)"],
    "instance": ["turn291(turn260(turn224c(turn224(class turn))))"],
}
DEFAULT_CONFIG292["merge292"] = {
    "base": "loop291 (scripts/claude_loop291_agent.py)",
    "added": ["266b chain-subject lift (outermost ears)",
              "268 n-hop direction guard (composer rebind)",
              "293 yes/no reader (outermost loop reader, 154d slot)"],
    "loop_mro": ["Correct252_Loop292AgentLoop", "Correct252LoopMixin",
                 "Loop292AgentLoop", "YesNo293Mixin", "Loop138nbAgentLoop",
                 "Label138nbMixin", "Loop138nAgentLoop", "... (291)"],
    "instance": ["turn291(turn260(turn224c(turn224(class turn))))"],
    "inner_ears": ["Comment258", "Merge252c", "Boundary259", "Correct252",
                   "Loop292Ears/Loop138nbEars + 266b lift",
                   "Loop138nEars(221c > FirstName138n > 221b > 237 > 229 > "
                   "Loop138lEars(209 > 223 > layer C > 222/215 ...) ...)"],
}


def _check(loop):
    if not isinstance(loop, Loop292AgentLoop):
        raise RuntimeError("292: loop is not Loop292AgentLoop")
    if not isinstance(loop, NB138.Loop138nbAgentLoop):
        raise RuntimeError("292: loop is not Loop138nbAgentLoop")
    if "YesNo293Mixin" not in _mro_names(type(loop)):
        raise RuntimeError("292: YesNo293Mixin not on loop")
    if "Correct252LoopMixin" not in _mro_names(type(loop)):
        raise RuntimeError("292: Correct252LoopMixin not on loop")
    if "Label138nbMixin" not in _mro_names(type(loop)):
        raise RuntimeError("292: Label138nbMixin not on loop")
    outer = getattr(loop, "ears", None)
    if "ChainLift266bMixin" not in _mro_names(type(outer)):
        raise RuntimeError("292: ChainLift266bMixin not on outer ears")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, NB138.Loop138nbEars):
        raise RuntimeError("292: inner ears are not Loop138nbEars")
    if not isinstance(inner, Loop292Ears):
        raise RuntimeError("292: inner ears are not Loop292Ears")
    for mix in ("Comment258EarsMixin", "Merge252cEarsMixin",
                "Boundary259EarsMixin", "Correct252EarsMixin"):
        if mix not in _mro_names(type(inner)):
            raise RuntimeError(f"292: {mix} not on inner ears")
    if not G228.is_installed():
        raise RuntimeError("292: 228 guard not installed")
    if not G268.is_installed():
        raise RuntimeError("292: 268 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn291":
        raise RuntimeError("292: turn291 not installed")
    if getattr(loop.turn291_inner, "__name__", "") != "turn260":
        raise RuntimeError("292: turn260 not under turn291")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("292: 224c not under turn260")
    import claude_fix252_correct as F252
    if F252.value_ok252.__name__ != "value_ok252b":
        raise RuntimeError("292: 252b screen not installed")
    loop.notes.append(NB138.NOTE138NB)
    loop.notes.append(NOTE292)


def build_agent292(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG292, **(cfg or {}))
    loop = _with_292(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes292Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 292 classes and the
    292-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        F252B.install_screen252b()
        _with_292(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop292Daemon(SrcGuardMixin228, Classes292Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases (228 guard > 220 restart index >
    Loop138jDaemon) with SrcGuardMixin228 first and the 292 build mixin
    (291 classes + 266b lift + 268 guard + 293 reader) ahead of the 220
    mixin, as 291's Classes291Mixin sits ahead of Loop138kDaemon."""


assert [c.__name__ for c in Loop292Daemon.__mro__][:5] == [
    "Loop292Daemon", "SrcGuardMixin228", "Classes292Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)

    ap = argparse.ArgumentParser(
        description="Merge 292 (291 + 266b + 268b + 293)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG292)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG292)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop292Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent292(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
