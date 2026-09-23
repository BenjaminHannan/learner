#!/usr/bin/env python3
"""Exp 213 PART A — EARS WRITE SAFETY MAP (Muse BUILD).

The review finding (director-verified): when an ears frame is rendered into
a notebook item, ``pick_surface`` (fable_ears47_score.py:179-218) falls back
to "any content word in the sentence", and ``canonical_relation`` turns that
word into a relation name which the listening validator then accepts::

    "Aldric Venmore is a Norvish pianist."  -> relation 'norvish'
    a date of birth                         -> relation 'birthplace'

The scorers only judge the frame's CLASS, never the rendered item.

THE FIX (scorer side; no training; verdict code untouched):
  * ``RELMAP``: the ONLY ears classes that may ever be written, each mapped
    to its notebook relation. Every class not in this table is ECHO-only and
    can never be written — there is no content-word fallback anywhere here.
  * ``render``: frame -> notebook item using ONLY the table (fixed
    per-class surface wording; zero dependence on sentence content words).
  * ``expected_from_gold47`` + ``judge``: score the RENDERED item
    (relation + subject + value) against gold, which Part B uses for the
    Learn-then-Test gate.

Table discipline: a class is listed ONLY if the frame's (subject, object)
spans directly state that notebook relation. When in doubt the class stays
out (ECHO-only). In particular there is deliberately NO entry for
'country of citizenship' (no notebook citizenship relation), 'spouse' /
'child' (no notebook spouse/child relation), 'creator' (notebook creator
direction convention is opposite to the frame direction, so not "clear"),
'capital' / 'capital of' (states office, not residence), or 'origin'
(no single ears class clearly means hometown).

Notebook relations used: LE.KNOWN_RELATIONS where they exist
(city, birthplace, mother, father, sibling, friend, employer, age) plus
three newly DECLARED literal relations (occupation, date_of_birth,
date_of_death). The notebook contract allows declaring relations
(declare_relation); the listening validator's copy constraint is satisfied
because rendered subject/value are verbatim utterance spans and the fixed
surface wordings below are ordinary English for the relation.

Additive only: fable_listening_english / fable_ears47_data imported
read-only, never edited. No torch import (probe runs anywhere).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE  # noqa: E402 (read-only)
import fable_ears47_data as D  # noqa: E402 (read-only class names)

# ------------------------------------------------------------------ the table
# ears class (D.CLASSES name) -> notebook relation. ONLY these may be written.
RELMAP: dict[str, str] = {
    "residence": "city",              # "X lives in Y" -> X's city is Y
    "birthplace": "birthplace",       # class name IS the notebook relation
    "place of birth": "birthplace",   # same relation, WebRED spelling
    "date of birth": "date_of_birth",       # literal date relation (declared)
    "date of death": "date_of_death",       # literal date relation (declared)
    "occupation": "occupation",       # job relation (declared)
    "mother": "mother",
    "father": "father",
    "sibling": "sibling",
    "friend": "friend",
    "employer": "employer",
    "age": "age",
}

# Fixed surface wording per ears class. Deterministic, table-only: render
# NEVER inspects sentence content words (that inspection was the bug).
SURFACE: dict[str, str] = {
    "residence": "lives in",
    "birthplace": "born in",
    "place of birth": "birthplace",
    "date of birth": "born on",
    "date of death": "died on",
    "occupation": "works as",
    "mother": "mother",
    "father": "father",
    "sibling": "sibling",
    "friend": "friend",
    "employer": "works for",
    "age": "years old",
}

# Relations the notebook must declare (KNOWN + the three new literal ones).
NEW_LITERAL_RELATIONS = ("occupation", "date_of_birth", "date_of_death")
NOTEBOOK_RELATIONS = set(LE.KNOWN_RELATIONS) | set(NEW_LITERAL_RELATIONS)

WRITE_ACTS = {"STATE", "RETRACT"}
PRON_BEN = {"i", "me", "my", "mine", "myself"}
PRON_SELF = {"you", "your", "yours", "yourself"}
PRON_BAD = {"he", "him", "his", "she", "her", "hers", "they", "them",
            "their", "theirs", "it"}


def check_table() -> list[str]:
    """Self-check: every table key is a real ears class, every value a
    notebook relation, every key has a fixed surface. Returns error list."""
    errs = []
    classes = set(D.CLASSES["classes"])
    for cls, rel in RELMAP.items():
        if cls not in classes:
            errs.append(f"class not in D.CLASSES: {cls!r}")
        if rel not in NOTEBOOK_RELATIONS:
            errs.append(f"relation not writable: {cls!r} -> {rel!r}")
        if cls not in SURFACE:
            errs.append(f"class has no fixed surface: {cls!r}")
    for rel in NEW_LITERAL_RELATIONS:
        if rel in LE.KNOWN_RELATIONS:
            errs.append(f"new relation already known: {rel!r}")
    return errs


# ------------------------------------------------------------------- rendering
def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s.casefold()).strip()


def render(frame: dict, utt: str, chspans) -> dict | None:
    """Frame -> notebook item dict, or None (ECHO-only: never written).

    Returns None unless: act is STATE/RETRACT, the class is in RELMAP, and
    the required spans exist. Subject/value are verbatim utterance spans
    (pronoun-mapped exactly as S47.decode: Ben/self kept, third-person
    pronouns refuse). The relation comes ONLY from RELMAP; the surface
    ONLY from SURFACE. No content-word fallback exists in this function.
    """
    if frame is None:
        return None
    act = frame.get("act")
    if act not in WRITE_ACTS:
        return None
    rel_str = frame.get("rel")
    if rel_str not in RELMAP:
        return None                      # ECHO-only class: never written
    nb_rel = RELMAP[rel_str]
    subj_span = frame.get("subj")
    if not subj_span:
        return None
    s, e = subj_span
    try:
        subj_txt = utt[chspans[s][0]:chspans[e][1]]
    except (IndexError, TypeError):
        return None
    low = subj_txt.casefold()
    if low in PRON_BAD:
        return None                      # cannot attribute: never written
    if low in PRON_BEN:
        subj_txt = "Ben"
    elif low in PRON_SELF:
        subj_txt = "self"
    item_act = "forget" if act == "RETRACT" else (
        "correct" if LE._has_correction_cue(utt) else "teach")
    if act == "STATE":
        obj_span = frame.get("obj")
        if not obj_span:
            return None
        s, e = obj_span
        try:
            val_txt = utt[chspans[s][0]:chspans[e][1]]
        except (IndexError, TypeError):
            return None
        if not val_txt.strip():
            return None
        value_kind = ("person" if rel_str in D.PERSON_CLASSES else "literal")
    else:                                # RETRACT carries subject+relation only
        val_txt, value_kind = None, "none"
    return {"act": item_act, "subject": subj_txt,
            "relation_path": [nb_rel],
            "relation_surface": [SURFACE[rel_str]],
            "value": val_txt, "value_kind": value_kind}


# ------------------------------------------------- judging the rendered item
def expected_from_gold47(row: dict) -> tuple | None:
    """Gold47 row -> expected (relation, subject, value) triple, or None
    meaning NO WRITE is expected (abstain golds, unmapped classes, OPEN,
    missing spans). Uses RAW gold rel names (no 119e REMAP): the question
    is what the sentence states, rendered through the same table."""
    g = row.get("gold47") or {}
    if g.get("act") not in WRITE_ACTS or not g.get("rep"):
        return None
    rel = g.get("rel")
    if rel not in RELMAP:
        return None                      # gold itself is ECHO-only
    utt = D.row_text(row)
    subj, obj = g.get("subj"), g.get("obj")
    if not subj:
        return None
    try:
        subj_txt = utt[subj[0]:subj[1]]
    except (IndexError, TypeError):
        return None
    if g["act"] == "STATE":
        if not obj:
            return None
        try:
            obj_txt = utt[obj[0]:obj[1]]
        except (IndexError, TypeError):
            return None
    else:
        obj_txt = ""
    if not subj_txt.strip():
        return None
    return (_norm(RELMAP[rel]), _norm(subj_txt), _norm(obj_txt or ""))


def triple_of(item: dict | None) -> tuple | None:
    """Rendered item -> normalised (relation, subject, value) triple."""
    if item is None:
        return None
    if item.get("act") == "forget":
        return (_norm((item.get("relation_path") or [""])[0]),
                _norm(item.get("subject")), "")
    return (_norm((item.get("relation_path") or [""])[0]),
            _norm(item.get("subject")), _norm(item.get("value") or ""))


def judge(rendered: dict | None, expected: tuple | None) -> bool:
    """True iff the rendered item matches gold: both None (correct
    abstention), or equal normalised triples. A write where none is
    expected, or no write where one is expected, is False."""
    if expected is None:
        return rendered is None
    if rendered is None:
        return False
    return triple_of(rendered) == tuple(expected)


def judge_against_reading_gold(rendered: dict | None,
                               gold_set: set[tuple]) -> bool | None:
    """Rendered item vs a reading-panel gold triple set (raw labeller
    relation strings). None = no write was rendered (abstain). NOTE: the
    vocabularies differ (notebook 'city' vs labeller wording), so a
    semantically right render can count wrong here; that is CONSERVATIVE
    for safety (over-counts wrong, never hides it)."""
    if rendered is None:
        return None
    return triple_of(rendered) in set(gold_set)
