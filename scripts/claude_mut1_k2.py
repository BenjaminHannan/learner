#!/usr/bin/env python3
"""EXP mut-1 k2: 274 wrapped with ONE deliberate break (CPU only).

Break k2: the inbox branch is DROPPED from step() (sleep_due ->
work_queue -> thinking). A waiting message is therefore never chosen by
step(); only the 274 reply-first turn wrapper (kept) still references the
inbox. Expected: M1 fails (inbox never drains / sleep runs inside the
turn), M2 fails (no SLEEP reachable while the inbox shadows nothing but
is never consumed... reported as measured), panel replies change.

Additive only: this file is new. scripts/claude_loop274_agent.py is
imported read-only and never edited; the break is installed as a bound
method on the built loop object.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop274_agent as B274  # noqa: E402 (read-only base)

NOTE_MUT1_K2 = ("loopmut1-k2 (scripts/claude_mut1_k2.py: 274 with the inbox "
                "branch dropped from step(); listening tick never chosen "
                "by step; reply-first turn kept)")


def _step_no_inbox_k2(self):
    """274 step with the inbox branch dropped (ONE break)."""
    self.tick += 1
    if self.sleep_due():
        event = self._sleep_tick()
    elif self.work_queue:
        event = self._work_tick()
    else:
        event = self._thinking_tick()
    self.mode = event["mode"]
    self._save()
    return event


def install_break_k2(loop):
    """Install the k2 break on a built 274 loop object (idempotent)."""
    cur = getattr(loop, "__dict__", {}).get("step", None)
    if not (isinstance(cur, types.MethodType)
            and cur.__func__ is _step_no_inbox_k2):
        loop.step = types.MethodType(_step_no_inbox_k2, loop)
    if NOTE_MUT1_K2 not in getattr(loop, "notes", []):
        loop.notes.append(NOTE_MUT1_K2)
    return loop


def build_agent274(cfg: dict | None = None):
    """274 build with the k2 break installed (same name/shape as 274)."""
    loop = B274.build_agent274(cfg)
    return install_break_k2(loop)


DEFAULT_CONFIG_MUT1_K2: dict = copy.deepcopy(B274.DEFAULT_CONFIG274)
DEFAULT_CONFIG_MUT1_K2["daemon"]["module"] = (
    "LoopMut1K2Daemon (scripts/claude_mut1_k2.py) over Loop274Daemon "
    "with the inbox branch dropped from step()")
DEFAULT_CONFIG_MUT1_K2["exp_mut1_k2"] = {
    "base": "loop274 (scripts/claude_loop274_agent.py, verified PASS)",
    "added": ["ONE break: step() has no inbox branch"],
    "untouched": ["reply-first turn", "sleep_due", "reader/ear stages"],
}


class LoopMut1K2Daemon(B274.Loop274Daemon):
    """274 daemon with the k2 break installed on the built loop."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        install_break_k2(self.loop)


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="mut-1 k2 (no inbox branch)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG_MUT1_K2)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG_MUT1_K2)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return LoopMut1K2Daemon(
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
