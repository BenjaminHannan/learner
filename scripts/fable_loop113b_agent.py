#!/usr/bin/env python3
"""Experiment 113b -- registered single-change follow-up to exp 113.

Diagnosis from 113 (design doc 113, artifact fable-bench113-20260922):
Loop113Ears reroutes EVERY "?" turn to the N-hop composers; on ordinary
possessive questions ("Who is Forget's city?") both composers return None
and v1 flatly clarifies, so loop102's own FakeStage path never runs
(P2 16 OK->BUG, L6 0/200, L5-Z1 47/60).

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to loop113, which is byte-identical to loop102 off "?" turns):

  Loop113bEars(Loop113Ears) keeps v1 routing exactly, except when BOTH
  composers return None (no n-hop frame AND no 2-hop frame) it delegates to
  the exact loop102 chain (Loop102Ears.hear -- hearsay/forget/correction/
  qualifier pre-filter + inner loop96 guarded chain + FakeStage). Flat
  clarify is kept ONLY for compound-guard hits and non-explicit 2-hop
  frames (the truncation shape 113 diagnosed).

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench113b-20260922/loop113b-config.json
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
import fable_bench73_english_arm as B73  # noqa: E402 (2-hop composer, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (N-hop composer, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop102_agent as L102  # noqa: E402 (fallback chain, read-only)
import fable_loop113_agent as L113  # noqa: E402 (v1 routing, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)


class Loop113bEars(L113.Loop113Ears):
    """Loop113Ears + fallback to the exact loop102 chain on double-None.

    hear() phases on "?" turns: F1 hearsay screen first (unchanged); then
    both composers are consulted on the notebook triples. N-hop frame ->
    ask unless the compound-subject guard fires (flat clarify, unchanged).
    2-hop frame + explicit single-hop/structural probe -> ask (unchanged);
    2-hop frame + non-explicit shape -> flat clarify (truncation shape,
    unchanged). BOTH None -> the exact loop102 chain
    (Loop102Ears.hear on this same instance: same nb binding, same inner
    loop96 chain, same FakeStage path loop102 used). Non-"?" turns inherit
    v1 behaviour, which already delegates byte-identical to loop102.
    """

    name = "loop113b-nhop-fallback"

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            if L102.is_hearsay(text):  # F1 preserved on questions
                self.last_stage, self.last_score = "loop113b-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            if self.nb is None:
                return self._delegate(turn)
            triples = L90.notebook_triples(self.nb)
            frame = B92.compose_n_hop(text, triples)
            if frame is not None:
                hit = L113.compound_subject_hit(triples, frame[0],
                                                list(frame[1]))
                if hit is None:
                    self.last_stage, self.last_score = "loop113b-nhop", 1.0
                    return [{"act": "ask", "name": frame[0],
                             "relations": list(frame[1]),
                             "stage": "loop113b"}]
                self.last_stage, self.last_score = (
                    "loop113b-compound-guard", 1.0)
                return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
            frame2 = B73.compose_question(text, triples)
            if frame2 is not None:
                if L113.is_explicit_question(text):
                    self.last_stage, self.last_score = (
                        "loop113b-explicit", 1.0)
                    return [{"act": "ask", "name": frame2[0],
                             "relations": list(frame2[1]),
                             "stage": "loop113b"}]
                # Non-explicit 2-hop frame: the truncation shape -- clarify.
                self.last_stage, self.last_score = (
                    "loop113b-nonexplicit", 1.0)
                return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
            # THE ONE CHANGE: both composers None -> exact loop102 chain.
            return L102.Loop102Ears.hear(self, turn)
        return super().hear(turn)


class Loop113bAgentLoop(L113.Loop113AgentLoop):
    """Loop113AgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG113B: dict = copy.deepcopy(L113.DEFAULT_CONFIG113)
DEFAULT_CONFIG113B["ears"]["stand_in"] = (
    "Loop113bEars (v1 N-hop router + fallback to the exact loop102 chain "
    "when both composers return None; flat clarify kept only for "
    "compound-guard hits and non-explicit 2-hop frames) over "
    "Loop102Ears pre-filter over Loop96Ears = GuardedEars91 over "
    "ChainEars(bench73 template + FakeEars templates); teach path identical "
    "to loop102")
DEFAULT_CONFIG113B["daemon"]["module"] = "Loop113bDaemon (this file)"


def build_agent113b(cfg: dict | None = None) -> Loop113bAgentLoop:
    """Build the loop113 agent shape with Loop113bEars on the question side."""
    cfg = dict(DEFAULT_CONFIG113B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop113bAgentLoop(
        state_dir, ears=Loop113bEars(Loop96Ears(chain)), mouth=mouth,
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


class Loop113bDaemon(L113.Loop113Daemon):
    """Loop113Daemon shape with the loop113b agent inside (mailbox identical)."""

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
        self.loop = build_agent113b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon113b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop113bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113b fallback loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop113)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG113B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG113B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG113B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon113b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent113b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
