#!/usr/bin/env python3
"""Experiment 137d -- non-assertive framings never write (WRONG-WRITE class).

Base agent: loop137c (`scripts/fable_loop137c_agent.py`,
`artifacts/fable-hypo137c-20260922/loop137c-config.json`; design
`design/v3/30-modes/137c-hypo-muse.md`).

Step-1 facts: 137c's closed sentence-initial marker list lives at
`scripts/fable_fix137c_hypo.py:48-60` (`_MARKERS`, longest-first). The
path that produced the Supposedly junk: on loop137c "Supposedly Kim's
boss is Lee." is not hypothetical, so `Loop137cEars.hear` falls through
at `scripts/fable_loop137c_agent.py:84` (`return super().hear(turn)`)
into the unchanged loop137b/138b pipeline, which parses "Supposedly
Kim" as a possessive subject and SAVES `[Supposedly Kim,boss,Lee]`
(live-verified pre-seal). "Say Kim's boss is Lee." saves
`[Kim,boss,Lee]` on loop137c (only "say that" is a 137c marker).

THE ONE CHANGE: `Loop137dEars` subclasses loop137c's ears and checks
`fable_fix137d_frame.frame_kind(turn)` FIRST, before any panel read
(before the unchanged loop137c pipeline runs). Say-group turns
("say"/"say that", sentence-initial, same filler/punctuation/case
rules as 137c) return one clarify carrying `say_reply(turn)` (the
sentence echoed without the marker + the sealed parenthetical);
hearsay-group turns (supposedly/apparently/allegedly/reportedly/rumor
(or rumour) has it/I heard (that)/they say (that)/people say) return
one clarify carrying the exact sealed hearsay sentence. The normal
`_act`/mouth path renders either verbatim with zero writes, zero
routing, and later questions answer only from real saved facts.
Everything else falls through to `super().hear()` byte-identical
("say that" alone moves from the 137c pretend reply to the say echo
reply by design; never writes either way).

No loop137c (or any other) file is edited; everything new lives in
this file (+ `scripts/fable_fix137d_*.py`,
`artifacts/fable-frame137d-20260922/`,
`design/v3/30-modes/137d-frame-muse.md`).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop137d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-frame137d-20260922/loop137d-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + thresholds, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_fix137d_frame as F137D  # noqa: E402 (this exp: closed groups)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only value source)
import fable_loop137b_agent as L137B  # noqa: E402 (read-only base)
import fable_loop137c_agent as L137C  # noqa: E402 (wrapped base, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Same process-wide overrides as loop137b/loop137c (no file edited).
WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134


class Loop137dEars(L137C.Loop137cEars):
    """Loop137cEars with THE ONE CHANGE: 137d frame guard first.

    hear() checks the closed-list say/hearsay groups FIRST (before the
    unchanged loop137c hypo guard + pipeline); framed turns return one
    clarify with the exact sealed reply. All other turns run the
    unchanged loop137c pipeline byte-identical.
    """

    name = "loop137d-frame"

    def hear(self, turn: str) -> list[dict]:
        kind = F137D.frame_kind(turn)
        if kind == "say":
            try:
                self.last_stage, self.last_score = ("loop137d-say", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": F137D.say_reply(turn)}]
        if kind == "hearsay":
            try:
                self.last_stage, self.last_score = ("loop137d-hearsay", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": F137D.HEARSAY_REPLY}]
        return super().hear(turn)


class Loop137dMouth(L137C.Loop137cMouth):
    """Loop137cMouth unchanged (mouth texts identical to loop137c)."""

    name = "loop137d-mouth"


class Loop137dAgentLoop(L137C.Loop137cAgentLoop):
    """Loop137cAgentLoop shape with the 137d ears (turn/_act inherited)."""

    pass


DEFAULT_CONFIG137D: dict = copy.deepcopy(L137C.DEFAULT_CONFIG137C)
DEFAULT_CONFIG137D["ears"]["stand_in"] = (
    "Loop137dEars (loop137c + 137d frame guard: sentence-initial "
    "closed-list say-group say/say that (echo + pretend parenthetical) "
    "and hearsay-group supposedly/apparently/allegedly/reportedly/rumor "
    "has it/rumour has it/I heard/I heard that/they say/they say "
    "that/people say (exact hearsay sentence), after optional ok/so/and "
    "fillers, never write; everything else byte-identical to loop137c)")
DEFAULT_CONFIG137D["mouth"]["stand_in"] = (
    "Loop137dMouth (Loop137cMouth unchanged)")
DEFAULT_CONFIG137D["daemon"]["module"] = "Loop137dDaemon (this file)"


def build_agent137d(cfg: dict | None = None) -> Loop137dAgentLoop:
    """Build the loop137c agent shape with the 137d ears swapped in."""
    cfg = dict(DEFAULT_CONFIG137D, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop137dMouth()
    from fable_loop148b_agent import (  # noqa: E402 (read-only wrap)
        ScreenStatusReasoner148b)
    reasoner = ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop137dAgentLoop(
        state_dir, ears=Loop137dEars(Loop96Ears(chain)), mouth=mouth,
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
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep137d: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


class Loop137dDaemon(L137C.Loop137cDaemon):
    """Loop137cDaemon shape with the 137d agent inside (settle inherited)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        self.cfg = dict(cfg or {})
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
        self.loop = build_agent137d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic-write client rule: write tmp in the same dir, then rename."""
    import os as _os
    tmp = Path(str(path) + ".tmp%d" % _os.getpid())
    tmp.write_text(text, encoding="utf-8")
    _os.replace(tmp, path)


def run_daemon137d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop137dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 137d frame loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop137c)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG137D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG137D)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG137D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon137d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent137d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
