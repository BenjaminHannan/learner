#!/usr/bin/env python3
"""Experiment 155 -- THE ONE CHANGE: an inverted-frame teach stage (mixin).

Director probe on loop150: "Rita is Ann's mother." and "Rita is the mother
of Ann." -> "I didn't understand that" (no write); "The mother of Ann is
Rita." -> a WRONG write ("mother of Ann", officeholder, "Rita") via the
bench73 catch-all ``The (.+?) is (.+?)`` (scripts/fable_bench73_english_arm.py
line 127). Exp 135's officeholder guard (scripts/fable_fix135_office.py
hear_teach135) turns that wrong write into a refusal; 135 is not in loop150
(it arrives through integration).

THE ONE CHANGE: an inverted-frame teach stage, ONLY for relation cues in
the loop's own relation tables (never the officeholder catch-all):

    "V is X's R." / "V is the R of X." / "The R of X is V."

-> save (X, R, V) through the same guards, audit trail and replies as the
canonical "X's R is V.".

How (stackable mixin InvertedFrame155Mixin, outer-ears level like the 150
subject guard):

  * hear() runs the base hear first. If the base already produced a
    non-officeholder teach/correct, the sentence is bench-known: return base
    untouched (bench73 specific patterns such as capital/author keep their
    exact action, stage tag and audit trail).
  * Otherwise the raw turn is matched against the three strict full-turn
    frames. The relation surface R must be relation-shaped (letters/spaces/
    slash/hyphen only) AND normalise to a key in ALLOWED_KEYS (union of the
    loop's own cue-table keys + the loop's person table, minus the exp-135
    office family) AND must not be an exp-135 office head (president, mayor,
    director, ...). Anything else -> base untouched (office phrases, unknown
    relations, hedged/two-fact sentences keep base behaviour exactly).
  * One-word X: the turn is rewritten to its canonical twin
    "X's R is V." (correction prefix preserved) and passed through the SAME
    super().hear -- literally the canonical path, so guards, audit trail
    and replies are identical by construction. The resulting teach/correct
    is accepted only when its triple is exactly (X, R, V); else base.
  * Multi-word X (two-word names, "of"-names: no canonical possessive exists
    -- FakeEars is one-word-names-only): a structured teach/correct is built
    with Bench73Stage._teach_action (same correct-vs-teach detection as the
    bench path, is_person mirrored from FakeEars), and returned only when
    the loop121 value screen, the loop102 hearsay-subject check and the 150
    subject screen all pass; any refusal -> base untouched. The loop _act
    guards (139b value + 150 subject just before the write) still apply.

No existing file is edited. Everything new lives in this file (+
scripts/fable_loop155_agent.py, which stacks this mixin onto loop150, and
optionally onto loop150 + the 135 mixin for the coexistence config).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON table, read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (cue tables, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (cue tables, read-only)
import fable_fix135_office as F135  # noqa: E402 (office family, read-only)
import fable_fix150_subjectguard as S150  # noqa: E402 (subject screen, read-only)
import fable_loop102_agent as L102  # noqa: E402 (hearsay check, read-only)
import fable_loop121_agent as L121  # noqa: E402 (value screen, read-only)
import fable_loop90_agent as L90  # noqa: E402 (Bench73Stage, read-only)

# ----------------------------------------------------------------------------
# The loop's own relation tables (mechanical union, sealed before any run).
# ----------------------------------------------------------------------------
TABLE_KEYS: frozenset = frozenset(
    set(getattr(B73, "REL_MENTION_CUES", {}))
    | set(getattr(B92, "REL_CUES92", {}))
    | set(getattr(B92, "EXTRA_REL_CUES", {})))
PERSON_KEYS: frozenset = frozenset(A.PERSON_RELATIONS)
OFFICE_KEYS: frozenset = frozenset(F135.OFFICE_RELATIONS)
ALLOWED_KEYS: frozenset = (TABLE_KEYS | PERSON_KEYS) - OFFICE_KEYS

# Relation surface shape: letters/spaces/slash/hyphen only (no apostrophe,
# comma, period, question -- hedged/two-fact remainders never match).
_REL_SHAPE = re.compile(r"[A-Za-z][A-Za-z /-]*")
_QUESTION_LEAD = re.compile(r"^(who|what|where)\s+(is|are)\b",
                            re.IGNORECASE)
_CORRECTION_LEAD = re.compile(
    r"^(actually\s*,|actually\s+|no\s*,|no\s+)(.+)$",
    re.IGNORECASE | re.DOTALL)
_APOS = r"(?:['\u2019]s)"
_FRAME1 = re.compile(r"(.+?)\s+is\s+(.+?)" + _APOS + r"\s+(.+?)\s*$",
                     re.IGNORECASE | re.DOTALL)
_FRAME2 = re.compile(r"(.+?)\s+is\s+the\s+(.+?)\s+of\s+(.+?)\s*$",
                     re.IGNORECASE | re.DOTALL)
_FRAME3 = re.compile(r"the\s+(.+?)\s+of\s+(.+?)\s+is\s+(.+?)\s*$",
                     re.IGNORECASE | re.DOTALL)


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def relation_key(surface: str) -> str | None:
    """Relation surface -> loop relation key, or None when not allowed.

    Allowed = key in the loop's own tables (cue-table keys + person table),
    minus the office family; the surface must also not be an exp-135 office
    head (president/mayor/director/... stay on the base path exactly).
    """
    text = _norm(surface)
    if not _REL_SHAPE.fullmatch(text):
        return None
    key = "_".join(text.lower().split())
    if key not in ALLOWED_KEYS:
        return None
    if F135.is_office_head(text.lower()):
        return None
    return key


def parse_inverted_frame(turn: str) -> dict | None:
    """Raw turn -> {frame, X, Rsurf, key, V, correction} or None.

    Strict full-turn match on the three sealed frames only; questions,
    forget shapes and correction-less non-frames never match.
    """
    text = _norm(turn)
    if not text or text.rstrip().endswith("?"):
        return None
    if _QUESTION_LEAD.match(text):
        # "who is ned's teacher" (no "?"): the base answers it as a
        # question; an inverted parse would see V="who" and mint a wrong
        # write via the canonical twin. Never a teach frame.
        return None
    body = text
    if body.endswith(".") and not body.endswith(".."):
        body = body[:-1].strip()
    if not body:
        return None
    correction = False
    m = _CORRECTION_LEAD.match(body)
    if m and m.group(2).strip():
        correction, body = True, m.group(2).strip()
    low_body = body  # regexes are case-insensitive; spans keep raw case
    got = None
    m = _FRAME1.fullmatch(low_body)
    if m:
        got = ("F1", m.group(2).strip(), m.group(3).strip(),
               m.group(1).strip())
    if got is None:
        m = _FRAME2.fullmatch(low_body)
        if m:
            got = ("F2", m.group(3).strip(), m.group(2).strip(),
                   m.group(1).strip())
    if got is None:
        m = _FRAME3.fullmatch(low_body)
        if m:
            got = ("F3", m.group(2).strip(), m.group(1).strip(),
                   m.group(3).strip())
    if got is None:
        return None
    frame, X, Rsurf, V = got
    if not X or not V or "?" in X or "?" in V or ";" in X or ";" in V:
        return None
    key = relation_key(Rsurf)
    if key is None:
        return None
    return {"frame": frame, "X": X, "Rsurf": _norm(Rsurf), "key": key,
            "V": V, "correction": correction}


def _base_has_real_teach(actions: list[dict]) -> bool:
    """True when the base already teaches/corrects a non-officeholder slot."""
    for a in actions:
        if (isinstance(a, dict) and a.get("act") in ("teach", "correct")
                and a.get("relation") != "officeholder"):
            return True
    return False


def _canonical_sentence(parsed: dict) -> str:
    prefix = "Actually, " if parsed["correction"] else ""
    return (f"{prefix}{parsed['X']}'s {parsed['Rsurf']} "
            f"is {parsed['V']}")


class InvertedFrame155Mixin:
    """Stackable mixin: inverted-frame teaches for table relations.

    Cooperative (super() first): the base hear runs untouched; only when it
    yields no non-officeholder teach/correct AND the turn strictly matches
    an inverted frame with an allowed relation does this stage produce the
    canonical-equivalent teach. Same shape as SubjectGuard150Mixin.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        base = super().hear(turn)  # type: ignore[misc]
        kinds = {a.get("act") for a in base if isinstance(a, dict)}
        if kinds - {"clarify", "teach", "correct"}:
            # ask/answer/forget/alias/person paths (incl. "?"-less
            # questions like "who is ned's teacher"): base owns them.
            return base
        parsed = parse_inverted_frame(turn)
        if parsed is None:
            return base
        if _base_has_real_teach(base):
            return base  # bench-known sentence: base wins byte-identical
        X, key, V = parsed["X"], parsed["key"], parsed["V"]
        if " " not in X:
            out = super().hear(_canonical_sentence(parsed))  # type: ignore[misc]
            for a in out:
                if (isinstance(a, dict)
                        and a.get("act") in ("teach", "correct")
                        and (a.get("name"), a.get("relation"),
                             a.get("value")) == (X, key, V)):
                    self.last_stage, self.last_score = (  # type: ignore[attr-defined]
                        "loop155-inverted", 1.0)
                    return out
            return base
        # Multi-word X: no canonical possessive exists (FakeEars is
        # one-word-names-only); build the bench-shaped structured action and
        # return it only when every canonical-side screen passes.
        if L102.subject_is_hearsay_shaped(X):
            return base
        if L121.screen_value_121(V) is not None:
            return base
        verdict, payload = S150.screen_subject_150(X)
        if verdict != "store":
            return base
        stage = L90.Bench73Stage()
        stage.bind(self.nb)  # type: ignore[attr-defined]
        action = stage._teach_action((payload, key, V))
        action["is_person"] = key in PERSON_KEYS  # mirror FakeEars, not bench
        action["stage"] = "loop155"
        self.last_stage, self.last_score = (  # type: ignore[attr-defined]
            "loop155-inverted", 1.0)
        return [action]
