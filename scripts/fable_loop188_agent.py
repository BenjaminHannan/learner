#!/usr/bin/env python3
"""Experiment 188 -- STATEFALL: statement-shaped fallback on loop138g.

loop188 = loop138g + ONE change (reply text only, outermost): when a turn
is statement-shaped AND the base would serve the generic QUESTION fallback
(HONEST_DECLINE + DECLINE_SUFFIX, byte-for-byte), serve one fixed
STATEMENT fallback instead. Nothing else changes: no new writes, no new
events, no ears/_act/reasoner/notebook/sleep/daemon change.

Statement-shaped (closed, stdlib-only):
  - no "?" anywhere in the turn, AND
  - first alphabetic word (lowercased) is not a question word
    (who/what/where/when/why/which/whom/whose/how), not an auxiliary
    (is/are/was/were/am/be/do/does/did/have/has/had/can/could/will/
    would/shall/should/may/might/must/ought/need/dare), and not a
    command/pretend/greeting opener the base already handles
    (tell/show/give/forget/remember/repeat/say/explain/describe/list/
    count/pretend/imagine/suppose/assume/hello/hi/hey/please/thanks).
Because the swap additionally requires the base reply to be the generic
question fallback, turns the base already handles (teaches, pretend,
greetings, confirmations, hearsay, hypo, split-clarifies, grounded self
replies) can never change: their replies differ from the fallback.

Hearsay ("Word is..." generic-fallback shapes get the statement fallback;
"I heard..."/"Rumour has it..." keep HEARSAY_MSG): 0 writes either way.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop188_agent.py --daemon --dir DIR \\
    --config artifacts/fable-statefall188-20260922/loop188-config.json
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
import fable_loop138_agent as L138  # noqa: E402 (DECLINE_SUFFIX, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (mouth, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (reasoner, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped base, read-only)
import fable_self105 as S105  # noqa: E402 (HONEST_DECLINE, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)
from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)

# Same process-wide overrides the 138g base applies (no file edited).
WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134

# The generic QUESTION fallback the base serves on DECLINE (sealed text).
QUESTION_FALLBACK188 = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX

# THE ONE sealed sentence served for statement-shaped unparsed turns. It
# keeps two shared abstain markers ("don't know", "another way") so the
# frozen mechanical judges -- sessions152 is_clarify, bench121
# ABSTAIN_PHRASES, rt81's wanted-marker check -- still read it as an
# honest abstain, exactly as they read the question fallback; it drops
# only the question-answering head ("I do not know that from what you
# taught me. I have no record of it, so I will not guess"), which is the
# part that answers a question nobody asked.
STATEMENT_FALLBACK188 = (
    'I couldn\'t save that as a fact. '
    'I don\'t know that shape yet. '
    'Could you say it another way, like "Kim\'s boss is Lee."'
)

_QWORDS188 = frozenset({
    "who", "what", "where", "when", "why", "which", "whom", "whose", "how",
})
_AUX188 = frozenset({
    "is", "are", "was", "were", "am", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "will", "would", "shall", "should",
    "may", "might", "must", "ought", "need", "dare",
})
_NONSTATEMENT_FIRST188 = frozenset({
    "tell", "show", "give", "forget", "remember", "repeat", "say",
    "explain", "describe", "list", "count",
    "pretend", "imagine", "suppose", "assume",
    "hello", "hi", "hey", "please", "thanks",
})

_FIRST_WORD188 = re.compile(r"^[^A-Za-z]*([A-Za-z]+)")


def is_statement_shaped188(turn: str) -> bool:
    """Closed statement-shape test (no question mark, opener not q/aux/cmd)."""
    s = " ".join(str(turn).split())
    if not s or "?" in s:
        return False
    m = _FIRST_WORD188.match(s)
    if not m:
        return False
    first = m.group(1).lower()
    if first in _QWORDS188 or first in _AUX188:
        return False
    if first in _NONSTATEMENT_FIRST188:
        return False
    return True


class Loop188AgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop + outermost statement-fallback swap (reply only).

    turn() runs the unchanged 138g path, then swaps the reply text ONLY
    when the base served QUESTION_FALLBACK188 on a statement-shaped turn.
    The notebook is never touched here (0 new facts/events by
    construction); the in-memory self log's served-reply field is updated
    to the served text, mirroring how the base overwrites it on routed
    answers.
    """

    def turn(self, text: str) -> list[str]:
        said = super().turn(text)
        reply = " ".join(said).strip() if said else ""
        if reply == QUESTION_FALLBACK188 and is_statement_shaped188(text):
            try:
                if self.self_turn_log:
                    self.self_turn_log[-1]["reply"] = STATEMENT_FALLBACK188
            except Exception:
                pass
            return [STATEMENT_FALLBACK188]
        return said


DEFAULT_CONFIG188: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG188["ears"]["stand_in"] = (
    "Loop138gEars unchanged (loop138f stack + layer A outside-in: 137 "
    "say/hearsay/hypo framing, 158c wh-city rewriter, 139e relation-gated "
    "tail guard)")
DEFAULT_CONFIG188["daemon"]["module"] = "Loop188Daemon (this file)"
DEFAULT_CONFIG188["statefall188"] = {
    "base": "loop138g (scripts/fable_loop138g_agent.py, read-only)",
    "change": ("outermost turn() reply swap only: statement-shaped turn + "
               "base QUESTION_FALLBACK188 -> STATEMENT_FALLBACK188; "
               "0 new writes/events"),
    "question_fallback": QUESTION_FALLBACK188,
    "statement_fallback": STATEMENT_FALLBACK188,
}


def build_agent188(cfg: dict | None = None) -> Loop188AgentLoop:
    """Build the loop138g agent shape with the 188 turn swap stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG188, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = L138G.Loop138gEars(Loop96Ears(chain))
    loop = Loop188AgentLoop(
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
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138g: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop188: loop138g + statefall swap (statement-shaped "
                      "turn + base question fallback -> one fixed statement "
                      "fallback; reply text only, 0 new writes/events)")
    return loop


class Loop188Daemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 188 agent inside."""

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
        self.loop = build_agent188(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon188(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop188Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 188 statefall on 138g")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG188 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG188)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG188)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon188(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent188(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
