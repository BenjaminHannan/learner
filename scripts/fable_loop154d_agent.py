#!/usr/bin/env python3
"""Experiment 154d -- loop154d = loop138f + grounded yes/no (ONE CHANGE).

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix154d_yesno.py (YesNo154dMixin: a yes/no stage that runs
ONLY when the forward path did not understand -- "Is V X's R?" /
"Is X's R V?" with one taught subject X and one stored relation R looked
up in the NOTEBOOK directly, never the wh-run: Yes on match, No only on
single-valued last hops per SINGLE_VALUED_154 imported read-only from
scripts/fable_fix154_yesno.py, "Not that I know of. I have W as X's R."
on multi-valued relations, the base reply unchanged otherwise; never a
write); this file stacks it onto loop138f (scripts/fable_loop138f_agent.py,
read-only) in the style of scripts/fable_loop154_agent.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop154d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-yesno154d-20260922/loop154d-config.json
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

import fable_fix154d_yesno as Y154d  # noqa: E402 (this experiment)
import fable_loop138f_agent as L138f  # noqa: E402 (wrapped base, read-only)


class Loop154dEars(L138f.Loop138fEars):
    """Loop138fEars unchanged (the yes/no stage is loop-level only)."""

    name = "loop154d-yesno-ears"


class Loop154dAgentLoop(Y154d.YesNo154dMixin, L138f.Loop138fAgentLoop):
    """Loop138fAgentLoop + the exp-154d grounded yes/no stage on miss."""


DEFAULT_CONFIG154D: dict = copy.deepcopy(L138f.DEFAULT_CONFIG138F)
DEFAULT_CONFIG154D["ears"]["stand_in"] = (
    "Loop154dEars (loop138f ears unchanged) over the loop138f chain; "
    "yes/no is a loop-level stage (YesNo154dMixin over Loop138fAgentLoop): "
    "an 'Is V X's R?' / 'Is X's R V?' turn the forward path did not "
    "understand is answered from the notebook directly (resolve + "
    "current, never the wh-run) -- Yes on match, No only on "
    "single-valued relations, 'Not that I know of. I have W as X's R.' "
    "on multi-valued, base reply unchanged otherwise; never a write")
DEFAULT_CONFIG154D["daemon"]["module"] = "Loop154dDaemon (this file)"


def build_agent154d(cfg: dict | None = None) -> Loop154dAgentLoop:
    """Build the loop138f agent shape with the yes/no mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG154D, **(cfg or {}))
    loop = L138f.build_agent138f(cfg)
    loop.ears.__class__ = Loop154dEars
    loop.ears.name = Loop154dEars.name
    loop.__class__ = Loop154dAgentLoop
    return loop


class Loop154dDaemon(L138f.Loop138fDaemon):
    """Loop138fDaemon shape with the loop154d agent inside (mailbox same).

    __init__ mirrors Loop138fDaemon.__init__ line for line except the
    build call. Name ends in Daemon / starts with Loop so the marks123
    loader picks this class.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float | None = None) -> None:
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        import fable_daemon141_settle as D141  # noqa: E402 (read-only)
        if grace_s is None:
            grace_s = D141.SETTLE_GRACE_S
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent154d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon154d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop154dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 154d grounded yes/no loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138f)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG154D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG154D)
        from fable_loop90_agent import THINKER_MODULE as _THINK
        out["thinker"]["module"] = _THINK
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG154D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon154d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent154d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
