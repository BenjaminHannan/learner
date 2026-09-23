#!/usr/bin/env python3
"""Exp 266 agent: loop138m + the chain-subject lift (one outermost ears stage).

loop266 = loop138m (scripts/claude_loop138m_agent.py: the newest accepted
base; its ears class Loop138mEars is reused as is)
  ears   + ChainLift266Mixin (scripts/claude_fix266_chainlift.py: THE ONE
           CHANGE, outermost; questions only, never writes)
  loop     (unchanged turn path: ask -> reasoner -> mouth)

ORDER (outermost first) and why:
  ChainLift266Mixin -- sees the raw turn first, exactly like 221c's
      QNorm221cMixin on its own stack. A lifted question is served from
      the canonical possessive hear; every other turn (statements,
      plain-name questions, possessive questions the probe rejects, "my"
      chains with no reader) goes through the 138m stack byte-identical.
  SrcGuardMixin228 -- installs the 228 guard first at import and at build
      (as in 138k/138l/138m).

How the classes get in: as in 138l/138m, build_agent138j (read-only)
constructs L138J.Loop138jEars / L138J.Loop138jAgentLoop by module-global
name; this file swaps those two globals for the 266 subclasses only while
the agent is built (process-local, restored in finally), with 138m's
224/224c-installing build as the construction function.
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

import claude_fix266_chainlift as F266  # noqa: E402 (the one change)
import claude_loop138k_agent as L138K  # noqa: E402 (daemon base, read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

_ORIG_EARS = L138J.Loop138jEars
_ORIG_LOOP = L138J.Loop138jAgentLoop
_ORIG_BUILD = L138J.build_agent138j


class Loop266Ears(G228.SrcGuardMixin228, F266.ChainLift266Mixin,
                  L138M.Loop138mEars):
    """138m ears with the 266 chain-subject lift outermost."""

    name = "loop266-chainlift"


class Loop266AgentLoop(L138M.Loop138mAgentLoop):
    """138m loop unchanged (renamed for logs)."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_E = _mro_names(Loop266Ears)
assert _E[:4] == ["Loop266Ears", "SrcGuardMixin228", "ChainLift266Mixin",
                  "Loop138lEars"], _E
_L = _mro_names(Loop266AgentLoop)
assert _L[:3] == ["Loop266AgentLoop", "Loop138mAgentLoop",
                  "Loop233AgentLoop"], _L
assert _L.index("Loop138jAgentLoop") < _L.index("Loop138iAgentLoop"), _L


def _with_266(fn, *args, **kwargs):
    pairs = [(L138J, "Loop138jEars", Loop266Ears),
             (L138J, "Loop138jAgentLoop", Loop266AgentLoop),
             (L138J, "build_agent138j", L138M._build138j_plus224c)]
    saved = [(mod, name, getattr(mod, name)) for mod, name, _ in pairs]
    for mod, name, val in pairs:
        setattr(mod, name, val)
    try:
        return fn(*args, **kwargs)
    finally:
        for mod, name, val in reversed(saved):
            setattr(mod, name, val)


NOTE266 = ("loop266: loop138m + 266 chain-subject lift "
           "(scripts/claude_fix266_chainlift.py): a verb/when question "
           "whose subject is a possessive chain is served from the "
           "canonical possessive hear; everything else byte-identical")

DEFAULT_CONFIG266: dict = copy.deepcopy(L138M.DEFAULT_CONFIG138M)
DEFAULT_CONFIG266["daemon"]["module"] = (
    "Loop266Daemon (scripts/claude_loop266_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG266["self"] = dict(DEFAULT_CONFIG266.get("self", {}))
DEFAULT_CONFIG266["self"]["rule266"] = (
    "266 chain-subject lift (scripts/claude_fix266_chainlift.py): "
    "a ?-turn with a possessive-chain subject is placeholder-probed "
    "(dry, write-free; exactly one one-hop ask frame for the placeholder) "
    "and served from 'What/Who is <chain>'s R?'; all other turns pass "
    "through byte-identical; never writes")
DEFAULT_CONFIG266["merge266"] = {
    "base": "loop138m (scripts/claude_loop138m_agent.py)",
    "added": ["266 chain-subject lift outermost ears stage"],
    "ears_mro": _E[:8],
    "loop_mro": _L[:12],
}


def _check(loop):
    if not isinstance(loop, Loop266AgentLoop):
        raise RuntimeError("266: loop is not Loop266AgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop266Ears):
        raise RuntimeError("266: inner ears are not Loop266Ears")
    import fable_fix220_restartindex as F220
    if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
        raise RuntimeError("266: notebook is not FixedIndexedLoopNotebook")
    if not G228.is_installed():
        raise RuntimeError("266: 228 guard not installed")
    t = vars(loop).get("turn")
    if t is None or getattr(t, "__name__", "") != "turn224c":
        raise RuntimeError("266: 224c turn wrapper not installed")
    if not hasattr(loop, "decline224_log"):
        raise RuntimeError("266: 224 not installed")
    loop.notes.append(NOTE266)


def build_agent266(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG266, **(cfg or {}))
    loop = _with_266(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes266Mixin:
    """Daemon mixin: 228 guard first, then 138k's daemon __init__ with the
    266 classes swapped in for the build only."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_266(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop266Daemon(Classes266Mixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + the 266 chain-subject lift.

    SrcGuardMixin228 stays first in the daemon chain (via Loop138kDaemon:
    SrcGuardMixin228 > RestartIndex220Mixin > Loop138jDaemon) and
    install_srcguard228() runs at import and first in every build path.
    """


def run_daemon266(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    return Loop266Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Exp 266 chain lift on 138m")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return F266.selftest266()
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG266)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG266)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon266(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent266(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
