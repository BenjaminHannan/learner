#!/usr/bin/env python3
"""Exp 224b — loop224: loop138i with ONE clear decline sentence per turn type.

THE ONE CHANGE (agent side). loop138i serves the glued double decline
S105.HONEST_DECLINE + L138.DECLINE_SUFFIX ("I do not know that from what you
taught me. I have no record of it, so I will not guess. I didn't understand
that, I don't know -- could you say it another way?") on every turn where
the notebook path did not understand AND the frozen self router declined.
Where it is served (MRO walk): Loop138iAgentLoop -> ... -> Loop138hAgentLoop
.turn (USER-key scrub only) -> Loop138gAgentLoop.turn (scripts/
fable_loop138g_agent.py:337-348, the ONLY place the glue is built for 138i;
Loop138AgentLoop.turn is bypassed because 138g calls L134's turn directly).
The mailbox daemon serves exactly what loop.turn returns
(scripts/fable_loop90_agent.py:498).

loop224 wraps loop.turn on the built 138i instance (read-only reuse of
build_agent138i; no file edited). When, and only when, the turn returned
exactly the glue with last_routed intent DECLINE, the glue is replaced by
ONE sentence chosen from what the pipeline actually did on that turn
(recorded by instance-level taps, not by keywords):

  Q1  the ears emitted an "ask" action (a lookup) -> Q1_SENTENCE
      (structurally unreachable on 138i: an ask always yields an answer
      record, which is never "notebook missed"; kept for honesty)
  Q2  no ask, and the pipeline's own question branch handled the turn
      (Loop138Ears._hear_question ran, or the text is a "?" turn / the
      exp-151 no-"?" question predicate fires -- the same tests the ears
      use to route) -> Q2_SENTENCE
  S1  otherwise (the turn went down the statement/teach path and nothing
      was saved) -> S1_SENTENCE

The sentences live in scripts/fable_decline224.py (sealed with 224a).
Every other reply (screens, small talk, self answers, clarifies, notebook
abstains, answers, saves) is untouched byte for byte. Nothing new is
written: the swap happens after the turn, on the reply text only; the
self logs (self_turn_log[-1]["reply"], the routed entry's "answer") are
updated to the served sentence so the self answerer reports what was said.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop224_agent.py --once "Who painted Blue Orchard?" \\
    --state-dir <scratch dir>
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

import fable_daemon108_run as D108  # noqa: E402 (reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_decline224 as DEC  # noqa: E402 (sealed 224a sentences)
import fable_loop138_agent as L138  # noqa: E402 (DECLINE_SUFFIX, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_qmark151_core as Q151  # noqa: E402 (151 question predicate)

GLUE = None  # resolved lazily from the frozen modules (see _glue)


def _glue() -> str:
    import fable_self105 as S105  # noqa: E402 (frozen text, read-only)
    return S105.HONEST_DECLINE + L138.DECLINE_SUFFIX


def _pipeline_question(text: str) -> bool:
    """The ears' own routing tests: a '?' turn, or the 151 predicate."""
    t = " ".join(str(text).split())
    if t.rstrip().endswith("?"):
        return True
    try:
        return bool(Q151.should_rewrite_151(t))
    except Exception:  # noqa: BLE001 -- predicate failure = not a question
        return False


def install_decline224(loop) -> None:
    """Instance-level taps + the one reply swap on a built 138i loop."""
    glue = _glue()
    state = {"acts": [], "qbranch": False}
    loop.decline224_log = []

    outer_hear = loop.ears.hear

    def hear224(turn):
        acts = outer_hear(turn)
        try:
            state["acts"].extend(a for a in acts if isinstance(a, dict))
        except TypeError:
            pass
        return acts

    loop.ears.hear = hear224
    inner = loop.parts90.get("ears")
    if inner is not None and hasattr(inner, "_hear_question"):
        inner_hq = inner._hear_question

        def hear_question224(*args, **kwargs):
            state["qbranch"] = True
            return inner_hq(*args, **kwargs)

        inner._hear_question = hear_question224

    base_turn = loop.turn

    def turn224(text: str) -> list[str]:
        state["acts"] = []
        state["qbranch"] = False
        said = base_turn(text)
        routed = getattr(loop, "last_routed", None)
        if not (list(said) == [glue] and isinstance(routed, dict)
                and routed.get("intent") == "DECLINE"):
            return said
        if any(a.get("act") == "ask" for a in state["acts"]):
            kind = "Q1"
        elif state["qbranch"] or _pipeline_question(text):
            kind = "Q2"
        else:
            kind = "S1"
        ans = DEC.NEW_SENTENCES224[kind]
        routed["answer"] = ans
        routed["decline224"] = kind
        try:
            loop.self_turn_log[-1]["reply"] = ans
        except (AttributeError, IndexError):
            pass
        loop.decline224_log.append({
            "text": text, "kind": kind, "qbranch": state["qbranch"],
            "acts": [a.get("act") for a in state["acts"]]})
        return [ans]

    loop.turn = turn224
    loop.notes.append("loop224: glue decline -> one sentence per turn type "
                      "(Q1 ask/no value, Q2 not understood question, S1 "
                      "unsaved statement); all other replies unchanged")


DEFAULT_CONFIG224: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG224["self"] = dict(DEFAULT_CONFIG224.get("self", {}))
DEFAULT_CONFIG224["self"]["decline224"] = (
    "glue decline replaced by one sentence per turn type "
    "(scripts/fable_decline224.py NEW_SENTENCES224)")
DEFAULT_CONFIG224["daemon"] = {"module": "Loop224Daemon (this file)"}


def build_agent224(cfg: dict | None = None):
    loop = L138I.build_agent138i(cfg)
    install_decline224(loop)
    return loop


class Loop224Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon.__init__ body (scripts/fable_loop138i_agent.py:441-
    470) with build_agent224 in place of build_agent138i; run() etc.
    inherited unchanged."""

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
        self.loop = build_agent224(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 224b loop224")
    ap.add_argument("--config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None, help="daemon directory")
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--once", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG224)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop224Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        if not args.state_dir:
            ap.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent224(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
