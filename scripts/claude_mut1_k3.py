#!/usr/bin/env python3
"""EXP mut-1 k3: 274 wrapped with ONE deliberate break (CPU only).

Break k3: sleep is NEVER due (sleep_due always False). Step order and the
274 reply-first turn wrapper are kept. Expected: M1 fails (its sleep-due
precondition never holds), M2 fails (no SLEEP tick ever runs), the sleep
smoke shows zero sleeps, while the 90-turn panel (which never lets sleep
go due anyway) stays identical -- a panel blind spot, reported not fixed.

Additive only: this file is new. scripts/claude_loop274_agent.py is
imported read-only and never edited; the break is installed as an instance
attribute shadowing sleep_due on the built loop object.
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

NOTE_MUT1_K3 = ("loopmut1-k3 (scripts/claude_mut1_k3.py: 274 with sleep_due "
                "always False; sleep never runs; step order and reply-first "
                "turn kept)")


def _never_due_k3(self) -> bool:
    """sleep_due replacement: sleep is never due (ONE break)."""
    return False


def install_break_k3(loop):
    """Install the k3 break on a built 274 loop object (idempotent)."""
    cur = getattr(loop, "__dict__", {}).get("sleep_due", None)
    if not (isinstance(cur, types.MethodType)
            and cur.__func__ is _never_due_k3):
        loop.sleep_due = types.MethodType(_never_due_k3, loop)
    if NOTE_MUT1_K3 not in getattr(loop, "notes", []):
        loop.notes.append(NOTE_MUT1_K3)
    return loop


def build_agent274(cfg: dict | None = None):
    """274 build with the k3 break installed (same name/shape as 274)."""
    loop = B274.build_agent274(cfg)
    return install_break_k3(loop)


DEFAULT_CONFIG_MUT1_K3: dict = copy.deepcopy(B274.DEFAULT_CONFIG274)
DEFAULT_CONFIG_MUT1_K3["daemon"]["module"] = (
    "LoopMut1K3Daemon (scripts/claude_mut1_k3.py) over Loop274Daemon "
    "with sleep_due always False")
DEFAULT_CONFIG_MUT1_K3["exp_mut1_k3"] = {
    "base": "loop274 (scripts/claude_loop274_agent.py, verified PASS)",
    "added": ["ONE break: sleep_due always False"],
    "untouched": ["step() branch order", "reply-first turn",
                  "reader/ear stages"],
}


class LoopMut1K3Daemon(B274.Loop274Daemon):
    """274 daemon with the k3 break installed on the built loop."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        install_break_k3(self.loop)


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="mut-1 k3 (sleep never due)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG_MUT1_K3)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG_MUT1_K3)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return LoopMut1K3Daemon(
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
