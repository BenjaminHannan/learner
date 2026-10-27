#!/usr/bin/env python3
"""Exp 291 glue -- two narrow interaction rules where 138nb's reading line
meets 260's opener handling (additive, 291 only; every other module is
imported read-only).

Background (design/v3/30-modes/291-join-muse.md + pilot amendment): on the
138m base, opener-led teaches ("so Marnie lives in Tollan.") either save
through the base ears or clarify in words 260 recognises, so 260's
strip-and-rerun path saves them cleanly. On the 138nb base two reading
layers claim those turns first:

G1. 229 table-teach parses "so Marnie ..." with subject "so Marnie" and
    refuses ("I did not save that: I read it as ... does not look like a
    name."). That clarify shape is not in 260's CLARIFY_MARKS260, and
    there is no comma, so 260's turn260 returns the refusal without ever
    stripping. (The stripped rest saves fine on its own.) A first attempt
    (skip 229 on opener-led turns) was REJECTED in the pilot: 229's verdict
    is load-bearing input for 252's correction logic ("Actually, Hesta
    lives in Lowick, not Umbry" broke), and 229's saves are 260's
    registered behaviour on titles ("Hey Jude", "So Long Summer").
G2. 137 filler-teach writes opener-led subjects with no comma ("Hi
    Orrin"), which 260's comma-only junk-subject guard does not catch, so
    the original writes junk and 260 (which never overrides a write) keeps
    it. A first attempt (guard every opener-led teach subject) was
    REJECTED in the pilot: it mangled titles 260 keeps ("Hey Jude",
    "So Long Summer"). 138m's own verdicts split exactly on the
    apostrophe: verb teaches with opener-led subjects clarify on 138m
    ("Hi Orrin lives in Varn.", "Hey Jude lives in Varn."), while
    possessive titles save whole ("Hey Jude's writer is Fenn.").
    Corrections/denials ("not", "n't", "it's", "that's") carry
    apostrophes too.

Rules (questions never match):

R1 (refusal rerun): the outermost turn wrapper. When the whole head
    returns exactly 229's no-save clarify on a statement turn that begins
    with a 260-listed opener/greeting AND carries no denial marker (not /
    n't / never -- corrections and denials keep 229's reply verbatim), the
    stripped rest is run through the whole head; the rest reply wins only
    when the rest wrote or is not itself a clarify, else the original
    stands. Titles are untouched (229 saves them, so no refusal fires).
R2 (junk-subject guard): a teach/correct action whose subject starts with
    a 260-listed opener/greeting word is replaced by 260's own clarify
    action -- but ONLY on plain active-verb turns: turns with an
    apostrophe (possessive titles, corrections, denials, particle names),
    denial markers (not / n't / never), or passive-agent shape (was/were
    ... by, where 138m and 138nb's loop121 layer both keep title subjects
    whole) always pass through. Guarded at ears-hear and at _act level
    (outside 260's own guards); 260 then strips and re-runs the rest.

New file only; no existing file is edited.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix260_openers as F260  # noqa: E402 (lists + clarify, read-only)

_GUARD_ALT291 = "|".join(
    F260._phrase_re(p) for p in
    sorted(set(F260._GUARD_WORDS), key=lambda s: (-len(s), s)))
# Subject starting with a listed opener/greeting word (comma or not).
_JUNK_SUBJECT_RE291 = re.compile(
    r"^\s*(?:" + _GUARD_ALT291 + r")(?:[\s,]+(?:" + F260._TAIL_ALT + r")){0,2}"
    r"(?=[\s,!.:\-–—]|$)", re.IGNORECASE)
# 229's no-save clarify prefix (G2 may rewrite the reason tail).
_NOSAVE_PREFIX291 = "I did not save that:"
# Denial markers: corrections/denials never rerun (229's reply stands).
_DENIAL_RE291 = re.compile(r"\bnot\b|n['\u2019]t\b|\bnever\b",
                           re.IGNORECASE)
# Passive-agent shape (was/were ... by): 138m and the loop121 layer keep
# title subjects whole ("Hey Jude was performed by ...").
_PASSIVE_BY_RE291 = re.compile(r"\bwas\b.*\bby\b|\bwere\b.*\bby\b",
                               re.IGNORECASE)


def starts_with_opener291(turn: str) -> bool:
    """A statement turn 260 would try to strip (listed opener present)."""
    t = str(turn or "")
    if not t.strip() or t.rstrip().endswith("?"):
        return False
    try:
        return F260.split_openers260(t) is not None
    except Exception:  # noqa: BLE001 -- never break the base turn
        return False


def junk_subject291(name) -> bool:
    """A teach subject starting with a listed opener/greeting word."""
    return bool(_JUNK_SUBJECT_RE291.match(str(name or "")))


def _junk_action291(a, turn: str) -> bool:
    # Shape parity with 138m (which never writes opener-led subjects on
    # plain active-verb teaches, but saves possessive/passive titles
    # whole): possessive/correction/denial apostrophes, denial markers
    # and passive-agent turns always pass through.
    t = str(turn or "")
    if "'" in t or "\u2019" in t:
        return False
    if _DENIAL_RE291.search(t) or _PASSIVE_BY_RE291.search(t):
        return False
    if not (isinstance(a, dict) and a.get("act") in ("teach", "correct")):
        return False
    return junk_subject291(a.get("name") or a.get("subject"))


def _inner_ears(loop):
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        ears = getattr(loop, "ears", None)
        inner = getattr(ears, "inner", None) or ears
    if inner is None:
        raise RuntimeError("glue291: no inner ears")
    return inner


def _nb_events(loop) -> int:
    try:
        return len(loop.nb.events)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return -1


def install_guards291(loop) -> None:
    """Outer hear/_act junk-subject guards (R2), outside 260's own guards."""
    inner = _inner_ears(loop)
    if not hasattr(loop, "glue291_log"):
        loop.glue291_log = []
    loop.glue291_turn = ""
    ears_hear = inner.hear

    def hear291(turn, _h=ears_hear):
        loop.glue291_turn = str(turn)
        acts = _h(turn)
        if isinstance(acts, list) and any(
                _junk_action291(a, turn) for a in acts):
            loop.glue291_log.append({"guard": "ears", "turn": str(turn)})
            return [dict(F260.CLARIFY_ACTION260)]
        return acts

    inner.hear = hear291
    class_act = loop._act

    def act291(action, _a=class_act):
        if _junk_action291(action, getattr(loop, "glue291_turn", "")):
            loop.glue291_log.append({"guard": "act",
                                     "act": action.get("act")})
            try:
                loop.counters["clarifications"] += 1
            except Exception:  # noqa: BLE001
                pass
            return {"kind": "clarify",
                    "text": F260.CLARIFY_ACTION260["text"]}
        return _a(action)

    loop._act = act291
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("glue291" in n for n in notes):
        notes.append("glue291: opener-led teach subjects clarify (R2); "
                     "229-refusal rerun on opener-led pure teaches (R1)")


def install_turn291(loop) -> None:
    """Outermost turn wrapper (R1): rerun the stripped rest only when the
    head returns exactly 229's no-save clarify on an opener-led pure
    teach (statement, listed opener, no denial marker)."""
    inner_turn = loop.turn  # turn260(...)
    loop.turn291_inner = inner_turn
    if not hasattr(loop, "glue291_log"):
        loop.glue291_log = []

    def turn291(text: str):  # type: ignore[no-untyped-def]
        t = str(text)
        s0 = F260.snapshot260(loop)
        e0 = _nb_events(loop)
        r0 = inner_turn(t)
        if _nb_events(loop) != e0:
            return r0  # something wrote: keep it, as 260 does
        if (not isinstance(r0, list) or len(r0) != 1
                or not str(r0[0]).startswith(_NOSAVE_PREFIX291)):
            return r0  # not 229's refusal: pass through
        if t.rstrip().endswith("?") or _DENIAL_RE291.search(t):
            return r0  # questions and denials keep 229's reply
        try:
            sp = F260.split_openers260(t)
        except Exception:  # noqa: BLE001
            return r0
        if sp is None:
            return r0
        rest = F260.recase_rest260(sp[0])
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        r1 = loop.turn(rest)
        wrote = _nb_events(loop) != e0
        if not wrote and F260.is_clarify_reply260(r1):
            F260.restore260(s1)
            return r0  # rest not understood either: keep the original
        loop.glue291_log.append({"rerun": rest})
        return r1

    turn291.__name__ = "turn291"
    loop.turn = turn291
    return loop
