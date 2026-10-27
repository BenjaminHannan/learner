#!/usr/bin/env python3
"""Experiment 146 -- THE ONE CHANGE: a DOUBT marker for refused corrections.

A REFUSED correction leaves the old fact standing, so the agent later
answers the stale value confidently. Evidence: (1) bench132 case
bench132-4hop-022: the edit teach "Charles M. Schulz is famous for The
Protocols of the Elders of Zion" is refused ("could you split that?"), the
old fact "Peanuts" stays, the 4-hop question answers wrong; (2) exp 139
(artifacts/fable-fix139-20260922/): the guard refused "... United Kingdom
of Great Britain and Ireland" edit teaches and 11 bench chains went
correct -> wrong (10x via the old citizenship, 1x abstain -> wrong).

THE RULE. When a teach message is refused or answered with a clarify reply
AND the refused message names a subject already in the notebook AND a
relation cue for that subject can be identified, record a DOUBT marker on
(subject, relation):

  * subject/relation detection reuses the existing parsers only
    (B73.hear_teach_template, B92.hear_teach92, FakeEars teach/correct
    actions -- the same functions the loop's own teach path uses); no new
    parsing is invented. Messages with no relation cue (chit-chat, opinions,
    small talk) therefore never create a doubt.
  * "already in the notebook" is the notebook's own resolve(): status OK or
    AMBIGUOUS. Unknown subjects never create a doubt.
  * While the doubt stands, any question whose answer walk uses that
    (subject, relation) abstains with a short reply: the user told it
    something new about it that it could not store, and it asks them to say
    it again as one fact. The walk is mirrored step-for-step over entity
    IDs like the reasoner; a walk that STOPS at a doubted subject also
    abstains when the doubted relation is question-mentioned or the
    question mentions relations beyond the walked frame (the composer
    walks the same post-edit chain and truncates exactly at the refusal
    gap, so the intended walk continues past the sink).
  * A later successful teach of the same (subject, relation) (Saved: for a
    new value, or "I already have that." for a repeat of the old value)
    clears the doubt.
  * The doubt is a notebook-side record (doubts146.json next to state.json
    and the notebook dir, atomic temp-write + fsync + replace, reloaded on
    every build so it survives daemon restarts), never in weights, and it
    never deletes or edits the old fact.

Cooperative Doubt146Mixin (same stacking style as exp 139/140): hear()
pre-parses with the existing parsers, runs the base hear, and records a
doubt when the base answers clarify on a known-subject teach; it also
screens ask actions (traversal + doubted-sink-mentioned check). _act()
records doubts for act-level clarify refusals of teach/correct actions and
clears doubts on successful writes. No existing file is edited.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (FakeEars parser reuse, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (teach parser, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (extra patterns, read-only)
import fable_loop102_agent as L102  # noqa: E402 (pre-filter helpers, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_notebook_contract as C  # noqa: E402 (status constants, read-only)

DOUBT_FILENAME = "doubts146.json"

# Successful-write replies (same contract the bench scorer uses): a Saved
# line stores a new value; the duplicate ack re-confirms the old value.
# Anything else (clarify text, CONFLICT question, "could NOT save") neither
# records nor clears.
DUP_ACK = "I already have that."

TEACH_ACTS = ("teach", "correct")


def norm_subject(name: str) -> str:
    """Notebook-alias normalisation (same as the contract's alias key)."""
    return " ".join(str(name).strip().lower().split())


def doubt_reply(subject: str, relation: str) -> str:
    """Short abstain reply. Contains the scorer's abstain phrase
    ("I can take one fact at a time") and no underscore (q4 scan)."""
    rel = str(relation).replace("_", " ").strip() or "that"
    return ("You told me something new about " + str(subject).strip()
            + "'s " + rel + " that I could not store. "
            + "I can take one fact at a time \u2014 could you say it "
            + "again as one fact?")


def _fake_teach_triple(sentence: str) -> tuple[str, str, str] | None:
    """Possessive teach shapes via the chain's own FakeEars (read-only use).

    B73/B92 cover the bench template frames; the M1 possessive frame
    ("Mira's city is Lisbon.") lives in FakeEars (FakeStage). Reusing its
    output is reuse, not new parsing.
    """
    try:
        actions = A.FakeEars().hear(sentence)
    except Exception:
        return None
    if len(actions) != 1:
        return None
    action = actions[0]
    if not isinstance(action, dict) or action.get("act") not in TEACH_ACTS:
        return None
    subj, rel = action.get("name", ""), action.get("relation", "")
    if not subj or not rel:
        return None
    return (subj, rel, action.get("value", ""))


def detect_teach146(turn: str) -> tuple[str, str, str] | None:
    """(subject, relation, object) for a teach-shaped turn, else None.

    Mirrors the Loop121Ears teach-side preprocessing order (correction
    prefix, forget shapes, qualifier strip) and tries the existing parsers
    in chain order: B73 template, B92 extra patterns, then the FakeEars
    possessive shape. Questions, forget turns, chit-chat, opinions and
    anything unparseable return None (never a doubt).
    """
    text = " ".join(str(turn).split())
    if not text or text.rstrip().endswith("?"):
        return None
    # Forget-shaped turns are doorway forgets, never teaches (F2 order).
    _t = text
    _m = L102._PLEASE_FORGET_RE.match(_t)
    if _m:
        _t = "forget" + _t[_m.end(1):]
    if L102._FORGET_VERB_RE.match(_t):
        return None

    def _try(sentence: str) -> tuple[str, str, str] | None:
        got = B73.hear_teach_template(sentence)
        if got is not None:
            return got
        got = B92.hear_teach92(sentence)
        if got is not None:
            return got
        return _fake_teach_triple(sentence)

    stripped = L102.strip_correction_prefix(text)
    if stripped is not None:
        got = _try(L102._cap1(L102.strip_trailing_qualifier(stripped)))
        if got is not None:
            return got
    return _try(L102.strip_trailing_qualifier(text))


def mentioned_relations(question: str) -> set[str]:
    """Question-mentioned relations via the existing cue lists (both arms)."""
    try:
        m73 = B73._relation_mentions(question)
    except Exception:
        m73 = set()
    try:
        m92 = B92._relation_mentions92(question)
    except Exception:
        m92 = set()
    return set(m73) | set(m92)


class DoubtStore146:
    """Notebook-side persisted doubt record (one JSON file per daemon dir).

    Keys are (normalised subject, relation); values carry the display
    subject, relation, the refused turn excerpt and a timestamp. Atomic
    temp-write + fsync + replace, stale temps swept on load (kill-9 safe).
    """

    def __init__(self, state_dir) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / DOUBT_FILENAME
        self.doubts: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        for stale in self.dir.glob(DOUBT_FILENAME + ".tmp*"):
            try:
                stale.unlink()
            except OSError:
                pass
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(raw, dict):
            for key, rec in raw.get("doubts", {}).items():
                if (isinstance(key, str) and "\x00" in key
                        and isinstance(rec, dict)):
                    self.doubts[key] = rec

    def _save(self) -> None:
        payload = {"version": 1, "doubts": self.doubts}
        tmp = self.dir / f"{DOUBT_FILENAME}.tmp{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False,
                                    sort_keys=True))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)

    @staticmethod
    def key(subject: str, relation: str) -> str:
        return norm_subject(subject) + "\x00" + str(relation).strip()

    def has(self, subject: str, relation: str) -> bool:
        return self.key(subject, relation) in self.doubts

    def record(self, subject: str, relation: str, turn: str = "") -> bool:
        key = self.key(subject, relation)
        if key in self.doubts:
            return False
        self.doubts[key] = {
            "subject": str(subject).strip(),
            "relation": str(relation).strip(),
            "turn": str(turn)[:200],
            "t": round(time.time(), 3),
        }
        self._save()
        return True

    def clear(self, subject: str, relation: str) -> bool:
        key = self.key(subject, relation)
        if key not in self.doubts:
            return False
        del self.doubts[key]
        self._save()
        return True


def _get_store(obj) -> DoubtStore146 | None:
    return getattr(obj, "doubt_store146", None)


def _subject_known(nb, subject: str) -> bool:
    try:
        found = nb.resolve(subject)
    except Exception:
        return False
    return found.status in (C.OK, C.AMBIGUOUS)


class Doubt146Mixin:
    """Stackable mixin: doubt on refused known-subject teaches; abstain on
    doubted answer walks. Cooperative (super() first for the reply, with a
    side-effect-free pre-parse before it)."""

    # -- internals ----------------------------------------------------
    def _doubt_store(self) -> DoubtStore146 | None:
        return _get_store(self)

    def _notebook(self):
        return getattr(self, "nb", None)

    def _record_doubt(self, subject: str, relation: str, turn: str = "") -> None:
        store = self._doubt_store()
        if store is None or not subject or not relation:
            return
        store.record(subject, relation, turn)

    def _clear_doubt(self, subject: str, relation: str) -> None:
        store = self._doubt_store()
        if store is None or not subject or not relation:
            return
        store.clear(subject, relation)

    def _walk_hit(self, name: str, relations: list[str],
                  question_text: str | None = None
                  ) -> tuple[str, str] | None:
        """(subject, relation) doubted hop used by this answer walk, if any.

        Mirrors the reasoner walk over entity IDs (missing fact / literal
        value ends the walk like notebook.ask). Then the truncation rule:
        the N-hop composer walks the same post-edit chain and stops exactly
        where a refused hop is missing, so a walk whose sink carries a
        doubt abstains when the doubted relation is question-mentioned OR
        the question mentions relations beyond the walked frame (the
        intended walk continues past the refusal gap, e.g. paraphrased
        cues like "calls home").
        """
        store = self._doubt_store()
        nb = self._notebook()
        if store is None or nb is None or not store.doubts:
            return None
        try:
            found = nb.resolve(name)
        except Exception:
            return None
        if found.status != C.OK:
            return None  # unknown/ambiguous: normal path already abstains
        cur = found.detail["entity_id"]
        sink = cur
        walked: list[str] = []
        try:
            for rel in list(relations or []):
                if store.has(nb.entities.get(cur, ""), rel):
                    return (nb.entities.get(cur, ""), rel)
                rows = nb.current(cur, rel)
                if not rows:
                    break  # missing: normal MISSING path; sink check below
                value = rows[0]["value"]
                if "entity" not in value:
                    break  # literal: chain cannot continue
                cur = value["entity"]
                sink = cur
                walked.append(rel)
        except Exception:
            return None
        if question_text is None:
            return None
        try:
            mentioned = mentioned_relations(question_text)
        except Exception:
            return None
        wants_more = bool(set(mentioned) - set(walked))
        sink_name = nb.entities.get(sink, "")
        for key, rec in store.doubts.items():
            if ("\x00" not in key
                    or key.split("\x00", 1)[0] != norm_subject(sink_name)):
                continue
            if rec.get("relation") in mentioned or wants_more:
                return (sink_name, rec.get("relation"))
        return None

    def _doubt_clarify(self, subject: str, relation: str) -> dict:
        try:
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
        except Exception:
            pass
        return {"kind": "clarify", "text": doubt_reply(subject, relation)}

    # -- ears side ----------------------------------------------------
    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = self._notebook()
        store = self._doubt_store()
        triple = None
        if nb is not None and store is not None:
            try:
                triple = detect_teach146(turn)
            except Exception:
                triple = None
        actions = super().hear(turn)  # type: ignore[misc]
        if nb is None or store is None:
            return actions
        if not isinstance(actions, list):
            return actions
        # Question side: an ask whose answer walk uses a doubted hop (or
        # whose sink carries a doubt for a mentioned relation) abstains.
        if (len(actions) == 1 and isinstance(actions[0], dict)
                and actions[0].get("act") == "ask"):
            try:
                hit = self._walk_hit(str(actions[0].get("name", "")),
                                     list(actions[0].get("relations", [])),
                                     str(turn))
            except Exception:
                hit = None
            if hit is not None:
                subj, rel = hit
                self.last_stage, self.last_score = "loop146-doubt", 1.0
                return [{"act": "clarify",
                         "text": doubt_reply(subj, rel)}]
            return actions
        # Teach side: refused (clarify) + known subject + relation cue.
        if triple is None:
            return actions
        if not any(isinstance(a, dict) and a.get("act") == "clarify"
                   for a in actions):
            return actions
        if any(isinstance(a, dict) and a.get("act") in TEACH_ACTS
               for a in actions):
            return actions
        subj, rel, _obj = triple
        if not _subject_known(nb, subj):
            return actions
        self._record_doubt(subj, rel, str(turn))
        return actions

    # -- loop side ----------------------------------------------------
    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in TEACH_ACTS:
            subj = str(action.get("name", ""))
            rel = str(action.get("relation", ""))
            result = super()._act(action)  # type: ignore[misc]
            if not isinstance(result, dict):
                return result
            if result.get("kind") == "clarify":
                # Act-level refusal (e.g. value-guard inner path): same
                # rule, with the action's own parser-built (name, relation).
                nb = self._notebook()
                if nb is not None and subj and rel and _subject_known(
                        nb, subj):
                    self._record_doubt(subj, rel, "")
            elif result.get("kind") == "write":
                text = str(result.get("text", "")).strip()
                if result.get("wrote") or text == DUP_ACK:
                    # Successful teach (new value or repeat) clears.
                    if subj and rel:
                        self._clear_doubt(subj, rel)
            return result
        return super()._act(action)  # type: ignore[misc]

    def _ask(self, name: str, relations: list[str],
             entity_id: str | None = None) -> dict:  # type: ignore[no-redef]
        # Defense-in-depth for asks that bypass ears hear (pending pick
        # re-asks): traversal check only (no question text available here).
        try:
            hit = self._walk_hit(str(name), list(relations or []), None)
        except Exception:
            hit = None
        if hit is not None:
            return self._doubt_clarify(hit[0], hit[1])
        return super()._ask(name, relations, entity_id)  # type: ignore[misc]
