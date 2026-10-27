"""Exp 259 THE ONE CHANGE: the denied value ends at a clause boundary.

Bug (252 / 252b, dev252b b252-001/003/010/013/015): 252's explicit-denial
path (Correct252EarsMixin._deny_named252) takes everything after the verb
as the denied value, trailing clause included ("Brimwell, that's
outdated"). That never equals the stored value, so the path replied
"I don't have Brimwell, that's outdated as Arlo's employer, ..." while
Brimwell stays stored: a false reply.

This mixin sits on top of Correct252EarsMixin on the inner ears and
overrides only the explicit-denial step:

1. When the denied span does not exactly match a stored value of that
   (subject, relation) (252's own test: lower-case equality), check whether
   the span STARTS with a stored value followed directly by a clause
   boundary: ", " " - " " — " "; " " (" (or the end of the span). If it
   does, that stored value is removed through 252's own retraction action
   (negate252 -> 154f's _act_negate_one138j) with 252's own "removed" reply.
   Only a punctuation boundary counts: "Brimwell Hall" never matches
   "Brimwell". Several stored values: the longest match wins.
   252's own clause-end words (_TAIL_RX: "anymore", "any more", "now",
   ...) are dropped from the part before the boundary, as 252 drops them
   at the end of a clause ("Garrow anymore, that's old" -> "Garrow").
2. If no stored value matches, 252's honest "I don't have ..." reply names
   only the part of the span before the first clause boundary. Rule-3
   wording: when that part is a stored value plus more words ("Garrow
   Hall", "Garrow lately" with "Garrow" stored), the reply is "I have S's R
   as Garrow, not Garrow Hall, so I didn't change anything." instead (no
   write), so it never reads as "I don't have Garrow".
3. A reply may never say "I don't have V" when (subject, relation, V) is
   stored. Two places outside step 1 broke this in the pilot and are
   covered here (both only when a clause boundary is present):
   a. the tail lands in the RELATION ("Sill isn't Evard's manager (that
      was last year)." parses as relation "manager (that was last year)");
      the relation words are cut at the first boundary, 252's own
      _TAIL_RX words ("anymore", "now", ...) are dropped, and the sentence
      "S's R is V." is re-read by the base ears; then steps 1-2 apply.
      If it still cannot be read, 252's own "Which fact is wrong?" ask is
      used (no write, no "I don't have").
   b. "X's R is not V, <tail>." is owned by the base 154f path, which
      replied "I don't have V, <tail> as X's R." When (and only when) the
      154f value holds a clause boundary, steps 1-2 are applied to 154f's
      own parse (name, relation key, value) and 252's own remove action /
      "I don't have ..." reply are used instead. Turns without a boundary
      stay with 154f, byte-identical.
Nothing else changes: contextual denials/corrections, teaches, questions,
the user-name confirm flow and inferred facts go through 252b unchanged.
No existing file is edited.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix252_correct as F252  # noqa: E402 (read-only)
import fable_fix154f_negate as N154F  # noqa: E402 (read-only)
import fable_notebook_contract as C  # noqa: E402 (read-only)

BOUNDARIES259 = (", ", " - ", " — ", "; ", " (")


def first_boundary259(span: str) -> int:
    """Index of the first clause boundary in span, or -1."""
    hits = [i for i in (span.find(b) for b in BOUNDARIES259) if i >= 0]
    return min(hits) if hits else -1


def head259(span: str) -> str:
    """The part of span before its first clause boundary, with 252's own
    clause-end words (_TAIL_RX: "anymore", "now", "any more", ...) dropped,
    exactly as 252 drops them at the end of a clause."""
    i = first_boundary259(span)
    if i < 0:
        return span
    return F252._strip_end(F252._TAIL_RX.sub("", span[:i].strip()))


def word_prefix259(head: str, values: list[str]) -> str | None:
    """Stored v when head is v + " " + more words ("Garrow Hall" / "Garrow
    lately" vs stored "Garrow"): not a match (no punctuation boundary), but
    saying "I don't have Garrow ..." would read as a claim about Garrow."""
    low = head.lower()
    best = None
    for v in values:
        if low.startswith(v.lower() + " ") and (best is None
                                               or len(v) > len(best)):
            best = v
    return best


def match_stored259(span: str, values: list[str]) -> str | None:
    """Stored value v with span == v, span starting v + boundary, or the
    head of span (see head259) == v."""
    low = span.lower()
    hd = head259(span).lower()
    best = None
    for v in values:
        lv = v.lower()
        if low == lv or hd == lv or any(low.startswith(lv + b)
                                        for b in BOUNDARIES259):
            if best is None or len(v) > len(best):
                best = v
    return best


def unstored_reply259(subj: str, rel_s: str, span: str,
                      values: list[str]) -> str:
    """Step 2 reply; rule 3 wording when the head only word-extends a
    stored value."""
    hd = head259(span)
    wp = word_prefix259(hd, values)
    if wp is not None:
        return (f"I have {subj}'s {rel_s} as {wp}, not {hd}, so I didn't "
                "change anything.")
    return f"I don't have {hd} as {subj}'s {rel_s}, so I didn't change anything."


class Boundary259EarsMixin:
    """On top of Correct252EarsMixin (class swap on the inner ears)."""

    def _deny_named252(self, pos: str, raw: str):  # type: ignore[override]
        if first_boundary259(F252._strip_end(pos)) < 0:
            # no clause boundary in the sentence: 252 exactly as before
            return super()._deny_named252(pos, raw)  # type: ignore[misc]
        got = self._read252(pos)  # type: ignore[attr-defined]
        if got is None:
            return super()._deny_named252(pos, raw)  # type: ignore[misc]
        name, key, val = got
        if name.upper() == "USER" or F252._ME_RX.search(name):
            return super()._deny_named252(pos, raw)  # type: ignore[misc]
        rel_s = F252._rel_surface(key)
        rel_tail = first_boundary259(rel_s) >= 0
        if first_boundary259(val) < 0 and not rel_tail:
            # no clause boundary anywhere: 252 exactly as before
            return super()._deny_named252(pos, raw)  # type: ignore[misc]
        r = self._resolve252(name)  # type: ignore[attr-defined]
        if r is None:
            return super()._deny_named252(pos, raw)  # type: ignore[misc]
        eid, subj = r
        if rel_tail:
            # 3a: the tail landed in the relation words
            rcut = F252._strip_end(F252._TAIL_RX.sub("", head259(rel_s)))
            again = None
            if rcut:
                again = self._read252(f"{subj}'s {rcut} is {head259(val)}.")  # type: ignore[attr-defined]
            if again is None or again[0].lower() != subj.lower() \
                    or first_boundary259(F252._rel_surface(again[1])) >= 0:
                return self._ask252(  # type: ignore[attr-defined]
                    "Which fact is wrong? Please say it like \"Kim's boss "
                    "is not Lee.\"", "which")
            key, val = again[1], again[2]
            rel_s = F252._rel_surface(key)
        values = self._values252(eid, key)  # type: ignore[attr-defined]
        hit = match_stored259(val, values)
        if hit is not None:
            return self._remove252(eid, subj, key, hit, raw)  # type: ignore[attr-defined]
        return self._ask252(  # type: ignore[attr-defined]
            unstored_reply259(subj, rel_s, val, values), "unstored")

    def _hear252(self, turn: str):  # type: ignore[override]
        got = self._route154f259(turn)
        if got is not None:
            return got
        return super()._hear252(turn)  # type: ignore[misc]

    def _route154f259(self, turn: str):
        """3b: a 154f-owned denial whose value holds a clause boundary."""
        nb = getattr(self, "nb", None)
        if nb is None or self._pending252():  # type: ignore[attr-defined]
            return None
        text = F252._norm(turn)
        if not text or F252.is_question252(text):
            return None
        parsed = N154F.parse_negate154f(text)
        if parsed is None or nb.resolve(parsed["name"]).status != C.OK:
            return None
        if first_boundary259(F252._strip_end(parsed["value"])) < 0:
            return None  # no boundary: 154f keeps it, byte-identical
        rest, prefixes = F252.strip_prefixes252(text)
        if prefixes or F252._ME_RX.search(rest):
            return None
        r = self._resolve252(parsed["name"])  # type: ignore[attr-defined]
        if r is None:
            return None
        eid, subj = r
        key = parsed["relation"]
        val = F252._strip_end(parsed["value"])
        values = self._values252(eid, key)  # type: ignore[attr-defined]
        hit = match_stored259(val, values)
        if hit is not None:
            return self._remove252(eid, subj, key, hit, turn)  # type: ignore[attr-defined]
        return self._ask252(  # type: ignore[attr-defined]
            unstored_reply259(subj, F252._rel_surface(key), val, values),
            "unstored")

def install_boundary259(loop) -> None:
    """Class-swap the loop's inner ears (after install_correct252)."""
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        ears = getattr(loop, "ears", None)
        inner = getattr(ears, "inner", None) or ears
    if inner is None or not isinstance(inner, F252.Correct252EarsMixin):
        raise RuntimeError("fix259 needs the 252 ears mixin installed first")
    if not isinstance(inner, Boundary259EarsMixin):
        cls = inner.__class__
        inner.__class__ = type(f"Boundary259_{cls.__name__}",
                               (Boundary259EarsMixin, cls), {})
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("fix259" in n for n in notes):
        notes.append("fix259: Boundary259EarsMixin on top of the 252 ears "
                     "mixin (denied value ends at a clause boundary)")
