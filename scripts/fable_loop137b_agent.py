#!/usr/bin/env python3
"""Experiment 137b -- discourse-glued multi-word names, on loop138b (Muse).

Base agent: loop138b (`scripts/fable_loop138b_agent.py`,
`artifacts/fable-agent138b-20260922/loop138b-config.json`).
137's 2-4 token rule lives at `scripts/fable_fix137_names.py:123-127`
(called from `scripts/fable_loop138b_agent.py:142-169`).

THE ONE CHANGE: `Loop137bEars` subclasses loop138b's ears and replaces
only the 137 upgrade step with a discourse-aware one
(`_upgrade137b`); everything else (135 patch window, 140 clean, 139b
value veto, 150 subject veto, 144 upgrade, 132 rewrite, 151 twin, 148b
screen, L2 turn(), _act guards, sleep145, settle daemon) is inherited
unchanged. No loop138b file is edited.

Upgrade rule (`scripts/fable_fix137b_discourse.py`, closed list fixed
before any panel read): a 137-parsed subject triggering the discourse
rule re-parses the message minus its leading token through the unchanged
loop138b pipeline; a triggering value re-parses with its first token
dropped (re-screened); phone-fronted "?" questions strip the same way.
The stripped result is used only when it yields a non-clarify action;
otherwise the base refusal stands.

No existing file is edited; everything new lives in this file (+
`scripts/fable_fix137b_*.py`, `artifacts/fable-discourse137b-20260922/`,
`design/v3/30-modes/137b-discourse-muse.md`).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop137b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-discourse137b-20260922/loop137b-config.json
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
import fable_bench73_english_arm as B73  # noqa: E402 (patched transiently, restored)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_earsguard91 as G91  # noqa: E402 (value screens, read-only)
import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_fix135_office as F135  # noqa: E402 (officeholder guard, read-only)
import fable_fix137_names as F137  # noqa: E402 (possessive parse, read-only)
import fable_fix137b_discourse as D137B  # noqa: E402 (this exp: closed list)
import fable_fix139b_valueguard as V139b  # noqa: E402 (value screen, read-only)
import fable_fix140_tail as T140  # noqa: E402 (tail cleaner, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
import fable_loop102_agent as L102  # noqa: E402 (guards + texts, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (wrapped base, read-only)
import fable_loop144_agent as L144  # noqa: E402 (single-teach parse, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_sleep145_agent as S145  # noqa: E402 (sleep retrofit, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (whole-word core, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Same process-wide overrides as loop138b (no file edited).
WM149.apply_wordmatch()
import fable_loop134_agent as L134  # noqa: E402 (read-only value source)
A._APOS = L134._APOS_SHOUTED_134


def _has_nonclarify(actions: list[dict]) -> bool:
    return bool(actions) and any(
        isinstance(a, dict) and a.get("act") != "clarify" for a in actions)


class Loop137bEars(L138b.Loop138bEars):
    """Loop138bEars with THE ONE CHANGE: discourse-aware 137 upgrade.

    hear() mirrors the base order exactly (135 patch window, chain, 140,
    139b, 150, 137b upgrade, 144 upgrade, 132 rewrite) plus the
    phone-fronted question strip on all-clarify "?" turns.
    """

    name = "loop137b-discourse"

    def hear(self, turn: str) -> list[dict]:
        original = B73.hear_teach_template
        B73.hear_teach_template = F135.hear_teach135  # type: ignore[method-assign]
        try:
            actions = super(L138b.Loop138bEars, self).hear(turn)
            actions = T140.sanitize_actions(actions)
            actions = V139b.guard_actions(actions)
            actions = S150.guard_actions(actions)
            actions = self._upgrade137b(actions, turn)
            actions = self._upgrade144(actions, turn)
            actions = self._rewrite132(actions, turn)
            actions = self._strip_question(actions, turn)
            return actions
        finally:
            B73.hear_teach_template = original

    # -- THE ONE CHANGE: discourse-aware 137 upgrade ---------------------
    def _upgrade137b(self, actions: list[dict], turn: str) -> list[dict]:
        if not isinstance(actions, list) or not actions:
            return actions
        if any(isinstance(a, dict) and a.get("act") in (
                "teach", "correct", "ask", "answer", "forget2",
                "person", "alias", "forget", "quote") for a in actions):
            return actions  # base understood the turn: never touch it
        parsed = F137.parse_possessive137(turn)
        if parsed is None:
            return L138b.Loop138bEars._upgrade137(self, actions, turn)
        name, relation, value, _correction = parsed
        if D137B.is_discourse_name(name):
            # Subject trigger: re-parse the message minus its leading
            # token through the unchanged loop138b pipeline.
            if not D137B.message_starts_with_name_token(turn, name):
                return L138b.Loop138bEars._upgrade137(self, actions, turn)
            rest = D137B.strip_first_token(" ".join(str(turn).split()))
            if not rest:
                return actions
            rest_actions = L138b.Loop138bEars.hear(self, rest)
            if _has_nonclarify(rest_actions):
                return rest_actions
            return actions  # rest does not parse: the base refusal
        if D137B.is_discourse_name(value):
            # Value trigger (discourse-first-token only; sentence-break
            # values keep the base refusal): drop the value's first token
            # and re-screen through the unchanged screens.
            if D137B.has_sentence_break(value):
                return L138b.Loop138bEars._upgrade137(self, actions, turn)
            new_value = D137B.strip_first_token(value)
            if not new_value:
                return actions
            if G91.screen_value(new_value) is not None:
                return actions
            stripped_v = P129.strip_sentence_punct(new_value)
            if V139b.screen_value_139b(
                    stripped_v if stripped_v else new_value) is not None:
                return actions
            verdict, _clean = S150.screen_subject_150(name)
            if verdict != "store":
                return actions
            action = T140.sanitize_action(P129.sanitize_action(
                F137.build_action137((name, relation, new_value,
                                      _correction))))
            if not action.get("name") or not action.get("value"):
                return actions
            try:
                self.last_stage, self.last_score = ("loop138b-fix137", 1.0)
            except AttributeError:
                pass
            return [action]
        return L138b.Loop138bEars._upgrade137(self, actions, turn)

    # -- phone-fronted questions: same glued token, same strip -----------
    def _strip_question(self, actions: list[dict], turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not (text and text.rstrip().endswith("?")):
            return actions
        if not actions or any((not isinstance(a, dict))
                              or a.get("act") != "clarify" for a in actions):
            return actions  # asks + teaches pass through untouched
        if D137B.first_token_lower(text) not in D137B.DISCOURSE137B:
            return actions
        rest = D137B.strip_first_token(text)
        if not rest:
            return actions
        rest_actions = L138b.Loop138bEars.hear(self, rest)
        if _has_nonclarify(rest_actions):
            return rest_actions
        return actions  # rest does not parse: the base refusal


class Loop137bMouth(L138b.Loop138bMouth):
    """Loop138bMouth unchanged (mouth texts identical to loop138b)."""

    name = "loop137b-mouth"


class Loop137bAgentLoop(L138b.Loop138bAgentLoop):
    """Loop138bAgentLoop shape with the 137b ears (turn/_act inherited)."""

    pass


DEFAULT_CONFIG137B: dict = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
DEFAULT_CONFIG137B["ears"]["stand_in"] = (
    "Loop137bEars (loop138b + 137b discourse-glued name strip: 137 "
    "subject/value names with a sentence break or a closed-list first "
    "token re-parse minus that token, phone-fronted ? the same)")
DEFAULT_CONFIG137B["mouth"]["stand_in"] = (
    "Loop137bMouth (Loop138bMouth unchanged)")
DEFAULT_CONFIG137B["daemon"]["module"] = "Loop137bDaemon (this file)"


def build_agent137b(cfg: dict | None = None) -> Loop137bAgentLoop:
    """Build the loop138b agent shape with the 137b ears swapped in."""
    cfg = dict(DEFAULT_CONFIG137B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop137bMouth()
    from fable_loop148b_agent import (  # noqa: E402 (read-only wrap)
        ScreenStatusReasoner148b)
    reasoner = ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop137bAgentLoop(
        state_dir, ears=Loop137bEars(Loop96Ears(chain)), mouth=mouth,
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
    loop.notes.append("sleep137b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit in place of sleep131)")
    return loop


class Loop137bDaemon(L138b.Loop138bDaemon):
    """Loop138bDaemon shape with the 137b agent inside (settle inherited)."""

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
        self.loop = build_agent137b(agent_cfg)
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


def run_daemon137b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop137bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 137b discourse loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG137B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG137B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG137B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon137b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent137b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
