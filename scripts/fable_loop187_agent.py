#!/usr/bin/env python3
"""Experiment 187 -- self-question paraphrase routing on loop138g (turn only).

Base: loop138g (scripts/fable_loop138g_agent.py, read-only). ONE CHANGE:
paraphrases of questions ABOUT THE AGENT ITSELF are routed to the
lineage's existing self answers instead of misrouting:

  WRONG today (director probe 09:40 on loop138g):
    "Who made you?" -> D8 user-name reply
      ("You never told me your name, so I do not know it.")
    "Who built you?" / "Who are you?" -> generic HONEST_DECLINE + suffix.

Rule (closed, stdlib regex only, in classify_self187):
  - maker: who (made|built|created|trained) you
  - identity: who are you / what are you
  - name: what is your name / what's your name / what are you called /
    do you have a name
  - cando: what can you do / what do you do / what are your
    capabilities / what are you able to do
  Guard: any maker/identity/name match is dropped when the turn names
  the user (my/me/mine/myself/i) or a third person (possessive 's or a
  trailing name/object other than "you"). Cando patterns need no guard
  ("What can you do for me?" stays self). Statements (no question
  shape) never match.

Answers reuse lineage content exactly:
  - cando -> G168.grounded_self_answer(self, text, "C24"), i.e. the exact
    C24 capability-sheet answer the lineage already serves for
    "What can you do?" (fixed sheet scripts/fable_self99.py:50-57).
  - maker/identity/name -> the lineage has NO answer (verified: no
    made/built/created/trained/who-are-you/what-are-you/your-name
    branch in answer_self; D8 "my name" is about the USER). Served with
    fixed honest replies written only from project docs (brief + D2):
    MAKER187 / IDENTITY187 / NAME187 below. No invented facts.
  - user questions ("What is my name?", "Who am I?", "Who is my boss?",
    "Who made Lee?", "Who made Kim's cake?") never match the closed
    patterns, so they fall through to super().turn() byte-identical.

No existing file is edited; loop138g is imported read-only. turn() is
the 138g body verbatim plus the intent-correction step (notebook-missed
only; asks/writes never touch it).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop187_agent.py --daemon --dir DIR \\
    --config artifacts/fable-selfq187-20260922/loop187-config.json
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
import fable_fix168_ground as G168  # noqa: E402 (168 grounding, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop138f_agent as L138F  # noqa: E402 (wrapped stack, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (wrapped stack, read-only)
import fable_loop96_agent as L96  # noqa: E402 (inner chain ears, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process.
A._APOS = L134._APOS_SHOUTED_134

# ------------------------------------------------- fixed honest replies 187
# Written ONLY from existing project docs (48 brief: teachable assistant;
# notebook/lookup-loop/fixed-rules from self99 D2 feelings answer). They
# claim no maker, no name, no fact not in live state.
MAKER187 = ("Nobody taught me who made me, so I do not know it. "
            "I am plain software you are teaching: a notebook, "
            "a lookup loop, and fixed rules.")
IDENTITY187 = ("I am plain software you are teaching: a notebook, "
               "a lookup loop, and fixed rules. "
               "I can only tell you what you taught me.")
NAME187 = ("You never gave me a name, so I do not have one. "
           "I am plain software you are teaching: a notebook, "
           "a lookup loop, and fixed rules.")

# ------------------------------------------------------- closed patterns 187
_MAKER187_RE = re.compile(
    r"^\s*who\s+(has\s+|did\s+|has\s+ever\s+)?"
    r"(made|built|created|trained)\s+you\s*\??\s*$", re.I | re.S)
_IDENTITY187_RE = re.compile(
    r"^\s*(who\s+are\s+you|what\s+are\s+you)\s*\??\s*$", re.I | re.S)
_NAME187_RES = [
    re.compile(r"^\s*what\s*'?s\s+(is\s+)?your\s+name\s*\??\s*$",
               re.I | re.S),
    re.compile(r"^\s*what\s+is\s+your\s+name\s*\??\s*$", re.I | re.S),
    re.compile(r"^\s*what\s+are\s+you\s+called\s*\??\s*$", re.I | re.S),
    re.compile(r"^\s*do\s+you\s+have\s+a\s+name\s*\??\s*$", re.I | re.S),
    re.compile(r"^\s*have\s+you\s+got\s+a\s+name\s*\??\s*$", re.I | re.S),
]
_CANDO187_RES = [
    re.compile(r"^\s*what\s+can\s+you\s+do\s*(for\s+me\s*)?\??\s*$",
               re.I | re.S),
    re.compile(r"^\s*what\s+do\s+you\s+do\s*\??\s*$", re.I | re.S),
    re.compile(r"^\s*what\s+are\s+your\s+capabilit(ies|y)\s*\??\s*$",
               re.I | re.S),
    re.compile(r"^\s*what\s+are\s+you\s+able\s+to\s+do\s*\??\s*$",
               re.I | re.S),
]
# User / third-person guard: maker+identity+name routes are dropped when
# the turn points at anyone but the agent.
_USER187_RE = re.compile(
    r"\bmy\b|\bme\b|\bmine\b|\bmyself\b|\bwho\s+am\s+i\b"
    r"|['\u2019]s\b", re.I)


def classify_self187(text: str) -> str | None:
    """Return maker|identity|name|cando for self-question paraphrases.

    Closed stdlib patterns only. User questions ("What is my name?",
    "Who am I?", "Who is my boss?") and third-person questions
    ("Who made Lee?", "Who made Kim's cake?") structurally miss every
    pattern (they end in a name/object or say "my", never bare "you" /
    "your <noun>"); the guard below is belt-and-braces.
    """
    t = str(text)
    for rx in _CANDO187_RES:
        if rx.match(t):
            return "cando"
    kind = None
    if _MAKER187_RE.match(t):
        kind = "maker"
    elif _IDENTITY187_RE.match(t):
        kind = "identity"
    elif any(rx.match(t) for rx in _NAME187_RES):
        kind = "name"
    if kind is not None:
        # The 's guard must ignore the leading "What's" contraction
        # (Q09 "What's your name?" is self; "Kim's"/"Lee's" stay traps).
        guard_t = re.sub(r"^\s*what['\u2019]s\s+", "what ", t,
                         flags=re.I)
        if _USER187_RE.search(guard_t):
            return None
    return kind


def self187_answer(loop, kind: str, text: str) -> tuple[str, str]:
    """Return (intent_tag, reply) reusing lineage content exactly."""
    if kind == "cando":
        return ("SELF187-cando",
                G168.grounded_self_answer(loop, text, "C24"))
    if kind == "maker":
        return ("SELF187-maker", MAKER187)
    if kind == "identity":
        return ("SELF187-identity", IDENTITY187)
    return ("SELF187-name", NAME187)


class Loop187AgentLoop(L138G.Loop138gAgentLoop):
    """Loop138gAgentLoop + 187 self-paraphrase routing (turn only).

    turn() is the 138g body verbatim; the single inserted step is the
    classify_self187 correction on the notebook-missed path. Non-self
    turns (user questions, traps, statements, teaches, asks) run the
    unchanged 138g path byte-identically.
    """

    def turn(self, text: str) -> list[str]:
        before = set(self.nb.facts)
        said = L134.Loop134AgentLoop.turn(self, text)
        reply = " ".join(said) if said else "(nothing to say)"
        records = list(getattr(self, "last_records", []))
        n = len(self.self_turn_log) + 1
        after = set(self.nb.facts)
        for fid in after - before:
            self.self_origin[fid] = {"by": "Ben", "turn": n}
        self.self_turn_log.append({
            "n": n, "ben": text, "reply": reply, "records": records,
            "statuses": [r.get("status", r.get("kind")) for r in records],
            "stage": getattr(self.ears, "last_stage", ""),
            "score": getattr(self.ears, "last_score", 0.0),
            "wrote": len(after - before) > 0 or str(text).startswith("forget"),
            "via": "loop", "tick": self.tick, "mode": self.mode,
        })
        self.self_mode_log.append({"tick": self.tick, "mode": self.mode})
        self.last_routed = None
        if L138.notebook_missed(records):
            # [187] THE ONE CHANGE: self-paraphrase routing first.
            kind187 = classify_self187(text)
            if kind187 is not None:
                tag, ans = self187_answer(self, kind187, text)
                entry = {"n": n, "text": text, "intent": tag,
                         "info": {"self187": kind187}, "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = tag
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            intent, info = L138._route127(text)
            if intent != "DECLINE":
                # [168] THE ONE CHANGE: grounded self answer.
                ans = G168.grounded_self_answer(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            import fable_self105 as S105  # noqa: E402 (frozen text, read-only)

            ans = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
            entry = {"n": n, "text": text, "intent": "DECLINE",
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans}
            self.self_routed.append(entry)
            self.last_routed = entry
            self.self_turn_log[-1]["routed"] = "DECLINE"
            self.self_turn_log[-1]["reply"] = ans
            return [ans]
        return said


DEFAULT_CONFIG187: dict = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
DEFAULT_CONFIG187["ears"]["stand_in"] = (
    "Loop138gEars unchanged (loop138f stack + layer A outside-in: 137 "
    "say/hearsay/hypo framing, 158c wh-city rewriter, 139e "
    "relation-gated tail guard)")
DEFAULT_CONFIG187["daemon"]["module"] = "Loop187Daemon (this file)"
DEFAULT_CONFIG187["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py) "
              "+ classify_self187 paraphrase gate (this file) on the "
              "notebook-missed path",
    "answerer": "cando reuses grounded_self_answer C24 verbatim; "
                "maker/identity/name use fixed honest replies written "
                "from project docs (no lineage answer exists)",
    "rule": ("loop138g verbatim otherwise: notebook answers win; "
             "notebook-missed self paraphrases serve the 187 reply; "
             "user questions keep their 138g replies byte-identical"),
}


def build_agent187(cfg: dict | None = None) -> Loop187AgentLoop:
    """Build the loop138g agent shape with the 187 turn gate on top."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG187, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = L138G.Loop138gEars(Loop96Ears(chain))
    loop = Loop187AgentLoop(
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
    loop.notes.append("sleep187: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop187: loop138g + self-question paraphrase routing "
                      "(exp-187 turn-only; cando reuses C24, maker/identity/"
                      "name use fixed honest replies; user questions "
                      "byte-identical)")
    return loop


class Loop187Daemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 187 agent inside."""

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
        self.loop = build_agent187(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon187(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop187Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 187 self-q routing")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138g)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG187 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--classify", default=None,
                        help="print classify_self187 for one turn and exit")
    args = parser.parse_args(argv)

    if args.classify is not None:
        print(classify_self187(args.classify))
        return 0

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG187)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG187)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon187(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent187(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
