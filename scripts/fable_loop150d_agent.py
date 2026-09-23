#!/usr/bin/env python3
"""Experiment 150d -- hedge words are case-sensitive (mixin on loop138b).

loop150d = loop138b + THE ONE CHANGE: exp-150's hedge list matches
case-sensitively on its content word (scripts/fable_fix150d_subjectguard.py).
"I Believe I Can Fly" / "I Think We're Alone Now" / "Maybe Tomorrow" store
as names; "I believe Kip ..." / "maybe Kip ..." / "Maybe Kip Dune" /
"Maybe, Kip ..." / whole-message ALL-CAPS stay refused.

Shape: subclass of loop138b (no loop138b/loop138 file edited). The 150d
screen is applied (a) explicitly in the subclass hear/_act via the 150d
guard module, and (b) process-wide at import by repointing
S150.screen_subject_150 (covers the inherited 137/144-upgrade + _act paths
that reference S150 directly -- the same process-wide override pattern
loop138b itself uses for WM149/_APOS; this process only, no file edited).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop150d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-hedgecase150d-20260922/loop150d-config.json
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

import fable_fix137_names as F137  # noqa: E402 (possessive parse, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (lists+replies, read-only)
import fable_fix150d_subjectguard as S150d  # noqa: E402 (THE ONE CHANGE)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)

# THE ONE CHANGE, process-wide in this process only (covers inherited
# _upgrade137/_upgrade144/_act paths that call S150.screen_subject_150).
S150.screen_subject_150 = S150d.screen_subject_150d  # type: ignore[method-assign]


# ------------------------------------------------------------ ears: the stack + 150d
class Loop150dEars(S150d.SubjectGuard150dMixin, L138b.Loop138bEars):
    """Loop138bEars with the 150d case-sensitive subject screen.

    MRO: the 150d guard runs first on hear() output (base hear already ran
    the 135-patch + 140/139b/150d-patched/137/144/132 chain inside), then
    _act() re-checks before the write. Inherited upgrade paths call the
    patched S150.screen_subject_150, i.e. the same 150d rule.
    """

    name = "loop150d-hedgecase"

    def _upgrade137(self, actions: list[dict], turn: str) -> list[dict]:
        # [150d] Possessive owners keep the 150 case-INsensitive hedge veto.
        # "Maybe Tom's boss is Ann" (sealed C081, nowrite) and "Maybe
        # Tomorrow's author is ..." (title possessive) are indistinguishable
        # at the owner-subject level ("Maybe <Title>"), so both refuse
        # exactly as on loop138b. Title frees happen only on the direct
        # (copula / of-shape) paths, where bench132-152 lives.
        try:
            parsed = F137.parse_possessive137(turn)
        except Exception:
            parsed = None
        if parsed is not None and S150._is_hedged(S150._norm(parsed[0])):
            return actions
        return super()._upgrade137(actions, turn)


class Loop150dMouth(L138b.Loop138bMouth):
    """Loop138bMouth unchanged."""

    name = "loop150d-mouth"


# ------------------------------------------------------------ loop (L2 frozen)
class Loop150dAgentLoop(S150d.SubjectGuard150dMixin, L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop + 150d pre-write guard (turn() inherited verbatim)."""


DEFAULT_CONFIG150D: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG150D["ears"]["stand_in"] = (
    "Loop150dEars (loop138b stack with the 150d case-sensitive hedge "
    "screen: hedge counts only when its content word is lowercase as "
    "typed, or the whole span is all-caps)")
DEFAULT_CONFIG150D["mouth"]["stand_in"] = (
    "Loop150dMouth (Loop138bMouth unchanged)")
DEFAULT_CONFIG150D["daemon"]["module"] = "Loop150dDaemon (this file)"


def build_agent150d(cfg: dict | None = None) -> Loop150dAgentLoop:
    """Build the loop138b agent shape with the 150d hedge screen swapped in.

    Mirrors L138b.build_agent138b part-for-part (same chain, mouth shape,
    reasoner, sleeper recipe, thinker, L2 self-logs, sleep145 retrofit);
    only the ears/loop classes are the 150d subclasses.
    """
    import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
    import fable_loop148b_agent as L148b  # noqa: E402 (reasoner, read-only)
    import fable_sleep145_agent as S145  # noqa: E402 (retrofit, read-only)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: (read-only)
    cfg = dict(DEFAULT_CONFIG150D, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop150dMouth()
    reasoner = L148b.ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop150dAgentLoop(
        state_dir, ears=Loop150dEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper,
        sleep_threshold=int(cfg.get("sleep_threshold", 20)))
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
    loop.notes.append("sleep150d: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit as in loop138b)")
    return loop


class Loop150dDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 150d agent inside (settle gate kept)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float | None = None) -> None:
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
        self.loop = build_agent150d(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(
            grace_s=D141.SETTLE_GRACE_S if grace_s is None else grace_s)


def run_daemon150d(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop150dDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


# Compat aliases for drivers that reuse the 138b bench module by import
# (module.L138b -> this module): they access Loop138bDaemon /
# DEFAULT_CONFIG138B / build_agent138b. (The marks123 loader picks the last
# Loop* Daemon alphabetically, i.e. Loop150dDaemon, so this alias is inert
# there.)
Loop138bDaemon = Loop150dDaemon
DEFAULT_CONFIG138B = DEFAULT_CONFIG150D
build_agent138b = build_agent150d


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 150d hedged-case loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG150D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG150D)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG150D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon150d(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent150d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
