#!/usr/bin/env python3
"""Experiment 150c -- THE ONE CHANGE: refuse teaches whose SUBJECT span,
after the loop's own normalisation, is a closed-class word or phrase.

Base: loop150 (scripts/fable_loop150_agent.py = loop129b + 139b value guard
+ 150 subject guard for hedge/reporting/filler words only). Director probe
03:40 on loop150 AND loop138: idioms and chat sentences with "'s" are saved
as facts about non-entities: "What's done is done." -> Saved (What, done,
done); "Today's weather is nice." -> Saved (Today, weather, nice).

PARSE PATH (read-only, nothing edited): the "'s" teaches go through the
FakeEars possessive split -- scripts/fable_agent_loop.py:96 (_STATEMENT
regex `^\\s*(.+?)\\s+is\\s+(.+?)\\s*\\.?\\s*$`), :102 (_chain splits the
left span on `'s`), :134-147 (FakeEars.hear builds the teach action with
name=parts[0], relation from parts[1]); reached through the loop chain via
scripts/fable_loop90_agent.py:184-190 (FakeStage passes non-clarify actions
through after Bench73Stage misses at :140-146). No span validation: "What"
and "Today" become entity names. The 150 guard
(scripts/fable_fix150_subjectguard.py:152-163) only screens hedge/reporting
openers and lowercase-lead shapes, so a capitalised closed-class subject
passes untouched; the 150b guard only screens clause-swallowing subjects.

THE RULE (on the subject span of every teach/correct action, AFTER the
loop's own normalisation -- whitespace-collapse as ChainEars/FakeEars do
plus the exp-129 trailing-punct strip the loop applies on every write path
-- at ears hear() and again at loop _act() just before the write, same two
levels as the 150/150b guards): refuse with the loop's OWN total-miss reply
("I didn't understand that. Could you say it another way?", 0 writes) when
the WHOLE normalised subject, case-folded for comparison only, equals a
closed-class entry (CLOSED_CLASS_150C, sealed: wh-words, personal /
demonstrative / indefinite pronouns, deictic time words, "here"/"there").

Whole-subject equality (never substring): capitalised names that merely
CONTAIN such a word still teach -- "Tomorrowland" (!= "tomorrow"),
"Nobody Knows" (!= "nobody"), "Who Framed Roger Rabbit" (!= "who"),
"It Follows" (!= "it"), "Theseus" (!= "these"), "Italy" (!= "it"),
"Wharton" (!= "what": whole-string compare, not prefix). This guard never
rewrites; values, relation keys, forget/ask/clarify paths untouched.
Untouched by design: every non-closed-class subject (screen returns the
span byte-identical); multi-word possessive titles the base already refuses
via the FakeEars one-word-names rule (no teach action exists, so this guard
never sees them -- verified 0 moves).

Cooperative MIXIN (ClosedClass150CMixin): hear() runs the base hear first
(the 129 strip + 139b value screen + 150 subject screen inside loop150 have
already run) and then screens the subject of teach/correct actions;
_act() re-checks just before the write (covers the inner-chain delegate
path). Same shape as Subject150BMixin; only the screen differs. No
existing file edited.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)

# The loop's own total-miss reply for an unparseable turn (reused, never
# invented): scripts/fable_agent_loop.py:148 (FakeEars.hear fallthrough) and
# scripts/fable_loop90_agent.py:291-292 (ChainEars total miss).
GENERIC_MSG = "I didn't understand that. Could you say it another way?"

# Closed-class subjects: refuse only on WHOLE-subject equality after the
# loop's own normalisation (case-folded for comparison only). Sealed; the
# brief's four classes, nothing added, nothing removed. One-line reason per
# entry lives in PASSMARKS.md.
CLOSED_CLASS_150C = frozenset({
    # wh-words (interrogatives: never entities)
    "what", "who", "which", "where", "when", "why", "how", "whatever",
    # personal / demonstrative / indefinite pronouns (never entities)
    "it", "this", "that", "these", "those",
    "he", "she", "they", "we", "you", "i", "me",
    "mine", "yours",
    "someone", "somebody", "everyone", "everybody",
    "nobody", "no one", "anyone",
    "something", "everything", "nothing",
    # deictic time words (indexicals: never entities)
    "today", "tomorrow", "yesterday", "tonight", "now",
    "this morning", "this week", "next year", "last year",
    # deictic place words (never entities)
    "here", "there",
})


def _norm(subject: str) -> str:
    return " ".join(str(subject).split())


def normalise_subject_150c(subject: str) -> str:
    """The loop's own normalisation for a subject span: whitespace-collapse
    (what ChainEars/FakeEars do) + the exp-129 trailing-punct strip the loop
    applies on every write path (ears and _act)."""
    text = _norm(subject)
    stripped = P129.strip_sentence_punct(text)
    return _norm(stripped if stripped else text)


def is_closed_class_subject(subject: str) -> bool:
    """True only when the WHOLE normalised subject is a closed-class entry
    (case-folded for comparison; stored names keep their case on teach)."""
    return normalise_subject_150c(subject).lower() in CLOSED_CLASS_150C


def screen_subject_150c(subject: str) -> tuple[str, str | None]:
    """Subject span -> (verdict, payload).

    "store"   -> payload is the subject to store (byte-identical; this guard
                 never rewrites, it only refuses).
    "generic" -> no write; payload is the loop's own total-miss reply.
    """
    text = _norm(subject)
    if not text:
        return ("store", subject)
    if is_closed_class_subject(text):
        return ("generic", GENERIC_MSG)
    return ("store", text)


def guard_action(action: dict) -> dict:
    """teach/correct action with a closed-class subject -> generic clarify."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("name", ""))
    verdict, payload = screen_subject_150c(
        stripped if stripped else action.get("name", ""))
    if verdict == "generic":
        return {"act": "clarify", "text": payload}
    return action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class ClosedClass150CMixin:
    """Stackable mixin: closed-class-subject guard on every teach path.

    Cooperative (super() first): on ears it runs after the base hear (so
    the 129 strip + 139b value screen + 150 subject screen inside loop150
    have already run); on the loop it re-checks strip-then-screen just
    before the write (covers the inner-chain delegate path). Same shape as
    Subject150BMixin; only the screen differs.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return guard_actions(actions)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            checked = copy.copy(action)
            cleaned = P129.strip_sentence_punct(checked.get("name", ""))
            if cleaned:
                checked["name"] = cleaned
            verdict, payload = screen_subject_150c(checked.get("name", ""))
            if verdict == "generic":
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": payload}
            if payload != action.get("name"):
                checked["name"] = payload
                return super()._act(checked)  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]
