#!/usr/bin/env python3
"""Experiment 172 -- copula/verb-shape re-teach ASKS before replacing (Muse).

Base: loop154c (scripts/fable_loop154c_agent.py), subclassed read-only.
No loop154c / loop138b / any other file is edited; everything new lives
here (+ scripts/fable_fix172_*.py + artifacts/fable-copula172-20260922/).

STEP 1 ANSWER: the copula shape is routed to `correct` (silent supersede)
in scripts/fable_loop90_agent.py:153-170 -- Bench73Stage._teach_action
(lines 164-165: same (subject, relation), new object -> act="correct").
The possessive shape ("Tavo's country of citizenship is Chile.") goes
through FakeEars (scripts/fable_agent_loop.py:145: no correction prefix
-> act="teach"), so Listening (scripts/fable_listening_m1.py:106-127)
asks before changing (CONFLICT -> pending confirm). Same meaning,
different behaviour = the bug.

Every surface shape that reaches the correct-route (all via the same
Bench73Stage._teach_action / Loop121Ears._bench73_action stateful
second-value rule, or the F3 explicit-correction path):
  bench73 STATEMENT_PATTERNS (scripts/fable_bench73_english_arm.py:73-128):
  "The author/capital/chairperson/CEO/company/headquarters/head of
  state/head of government/official language/music/university of X is Y",
  "X died in the city of Y" (place_of_death), "X is a citizen of Y"
  (country_of_citizenship), "X is affiliated with the religion of Y",
  "X is associated with the sport of Y", "X is famous for Y"
  (notable_work), "X is located in the continent of Y", "X is married
  to Y" (spouse), "X is the apprentice/author/composer/discoverer/envoy/
  founder/herald/inventor/keeper/mentor/rival/scout/warden of Y",
  "X plays the position of Y", "X speaks the language of Y",
  "X was born in the city of Y", "X was composed/created/(created in
  country)/developed/discovered/founded/(founded in city)/invented/
  performed/written by Y", "X worked in the city of Y", generic "The Y
  is Z" (officeholder);
  bench92 EXTRA patterns (Loop121Ears.hear_teach_extra): "X is employed
  by Y" (employer), "X works in the field of Y" (occupation), "X was
  written in the language of Y", "X's child is Y" (child), "The head
  coach / origianl broadcaster / director of X is Y";
  F3 explicit-correction path (Loop102Ears/Loop121Ears via
  scripts/fable_loop102_agent.py:92-95 _CORRECTION_PREFIX_RE):
  "Actually, ...", "No, ...", "Correction: ...", "Sorry I meant, ..."
  + any bench73/extra fact -> structured correct (kept as-is by 172).

THE ONE CHANGE versus loop154c: a structured (bench73/extra-shape)
teach/correct that would change an existing value on a relation NOT on
154c's MULTI_VALUED allow-list, with NO explicit correction prefix on
the raw turn, is downgraded correct->teach in the ears, so it takes the
SAME Listening change-prompt path as the possessive shape (same wording,
same yes/no pending state). Explicit-correction-prefixed turns keep
correcting exactly as now. Allow-listed relations keep 154c's add path.
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

import fable_agent_loop as A  # noqa: E402 (Protocols + person set, read-only)
import fable_fix154b_multival as M154  # noqa: E402 (relation_key, read-only)
import fable_fix154c_allowlist as M154C  # noqa: E402 (allow-list, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop154b_agent as L154b  # noqa: E402 (wrapped base, read-only)
import fable_loop154c_agent as L154c  # noqa: E402 (wrapped base, read-only)
import fable_loop102_agent as L102  # noqa: E402 (prefix RE, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)


def has_correction_prefix172(turn: str) -> bool:
    """True iff the raw turn carries the base's explicit-correction prefix.

    The base's correct path uses scripts/fable_loop102_agent.py:92-95
    (_CORRECTION_PREFIX_RE: actually, / actually / no, / correction: /
    sorry I meant). FakeEars' _CORRECTION (actually|no,) is a subset.
    """
    return L102.strip_correction_prefix(" ".join(str(turn).split())) is not None


def downgrade172(turn: str, actions: list[dict]) -> list[dict]:
    """correct->teach for non-allow structured re-teaches without prefix."""
    if not isinstance(actions, list) or not actions:
        return actions
    if has_correction_prefix172(turn):
        return actions  # explicit correction: correct exactly as now
    out = []
    for a in actions:
        if (isinstance(a, dict) and a.get("act") == "correct"
                and a.get("name") and a.get("value")):
            key = M154.relation_key154b(str(a.get("relation", "")))
            if not M154C.is_multi154c(key):
                a = dict(a, act="teach")
        out.append(a)
    return out


class Loop172Ears(L154c.Loop154cEars):
    """Loop154cEars + the copula re-teach downgrade (allow-listed and
    explicit-correction turns pass through byte-identical)."""

    name = "loop172-ears"

    def hear(self, turn: str) -> list[dict]:
        actions = super().hear(turn)
        fixed = downgrade172(turn, actions)
        if any(f is not a for f, a in zip(fixed, actions)
               if isinstance(f, dict) and isinstance(a, dict)):
            try:
                self.last_stage, self.last_score = (
                    "loop172-copula-ask", 1.0)
            except AttributeError:
                pass
        return fixed


class Loop172AgentLoop(L154c.Loop154cAgentLoop):
    """Loop154cAgentLoop with 172 ears. turn() and every _act handler are
    inherited VERBATIM: a downgraded teach on a non-allow key routes to
    Loop138bAgentLoop._act -> Listening CONFLICT change-prompt, byte for
    byte the possessive path (same wording, same yes/no pending state)."""

    # -- main override --------------------------------------------------
    def _act(self, action: dict) -> dict:
        # No _act change: the ears already downgraded correct->teach, so
        # the inherited 154c router sends it down the loop138b path.
        return super()._act(action)


DEFAULT_CONFIG172: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG172["ears"]["stand_in"] = (
    "Loop172Ears (loop154c stack + copula/verb-shape re-teach on "
    "non-allow relations without an explicit correction prefix takes "
    "the possessive change-prompt path; explicit corrections and "
    "allow-listed relations byte-identical to loop154c)")
DEFAULT_CONFIG172["mouth"]["stand_in"] = (
    "Loop138bMouth unchanged (multi lists render through the base template)")
DEFAULT_CONFIG172["daemon"]["module"] = "Loop172Daemon (this file)"
DEFAULT_CONFIG172["sleep"] = dict(L138b.DEFAULT_CONFIG138B.get("sleep", {}))


def build_agent172(cfg: dict | None = None) -> Loop172AgentLoop:
    """Build the loop154c agent shape with the 172 copula-ask rule."""
    cfg = dict(DEFAULT_CONFIG172, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    from fable_loop90_agent import ChainEars  # noqa: E402 (read-only wrap)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    chain = ChainEars(cfg)
    mouth = L138b.Loop138bMouth()
    reasoner = L138b.L148b.ScreenStatusReasoner148b()
    from fable_wire51_adapters import HardGate46Sleeper  # noqa: E402
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    loop = Loop172AgentLoop(
        state_dir, ears=Loop172Ears(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L138b.L90.build_thinker(loop.nb)
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
    L154c._wrap_relation154c(loop)
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep172: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131, as 154c)")
    loop.notes.append("copula172: non-allow structured re-teach without an "
                      "explicit correction prefix asks before replacing")
    return loop


class Loop172Daemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 172 agent inside (settle gate + atomic
    clients inherited unchanged). Name ends in Daemon / starts with Loop so
    the marks123 loader picks this class."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L138b.D141.SETTLE_GRACE_S) -> None:
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
        self.loop = build_agent172(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138b.D108.boot_reconcile(self)
        self.settle = L138b.D141.SettleGate141(grace_s=grace_s)


def run_daemon172(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop172Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 172 copula-ask loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop154c)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG172 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG172)
        out["thinker"]["module"] = L138b.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG172)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon172(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent172(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
