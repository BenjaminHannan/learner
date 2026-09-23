#!/usr/bin/env python3
"""Merge 138l -- staged merge: 138k + the six safety pieces 209, 212, 216,
222, 223, 226. New file only; every piece module is imported read-only
and its OWN classes are reused (no rule body is copied or re-typed).

loop138l = loop138k (scripts/claude_loop138k_agent.py: 138j + 228 guard
           + 220 restart index, unchanged)
  ears   + 209 WriteScreen209EarsMixin   (scripts/fable_loop209_agent.py)
         + 223 Loop223Ears               (scripts/fable_loop223_agent.py)
         + 222 Loop222Ears (215 rewrite + 222 a/an gate)
                                          (scripts/fable_loop222_agent.py,
                                           scripts/fable_loop215_agent.py)
  loop   + 226 Source226Mixin            (scripts/fable_loop226_agent.py)
         + 212 Loop212AgentLoop.turn     (scripts/fable_loop212_agent.py)
         + 216 Loop216AgentLoop.turn     (scripts/fable_loop216_agent.py)
         + 209 WriteScreen209LoopMixin   (_act value backstop)

EARS MRO (outermost first; C3 linearisation, asserted at import):
  WriteScreen209 > Loop223Ears > [138j layer C: Case180b > Apos193 >
  About164b > Reverse190b > Reverse190 > Negate154f > Replace154g] >
  Loop222Ears > Loop215Ears > OfTeach215Mixin > Loop138iEars chain.
  - 209 post-processes every action the full chain returns (outermost,
    as on its own 138i stack).
  - 223 patches S148.trigger_spans for the WHOLE hear call when it
    fires (outermost below 209, as on its own stack).
  - 215/222 sit directly on the 138i chain, as on their own stack, so
    222's sealed gate call `L138I.Loop138iEars.hear(self, turn)` still
    skips exactly the 215 mixin and nothing else (Loop222Ears and
    Loop215Ears define no other hear). Layer C sees the raw turn first
    (case/apostrophe normalisation happens before the of-rewrite).
LOOP MRO (outermost first):
  Source226 > Loop212 > Loop216 > WriteScreen209Loop > Loop138jAgentLoop
  (> Disp180bTick > About164bTick > CorrectReply192 > Negate154fAct >
  Replace154gAct > Loop138iAgentLoop ...).
  - 226's tick interception runs before every other tick layer and its
    turn() wraps everything (as on its own stack).
  - 212 then 216 swap L138._route127 for the turn (216's docstring:
    either nesting order gives the same verdicts).
DAEMON: Loop138lDaemon(Classes138lMixin, Loop138kDaemon); the 228 guard
  is installed at import and again first thing in __init__; MRO after
  this class is 138k's (SrcGuardMixin228 > RestartIndex220Mixin >
  Loop138jDaemon).
How the classes get in: build_agent138j (read-only) constructs
L138J.Loop138jEars / L138J.Loop138jAgentLoop by module-global name; this
file swaps those two globals for the 138l subclasses only while the
agent is built (process-local, restored in finally), exactly the
mechanism 138k uses for the 220 notebook and 226 uses on 138i.
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

G228.install_srcguard228()  # 228 first, at import

import claude_loop138k_agent as L138K  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
import fable_loop209_agent as L209  # noqa: E402 (piece, read-only)
import fable_loop212_agent as L212  # noqa: E402 (piece, read-only)
import fable_loop216_agent as L216  # noqa: E402 (piece, read-only)
import fable_loop222_agent as L222  # noqa: E402 (piece, read-only)
import fable_loop223_agent as L223  # noqa: E402 (piece, read-only)
import fable_loop226_agent as L226  # noqa: E402 (piece, read-only)

_ORIG_EARS = L138J.Loop138jEars
_ORIG_LOOP = L138J.Loop138jAgentLoop


class Loop138lEars(L209.WriteScreen209EarsMixin, L223.Loop223Ears,
                   _ORIG_EARS, L222.Loop222Ears):
    """138j ears + 209 screen (outermost) + 223 bypass + 215/222."""

    name = "loop138l-safety"


class Loop138lAgentLoop(L226.Source226Mixin, L212.Loop212AgentLoop,
                        L216.Loop216AgentLoop, L209.WriteScreen209LoopMixin,
                        _ORIG_LOOP):
    """138j loop + 226 source layer + 212/216 router gates + 209 _act."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


# Order assertions (fail loudly at import if C3 ever differs).
_E = _mro_names(Loop138lEars)
assert _E[:4] == ["Loop138lEars", "WriteScreen209EarsMixin", "Loop223Ears",
                  "Loop138jEars"], _E
assert _E.index("Replace154gEarsMixin") < _E.index("Loop222Ears") \
    < _E.index("Loop215Ears") < _E.index("OfTeach215Mixin") \
    < _E.index("Loop138iEars"), _E
_L = _mro_names(Loop138lAgentLoop)
assert _L[:6] == ["Loop138lAgentLoop", "Source226Mixin", "Loop212AgentLoop",
                  "Loop216AgentLoop", "WriteScreen209LoopMixin",
                  "Loop138jAgentLoop"], _L
assert _L.index("Loop138jAgentLoop") < _L.index("Loop138iAgentLoop"), _L


def _with_138l_classes(fn, *args, **kwargs):
    L138J.Loop138jEars = Loop138lEars  # type: ignore[misc]
    L138J.Loop138jAgentLoop = Loop138lAgentLoop  # type: ignore[misc]
    try:
        return fn(*args, **kwargs)
    finally:
        L138J.Loop138jEars = _ORIG_EARS  # type: ignore[misc]
        L138J.Loop138jAgentLoop = _ORIG_LOOP  # type: ignore[misc]


NOTE138L = ("loop138l: loop138k + 209 write screen + 212 statement gate + "
            "216 decline cue gate + 222 (215) of-teach + 223 cant-do "
            "bypass + 226 source questions")

DEFAULT_CONFIG138L: dict = copy.deepcopy(L138K.DEFAULT_CONFIG138K)
DEFAULT_CONFIG138L["daemon"]["module"] = (
    "Loop138lDaemon (scripts/claude_loop138l_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG138L["merge138l"] = {
    "base": "loop138k (scripts/claude_loop138k_agent.py)",
    "added": ["209 write screen", "212 self-router statement gate",
              "216 decline-intent cue gate",
              "222 a/an of-teach gate (with 215 of-teach rewrite)",
              "223 cant-do negation-screen bypass",
              "226 source questions about the last reply"],
    "ears_mro": _E[:12],
    "loop_mro": _L[:12],
}


def _check(loop):
    if not isinstance(loop, Loop138lAgentLoop):
        raise RuntimeError("138l: loop is not Loop138lAgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop138lEars):
        raise RuntimeError("138l: inner ears are not Loop138lEars")
    import fable_fix220_restartindex as F220
    if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
        raise RuntimeError("138l: notebook is not FixedIndexedLoopNotebook")
    if not G228.is_installed():
        raise RuntimeError("138l: 228 guard not installed")
    loop.notes.append(NOTE138L)


def build_agent138l(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG138L, **(cfg or {}))
    loop = _with_138l_classes(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes138lMixin:
    """Daemon mixin: 228 guard first, then 138k's daemon __init__ with the
    138l ears/loop classes swapped in for the build only."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_138l_classes(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop138lDaemon(Classes138lMixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + the six 138l safety pieces."""


def run_daemon138l(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop138lDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Merge 138l (138k + 6)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138L)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG138L)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138l(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138l(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
