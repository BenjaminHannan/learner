#!/usr/bin/env python3
"""Experiment 138f -- STACK CLEAN: loop138d minus the pieces that add wrong writes.

loop138f = loop138d with THREE pieces switched OFF (Step-1 attribution in
scripts/fable_fix138f_ablate.py + artifacts/fable-agent138f-20260922/
attribution-138f.json; nothing else changes):

  OFF (1) 155 inverted frames (x135 variant) -- caused 6 wrong writes:
      redteam136 C124/C127/C129 (plain inverted teaches), C142 (all-caps
      shout "KIM'S BOSS IS LEE!!!" -> saved "KIM's boss is LEE"), cases139b
      C10/C21 (compound inversions, garbage parses like "Tom and Ann's
      boss is Lena's boss"). Removing the mixin alone restores the OK
      verdict (no write); the 138b reply text needs (3) as well.
      Capability lost: inverted-shape teaches ("V is X's R.", "V is the R
      of X.", "The R of X is V.") now clarify exactly as on loop138b.
  OFF (2) 154 yes/no -- caused 1 wrong answer: redteam143 M3 ("Is Aldport
      the capital of Norland?" -> "Yes -- Norland's capital is Aldport"
      where the seal demands abstain). Only switching it off restores the
      abstain; the 138b reply text needs (3) as well.
      Capability lost: yes/no Is-questions fall back to the base clarify
      (as on loop138b) instead of Yes/No/wh-run answers; the three honest-
      reply moves 138d had on marks123 (p3 l5z1 turns 49/58, rt81
      D_q_vs_s-04) revert to base behaviour (predicted in PASSMARKS.md).
  OFF (3) 138c serving rule (turn) -- no wrong write/answer of its own,
      but its L134 base path renders leftover clarifies as "I didn't
      understand that. Could you say it another way?" where loop138b
      (L138 turn) renders the long abstain sentence. Step 1 shows NO
      single piece fixes C124/C127/C129/C142/M3; the smallest fixing sets
      are {155,138c} (teaches) and {154,138c} (M3), so all three go.
      Capability lost: notebook-missed turns serve the base reply
      verbatim (loop138 rule) instead of a grounded Self99 answer; rt110
      S1 reverts BUG->OK (a revert to the 138b row, predicted).

KEPT (8): 142 speed index (IndexedLoopNotebook + FastReasoner142 +
patch_chain142 + patch_loop121_teach + _patch_relation; the "?" reroute
stays OUT as in 138d), 146d doubt, 153 reverse, 156b small talk, 157
fillers, 158 question forms, 159 hop fallback, 150b clause guard.

Base loop138d (scripts/fable_loop138d_agent.py) is imported read-only and
never edited; every rule body is imported read-only from its own module.
Everything new lives in this file (+ scripts/fable_fix138f_*.py drivers +
artifacts/fable-agent138f-20260922/ + design/v3/30-modes/
138f-stack-clean-muse.md).

Composition:
  Ears (outermost first):
    Qform158 > Filler157 > Smalltalk156b > Doubt146b > Subject150B >
    Reverse153 > Loop138bEars (155 InvertedFrame155Mixin REMOVED).
  Loop _act: Doubt146b record/clear > Subject150B clause guard > 138b
    guards (unchanged). No YesNo154Mixin (154 REMOVED).
  turn(): loop138 verbatim (138c rule REMOVED).
  Reasoner: Reasoner138d reused read-only (148b tags over FastReasoner142
    + one 159 fallback on untagged non-OK).
  Notebook: IndexedLoopNotebook (142, unchanged). L3 sleep145, L4 daemon
    unchanged.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138f_agent.py --daemon --dir DIR \\
    --config artifacts/fable-agent138f-20260922/loop138f-config.json
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
import fable_doubt146b_store as D146B  # noqa: E402 (146d doubt mixin, read-only)
import fable_fix150b_subject150b as S150B  # noqa: E402 (150b guard, read-only)
import fable_fix153_reverse as R153  # noqa: E402 (reverse stage, read-only)
import fable_fix156b_smalltalk as S156B  # noqa: E402 (smalltalk, read-only)
import fable_fix157_filler as F157  # noqa: E402 (filler strip, read-only)
import fable_fix158_qform as Q158  # noqa: E402 (qform normalize, read-only)
import fable_loop138_agent as L138  # noqa: E402 (138b turn path, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (donor stack, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_perf142_index import (  # noqa: E402 (142 fast pieces, read-only)
    patch_chain142,
    patch_loop121_teach,
)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# THE 149 PIECE, applied at import (this process only, no file edited --
# the same process-wide override pattern loop134/loop138b/loop138d use).
WM149.apply_wordmatch()

# Re-assert the loop134 shouted-possessive override in this process (same
# value loop134/loop138/loop138b/loop138d set; no file edited).
import fable_loop134_agent as L134  # noqa: E402 (read-only)
A._APOS = L134._APOS_SHOUTED_134


# ------------------------------------------------------------ ears: 138d stack minus 155
class Loop138fEars(Q158.Qform158Mixin,
                   F157.Filler157Mixin,
                   S156B.Smalltalk156bMixin,
                   D146B.Doubt146bMixin,
                   S150B.Subject150BMixin,
                   R153.Reverse153Mixin,
                   L138b.Loop138bEars):
    """Loop138bEars + six ears-level late fixes (155 inverted REMOVED)."""

    name = "loop138f-stack"


# ------------------------------------------------------------ loop: 138d shape minus 154 and 138c
class Loop138fAgentLoop(D146B.Doubt146bMixin,
                        S150B.Subject150BMixin,
                        L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop + doubt + 150b guard + 142 indexed shape.

    No YesNo154Mixin (154 off). turn() is inherited verbatim from loop138
    (138c serving rule off): notebook-missed turns serve the base reply.
    __init__/_save mirror Loop138dAgentLoop (IndexedLoopNotebook +
    torn-tail repair + Listening + _patch_relation + tail-200 persist).
    """

    def __init__(self, state_dir, *, ears=None, mouth=None, reasoner=None,
                 sleeper=None, thinker=None,
                 sleep_threshold: int = A.SLEEP_THRESHOLD) -> None:
        L138d.Loop138dAgentLoop.__init__(
            self, state_dir, ears=ears, mouth=mouth, reasoner=reasoner,
            sleeper=sleeper, thinker=thinker,
            sleep_threshold=sleep_threshold)

    _save = L138d.Loop138dAgentLoop._save


DEFAULT_CONFIG138F: dict = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
DEFAULT_CONFIG138F["ears"]["stand_in"] = (
    "Loop138fEars (loop138b stack + 158 qform + 157 filler + 156b "
    "smalltalk + 146d hearsay-exempt doubt + 150b clause-subject guard + "
    "153 reverse questions, outermost first; 155 inverted OFF)")
DEFAULT_CONFIG138F["reasoner"]["class"] = (
    "Reasoner138d reused (148b screen-tag logic over FastReasoner142 + "
    "one 159 bridge fallback on untagged non-OK answers)")
DEFAULT_CONFIG138F["daemon"]["module"] = "Loop138fDaemon (this file)"
DEFAULT_CONFIG138F["self"] = {
    "router": "route127 (frozen novelty-guard router, scripts/fable_self127.py)",
    "answerer": "Self99Agent.answer_self over live loop state (served only "
                "by the inherited loop138 turn rule, as on loop138b)",
    "rule": ("loop138 verbatim (138c OFF): notebook answers win; "
             "notebook-missed turns serve the base loop's own reply"),
}
DEFAULT_CONFIG138F["sleep"] = {
    "retrofit": "Sleep145Reasoner + Sleep145Sleeper via retrofit_sleep145",
    "recipe": "exp-46 recipe + taught-beats-sleep answer rule (all words)",
}


def build_agent138f(cfg: dict | None = None) -> Loop138fAgentLoop:
    """Build the loop138d agent shape minus pieces 155, 154, 138c."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG138F, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop138fEars(Loop96Ears(chain))
    loop = Loop138fAgentLoop(
        state_dir, ears=inner_ears, mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    # 142 teach/chain index patches on the INNER ears (before the sleep
    # wrap replaces loop.ears with its Sleep130Ears delegate).
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
    # L2 live-self state (Self99-shaped logs; the inherited loop138 turn
    # maintains them -- same shape loop138/loop138b keep).
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    # 146d doubt store (notebook-side doubts146.json contract, shared by
    # the loop and the inner ears; attached BEFORE the sleep wrap).
    store = D146B.D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    inner_ears.doubt_store146 = store
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep138f: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop138f: 138d minus 155-inverted minus 154-yesno "
                      "minus 138c-serve (142-index + 146d-doubt + "
                      "153-reverse + 156b-smalltalk + 157-filler + "
                      "158-qform + 159-hop + 150b-guard kept)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop138fDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 138f agent inside.

    141 settle gate + exactly-once process_file are inherited unchanged.
    __init__ mirrors Loop138dDaemon.__init__ line for line except the
    build call. Name ends in Daemon / starts with Loop so the marks123
    loader picks this class.
    """

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent138f(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon138f(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138fDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 138f stacked loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138d)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138F to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138F)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138F)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138f(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138f(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
