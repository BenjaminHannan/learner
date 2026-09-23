#!/usr/bin/env python3
"""Experiment 212 -- SELF-ROUTER ONLY ON QUESTION-SHAPED TURNS, on loop138i.

loop212 = loop138i + ONE change (Muse). Problem (director-verified on
138i): the self-question router (route127 over live state, reached through
the loop138 chain) answers STATEMENTS about the user or other people as if
they were questions about the assistant, so the user's fact is dropped:
"My favourite colour is teal." -> "I do not have favourites.";
"Tired is my cat's name." -> "You never told me your name, so I do not
know it.".

THE ONE CHANGE: the self router is skipped (the turn goes on to the normal
pipeline, exactly as if the router had declined: HONEST_DECLINE +
DECLINE_SUFFIX, zero new writes) when the turn is statement-shaped AND
contains no second-person word.

Statement-shaped (this file): the whitespace-normalised turn does not end
with "?" and its first word (first [A-Za-z]+ via the base's own
_FIRST_WORD188 regex, after the base's own whitespace normalisation) is
not a question word or auxiliary. _QWORDS188/_AUX188/_FIRST_WORD188 are
reused by import from scripts/fable_loop188_agent.py:91-119 (read-only;
note this is wider than 188's statement test on purpose: command openers
such as tell/describe count as statement-shaped here and are kept on
today's route only by the second-person rule).
Second-person words (closed): you, your, yours, yourself, u, ur
(matched as whole [a-z]+ tokens, case-insensitive). So "Tell me about
yourself.", "Describe yourself.", "You are clever." keep today's route.
Questions are untouched ("Where am I from?" keeps its current, separate
bug; not fixed here).

EXACT CALL SITE (followed through loop138i's MRO): Loop138iAgentLoop
defines no turn(), so turn() resolves to Loop138hAgentLoop.turn
(scripts/fable_loop138h_agent.py:160: super().turn + USER-key scrub),
whose super().turn is Loop138gAgentLoop.turn, whose notebook-miss branch
calls intent, info = L138._route127(text)
(scripts/fable_loop138g_agent.py:324; L138 is scripts/fable_loop138_agent,
the same module object whose _route127 the 138 base turn also calls).
This file's Loop212AgentLoop.turn wraps that whole chain: when the gate
fires it swaps L138._route127 for a DECLINE stub for the duration of this
turn only (same module attribute the call site reads, restored in
finally), so the DECLINE branch runs byte-for-byte as it does today when
the router declines. No other path is touched: ears/_act/reasoner/
notebook/sleep/daemon are 138i's unchanged.

New files only (212 prefix); 138i and every earlier piece unread-only.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop212_agent.py --daemon --dir DIR \\
    --config artifacts/fable-selfgate212-20260922/loop212-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_loop188_agent import (  # noqa: E402 (statement-shape sets, read-only)
    _AUX188,
    _FIRST_WORD188,
    _QWORDS188,
)
from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Same process-wide overrides the 138i base applies (no file edited).
WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134

# Closed second-person set (whole-token, case-insensitive).
_SECOND_PERSON212 = frozenset({"you", "your", "yours", "yourself", "u", "ur"})

_TOKEN212 = re.compile(r"[a-z]+")


def _norm212(text: object) -> str:
    """The base's own normalisation: collapse whitespace."""
    return " ".join(str(text).split())


def is_statement_shaped212(turn: str) -> bool:
    """Spec statement shape: no trailing "?", first word not qword/aux."""
    s = _norm212(turn)
    if not s or s.endswith("?"):
        return False
    m = _FIRST_WORD188.match(s)
    if not m:
        return False
    first = m.group(1).lower()
    if first in _QWORDS188 or first in _AUX188:
        return False
    return True


def has_second_person212(turn: str) -> bool:
    """True iff any whole token is a second-person word."""
    return any(t in _SECOND_PERSON212
               for t in _TOKEN212.findall(str(turn).lower()))


def should_skip_self_router212(turn: str) -> bool:
    """The one gate: statement-shaped AND no second-person word."""
    return is_statement_shaped212(turn) and not has_second_person212(turn)


def _declined212(text: str) -> tuple[str, dict]:
    """Stand-in for L138._route127 while the gate fires: always DECLINE.

    Never calls the encoder. The info dict carries the gate marker so the
    self_routed log shows why the router was not consulted.
    """
    return ("DECLINE", {"gate212": "skip-statement-no-second-person",
                        "best": "DECLINE", "best_score": 0, "second": 0,
                        "need": 0, "margin": 0})


class Loop212AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + the one self-router gate (turn wrapper only).

    When should_skip_self_router212 fires, L138._route127 (the exact
    function object the 138g call site reads) is swapped for _declined212
    for this turn only, so the turn is served the base's normal decline
    byte-for-byte as when the router declines. All other turns run the
    unchanged 138i path.
    """

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        if should_skip_self_router212(text):
            orig = L138._route127
            L138._route127 = _declined212  # type: ignore[method-assign]
            try:
                return super().turn(text)
            finally:
                L138._route127 = orig  # type: ignore[method-assign]
        return super().turn(text)


DEFAULT_CONFIG212: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG212["ears"]["stand_in"] = (
    L138I.DEFAULT_CONFIG138I["ears"]["stand_in"]
    + "; 212 self-router gate (statement-shaped + no second-person "
    "-> router skipped as DECLINE)")
DEFAULT_CONFIG212["daemon"]["module"] = "Loop212Daemon (this file)"


def build_agent212(cfg: dict | None = None) -> Loop212AgentLoop:
    """Build the loop138i agent shape with the 212 turn gate stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG212, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    import fable_fix167e_label as L167E  # noqa: E402 (read-only)
    mouth = L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = L138I.Loop138iEars(Loop96Ears(chain))
    loop = Loop212AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    patch_chain142(chain)
    patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop212: loop138i + self-router gate (statement-"
                      "shaped + no second-person -> router skipped as "
                      "DECLINE; questions untouched)")
    return loop


class Loop212Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 212 agent inside."""

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
        self.pid = _os.getpid()
        self.boot_time = time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent212(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon212(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop212Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 212 selfgate on 138i")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG212 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--selftest", action="store_true",
                        help="gate unit checks only (no agent build)")
    args = parser.parse_args(argv)

    if args.selftest:
        checks = [
            ("My favourite colour is teal.", True),
            ("Tired is my cat's name.", True),
            ("Tell me about yourself.", False),
            ("Describe yourself.", False),
            ("You are clever.", False),
            ("Where am I from?", False),
            ("What is your name?", False),
            ("What can you do for me?", False),
            ("Nora baked a pie.", True),
        ]
        ok = True
        for text, want in checks:
            got = should_skip_self_router212(text)
            flag = "OK" if got == want else "MISMATCH"
            if got != want:
                ok = False
            print(f"{flag}: skip={got} want={want} :: {text}", flush=True)
        return 0 if ok else 1

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG212)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG212)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon212(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent212(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
