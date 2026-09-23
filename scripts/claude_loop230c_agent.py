#!/usr/bin/env python3
"""Experiment 230c -- NAME CHECK FAILS CLOSED (Claude/Opus).

loop230c = loop230b + ONE change (+ the required 228 guard).
Diagnosis (230b-r FAIL, r230b-038): "Is it Wystane Borrick, my name?" got
"Yes. Your name is Wystane Morrick." because 230b's name finder could not
pull the asked name out, and the inherited 219/230 "Yes." was kept.

THE ONE CHANGE: on a reply line that starts "Yes. Your name is " (the
user-name yes/no route), "Yes." / "No." is only given when the asked name
was actually extracted and compared (230b's asked_name + same_name,
unchanged). If the turn mentions something that may be a name -- any word
outside a closed list of common question words -- but no name could be
extracted, the line fails closed to the plain "Your name is <stored>."
with no Yes/No prefix. Turns made only of common words ("Do you remember
my name?", "Can you say my name?") name no name and keep 230b's reply.
The pattern list is NOT widened; routing is NOT widened; only a
"Yes. Your name is " line is ever touched, so relation yes/no questions
stay byte-identical. Reply-only; never writes.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop230c_agent.py --daemon --dir DIR \\
    --config artifacts/claude-namecheck230c-20260922/loop230c-config.json
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
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import claude_loop230_agent as L230  # noqa: E402 (read-only)
import claude_loop230b_agent as L230B  # noqa: E402 (wrapped, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

YES_NAME_PREFIX = L230B.YES_NAME_PREFIX  # "Yes. Your name is "
YES = "Yes. "

# Closed list of common words a name-question may use without naming a
# name. Any other word may be a name -> fail closed when none is extracted.
COMMON_WORDS = frozenset(L230B.NOT_NAMES | L230.AUXILIARIES | frozenset("""
name names named called call calls nickname surname firstname
remember remembered recall know knew known tell told say said saying
mention mentioned give gave given got get keep kept save saved store
stored write wrote written note notes notebook memory record records
recorded list listed file filed log logged spell spelled spelling
pronounce said hey hi hello okay ok so well um uh please thanks thank
yes no yeah yep nope i me my mine myself you your yours yourself we us
am are is was were be been being do does did done can could will would
shall should may might must have has had having ever never already again
now yet still today earlier before last time first full real right
correct wrong sure certain think thought guess believe mean and or but
if not also just even only who what which whom whose how why when where
it its it's that this there these those here in on at of to for with
from about as by into up down out over any some all
""".split()))

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def may_name_something(text: str) -> bool:
    """True iff the turn holds a word outside COMMON_WORDS (a possible name)."""
    t = str(text).replace("’", "'")
    for w in _WORD.findall(t):
        lw = w.lower()
        if lw.endswith("'s"):
            lw = lw[:-2]
        lw = lw.strip("'-")
        if lw and lw not in COMMON_WORDS:
            return True
    return False


class Loop230cAgentLoop(L230B.Loop230bAgentLoop):
    """Loop230bAgentLoop; unextracted name checks fail closed (no Yes/No)."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        said = L230B.Loop230bAgentLoop.turn(self, text)
        if not any(line.startswith(YES_NAME_PREFIX) for line in said):
            return said
        if L230B.asked_name(text) is not None:
            return said  # extracted and compared by 230b (unchanged)
        if not may_name_something(text):
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


DEFAULT_CONFIG230C: dict = copy.deepcopy(L230B.DEFAULT_CONFIG230B)
DEFAULT_CONFIG230C["ears"]["stand_in"] = (
    "Loop230cAgentLoop (loop230b + unextracted name checks fail closed)")
DEFAULT_CONFIG230C["daemon"]["module"] = (
    "Loop230cDaemon (scripts/claude_loop230c_agent.py)")
DEFAULT_CONFIG230C["self"] = dict(L230B.DEFAULT_CONFIG230B.get("self", {}))
DEFAULT_CONFIG230C["self"]["rule230c"] = (
    "on a 'Yes. Your name is X.' line: Yes/No only when the asked name was "
    "extracted and compared; if the turn holds a possible name that could "
    "not be extracted -> 'Your name is X.'; never writes")


def build_agent230c(cfg: dict | None = None) -> Loop230cAgentLoop:
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG230C, **(cfg or {}))
    loop = L230B.build_agent230b(cfg)
    loop.__class__ = Loop230cAgentLoop
    loop.notes.append("loop230c: loop230b + unextracted name checks fail "
                      "closed")
    return loop


class Loop230cDaemon(SrcGuardMixin228, L230.Loop230Daemon):
    """Loop230Daemon shape (as 230b) with the 230c agent inside; 228 guard first."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        install_srcguard228()
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
        self.loop = build_agent230c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon230c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop230cDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 230c fail-closed agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG230C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG230C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon230c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent230c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
