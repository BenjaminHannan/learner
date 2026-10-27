#!/usr/bin/env python3
"""Experiment 113d -- registered single-change follow-up to exp 113c.

Diagnosis (design doc 113c, artifacts/fable-bench113c-20260922/, scripts/
fable_loop113c_agent.py; director re-ran red team 124's 62 sealed cases,
artifacts/fable-redteam124-20260922/fable_redteam124_cases.json, through
loop113c): the composer-prefix answers are gone, but when 113c delegates
to the loop102 chain, loop102's Bench73Stage still answers a 2-hop PREFIX
of a longer question -- B5 "Duggan's spouse's country of citizenship is
Spain", Q2 / U1 / V4 "CM Punk's spouse's country of citizenship is
Spain" -- each to a question that names more relations (or a qualifier /
"whose" direction) than the answer consumed. Red team 124 (doc 124) found
loop102 does this in 16 cases.

THE ONE CHANGE (question side only; teach path and everything else
byte-identical to loop113c):

  113c's consume-every-relation-phrase/qualifier rule
  (fable_loop113c_agent.frame_consumes_question, unchanged and reused
  here) is applied to the loop102 fallback path's question answering too.
  Every fallback "ask" action whose frame leaves relation words or
  qualifiers of the question unconsumed is replaced with the honest
  abstain (the loop's own clarify text, L113.CHAIN_MISS_TEXT) instead of
  the prefix answer. This covers Bench73Stage and any other 2-hop
  question path reached through the fallback, because the guard sits on
  the fallback's returned actions, not inside any one stage. Composer
  routing, compound-guard, non-explicit clarify, hearsay screen, and the
  teach path are unchanged from 113c.

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench113d-20260922/loop113d-config.json
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
import fable_loop113_agent as L113  # noqa: E402 (CHAIN_MISS_TEXT, read-only)
import fable_loop113b_agent as L113B  # noqa: E402 (loop shape, read-only)
import fable_loop113c_agent as L113C  # noqa: E402 (router + gate, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)

# Reuse 113c's gate byte-for-byte: a frame is usable only if it consumes
# every relation phrase / qualifier in the question.
frame_consumes_question = L113C.frame_consumes_question


class Loop113dEars(L113C.Loop113cEars):
    """Loop113cEars + the consumption gate on the loop102 fallback path.

    hear() is 113c routing exactly, except every delegation to the loop102
    chain goes through _fallback_guarded(): after the exact loop102 chain
    runs, any returned "ask" whose relations fail frame_consumes_question()
    on the asked turn is replaced with the honest abstain
    (L113.CHAIN_MISS_TEXT clarify -- the loop's own "I didn't understand"
    form, which every abstain scorer counts). Asks that consume the
    question, and all non-ask actions (teach / correct / forget2 /
    clarify), pass through byte-identical. Non-"?" turns inherit 113c
    behaviour.
    """

    name = "loop113d-fallback-partial-frame"

    def _fallback_guarded(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        actions = L102.Loop102Ears.hear(self, turn)
        if text and text.rstrip().endswith("?") and self.nb is not None:
            triples = L90.notebook_triples(self.nb)
            for act in actions:
                if act.get("act") != "ask":
                    continue
                rels = list(act.get("relations") or (
                    [act["relation"]] if act.get("relation") else []))
                if not rels:
                    continue
                if not frame_consumes_question(text, rels, triples):
                    self.last_stage, self.last_score = (
                        "loop113d-fallback-partial", 1.0)
                    return [{"act": "clarify",
                             "text": L113.CHAIN_MISS_TEXT}]
        return actions

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if text and text.rstrip().endswith("?"):
            if L102.is_hearsay(text):  # F1 preserved on questions
                self.last_stage, self.last_score = "loop113d-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            if self.nb is None:
                return self._delegate(turn)
            triples = L90.notebook_triples(self.nb)
            frame = B92.compose_n_hop(text, triples)
            if frame is not None:
                if frame_consumes_question(text, list(frame[1]), triples):
                    hit = L113.compound_subject_hit(triples, frame[0],
                                                    list(frame[1]))
                    if hit is None:
                        self.last_stage, self.last_score = (
                            "loop113d-nhop", 1.0)
                        return [{"act": "ask", "name": frame[0],
                                 "relations": list(frame[1]),
                                 "stage": "loop113d"}]
                    self.last_stage, self.last_score = (
                        "loop113d-compound-guard", 1.0)
                    return [{"act": "clarify",
                             "text": L113.CHAIN_MISS_TEXT}]
                # Partial/prefix N-hop frame -> guarded fallback (one change
                # vs 113c: the fallback itself is now consumption-gated).
                self.last_stage, self.last_score = (
                    "loop113d-partial", 1.0)
                return self._fallback_guarded(turn)
            frame2 = B73.compose_question(text, triples)
            if frame2 is not None:
                if (L113.is_explicit_question(text)
                        and frame_consumes_question(text, list(frame2[1]),
                                                    triples)):
                    self.last_stage, self.last_score = (
                        "loop113d-explicit", 1.0)
                    return [{"act": "ask", "name": frame2[0],
                             "relations": list(frame2[1]),
                             "stage": "loop113d"}]
                if not L113.is_explicit_question(text):
                    # Non-explicit 2-hop frame: the truncation shape.
                    self.last_stage, self.last_score = (
                        "loop113d-nonexplicit", 1.0)
                    return [{"act": "clarify",
                             "text": L113.CHAIN_MISS_TEXT}]
                self.last_stage, self.last_score = (
                    "loop113d-partial", 1.0)
                return self._fallback_guarded(turn)
            # Both composers None -> guarded loop102 chain (the one change).
            return self._fallback_guarded(turn)
        return super().hear(turn)


class Loop113dAgentLoop(L113B.Loop113bAgentLoop):
    """Loop113bAgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG113D: dict = copy.deepcopy(L113C.DEFAULT_CONFIG113C)
DEFAULT_CONFIG113D["ears"]["stand_in"] = (
    "Loop113dEars (113c router + 113c consumption gate applied to the "
    "loop102 fallback path too: a fallback ask whose frame leaves relation "
    "words/qualifiers unconsumed becomes the honest abstain instead of a "
    "prefix answer) over Loop102Ears pre-filter over Loop96Ears = "
    "GuardedEars91 over ChainEars(bench73 template + FakeEars templates); "
    "teach path identical to loop102")
DEFAULT_CONFIG113D["daemon"]["module"] = "Loop113dDaemon (this file)"


def build_agent113d(cfg: dict | None = None) -> Loop113dAgentLoop:
    """Build the loop113b agent shape with Loop113dEars on the question side."""
    cfg = dict(DEFAULT_CONFIG113D, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop113dAgentLoop(
        state_dir, ears=Loop113dEars(Loop96Ears(chain)), mouth=mouth,
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


class Loop113dDaemon(L113B.Loop113bDaemon):
    """Loop113bDaemon shape with the loop113d agent inside (mailbox identical)."""

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
        self.loop = build_agent113d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon113d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop113dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113d fallback loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop113c)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG113D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG113D)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG113D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon113d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent113d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
