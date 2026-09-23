#!/usr/bin/env python3
"""Merge 268b -- 138nb + the unchanged 268 n-hop direction guard.

New file only; every piece module is imported read-only and reused.

268b = base 138nb (scripts/claude_loop138nb_agent.py +
    artifacts/claude-merge138nb-20260923/loop138nb-config.json, with its
    saved rows in artifacts/claude-merge138nb-20260923/run/)
  + 268 THE ONE CHANGE unchanged (scripts/claude_fix268_nhopdir.py):
    question-side direction guard around the nhop frame. When the
    question is backwards-shaped about the composer `start` (the value
    slot: "Whose R is V?", "Who is/was married to V?",
    "Who has V as their R?", "What has/did V <verb>?" with the
    relation's own verb), the nhop frame is not used and the turn falls
    through UNCHANGED to the layers below (190 reverse, 221/237 table
    inverse). Forward n-hop questions are untouched. No writes.

How the guard gets in: process-locally, the way 138nb installs its own
overrides (claude_fix228_srcguard.install_srcguard228): at import
(SrcGuardMixin228 first, then install_nhopdir268) and again at build,
so every 268b process runs guarded. No existing file is edited. The
loop and ears classes are 138nb's own, unchanged (including the 190
"(worked out backwards)" label); only the composer module global is
rebound in this process.
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

import claude_fix268_nhopdir as G268  # noqa: E402 (the one change, unchanged)
import claude_loop138k_agent as L138K  # noqa: E402 (daemon base, read-only)
import claude_loop138m_agent as M138  # noqa: E402 (_Swap + 224c, read-only)
import claude_loop138n_agent as N138  # noqa: E402 (_set_paths, read-only)
import claude_loop138nb_agent as L138NB  # noqa: E402 (base, read-only)
import claude_loop232c_agent as L232C  # noqa: E402 (232c rule, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

G268.install_nhopdir268()  # 268 guard, at import

Loop268bEars = L138NB.Loop138nbEars  # ears unchanged from 138nb


class Loop268bAgentLoop(G228.SrcGuardMixin228, L138NB.Loop138nbAgentLoop):
    """138nb loop + SrcGuardMixin228 first (re-installs 228 at build).

    The 268 direction guard itself lives in the rebound composer module
    global (installed at import and at build); there is no turn
    override, so every non-nhop turn is 138nb byte-identical by
    construction. The 138nb "(worked out backwards)" label stays
    outermost below 228 (Label138nbMixin.turn cooperates via super()).
    """


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_L = _mro_names(Loop268bAgentLoop)
assert _L[0] == "Loop268bAgentLoop", _L
assert _L[1] == "SrcGuardMixin228", _L
assert "Loop138nbAgentLoop" in _L, _L
assert "Label138nbMixin" in _L, _L
assert "Loop138nAgentLoop" in _L, _L


def _with_268b(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", Loop268bEars),
                     (L138J, "Loop138jAgentLoop", Loop268bAgentLoop),
                     (L138J, "build_agent138j",
                      M138._build138j_plus224c)]):
        return fn(*args, **kwargs)


NOTE268B = ("loop268b: loop138nb + 268 n-hop direction guard "
            "(scripts/claude_fix268_nhopdir.py): a backwards-shaped "
            "question about the nhop start falls through to the layers "
            "below; forward n-hop untouched")

DEFAULT_CONFIG268B: dict = copy.deepcopy(L138NB.DEFAULT_CONFIG138NB)
DEFAULT_CONFIG268B["daemon"]["module"] = (
    "Loop268bDaemon (scripts/claude_loop268b_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG268B["self"] = dict(DEFAULT_CONFIG268B.get("self", {}))
DEFAULT_CONFIG268B["self"]["rule268b"] = (
    "268 n-hop direction guard (scripts/claude_fix268_nhopdir.py): "
    "compose_n_hop frames whose question is backwards-shaped about the "
    "start (Whose R is V? / Who is married to V? / Who has V as their R? "
    "/ What has/did V <verb>?) return None so 190/table layers answer; "
    "forward questions unchanged")
DEFAULT_CONFIG268B["merge268b"] = {
    "base": ("loop138nb (scripts/claude_loop138nb_agent.py, "
             "artifacts/claude-merge138nb-20260923/loop138nb-config.json)"),
    "added": ["268 question-side direction guard around compose_n_hop"],
    "loop_mro": _L[:8],
}


def _check(loop):
    L138NB._check(loop)  # 138nb's own checks (passes: subclass + same ears)
    loop.notes.pop()  # drop 138nb's note; ours follows
    if not isinstance(loop, Loop268bAgentLoop):
        raise RuntimeError("268b: loop is not Loop268bAgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop268bEars):
        raise RuntimeError("268b: inner ears are not Loop268bEars")
    if not G228.is_installed():
        raise RuntimeError("268b: 228 guard not installed")
    if not G268.is_installed():
        raise RuntimeError("268b: 268 guard not installed")
    t = vars(loop).get("turn")
    if t is None or getattr(t, "__name__", "") != "turn224c":
        raise RuntimeError("268b: 224c turn wrapper not installed")
    if not hasattr(loop, "decline224_log"):
        raise RuntimeError("268b: 224 not installed")
    loop.notes.append(M138.NOTE138M)
    loop.notes.append(N138.NOTE138N)
    loop.notes.append(L138NB.NOTE138NB)
    loop.notes.append(NOTE268B)


def build_agent268b(cfg: dict | None = None):
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    cfg = dict(DEFAULT_CONFIG268B, **(cfg or {}))
    loop = _with_268b(L138K.build_agent138k, cfg)
    N138._set_paths(loop, cfg)
    _check(loop)
    return loop


class _Guard268b(G228.SrcGuardMixin228):
    """SrcGuardMixin228, first in the daemon's MRO (installs the guard)."""


class Classes268bMixin:
    """Daemon mixin: 138k's daemon __init__ with the 268b classes and the
    224c-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        _with_268b(super().__init__, *args, **kwargs)
        cfg = dict(DEFAULT_CONFIG268B, **(getattr(self, "cfg", None) or {}))
        N138._set_paths(self.loop, cfg)
        _check(self.loop)


class Loop268bDaemon(_Guard268b, Classes268bMixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + 138nb stack + 268 guard."""


def run_daemon268b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop268bDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Merge 268b (138nb + guard)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG268B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG268B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon268b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        if not args.state_dir:
            parser.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent268b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
