#!/usr/bin/env python3
"""Exp 274: never-deaf step A on the 273 base (CPU only, GPU: no).

ONE change on the verified 273 build (scripts/claude_loop273_agent.py,
read-only): scripts/fable_agent_loop.py:313-319 turn() = submit() +
run_until_idle(), and busy() includes sleep_due(), so when sleep is due
the reply to a turn is only returned after the whole sleep runs. 273
fixed tick order but not this.

The change, installed as wrappers on the built loop object (additive
only; this file is new; every base module is imported read-only and
never edited):

  1. turn() runs ticks only while the inbox is non-empty (the listening
     ticks), returns/writes the reply, and leaves any due sleep for the
     next idle tick (the daemon's idle loop calls loop.step() directly;
     the next run_until_idle() outside a turn keeps its full behaviour).
     The full talking stack (turn282b ... turn291 ... class turn) is
     kept: the wrapper delegates to the saved outer turn and only scopes
     the inner drain (run_until_idle) to inbox ticks while the turn runs.
     Skipped ticks say nothing (SLEEP/WORK/THINKING events carry no
     sentences), so replies are unchanged; WORK vs SLEEP order is NOT
     changed (pending ruling for Ben).
  2. Deaf-seconds meter: for every turn, seconds between the message
     arriving and its reply being written, appended to
     loop.deaf_log274 (one {"n", "deaf_s"} row per turn) and summarised
     by deaf_summary274 (n, median, max).

The 273 step order (inbox -> sleep_due -> work_queue -> thinking) is
installed exactly as in 273; reader/ear stages are untouched.
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (read-only, drain + tick budget)
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

NOTE274_STEP = ("loop274: 292t with listen-before-sleep step order "
                "(scripts/claude_loop274_agent.py: inbox -> sleep_due -> "
                "work_queue -> thinking; reader/ear stages untouched)")
NOTE274_TURN = ("loop274: reply-first turn (scripts/claude_loop274_agent.py: "
                "turn() drains listening ticks only and returns the reply "
                "before any due sleep; sleep left for the next idle tick; "
                "deaf seconds logged per turn on loop.deaf_log274)")


def _step_listen_first274(self):
    """step() with Ben's order: inbox first, then sleep_due.

    Same four ticks as scripts/fable_agent_loop.py AgentLoop.step
    (same bound _listening_tick / _sleep_tick / _work_tick /
    _thinking_tick, same tick/mode/save bookkeeping); only the first
    two branches are swapped. Identical to 273's step.
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


def _run_until_idle274(self, limit: int = A.MAX_TICKS_PER_RUN) -> list[dict]:
    """run_until_idle() scoped during a 274 turn, full otherwise.

    While a 274 turn runs (loop._listen_only274 True), drain ticks only
    while the inbox is non-empty, i.e. the listening ticks; the reply is
    then returned before any due sleep tick runs. Outside a turn the
    saved original runs unchanged (the daemon's idle loop calls step()
    directly and never touches this path).
    """
    if getattr(self, "_listen_only274", False):
        events: list[dict] = []
        while self.inbox and len(events) < limit:
            events.append(self.step())
        return events
    return self._orig_run_until_idle274(limit)


def _turn274(self, text: str) -> list[str]:
    """Reply-first turn: delegate to the saved full stack, scope the drain.

    The saved outer turn (turn282b ... class turn) is kept whole; only
    the inner run_until_idle drain is scoped to inbox ticks (see
    _run_until_idle274). Arrival time is taken here (message arriving),
    reply time when the stack returns (reply written out next by the
    caller); the gap is appended to loop.deaf_log274.
    """
    t_arrive = time.monotonic()
    self._listen_only274 = True
    try:
        said = self._orig_turn274(text)
    finally:
        self._listen_only274 = False
    t_reply = time.monotonic()
    self.deaf_log274.append({"n": len(self.deaf_log274) + 1,
                             "deaf_s": t_reply - t_arrive})
    return said


def install_listen_first274(loop):
    """Install the 273 step order on a built 292t loop object (idempotent)."""
    import types
    cur = getattr(loop, "__dict__", {}).get("step", None)
    if not (isinstance(cur, types.MethodType)
            and cur.__func__ is _step_listen_first274):
        loop.step = types.MethodType(_step_listen_first274, loop)
    if NOTE274_STEP not in getattr(loop, "notes", []):
        loop.notes.append(NOTE274_STEP)
    return loop


def install_turn_reply_first274(loop):
    """Install the reply-first turn + scoped drain + deaf meter (idempotent).

    Idempotent: a second call leaves the already-installed wrappers alone,
    keeps the existing deaf log, and does not duplicate notes.
    """
    import types
    cur_run = getattr(loop, "__dict__", {}).get("run_until_idle", None)
    if not (isinstance(cur_run, types.MethodType)
            and cur_run.__func__ is _run_until_idle274):
        loop._orig_run_until_idle274 = types.MethodType(
            type(loop).run_until_idle, loop)
        loop.run_until_idle = types.MethodType(_run_until_idle274, loop)
    cur_turn = getattr(loop, "__dict__", {}).get("turn", None)
    if not (isinstance(cur_turn, types.MethodType)
            and cur_turn.__func__ is _turn274):
        loop._orig_turn274 = loop.turn
        loop.turn = types.MethodType(_turn274, loop)
    if not isinstance(getattr(loop, "deaf_log274", None), list):
        loop.deaf_log274 = []
    if not isinstance(getattr(loop, "_listen_only274", None), bool):
        loop._listen_only274 = False
    if NOTE274_TURN not in getattr(loop, "notes", []):
        loop.notes.append(NOTE274_TURN)
    return loop


def deaf_summary274(loop) -> dict:
    """Summarise the per-turn deaf log: {n, median_s, max_s}."""
    vals = [float(r.get("deaf_s", 0.0)) for r in
            getattr(loop, "deaf_log274", []) or []]
    if not vals:
        return {"n": 0, "median_s": 0.0, "max_s": 0.0}
    return {"n": len(vals), "median_s": float(statistics.median(vals)),
            "max_s": float(max(vals))}


def _build274(cfg=None):
    """Exact 292t build plus the 273 step order (turn added after _check)."""
    loop = T292T.build_agent292t(cfg)
    return install_listen_first274(loop)


def _with_274(fn, *args, **kwargs):
    with M138._Swap([(L138J, "Loop138jEars", L292.Loop292Ears),
                      (L138J, "Loop138jAgentLoop", L292.Loop292AgentLoop),
                      (L138J, "build_agent138j", _build274)]):
        return fn(*args, **kwargs)


DEFAULT_CONFIG274: dict = copy.deepcopy(T292T.DEFAULT_CONFIG292T)
DEFAULT_CONFIG274["daemon"]["module"] = (
    "Loop274Daemon (scripts/claude_loop274_agent.py) over "
    "Loop138kDaemon with the 292 classes + talking layers + "
    "listen-before-sleep step order + reply-first turn")
DEFAULT_CONFIG274["exp274"] = {
    "base": "loop273 (scripts/claude_loop273_agent.py: 292t + "
            "listen-before-sleep step order)",
    "added": ["reply-first turn (instance wrapper on the built loop "
              "object: turn() drains listening ticks only, due sleep "
              "left for the next idle tick)",
              "deaf-seconds meter (loop.deaf_log274 per turn + "
              "deaf_summary274 median/max)"],
    "touches": ["turn() drain scope only"],
    "untouched": ["step() branch order (273: inbox -> sleep_due -> "
                  "work_queue -> thinking)", "turn stack", "reader stage",
                  "ear stages", "guards", "sleeper", "thinker", "notebook"],
}


def build_agent274(cfg: dict | None = None):
    """Build the 273 agent shape with the reply-first turn installed."""
    G228.install_srcguard228()
    L232C.install232c()
    G268.install_nhopdir268()
    F252B.install_screen252b()
    cfg = dict(DEFAULT_CONFIG274, **(cfg or {}))
    loop = _with_274(L138K.build_agent138k, cfg)
    T292T._check(loop)
    install_listen_first274(loop)
    install_turn_reply_first274(loop)
    if getattr(loop.turn, "__func__", None) is not _turn274:
        raise RuntimeError("274: reply-first turn not installed")
    return loop


class Classes274Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 292 classes, the 292t
    talking layers, the 273 step order and the 274 turn swapped in."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        L232C.install232c()
        G268.install_nhopdir268()
        F252B.install_screen252b()
        _with_274(super().__init__, *args, **kwargs)
        install_listen_first274(self.loop)
        T292T._check(self.loop)
        install_turn_reply_first274(self.loop)


class Loop274Daemon(SrcGuardMixin228, Classes274Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 274
    build mixin ahead of the 220 mixin, exactly as 273 stacks its own."""


assert [c.__name__ for c in Loop274Daemon.__mro__][:5] == [
    "Loop274Daemon", "SrcGuardMixin228", "Classes274Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 274 (reply-first on 273)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG274)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG274)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop274Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent274(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
