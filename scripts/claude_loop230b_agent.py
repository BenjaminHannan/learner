#!/usr/bin/env python3
"""Experiment 230b -- A NAME CHECK MUST COMPARE THE NAME (Claude/Opus).

loop230b = loop230 + ONE change (+ the required 228 _src_of guard).
Bug (independent verifier, artifacts/claude-verify-20260922/227bc230/):
after "My name is Ottilie.", "Is my name Quenby?" gets "Yes. Your name is
Ottilie." -- a false yes inherited from 219, whose D8 grounding answers
"Yes. Your name is <stored>." without looking at the name that was asked.

THE ONE CHANGE: only when the 230 turn already produced a reply line that
starts "Yes. Your name is " (i.e. the turn reached the user-name answer
path AND is a yes/no question), and the turn is a name check that names a
specific name ("Is my name X?", "Is X my name?", "Am I called X?",
"Did I say my name was X?", ...), the asked name X is compared with the
stored user name, case-insensitively on the whole name:
  same name      -> reply unchanged ("Yes. Your name is <stored>.")
  different name -> "No. Your name is <stored>."
Untaught turns never reach a "Yes. Your name is" line, so they keep the
untaught reply. Which turns reach the name path is NOT widened: nothing
outside a "Yes. Your name is " line is touched. Reply-only; never writes.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop230b_agent.py --daemon --dir DIR \\
    --config artifacts/claude-namecheck230b-20260922/loop230b-config.json
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
import fable_fix219_selfname as F219  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import claude_loop230_agent as L230  # noqa: E402 (wrapped, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

YES_NAME_PREFIX = L230.YES_NAME_PREFIX  # "Yes. Your name is "
NO_NAME_FMT = "No. Your name is %s."

# Words that can follow "Is my name ..." / "Am I ..." but are not names.
NOT_NAMES = frozenset("""
a an the in on at of for to into with by from about as my your our their his
her its it this that these those there here what which who whom whose how
why when where saved stored written kept noted known remembered recorded
listed logged filed down up still really actually just real right correct
wrong ok okay fine good bad nice cool weird strange odd unusual common rare
long short hard easy simple pretty ugly spelled spelt same different new old
safe important familiar something anything nothing everything someone anyone
one also too even not so very true false set there's you me i we they
""".split())

_NAME_WORD = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")

_PATTERNS = [re.compile(p, re.I) for p in (
    r"^is my (?:first |real |actual |full )?name (?:really |actually |still "
    r"|just )?(?P<n>.+)$",
    r"^is (?P<n>.+?) (?:really |actually |still )?my (?:first |real |actual "
    r"|full )?name$",
    r"^am i (?:called |named |really |actually )?(?P<n>.+)$",
    r"^(?:did|have|had) i (?:say|said|tell you|told you|mention|mentioned) "
    r"(?:that )?my name (?:is|was) (?P<n>.+)$",
    r"^(?:do|did) you (?:know|remember|think|have|save|store|write down) "
    r"(?:that )?my name (?:is|was|as) (?P<n>.+)$",
    r"^(?:do|did) you (?:have|save|store|write) me (?:down )?as (?P<n>.+)$",
)]


def asked_name(text: str) -> str | None:
    """The specific name a yes/no name check asks about, or None."""
    t = str(text).replace("’", "'").strip()
    t = re.sub(r"[\s?.!]+$", "", t)
    t = re.sub(r",?\s+(?:right|then|correct|yes|no)$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    has_caps = t[1:] != t[1:].lower()
    for pat in _PATTERNS:
        m = pat.match(t)
        if not m:
            continue
        cand = m.group("n").strip(" ,;:'\"")
        words = cand.split(" ")
        if not 1 <= len(words) <= 3:
            return None
        if any(not _NAME_WORD.match(w) for w in words):
            return None
        if any(w.lower() in NOT_NAMES or w.lower() == "or" for w in words):
            return None
        if has_caps and any(not w[0].isupper() for w in words):
            return None
        return cand
    return None


def same_name(asked: str, stored: str) -> bool:
    """Case-insensitive whole-name comparison (spaces collapsed)."""
    norm = lambda s: " ".join(str(s).split()).casefold()  # noqa: E731
    return norm(asked) == norm(stored)


class Loop230bAgentLoop(L230.Loop230AgentLoop):
    """Loop230AgentLoop; a named yes/no name check compares the name."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        said = L230.Loop230AgentLoop.turn(self, text)
        if not any(line.startswith(YES_NAME_PREFIX) for line in said):
            return said
        asked = asked_name(text)
        if asked is None:
            return said
        stored = F219.stored_user_name(self.nb)
        if not stored or same_name(asked, stored):
            return said
        new = NO_NAME_FMT % stored
        out = [new if line.startswith(YES_NAME_PREFIX) else line
               for line in said]
        lr = getattr(self, "last_routed", None)
        if lr is not None and str(lr.get("answer", "")).startswith(
                YES_NAME_PREFIX):
            lr["answer"] = new
        if self.self_turn_log:
            rep = str(self.self_turn_log[-1].get("reply", ""))
            if rep.startswith(YES_NAME_PREFIX):
                self.self_turn_log[-1]["reply"] = new
        return out


DEFAULT_CONFIG230B: dict = copy.deepcopy(L230.DEFAULT_CONFIG230)
DEFAULT_CONFIG230B["ears"]["stand_in"] = (
    "Loop230bAgentLoop (loop230 + named name checks compare the name)")
DEFAULT_CONFIG230B["daemon"]["module"] = (
    "Loop230bDaemon (scripts/claude_loop230b_agent.py)")
DEFAULT_CONFIG230B["self"] = dict(L230.DEFAULT_CONFIG230.get("self", {}))
DEFAULT_CONFIG230B["self"]["rule230b"] = (
    "a 'Yes. Your name is X.' reply to a name check naming a specific name "
    "compares it with the stored name (case-insensitive, whole name); "
    "different -> 'No. Your name is X.'; never writes")
DEFAULT_CONFIG230B["srcguard228"] = "installed (SrcGuardMixin228 first)"


def build_agent230b(cfg: dict | None = None) -> Loop230bAgentLoop:
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG230B, **(cfg or {}))
    loop = L230.build_agent230(cfg)
    loop.__class__ = Loop230bAgentLoop
    loop.notes.append("loop230b: loop230 + named name checks compare the "
                      "asked name with the stored one")
    return loop


class Loop230bDaemon(SrcGuardMixin228, L230.Loop230Daemon):
    """Loop230Daemon shape with the 230b agent inside (228 guard first)."""

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
        self.loop = build_agent230b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon230b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop230bDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 230b name-check agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG230B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG230B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon230b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent230b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
