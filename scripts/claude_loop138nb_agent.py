#!/usr/bin/env python3
"""Merge 138nb -- 138n + THE ONE CHANGE (label 190's backwards answers).

Base (read-only): scripts/claude_loop138n_agent.py with
artifacts/claude-merge138n-20260922/loop138n-config.json and its saved
rows in artifacts/claude-merge138n-20260922/run/.

THE ONE CHANGE (design/v3/30-modes/138nb-inverse-diagnosis.md): one
outermost reply-text wrapper, scripts/claude_fix138nb_label.py
(Label138nbMixin): when the turn's answering stage is exactly
"loop190-reverse" and the reply names at least one subject (190's "S's
R is V." sentences, including "Your R is V."), append " (worked out
backwards)" (LABEL221 text, one space). No other reply changes, no new
shapes, no ownership change, no writes. 190's "I don't know anyone
whose R is V." and unknown-name replies stay byte-identical.

LOOP: Loop138nbAgentLoop = Label138nbMixin outermost over 138n's
Loop138nAgentLoop (Cap138nMixin G3 and everything below unchanged).
EARS: 138n's Loop138nEars unchanged. SrcGuardMixin228 stays first in
the daemon MRO; install_srcguard228() runs at import.

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

import claude_fix138nb_label as LB138NB  # noqa: E402 (the one change)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only)
import claude_loop138n_agent as N138  # noqa: E402 (base, read-only)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

Loop138nbEars = N138.Loop138nEars  # ears unchanged from 138n


class Loop138nbAgentLoop(LB138NB.Label138nbMixin, N138.Loop138nAgentLoop):
    """138n loop + the 190-answer label, outermost (text only)."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_L = _mro_names(Loop138nbAgentLoop)
assert _L[0] == "Loop138nbAgentLoop", _L
assert _L[1] == "Label138nbMixin", _L
assert _L[2] == "Loop138nAgentLoop", _L
assert _L[3] == "Cap138nMixin", _L


def _with_138nb(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", Loop138nbEars),
                     (L138J, "Loop138jAgentLoop", Loop138nbAgentLoop),
                     (L138J, "build_agent138j",
                      M138._build138j_plus224c)]):
        return fn(*args, **kwargs)


NOTE138NB = ("loop138nb: loop138n + label 190's backwards answers "
             "' (worked out backwards)' (scripts/claude_fix138nb_label.py)")

DEFAULT_CONFIG138NB: dict = copy.deepcopy(N138.DEFAULT_CONFIG138N)
DEFAULT_CONFIG138NB["daemon"]["module"] = (
    "Loop138nbDaemon (scripts/claude_loop138nb_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG138NB["merge138nb"] = {
    "base": "loop138n (scripts/claude_loop138n_agent.py)",
    "added": ["label 190 reverse answers "
              "(scripts/claude_fix138nb_label.py Label138nbMixin, "
              "outermost reply-text rule over 138n's loop)"],
    "loop_extra": "Label138nbMixin outermost over Loop138nAgentLoop",
}


def _set_paths(loop, cfg: dict) -> None:
    N138._set_paths(loop, cfg)


def _check(loop):
    N138._check(loop)  # 138n's own checks (138m checks + 138n classes)
    loop.notes.pop()  # drop 138n's note; ours follows
    if not isinstance(loop, Loop138nbAgentLoop):
        raise RuntimeError("138nb: loop is not Loop138nbAgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop138nbEars):
        raise RuntimeError("138nb: inner ears are not Loop138nbEars")
    loop.notes.append(M138.NOTE138M)
    loop.notes.append(N138.NOTE138N)
    loop.notes.append(NOTE138NB)


def build_agent138nb(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    cfg = dict(DEFAULT_CONFIG138NB, **(cfg or {}))
    loop = _with_138nb(L138K.build_agent138k, cfg)
    _set_paths(loop, cfg)
    _check(loop)
    return loop


class _Guard138nb(G228.SrcGuardMixin228):
    """SrcGuardMixin228, first in the daemon's MRO (installs the guard)."""


class Classes138nbMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138nb classes and the
    224c-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        _with_138nb(super().__init__, *args, **kwargs)
        cfg = dict(DEFAULT_CONFIG138NB, **(getattr(self, "cfg", None) or {}))
        _set_paths(self.loop, cfg)
        _check(self.loop)


class Loop138nbDaemon(_Guard138nb, Classes138nbMixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + 138l/138m pieces + 138n reading line + 138nb label."""


def run_daemon138nb(root, cfg: dict | None = None,
                    idle_seconds: float = 30.0) -> int:
    return Loop138nbDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Merge 138nb (138n + 1)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138NB)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG138NB)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138nb(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
    if args.once:
        if not args.state_dir:
            parser.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent138nb(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
