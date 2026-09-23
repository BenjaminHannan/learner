#!/usr/bin/env python3
"""Experiment 148 -- question screen for meaning-changing words (registered).

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to the wrapped base, subclassed never edited):

  QuestionScreenMixin148.hear runs FIRST on "?" turns (notebook bound).
  It strips taught entity/value mentions (live notebook triples) and scans
  the remainder for the sealed trigger list (scripts/fable_screen148_mixin.py:
  negation not/never/n't/"no one"/nobody/none; time: 4-digit year, "as of",
  before/after/formerly/originally/"used to"/currently). On a hit it returns
  a short honest clarify and no composer/lookup ever runs. Statements
  (non-"?" turns) inherit the base byte-identical. When the base path ASKS,
  an unscreened question is returned untouched, so every base correct answer
  stays correct by construction.

Two lineages share the mixin:
  Loop148Ears134 (QuestionScreenMixin148 over Loop134Ears) -- shipped arm.
  Loop148Ears132 (QuestionScreenMixin148 over Loop132Ears) -- Q1 arm, the
    loop132 red-team target (exp 143) plus the screen.

No existing file is edited; everything new lives here + fable_screen148_mixin.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148_agent.py --daemon --dir DIR \\
    --config artifacts/fable-screen148-20260922/loop148-config.json
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
import fable_loop121_agent as L121  # noqa: E402 (daemon shape, read-only)
import fable_loop132_agent as L132  # noqa: E402 (Q1 base, read-only)
import fable_loop134_agent as L134  # noqa: E402 (shipped base, read-only)
import fable_screen148_mixin as S148  # noqa: E402 (this experiment's screen)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)


class QuestionScreenMixin148:
    """Screen "?" turns for meaning-changing words before any composer runs."""

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?") and self.nb is not None:
            try:
                triples = L90.notebook_triples(self.nb)
            except Exception:  # noqa: BLE001 -- fail safe: screen unexempted
                triples = []
            known: list[str] = []
            for subj, _rel, val in triples:
                known.append(str(subj))
                known.append(str(val))
            try:
                hits = S148.trigger_spans(text, known)
            except Exception:  # noqa: BLE001 -- never break the base path
                hits = []
            if hits:
                kinds = {k for k, _ in hits}
                msg = (S148.NEG_MSG if "neg" in kinds else S148.TIME_MSG)
                stage = ("loop148-screen-neg" if "neg" in kinds
                         else "loop148-screen-time")
                self.last_stage, self.last_score = stage, 1.0
                return [{"act": "clarify", "text": msg}]
        return super().hear(turn)


class Loop148Ears134(QuestionScreenMixin148, L134.Loop134Ears):
    """Loop134Ears + the 148 question screen (shipped arm)."""

    name = "loop148-question-screen-on-134"


class Loop148Ears132(QuestionScreenMixin148, L132.Loop132Ears):
    """Loop132Ears + the 148 question screen (Q1 red-team arm)."""

    name = "loop148-question-screen-on-132"


class Loop148AgentLoop(L134.Loop134AgentLoop):
    """Loop134AgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG148: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG148["ears"]["stand_in"] = (
    "Loop148Ears134 (QuestionScreenMixin148: sealed negation/time word "
    "screen with taught-mention exemption before the unchanged composers; "
    "statements untouched) over " + str(
        L134.DEFAULT_CONFIG134["ears"]["stand_in"]))
DEFAULT_CONFIG148["daemon"]["module"] = "Loop148Daemon (this file)"


def build_agent148(cfg: dict | None = None) -> Loop148AgentLoop:
    """Build the loop134 agent shape with the 148 screen on the question side."""
    cfg = dict(DEFAULT_CONFIG148, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L134.Loop134Mouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4148)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop148AgentLoop(
        state_dir, ears=Loop148Ears134(Loop96Ears(chain)), mouth=mouth,
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


def build_agent148_on132(cfg: dict | None = None):
    """Build the loop132 agent shape with the 148 screen (Q1 arm)."""
    cfg = dict(copy.deepcopy(L132.DEFAULT_CONFIG132), **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4148)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = L132.Loop132AgentLoop(
        state_dir, ears=Loop148Ears132(Loop96Ears(chain)), mouth=mouth,
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


class _DaemonBase148(L121.Loop121Daemon):
    """Loop121Daemon mailbox shape with a 148 agent inside."""

    _builder = staticmethod(build_agent148)

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
        self.loop = self._builder(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


class Loop148Daemon(_DaemonBase148):
    """134-lineage daemon (shipped arm)."""

    _builder = staticmethod(build_agent148)


class Loop148Daemon132(_DaemonBase148):
    """132-lineage daemon (Q1 red-team arm)."""

    _builder = staticmethod(build_agent148_on132)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 148 screen loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG148 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG148)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG148)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop148Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent148(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
