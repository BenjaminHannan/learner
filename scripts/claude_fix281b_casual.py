#!/usr/bin/env python3
"""Exp 281b -- THE ONE CHANGE: 281's called/named reader also accepts the
same question typed casually.

Base: 281 (scripts/claude_loop281_agent.py + its config, read-only).
New file only. Outermost instance turn wrapper turn281b over turn281.

DIAGNOSIS (reproduced live on 281 with own dev turns, 2026-09-23):
  - "What is Ana's cat called?" (formal) answers; the same question as
    "whats Cleo's boat called?" clarifies, "What is Dara's band called"
    (no "?") gives the broken "I don't know Dara's band called.",
    "whats elifs street called" (all casual) gets a save-error, and
    "what do you call gretas boss" (no "?") clarifies -- all while the
    fact is stored. Only lowercase+no-apostrophe WITH "?" already works.
  - "What's X's R called?" never matches 281 (its trailing shape needs
    "what is"/"who is"), so it is casual-scope too.

THE RULE (turn281b, outermost, instance):
  1. Formal turns 281 already rewrites are untouched (normalize returns
     None; the 281 path runs byte-identical, stores included).
  2. Otherwise, on a turn that ends with "?" or -- only when the turn (or
     its opener-stripped core) starts with a question word -- has no "?",
     and that carries a called/named cue, build a formal called-wording:
     leading "whats"/"what's" (any case) -> "What is"; a possessive
     written without its apostrophe ("anas") is restored to the known
     entity's form ("Ana's") ONLY when its stem names a subject already
     in the notebook; a missing "?" is appended. An opener prefix is kept.
  3. If the formal turn is not a 281 called shape (e.g. "called Bo" still
     has a name after called), normalize returns None: 281 stands.
  4. The original turn runs first through the whole head (281's turn). If
     it already answers, or it wrote, its reply stands. Else the formal
     turn runs as if typed alone; its reply is used only if it answers
     with 0 writes (a written run is undone and the original stands).
     Teach turns and writes are untouched: plain teaches never start with
     a question word and never match a called shape, so they always take
     the identical path.
Net effect: the only moves vs 281 are casual called-wording + stored fact
-> the exact answer; everything else is byte-identical to 281.
"""

from __future__ import annotations

import re

import claude_fix260_openers as F260  # noqa: E402 (read-only helpers)
import claude_fix281_called as F281  # noqa: E402 (matcher + answer test)
import fable_loop90_agent as L90  # noqa: E402 (read-only triple reader)


_QWORD_START281B = re.compile(
    r"^\s*(who|what|whats|when|where|why|how|which|whose)\b", re.IGNORECASE)

_WHATS_LEAD281B = re.compile(r"^\s*what(?:'s|s)\b", re.IGNORECASE)

_CALLED_CUE281B = ("called", "named", "name of", "do you call")


def _has_cue281b(core: str) -> bool:
    c = " ".join(core.lower().split())
    return any(w in c for w in _CALLED_CUE281B)


# Tokens never treated as an apostrophe-less possessive (their stem could
# collide with a stored subject, e.g. "is" -> "i").
_STOP281B = frozenset({
    "is", "was", "has", "as", "us", "his", "its", "this", "thus",
    "does", "goes", "says", "gets", "puts",
})


def known_subjects281b(loop) -> dict:
    """lowercase subject -> canonical subject from the notebook now."""
    try:
        triples = L90.notebook_triples(loop.nb)
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for t in triples or []:
        try:
            s = str(t[0])
        except Exception:  # noqa: BLE001
            continue
        out.setdefault(" ".join(s.lower().split()), s)
    return out


def _fix_tok281b(tok: str, subjects: dict):
    if "'" in tok or "\u2019" in tok:
        return None
    if tok.lower() in _STOP281B:
        return None
    m = re.match(r"^([A-Za-z]+)s$", tok)
    if m is not None:
        stem = m.group(1)
        if len(stem) >= 2 and stem.lower() in subjects:
            # "anas" names known "Ana" -> the formal possessive.
            return subjects[stem.lower()] + "'s"
    if tok.lower() in subjects:
        canon = subjects[tok.lower()]
        if canon.endswith(("s", "S")):
            # "nils" names known "Nils" -> "Nils's", the formal teach form.
            return canon + "'s"
        return canon
    return None


# (head, subj_tok, rel_tok) shapes for the possessive fix, matched on the
# whats-normalised core with an optional trailing "?".
_SHAPES281B = (
    re.compile(r"^((?:who|what)\s+is)\s+(\S+?)\s+(\S+?)\s+"
               r"(called|named)\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^(what\s+do\s+you\s+call)\s+(\S+?)\s+(\S+?)\s*\??\s*$",
               re.IGNORECASE),
    re.compile(r"^(what\s+is\s+the\s+name\s+of)\s+(\S+?)\s+(\S+?)\s*"
               r"\??\s*$", re.IGNORECASE),
)


def _restore_apos281b(core: str, subjects: dict) -> str:
    for rx in _SHAPES281B:
        m = rx.match(core)
        if m is None:
            continue
        head, subj_tok, rel_tok = m.group(1), m.group(2), m.group(3)
        # Never touch a value/name after called: the trailing shape only
        # reaches here when nothing follows called/named.
        fix = _fix_tok281b(subj_tok, subjects)
        if fix is None:
            return core
        start, end = m.span(2)
        return core[:start] + fix + core[end:]
    return core


def normalize_casual281b(text: str, subjects: dict):
    """Return the formal called-wording for a casual called/named turn,
    else None (281's path then runs byte-identical)."""
    t = str(text)
    ta = F281._apos(t)
    if F281.rewrite_called281(ta) is not None:
        return None
    core = ta.strip()
    prefix = ""
    sp = F260.split_openers260(ta)
    if sp is not None:
        rest = sp[0]
        rstrip = ta.rstrip()
        core_stripped = rest.strip()
        if core_stripped and rstrip.endswith(core_stripped):
            prefix = rstrip[:len(rstrip) - len(core_stripped)]
            core = core_stripped
    if not core.endswith("?"):
        if _QWORD_START281B.match(core) is None:
            return None
    if not _has_cue281b(core):
        return None
    core2 = _WHATS_LEAD281B.sub("What is", core, count=1)
    core3 = _restore_apos281b(core2, subjects)
    if not core3.rstrip().endswith("?"):
        core3 = core3.rstrip() + "?"
    if F281.rewrite_called281(core3) is None:
        return None
    cand = prefix + core3
    if cand == t or F281._apos(cand) == ta:
        return None
    if F281.rewrite_called281(cand) is None:
        cand = core3  # opener blocks the match; run the bare formal turn
    return cand


def install_casual281b(loop):
    """Install the 281b layer on a built 281 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn281(turn260(...))
    loop.turn281b_inner = inner_turn
    loop.casual281b_log = []

    def turn281b(text: str) -> list[str]:
        t = str(text)
        subjects = known_subjects281b(loop)
        norm = normalize_casual281b(t, subjects)
        if norm is None or norm == t:
            return inner_turn(t)
        s0 = F260.snapshot260(loop)
        e0 = F260._nb_events(loop)
        r0 = list(inner_turn(t))
        if F260._nb_events(loop) != e0:
            return r0                 # a write: keep the original
        if F281.is_answer281(r0):
            return r0                 # already answered: keep it
        s1 = F260.snapshot260(loop)
        F260.restore260(s0)
        r1 = list(inner_turn(norm))
        wrote = F260._nb_events(loop) != e0
        if wrote or not F281.is_answer281(r1):
            F260.restore260(s1)
            return r0                 # rewrite failed: 281's route stands
        loop.casual281b_log.append({"turn": t, "formal": norm})
        return r1

    turn281b.__name__ = "turn281b"
    loop.turn = turn281b
    return loop
