#!/usr/bin/env python3
"""Experiment 189 -- SAY-AGAIN: verbatim repeat requests on loop138g.

ONE CHANGE on loop138g (`scripts/fable_loop138g_agent.py`,
`artifacts/fable-agent138g-20260922/`,
`design/v3/30-modes/138g-merge-layer-a-muse.md`): repeat requests.

Director probe 09:40 on loop138g: after "Kim's boss is Lee." ->
"Saved: Kim's boss is Lee.", the turn "Say it again." ->
"it again. (I'm treating that as pretend, so I won't save it.)"
(the pretend-Say rule swallowed a repeat request).

THE ONE CHANGE (new file, no existing file edited): an outermost
repeat-request stage, checked BEFORE the Say-pretend rule (i.e. before
delegating to the unchanged loop138g turn path):

  closed list (whole-turn, case-insensitive, trailing .?! stripped):
    say it again | say that again | repeat that | can you repeat that |
    what did you say | come again | pardon | sorry
  -> reply with the agent's previous reply text VERBATIM (the exact
     string this agent returned on the previous NON-REPEAT turn);
     if there is no previous reply, one fixed line:
       "I haven't said anything yet."
     Never writes (no notebook event, no fact, no correction, no
     self-route). Never re-runs the previous turn (a repeated "Saved:"
     reply is an echo: it must not write twice).

"Say Kim's boss is Lee." and any other "Say X" stays pretend exactly
as loop138g (Ben's ruling): only the 8 whole-turn repeat shapes above
match, so "Say hello." / "Say it in French." / "Say that Lee is kind."
still take the 137d say-echo path, and "Repeat after me: ...",
"Again, Kim's ..." never match (exact whole-turn match only).

"Previous reply" = the verbatim reply string of the latest non-repeat
turn in this session (repeat turns do not overwrite it, so consecutive
repeats echo the same text). In-memory only; nothing is persisted.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop189_agent.py --daemon --dir DIR \\
    --config artifacts/fable-sayagain189-20260922/loop189-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138g_agent as L138G  # noqa: E402 (wrapped base, read-only)

# THE ONE CHANGE: closed repeat-request list (whole-turn match only).
REPEAT189 = frozenset([
    "say it again",
    "say that again",
    "repeat that",
    "can you repeat that",
    "what did you say",
    "come again",
    "pardon",
    "sorry",
])

# The one fixed line when there is no previous reply.
NO_PREV189 = "I haven't said anything yet."


def norm189(turn: str) -> str:
    """Lowercase, collapse whitespace, strip trailing sentence punctuation."""
    s = str(turn).replace("\u2019", "'").replace("\u2018", "'")
    s = " ".join(s.split()).lower().strip()
    s = s.rstrip(" \t.,;:!?\"'()[]{}")
    return " ".join(s.split()).strip()


def is_repeat189(turn: str) -> bool:
    """True iff the whole turn is one of the 8 closed repeat requests."""
    return norm189(turn) in REPEAT189


class Loop189AgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop + outermost verbatim repeat-request stage.

    turn() checks is_repeat189 FIRST (before the 137d Say-pretend rule
    inside the unchanged 138g path). Repeats echo _prev189 verbatim
    (or NO_PREV189), write nothing, re-run nothing, and never overwrite
    _prev189. All other turns delegate to super().turn() and then store
    the verbatim reply as the new _prev189.
    """

    def turn(self, text: str) -> list[str]:
        prev = getattr(self, "_prev189", None)
        if is_repeat189(text):
            echo = prev if prev is not None else NO_PREV189
            try:
                n = len(self.self_turn_log) + 1
                self.self_turn_log.append({
                    "n": n, "ben": text, "reply": echo, "records": [],
                    "statuses": [],
                    "stage": getattr(
                        getattr(self, "ears", None),
                        "last_stage", ""),
                    "score": getattr(
                        getattr(self, "ears", None), "last_score", 0.0),
                    "wrote": False, "via": "repeat189",
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", ""),
                })
                self.self_mode_log.append({
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", "")})
            except Exception:
                pass
            return [echo]
        said = super().turn(text)
        reply = " ".join(said) if said else "(nothing to say)"
        self._prev189 = reply
        return said


DEFAULT_CONFIG189: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG189["ears"]["stand_in"] = (
    "Loop189 (loop138g stack + outermost verbatim repeat-request stage: "
    "8 closed whole-turn shapes echo the previous reply, fixed line "
    "when none; never writes, never re-runs)")
DEFAULT_CONFIG189["daemon"]["module"] = "Loop189Daemon (this file)"


def build_agent189(cfg: dict | None = None) -> Loop189AgentLoop:
    """Build the loop138g agent shape with the 189 repeat stage on top."""
    cfg = dict(DEFAULT_CONFIG189, **(cfg or {}))
    loop = L138G.build_agent138g(cfg)
    loop.__class__ = Loop189AgentLoop
    loop._prev189 = None
    loop.notes.append("loop189: outermost verbatim repeat-request stage "
                      "(8 closed shapes; fixed no-prev line; never writes, "
                      "never re-runs; Say-X stays pretend per ruling)")
    return loop


class Loop189Daemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 189 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = 30.0) -> None:
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        import fable_daemon141_settle as D141  # noqa: E402 (read-only)
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
        self.loop = build_agent189(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon189(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop189Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 189 say-again agent")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG189 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG189)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG189)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon189(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent189(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
