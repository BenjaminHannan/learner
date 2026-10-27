#!/usr/bin/env python3
"""Experiment 189b -- widened repeat-request matcher on loop189.

ONE CHANGE on loop189 (`scripts/fable_loop189_agent.py`,
`artifacts/fable-sayagain189-20260922/`,
`design/v3/30-modes/189-sayagain-muse.md`): replace the 8-shape closed
repeat list with a small grammar covering politeness wrappers and
variants.

Director probe 10:19 on loop189 (after "Ines's boss is Tom."): "Could
you say that again?" and "What?" -> generic don't-know; "Say that one
more time." -> "one more time. (I'm treating that as pretend...)";
"Say again please." -> "again please. (I'm treating that as
pretend...)". The listed forms ("Repeat that.", "Say it again.") work.

THE ONE CHANGE (new file, no existing file edited): an outermost
repeat-request stage, checked BEFORE the Say-pretend rule (i.e. before
delegating to the unchanged loop189 turn path, which itself wraps the
frozen loop138g stack):

  whole-turn, case-insensitive, trailing .?! stripped, commas dropped:
  (a) bare shapes: again | what | huh | sorry what | come again |
      pardon | pardon me | sorry | what did you say |
      what did you just say | say again
  (b) grammar: optional leading/trailing "please",
      optional (could you | can you | would you | will you),
      verb (say | repeat),
      optional object (what you just said | what you said | it | that),
      optional marker (again | one more time | once more),
      with at least one of (politeness, object, marker, please)
      present -- bare "say"/"repeat" alone never match.
  -> reply with the agent's previous reply text VERBATIM (the exact
     string this agent returned on the previous NON-REPEAT turn);
     if there is no previous reply, one fixed line:
       "I haven't said anything yet."  (same string as loop189)
     Never writes (no notebook event, no fact, no correction, no
     self-route). Never re-runs the previous turn (a repeated "Saved:"
     reply is an echo: it must not write twice).

Rule: a "Say ..." turn is a repeat request ONLY when everything after
"say" is from the repeat vocabulary (it, that, what you said, again,
one more time, once more, please, plus the politeness wrappers above);
any other content keeps loop189's pretend behaviour (Ben's ruling:
"Say X" = pretend). So "Say hello.", "Say Kim's boss is Lee.",
"Say it in French.", "Say something nice.", "Say that Lee is kind."
stay pretend; "What is Kim's boss?", "What about Lee?",
"Again, Kim's boss is Lee.", "Repeat after me: ..." never match
(exact whole-turn match only).

"Previous reply" = the verbatim reply string of the latest non-repeat
turn in this session (repeat turns do not overwrite it, so consecutive
repeats echo the same text). In-memory only; nothing is persisted.
The 8 loop189 shapes are a strict subset of the new grammar, so every
loop189 repeat still echoes identically.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop189b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-sayagain189b-20260922/loop189b-config.json
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

import fable_loop138g_agent as L138G  # noqa: E402 (wrapped base, read-only)
import fable_loop189_agent as L189  # noqa: E402 (wrapped parent, read-only)

# THE ONE CHANGE: widened repeat-request grammar (whole-turn match only).
# The 8 loop189 closed shapes are a strict subset of what matches here.
BARE189B = frozenset([
    "again",
    "what",
    "huh",
    "sorry what",
    "come again",
    "pardon",
    "pardon me",
    "sorry",
    "what did you say",
    "what did you just say",
    "say again",
])

POLITE189B = ("could you", "can you", "would you", "will you")
OBJECTS189B = ("what you just said", "what you said", "it", "that")
MARKERS189B = ("one more time", "once more", "again")
VERBS189B = ("say", "repeat")

# The one fixed line when there is no previous reply (same as loop189).
NO_PREV189B = L189.NO_PREV189


def norm189b(turn: str) -> str:
    """Lowercase, drop commas, collapse whitespace, strip trailing punct."""
    s = str(turn).replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace(",", " ")
    s = " ".join(s.split()).lower().strip()
    s = s.rstrip(" \t.,;:!?\"'()[]{}")
    return " ".join(s.split()).strip()


def _strip_please(core: str) -> tuple[str, bool]:
    """Strip at most one leading and (repeatedly) trailing 'please'."""
    had = False
    prev = None
    while prev != core:
        prev = core
        if core.startswith("please "):
            core = core[len("please "):].strip()
            had = True
        if core.endswith(" please"):
            core = core[: -len(" please")].strip()
            had = True
    return core, had


def _consume_phrase(s: str, phrases: tuple[str, ...]) -> str | None:
    """Consume the longest matching phrase at the start of s (else None)."""
    for p in sorted(phrases, key=len, reverse=True):
        if s == p:
            return ""
        if s.startswith(p + " "):
            return s[len(p) + 1:].strip()
    return None


def is_repeat189b(turn: str) -> bool:
    """True iff the whole turn is a repeat request under the 189b grammar."""
    n = norm189b(turn)
    if not n:
        return False
    core, had_please = _strip_please(n)
    if not core:
        return False
    if core in BARE189B:
        return True
    rest = core
    polite = False
    got = _consume_phrase(rest, POLITE189B)
    if got is not None:
        polite = True
        rest = got
    got = _consume_phrase(rest, VERBS189B)
    if got is None:
        return False
    rest = got
    obj = False
    got = _consume_phrase(rest, OBJECTS189B)
    if got is not None:
        obj = True
        rest = got
    mark = False
    got = _consume_phrase(rest, MARKERS189B)
    if got is not None:
        mark = True
        rest = got
    if rest != "":
        return False
    # Bare "say"/"repeat" (verb only, nothing else) is never a repeat.
    return bool(polite or obj or mark or had_please)


class Loop189bAgentLoop(L189.Loop189AgentLoop):
    """Loop189AgentLoop + widened 189b repeat-request stage.

    turn() checks is_repeat189b FIRST (before the 189 closed list inside
    the unchanged loop189 path, hence before the 137d Say-pretend rule).
    Repeats echo _prev189 verbatim (or NO_PREV189B), write nothing,
    re-run nothing, and never overwrite _prev189. All other turns
    delegate to super().turn() (loop189 behaviour exactly) and inherit
    its _prev189 bookkeeping.
    """

    def turn(self, text: str) -> list[str]:
        prev = getattr(self, "_prev189", None)
        if is_repeat189b(text):
            echo = prev if prev is not None else NO_PREV189B
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
                    "wrote": False, "via": "repeat189b",
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", ""),
                })
                self.self_mode_log.append({
                    "tick": getattr(self, "tick", 0),
                    "mode": getattr(self, "mode", "")})
            except Exception:
                pass
            return [echo]
        return super().turn(text)


DEFAULT_CONFIG189B: dict = copy.deepcopy(L189.DEFAULT_CONFIG189)
DEFAULT_CONFIG189B["ears"]["stand_in"] = (
    "Loop189b (loop189 stack + widened repeat-request grammar: bare "
    "shapes + politeness/object/marker grammar echo the previous reply, "
    "fixed line when none; never writes, never re-runs)")
DEFAULT_CONFIG189B["daemon"]["module"] = "Loop189bDaemon (this file)"


def build_agent189b(cfg: dict | None = None) -> Loop189bAgentLoop:
    """Build the loop189 agent shape with the 189b repeat stage on top."""
    cfg = dict(DEFAULT_CONFIG189B, **(cfg or {}))
    loop = L189.build_agent189(cfg)
    loop.__class__ = Loop189bAgentLoop
    loop.notes.append("loop189b: widened repeat-request grammar "
                      "(bare shapes + politeness/object/marker grammar; "
                      "fixed no-prev line; never writes, never re-runs; "
                      "Say-X stays pretend per ruling)")
    return loop


class Loop189bDaemon(L189.Loop189Daemon):
    """Loop189Daemon shape with the 189b agent inside."""

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
        self.loop = build_agent189b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon189b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop189bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 189b say-again agent")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop189)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG189B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG189B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG189B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon189b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent189b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
