#!/usr/bin/env python3
"""Experiment 148b -- status-preserving question screen (registered follow-up).

Registered single-change follow-up to the exp-148 FAIL (see
artifacts/fable-screen148-20260922/RESULTS.md and
design/v3/30-modes/148-question-screen-muse.md).

148's question screen behaves as intended (Q1/Q2/Q3/Q5 PASS, 0 wrong writes)
but failed Q4 because its clarify is an ears-level {"act": "clarify"} with NO
reasoner status, so status-based marks123 judges score it differently:
p3 L5-Z2's 37 never-items become NO_RECORD (MISS) where the base had
MISSING_FACT (abstain_ok), and p3 L5-Z1 turns 42/43 ("What is Mira's city in
2019?") mismatch a sealed expectation that encodes the old qualifier-blind
answer.

THE ONE CHANGE (record plumbing only; user-visible replies byte-identical to
148's): a screened question is answered through the REASONER record path, so
the refusal carries an explicit abstain-type status (kind "answer" + status)
instead of a status-less ears clarify:

  ScreenStatusMixin148b.hear  -- 148-identical detection (same gate, same
      taught-mention exemption, same sealed word list via
      fable_screen148_mixin, same neg-wins precedence). On a hit it parses
      the turn with the unchanged base ears and tags the resulting ask
      action(s) with screen148b="neg"/"time" instead of clarifying.
  ScreenStatusReasoner148b.answer -- on a tagged question it first asks the
      real QualifierAwareReasoner77 lookup (read-only, no writes):
        * lookup abstains (e.g. MISSING_FACT on never-taught relations) ->
          that record is returned unchanged apart from a screen148b marker
          in fields. MISSING_FACT is then literally true BY CONSTRUCTION
          (the store itself said so). This covers p3 L5-Z2's 37 never-items.
        * lookup would answer OK through the unsupported qualifier/negation
          (the exact bug 148 screens) -> replaced with an UNSUPPORTED_QUESTION
          refusal record. MISSING_FACT is NOT used here because the fact
          exists; only qualifier support is missing.
  ScreenTextMouth148b.say -- a record carrying the screen148b marker renders
      148's exact clarify text (imported read-only from fable_screen148_mixin),
      so every user-visible reply is byte-identical to 148's.

Per-judge treatment of the one new status UNSUPPORTED_QUESTION (every judge
that reads statuses, verified in the registered run):
  * p3 L5-Z2 (`status in B65.ABSTAIN`): never receives it -- every L5-Z2
    screen hit is a genuinely never-taught relation, so the reasoner's own
    MISSING_FACT is returned (abstain_ok). Shown per-turn in RESULTS.
  * p3 L5-Z1 (exact status match): turns 42/43 observe UNSUPPORTED_QUESTION
    vs the sealed OK (which encodes the old qualifier-blind answer) --
    PREDICTED mismatch, the only non-identical turns.
  * reply-text judges (P2/R98 is_abstain, RT110, 143-runner, benches, Q1/Q2
    drivers): see 148's byte-identical clarify text -> abstain, as in 148.

No existing file is edited. 148 is imported read-only (mixin word logic) and
wrapped by subclassing; loop134/loop132 bases are imported read-only.

Status vocabulary (all pre-existing except the last):
  MISSING_FACT / BROKEN_CHAIN / UNKNOWN_ENTITY / AMBIGUOUS (contract);
  BAD_REQUEST (contract, e.g. degenerate unparseable asks);
  UNSUPPORTED_QUESTION (new in this file: well-formed question whose
  negation/time qualifier the notebook cannot represent; refused before
  answering; never a confident answer, never a write).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop148b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-screen148b-20260922/loop148b-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook triples, read-only)
import fable_loop121_agent as L121  # noqa: E402 (daemon shape, read-only)
import fable_loop132_agent as L132  # noqa: E402 (Q1 base, read-only)
import fable_loop134_agent as L134  # noqa: E402 (shipped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
import fable_screen148_mixin as S148  # noqa: E402 (148 word list, read-only)
from fable_fix77_core import (  # noqa: E402 (reasoner parent, read-only)
    QualifierAwareReasoner77)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# The one new status. Meaning: the question parsed but carries a negation or
# time qualifier the notebook cannot represent, so it was refused before any
# answer was composed. Never a confident answer, never a notebook write.
UNSUPPORTED_QUESTION = "UNSUPPORTED_QUESTION"

_SCREEN_REASONS = {
    "neg": ("negation outside notebook semantics "
            "(not/never/n't/no-one/nobody/none); refused before answering"),
    "time": ("time qualifier outside notebook semantics "
             "(year/as-of/before/after/formerly/originally/used-to/currently); "
             "the store holds current facts only; refused before answering"),
}


class ScreenStatusMixin148b:
    """148-identical screen detection; the refusal becomes a tagged ask.

    Detection block mirrors QuestionScreenMixin148.hear verbatim (same "?"
    gate, same notebook-bound guard, same taught-mention exemption, same
    sealed trigger_spans, same neg-wins precedence). The ONLY difference:
    instead of returning {"act": "clarify"}, the turn is parsed with the
    unchanged base ears and each ask action is tagged screen148b="neg"/"time"
    so the refusal flows through the reasoner record path.
    """

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        kind = self._screen148b_kind(text)
        if kind is None:
            return super().hear(turn)
        base_acts = super().hear(text)
        tagged = [dict(a, screen148b=kind) for a in base_acts
                  if a.get("act") == "ask"]
        if tagged:
            out = []
            for a in base_acts:
                out.append(dict(a, screen148b=kind)
                           if a.get("act") == "ask" else a)
            self.last_stage, self.last_score = (
                f"loop148b-screen-{kind}", 1.0)
            return out
        # Base could not parse the screened turn either: route a degenerate
        # tagged ask so the record path still yields an abstain status with
        # 148's text (fallback; no registered turn takes it).
        self.last_stage, self.last_score = (
            f"loop148b-screen-{kind}-unparsed", 1.0)
        return [{"act": "ask", "name": "", "relations": [],
                 "screen148b": kind}]

    def _screen148b_kind(self, text: str) -> str | None:
        """148-identical detection; returns "neg"/"time"/None."""
        if text and text.rstrip().endswith("?") and self.nb is not None:
            try:
                triples = L90.notebook_triples(self.nb)
            except Exception:  # noqa: BLE001 -- fail safe: screen unexempted
                triples = []
            known: list[str] = []
            for subj, _rel, val in triples:
                known.append(str(subj))
                known.append(str(val))
            try:
                hits = S148.trigger_spans(text, known)
            except Exception:  # noqa: BLE001 -- never break the base path
                hits = []
            if hits:
                kinds = {k for k, _ in hits}
                return "neg" if "neg" in kinds else "time"
        return None


class ScreenStatusReasoner148b(QualifierAwareReasoner77):
    """Reasoner parent unchanged; tagged asks become status-carrying refusals.

    Untagged questions: super().answer() verbatim. Tagged questions: the real
    lookup runs first (read-only, never writes). A non-OK verdict is returned
    as-is plus a screen148b marker (MISSING_FACT then literally true by
    construction). An OK verdict -- i.e. the qualifier-blind answer 148
    screens -- is replaced with an UNSUPPORTED_QUESTION refusal (MISSING_FACT
    would be literally false here: the fact exists).
    """

    def answer(self, question: dict, notebook) -> dict:
        kind = question.get("screen148b")
        if kind not in ("neg", "time"):
            return super().answer(question, notebook)
        inner = {k: v for k, v in question.items() if k != "screen148b"}
        try:
            rec = super().answer(inner, notebook)
        except Exception:  # noqa: BLE001 -- lookup must never break the path
            rec = None
        if (isinstance(rec, dict) and rec.get("kind") == "answer"
                and rec.get("status") != C.OK):
            out = dict(rec)
            out["fields"] = dict(rec.get("fields") or {})
            out["fields"]["screen148b"] = kind
            return out
        return {"kind": "answer", "status": UNSUPPORTED_QUESTION,
                "name": question.get("name", ""),
                "relations": list(question.get("relations") or []),
                "fields": {"screen148b": kind,
                           "reason": _SCREEN_REASONS[kind]}}


class ScreenTextMouth148b:
    """Render screen-marked records as 148's exact clarify text, byte-identical.

    Mixin first in MRO (over Loop134Mouth / FakeMouth). Non-marked records
    fall through untouched, so every other reply is base-identical.
    """

    def say(self, record: dict) -> str:
        fields = record.get("fields") or {}
        if record.get("kind") == "answer" and fields.get(
                "screen148b") == "neg":
            return S148.NEG_MSG
        if record.get("kind") == "answer" and fields.get(
                "screen148b") == "time":
            return S148.TIME_MSG
        return super().say(record)


class Loop148bEars134(ScreenStatusMixin148b, L134.Loop134Ears):
    """Loop134Ears + the 148b status-preserving screen (shipped arm)."""

    name = "loop148b-status-screen-on-134"


class Loop148bEars132(ScreenStatusMixin148b, L132.Loop132Ears):
    """Loop132Ears + the 148b status-preserving screen (Q1 red-team arm)."""

    name = "loop148b-status-screen-on-132"


class Loop148bMouth134(ScreenTextMouth148b, L134.Loop134Mouth):
    """Loop134Mouth + exact 148 screen texts for marked records."""


class Loop148bMouth132(ScreenTextMouth148b, A.FakeMouth):
    """FakeMouth + exact 148 screen texts for marked records (Q1 arm)."""


class ScreenTagActMixin:
    """Carry the ears screen tag into the reasoner question.

    Mixin-first in loop MRO. Tagged asks go through the tag-carrying _ask
    below (reasoner record path); every other action falls through to the
    base _act untouched (forget2/structured/teach paths identical).
    """

    def _ask(self, name: str, relations: list[str],
             entity_id: str | None = None) -> dict:
        tag = getattr(self, "_screen148b_tag", None)
        record = self.reasoner.answer(
            {"name": name, "relations": relations, "entity_id": entity_id,
             **({"screen148b": tag} if tag else {})}, self.nb)
        self.counters["answers"] += 1
        if record.get("status") == C.AMBIGUOUS:
            self.question_pending = {"name": name, "relations": relations,
                                     "ids": list(record["fields"].get(
                                         "ids", []))}
        return record

    def _act(self, action: dict) -> dict:
        if action.get("act") == "ask" and action.get("screen148b") in (
                "neg", "time"):
            self._screen148b_tag = action["screen148b"]
            try:
                return self._ask(action.get("name", ""),
                                 list(action.get("relations") or []),
                                 action.get("entity_id"))
            finally:
                self._screen148b_tag = None
        return super()._act(action)


class Loop148bAgentLoop(ScreenTagActMixin, L134.Loop134AgentLoop):
    """Loop134AgentLoop (forget2 action included); ears/reasoner/mouth differ."""


class Loop148bAgentLoop132(ScreenTagActMixin, L132.Loop132AgentLoop):
    """Loop132AgentLoop + tag-carrying _act (Q1 red-team arm)."""


DEFAULT_CONFIG148B: dict = copy.deepcopy(L134.DEFAULT_CONFIG134)
DEFAULT_CONFIG148B["ears"]["stand_in"] = (
    "Loop148bEars134 (ScreenStatusMixin148b: 148-identical negation/time word "
    "screen with taught-mention exemption; screened turns become tagged asks "
    "so the refusal flows through the reasoner record path; statements "
    "untouched) over " + str(
        L134.DEFAULT_CONFIG134["ears"]["stand_in"]))
DEFAULT_CONFIG148B["reasoner"]["stand_in"] = (
    "ScreenStatusReasoner148b over QualifierAwareReasoner77: tagged asks keep "
    "the lookup's own non-OK verdict (MISSING_FACT literally true by "
    "construction) or refuse as UNSUPPORTED_QUESTION when the lookup would "
    "answer through the unsupported qualifier")
DEFAULT_CONFIG148B["mouth"]["stand_in"] = (
    "Loop148bMouth134 (ScreenTextMouth148b over Loop134Mouth: screen-marked "
    "records render 148's exact clarify text; all else base-identical)")
DEFAULT_CONFIG148B["daemon"]["module"] = "Loop148bDaemon (this file)"

DEFAULT_CONFIG148B_ON132: dict = copy.deepcopy(L132.DEFAULT_CONFIG132)
DEFAULT_CONFIG148B_ON132["ears"]["stand_in"] = (
    "Loop148bEars132 (ScreenStatusMixin148b over Loop132Ears) Q1 arm")
DEFAULT_CONFIG148B_ON132["reasoner"]["stand_in"] = (
    "ScreenStatusReasoner148b over QualifierAwareReasoner77 (as shipped arm)")
DEFAULT_CONFIG148B_ON132["mouth"]["stand_in"] = (
    "Loop148bMouth132 (ScreenTextMouth148b over FakeMouth: screen-marked "
    "records render 148's exact clarify text)")
DEFAULT_CONFIG148B_ON132["daemon"]["module"] = (
    "Loop148bDaemon132 (scripts/fable_loop148b_agent.py)")


def _build_common(chain, mouth, state_dir: Path):
    reasoner = ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4149)
    return reasoner, sleeper


def build_agent148b(cfg: dict | None = None) -> Loop148bAgentLoop:
    """Build the loop134 agent shape with the 148b status screen."""
    cfg = dict(DEFAULT_CONFIG148B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop148bMouth134()
    reasoner, sleeper = _build_common(chain, mouth, state_dir)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop148bAgentLoop(
        state_dir, ears=Loop148bEars134(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop._screen148b_tag = None
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


def build_agent148b_on132(cfg: dict | None = None):
    """Build the loop132 agent shape with the 148b status screen (Q1 arm)."""
    cfg = dict(copy.deepcopy(L132.DEFAULT_CONFIG132), **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop148bMouth132()
    reasoner, sleeper = _build_common(chain, mouth, state_dir)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop148bAgentLoop132(
        state_dir, ears=Loop148bEars132(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop._screen148b_tag = None
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


class _DaemonBase148b(L121.Loop121Daemon):
    """Loop121Daemon mailbox shape with a 148b agent inside."""

    _builder = staticmethod(build_agent148b)

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
        self.loop = self._builder(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


class Loop148bDaemon(_DaemonBase148b):
    """134-lineage daemon (shipped arm)."""

    _builder = staticmethod(build_agent148b)


class Loop148bDaemon132(_DaemonBase148b):
    """132-lineage daemon (Q1 red-team arm)."""

    _builder = staticmethod(build_agent148b_on132)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 148b status-screen loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop134)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG148B to PATH and exit")
    parser.add_argument("--write-config132", default=None,
                        help="write DEFAULT_CONFIG148B_ON132 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG148B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0
    if args.write_config132:
        out = copy.deepcopy(DEFAULT_CONFIG148B_ON132)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config132).write_text(json.dumps(out, indent=1),
                                              encoding="utf-8")
        print(f"wrote {args.write_config132}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG148B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop148bDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent148b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
