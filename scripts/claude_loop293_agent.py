#!/usr/bin/env python3
"""Merge 293 -- 138nb + THE ONE CHANGE (yes/no reader).

Base (read-only): scripts/claude_loop138nb_agent.py with
artifacts/claude-merge138nb-20260923/loop138nb-config.json.

THE ONE CHANGE (design/v3/30-modes/293-yesno-questions.md): one loop-level
reader in the 154d slot, scripts/claude_fix293_yesno.py (YesNo293Mixin):
on the didn't-understand miss clarify it answers yes/no questions
read-only from the notebook (Does-have / Has-got / Does-live-in /
Does-work-at-for / Does-come-from / Was-born-in / Is with multi-word
names / Is-of-forms). 154d's own shapes keep 154d's byte-identical
replies and stage tags (154d imported read-only). Chain subjects pass
through unchanged. No other reply changes, no new writes.

LOOP: Loop293AgentLoop = YesNo293Mixin outermost over 138nb's
Loop138nbAgentLoop (everything below unchanged). EARS: 138nb's
Loop138nbEars unchanged. SrcGuardMixin228 stays first in the daemon MRO;
install_srcguard228() runs at import.

New file only; every other module is imported read-only.
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

import claude_fix293_yesno as F293  # noqa: E402 (the one change)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only)
import claude_loop138n_agent as N138  # noqa: E402 (read-only)
import claude_loop138nb_agent as NB138  # noqa: E402 (base, read-only)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

Loop293Ears = NB138.Loop138nbEars  # ears unchanged from 138nb


class Loop293AgentLoop(F293.YesNo293Mixin, NB138.Loop138nbAgentLoop):
    """138nb loop + the 293 yes/no reader, outermost (read-only)."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_L = _mro_names(Loop293AgentLoop)
assert _L[0] == "Loop293AgentLoop", _L
assert _L[1] == "YesNo293Mixin", _L
assert _L[2] == "Loop138nbAgentLoop", _L


def _with_293(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", Loop293Ears),
                     (L138J, "Loop138jAgentLoop", Loop293AgentLoop),
                     (L138J, "build_agent138j",
                      M138._build138j_plus224c)]):
        return fn(*args, **kwargs)


NOTE293 = ("loop293: loop138nb + yes/no reader "
          "'(scripts/claude_fix293_yesno.py)'")

DEFAULT_CONFIG293: dict = copy.deepcopy(NB138.DEFAULT_CONFIG138NB)
DEFAULT_CONFIG293["daemon"]["module"] = (
    "Loop293Daemon (scripts/claude_loop293_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG293["merge293"] = {
    "base": "loop138nb (scripts/claude_loop138nb_agent.py)",
    "added": ["yes/no reader "
              "(scripts/claude_fix293_yesno.py YesNo293Mixin, "
              "outermost read-only rule over 138nb's loop)"],
    "loop_extra": "YesNo293Mixin outermost over Loop138nbAgentLoop",
}


def _set_paths(loop, cfg: dict) -> None:
    N138._set_paths(loop, cfg)


def _check(loop):
    N138._check(loop)  # 138n's own checks (138m checks + 138n classes)
    loop.notes.pop()  # drop 138n's note; ours follows
    if not isinstance(loop, Loop293AgentLoop):
        raise RuntimeError("293: loop is not Loop293AgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop293Ears):
        raise RuntimeError("293: inner ears are not Loop293Ears")
    loop.notes.append(M138.NOTE138M)
    loop.notes.append(N138.NOTE138N)
    loop.notes.append(NB138.NOTE138NB)
    loop.notes.append(NOTE293)


def build_agent293(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    cfg = dict(DEFAULT_CONFIG293, **(cfg or {}))
    loop = _with_293(L138K.build_agent138k, cfg)
    _set_paths(loop, cfg)
    _check(loop)
    return loop


class _Guard293(G228.SrcGuardMixin228):
    """SrcGuardMixin228, first in the daemon's MRO (installs the guard)."""


class Classes293Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 293 classes and the
    224c-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        _with_293(super().__init__, *args, **kwargs)
        cfg = dict(DEFAULT_CONFIG293, **(getattr(self, "cfg", None) or {}))
        _set_paths(self.loop, cfg)
        _check(self.loop)


class Loop293Daemon(_Guard293, Classes293Mixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + 138l/138m pieces + 138n line + 138nb label + 293."""


def run_daemon293(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    return Loop293Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Merge 293 (138nb + 1)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG293)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG293)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon293(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        if not args.state_dir:
            parser.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent293(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
