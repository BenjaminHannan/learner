#!/usr/bin/env python3
"""Merge 268 -- 138m + the n-hop direction guard (reasoning line). New file
only; every piece module is imported read-only and reused.

268 = base 138m (scripts/claude_loop138m_agent.py +
    artifacts/claude-merge138m-20260922/loop138m-config.json)
  + 268 THE ONE CHANGE (scripts/claude_fix268_nhopdir.py):
    question-side direction guard around the nhop frame. When the question
    is backwards-shaped about the composer `start` (the value slot), the
    nhop frame is not used and the turn falls through UNCHANGED to the
    layers below (190 reverse and friends). Forward n-hop questions are
    untouched. No writes.

How the guard gets in: process-locally, the way 138m installs its own
overrides (claude_fix228_srcguard.install_srcguard228): at import
(SrcGuardMixin228 first, then install_nhopdir268) and again at build, so
every 268 process runs guarded. No existing file is edited. The loop and
ears classes are 138m's own, unchanged; only the composer module global
is rebound in this process.
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

import claude_fix268_nhopdir as G268  # noqa: E402 (the one change)
import claude_loop138k_agent as L138K  # noqa: E402 (daemon base, read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

G268.install_nhopdir268()  # 268 guard, at import

Loop268Ears = L138M.Loop138mEars  # ears unchanged from 138m


class Loop268AgentLoop(G228.SrcGuardMixin228, L138M.Loop138mAgentLoop):
    """138m loop + SrcGuardMixin228 first (re-installs 228 at build).

    The 268 direction guard itself lives in the rebound composer module
    global (installed at import and at build); there is no turn override,
    so every non-nhop turn is 138m byte-identical by construction.
    """


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_L = _mro_names(Loop268AgentLoop)
assert _L[0] == "Loop268AgentLoop", _L
assert _L[1] == "SrcGuardMixin228", _L
assert "Loop138mAgentLoop" in _L, _L


def _build268(cfg=None):
    """138m's 224c-installing build, with the 268 classes swapped in."""
    import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
    G228.install_srcguard228()
    G268.install_nhopdir268()
    saved = [(L138J.Loop138jEars, "Loop138jEars"),
             (L138J.Loop138jAgentLoop, "Loop138jAgentLoop"),
             (L138J.build_agent138j, "build_agent138j")]
    L138J.Loop138jEars = Loop268Ears  # type: ignore[assignment]
    L138J.Loop138jAgentLoop = Loop268AgentLoop  # type: ignore[assignment]
    L138J.build_agent138j = L138M._build138j_plus224c  # type: ignore[assignment]
    try:
        import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
        loop = L138K.build_agent138k(cfg)
    finally:
        (L138J.Loop138jEars, L138J.Loop138jAgentLoop,
         L138J.build_agent138j) = [s[0] for s in saved]
    return loop


NOTE268 = ("loop268: loop138m + 268 n-hop direction guard "
           "(scripts/claude_fix268_nhopdir.py): a backwards-shaped question "
           "about the nhop start falls through to the layers below; "
           "forward n-hop untouched")

DEFAULT_CONFIG268: dict = copy.deepcopy(L138M.DEFAULT_CONFIG138M)
DEFAULT_CONFIG268["daemon"]["module"] = (
    "Loop268Daemon (scripts/claude_loop268_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG268["self"] = dict(DEFAULT_CONFIG268.get("self", {}))
DEFAULT_CONFIG268["self"]["rule268"] = (
    "268 n-hop direction guard (scripts/claude_fix268_nhopdir.py): "
    "compose_n_hop frames whose question is backwards-shaped about the "
    "start (Whose R is V? / Who is married to V? / Who has V as their R? / "
    "What has/did V <verb>?) return None so 190/153/table layers answer; "
    "forward questions unchanged")
DEFAULT_CONFIG268["merge268"] = {
    "base": ("loop138m (scripts/claude_loop138m_agent.py, "
             "artifacts/claude-merge138m-20260922/loop138m-config.json)"),
    "added": ["268 question-side direction guard around compose_n_hop"],
    "loop_mro": _L[:6],
}


def _check(loop):
    if not isinstance(loop, Loop268AgentLoop):
        raise RuntimeError("268: loop is not Loop268AgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop268Ears):
        raise RuntimeError("268: inner ears are not Loop268Ears")
    import fable_fix220_restartindex as F220
    if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
        raise RuntimeError("268: notebook is not FixedIndexedLoopNotebook")
    if not G228.is_installed():
        raise RuntimeError("268: 228 guard not installed")
    if not G268.is_installed():
        raise RuntimeError("268: 268 guard not installed")
    t = vars(loop).get("turn")
    if t is None or getattr(t, "__name__", "") != "turn224c":
        raise RuntimeError("268: 224c turn wrapper not installed")
    if not hasattr(loop, "decline224_log"):
        raise RuntimeError("268: 224 not installed")
    loop.notes.append(NOTE268)


def build_agent268(cfg: dict | None = None):
    G228.install_srcguard228()
    G268.install_nhopdir268()
    cfg = dict(DEFAULT_CONFIG268, **(cfg or {}))
    loop = _build268(cfg)
    _check(loop)
    return loop


class Classes268Mixin:
    """Daemon mixin: 228 + 268 guards first, then 138k's daemon __init__
    with the 268 classes and the 224c-installing build swapped in."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        G268.install_nhopdir268()
        import fable_loop138j_agent as L138J  # noqa: E402 (read-only)
        saved = [(L138J.Loop138jEars, "Loop138jEars"),
                 (L138J.Loop138jAgentLoop, "Loop138jAgentLoop"),
                 (L138J.build_agent138j, "build_agent138j")]
        L138J.Loop138jEars = Loop268Ears  # type: ignore[assignment]
        L138J.Loop138jAgentLoop = Loop268AgentLoop  # type: ignore[assignment]
        L138J.build_agent138j = (  # type: ignore[assignment]
            L138M._build138j_plus224c)
        try:
            super().__init__(*args, **kwargs)
        finally:
            (L138J.Loop138jEars, L138J.Loop138jAgentLoop,
             L138J.build_agent138j) = [s[0] for s in saved]
        _check(self.loop)


class Loop268Daemon(Classes268Mixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + 138m stack + 268 guard."""


def run_daemon268(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    return Loop268Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Merge 268 (138m + guard)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG268)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG268)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon268(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent268(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
