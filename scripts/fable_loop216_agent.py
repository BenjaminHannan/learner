#!/usr/bin/env python3
"""Experiment 216 -- DECLINE INTENTS NEED THEIR CUE, on loop138i.

loop216 = loop138i + ONE change (Muse). Problem (director-verified on
loop138i): when the notebook misses, the learned self router (route127)
sends ordinary world questions to canned decline answers, and decline
intents skip the novelty guard ("novelty: vacuous (always-decline
intent)"): "Who painted Tin Stars?" -> "I do not have favourites."
(intent D1); "Who composed Blue Rain?" -> D1; "What did Barnaby
Quillfeather direct?" / "Who designed Xenon Lullabies?" -> "You never
told me why. ..." (D5). No false fact, but the reply answers a question
nobody asked.

THE ONE CHANGE: a decline intent Dk (the D1-D10 keys of
fable_self105.CANONICAL) is served only when the turn contains one of
Dk's cue words or a second-person word (you, your, yours, yourself, u,
ur); otherwise the turn gets exactly the reply the router's own DECLINE
branch gives today (fable_self105.HONEST_DECLINE + the loop's
DECLINE_SUFFIX), never a new sentence.

Cue table (one table; whole [a-z]+ tokens, case-insensitive; listed
inflections included, i.e. stems allowed):
  D1  favourite, favourites, favorite, favorites
  D2  feel, feels, felt, feeling, feelings, emotion, emotions
  D3  yesterday, ago, earlier, last, week, weeks, night, nights, time, times
  D4  will, tomorrow, future, next, year, years, week, weeks, month, months,
      plus the phrase "going to"
  D5  why, reason, reasons, because
  D6  tell, tells, told, say, says, said -- only together with a
      second-person word (so D6 reduces to "second-person present")
  D7  better, worse, best, worst, prefer, prefers, than
  D8  name, names -- only together with my / i / me
  D9  old, older, oldest, age, ages, aged
  D10 dream, dreams, dreamt, dreamed, dreaming
Second-person words (closed): you, your, yours, yourself, u, ur.

EXACT CALL SITE (same one exp 212 wraps, kept stackable): the 138g
notebook-miss branch calls intent, info = L138._route127(text)
(scripts/fable_loop138g_agent.py:324; L138 is scripts/fable_loop138_agent).
This file's Loop216AgentLoop.turn wraps the whole 138i chain: it swaps
L138._route127 for a cue-gated stand-in for the duration of this turn
only (same module attribute the call site reads, saved/restored in
finally). The stand-in calls the saved router, then downgrades a Dk
verdict to DECLINE when the turn has neither Dk's cue nor a
second-person word. The DECLINE branch then runs byte-for-byte as it
does today. Non-decline intents, DECLINE verdicts, ears/_act/reasoner/
notebook/sleep/daemon are untouched. Because the wrapper delegates to
whatever L138._route127 currently is, a later merge can nest this gate
with exp 212's statement gate in either order.

New files only (216 prefix); 138i and every earlier piece read-only.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop216_agent.py --daemon --dir DIR \\
    --config artifacts/fable-declinecue216-20260922/loop216-config.json
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
import fable_loop134_agent as L134  # noqa: E402 (turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
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

# --------------------------------------------------------------------------
# THE ONE TABLE: decline-intent cue words (whole-token, case-insensitive).
# --------------------------------------------------------------------------
_SECOND_PERSON216 = frozenset({"you", "your", "yours", "yourself", "u", "ur"})
_FIRST_PERSON216 = frozenset({"my", "i", "me"})
_TOKEN216 = re.compile(r"[a-z]+")
_GOING_TO216 = re.compile(r"\bgoing\s+to\b")

CUES216: dict[str, frozenset[str]] = {
    "D1": frozenset({"favourite", "favourites", "favorite", "favorites"}),
    "D2": frozenset({"feel", "feels", "felt", "feeling", "feelings",
                      "emotion", "emotions"}),
    "D3": frozenset({"yesterday", "ago", "earlier", "last", "week", "weeks",
                      "night", "nights", "time", "times"}),
    "D4": frozenset({"will", "tomorrow", "future", "next", "year", "years",
                      "week", "weeks", "month", "months"}),
    "D5": frozenset({"why", "reason", "reasons", "because"}),
    "D6": frozenset({"tell", "tells", "told", "say", "says", "said"}),
    "D7": frozenset({"better", "worse", "best", "worst", "prefer", "prefers",
                      "than"}),
    "D8": frozenset({"name", "names"}),
    "D9": frozenset({"old", "older", "oldest", "age", "ages", "aged"}),
    "D10": frozenset({"dream", "dreams", "dreamt", "dreamed", "dreaming"}),
}


def _tokens216(turn: str) -> set[str]:
    """Whole [a-z]+ tokens of the lowered turn (case-insensitive)."""
    return set(_TOKEN216.findall(str(turn).lower()))


def has_second_person216(turn: str) -> bool:
    """True iff any whole token is a second-person word."""
    return bool(_tokens216(turn) & _SECOND_PERSON216)


def decline_cues_present216(turn: str, intent: str) -> bool:
    """True iff the turn carries intent Dk's cue (pure function).

    D6's cue counts only together with a second-person word; D8's cue
    ("name") counts only together with my / i / me; D4 also fires on the
    phrase "going to". Non-decline intents return True (never gated).
    """
    cues = CUES216.get(intent)
    if cues is None:
        return True
    toks = _tokens216(turn)
    hit = bool(toks & cues)
    if intent == "D4" and not hit:
        hit = _GOING_TO216.search(str(turn).lower()) is not None
    if not hit:
        return False
    if intent == "D6":
        return bool(toks & _SECOND_PERSON216)
    if intent == "D8":
        return bool(toks & _FIRST_PERSON216)
    return True


def should_serve_decline216(turn: str, intent: str) -> bool:
    """The one gate: serve Dk iff cue(Dk) or a second-person word."""
    if intent not in CUES216:
        return True
    return decline_cues_present216(turn, intent) \
        or has_second_person216(turn)


def _gated_route216(text: str) -> tuple[str, dict]:
    """Stand-in for L138._route127 while the turn runs (pure downgrade).

    Calls the saved router, then maps a cueless Dk verdict to DECLINE.
    Never calls the encoder itself; the DECLINE branch below runs
    byte-for-byte as it does today.
    """
    intent, info = _gated_route216.saved(text)  # type: ignore[attr-defined]
    if intent in CUES216 and not should_serve_decline216(text, intent):
        info = dict(info)
        info["gate216"] = "decline-needs-cue:%s" % intent
        info["gated_intent"] = intent
        return ("DECLINE", info)
    return intent, info


class Loop216AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + the one decline-cue gate (turn wrapper only).

    L138._route127 (the exact function object the 138g call site reads)
    is swapped for _gated_route216 for this turn only and restored in
    finally, so nesting with exp 212's identical-pattern wrapper stacks
    in either order.
    """

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        orig = L138._route127
        _gated_route216.saved = orig  # type: ignore[attr-defined]
        L138._route127 = _gated_route216  # type: ignore[method-assign]
        try:
            return super().turn(text)
        finally:
            L138._route127 = orig  # type: ignore[method-assign]


DEFAULT_CONFIG216: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG216["ears"]["stand_in"] = (
    L138I.DEFAULT_CONFIG138I["ears"]["stand_in"]
    + "; 216 decline-cue gate (D-intent served only with its cue or a "
    "second-person word, else today's DECLINE reply)")
DEFAULT_CONFIG216["daemon"]["module"] = "Loop216Daemon (this file)"


def build_agent216(cfg: dict | None = None) -> Loop216AgentLoop:
    """Build the loop138i agent shape with the 216 turn gate stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG216, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    import fable_fix167e_label as L167E  # noqa: E402 (read-only)
    mouth = L167E.Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    inner_ears = L138I.Loop138iEars(Loop96Ears(chain))
    loop = Loop216AgentLoop(
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
    loop.notes.append("loop216: loop138i + decline-cue gate (D-intent "
                      "served only with its cue or a second-person word, "
                      "else today's HONEST_DECLINE + DECLINE_SUFFIX)")
    return loop


class Loop216Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 216 agent inside."""

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
        self.loop = build_agent216(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon216(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop216Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def selftest216() -> int:
    """Gate unit checks only (pure function, no agent build)."""
    checks = [
        # (turn, intent, want_serve)
        ("Who painted Tin Stars?", "D1", False),
        ("Who composed Blue Rain?", "D1", False),
        ("What did Barnaby Quillfeather direct?", "D5", False),
        ("Who designed Xenon Lullabies?", "D5", False),
        ("What's your favourite colour?", "D1", True),
        ("What is the favourite colour?", "D1", True),
        ("Do you feel sad?", "D2", True),
        ("What is a feeling?", "D2", True),
        ("What did Ben say yesterday?", "D3", True),
        ("Where will Mira live next year?", "D4", True),
        ("They are going to march.", "D4", True),
        ("Why does Pim live in Arden?", "D5", True),
        ("What did Tom tell you?", "D6", True),
        ("What did Tom tell Mara?", "D6", False),
        ("What did Tom say?", "D6", False),
        ("Did Tom speak to you?", "D6", True),
        ("Is Oslo better than Rome?", "D7", True),
        ("What is my name?", "D8", True),
        ("What is the name of this song?", "D8", False),
        ("Do you know the name?", "D8", True),
        ("How old is Pim?", "D9", True),
        ("Did you dream?", "D10", True),
        ("Do dreams happen?", "D10", True),
        ("Who painted Tin Stars?", "C5", True),
        ("Who painted Tin Stars?", "DECLINE", True),
    ]
    ok = True
    for text, intent, want in checks:
        got = should_serve_decline216(text, intent)
        flag = "OK" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print("%s: serve=%s want=%s :: [%s] %s"
              % (flag, got, want, intent, text), flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 216 decline-cue on 138i")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG216 to PATH and exit")
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
        return selftest216()

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG216)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG216)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon216(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent216(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
