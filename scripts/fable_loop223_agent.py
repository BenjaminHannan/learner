#!/usr/bin/env python3
"""Experiment 223 -- CAPABILITY QUESTIONS PASS THE NEGATION SCREEN.

Problem (director-verified on loop138i): "What can you do?" gets the fixed
capability sheet, but "What can't you do?" gets the 148 negation clarify,
because the exp-148 question screen runs before the self router, while the
self router already has a CANNOT answer (intent C25, fixed sheet
CAPABILITY_CANNOT in scripts/fable_self99.py).

THE ONE CHANGE (loop138i subclass; no earlier file edited, no router
widening, no new reply text): on a "?" turn that the screen would stop,
first ask the base's own self router -- the same routing call the base
already makes on the notebook-miss path (fable_loop138_agent._route127,
reached via loop138i's MRO: Loop138iAgentLoop -> ... -> Loop138gAgentLoop /
Loop138dAgentLoop turn(), which call L138._route127) -- for its intent; if
that intent is C24 or C25 (capability) AND the turn contains a
second-person word (you, your, yours, yourself), skip the screen so the
turn follows the base's normal self path. Nothing else changes.

Implementation: Loop223Ears.hear mirrors the screen's own gate
(ScreenStatusMixin148b._screen148b_kind: trailing "?", notebook triples as
the taught-mention exemption, S148.trigger_spans, neg-wins) to decide
whether the screen would stop the turn. If it would, route with
L138._route127 (frozen; read-only). On (C24|C25 + second-person) the
super().hear() call runs with S148.trigger_spans temporarily returning no
hits (process-local, try/finally restored), which is exactly the base path
with the screen absent: no tags are produced, so _act / reasoner / mouth
and the turn() self path run byte-identical to an unscreened turn. Every
other turn calls super().hear() untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop223_agent.py --daemon --dir DIR \\
    --config artifacts/fable-cantdo223-20260922/loop223-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_loop138_agent as L138  # noqa: E402 (base router call, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)
import fable_screen148_mixin as S148  # noqa: E402 (148 word list, read-only)

_SECOND_RE = re.compile(r"\b(you|your|yours|yourself)\b", re.IGNORECASE)
_CAPABILITY_INTENTS = frozenset({"C24", "C25"})


def _screen_would_stop(text: str, nb) -> bool:
    """True iff the 148 screen would stop this turn (detection only).

    Mirrors ScreenStatusMixin148b._screen148b_kind verbatim (same "?" gate,
    same notebook-triples exemption, same sealed trigger_spans call). Used
    only to decide whether to consult the router; the screen itself is
    never reimplemented.
    """
    t = " ".join(str(text).split())
    if not t or not t.rstrip().endswith("?") or nb is None:
        return False
    try:
        triples = L138I.L90.notebook_triples(nb)
    except Exception:  # noqa: BLE001 -- fail safe: treat as no screen
        triples = []
    known: list[str] = []
    for subj, _rel, val in triples:
        known.append(str(subj))
        known.append(str(val))
    try:
        hits = S148.trigger_spans(t, known)
    except Exception:  # noqa: BLE001 -- never break the base path
        hits = []
    return bool(hits)


def _self_intent(text: str) -> str:
    """The base's own self-router intent (same call the base makes)."""
    try:
        intent, _info = L138._route127(text)
    except Exception:  # noqa: BLE001 -- fail safe: keep the screen
        return "DECLINE"
    return intent


class Loop223Ears(L138I.Loop138iEars):
    """Loop138iEars + the one capability-negation bypass (this file only)."""

    name = "loop223-cantdo-bypass"

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        text = " ".join(str(turn).split())
        bypass = False
        if _screen_would_stop(text, nb):
            if _SECOND_RE.search(text) is not None:
                if _self_intent(text) in _CAPABILITY_INTENTS:
                    bypass = True
        if not bypass:
            return super().hear(turn)
        real = S148.trigger_spans
        S148.trigger_spans = lambda *a, **k: []  # type: ignore[method-assign]
        try:
            return super().hear(turn)
        finally:
            S148.trigger_spans = real  # type: ignore[method-assign]


class Loop223AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG223: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG223["ears"]["stand_in"] = (
    "Loop223Ears (loop138i stack + 223 gate: a '?' turn the 148 screen "
    "would stop skips the screen iff the base's own route127 intent is "
    "C24/C25 and the turn has a second-person word; else the 138i path "
    "byte-identical)")
DEFAULT_CONFIG223["daemon"]["module"] = "Loop223Daemon (this file)"


def build_agent223(cfg: dict | None = None) -> Loop223AgentLoop:
    """Build the loop138i agent shape with the 223 bypass stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG223, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop223Ears(Loop96Ears(chain))
    loop = Loop223AgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    L138I.patch_chain142(chain)
    L138I.patch_loop121_teach(inner_ears)
    thinker, thinker_module = L138I.L90.build_thinker(loop.nb)
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
    store = L138I.D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    loop._dc166c = {}
    L138I._wrap_relation154e(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138i: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop223: loop138i + capability-negation bypass (C24/"
                      "C25 + second-person skips the 148 screen; no router "
                      "widening, no new reply text)")
    return loop


class Loop223Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 223 agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138I.D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent223(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon223(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop223Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 223 cantdo loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG223 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG223)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG223)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon223(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent223(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
