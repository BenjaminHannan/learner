#!/usr/bin/env python3
"""Experiment 137e -- one hearsay reply (Muse, 2026-09-22).

Base agent: loop137d (`scripts/fable_loop137d_agent.py`,
`artifacts/fable-frame137d-20260922/loop137d-config.json`; design
`design/v3/30-modes/137d-frame-muse.md`; RESULTS
`artifacts/fable-frame137d-20260922/RESULTS.md`, a registered FAIL on
G2/G3 for 7 frozen reply-text checks).

Step-1 facts (asked): the existing hearsay reply HEARSAY_MSG lives at
`scripts/fable_loop102_agent.py:70-71`:
"Do you know that yourself, or did you hear it somewhere? I only save
facts you tell me directly." Loop137d catches sentence-initial hearsay
framings (`scripts/fable_fix137d_frame.py:86-98`, `_HEARSAY`) and
replies with a NEW sealed sentence, while trailing/base hearsay
("Nia's boss is Obi, I heard.") still falls through to the base
pipeline and gets the old HEARSAY_MSG -- so loop137d gives TWO
different hearsay replies (director probe 07:52; 137d RESULTS
diagnosis: 6 cases150 OK->WRONG-REPLY + rt110-T6 OK->BUG, all 7 store
nothing).

THE ONE CHANGE (against loop137d): `Loop137eEars` subclasses
loop137d's ears and, for turns whose 137d frame kind is "hearsay",
returns one clarify carrying the EXISTING HEARSAY_MSG byte-for-byte
(imported read-only from `fable_loop102_agent`, never retyped) instead
of the 137d new sentence. Say-group turns ("say"/"say that" echo +
pretend parenthetical) and every other turn run the unchanged loop137d
pipeline byte-identical (via `super().hear()`).

No loop137d (or any other) file is edited; everything new lives in
this file (+ `scripts/fable_fix137e_*.py`,
`artifacts/fable-frame137e-20260922/`,
`design/v3/30-modes/137e-one-hearsay-reply-muse.md`).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop137e_agent.py --daemon --dir DIR \\
    --config artifacts/fable-frame137e-20260922/loop137e-config.json
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
import fable_fix137d_frame as F137D  # noqa: E402 (frame groups, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG source, read-only)
import fable_loop134_agent as L134  # noqa: E402 (read-only value source)
import fable_loop137b_agent as L137B  # noqa: E402 (read-only base)
import fable_loop137c_agent as L137C  # noqa: E402 (read-only base)
import fable_loop137d_agent as L137D  # noqa: E402 (wrapped base, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Same process-wide overrides as loop137b/loop137c/loop137d (no file edited).
WM149.apply_wordmatch()
A._APOS = L134._APOS_SHOUTED_134

# The one and only hearsay reply: loop102's existing sentence, imported
# (never retyped, never edited).
HEARSAY_MSG_137E = L102.HEARSAY_MSG


class Loop137eEars(L137D.Loop137dEars):
    """Loop137dEars with THE ONE CHANGE: hearsay replies HEARSAY_MSG.

    hear() checks the 137d closed-list hearsay group FIRST; hearsay
    turns return one clarify with the existing HEARSAY_MSG
    byte-for-byte. All other turns (say-group echo + pretend
    parenthetical, 137c hypo guard, base pipeline) run the unchanged
    loop137d path byte-identical via super().hear().
    """

    name = "loop137e-hearsay1"

    def hear(self, turn: str) -> list[dict]:
        if F137D.frame_kind(turn) == "hearsay":
            try:
                self.last_stage, self.last_score = ("loop137e-hearsay", 1.0)
            except AttributeError:
                pass
            return [{"act": "clarify", "text": HEARSAY_MSG_137E}]
        return super().hear(turn)


class Loop137eMouth(L137D.Loop137dMouth):
    """Loop137dMouth unchanged (mouth texts identical to loop137d)."""

    name = "loop137e-mouth"


class Loop137eAgentLoop(L137D.Loop137dAgentLoop):
    """Loop137dAgentLoop shape with the 137e ears (turn/_act inherited)."""

    pass


DEFAULT_CONFIG137E: dict = copy.deepcopy(L137D.DEFAULT_CONFIG137D)
DEFAULT_CONFIG137E["ears"]["stand_in"] = (
    "Loop137eEars (loop137d + one change: closed-list hearsay-group turns "
    "reply the existing loop102 HEARSAY_MSG byte-for-byte "
    "('Do you know that yourself, or did you hear it somewhere? I only "
    "save facts you tell me directly.'); say-group echo + pretend "
    "parenthetical and everything else byte-identical to loop137d)")
DEFAULT_CONFIG137E["mouth"]["stand_in"] = (
    "Loop137eMouth (Loop137dMouth unchanged)")
DEFAULT_CONFIG137E["daemon"]["module"] = "Loop137eDaemon (this file)"


def build_agent137e(cfg: dict | None = None) -> Loop137eAgentLoop:
    """Build the loop137d agent shape with the 137e ears swapped in."""
    cfg = dict(DEFAULT_CONFIG137E, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop137eMouth()
    from fable_loop148b_agent import (  # noqa: E402 (read-only wrap)
        ScreenStatusReasoner148b)
    reasoner = ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop137eAgentLoop(
        state_dir, ears=Loop137eEars(Loop96Ears(chain)), mouth=mouth,
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
    loop.notes.append("sleep137e: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


class Loop137eDaemon(L137D.Loop137dDaemon):
    """Loop137dDaemon shape with the 137e agent inside (settle inherited)."""

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
        self.loop = build_agent137e(agent_cfg)
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


def run_daemon137e(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop137eDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 137e one-hearsay loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop137d)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG137E to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG137E)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG137E)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon137e(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent137e(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
