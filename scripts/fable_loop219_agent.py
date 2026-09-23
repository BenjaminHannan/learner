#!/usr/bin/env python3
"""Experiment 219 -- "YOU NEVER TOLD ME" REPLIES MUST BE TRUE (Muse).

loop219 = loop138i + ONE change (director-verified problem 14:25 on
loop138i): self replies that claim the user never told/taught something
are checked against the notebook before they are sent.

New files only; no existing file edited. loop138i is wrapped read-only:
the ears, _act, _listening_tick, reasoner, notebook, sleep and daemon
are loop138i's verbatim. turn() is the 138g body verbatim
(L134 notebook path + live-state logging + route127 notebook-miss router
+ DECLINE, scripts/fable_loop138g_agent.py:304-349) plus the 138h
raw-USER backstop (scripts/fable_loop138h_agent.py:171-183), with the
SINGLE swapped call: grounded_self_answer (fix168) becomes
grounded219_self_answer (scripts/fable_fix219_selfname.py: this exp's
one change). When the D8 canned denial would claim the user never told
their name while the notebook holds (USER, name, X), the reply is
"Yes. Your name is X." with X from the notebook; otherwise the reply is
byte-identical to loop138i, and no notebook write ever occurs.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop219_agent.py --daemon --dir DIR \\
    --config artifacts/fable-selfname219-20260922/loop219-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
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
import fable_fix166_me as M166  # noqa: E402 (USER_KEY scrub, read-only)
import fable_fix219_selfname as F219  # noqa: E402 (this exp, one change)
import fable_loop102_agent as L102  # noqa: E402 (HEARSAY_MSG, read-only)
import fable_loop134_agent as L134  # noqa: E402 (138b turn path, read-only)
import fable_loop138_agent as L138  # noqa: E402 (router + decline, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (mouth base, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (reasoner donor, read-only)
import fable_loop138g_agent as L138G  # noqa: E402 (turn shape, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (scrub donor, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped stack, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_fix167e_label import Label167eMouth  # noqa: E402 (167e, read-only)
from fable_fix170_compose import install_index170  # noqa: E402 (170, read-only)
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
A._APOS = L134._APOS_SHOUTED_134

# 170 speed index: installed once at import (same pattern as
# scripts/fable_loop170_agent.py:38-40). FABLE219_INDEX=off skips it.
if os.environ.get("FABLE219_INDEX", "on") != "off":
    install_index170()


# ------------------------------------------------- loop: 138i + 219 turn
class Loop219AgentLoop(L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop with the single 219 swapped call in turn().

    turn() mirrors scripts/fable_loop138g_agent.py:304-349 (L134 path +
    logging + route127/decline) plus the 138h raw-USER backstop
    (scripts/fable_loop138h_agent.py:171-183). The ONLY difference from
    loop138i behaviour: the self path serves grounded219_self_answer
    instead of grounded_self_answer. Ears, _act, _listening_tick,
    reasoner, notebook, sleep: inherited untouched.
    """

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        before = set(self.nb.facts)
        said = L134.Loop134AgentLoop.turn(self, text)
        reply = " ".join(said) if said else "(nothing to say)"
        records = list(getattr(self, "last_records", []))
        n = len(self.self_turn_log) + 1
        after = set(self.nb.facts)
        for fid in after - before:
            self.self_origin[fid] = {"by": "Ben", "turn": n}
        self.self_turn_log.append({
            "n": n, "ben": text, "reply": reply, "records": records,
            "statuses": [r.get("status", r.get("kind")) for r in records],
            "stage": getattr(self.ears, "last_stage", ""),
            "score": getattr(self.ears, "last_score", 0.0),
            "wrote": len(after - before) > 0 or str(text).startswith("forget"),
            "via": "loop", "tick": self.tick, "mode": self.mode,
        })
        self.self_mode_log.append({"tick": self.tick, "mode": self.mode})
        self.last_routed = None
        if L138.notebook_missed(records):
            intent, info = L138._route127(text)
            if intent != "DECLINE":
                # [219] THE ONE CHANGE: notebook-checked self answer.
                ans = F219.grounded219_self_answer(self, text, intent)
                entry = {"n": n, "text": text, "intent": intent,
                         "info": {k: v for k, v in info.items()
                                  if k != "reply"},
                         "answer": ans}
                self.self_routed.append(entry)
                self.last_routed = entry
                self.self_turn_log[-1]["routed"] = intent
                self.self_turn_log[-1]["reply"] = ans
                out = [ans]
                if (M166.USER_KEY not in str(text)
                        and any(M166.USER_KEY in line for line in out)):
                    out = [L138H.Loop138hAgentLoop._scrub_user_key(line)
                           for line in out]
                return out
            import fable_self105 as S105  # noqa: E402 (frozen text, read-only)

            ans = S105.HONEST_DECLINE + L138.DECLINE_SUFFIX
            entry = {"n": n, "text": text, "intent": "DECLINE",
                     "info": {k: v for k, v in info.items()
                              if k != "reply"},
                     "answer": ans}
            self.self_routed.append(entry)
            self.last_routed = entry
            self.self_turn_log[-1]["routed"] = "DECLINE"
            self.self_turn_log[-1]["reply"] = ans
            return [ans]
        if (M166.USER_KEY not in str(text)
                and any(M166.USER_KEY in line for line in said)):
            said = [L138H.Loop138hAgentLoop._scrub_user_key(line)
                    for line in said]
        return said


DEFAULT_CONFIG219: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG219["ears"]["stand_in"] = (
    "Loop219AgentLoop (loop138i stack + 219 notebook-checked self replies)")
DEFAULT_CONFIG219["daemon"]["module"] = "Loop219Daemon (this file)"
DEFAULT_CONFIG219["self"] = dict(L138I.DEFAULT_CONFIG138I.get("self", {}))
DEFAULT_CONFIG219["self"]["rule219"] = (
    "D8 denial checked against notebook: stored USER name wins "
    "('Yes. Your name is X.'); else byte-identical; never writes")


def build_agent219(cfg: dict | None = None) -> Loop219AgentLoop:
    """Build the loop138i agent shape with the 219 turn (this file)."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG219, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Label167eMouth(L138b.Loop138bMouth())
    reasoner = L138d.Reasoner138d()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = L138I.Loop138iEars(Loop96Ears(chain))
    loop = Loop219AgentLoop(
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
    # L2 live-self state (Self99-shaped logs; the 219 turn above
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
    # 166c display-case overrides (agent-layer only; notebook append-only).
    loop._dc166c = {}
    # 154e relation functionality (instance-level Listening._relation
    # patch: allow-listed keys incl. language are non-functional).
    L138I._wrap_relation154e(loop)
    # L3 sleep145 (grow-slot + taught-beats-sleep; serving files
    # sleep145-* so sealed 104/131 state is never touched).
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep219: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    loop.notes.append("loop219: loop138i + 219 notebook-checked self "
                      "replies (D8 denial yields to stored USER name; "
                      "else byte-identical; never writes)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop219Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 219 agent inside."""

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
        self.loop = build_agent219(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def run_daemon219(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop219Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 219 selfname agent")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG219 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG219)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG219)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon219(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent219(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
