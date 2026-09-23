#!/usr/bin/env python3
"""Experiment 149 -- whole-word entity matching in questions (one fix).

Class 5 of exp 143: "What is the capital of Norlandia?" matched the taught
entity "Norland" by substring (``str.find``) and answered "Aldport".

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to the wrapped loop): an entity counts as mentioned only on
word boundaries (case-insensitive as today; trailing possessive "'s" and
trailing punctuation allowed); longer names still win over shorter ones.
Implemented in scripts/fable_wordmatch149_core.py and applied here at import
(process-wide rebinding of the five substring entity-match sites, no file
edited -- the same override pattern loop134 uses for _APOS).

Two variants in this file (separate processes per registered run):
  Variant A (default): Loop149Ears over Loop134Ears (loop134 + wordmatch).
  Variant B: Qrewrite149Ears over Loop132Ears (loop132 + wordmatch).
Variant-B names deliberately avoid the "Loop*Daemon" / "DEFAULT_CONFIG*" /
"build_agent*" prefixes so generic runners (marks123) pick variant A.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop149_agent.py --daemon --dir DIR \\
    --config artifacts/fable-wordmatch149-20260922/loop149-config.json
  (... --variant qrewrite --config .../loop149-qrewrite-config.json)
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
import fable_wordmatch149_core as WM149  # noqa: E402 (this exp's core)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE ONE CHANGE, applied at import (this process only, no file edited).
WM149.apply_wordmatch()


class WordMatchMixin149:
    """Marker mixin: re-asserts the wordmatch patch at bind time."""

    def bind(self, nb):
        WM149.apply_wordmatch()
        assert WM149.is_applied()
        return super().bind(nb)


# -- Variant A: loop134 + wordmatch -----------------------------------------

class Loop149Ears(WordMatchMixin149, L134.Loop134Ears):
    """Loop134Ears with whole-word entity matching (via module patch)."""


class Loop149AgentLoop(L134.Loop134AgentLoop):
    """Loop134AgentLoop (forget2 action included); ears differ only."""


DEFAULT_CONFIG149: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG149["ears"]["stand_in"] = (
    "Loop149Ears (WordMatchMixin149 over Loop134Ears: taught entities count "
    "as mentioned only on word boundaries, case-insensitive, trailing "
    "possessive/punctuation allowed, longer names win; teach coverage and "
    "the loop113b question side otherwise identical to loop134)")
DEFAULT_CONFIG149["daemon"]["module"] = "Loop149Daemon (this file)"


def build_agent149(cfg: dict | None = None) -> Loop149AgentLoop:
    """Build the loop134 agent shape with whole-word entity matching."""
    cfg = dict(DEFAULT_CONFIG149, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L134.Loop134Mouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4149)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop149AgentLoop(
        state_dir, ears=Loop149Ears(Loop96Ears(chain)), mouth=mouth,
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


class Loop149Daemon(L134.Loop134Daemon):
    """Loop134Daemon shape with the loop149 agent inside (mailbox identical)."""

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
        self.loop = build_agent149(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon149(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop149Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


# -- Variant B: loop132 + wordmatch ------------------------------------------

class Qrewrite149Ears(WordMatchMixin149, L132.Loop132Ears):
    """Loop132Ears with whole-word entity matching (composer + rewriter)."""


class Qrewrite149AgentLoop(L132.Loop132AgentLoop):
    """Loop132AgentLoop; ears differ only."""


QREWRITE149_CONFIG: dict = copy.deepcopy(L132.DEFAULT_CONFIG132)
QREWRITE149_CONFIG["ears"]["stand_in"] = (
    "Qrewrite149Ears (WordMatchMixin149 over Loop132Ears: whole-word "
    "entity matching in the composers and the 132 rewriter seed "
    "selection; asks untouched, clarifies reconsidered once, as loop132)")
QREWRITE149_CONFIG["daemon"]["module"] = "Qrewrite149Daemon (this file)"


def build_qrewrite149(cfg: dict | None = None) -> Qrewrite149AgentLoop:
    """Build the loop132 agent shape with whole-word entity matching."""
    cfg = dict(QREWRITE149_CONFIG, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4150)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Qrewrite149AgentLoop(
        state_dir, ears=Qrewrite149Ears(Loop96Ears(chain)), mouth=mouth,
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


class Qrewrite149Daemon(L132.Loop132Daemon):
    """Loop132Daemon shape with the qrewrite149 agent inside."""

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
        self.loop = build_qrewrite149(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_qrewrite149(root, cfg: dict | None = None,
                    idle_seconds: float = 30.0) -> int:
    daemon = Qrewrite149Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 149 wordmatch loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134/132)")
    parser.add_argument("--write-config", default=None,
                        help="write default config to PATH and exit")
    parser.add_argument("--variant", default="149", choices=["149", "qrewrite"],
                        help="149 = loop134+wordmatch; qrewrite = "
                        "loop132+wordmatch")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    base = DEFAULT_CONFIG149 if args.variant == "149" else QREWRITE149_CONFIG

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
        if args.variant == "149":
            return run_daemon149(args.dir, cfg=cfg,
                                 idle_seconds=args.idle_seconds)
        return run_qrewrite149(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = (build_agent149(cfg) if args.variant == "149"
                else build_qrewrite149(cfg))
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
