#!/usr/bin/env python3
"""Experiment 138c -- ONE CHANGE to loop138's self-layer serving rule.

Additive-only follow-up to scripts/fable_loop138_agent.py (imported
read-only, never edited; no existing file is touched). Everything else --
L1 ears (134 + 129 punct + 113c gate), notebook, reasoner, mouth, sleep
retrofit, exactly-once daemon -- is loop138 unchanged.

THE ONE CHANGE (serving rule, in Loop138cAgentLoop.turn):
  loop138 served a self reply on every notebook-missed turn the frozen
  router did not decline: routed intent's canonical self answer on
  non-DECLINE, and the mashed loop138 decline
  (HONEST_DECLINE + DECLINE_SUFFIX) on DECLINE.
  loop138c serves the self answer ONLY when BOTH hold:
    (a) the router gives a non-DECLINE intent, AND
    (b) the self answerer returns a GROUNDED answer.
  In every other case the turn's reply is the BASE loop's own reply,
  verbatim (exactly what super().turn -- loop134+L1 -- returned).

  Grounded (sealed predicate, see PASSMARKS.md): the answer is NOT the
  Self99 FALLBACK text ("I do not understand that question...") AND it
  contains NONE of the Self99 DECLINE_MARKERS ("I have no record",
  "I have no opinions", "You never told me", ...). Rationale: a
  decline-marker sentence claims no fact, so it is not grounded content.
  This matters because the frozen router can return decline-kind intents
  (e.g. D7) as non-DECLINE: bench121-4hop-165 routes D7 and its canonical
  answer ("I have no opinions...") is a decline body, not FALLBACK, so a
  FALLBACK-only check would keep serving it. Genuine self answers (counts,
  names, turns, capability lists -- verified against every answer_self
  branch) contain no marker and are still served.

  Diagnostic logging (self_routed entries, last_routed, self_turn_log) is
  kept: entries gain "served": "self"|"base" and "grounded": bool, so the
  bench/panel drivers can count what was served vs merely routed.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-self138c-20260922/loop138c-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_loop134_agent as L134  # noqa: E402 (base loop, read-only)
import fable_loop138_agent as L138  # noqa: E402 (wrapped agent, read-only)
import fable_loop90_agent as L90  # noqa: E402 (thinker module name, read-only)
import fable_self99 as S99  # noqa: E402 (markers, read-only)

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138 set; no file edited).
A._APOS = L134._APOS_SHOUTED_134

# Exact Self99 FALLBACK text (scripts/fable_self99.py lines ~597-598; also
# scripts/fable_self100_runner.py FALLBACK). Compared by equality plus a
# startswith guard so a trailing-space variant can never slip through.
FALLBACK = ("I do not understand that question. Ask me about what I "
            "know, where it came from, or what I am doing.")
FALLBACK_PREFIX = "I do not understand that question"


def self_grounded(ans: str) -> bool:
    """Sealed grounded predicate: not FALLBACK and no decline marker."""
    if ans == FALLBACK or ans.startswith(FALLBACK_PREFIX):
        return False
    return not any(m in ans for m in S99.DECLINE_MARKERS)


class Loop138cAgentLoop(L138.Loop138AgentLoop):
    """Loop138AgentLoop with the one changed serving rule.

    Base path (notebook-first, L1 ears, _act sanitize, self-turn logging)
    is inherited byte-for-byte; only the notebook-missed branch changes:
    serve the self answer solely on (non-DECLINE + grounded), else serve
    the base loop's own reply verbatim.
    """

    def turn(self, text: str) -> list[str]:
        before = set(self.nb.facts)
        # Base reply verbatim: exactly what loop138's super().turn --
        # loop134+L1 -- returns (Loop138AgentLoop.turn calls
        # super().turn, i.e. this method, on the same state).
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
            intent, info = L138._route127(text)
            ans: str | None = None
            grounded = False
            if intent != "DECLINE":
                ans = L138.self_answer_from_live_state(self, text, intent)
                grounded = self_grounded(ans)
            entry = {"n": n, "text": text, "intent": intent,
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans, "grounded": grounded,
                     "served": ("self" if (intent != "DECLINE"
                                           and grounded) else "base")}
            self.self_routed.append(entry)
            self.last_routed = entry
            if intent != "DECLINE" and grounded:
                assert ans is not None
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            # Every other case: the BASE loop's own reply, verbatim.
            self.self_turn_log[-1]["routed"] = intent + " (base served)"
            self.self_turn_log[-1]["reply"] = reply
            return said
        return said


DEFAULT_CONFIG138C: dict = copy.deepcopy(L138.DEFAULT_CONFIG138)
DEFAULT_CONFIG138C["daemon"]["module"] = "Loop138cDaemon (this file)"
DEFAULT_CONFIG138C["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py)",
    "answerer": "Self99Agent.answer_self over live loop138c state",
    "rule": ("notebook answers always win; a notebook-missed turn serves "
             "the self answer ONLY on (router non-DECLINE AND grounded "
             "answer: not FALLBACK, no DECLINE_MARKERS); every other case "
             "serves the base loop's own reply verbatim"),
}


def build_agent138c(cfg: dict | None = None) -> Loop138cAgentLoop:
    """Same construction as loop138, with the loop class swapped.

    build_agent138 is reused read-only for the full L1/L2-state/L3 wiring;
    only the instance class changes (the subclass adds no attributes, it
    only overrides turn), so behaviour differs solely by the serving rule.
    """
    cfg = dict(DEFAULT_CONFIG138C, **(cfg or {}))
    loop = L138.build_agent138(cfg)
    loop.__class__ = Loop138cAgentLoop
    loop.notes.append("loop138c: self serves only on "
                      "(non-DECLINE + grounded); else base reply verbatim")
    return loop


class Loop138cDaemon(L138.Loop138Daemon):
    """Loop138Daemon shape with the loop138c agent inside + 108 exactly-once.

    __init__ mirrors Loop138Daemon.__init__ line for line except the build
    call; process_file/run are inherited unchanged.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
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
        self.loop = build_agent138c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)


def run_daemon138c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138c loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
