#!/usr/bin/env python3
"""Experiment 227b -- THE ASSISTANT IS NAMED PREMONITION (Claude/Opus).

loop227b = loop227 + ONE change: the identity sheet's NAME answer
"I don't have a name yet." becomes "My name is Premonition." (name decided
by Ben, its builder). The NAME line is the only sheet line that says the
assistant has no name (MAKER/WHAT/LEARN/AGE/HOME never mention a name), so
it is the only line replaced.

New file only; scripts/fable_loop227_agent.py and
scripts/fable_identity227.py are wrapped read-only (never edited). The
sheet dict in fable_identity227 is NOT mutated (other agents in the same
process keep the 227 text); instead Loop227bAgentLoop.turn() runs the
227 turn verbatim and, only when that turn was served by the identity
sheet with intent NAME (last_routed intent "IDENTITY-NAME"), swaps the
reply text. Same gate, same templates, same routing, same 0 writes.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop227b_agent.py --daemon --dir DIR \\
    --config artifacts/claude-name227b-20260922/loop227b-config.json
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

import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_identity227 as F227  # noqa: E402 (read-only)
import fable_loop227_agent as L227  # noqa: E402 (wrapped, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

# THE ONE CHANGE (text only).
NAME_227B = "My name is Premonition."
OLD_NAME_227 = F227.SHEET["NAME"]


def sheet227b() -> dict:
    """The 227b identity sheet: 227's sheet with the NAME line replaced."""
    out = dict(F227.SHEET)
    out["NAME"] = NAME_227B
    return out


class Loop227bAgentLoop(L227.Loop227AgentLoop):
    """Loop227AgentLoop; identity-NAME replies say the assistant's name."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        said = L227.Loop227AgentLoop.turn(self, text)
        lr = getattr(self, "last_routed", None)
        if lr is not None and lr.get("intent") == "IDENTITY-NAME":
            lr["answer"] = NAME_227B
            if self.self_turn_log:
                self.self_turn_log[-1]["reply"] = NAME_227B
            return [NAME_227B]
        return said


DEFAULT_CONFIG227B: dict = copy.deepcopy(L227.DEFAULT_CONFIG227)
DEFAULT_CONFIG227B["ears"]["stand_in"] = (
    "Loop227bAgentLoop (loop227 + assistant name Premonition)")
DEFAULT_CONFIG227B["daemon"]["module"] = "Loop227bDaemon (this file)"
DEFAULT_CONFIG227B["self"] = dict(L227.DEFAULT_CONFIG227.get("self", {}))
DEFAULT_CONFIG227B["self"]["rule227b"] = (
    "identity-sheet NAME answer is 'My name is Premonition.' (was "
    "\"I don't have a name yet.\"); everything else byte-identical to loop227")


def build_agent227b(cfg: dict | None = None) -> Loop227bAgentLoop:
    """build_agent227 (read-only) with the loop's class set to 227b.

    Loop227bAgentLoop adds no state and no __init__; only turn() differs,
    so re-classing the freshly built 227 loop is equivalent to building it
    as 227b.
    """
    cfg = dict(DEFAULT_CONFIG227B, **(cfg or {}))
    loop = L227.build_agent227(cfg)
    loop.__class__ = Loop227bAgentLoop
    loop.notes.append("loop227b: loop227 + identity NAME answer "
                      "'My name is Premonition.'")
    return loop


class Loop227bDaemon(L227.Loop227Daemon):
    """Loop227Daemon shape with the 227b agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent227b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon227b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop227bDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 227b Premonition agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG227B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG227B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon227b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent227b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
