#!/usr/bin/env python3
"""Experiment 121 -- teach-side phrasing coverage for the joined-up agent.

Wraps scripts/fable_loop113b_agent.py (it exists; per the brief the 113b
wrapper is used, NOT the loop102 fallback).

Diagnosis from exps 111/113: through the real mailbox, 22 teaches in 12
old-fresh items are rejected -- 18x "I didn't understand…" on three relation
phrasings no teach pattern parses ("X works in the field of Y" occupation,
"X is employed by Y" employer, "X's child is Y" child), plus 4x
one-fact-at-a-time "and"-guard hits whose VALUE is a single capitalised name
containing "and" ("United Kingdom of Great Britain and Ireland": 7 words, so
exp-91's >6-word screen fires).

THE ONE CHANGE (teach side of the ears pre-filter only; question side
byte-identical to loop113b):

  Loop121Ears(Loop113bEars) on non-"?" turns mirrors Loop102Ears.hear
  phase-for-phase (hearsay screen, correction prefix, forget shapes,
  qualifier strip), except the teach-pattern match tries bench73 FIRST and,
  only when bench73 returns None, exp-92's EXTRA patterns (employer /
  occupation / child, imported read-only -- never edited). Bench73-known
  sentences and unparseable sentences both delegate to the exact loop113b
  chain, so every previously-passing and every previously-refused turn
  behaves identically. An extra-pattern match becomes the same structured
  teach/correct action Bench73Stage builds (same notebook correction
  detection), screened by the exp-91 value screen with ONE narrowing: the
  >6-word screen passes a value that is a single capitalised name span
  (Title-Case run: every token starts uppercase or is lowercase glue
  "of"/"and", and the value contains " and "). Every other screen
  ("?", ";", possessive-is, and-possessive, second copula) still refuses --
  so "Mira's city is Oslo and Tom's pet is a cat" (possessive-is + second
  copula in the value) is still refused.

"?" turns delegate byte-identical to loop113b (N-hop router + fallback).

No existing file is edited; everything new lives in this file.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop121_agent.py --daemon --dir DIR \\
    --config artifacts/fable-bench121-20260922/loop121-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (teach patterns, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (extra patterns, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_earsguard91 as G91  # noqa: E402 (guard screens, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop102_agent as L102  # noqa: E402 (pre-filter logic, read-only)
import fable_loop113b_agent as L113b  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)

# Lowercase glue allowed inside a single capitalised name span. Narrow by
# evidence: the observed "and"-names need "of" and "and" only.
_NAME_GLUE = frozenset({"of", "and"})
_AND_RE = re.compile(r"\band\b", re.IGNORECASE)


def _is_single_name_span(value: str) -> bool:
    """True when value is one Title-Case name span containing "and".

    Every whitespace-separated token must start with an uppercase letter
    (punctuation edges ignored) or be lowercase glue ("of"/"and").
    """
    text = str(value)
    if not _AND_RE.search(text):
        return False
    toks = text.split()
    if not toks:
        return False
    for tok in toks:
        stripped = tok.strip(".,;:'\"()")
        if not stripped:
            return False
        if stripped[0].isupper():
            continue
        if stripped.islower() and stripped.lower() in _NAME_GLUE:
            continue
        return False
    return True


def screen_value_121(value: str) -> str | None:
    """Exp-91 value screen with the single-name-span narrowing.

    Identical refuses for "?", ";", possessive-is, and-possessive and second
    copula; the >6-word screen additionally passes a single capitalised name
    span containing "and". Returns the clarify message or None to let pass.
    """
    text = str(value)
    if "?" in text:
        return G91.QUESTION_MSG
    if (";" in text
            or G91._POSSESSIVE_IS.search(text)
            or G91._AND_POSSESSIVE.search(text)
            or G91._SECOND_COPULA.search(text)):
        return G91.SPLIT_MSG
    if len(text.split()) > G91.MAX_VALUE_WORDS:
        if _is_single_name_span(text):
            return None
        return G91.SPLIT_MSG
    return None


def hear_teach_extra(sentence: str) -> tuple[str, str, str] | None:
    """Exp-92 EXTRA teach patterns only (employer/occupation/child/...).

    hear_teach92 tries bench73 first, so when bench73 already returned None
    this is exactly the extra-pattern set -- never a double parse.
    """
    return B92.hear_teach92(sentence)


class Loop121Ears(L113b.Loop113bEars):
    """Loop113bEars + teach-pattern coverage on non-"?" turns.

    "?" turns: byte-identical to loop113b (never touched here). Non-"?" turns
    mirror Loop102Ears.hear phase-for-phase; the only difference is the
    teach-pattern match (bench73, else the exp-92 extra patterns) and the
    121 value screen on extra-pattern actions.
    """

    name = "loop121-teach-coverage"

    def _structured_correct(self, triple: tuple[str, str, str]) -> dict:
        subj, rel, obj = triple
        return {"act": "correct", "name": subj, "relation": rel,
                "value": obj, "is_person": True, "structured": True,
                "stage": "loop121"}

    def _bench73_action(self, triple: tuple[str, str, str]) -> dict:
        """Same structured teach/correct action Bench73Stage builds."""
        stage = L90.Bench73Stage()
        stage.bind(self.nb)
        action = stage._teach_action(triple)
        action["stage"] = "loop121"
        return action

    def _guarded_extra(self, triple: tuple[str, str, str],
                       correction: bool) -> list[dict]:
        if correction:
            action = self._structured_correct(triple)
        else:
            action = self._bench73_action(triple)
        msg = screen_value_121(action.get("value", ""))
        if msg is not None:
            self.last_stage, self.last_score = "loop121-guard", 1.0
            return [{"act": "clarify", "text": msg}]
        self.last_stage, self.last_score = "loop121-teach", 1.0
        return [action]

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not text:
            return super().hear(turn)
        if text.rstrip().endswith("?"):
            return super().hear(turn)  # question side: exact loop113b
        if self.nb is None:
            return super().hear(turn)
        if L102.is_hearsay(text):  # F1 (unchanged)
            self.last_stage, self.last_score = "loop121-hearsay", 1.0
            return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
        stripped = L102.strip_correction_prefix(text)  # F3
        if stripped is not None:
            cand = L102._cap1(L102.strip_trailing_qualifier(stripped))
            triple = B73.hear_teach_template(cand)
            if triple is None:
                triple = hear_teach_extra(cand)
                if triple is not None:
                    if L102.subject_is_hearsay_shaped(triple[0]):
                        self.last_stage, self.last_score = (
                            "loop121-hearsay", 1.0)
                        return [{"act": "clarify",
                                 "text": L102.HEARSAY_MSG}]
                    return self._guarded_extra(triple, correction=True)
            return super().hear(turn)
        # F2: forget-shaped turns take the exact old path untouched.
        t = text
        m = L102._PLEASE_FORGET_RE.match(t)
        if m:
            t = "forget" + t[m.end(1):]
        if L102._FORGET_VERB_RE.match(t):
            return super().hear(turn)
        cand = L102.strip_trailing_qualifier(text)  # F4 (never on "?")
        if not cand:
            return super().hear(turn)
        triple73 = B73.hear_teach_template(cand)
        if triple73 is not None:
            # Bench73-known: same action the chain would build, screened by
            # the 121 screen. Pass (including the Title-Case "and"-name
            # exception) -> accept here; refuse -> the exact old path, which
            # refuses identically (the 121 screen refuses whenever exp-91
            # refuses). Only the stage tag differs, never the reply text.
            if L102.subject_is_hearsay_shaped(triple73[0]):
                self.last_stage, self.last_score = "loop121-hearsay", 1.0
                return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
            action = self._bench73_action(triple73)
            if screen_value_121(action.get("value", "")) is None:
                self.last_stage, self.last_score = "loop121-teach", 1.0
                return [action]
            return super().hear(turn)
        triple = hear_teach_extra(cand)
        if triple is None:
            return super().hear(turn)  # unparseable: exact old path
        if L102.subject_is_hearsay_shaped(triple[0]):  # F1 subject guard
            self.last_stage, self.last_score = "loop121-hearsay", 1.0
            return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
        return self._guarded_extra(triple, correction=False)


class Loop121AgentLoop(L113b.Loop113bAgentLoop):
    """Loop113bAgentLoop (forget2 action included); ears differ, acts don't."""


DEFAULT_CONFIG121: dict = copy.deepcopy(L113b.DEFAULT_CONFIG113B)
DEFAULT_CONFIG121["ears"]["stand_in"] = (
    "Loop121Ears (teach-pattern coverage: exp-92 employer/occupation/child "
    "patterns + Title-Case and-name guard narrowing) over Loop113bEars "
    "(N-hop router + loop102 fallback) over Loop102Ears pre-filter over "
    "Loop96Ears = GuardedEars91 over ChainEars(bench73 template + FakeEars "
    "templates); question side identical to loop113b")
DEFAULT_CONFIG121["daemon"]["module"] = "Loop121Daemon (this file)"


def build_agent121(cfg: dict | None = None) -> Loop121AgentLoop:
    """Build the loop113b agent shape with Loop121Ears on the teach side."""
    cfg = dict(DEFAULT_CONFIG121, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop121AgentLoop(
        state_dir, ears=Loop121Ears(Loop96Ears(chain)), mouth=mouth,
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
    return loop


class Loop121Daemon(L113b.Loop113bDaemon):
    """Loop113bDaemon shape with the loop121 agent inside (mailbox identical)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent121(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon121(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop121Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 121 teach-coverage loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop113b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG121 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG121)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG121)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon121(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent121(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
