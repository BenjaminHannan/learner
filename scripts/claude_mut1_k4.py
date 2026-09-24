#!/usr/bin/env python3
"""EXP mut-1 k4: 274 wrapped with ONE deliberate break (CPU only).

Break k4: the listening tick is REPLACED by the thinking tick -- when the
inbox is non-empty, step() runs _thinking_tick() instead of
_listening_tick(). Step order and the 274 reply-first turn wrapper are
kept; sleep_due is untouched. A waiting message is therefore never heard.
Expected: M1 fails (inbox never drains), M2 fails (inbox shadows sleep
forever), panel replies change wholesale.

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

NOTE_MUT1_K4 = ("loopmut1-k4 (scripts/claude_mut1_k4.py: 274 with the "
                "listening tick replaced by the thinking tick; waiting "
                "messages never heard; step order and reply-first turn "
                "kept)")


def _step_think_for_listen_k4(self):
    """274 step with listening replaced by thinking (ONE break)."""
    self.tick += 1
    if self.inbox:
        event = self._thinking_tick()
    elif self.sleep_due():
        event = self._sleep_tick()
    elif self.work_queue:
        event = self._work_tick()
    else:
        event = self._thinking_tick()
    self.mode = event["mode"]
    self._save()
    return event


def install_break_k4(loop):
    """Install the k4 break on a built 274 loop object (idempotent)."""
    cur = getattr(loop, "__dict__", {}).get("step", None)
    if not (isinstance(cur, types.MethodType)
            and cur.__func__ is _step_think_for_listen_k4):
        loop.step = types.MethodType(_step_think_for_listen_k4, loop)
    if NOTE_MUT1_K4 not in getattr(loop, "notes", []):
        loop.notes.append(NOTE_MUT1_K4)
    return loop


def build_agent274(cfg: dict | None = None):
    """274 build with the k4 break installed (same name/shape as 274)."""
    loop = B274.build_agent274(cfg)
    return install_break_k4(loop)


DEFAULT_CONFIG_MUT1_K4: dict = copy.deepcopy(B274.DEFAULT_CONFIG274)
DEFAULT_CONFIG_MUT1_K4["daemon"]["module"] = (
    "LoopMut1K4Daemon (scripts/claude_mut1_k4.py) over Loop274Daemon "
    "with the listening tick replaced by the thinking tick")
DEFAULT_CONFIG_MUT1_K4["exp_mut1_k4"] = {
    "base": "loop274 (scripts/claude_loop274_agent.py, verified PASS)",
    "added": ["ONE break: inbox branch runs _thinking_tick"],
    "untouched": ["step() branch order", "reply-first turn", "sleep_due",
                  "reader/ear stages"],
}


class LoopMut1K4Daemon(B274.Loop274Daemon):
    """274 daemon with the k4 break installed on the built loop."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        install_break_k4(self.loop)


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="mut-1 k4 (think for listen)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG_MUT1_K4)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG_MUT1_K4)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return LoopMut1K4Daemon(
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
