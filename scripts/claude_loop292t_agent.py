#!/usr/bin/env python3
"""Exp 292t agent: join of the talking line's three layers on main base 292.

Everything is 292 (scripts/claude_loop292_agent.py, read-only: 291 + 266b
lift + 268b guard + 293 reader) plus the 280m piece files imported
read-only and unchanged, installed in 280m's order, inner to outer:

  292, then 281, then 280/280b, then 282/282b.

That is, on top of 292's own instance stack
turn291(turn260(turn224c(turn224(class turn)))):
  turn282b(turn282(turn280b(turn280(turn281(turn291(...)))))).

No new behaviour: the new files are this join agent (plus its config)
and the three single-layer arm agents (scripts/claude_292t_281_agent.py,
scripts/claude_292t_280b_agent.py, scripts/claude_292t_282b_agent.py),
which reuse the shared _build292_* builders below. Each layer only ever
substitutes the reply of a turn its own head already mishandled (or serves
its sealed text), and otherwise passes through byte-identical, so the
three triggers never fire on the same turn (shown on the builder's own dev
turns before the seal; 0 overlaps).

It is installed inside the build (like 292/260/281/280/282), so the
daemon's boot reconcile already runs through it. The daemon keeps
SrcGuardMixin228 first, exactly where 292 has it.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_fix268_nhopdir as G268  # noqa: E402 (268 guard, read-only)
import claude_fix252b_screen as F252B  # noqa: E402 (read-only)
import claude_fix280_capab as F280  # noqa: E402 (piece, read-only)
import claude_fix280b_general as F280B  # noqa: E402 (piece, read-only)
import claude_fix281_called as F281  # noqa: E402 (piece, read-only)
import claude_fix282_small as F282  # noqa: E402 (piece, read-only)
import claude_fix282b_vocab as F282B  # noqa: E402 (piece, read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only, _Swap)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only, 232c rule)
import claude_loop292_agent as L292  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _install_all_talking(loop):
    """Install 280m's layers on a 292 loop in 280m's order (inner first)."""
    F281.install_called281(loop)        # innermost piece (over 292)
    F280.install_capab280(loop)         # 280 over 281
    F280B.install_general280b(loop)     # 280b over 280
    F282.install_small282(loop)         # 282 over 280b
    F282B.install_small282b(loop)       # 282b outermost
    return loop


def _install_280b_layers(loop):
    """Single-layer arm: 292 + 280 ability table + 280b general layer."""
    F280.install_capab280(loop)
    F280B.install_general280b(loop)
    return loop


def _install_281_layer(loop):
    """Single-layer arm: 292 + 281 called/named layer."""
    F281.install_called281(loop)
    return loop


def _install_282b_layers(loop):
    """Single-layer arm: 292 + 282 small-talk + 282b vocabulary layers."""
    F282.install_small282(loop)
    F282B.install_small282b(loop)
    return loop


def _build292t(cfg=None):
    loop = L292._build292(cfg)          # base 292 (read-only build)
    return _install_all_talking(loop)


def _build292_280b(cfg=None):
    loop = L292._build292(cfg)
    return _install_280b_layers(loop)


def _build292_281(cfg=None):
    loop = L292._build292(cfg)
    return _install_281_layer(loop)


def _build292_282b(cfg=None):
    loop = L292._build292(cfg)
    return _install_282b_layers(loop)


def _with_292t(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", L292.Loop292Ears),
                      (L138J, "Loop138jAgentLoop", L292.Loop292AgentLoop),
                      (L138J, "build_agent138j", _build292t)]):
        return fn(*args, **kwargs)


NOTE292T = ("loop292t: join of 281 + 280/280b + 282/282b on base 292 "
            "(outermost turn stack "
            "turn282b(turn282(turn280b(turn280(turn281(turn291(turn260("
            "turn224c(turn224(class turn))))))))))")


def _base_config292t() -> dict:
    cfg = copy.deepcopy(L292.DEFAULT_CONFIG292)
    cfg["daemon"]["module"] = (
        "Loop292tDaemon (scripts/claude_loop292t_agent.py) over "
        "Loop138kDaemon with the 292 classes + talking layers")
    cfg["self"] = dict(cfg.get("self", {}))
    cfg["self"]["rule281"] = (
        "281 (scripts/claude_fix281_called.py): trailing called/named, "
        "'what do you call X?' and 'name of X?' question turns are read as "
        "the plain possessive question; teaches and writes untouched; "
        "never writes")
    cfg["self"]["rule280"] = (
        "280 (scripts/claude_fix280_capab.py): general ability questions and "
        "any C24-shaped head reply are answered with the sealed CAN280 text "
        "(6 table-backed abilities, 3 dropped); everything else byte-identical "
        "to the layer below; never writes")
    cfg["self"]["rule280b"] = (
        "280b (scripts/claude_fix280b_general.py): question-shaped turns "
        "addressing the assistant with an ability cue and no named "
        "entity/relation get the sealed CAN280 text (0 writes); "
        "'Can you <specific>?' keeps the lower reply; everything else "
        "byte-identical; never writes")
    cfg["self"]["rule282"] = (
        "282 (scripts/claude_fix282_small.py): whole-turn pure-small-talk "
        "greetings and closings that the head mishandles get the head's own "
        "canonical reply for their class; mixed turns keep the lower route; "
        "never writes")
    cfg["self"]["rule282b"] = (
        "282b (scripts/claude_fix282b_vocab.py): a whole turn is small talk "
        "when every word belongs to the sealed vocabulary, it holds a "
        "greeting/thanks/closing word, and it names no stored entity and no "
        "relation word; class = the first such word; mishandled turns get "
        "the head's own canonical reply for their class; mixed turns keep "
        "the lower route; never writes")
    cfg["exp292t"] = {
        "base": "loop292 (scripts/claude_loop292_agent.py)",
        "added": ["281 called/named layer", "280 ability table + 280b "
                  "general-question layer", "282 small-talk + 282b "
                  "vocabulary layer (all outermost, instance, in order)"],
        "instance": ["turn282b(turn282(turn280b(turn280(turn281(turn291("
                     "turn260(turn224c(turn224(class turn))))))))"],
    }
    return cfg


DEFAULT_CONFIG292T: dict = _base_config292t()


def _check_talk_stack(loop, tag: str) -> None:
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn282b":
        raise RuntimeError(f"{tag}: turn282b not outermost")
    if getattr(loop.turn282b_inner, "__name__", "") != "turn282":
        raise RuntimeError(f"{tag}: 282 not under turn282b")
    if getattr(loop.turn282_inner, "__name__", "") != "turn280b":
        raise RuntimeError(f"{tag}: 280b not under turn282")
    if getattr(loop.turn280b_inner, "__name__", "") != "turn280":
        raise RuntimeError(f"{tag}: 280 not under turn280b")
    if getattr(loop.turn280_inner, "__name__", "") != "turn281":
        raise RuntimeError(f"{tag}: 281 not under turn280")
    if getattr(loop.turn281_inner, "__name__", "") != "turn291":
        raise RuntimeError(f"{tag}: 291 not under turn281")


def _check_292_base(loop, tag: str) -> None:
    if not isinstance(loop, L292.Loop292AgentLoop):
        raise RuntimeError(f"{tag}: loop is not Loop292AgentLoop")
    if "YesNo293Mixin" not in [c.__name__ for c in type(loop).__mro__]:
        raise RuntimeError(f"{tag}: YesNo293Mixin not on loop")
    if "Correct252LoopMixin" not in [c.__name__ for c in type(loop).__mro__]:
        raise RuntimeError(f"{tag}: Correct252LoopMixin not on loop")
    inner = getattr(loop, "_inner138j_ears", None)
    if "ChainLift266bMixin" not in [c.__name__ for c in type(inner).__mro__]:
        raise RuntimeError(f"{tag}: ChainLift266bMixin not on inner ears")
    if not isinstance(inner, L292.Loop292Ears):
        raise RuntimeError(f"{tag}: inner ears are not Loop292Ears")
    if not G228.is_installed():
        raise RuntimeError(f"{tag}: 228 guard not installed")
    if not G268.is_installed():
        raise RuntimeError(f"{tag}: 268 guard not installed")
    if getattr(loop.turn291_inner, "__name__", "") != "turn260":
        raise RuntimeError(f"{tag}: turn260 not under turn291")
    import claude_fix252_correct as F252
    if F252.value_ok252.__name__ != "value_ok252b":
        raise RuntimeError(f"{tag}: 252b screen not installed")


def _check(loop):
    if not G228.is_installed():
        raise RuntimeError("292t: 228 guard not installed")
    _check_292_base(loop, "292t")
    _check_talk_stack(loop, "292t")
    loop.notes.append(L292.NOTE292)
    loop.notes.append(NOTE292T)


def build_agent292t(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG292T, **(cfg or {}))
    loop = _with_292t(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes292tMixin:
    """Daemon mixin: 138k's daemon __init__ with the 292 classes and the
    292t-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        F252B.install_screen252b()
        _with_292t(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop292tDaemon(SrcGuardMixin228, Classes292tMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 292t
    build mixin ahead of the 220 mixin, exactly as 292 stacks its own."""


assert [c.__name__ for c in Loop292tDaemon.__mro__][:5] == [
    "Loop292tDaemon", "SrcGuardMixin228", "Classes292tMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 292t (talking join on 292)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG292T)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG292T)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop292tDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent292t(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
