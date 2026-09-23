#!/usr/bin/env python3
"""Exp 273: listen-before-sleep on the 292t base (CPU only, GPU: no).

ONE change on main base 292t (scripts/claude_loop292t_agent.py, read-only):
the loop's step() schedule checks the inbox BEFORE sleep_due(), i.e. the
order becomes inbox -> sleep_due -> work_queue -> thinking, instead of the
inherited scripts/fable_agent_loop.py order
(sleep_due -> inbox -> work_queue -> thinking), which delays a waiting user
turn by a whole sleep tick.

Additive only: this file is new. The 292t build (classes, turn stack,
reader/ear stages, guards, config) is reused read-only through
claude_loop292t_agent.build_agent292t; the reorder is a bound-method
wrapper installed on the built loop object (install_listen_first273), so
no existing file is edited. Reader/ear stages are untouched (the listener
line wraps the READER stage separately, and must not collide with this).
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
import claude_fix252b_screen as F252B  # noqa: E402 (read-only)
import claude_fix268_nhopdir as G268  # noqa: E402 (268 guard, read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as M138  # noqa: E402 (read-only, _Swap)
import claude_loop232c_agent as L232C  # noqa: E402 (read-only, 232c rule)
import claude_loop292_agent as L292  # noqa: E402 (base classes, read-only)
import claude_loop292t_agent as T292T  # noqa: E402 (base build, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)

NOTE273 = ("loop273: 292t with listen-before-sleep step order "
           "(scripts/claude_loop273_agent.py: inbox -> sleep_due -> "
           "work_queue -> thinking; reader/ear stages untouched)")


def _step_listen_first273(self):
    """step() with Ben's order: inbox first, then sleep_due.

    Same four ticks as scripts/fable_agent_loop.py AgentLoop.step
    (same bound _listening_tick / _sleep_tick / _work_tick /
    _thinking_tick, same tick/mode/save bookkeeping); only the first
    two branches are swapped.
    """
    self.tick += 1
    if self.inbox:
        event = self._listening_tick()
    elif self.sleep_due():
        event = self._sleep_tick()
    elif self.work_queue:
        event = self._work_tick()
    else:
        event = self._thinking_tick()
    self.mode = event["mode"]
    self._save()
    return event


def install_listen_first273(loop):
    """Install the 273 order on a built 292t loop object (instance wrapper).

    Idempotent: a second call leaves the already-installed wrapper alone
    and does not duplicate the note.
    """
    import types
    cur = getattr(loop, "__dict__", {}).get("step", None)
    if not (isinstance(cur, types.MethodType)
            and cur.__func__ is _step_listen_first273):
        loop.step = types.MethodType(_step_listen_first273, loop)
    if NOTE273 not in getattr(loop, "notes", []):
        loop.notes.append(NOTE273)
    return loop


def _build273(cfg=None):
    """Exact 292t build, then the listen-first wrapper on the object."""
    loop = T292T.build_agent292t(cfg)
    return install_listen_first273(loop)


def _with_273(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", L292.Loop292Ears),
                      (L138J, "Loop138jAgentLoop", L292.Loop292AgentLoop),
                      (L138J, "build_agent138j", _build273)]):
        return fn(*args, **kwargs)


DEFAULT_CONFIG273: dict = copy.deepcopy(T292T.DEFAULT_CONFIG292T)
DEFAULT_CONFIG273["daemon"]["module"] = (
    "Loop273Daemon (scripts/claude_loop273_agent.py) over "
    "Loop138kDaemon with the 292 classes + talking layers + "
    "listen-before-sleep step order")
DEFAULT_CONFIG273["exp273"] = {
    "base": "loop292t (scripts/claude_loop292t_agent.py)",
    "added": ["listen-before-sleep step order (instance wrapper on the "
              "built loop object; inbox -> sleep_due -> work_queue -> "
              "thinking)"],
    "touches": ["step() branch order only"],
    "untouched": ["turn stack", "reader stage", "ear stages", "guards",
                  "sleeper", "thinker", "notebook"],
}


def build_agent273(cfg: dict | None = None):
    """Build the 292t agent shape with the 273 step order installed."""
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG273, **(cfg or {}))
    loop = _with_273(L138K.build_agent138k, cfg)
    T292T._check(loop)
    install_listen_first273(loop)
    return loop


class Classes273Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 292 classes, the 292t
    talking layers and the 273 step order swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        F252B.install_screen252b()
        _with_273(super().__init__, *args, **kwargs)
        install_listen_first273(self.loop)
        T292T._check(self.loop)


class Loop273Daemon(SrcGuardMixin228, Classes273Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 273
    build mixin ahead of the 220 mixin, exactly as 292t stacks its own."""


assert [c.__name__ for c in Loop273Daemon.__mro__][:5] == [
    "Loop273Daemon", "SrcGuardMixin228", "Classes273Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 273 (listen-first on 292t)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG273)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG273)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop273Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent273(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
