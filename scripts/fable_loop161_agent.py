#!/usr/bin/env python3
"""Experiment 161 -- loop161: loop138 with the grounded self card in L2.

Additive wrap of scripts/fable_loop138_agent.py (imported read-only, never
edited). Everything is inherited except the L2 self step: where loop138
serves the frozen router plus the baked table, loop161 serves SelfCard161
(scripts/fable_selfcard161.py), which computes every reply from live loop
state. The serving rule is unchanged: the notebook always wins; only a
notebook-missed turn reaches the card; a card DECLINE serves the loop138
decline text verbatim.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop161_agent.py --daemon --dir DIR \\
    --config artifacts/fable-selfcard161-20260922/loop161-config.json
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

import fable_agent_loop as A  # noqa: E402 (thresholds, read-only)
import fable_loop134_agent as L134  # noqa: E402 (base, read-only)
import fable_loop138_agent as L138  # noqa: E402 (wrapped base, read-only)
import fable_self105 as S105  # noqa: E402 (frozen decline, read-only)
import fable_selfcard161 as SC161  # noqa: E402 (the grounded card)

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134 sets; no file edited). Stored relation keys unchanged.
A._APOS = L134._APOS_SHOUTED_134


class Loop161AgentLoop(L138.Loop138AgentLoop):
    """Loop138AgentLoop with the L2 answerer swapped for the self card."""

    def turn(self, text: str) -> list[str]:
        """Notebook path first; self card only on a notebook miss."""
        before = set(self.nb.facts)
        said = super(L138.Loop138AgentLoop, self).turn(text)
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
            intent = self.self_card.route(text)
            if intent != "DECLINE":
                ans = self.self_card.answer_self(text)
                entry = {"n": n, "text": text, "intent": intent,
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            ans = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
            entry = {"n": n, "text": text, "intent": "DECLINE",
                     "answer": ans}
            self.self_routed.append(entry)
            self.last_routed = entry
            self.self_turn_log[-1]["routed"] = "DECLINE"
            self.self_turn_log[-1]["reply"] = ans
            return [ans]
        return said


DEFAULT_CONFIG161: dict = copy.deepcopy(L138.DEFAULT_CONFIG138)
DEFAULT_CONFIG161["ears"]["stand_in"] = (
    "Loop161Ears = Loop138Ears unchanged "
    "(Loop134Ears teach coverage + F5/M5 fixes + exp-129 "
    "sentence-punctuation strip on teach/correct + exp-113c partial-frame "
    "composer gate on '?' turns) over Loop121Ears over Loop113bEars over "
    "Loop102Ears pre-filter over Loop96Ears = GuardedEars91 over "
    "ChainEars(bench73 template + FakeEars templates)")
DEFAULT_CONFIG161["mouth"]["stand_in"] = (
    "Loop161Mouth = Loop138Mouth unchanged (Loop134Mouth: relation keys "
    "rendered with spaces in replies only, stored keys unchanged)")
DEFAULT_CONFIG161["daemon"]["module"] = "Loop161Daemon (this file)"
DEFAULT_CONFIG161["self"] = {
    "router": "SelfCard161.route (this build; vocab-free intent match, "
              "names read from live state, never baked in)",
    "answerer": "SelfCard161.answer_self over live loop161 state",
    "rule": ("notebook answers always win; notebook-missed turns go to "
             "the self path (card reply on non-DECLINE, HONEST_DECLINE + "
             "'Could you say it another way?' on DECLINE)"),
}


def build_agent161(cfg: dict | None = None) -> Loop161AgentLoop:
    """Build the loop138 agent shape with the loop161 loop class."""
    cfg = dict(DEFAULT_CONFIG161, **(cfg or {}))
    loop = L138.build_agent138(cfg)
    loop.__class__ = Loop161AgentLoop
    loop.self_card = SC161.SelfCard161(loop)
    loop.notes.append("self161: SelfCard161 grounded self card (exp-161)")
    return loop


class Loop161Daemon(L138.Loop138Daemon):
    """Loop138Daemon shape with the loop161 agent inside + 108 exactly-once."""

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
        self.loop = build_agent161(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        self.reconcile_report = D108.boot_reconcile(self)


def run_daemon161(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop161Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 161 loop with self card")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG161 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG161)
        out["thinker"]["module"] = "fable_webfix89_thinking"
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG161)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon161(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent161(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
