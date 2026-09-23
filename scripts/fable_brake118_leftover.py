#!/usr/bin/env python3
"""Exp 118 — LEFTOVER BRAKE for the sealed ears-rung-2 checkpoints (design doc 118).

Single change, plain software, CPU only, no retraining: after the ears propose
a frame, if the sentence contains content words outside the frame's
subject/value spans (beyond a fixed allow-list of function words plus the
predicted relation's own cue words), the write is refused (downgraded from
EXECUTE to ECHO/REPHRASE).

Word lists were defined BEFORE looking at any panel result:
  * FUNCTION_WORDS_V1 — closed-class English + copula/aux + generic discourse
    interjections (general knowledge, no panel input).
  * RELATION_CUE_WORDS — derived ONLY from code tables (the predicted class
    name tokens, closed_map surfaces, LE.RELATION_MAP surfaces that canonicalise
    to the predicted class). Never from panels.
Tuning on the CAL split only (see scripts/fable_brake118_tune.py) added a small
set of framing words observed in CAL correct STATE rows (CAL_FRAMING_V2); no
test-panel token was ever added (verified by construction: additions required a
CAL-correct occurrence).

Usage:
    from fable_brake118_leftover import leftover_blocks
    blocked, reason, leftovers = leftover_blocks(text, frame, chspans)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE  # noqa: E402 (read-only: relation surfaces)
import fable_ears47_data as D  # noqa: E402 (read-only: class tables)

WRITE_ACTS = {"STATE", "RETRACT"}

# ---------------------------------------------------------------------------
# V1: closed-class English + copula/aux + generic interjections.
# Fixed a priori (general knowledge of English grammar), before any panel read.
# ---------------------------------------------------------------------------
FUNCTION_WORDS_V1 = frozenset("""
a an the this that these those my your his her its our their
is are was were be been being am do does did done have has had having
will would shall should can could may might must ought
's 're 've 'll 'd n't not never no longer
and or but nor yet so for of in on at to from with by as about into over
after before between through during without within along across around
up down out off again once here there where when why how what which who whom
whose if then than too very just only also even still already yet quite rather
more most much many few little own same other another such
i me my mine myself you your yours yourself he him his she her hers
it its they them theirs we us ours
please thanks thank hello hi hey well oh um uh alright okay ok btw fyi wait
""".split())

# ---------------------------------------------------------------------------
# V2: framing words added by CAL-only tuning (each occurs in a CAL correct
# STATE row that V1 blocked; none comes from any test panel).
# Tuned 2026-09-22 on CAL only; see fable_brake118_tune_cal.json for counts.
# Initial value: empty. The tune script (fable_brake118_tune.py, CAL only)
# proposes additions; they are committed here only with CAL counts.
# ---------------------------------------------------------------------------
CAL_FRAMING_V2 = frozenset("""
one keep mind hmm quick way listen thing actually meant say
""".split())

ALLOW_WORDS = FUNCTION_WORDS_V1 | CAL_FRAMING_V2

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _cue_words_for_rel(rel: str) -> set[str]:
    """Cue words for a predicted relation class, from code tables only."""
    cues: set[str] = set()
    if not rel:
        return cues
    cues.update(_WORD_RE.findall(rel.casefold()))
    cm = D.CLASSES.get("closed_map") or {}
    for endpoint in (cm.get(rel),):
        if endpoint:
            cues.update(_WORD_RE.findall(endpoint.casefold()))
    for surface, key in LE.RELATION_MAP.items():
        try:
            can = LE.canonical_relation(surface)
        except Exception:
            continue
        if key == rel or can == rel.casefold() or surface.casefold() == rel.casefold():
            cues.update(_WORD_RE.findall(surface.casefold()))
    return {w for w in cues if len(w) > 1}


def _word_list(text: str) -> list[tuple[str, int, int]]:
    """(lowercased word minus possessive, char_start, char_end) per word."""
    out = []
    for m in _WORD_RE.finditer(text):
        w = m.group(0).casefold()
        if w.endswith("'s"):
            w = w[:-2]
        s, e = m.start(), m.end()
        # trim a leading apostrophe remnant (e.g. "'s" alone handled by len rule)
        out.append((w, s, e))
    return out


def leftover_blocks(text: str, frame: dict | None, chspans) -> tuple[bool, str, list[str]]:
    """Return (blocked, reason, leftover_words).

    blocked=True means: the proposed write covers only part of the sentence;
    unconsumed content words remain, so the write must be refused.
    Never blocks abstain frames (they never EXECUTE anyway) or frames without
    usable spans (decode already refuses those via ok4=False paths).
    """
    if frame is None:
        return False, "no-frame", []
    if frame.get("act") not in WRITE_ACTS:
        return False, "not-a-write", []
    subj = frame.get("subj")
    obj = frame.get("obj")
    if not subj:
        return False, "no-subj-span", []
    if frame["act"] == "STATE" and not obj:
        return False, "no-obj-span", []
    if chspans is None:
        return False, "no-chspans", []
    try:
        cs, ce = chspans[subj[0]][0], chspans[subj[1]][1]
        covered = [(cs, ce)]
        if obj:
            vs, ve = chspans[obj[0]][0], chspans[obj[1]][1]
            covered.append((vs, ve))
    except (IndexError, TypeError):
        return False, "span-out-of-range", []

    cues = _cue_words_for_rel(frame.get("rel"))

    def _covered(ws: int, we: int) -> bool:
        return any(ws < e and we > s for s, e in covered)

    leftovers: list[str] = []
    for w, ws, we in _word_list(text):
        if len(w) < 2:
            continue
        if _covered(ws, we):
            continue
        if w in ALLOW_WORDS:
            continue
        if w in cues:
            continue
        leftovers.append(w)
    if leftovers:
        return True, "leftover-content:%s" % ",".join(sorted(set(leftovers))[:8]), leftovers
    return False, "fully-consumed", []
