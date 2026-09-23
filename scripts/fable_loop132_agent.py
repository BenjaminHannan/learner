#!/usr/bin/env python3
"""Experiment 132 -- question-rewriter loop (registered single-change follow-up).

Diagnosis (exp 121 evidence on the sealed bench121 4-hop split: loop121
answers 136, abstains 63, wrong 1 -- 62 of the 63 abstains are the loop's own
"I didn't understand that"): natural MQuAKE-style questions with relative
clauses and inverted order ("... the country that the founder of the company
that produced X calls home?", "Which continent is the country in, where the
director of the performer of X is a citizen?", "In what city, which is the
capital of a country, is ..."), which the N-hop composers (exp 113/113c)
cannot parse into the full chain.

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to loop121, wrapped never edited):

  Loop132Ears(Loop121Ears) runs the exact base path first. When the base
  path ASKS, its actions are returned untouched (so every base-loop correct
  answer stays correct by construction). Only when the base path CLARIFIES
  ("?" turn, notebook bound) is scripts/fable_qrewrite132_.rewrite_question
  consulted: a deterministic rewriter that turns relative-clause / inverted
  multi-hop questions into the canonical nested-possessive form the composers
  already accept ("X's performer's director's country of citizenship's
  continent?"), using only the notebook's own relation vocabulary (relation
  surface phrases already in the code tables; plain software, tiny grammar,
  no model, no downloads). If the rewrite is not certain (any leftover
  content word, ambiguity, failed verification against the unchanged
  composers) the question passes through unchanged -- the base clarify is
  returned verbatim, never a guess. The rewritten turn is then fed through
  the exact base path, so a rewrite can only convert a clarify into an ask,
  never alter an ask.

Base: scripts/fable_loop121_agent.py (existed at build time; subclassed).
If artifacts/fable-bench113d-20260922/ ever gains a PASS it postdates this
build (only PASSMARKS.md exists at build time), so loop121 stands.

No existing file is edited; everything new lives here + fable_qrewrite132_.py.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop132_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench132-20260922/loop132-config.json
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
import fable_qrewrite132 as Q132  # noqa: E402 (this experiment's rewriter)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)


def _is_ask(actions: list[dict]) -> bool:
    return bool(actions) and actions[0].get("act") == "ask"


class Loop132Ears(L121.Loop121Ears):
    """Loop121Ears + deterministic question rewrite on clarified "?" turns.

    hear() on "?" turns (notebook bound): run the exact base path first; an
    ask is returned untouched. Only a clarify consults the rewriter, and the
    rewritten turn goes through the exact base path again -- so the only
    observable change is clarify -> ask on certain rewrites. Non-"?" turns
    inherit loop121 behaviour byte-identical.
    """

    name = "loop132-question-rewriter"

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?") and self.nb is not None:
            base = super().hear(turn)
            if _is_ask(base):
                return base
            try:
                triples = L90.notebook_triples(self.nb)
                newq, _info = Q132.rewrite_question(text, triples)
            except Exception:
                return base
            if newq != text:
                save_stage, save_score = self.last_stage, self.last_score
                try:
                    second = super().hear(newq)
                except Exception:
                    self.last_stage, self.last_score = save_stage, save_score
                    return base
                if _is_ask(second):
                    self.last_stage, self.last_score = (
                        "loop132-rewrite", 1.0)
                    return second
                self.last_stage, self.last_score = save_stage, save_score
            return base
        return super().hear(turn)


class Loop132AgentLoop(L121.Loop121AgentLoop):
    """Loop121AgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG132: dict = copy.deepcopy(L121.DEFAULT_CONFIG121)
DEFAULT_CONFIG132["ears"]["stand_in"] = (
    "Loop132Ears (deterministic relative-clause/inverted question rewriter "
    "to canonical nested-possessive form before the unchanged composers; "
    "asks untouched, clarifies reconsidered once, uncertain rewrites pass "
    "through) over Loop121Ears (teach-pattern coverage) over Loop113bEars "
    "(N-hop router + loop102 fallback) over Loop102Ears pre-filter over "
    "Loop96Ears = GuardedEars91 over ChainEars(bench73 template + FakeEars "
    "templates)")
DEFAULT_CONFIG132["daemon"]["module"] = "Loop132Daemon (this file)"


def build_agent132(cfg: dict | None = None) -> Loop132AgentLoop:
    """Build the loop121 agent shape with Loop132Ears on the question side."""
    cfg = dict(DEFAULT_CONFIG132, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    from fable_fix77_core import (  # noqa: E402 (read-only wrap)
        QualifierAwareReasoner77)
    reasoner = QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4132)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop132AgentLoop(
        state_dir, ears=Loop132Ears(Loop96Ears(chain)), mouth=mouth,
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


class Loop132Daemon(L121.Loop121Daemon):
    """Loop121Daemon shape with the loop132 agent inside (mailbox identical)."""

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
        self.loop = build_agent132(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon132(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop132Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 132 rewrite loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop121)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG132 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG132)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG132)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon132(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent132(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
