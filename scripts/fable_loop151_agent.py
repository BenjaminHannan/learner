#!/usr/bin/env python3
"""Experiment 151 -- no-question-mark fix (one single-change fix).

Director probe: after "The capital of Peru is Lima",
"What is the capital of peru?" answers but "What is the capital of Peru"
(no "?"), "what is the capital of peru", "who is jo ng married to",
"whats jo ng's country of citizenship", "Where is Jo Ng a citizen of"
all reply "I didn't understand that." Phone typists skip "?".

Question-vs-statement decision (written down, read-only, never edited):
  scripts/fable_loop121_agent.py:175 -- Loop121Ears.hear: a turn ending in
    "?" takes the question side (exact loop113b); anything else takes the
    teach path. THIS is where the loop decides question vs statement.
  scripts/fable_loop113b_agent.py:70 -- Loop113bEars.hear: "?" turns run
    the N-hop router; non-"?" turns delegate to the loop102 chain.
  scripts/fable_loop132_agent.py:83 -- Loop132Ears: the 132 rewriter only
    consults clarified "?" turns.
  scripts/fable_loop102_agent.py:290 -- F4 qualifier strip never on "?".

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to the wrapped loop): a message containing NO "?" at all is
fed through the exact base path as its byte-exact "?" twin (collapsed
whitespace, trailing phone-typing "." / "!" stripped, "?" appended) when
(a) its first word after optional openers is a sealed question word /
auxiliary and (b) the existing teach parser rejects it
(see scripts/fable_qmark151_core.py for the sealed word list + predicate).
Anything else passes through untouched, so a rewrite can only convert a
clarify/teach-path miss into the "?"-twin reply, never alter a "?" reply.

Two variants in this file (separate processes per registered run):
  Variant A (default): Loop151Ears over Loop134Ears (loop134 + qmark).
  Variant B: Qmark151Ears over Loop132Ears + wordmatch149 re-applied at
    bind (loop132 + wordmatch149 + qmark; the loop132+149 config shape).
Variant-B names deliberately avoid the "Loop*Daemon" / "DEFAULT_CONFIG*" /
"build_agent*" prefixes so generic runners (marks123) pick variant A.
No existing file is edited; subclass/wrap only.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop151_agent.py --daemon --dir DIR \\
    --config artifacts/fable-qmark151-20260922/loop151-config.json
  (... --variant qrewrite --config .../loop151-qrewrite-config.json)
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

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook triples, read-only)
import fable_loop121_agent as L121  # noqa: E402 (wrapped base, read-only)
import fable_loop132_agent as L132  # noqa: E402 (wrapped base, read-only)
import fable_loop134_agent as L134  # noqa: E402 (wrapped base, read-only)
import fable_qmark151_core as Q151  # noqa: E402 (this exp's core)
import fable_wordmatch149_core as WM149  # noqa: E402 (variant B only; inert)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)


class QMarkMixin151:
    """THE ONE CHANGE: no-"?" question-shaped turns take the "?" path."""

    name = "loop151-no-question-mark"

    def hear(self, turn: str) -> list[dict]:
        if Q151.should_rewrite_151(turn):
            twin = Q151.with_question_mark_151(turn)
            save_stage = getattr(self, "last_stage", "")
            save_score = getattr(self, "last_score", 0.0)
            try:
                out = super().hear(twin)  # type: ignore[misc]
            except Exception:
                self.last_stage, self.last_score = save_stage, save_score
                raise
            try:
                self.last_stage = f"loop151-qmark+{self.last_stage}"
            except Exception:  # noqa: BLE001 -- tag is cosmetic only
                pass
            return out
        return super().hear(turn)  # type: ignore[misc]


class WordMatchBind151:
    """Variant-B only: re-assert the 149 whole-word patch at bind time."""

    def bind(self, nb):
        WM149.apply_wordmatch()
        assert WM149.is_applied()
        return super().bind(nb)


# -- Variant A: loop134 + qmark ---------------------------------------------

class Loop151Ears(QMarkMixin151, L134.Loop134Ears):
    """Loop134Ears with the no-"?" question fix layered by MRO."""


class Loop151AgentLoop(L134.Loop134AgentLoop):
    """Loop134AgentLoop (forget2 action included); ears differ only."""


DEFAULT_CONFIG151: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG151["ears"]["stand_in"] = (
    "Loop151Ears (QMarkMixin151 over Loop134Ears: a message with no '?' "
    "whose first word after openers hey/hi/ok/so/and/um is a sealed "
    "question word/auxiliary and which the teach parser rejects is fed "
    "through the exact base path as its byte-exact '?' twin; all other "
    "turns byte-identical to loop134)")
DEFAULT_CONFIG151["daemon"]["module"] = "Loop151Daemon (this file)"


def build_agent151(cfg: dict | None = None) -> Loop151AgentLoop:
    """Build the loop134 agent shape with the no-"?" fix swapped in."""
    cfg = dict(DEFAULT_CONFIG151, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L134.Loop134Mouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4151)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop151AgentLoop(
        state_dir, ears=Loop151Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    return loop


class Loop151Daemon(L134.Loop134Daemon):
    """Loop134Daemon shape with the loop151 agent inside (mailbox identical)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent151(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon151(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop151Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


# -- Variant B: loop132 + wordmatch149 + qmark -------------------------------

class Qmark151Ears(QMarkMixin151, WordMatchBind151, L132.Loop132Ears):
    """Loop132Ears + whole-word entity matching + the no-"?" fix."""


class Qmark151AgentLoop(L132.Loop132AgentLoop):
    """Loop132AgentLoop; ears differ only."""


QMARK151_CONFIG: dict = copy.deepcopy(L132.DEFAULT_CONFIG132)
QMARK151_CONFIG["ears"]["stand_in"] = (
    "Qmark151Ears (QMarkMixin151 over WordMatchBind151 over Loop132Ears: "
    "whole-word entity matching in the composers and the 132 rewriter "
    "seed selection as loop132+149, plus the no-'?' question fix; asks "
    "untouched, clarifies reconsidered once, as loop132)")
QMARK151_CONFIG["daemon"]["module"] = "Qmark151Daemon (this file)"


def build_qmark151(cfg: dict | None = None) -> Qmark151AgentLoop:
    """Build the loop132+149 agent shape with the no-"?" fix swapped in."""
    cfg = dict(QMARK151_CONFIG, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4152)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Qmark151AgentLoop(
        state_dir, ears=Qmark151Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    return loop


class Qmark151Daemon(L132.Loop132Daemon):
    """Loop132Daemon shape with the qmark151 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_qmark151(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_qmark151(root, cfg: dict | None = None,
                 idle_seconds: float = 30.0) -> int:
    daemon = Qmark151Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 151 no-'?'-mark loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134/132)")
    parser.add_argument("--write-config", default=None,
                        help="write default config to PATH and exit")
    parser.add_argument("--variant", default="151", choices=["151", "qrewrite"],
                        help="151 = loop134+qmark; qrewrite = "
                        "loop132+wordmatch149+qmark")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    base = DEFAULT_CONFIG151 if args.variant == "151" else QMARK151_CONFIG

    if args.write_config:
        out = copy.deepcopy(base)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(base)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        if args.variant == "151":
            return run_daemon151(args.dir, cfg=cfg,
                                 idle_seconds=args.idle_seconds)
        return run_qmark151(args.dir, cfg=cfg,
                            idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = (build_agent151(cfg) if args.variant == "151"
                else build_qmark151(cfg))
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
