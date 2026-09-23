#!/usr/bin/env python3
"""Experiment 209 -- WRITE SCREEN on loop138i (Muse).

loop138i declares facts/relations through exactly one path:

    Ears.hear(turn) -> [{"act": "teach"/"correct", "name", "relation",
                         "value", "is_person", ...}]
      -> AgentLoop._act -> _write("teach NAME REL ->/=> VALUE")
        -> Listening.hear (scripts/fable_listening_m1.py:106 _teach)
          -> Notebook.new_entity (arrow "->" only) + declare_relation
             + assert_fact (scripts/fable_notebook_contract.py)

So the screen sits at the two narrowest additive points (subclass only;
scripts/fable_loop138i_agent.py is never edited):

  (1) Loop209Ears(WriteScreen209EarsMixin, Loop138iEars).hear --
      outermost ears: post-processes every teach/correct action the full
      138i chain returns.
  (2) Loop209AgentLoop(WriteScreen209LoopMixin, Loop138iAgentLoop)._act --
      backstop for the one path that re-enters _act below the ears
      (Multival154eMixin._act_multi_teach138i calls super()._act with a
      rebuilt teach); applies the value strip only, idempotently.

THE ONE CHANGE (three screens, nothing else):

  (a) Leading "named"/"called" is stripped from a taught/corrected value
      ("is named Pip" / "is called Pip" -> "Pip"), repeatedly so the
      hear screen and the _act backstop are idempotent. Only a LEADING
      occurrence is stripped, so values that contain "named"/"called"
      later ("Pip, named after grandfather") are byte-identical to 138i.
      A value that is nothing but the prefix clarifies with the base's
      own "I didn't get the value." and writes nothing.
  (b) Date-type relations (closed rule: the key contains "birthday" or
      "anniversar", or contains "birth" plus "date"/"day", or is exactly
      "birthdate"/"dob") with a value of the shape "in|on <rest>" where
      <rest> is a month name, a weekday name, or a digit-containing date
      ("in March", "on Friday", "on 12 May") are stored as LITERALS with
      the preposition stripped ("March"), never as entities -- so no
      "in March" person is created and "When is my birthday?" can no
      longer answer about age. Person relations are untouched, so
      month-named people ("Kim's sister is April.", "May's city is
      Paris.") stay entities exactly as on 138i.
  (c) A teach/correct whose relation KEY contains a clause word ("but",
      "now", "that", "which", "who", "because", "then", or the bigram
      "used to", matched as whole underscore/space-separated tokens) is
      not declared: the whole turn becomes the base's own
      one-fact-at-a-time clarify ("I can take one fact at a time \u2014
      could you split that?", fable_earsguard91.SPLIT_MSG), 0 writes
      (no FACT, no RELATION, no ENTITY event beyond what already
      existed). Values containing those words are fine -- only the
      relation key is screened.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop209_agent.py --daemon --dir DIR \\
    --config artifacts/fable-writescreen209-20260922/loop209-config.json
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

import fable_agent_loop as A  # noqa: E402 (FakeEars texts, read-only)
import fable_earsguard91 as G91  # noqa: E402 (SPLIT_MSG, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (wrapped base, read-only)

# ------------------------------------------------------------------ (a)
_NAMED_LEAD_RE = re.compile(
    r"^(?:named|called)\b\s*(?=\S)", re.IGNORECASE)


def strip_named209(value: str) -> str:
    """Strip leading "named"/"called" occurrences (idempotent)."""
    text = str(value)
    while True:
        cleaned = _NAMED_LEAD_RE.sub("", text).strip()
        if cleaned == text:
            return cleaned
        text = cleaned


NO_VALUE_MSG = "I didn't get the value."  # FakeEars text, fable_agent_loop.py

# ------------------------------------------------------------------ (b)
_MONTHS209 = frozenset(
    "january february march april may june july august september october "
    "november december jan feb mar apr jun jul aug sep sept oct nov dec".split())
_WEEKDAYS209 = frozenset(
    "monday tuesday wednesday thursday friday saturday sunday "
    "mon tue tues wed thu thur thurs fri sat sun".split())
_DATE_PREP_RE = re.compile(r"^(in|on)\s+(\S.*)$",
                           re.IGNORECASE | re.DOTALL)


def is_date_relation209(relation: str) -> bool:
    """Closed date-type rule over the relation KEY."""
    norm = str(relation).lower().replace("_", " ").replace("-", " ").strip()
    norm = " ".join(norm.split())
    if not norm:
        return False
    if "birthday" in norm or "anniversar" in norm:
        return True
    toks = set(norm.split())
    if "birth" in toks and ("date" in toks or "day" in toks):
        return True
    return norm in ("birthdate", "dob", "birth date", "day of birth")


def date_literal209(value: str) -> str | None:
    """'in|on <month|weekday|date>' -> stripped literal, else None."""
    m = _DATE_PREP_RE.match(" ".join(str(value).split()))
    if m is None:
        return None
    rest = m.group(2).strip().rstrip(".").strip()
    if not rest:
        return None
    low = rest.lower().rstrip(".").strip()
    if low in _MONTHS209 or low in _WEEKDAYS209:
        return rest
    if re.search(r"\d", rest):
        return rest
    return None


# ------------------------------------------------------------------ (c)
_CLAUSE_WORDS209 = frozenset(
    {"but", "now", "that", "which", "who", "because", "then"})
_REL_TOK_RE = re.compile(r"[_\s/\-]+")
_ONE_FACT_MSG = G91.SPLIT_MSG  # base's one-fact-at-a-time reply


def relation_has_clause209(relation: str) -> bool:
    """True when the relation KEY contains a clause word token."""
    toks = [t for t in _REL_TOK_RE.split(str(relation).lower()) if t]
    if any(t in _CLAUSE_WORDS209 for t in toks):
        return True
    return any(a == "used" and b == "to"
               for a, b in zip(toks, toks[1:]))


# ------------------------------------------------------------------ screen
_TEACH_ACTS = ("teach", "correct")


def screen_action209(action: dict) -> dict | None:
    """One teach/correct action -> screened action, "clarify" dict, or None.

    Returns None when the action is not a teach/correct (caller keeps it
    untouched). Returns a clarify dict for the empty-value edge.
    Relation-clause refusal is handled at the turn level (screen_turn209),
    not here, so one bad relation refuses the whole turn with 0 writes.
    """
    if not isinstance(action, dict) or action.get("act") not in _TEACH_ACTS:
        return None
    out = dict(action)
    out["value"] = strip_named209(out.get("value", ""))
    if not str(out["value"]).strip():
        return {"act": "clarify", "text": NO_VALUE_MSG}
    if out.get("is_person") and is_date_relation209(out.get("relation", "")):
        lit = date_literal209(out["value"])
        if lit is not None:
            out["value"] = lit
            out["is_person"] = False
    return out


def screen_turn209(actions: list[dict]) -> list[dict]:
    """Apply the 209 write screen to one hear() result (0+ writes safe)."""
    if not isinstance(actions, list) or not actions:
        return actions
    for action in actions:
        if (isinstance(action, dict)
                and action.get("act") in _TEACH_ACTS
                and relation_has_clause209(action.get("relation", ""))):
            return [{"act": "clarify", "text": _ONE_FACT_MSG}]
    out = []
    for action in actions:
        screened = screen_action209(action)
        out.append(action if screened is None else screened)
    return out


class WriteScreen209EarsMixin:
    """Outermost ears screen: post-process the full 138i chain's actions."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        return screen_turn209(super().hear(turn))  # type: ignore[misc]


class Loop209Ears(WriteScreen209EarsMixin, L138I.Loop138iEars):
    """Loop138iEars + the 209 write screen outside everything."""

    name = "loop209-write-screen"


class WriteScreen209LoopMixin:
    """_act backstop: the value strip only (idempotent with hear)."""

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in _TEACH_ACTS:
            stripped = strip_named209(action.get("value", ""))
            if not str(stripped).strip():
                return super()._act(  # type: ignore[misc]
                    {"act": "clarify", "text": NO_VALUE_MSG})
            if stripped != action.get("value"):
                action = dict(action, value=stripped)
        return super()._act(action)  # type: ignore[misc]


class Loop209AgentLoop(WriteScreen209LoopMixin, L138I.Loop138iAgentLoop):
    """Loop138iAgentLoop + the 209 _act value backstop."""


DEFAULT_CONFIG209: dict = copy.deepcopy(L138I.DEFAULT_CONFIG138I)
DEFAULT_CONFIG209["ears"]["stand_in"] = (
    "Loop209Ears (loop138i stack + outermost write screen: strip leading "
    "named/called; date relations store in/on month/weekday/date as "
    "literals; clause-word relations refuse with one-fact-at-a-time)")
DEFAULT_CONFIG209["daemon"]["module"] = "Loop209Daemon (this file)"


def build_agent209(cfg: dict | None = None) -> Loop209AgentLoop:
    """Build the loop138i agent shape with the 209 screen stacked on."""
    import fable_sleep145_agent as S145  # noqa: E402 (read-only)
    cfg = dict(DEFAULT_CONFIG209, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L138I.L90.ChainEars(cfg)
    mouth = L138I.L167E.Label167eMouth(L138I.L138b.Loop138bMouth())
    reasoner = L138I.L138d.Reasoner138d()
    from fable_wire51_adapters import (  # noqa: E402 (read-only)
        HardGate46Sleeper)
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    inner_ears = Loop209Ears(Loop96Ears(chain))
    loop = Loop209AgentLoop(
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
    loop.notes.append("loop209: loop138i + write screen (named/called "
                      "strip; date literals; clause-word relation refuse)")
    return loop


class Loop209Daemon(L138I.Loop138iDaemon):
    """Loop138iDaemon shape with the 209 agent inside."""

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
        self.loop = build_agent209(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L138I.D108.boot_reconcile(self)
        self.settle = L138I.D141.SettleGate141(grace_s=grace_s)


def run_daemon209(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop209Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 209 write screen")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138i)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG209 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG209)
        out["thinker"]["module"] = L138I.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG209)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon209(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent209(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
