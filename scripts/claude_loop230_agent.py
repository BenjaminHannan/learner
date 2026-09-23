#!/usr/bin/env python3
"""Experiment 230 -- "YES." ONLY ON YES/NO QUESTIONS (Claude/Opus).

loop230 = loop219 + ONE change. 219 answers the D8 user-name route with
"Yes. Your name is X." when the notebook holds the user's name, but the
"Yes." also lands on wh-questions and requests ("What am I called?",
"Remind me what my name is?" -> "Yes. Your name is Juno."). Now the
"Yes. " prefix is kept only when the turn is a yes/no question, i.e. its
first word is an auxiliary verb (do/does/did/can/could/will/would/is/are/
am/was/were/have/has/had/shall/should/may/might/must, or a negative
contraction of one such as don't/isn't). Otherwise the reply is
"Your name is X." (the same sentence without "Yes. ").

New file only; scripts/fable_loop219_agent.py and
scripts/fable_fix219_selfname.py are wrapped read-only. The 219 turn runs
verbatim; only a reply line that starts with the 219 grounded text
"Yes. Your name is " is touched, and only on non-yes/no turns. Reply-only,
never writes.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop230_agent.py --daemon --dir DIR \\
    --config artifacts/claude-yesprefix230-20260922/loop230-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_loop219_agent as L219  # noqa: E402 (wrapped, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

# The exact 219 grounded prefix (scripts/fable_fix219_selfname.py:112).
YES_NAME_PREFIX = "Yes. Your name is "
YES = "Yes. "

AUXILIARIES = frozenset("""
do does did can could will would is are am was were have has had shall
should may might must
don't doesn't didn't can't couldn't won't wouldn't isn't aren't wasn't
weren't haven't hasn't hadn't shouldn't mustn't
""".split())


def is_yes_no_question(text: str) -> bool:
    """True iff the turn's first word is an auxiliary verb (yes/no form)."""
    t = str(text).replace("\u2019", "'").strip().lower()
    m = re.match(r"[^a-z']*([a-z']+)", t)
    return bool(m) and m.group(1) in AUXILIARIES


class Loop230AgentLoop(L219.Loop219AgentLoop):
    """Loop219AgentLoop; the 219 'Yes. ' prefix only on yes/no questions."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        said = L219.Loop219AgentLoop.turn(self, text)
        if is_yes_no_question(text):
            return said
        if not any(line.startswith(YES_NAME_PREFIX) for line in said):
            return said
        out = [line[len(YES):] if line.startswith(YES_NAME_PREFIX) else line
               for line in said]
        lr = getattr(self, "last_routed", None)
        if lr is not None and str(lr.get("answer", "")).startswith(
                YES_NAME_PREFIX):
            lr["answer"] = lr["answer"][len(YES):]
        if self.self_turn_log:
            rep = str(self.self_turn_log[-1].get("reply", ""))
            if rep.startswith(YES_NAME_PREFIX):
                self.self_turn_log[-1]["reply"] = rep[len(YES):]
        return out


DEFAULT_CONFIG230: dict = copy.deepcopy(L219.DEFAULT_CONFIG219)
DEFAULT_CONFIG230["ears"]["stand_in"] = (
    "Loop230AgentLoop (loop219 + 'Yes.' only on yes/no questions)")
DEFAULT_CONFIG230["daemon"]["module"] = "Loop230Daemon (this file)"
DEFAULT_CONFIG230["self"] = dict(L219.DEFAULT_CONFIG219.get("self", {}))
DEFAULT_CONFIG230["self"]["rule230"] = (
    "219 'Yes. Your name is X.' keeps 'Yes. ' only when the turn starts "
    "with an auxiliary verb; else 'Your name is X.'; never writes")


def build_agent230(cfg: dict | None = None) -> Loop230AgentLoop:
    """build_agent219 (read-only) with the loop's class set to 230.

    Loop230AgentLoop adds no state and no __init__; only turn() differs.
    """
    cfg = dict(DEFAULT_CONFIG230, **(cfg or {}))
    loop = L219.build_agent219(cfg)
    loop.__class__ = Loop230AgentLoop
    loop.notes.append("loop230: loop219 + 'Yes.' prefix only on yes/no "
                      "questions")
    return loop


class Loop230Daemon(L219.Loop219Daemon):
    """Loop219Daemon shape with the 230 agent inside."""

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
        self.loop = build_agent230(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon230(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop230Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 230 yes-prefix agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG230)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG230)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon230(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent230(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
