#!/usr/bin/env python3
"""Experiment 150b -- THE ONE CHANGE: refuse teaches whose SUBJECT span
swallows a whole second clause.

Base: loop150 (scripts/fable_loop150_agent.py = loop129b + 139b value guard
+ 150 subject guard for hedge/reporting/filler words only). Director probe,
re-checked on loop129b, loop144 AND loop150: "Ann is famous for Cats and
Tom died in the city of Oslo" saves ("Ann is famous for Cats and Tom",
place_of_death, "Oslo") -- the SUBJECT span swallows a whole teach clause;
150's guard only looks for hedge/filler words
(scripts/fable_fix150_subjectguard.py:152-163). The value-side twin ("Bea
was born in the city of Lima and Tom died in Oslo" -> value "Lima and Tom
died in Oslo") is already refused by 139b's value guard on loop150.

ROOT CAUSE (read-only, nothing edited): the teach parser takes the first
ordered pattern that fullmatches and never validates the subject span --
scripts/fable_bench73_english_arm.py:89 (the `(.+?) died in the city of
(.+?)` pattern) + :194-205 (hear_teach_template: ordered fullmatch loop,
`(.+?)` matches anything incl. whole relation clauses); extras at
scripts/fable_bench92_english_arm.py:58-68 / :176-188; accepted unchecked at
scripts/fable_loop121_agent.py:206-220. Value screens only guard the VALUE
span (scripts/fable_earsguard91.py:39-60,
scripts/fable_fix139b_valueguard.py:99-115).

THE RULE (on the subject span of every teach/correct action, AFTER the
exp-129 strip and the 150 screen, at ears hear() and again at loop _act()
just before the write -- same two levels as the 150 guard): refuse with
the existing SPLIT reply ("I can take one fact at a time -- could you
split that?", 0 writes) when the subject span contains

  (a) a relation cue from the loop's own relation tables
      (REL_CUES_150B, sealed: multi-word phrases from STATEMENT_PATTERNS /
      EXTRA_STATEMENT_PATTERNS / REL_MENTION_CUES, every phrase containing
      a finite verb; matched case-SENSITIVELY with word boundaries, so only
      an all-lowercase occurrence fires), or
  (b) a lower-case finite verb/copula token (VERBS_150B, sealed: matched as
      a whole token that is all-lowercase in the original span, so a
      capitalised title word never fires).

Exempt by construction (never fire, never listed as cues):
  - single-token subjects (one token cannot swallow a clause);
  - capitalised title words ("Gone" in "Gone with the Wind", "Framed" in
    "Who Framed Roger Rabbit", "Is"/"May"/"Lives"/"Born" sentence-titles):
    matching is case-sensitive, only lowercase fires;
  - bare role nouns and verbless of-phrases ("author", "director",
    "capital of", "city of", "country of"): NOT cues (no finite verb), so
    possessive tails ("Rabbit's director") and role phrases pass;
  - values, relation keys, forget/ask/clarify paths: untouched.

Cooperative MIXIN (Subject150BMixin): hear() runs the base hear first (the
129 strip + 139b value screen + 150 subject screen inside loop150 have
already run) and then screens the subject of teach/correct actions;
_act() re-checks just before the write (covers the inner-chain delegate
path). Same shape as SubjectGuard150Mixin; only the screen differs. No
existing file edited.
"""

from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_punct as P129  # noqa: E402 (strip rule, read-only)
import fable_fix139_valueguard as V139  # noqa: E402 (SPLIT reply, read-only)

# The loop's existing reply for a refused multi-fact write (reused, never
# invented). Same message the 139b value guard and the 150 subject guard use.
SPLIT_MSG = V139.CLARIFY_MSG

# (a) Relation cues from the loop's own relation tables. Every phrase
# contains a finite verb (verbless of-phrases such as "city of",
# "country of", "capital of", "author of", "director of" are deliberately
# NOT cues: they occur in legit single-fact subjects such as possessive
# tails and role phrases). Sealed; case-SENSITIVE match (word boundaries),
# so only an all-lowercase occurrence fires and capitalised title words
# ("Gone", "Framed", "Stood", "Lives", "Born") never fire. One-line reason
# per phrase lives in PASSMARKS.md.
REL_CUES_150B = (
    "died in",
    "is a citizen of",
    "is affiliated with",
    "is associated with",
    "is employed by",
    "is famous for",
    "is from",
    "is home",
    "is located in",
    "is married to",
    "is the apprentice of",
    "is the author of",
    "is the composer of",
    "is the discoverer of",
    "is the envoy of",
    "is the founder of",
    "is the herald of",
    "is the inventor of",
    "is the keeper of",
    "is the mentor of",
    "is the rival of",
    "is the scout of",
    "is the warden of",
    "was born in",
    "was composed by",
    "was created by",
    "was created in",
    "was developed by",
    "was discovered by",
    "was educated",
    "was founded by",
    "was founded in",
    "was invented by",
    "was performed by",
    "was written by",
    "was written in",
    "works in the field of",
    "worked in",
    "works for",
    "holds citizenship",
    "gave birth",
    "known for",
    "that produced",
    "company that employs",
    "'s child is",
)

# (b) Lower-case finite verbs / copulas / auxiliaries + the relation verbs
# of the loop's tables. Sealed; matched as whole tokens that are
# all-lowercase in the ORIGINAL span (token.strip(".,;:'\"()") must satisfy
# .islower()), so capitalised title words never fire. One-line reason per
# token lives in PASSMARKS.md.
VERBS_150B = frozenset({
    "is", "are", "was", "were", "am", "be", "been", "being",
    "has", "have", "had", "do", "does", "did",
    "will", "would", "can", "could", "shall", "should", "may", "might",
    "must",
    "died", "die", "dies", "born",
    "lives", "live", "lived", "works", "work", "worked",
    "plays", "play", "played", "speaks", "speak", "spoke", "spoken",
    "married", "marry", "employs", "employ", "employed",
    "creates", "create", "created",
    "founded", "invents", "invent", "invented",
    "discovers", "discover", "discovered",
    "composes", "compose", "composed",
    "writes", "write", "wrote", "written",
    "performs", "perform", "performed",
    "develops", "develop", "developed",
    "produces", "produce", "produced",
    "educates", "educate", "educated",
    "locates", "locate", "located",
    "affiliates", "affiliate", "affiliated",
    "associates", "associate", "associated",
    "renowned", "known",
})

_CUE_RES = [re.compile(r"(?<![A-Za-z])" + re.escape(c) + r"(?![A-Za-z])")
            for c in REL_CUES_150B]


def _norm(subject: str) -> str:
    return " ".join(str(subject).split())


def _has_relation_cue(subject: str) -> bool:
    """True when a sealed cue occurs all-lowercase (word boundaries)."""
    return any(rx.search(subject) is not None for rx in _CUE_RES)


def _has_lowercase_verb(subject: str) -> bool:
    """True when a whitespace-separated token is all-lowercase and a verb."""
    for tok in _norm(subject).split():
        stripped = tok.strip(".,;:'\"()")
        if stripped and stripped.islower() and stripped.lower() in VERBS_150B:
            return True
    return False


def screen_subject_150b(subject: str) -> tuple[str, str | None]:
    """Subject span -> (verdict, payload).

    "store" -> payload is the subject to store (unchanged; this guard never
               rewrites, it only refuses).
    "split" -> no write; payload is the SPLIT clarify reply.
    """
    text = _norm(subject)
    if not text:
        return ("store", subject)
    if len(text.split()) < 2:
        return ("store", text)
    if _has_relation_cue(text):
        return ("split", SPLIT_MSG)
    if _has_lowercase_verb(text):
        return ("split", SPLIT_MSG)
    return ("store", text)


def guard_action(action: dict) -> dict:
    """teach/correct action with a clause-swallowing subject -> clarify."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    stripped = P129.strip_sentence_punct(action.get("name", ""))
    verdict, payload = screen_subject_150b(
        stripped if stripped else action.get("name", ""))
    if verdict == "split":
        return {"act": "clarify", "text": payload}
    return action


def guard_actions(actions: list[dict]) -> list[dict]:
    return [guard_action(a) for a in list(actions)]


class Subject150BMixin:
    """Stackable mixin: clause-in-subject guard on every teach path.

    Cooperative (super() first): on ears it runs after the base hear (so
    the 129 strip + 139b value screen + 150 subject screen inside loop150
    have already run); on the loop it re-checks strip-then-screen just
    before the write (covers the inner-chain delegate path). Same shape as
    SubjectGuard150Mixin; only the screen differs.
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
            verdict, payload = screen_subject_150b(checked.get("name", ""))
            if verdict == "split":
                self.counters["clarifications"] += 1  # type: ignore[attr-defined]
                return {"kind": "clarify", "text": payload}
            if payload != action.get("name"):
                checked["name"] = payload
                return super()._act(checked)  # type: ignore[misc]
        return super()._act(action)  # type: ignore[misc]
