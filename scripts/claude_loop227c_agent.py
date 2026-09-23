#!/usr/bin/env python3
"""Experiment 227c -- WIDER IDENTITY MATCHING (Claude/Opus).

loop227c = loop227b + ONE change: the identity gate in the notebook-miss
branch also tries the widened matcher scripts/claude_identity227c.py
(contractions, missing "?", trailing/leading fillers, casual synonyms,
plus two new intents NAMECHECK "Is your name X?" and RENAME "Your name is
X." / "I'll call you X.") when the untouched 227 exact-template gate does
not match. Order inside the miss branch: 227 gate (with 227b's
Premonition NAME text) -> 227c gate -> loop138i route127 self path /
DECLINE verbatim. Notebook answers always win (the gate is inside the miss
branch); the gate never writes (reply-only).

New file only; loop227/loop227b/fable_identity227 are wrapped read-only.
turn() is the 227 body (scripts/fable_loop227_agent.py Loop227AgentLoop.turn)
with the gate extended; everything else is inherited.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop227c_agent.py --daemon --dir DIR \\
    --config artifacts/claude-identity227c-20260922/loop227c-config.json
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

import claude_identity227c as C227C  # noqa: E402 (this exp, one change)
import claude_loop227b_agent as L227B  # noqa: E402 (wrapped, read-only)
import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_fix166_me as M166  # noqa: E402 (read-only)
import fable_fix168_ground as G168  # noqa: E402 (read-only)
import fable_identity227 as F227  # noqa: E402 (read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only)
import fable_loop138_agent as L138  # noqa: E402 (read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def gate227c(text: str) -> tuple[str, str] | None:
    """227 exact gate (227b NAME text) first, then the widened 227c gate."""
    hit = F227.identity_answer(text)
    if hit is not None:
        intent, ans = hit
        if intent == "NAME":
            ans = L227B.NAME_227B
        return "IDENTITY-" + intent, ans
    hit = C227C.identity_answer227c(text)
    if hit is not None:
        return "IDENTITY227C-" + hit[0], hit[1]
    return None


class Loop227cAgentLoop(L227B.Loop227bAgentLoop):
    """Loop227bAgentLoop with the widened identity gate in turn()."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
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
            # [227c] identity gate: 227 exact (227b text), then widened.
            hit = gate227c(text)
            if hit is not None:
                intent, ans = hit
                entry = {"n": n, "text": text, "intent": intent,
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                return [ans]
            intent, info = L138._route127(text)
            if intent != "DECLINE":
                ans = G168.grounded_self_answer(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                out = [ans]
                if (M166.USER_KEY not in str(text)
                        and any(M166.USER_KEY in line for line in out)):
                    out = [L138H.Loop138hAgentLoop._scrub_user_key(line)
                           for line in out]
                return out
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
        if (M166.USER_KEY not in str(text)
                and any(M166.USER_KEY in line for line in said)):
            said = [L138H.Loop138hAgentLoop._scrub_user_key(line)
                    for line in said]
        return said


DEFAULT_CONFIG227C: dict = copy.deepcopy(L227B.DEFAULT_CONFIG227B)
DEFAULT_CONFIG227C["ears"]["stand_in"] = (
    "Loop227cAgentLoop (loop227b + widened identity matching)")
DEFAULT_CONFIG227C["daemon"]["module"] = "Loop227cDaemon (this file)"
DEFAULT_CONFIG227C["self"] = dict(L227B.DEFAULT_CONFIG227B.get("self", {}))
DEFAULT_CONFIG227C["self"]["rule227c"] = (
    "after the 227 exact gate misses, the widened 227c matcher serves the "
    "sheet (contractions, no '?', fillers, synonyms) plus NAMECHECK and "
    "RENAME; reply-only, 0 writes")


def build_agent227c(cfg: dict | None = None) -> Loop227cAgentLoop:
    """build_agent227b (read-only) with the loop's class set to 227c."""
    cfg = dict(DEFAULT_CONFIG227C, **(cfg or {}))
    loop = L227B.build_agent227b(cfg)
    loop.__class__ = Loop227cAgentLoop
    loop.notes.append("loop227c: loop227b + widened identity matching")
    return loop


class Loop227cDaemon(L227B.Loop227bDaemon):
    """Loop227bDaemon shape with the 227c agent inside."""

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
        self.loop = build_agent227c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon227c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop227cDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 227c identity agent")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG227C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG227C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon227c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent227c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
