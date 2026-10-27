#!/usr/bin/env python3
"""Experiment 234 -- ONE HONEST SMALL-TALK REPLY (Claude/Opus).

loop234 = loop138i + ONE change. A turn whose WHOLE content is a question
about how the assistant itself is doing ("How are you?", "how's it going",
"how have you been", "how r u", ...), optionally after a greeting ("Hi,",
"Hey there,", "Good morning!") and optionally addressed to "Premonition",
gets one fixed, honest reply:

    I'm here and ready to learn. Tell me something, or ask me about what
    you've told me.

If the turn also has a greeting, the reply starts with 138i's greeting
word "Hi! " (the same opener 138i's 156b greeting reply uses). The reply
claims no feelings (the CANNOT sheet says the assistant cannot feel).

On 138i such turns got a mode-status line ("Right now I am back in
LISTENING mode, waiting for your next turn.") from the self router, or a
decline. Everything else is untouched: the 138i turn runs verbatim first
(so every log/state update is 138i's), and only when the matcher below
fires AND that turn wrote nothing is the reply text swapped. Questions
about a person ("How is Kim?"), status/mode questions, a greeting followed
by a real question, greeting-only turns and every other "how" question
never match (the matcher is a closed whole-turn grammar, not keywords).
Reply-only: zero notebook writes by construction.

New file only; scripts/fable_loop138i_agent.py is wrapped read-only.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop234_agent.py --daemon --dir DIR \\
    --config artifacts/claude-smalltalk234-20260922/loop234-config.json
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
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

# THE ONE CHANGE (text).
FIXED_234 = ("I'm here and ready to learn. Tell me something, "
             "or ask me about what you've told me.")
GREET_PREFIX_234 = "Hi! "  # 138i's greeting opener (156b GREETING_REPLY)

# ------------------------------------------------------------ matcher
# Closed grammar over normalised tokens:
#   turn := [greeting] [address] [filler] core [tail]* ( [filler] core [tail]* )*
# with "premonition" (the assistant's name) allowed as an address anywhere
# between parts. Every token must be consumed, else no match.

GREET_SEQS = [
    ("good", "morning"), ("good", "afternoon"), ("good", "evening"),
    ("good", "day"), ("hi",), ("hey",), ("hello",), ("hiya",), ("heya",),
    ("howdy",), ("yo",), ("greetings",), ("morning",), ("afternoon",),
    ("evening",),
]
GREET_TAIL = {"there", "again", "hi", "hey", "hello"}
ADDRESS = {"premonition"}
FILLER = {"so", "and", "well", "oh", "um", "uh", "hmm"}

YOU = ("you", "u", "ya", "yah")
_CORES: list[tuple[str, ...]] = []


def _add(*seqs: tuple[str, ...]) -> None:
    for s in seqs:
        _CORES.append(tuple(s))


for _y in YOU:
    for _h in (("how", "are"), ("how", "r"), ("howre",), ("how", "re")):
        _add(_h + (_y,))
        for _v in (("doing",), ("feeling",), ("keeping",), ("getting", "on"),
                   ("holding", "up"), ("going",), ("today",)):
            _add(_h + (_y,) + _v)
    for _v in ("doing", "been", "feeling", "keeping"):
        _add(("how", _y, _v))
    _add(("how", "have", _y, "been"), ("howve", _y, "been"),
         ("how", "ve", _y, "been"), ("how", "do", _y, "do"),
         ("how", "do", _y, "feel"),
         ("how", "is", "it", "going", "for", _y),
         ("hows", "it", "going", "for", _y))
    for _ok in (("ok",), ("okay",), ("alright",), ("all", "right"),
                ("good",), ("well",), ("fine",)):
        for _lead in (("are", _y), (_y,), ("are", _y, "doing"),
                      (_y, "doing")):
            _add(_lead + _ok)
for _hs in (("hows",), ("how", "is"), ("how", "s")):
    _add(_hs + ("it", "going"), _hs + ("it", "goin"),
         _hs + ("things",), _hs + ("things", "going"),
         _hs + ("everything",), _hs + ("everything", "going"),
         _hs + ("life",), _hs + ("life", "treating", "you"),
         _hs + ("your", "day"), _hs + ("your", "day", "going"),
         _hs + ("your", "day", "been"))
_add(("how", "it", "going"), ("how", "are", "things"),
     ("how", "are", "things", "going"), ("how", "was", "your", "day"),
     ("how", "has", "your", "day", "been"), ("hru",))
_CORES.sort(key=len, reverse=True)

TAIL_SEQS = [
    ("this", "morning"), ("this", "afternoon"), ("this", "evening"),
    ("these", "days"), ("so", "far"), ("today",), ("tonight",),
    ("lately",), ("then",), ("now",), ("anyway",), ("doing",),
]
TAIL_SEQS.sort(key=len, reverse=True)


def normalize_234(text: str) -> list[str]:
    """Lower-case, fold curly quotes, drop apostrophes, collapse letter
    runs of 3+ ("youuu" -> "you", "hiii" -> "hi"), split on non-letters."""
    low = str(text).lower().replace("’", "'").replace("‘", "'")
    low = low.replace("'", "")
    low = re.sub(r"([a-z])\1{2,}", r"\1", low)
    low = re.sub(r"[^a-z]+", " ", low)
    return low.split()


def _match_at(toks: list[str], i: int, seqs) -> int:
    """Length of the first (longest) seq matching toks at i, else 0."""
    for s in seqs:
        n = len(s)
        if tuple(toks[i:i + n]) == s:
            return n
    return 0


def classify_234(text: str) -> dict | None:
    """{'greeting': bool} if the whole turn is (greeting +) wellbeing
    question(s) about the assistant, else None."""
    toks = normalize_234(text)
    if not toks:
        return None
    i, n, greeted, cores = 0, len(toks), False, 0
    # greeting block
    while i < n:
        k = _match_at(toks, i, GREET_SEQS)
        if k:
            greeted, i = True, i + k
            while i < n and toks[i] in GREET_TAIL:
                i += 1
            continue
        if toks[i] in ADDRESS:
            i += 1
            continue
        break
    # one or more cores
    while i < n:
        while i < n and (toks[i] in FILLER or toks[i] in ADDRESS):
            i += 1
        if i >= n:
            break
        k = _match_at(toks, i, _CORES)
        if not k:
            return None
        cores, i = cores + 1, i + k
        while i < n:
            k = _match_at(toks, i, TAIL_SEQS)
            if k:
                i += k
                continue
            if toks[i] in ADDRESS:
                i += 1
                continue
            break
    if cores == 0 or i != n:
        return None
    return {"greeting": greeted}


def reply_234(text: str) -> str | None:
    c = classify_234(text)
    if c is None:
        return None
    return (GREET_PREFIX_234 + FIXED_234) if c["greeting"] else FIXED_234


# ------------------------------------------------------------ loop
def _n_facts(loop) -> int:
    try:
        return len(loop.nb.facts)
    except Exception:  # pragma: no cover
        return -1


class Loop234Mixin:
    """Runs the 138i turn verbatim, then swaps the reply on a match."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        before = _n_facts(self)
        said = super().turn(text)  # type: ignore[misc]
        rep = reply_234(text)
        if rep is None or _n_facts(self) != before:
            return said
        lr = getattr(self, "last_routed", None)
        if isinstance(lr, dict):
            lr["answer"] = rep
            lr["smalltalk234"] = True
        log = getattr(self, "self_turn_log", None)
        if log and isinstance(log[-1], dict) and "reply" in log[-1]:
            log[-1]["reply"] = rep
        return [rep]


_CLASS_CACHE: dict = {}


def _class234(base_cls):
    if base_cls not in _CLASS_CACHE:
        _CLASS_CACHE[base_cls] = type(
            "Loop234AgentLoop", (Loop234Mixin, base_cls), {})
    return _CLASS_CACHE[base_cls]


DEFAULT_CONFIG234: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG234["daemon"]["module"] = "Loop234Daemon (this file)"
DEFAULT_CONFIG234["self"] = dict(L138I.DEFAULT_CONFIG138I.get("self", {}))
DEFAULT_CONFIG234["self"]["rule234"] = (
    "whole-turn (greeting +) how-are-you questions about the assistant get "
    "the fixed reply \"" + FIXED_234 + "\" (\"Hi! \" first when greeted); "
    "reply-only; everything else byte-identical to loop138i")


def build_agent234(cfg: dict | None = None):
    """build_agent138i (read-only) re-classed with the 234 turn wrapper.
    Adds no state and no __init__; only turn() differs."""
    cfg = dict(DEFAULT_CONFIG234, **(cfg or {}))
    loop = L138I.build_agent138i(cfg)
    loop.__class__ = _class234(type(loop))
    loop.notes.append("loop234: loop138i + fixed honest how-are-you reply")
    return loop


class Loop234Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 234 agent inside."""

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
        self.loop = build_agent234(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon234(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    return Loop234Daemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 234 small-talk agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--classify", default=None,
                        help="print the matcher verdict for TEXT and exit")
    args = parser.parse_args(argv)
    if args.classify is not None:
        print(json.dumps({"text": args.classify,
                          "reply": reply_234(args.classify)}))
        return 0
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG234)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG234)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon234(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent234(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
