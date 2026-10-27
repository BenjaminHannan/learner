#!/usr/bin/env python3
"""Experiment 102 -- PATCH the 15 remaining red-team-98 bugs in the joined-up agent.

Loop102 = Loop96 (loop90 + GuardedEars91) + five ADDITIVE fixes, subclass/wrap
only. No existing file is edited; everything new lives in this file.

  F1 HEARSAY: a teach/correct-shaped sentence carrying an attribution marker
     (", X said", "according to", "I read online/that", "I heard",
     "apparently", "reportedly", leading "quote", "the web says") never
     writes; the ears answer a plain clarify instead. A bench-template match
     whose subject starts lowercase AND carries attribution vocabulary is also
     refused (never minted as an entity). Narrowed by evidence: bare "online"
     is NOT a marker (people are called Online, exp-102 scan), and a
     lowercase subject alone is legal (22 "baseball ..."/"jazz ..." subjects
     in Fable-Edit-200) -- the pair together is hearsay-shaped.
  F2 FORGET: template ears parse English forget requests ("forget <Name>
     <rel>", "Forget X's <rel>.", "Forget that X's <rel> is V.", "Please
     forget ...") into a forget2 action served by the M1 doorway's EXISTING
     forget operation (Listening._forget; same store, no new store). Guards:
     a name that IS the verb ("forget Forget city", sealed G1) clarifies
     instead of guessing; unknown names resolve through the doorway's own
     MISSING path; unique whole-word-prefix names ("Roberto" for the taught
     "Roberto Merhi") resolve to the full name, ambiguity clarifies.
  F3 CORRECTION PREFIX: "Actually, ...", "No, ...", "Correction: ...",
     "Sorry, I meant ..." + a bench-template fact = a user correction of
     that slot (correction=True through the same structured path B1-B4 use).
     Non-template remainders fall through untouched (FakeEars keeps its
     Actually-possessive correction; bare yes/no answers keep working).
  F4 QUALIFIERS: a trailing "in/since/until <year>", "from <year> to <year>",
     "as of <year>" is stripped and the BARE value is taught (the sealed D2/D7
     asks require the bare answer; attaching qualifier metadata would make
     the unqualified ask abstain per the doc-56 gate, so the qualifier phrase
     is dropped, not stored -- documented deviation). Questions are never
     stripped (sealed D8 must keep abstaining).
  F5 MAILBOX BYTES: Loop102Daemon.process_file catches (OSError,
     ValueError) around the UTF-8 read: an unreadable inbox file gets the
     reply "I couldn't read that message -- please send it as plain text.",
     is moved aside to done/, is logged, and the daemon keeps running.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop102_agent.py --daemon --dir DIR \\
    --config artifacts/fable-loop102-20260921/loop102-config.json
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
import fable_bench73_english_arm as B73  # noqa: E402 (template ears, read-only)
import fable_daemon74_run as D74  # noqa: E402 (mailbox helpers, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop90_agent as L90  # noqa: E402 (whole loop90 build, read-only)
import fable_notebook_contract as C  # noqa: E402 (contract, read-only)
from fable_earsguard91 import GuardedEars  # noqa: E402 (exp-91 fix, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper, NotebookThinker)

HEARSAY_MSG = ("Do you know that yourself, or did you hear it somewhere? "
               "I only save facts you tell me directly.")
UNREADABLE_MSG = ("I couldn't read that message -- please send it as plain "
                  "text.")
FORGET_AMBIG_MSG = ("I didn't understand that. Could you say it another way?")

_HEARSAY_RES = [
    re.compile(r",[^,.\n]{1,40}?\bsaid\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"\baccording\s+to\b", re.IGNORECASE),
    re.compile(r"\bread\s+online\b", re.IGNORECASE),
    re.compile(r"\bi\s+read\s+that\b", re.IGNORECASE),
    re.compile(r"\bi\s+heard\b", re.IGNORECASE),
    re.compile(r"\bapparently\b", re.IGNORECASE),
    re.compile(r"\breportedly\b", re.IGNORECASE),
    re.compile(r"^quote[\s:]", re.IGNORECASE),
    re.compile(r"\bthe\s+web\s+says\b", re.IGNORECASE),
]
# Subjects carrying attribution vocabulary are hearsay-shaped, never entities.
_SUBJECT_FRAGMENTS = ("quote", "said", "say", "says", "read", "online",
                      "according", "web", "heard", "hearsay", "apparently",
                      "reportedly", "rumor", "rumour")

_CORRECTION_PREFIX_RE = re.compile(
    r"^(actually\s*,|actually\s+|no\s*,|correction\s*:"
    r"|sorry\s*,?\s*i\s+meant\s*,?)\s+(.+)$",
    re.IGNORECASE | re.DOTALL)

_FORGET_THAT_RE = re.compile(
    r"^forget\s+that\s+(.+?)'s\s+(.+?)\s+is\s+.+$",
    re.IGNORECASE | re.DOTALL)
_FORGET_POSS_RE = re.compile(r"^forget\s+(.+?)'s\s+(.+?)\s*\.?\s*$",
                             re.IGNORECASE | re.DOTALL)
_FORGET_VERB_RE = re.compile(r"^forget(\s|$)", re.IGNORECASE)
_PLEASE_FORGET_RE = re.compile(r"^please\s+forget(\s|$)", re.IGNORECASE)
_IS_VERB_RE = re.compile(r"\bis\b", re.IGNORECASE)

_QUAL_RES = [
    re.compile(r"\s+from\s+\d{4}\s+to\s+\d{4}\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"\s+as\s+of\s+\d{4}\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"\s+(in|since|until)\s+\d{4}\s*\.?\s*$", re.IGNORECASE),
]


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _cap1(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def is_hearsay(text: str) -> bool:
    return any(rx.search(text) for rx in _HEARSAY_RES)


def strip_correction_prefix(text: str) -> str | None:
    m = _CORRECTION_PREFIX_RE.match(text)
    return m.group(2).strip() if m and m.group(2).strip() else None


def strip_trailing_qualifier(text: str) -> str:
    for rx in _QUAL_RES:
        if rx.search(text):
            return rx.sub("", text).strip()
    return text


def subject_is_hearsay_shaped(subject: str) -> bool:
    if not subject or not subject[0].islower():
        return False
    low = subject.lower()
    return any(frag in low for frag in _SUBJECT_FRAGMENTS)


def _declared_relations(nb) -> set[str]:
    return {e["relation"] for e in nb.events if e["kind"] == "RELATION"}


class Loop102Ears:
    """Pre-filter stage around the loop96 guarded chain (Ears protocol).

    hear() phases on the raw turn: F1 hearsay clarify; F3 correction-prefix
    bench match as correct; F2 forget parse as forget2; F4 qualifier strip
    then delegate; F1 lowercase-subject guard on bench matches; otherwise the
    inner (loop96) ears hear the turn byte-identical.
    """

    name = "loop102-prefilter"

    def __init__(self, inner) -> None:
        self.inner = inner
        self.nb = None
        self.last_stage = ""
        self.last_score = 0.0

    def bind(self, nb) -> None:
        self.nb = nb
        inner = self.inner
        if hasattr(inner, "bind"):
            inner.bind(nb)

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(self.__dict__["inner"], name)

    # -- helpers needing the notebook ----------------------------------
    def _structured_correct(self, triple: tuple[str, str, str]) -> dict:
        subj, rel, obj = triple
        return {"act": "correct", "name": subj, "relation": rel,
                "value": obj, "is_person": True, "structured": True,
                "stage": "loop102"}

    def _resolve_forget_name(self, name: str) -> str | None:
        """Exact resolve, else unique whole-word-prefix entity match.

        Returns the full entity name, or None when the doorway should report
        (unknown / ambiguous stays the doorway's job).
        """
        nb = self.nb
        if nb is None:
            return None
        try:
            found = nb.resolve(name)
        except Exception:
            return None
        if found.status == C.OK:
            return nb.entities.get(found.detail["entity_id"], name)
        if found.status == C.AMBIGUOUS:
            return None
        want = " ".join(str(name).strip().lower().split())
        if not want:
            return None
        cands = []
        try:
            entities = dict(nb.entities)
        except Exception:
            return None
        for eid, ename in entities.items():
            normed = " ".join(str(ename).strip().lower().split())
            if normed.startswith(want + " ") or normed == want:
                cands.append(ename)
        if len(cands) == 1:
            return cands[0]
        return None

    def _parse_forget(self, text: str):
        """-> (name, relation) | 'AMBIG' | None. None = not a forget turn."""
        t = text
        m = _PLEASE_FORGET_RE.match(t)
        if m:
            t = "forget" + t[m.end(1):]
        if not _FORGET_VERB_RE.match(t):
            return None
        if t.rstrip().endswith("?"):
            return None
        m = _FORGET_THAT_RE.match(t)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        m = _FORGET_POSS_RE.match(t)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        # Raw M1 shape "forget <Name...> <rel>": never a teach ("is" inside
        # means the sentence teaches; e.g. "Forget's city is Lisbon." never
        # reaches here anyway for lack of the verb+space shape).
        if _IS_VERB_RE.search(t):
            return None
        rest = _FORGET_VERB_RE.sub("", t, count=1).strip().rstrip(".").strip()
        toks = rest.split()
        if len(toks) < 2:
            return None
        return (" ".join(toks[:-1]).strip(), toks[-1].strip())

    # -- the protocol ----------------------------------------------------
    def _delegate(self, text: str) -> list[dict]:
        out = self.inner.hear(text)
        self.last_stage = str(getattr(self.inner, "last_stage", ""))
        try:
            self.last_score = float(getattr(self.inner, "last_score", 0.0))
        except (TypeError, ValueError):
            self.last_score = 0.0
        return out

    def hear(self, turn: str) -> list[dict]:
        text = _norm(turn)
        if not text:
            return self._delegate(turn)
        if is_hearsay(text):  # F1
            self.last_stage, self.last_score = "loop102-hearsay", 1.0
            return [{"act": "clarify", "text": HEARSAY_MSG}]
        stripped = strip_correction_prefix(text)  # F3
        if stripped is not None:
            cand = _cap1(strip_trailing_qualifier(stripped))
            triple = B73.hear_teach_template(cand)
            if triple is not None:
                if subject_is_hearsay_shaped(triple[0]):
                    self.last_stage, self.last_score = "loop102-hearsay", 1.0
                    return [{"act": "clarify", "text": HEARSAY_MSG}]
                self.last_stage, self.last_score = "loop102-correction", 1.0
                return [self._structured_correct(triple)]
        parsed = self._parse_forget(text)  # F2
        if parsed == "AMBIG":
            self.last_stage, self.last_score = "loop102-forget", 1.0
            return [{"act": "clarify", "text": FORGET_AMBIG_MSG}]
        if parsed is not None:
            name, rel = parsed
            if " ".join(str(name).lower().split()) == "forget":
                # Sealed G1: a person literally called Forget; the verb/noun
                # overlap is genuinely ambiguous, so clarify, never guess.
                self.last_stage, self.last_score = "loop102-forget", 1.0
                return [{"act": "clarify", "text": FORGET_AMBIG_MSG}]
            relation = "_".join(str(rel).strip().lower().split())
            if not relation:
                self.last_stage, self.last_score = "loop102-forget", 1.0
                return [{"act": "clarify", "text": FORGET_AMBIG_MSG}]
            full = self._resolve_forget_name(name)
            self.last_stage, self.last_score = "loop102-forget", 1.0
            return [{"act": "forget2",
                     "name": full if full is not None else name,
                     "relation": relation, "stage": "loop102"}]
        if not text.rstrip().endswith("?"):  # F4 (never on questions: D8)
            bare = strip_trailing_qualifier(text)
            if bare != text and bare:
                return self._delegate(bare)
        triple = B73.hear_teach_template(text)  # F1 subject guard
        if triple is not None and subject_is_hearsay_shaped(triple[0]):
            self.last_stage, self.last_score = "loop102-hearsay", 1.0
            return [{"act": "clarify", "text": HEARSAY_MSG}]
        return self._delegate(turn)


class Loop102AgentLoop(L90.Loop90AgentLoop):
    """Loop90AgentLoop + the F2 forget2 action via the M1 doorway's forget."""

    def _act(self, action: dict) -> dict:
        if action.get("act") == "forget2":
            before = len(self.nb.events)
            try:
                text = self.listening._forget(action["name"],
                                              action["relation"])
            except C.LogCorrupt as exc:
                text = ("I could NOT save that: the notebook reported a "
                        f"problem ({exc}).")
            wrote = len(self.nb.events) > before
            self.counters["writes"] += int(wrote)
            return {"kind": "write",
                    "line": ("forget %(name)s %(relation)s" % action),
                    "text": text, "wrote": wrote,
                    "pending": self.listening.pending is not None}
        return super()._act(action)


DEFAULT_CONFIG102: dict = copy.deepcopy(L90.DEFAULT_CONFIG)
DEFAULT_CONFIG102["ears"]["stand_in"] = (
    "Loop102Ears pre-filter (hearsay/forget/correction-prefix/qualifier) "
    "over Loop96Ears = GuardedEars91 over ChainEars(bench73 template + "
    "FakeEars templates)")
DEFAULT_CONFIG102["daemon"]["module"] = "Loop102Daemon (this file)"


def build_agent102(cfg: dict | None = None) -> Loop102AgentLoop:
    """Build the loop90 agent, then wrap its chain: GuardedEars91 + F1-F5."""
    cfg = dict(DEFAULT_CONFIG102, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = A.FakeMouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4102)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop102AgentLoop(
        state_dir, ears=Loop102Ears(Loop96Ears(chain)), mouth=mouth,
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


class Loop102Daemon(L90.Loop90Daemon):
    """Loop96Daemon shape with the loop102 agent and F5 byte-safe mailbox."""

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
        self.loop = build_agent102(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)

    def process_file(self, path: Path) -> dict:
        import os as _os
        nb = self.loop.nb
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            # F5: non-UTF-8 (or unreadable) inbox bytes never escape: reply,
            # move the file aside to done/, log, keep running.
            D74._atomic_write(self.outbox / path.name, UNREADABLE_MSG + "\n")
            try:
                _os.replace(path, self.done / path.name)
            except OSError:
                pass
            record = {"t": D74._now_iso(), "event": "turn-skipped-unreadable",
                      "file": path.name, "reply": UNREADABLE_MSG,
                      "turn_count": int(self.loop.counters.get("turns", 0)),
                      "notebook_events": len(nb.events)}
            D74._append_log(self.log_path, record)
            return record
        before_facts = set(nb.facts)
        before_entities = set(nb.entities)
        said = self.loop.turn(text)  # notebook append happens INSIDE first
        records = list(getattr(self.loop, "last_records", []))
        new_facts = sorted(set(nb.facts) - before_facts)
        new_entities = {eid: nb.entities[eid]
                        for eid in set(nb.entities) - before_entities}
        reply = " ".join(said) if said else "(nothing to say)"
        D74._atomic_write(self.outbox / path.name, reply + "\n")
        _os.replace(path, self.done / path.name)
        record = {"t": D74._now_iso(), "event": "turn", "file": path.name,
                  "turn_text": text.strip()[:200], "reply": reply[:500],
                  "records": records,
                  "ears_stage": getattr(self.loop.ears, "last_stage", ""),
                  "ears_score": getattr(self.loop.ears, "last_score", 0.0),
                  "new_fact_ids": new_facts, "new_entities": new_entities,
                  "turn_count": int(self.loop.counters.get("turns", 0)),
                  "notebook_events": len(nb.events)}
        D74._append_log(self.log_path, record)
        return record


def run_daemon102(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop102Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 102 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop90)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG102 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG102)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG102)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon102(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent102(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
