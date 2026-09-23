#!/usr/bin/env python3
"""Experiment 190b -- ONE CHANGE on the 190 agent: reverse no-match wording.

190 split no-match reverse replies into known-value
("I don't know anyone whose <R> is <V>.") vs unknown-name
("I don't know anyone called <V>."). Director probe: a REVERSE-shaped
question about a value nobody has ("Who lives in Lima?") got the who-is
wording ("...called Lima") even though Lima is a city, not a person.

190b = 190 + reply-text-only change: any reverse question in the closed
190 shapes (E1-E4 parsed by fable_fix190_reverse.parse_reverse190) with
zero stored matches replies "I don't know anyone whose <R> is <V>."
using the relation display name -- whether or not the value is known.
Plain who-is questions about unknown names ("Who is Lima?") do NOT
parse as reverse and keep "I don't know anyone called Lima."

Composition: Loop190bEars(L190.Loop190Ears) overrides hear() only: run
the full 190 stack, and only when it returns a single clarify whose
text is exactly the notebook UNKNOWN_ENTITY sentence
"I don't know anyone called <V>." AND the turn parses as a closed 190
reverse shape, re-emit the clarify with the whose-sentence for the
parsed relation key. Everything else (matches, known no-match,
forward asks, teaches/corrects, 153 frames, traps) passes through
byte-identical. Clarify-only, never writes; notebook events identical
to 190 by construction.

No existing file edited; 190 files only imported.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix190_reverse as R190  # noqa: E402 (parser, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (daemon base, read-only)
import fable_loop190_agent as L190  # noqa: E402 (wrapped stack, read-only)


def _clean_value(text: str) -> str:
    return " ".join(str(text).split()).rstrip("?").rstrip(".").strip()


def _display_rel(rel_key: str) -> str:
    return rel_key.replace("_", " ")


def whose_sentence190b(rel_key: str, value: str) -> str:
    return (f"I don't know anyone whose {_display_rel(rel_key)} is "
            f"{_clean_value(value)}.")


class Reverse190bMixin:
    """Outermost text-only patch over the sealed 190 stack."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        if (not isinstance(actions, list) or len(actions) != 1
                or not isinstance(actions[0], dict)
                or actions[0].get("act") != "clarify"):
            return actions
        text = str(actions[0].get("text", "")).strip()
        if not text.startswith("I don't know anyone called "):
            return actions
        parsed = R190.parse_reverse190(turn)
        if parsed is None:
            return actions
        rel_key, value = parsed
        # Only rewrite when the called-name equals the parsed reverse
        # value (guards against accidental rewrites of who-is replies
        # that merely coincide with a reverse parse).
        called_name = _clean_value(
            text[len("I don't know anyone called "):])
        if called_name != _clean_value(value):
            return actions
        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
            "loop190b-reverse-nomatch", 1.0)
        return [{"act": "clarify",
                 "text": whose_sentence190b(rel_key, value)}]


class Loop190bEars(Reverse190bMixin, L190.Loop190Ears):
    """Loop190Ears + outermost 190b no-match rewording."""

    name = "loop190b-reverse-nomatch"


class Loop190bAgentLoop(L190.Loop190AgentLoop):
    """Loop190AgentLoop unchanged (no _act/turn override)."""


DEFAULT_CONFIG190B: dict = copy.deepcopy(L190.DEFAULT_CONFIG190)
DEFAULT_CONFIG190B["ears"]["stand_in"] = (
    "Loop190bEars (loop190 stack + outermost 190b text-only stage: "
    "unknown-value reverse no-match reworded to whose-sentence; "
    "who-is unknown unchanged; clarify-only, never writes)")
DEFAULT_CONFIG190B["daemon"]["module"] = "Loop190bDaemon (this file)"


def build_agent190b(cfg: dict | None = None) -> Loop190bAgentLoop:
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    import fable_daemon108_run as D108  # noqa: E402 (read-only)
    import fable_daemon141_settle as D141  # noqa: E402 (read-only)
    import fable_doubt146b_store as D146B  # noqa: E402 (read-only)
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    import fable_loop138_agent as L138  # noqa: E402 (read-only)
    import fable_loop138b_agent as L138b  # noqa: E402 (read-only)
    import fable_loop138d_agent as L138d  # noqa: E402 (read-only)
    from fable_perf142_index import (  # noqa: E402 (read-only)
        patch_chain142, patch_loop121_teach)
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    import fable_agent_loop as A  # noqa: E402 (read-only)
    import fable_loop134_agent as L134  # noqa: E402 (read-only)
    import fable_wordmatch149_core as WM149  # noqa: E402 (read-only)
    WM149.apply_wordmatch()
    A._APOS = L134._APOS_SHOUTED_134
    cfg = dict(DEFAULT_CONFIG190B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop190bEars(Loop96Ears(chain))
    loop = Loop190bAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    patch_chain142(chain)
    patch_loop121_teach(inner_ears)
    thinker, thinker_module = L90.build_thinker(loop.nb)
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
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep190b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop190b: loop190 + text-only reverse no-match "
                      "reword (unknown-value reverse -> whose-sentence; "
                      "who-is unchanged; clarify-only)")
    return loop


class Loop190bDaemon(L138G.Loop138gDaemon):
    """Loop138gDaemon shape with the 190b agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = 30.0) -> None:
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        import fable_daemon141_settle as D141  # noqa: E402 (read-only)
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
        self.loop = build_agent190b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon190b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop190bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 190b reverse loop")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG190B)
        import fable_loop90_agent as L90w  # noqa: E402 (read-only)
        out["thinker"]["module"] = L90w.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG190B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon190b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent190b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
