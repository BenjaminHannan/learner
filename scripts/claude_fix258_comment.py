"""Exp 258 THE ONE CHANGE: commentary clauses after a denial or correction.

Bug (252b dev b252-035 and 37 of 38 tail items in dev252b): after a denial
or correction the user often adds a clause that talks ABOUT the old fact:
"That's wrong, that's old news.", "No, it's Quarry, that's outdated.",
"X doesn't work at Y (that was last year).". 252/252b parse that clause as
part of the fact: "that's old news" becomes a new value (junk write), or
"Y, that's outdated" is looked up as the value and not found (the denial is
not carried out, and the reply says "I don't have Y, that's outdated ...").

The change (outermost on the loop's inner ears, outside 252's mixin):
- Only on turns that are not questions (252's own is_question252), with no
  pending question (252's own _pending252), and only when the whole turn is
  a denial or a correction by 252/252b's own signals (see is_deny_or_correct258: 154f's parse_negate154f, 252's prefix
  lists, positive_of252, the ", not W" tail, the "not W, Z" shape and the
  pronoun + now/instead shape). No new detection grammar.
- A trailing commentary clause is: a clause boundary (", ", " - ", " -- ",
  " – ", " — ", "; " or an opening bracket), then that's / that is /
  that was / that isn't / that's not / which is / which was / this is
  (also "thats", "that isnt"), running to the end of the turn, or to the
  closing bracket (only end punctuation may follow the bracket).
- The clause is removed and the shortened turn is handed to 252b
  (super().hear) exactly as if the user had typed it. Nothing is taken from
  the clause. Every write or removal still goes through 252b's own paths.
- Candidates are tried leftmost first; the first one whose shortened turn
  is still a denial or correction wins ("No, that's wrong, that was last
  year." -> "No, that's wrong.").
- If no shortened turn is a denial or correction by itself: when 252 reads
  the whole turn as a plain contextual denial whose denial phrase IS the
  clause ("Nope, that's outdated."), the turn is left to 252b unchanged.
  Otherwise 252 would take the new value from the clause ("No, that's old
  news." -> employer "old news"), so the leftmost shortened turn ("No.") is
  handed on instead: no value is ever taken from the clause. Known cost:
  "No, that's Quarry." no longer replaces the value (it gets 252b's reply
  to "No.", and nothing is written).
- Every other turn goes to 252b unchanged (byte-identical behaviour).

No existing file is edited. Installed per instance (class swap), like 252.
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

STAGE258 = "comment258"

_OPENER258 = (r"(?:that'?s\s+not|that'?s|that\s+is|that\s+was|that\s+isn'?t|"
              r"which\s+is|which\s+was|this\s+is)")
# boundary + opener; group "br" is set when the boundary is a bracket
_CLAUSE258 = re.compile(
    r"(?:(?P<br>\s*\()|,\s*|\s+(?:-{1,2}|–|—)\s+|\s*[—–]\s*|\s*;\s*)"
    + _OPENER258 + r"\b", re.IGNORECASE)
_BRACKET_END258 = re.compile(r"^[^()]*\)?\s*[.!]*\s*$")
_END_PUNCT258 = re.compile(r"([.!]+)\s*$")


def is_deny_or_correct258(text: str, ctx_one) -> bool:
    """252/252b's own denial/correction signals on a statement turn.

    ctx_one: callable -> True when the previous reply stated exactly one
    stored fact (252's stated_facts252 == "one"); used only for 252's own
    pronoun + now/instead correction shape.
    """
    t = F252._norm(text)
    if not t or F252.is_question252(t):
        return False
    if N154F.parse_negate154f(t) is not None:
        return True  # base 154f "X's R is not Y."
    rest, prefixes = F252.strip_prefixes252(t)
    rest = rest.strip()
    low = rest.lower()
    if not rest or low in ("at all", "anymore", "any more"):
        return F252.has_deny252(prefixes)  # 252 rule 2
    if F252.positive_of252(rest) is not None:
        return True  # 252 rule 1 (single negated clause)
    parts = re.split(r"\s*(?:,\s*but\s+|;\s*|,\s*|\.\s+|\s+but\s+)\s*",
                     rest, maxsplit=1)
    if len(parts) == 2 and F252.positive_of252(parts[0]) is not None:
        return True  # 252 rule 4 (denial + positive clause)
    if prefixes and F252.has_corr_signal252(prefixes):
        return True  # 252 correction words
    if F252._NOT_TAIL_RX.match(rest):
        return True  # ", not W"
    if re.match(r"^not\s+[^,]+?\s*(?:,\s*(?:but\s+)?|\s+but\s+)", rest,
                re.IGNORECASE):
        return True  # "not W, Z"
    first = low.split()[0]
    if (first in F252._PRON or first in F252._POSS_PRON) \
            and re.search(r"\b(?:now|instead)\b", low):
        try:
            return bool(ctx_one())
        except Exception:  # noqa: BLE001
            return False
    return False


def comment_candidates258(text: str) -> list[str]:
    """Shortened turns, leftmost clause first (the clause never kept)."""
    t = F252._norm(text)
    m_end = _END_PUNCT258.search(t)
    end = m_end.group(1)[:1] if m_end else ""
    out = []
    for m in _CLAUSE258.finditer(t):
        head = t[:m.start()]
        if not head.strip():
            continue
        if m.group("br") is not None:
            if not _BRACKET_END258.match(t[m.end():]):
                continue  # bracket clause must be the tail
        head = re.sub(r"[\s,;:\-–—(]+$", "", head)
        if not head:
            continue
        out.append(head + end)
    return out


class Comment258EarsMixin:
    """Outermost on the inner ears (outside Correct252EarsMixin)."""

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        short = None
        try:
            short = self._short258(turn)
        except Exception:  # noqa: BLE001 -- never break the 252b path
            short = None
        self._comment258 = (turn, short) if short is not None else None
        if short is not None:
            return super().hear(short)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]

    def _ctx_one258(self) -> bool:
        kind, _facts = self._ctx252()  # type: ignore[attr-defined]
        return kind == "one"

    def _short258(self, turn: str) -> str | None:
        if getattr(self, "nb", None) is None:
            return None
        text = F252._norm(turn)
        if not text or F252.is_question252(text):
            return None
        if not _CLAUSE258.search(text):
            return None
        if self._pending252():  # type: ignore[attr-defined]
            return None
        if not is_deny_or_correct258(text, self._ctx_one258):
            return None
        cands = comment_candidates258(text)
        for short in cands:
            if is_deny_or_correct258(short, self._ctx_one258):
                return short
        if not cands:
            return None
        # No shortened turn is a denial/correction by itself. If 252 reads
        # the whole turn as a plain contextual denial ("Nope, that's
        # outdated." -- the clause IS 252's own denial phrase), keep it.
        rest, prefixes = F252.strip_prefixes252(text)
        rest = rest.strip()
        if not rest or rest.lower() in ("at all", "anymore", "any more"):
            return None
        # Otherwise 252 would take the value from the clause itself ("No,
        # that's old news." -> employer = "old news"): never take a value
        # from a commentary clause; hand the shortened turn ("No.").
        return cands[0]


def install_comment258(loop) -> None:
    """Class-swap the loop's inner ears (after install_correct252)."""
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        ears = getattr(loop, "ears", None)
        inner = getattr(ears, "inner", None) or ears
    if inner is None or not isinstance(inner, F252.Correct252EarsMixin):
        raise RuntimeError("install_comment258 needs 252's ears mixin first")
    if not isinstance(inner, Comment258EarsMixin):
        cls = inner.__class__
        inner.__class__ = type(f"Comment258_{cls.__name__}",
                               (Comment258EarsMixin, cls), {})
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("fix258" in n for n in notes):
        notes.append("fix258: Comment258EarsMixin outermost on inner ears "
                     "(trailing commentary clause removed on 252 denial/"
                     "correction turns)")
