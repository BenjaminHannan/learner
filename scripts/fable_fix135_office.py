#!/usr/bin/env python3
"""Experiment 135 -- officeholder catch-all guard (ONE CHANGE, mixin).

Registered single-change fix for a confident wrong write the director found
in a held-out probe: in scripts/fable_bench73_english_arm.py STATEMENT_PATTERNS
the last pattern is a catch-all officeholder frame ``The (.+?) is (.+?)``,
so "The mother of Dara Fenn is Ora Fenn." is saved as
('mother of Dara Fenn', 'officeholder', 'Ora Fenn') -- likewise "The father
of Tom is Bob." and "The boss of Tom is Bob." (director reproduced on
loop129a and loop129b). Presumably ANY "The <anything> is <anything>."
sentence is written.

THE ONE CHANGE: the officeholder catch-all fires only when the head phrase
(text before " of ") is an office title drawn mechanically from the existing
code tables (see OFFICE_TITLE_SOURCES below); otherwise the sentence falls
through to whatever the loop does with an unparsed sentence (no write).
No routing of "The mother of X is Y" to the mother relation is added here
(that is a separate later change).

Stacking: OfficeholderGuardMixin only overrides hear(); it patches
fable_bench73_english_arm.hear_teach_template with the guarded version for
the duration of super().hear(turn) and restores it in a finally block, so
the wrapped loop's teach logic (loop121 patterns, exp-92 extras, guards,
question side) runs byte-identical otherwise. Tonight's integration can
stack it with other mixins via normal multiple inheritance, e.g.
class LoopNextEars(OtherMixin, OfficeholderGuardMixin, Loop129bEars).

No existing file is edited; everything new lives in this file (+
scripts/fable_loop135_agent.py, which is loop129b + this mixin).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (read-only, never edited)
import fable_bench92_english_arm as B92  # noqa: E402 (read-only, never edited)

# Original unguarded template parse, bound at import time. hear_teach135 must
# call THIS (not B73.hear_teach_template, which the mixin transiently
# repoints at hear_teach135 itself during hear()).
_hear_teach_template_orig = B73.hear_teach_template

# ----------------------------------------------------------------------------
# Mechanical title derivation (no hand-picked titles).
# ----------------------------------------------------------------------------
# Relations whose cue lists count as "office" tables. The first five are the
# brief's list (officeholder / head_of_state / head_of_government /
# chairperson / chief_executive_officer in the bench73 + bench92 modules).
# The last three (director_manager / head_coach / original_broadcaster, bench92
# only) are REQUIRED additions, with measured evidence: the loop's catch-all
# demonstrably fires for those sentences today -- 110 such teaches in
# data/open/bench103/fable_edit103_s2fresh_4hop.jsonl and 132 in
# data/open/bench121/fable_edit121_4hop.jsonl -- so excluding them would turn
# the registered K2 bench into a regression.
OFFICE_RELATIONS = (
    "officeholder",
    "head_of_state",
    "head_of_government",
    "chairperson",
    "chief_executive_officer",
    "director_manager",
    "head_coach",
    "original_broadcaster",
)

OFFICE_TITLE_SOURCES = (
    "fable_bench73_english_arm.REL_MENTION_CUES",
    "fable_bench92_english_arm.REL_CUES92",
    "fable_bench92_english_arm.EXTRA_REL_CUES",
    "literal 'The <head> of' pattern heads for office-like relations in "
    "fable_bench73_english_arm.STATEMENT_PATTERNS + "
    "fable_bench92_english_arm.EXTRA_STATEMENT_PATTERNS",
)


def _cue_table(module, attr: str) -> dict:
    table = getattr(module, attr, {})
    return dict(table) if isinstance(table, dict) else {}


def _normalize_cue(cue: str) -> str:
    """Lowercase a cue phrase; drop a trailing ' of' / ' of the' preposition."""
    c = " ".join(str(cue).lower().split())
    for tail in (" of the", " of"):
        if c.endswith(tail) and len(c) > len(tail):
            c = c[: -len(tail)]
            break
    return c.strip(" .")


def _pattern_head_literals() -> set[str]:
    """Literal 'The <head> of' heads from office-like statement patterns.

    Mechanical: for every compiled pattern in STATEMENT_PATTERNS (bench73)
    and EXTRA_STATEMENT_PATTERNS (bench92), take the pattern source text; if
    it starts with 'The ' and contains ' of' before the first regex group,
    the literal words between them are a head (e.g. 'director', 'head coach',
    and the data's misspelt 'origianl broadcaster' in the bench92 pattern).
    Heads belonging to non-office relations are skipped -- the catch-all only
    needs office heads, and specific patterns match their own sentences first.
    """
    heads: set[str] = set()
    tables: list = [list(B73.STATEMENT_PATTERNS),
                    list(B92.EXTRA_STATEMENT_PATTERNS)]
    for table in tables:
        for pat, rel in table:
            if rel not in OFFICE_RELATIONS:
                continue
            src = pat.pattern
            m = re.match(r"^The ([A-Za-z /-]+?) of[ (]", src)
            if m:
                heads.add(" ".join(m.group(1).lower().split()))
    return heads


def build_office_titles() -> dict:
    """Build the title set mechanically from the code tables.

    Returns {"singles": [...], "phrases": [...], "sources": [...]} with sorted
    lists. Singles match a whole head or any whole whitespace-separated token
    of a head; phrases match a whole head exactly.
    """
    cues: set[str] = set()
    for module, attr in ((B73, "REL_MENTION_CUES"), (B92, "REL_CUES92"),
                         (B92, "EXTRA_REL_CUES")):
        for rel in OFFICE_RELATIONS:
            for cue in _cue_table(module, attr).get(rel, []):
                norm = _normalize_cue(cue)
                if norm:
                    cues.add(norm)
    cues |= _pattern_head_literals()
    singles = sorted({c for c in cues if " " not in c})
    phrases = sorted({c for c in cues if " " in c})
    return {"singles": singles, "phrases": phrases,
            "sources": list(OFFICE_TITLE_SOURCES)}


_TITLES = build_office_titles()
OFFICE_SINGLE_TITLES: frozenset = frozenset(_TITLES["singles"])
OFFICE_PHRASE_TITLES: frozenset = frozenset(_TITLES["phrases"])


def office_head_of(subject: str) -> str:
    """Head phrase of a catch-all subject: text before ' of ' (else all)."""
    s = " ".join(str(subject).split())
    if " of " in f" {s} ":
        return s.split(" of ", 1)[0].strip().lower()
    return s.strip().lower()


def is_office_head(head: str) -> bool:
    """True when head is a table-derived office title.

    Whole-head equality against singles + phrases, or any single-word title
    appearing as a whole whitespace-separated token of the head (covers
    "vice president", "assistant coach", ...). Multi-word titles match whole
    heads only ("prime minister", "chief executive officer", "head coach",
    "original broadcaster", ...).
    """
    h = " ".join(str(head).lower().split())
    if not h:
        return False
    if h in OFFICE_SINGLE_TITLES or h in OFFICE_PHRASE_TITLES:
        return True
    return any(tok in OFFICE_SINGLE_TITLES for tok in h.split())


def hear_teach135(sentence: str) -> tuple[str, str, str] | None:
    """bench73 template parse with the officeholder catch-all guarded.

    Identical to fable_bench73_english_arm.hear_teach_template except: an
    officeholder triple whose head phrase is not a table-derived office title
    returns None (falls through to the loop's unparsed-sentence path, no
    write). Every other relation passes through untouched.
    """
    triple = _hear_teach_template_orig(sentence)
    if triple is None:
        return None
    subj, rel, _obj = triple
    if rel != "officeholder":
        return triple
    if is_office_head(office_head_of(subj)):
        return triple
    return None


class OfficeholderGuardMixin:
    """Stackable mixin: guard the officeholder catch-all during hear().

    Overrides hear() only. For the duration of super().hear(turn) the module
    attribute fable_bench73_english_arm.hear_teach_template is pointed at
    hear_teach135 (the wrapped loop calls it by module attribute, so both
    the direct teach path and bench92's hear_teach92 bench73-first path see
    the guard); it is restored in a finally block. In-process suites run
    serially, so the transient patch is safe.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        original = B73.hear_teach_template
        B73.hear_teach_template = hear_teach135  # type: ignore[method-assign]
        try:
            return super().hear(turn)  # type: ignore[misc]
        finally:
            B73.hear_teach_template = original


def title_list_report() -> dict:
    """The mechanically derived title list, for the artifact dir."""
    built = build_office_titles()
    return {"singles": built["singles"], "phrases": built["phrases"],
            "sources": built["sources"],
            "note": ("king/queen/monarch/emperor are NOT in these tables, "
                     "so they fall through to didn't-understand by design; "
                     "mother/father/boss/friend/teacher/weather/sky/cat and "
                     "possessions likewise.")}


if __name__ == "__main__":
    import json
    print(json.dumps(title_list_report(), indent=1))
