"""Exp 252c merge glue: 252b + 258 (clause strip) + 259 (value boundary).

Layer order on the loop's inner ears (outermost first):
  Comment258EarsMixin   (258: trailing "that's ..." clause removed on
                         252b denial/correction turns; turn level)
  Merge252cEarsMixin    (this file: the ONE piece of glue, see below)
  Boundary259EarsMixin  (259: the denied value ends at a clause boundary,
                         inside 252's explicit-denial path + 154f route 3b)
  Correct252EarsMixin   (252 / 252b)
  base ears

Both pieces are imported read-only and installed unchanged.

The glue (why it is needed): 258 removes the clause, so the shortened turn
that reaches 259 no longer holds a boundary. For 252's own denial path this
is harmless (252 drops its clause-end words "anymore", "now", ... at the end
of the clause). But the base 154f path ("X's R is not V anymore, that's
outdated." -> after 258 "X's R is not V anymore.") keeps "V anymore" as the
value and replies "I don't have V anymore as X's R." while V is stored (the
false reply on corrpanel252 c252-022 in 258's run). 259 alone fixed that
because the boundary was still there (its 3b route drops 252's clause-end
words before the boundary).

Merge252cEarsMixin therefore treats 258's cut point as the clause boundary
for 259's 3b route, and only there:
- only on a turn that 258 actually shortened (this very turn is 258's
  short form), not a question, no pending question;
- only when 154f owns the turn ("X's R is not V ...", X resolvable), no
  252 prefix and not about the user (the same pre-checks as 259's 3b);
- only when dropping 252's clause-end words (_TAIL_RX) from V changes V
  and the result equals a stored value of (X, R) (case-insensitive), while
  V itself matches none: that stored value is removed through 252's own
  remove action and "OK, I removed ..." reply (as 259's 3b does).
- 259's rule-3 wording for a head that is a stored value plus more words
  ("Garrow Hall" with "Garrow" stored): "I have S's R as Garrow, not
  Garrow Hall, so I didn't change anything." (no write). 259 gives it only
  when a boundary is present; after 258's cut the boundary is gone and
  252 / 154f would say "I don't have Garrow Hall as ...", which reads as a
  claim about the stored Garrow. On a turn 258 shortened, the glue gives
  259's wording instead, on both routes (252's explicit denial and 154f).
Anything else goes to 259 / 252b / 154f unchanged. Nothing is written from
the removed clause. No existing file is edited.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix252_correct as F252  # noqa: E402 (read-only)
import claude_fix258_comment as F258  # noqa: E402 (read-only)
import claude_fix259_boundary as F259  # noqa: E402 (read-only)
import fable_fix154f_negate as N154F  # noqa: E402 (read-only)
import fable_notebook_contract as C  # noqa: E402 (read-only)


def cut_head252c(val: str) -> str:
    """V with 252's clause-end words dropped (as 259's head259 does before
    a boundary); the 258 cut point is the boundary."""
    return F252._strip_end(F252._TAIL_RX.sub("", F252._strip_end(val)))


class Merge252cEarsMixin:
    """Between Comment258EarsMixin (outside) and Boundary259EarsMixin."""

    def _was_cut252c(self, turn: str) -> bool:
        c = getattr(self, "_comment258", None)
        return bool(c) and c[1] is not None and c[1] == turn

    def _route154f259(self, turn: str):  # type: ignore[override]
        got = super()._route154f259(turn)  # type: ignore[misc]
        if got is not None:
            return got
        try:
            if not self._was_cut252c(turn):
                return None
            return self._cut154f252c(turn)
        except Exception:  # noqa: BLE001 -- never break the 259 path
            return None

    def _deny_named252(self, pos: str, raw: str):  # type: ignore[override]
        try:
            got = self._near252c(pos, raw)
        except Exception:  # noqa: BLE001 -- never break the 259 path
            got = None
        if got is not None:
            return got
        return super()._deny_named252(pos, raw)  # type: ignore[misc]

    def _near252c(self, pos: str, raw: str):
        """252 route on a 258-cut turn without a boundary: only the
        near-miss wording (stored value + more words) is changed."""
        if not self._was_cut252c(raw):
            return None
        if F259.first_boundary259(F252._strip_end(pos)) >= 0:
            return None  # 259 owns it
        got = self._read252(pos)  # type: ignore[attr-defined]
        if got is None:
            return None
        name, key, val = got
        if name.upper() == "USER" or F252._ME_RX.search(name):
            return None
        r = self._resolve252(name)  # type: ignore[attr-defined]
        if r is None:
            return None
        eid, subj = r
        values = self._values252(eid, key)  # type: ignore[attr-defined]
        if any(v.lower() == val.lower() for v in values):
            return None  # 252 removes it
        if F259.word_prefix259(val, values) is None:
            return None
        return self._ask252(  # type: ignore[attr-defined]
            F259.unstored_reply259(subj, F252._rel_surface(key), val, values),
            "unstored")

    def _cut154f252c(self, turn: str):
        nb = getattr(self, "nb", None)
        if nb is None or self._pending252():  # type: ignore[attr-defined]
            return None
        text = F252._norm(turn)
        if not text or F252.is_question252(text):
            return None
        parsed = N154F.parse_negate154f(text)
        if parsed is None or nb.resolve(parsed["name"]).status != C.OK:
            return None
        rest, prefixes = F252.strip_prefixes252(text)
        if prefixes or F252._ME_RX.search(rest):
            return None
        val = F252._strip_end(parsed["value"])
        if F259.first_boundary259(val) >= 0:
            return None  # 259's own 3b case (handled above)
        hd = cut_head252c(val)
        if not hd:
            return None
        r = self._resolve252(parsed["name"])  # type: ignore[attr-defined]
        if r is None:
            return None
        eid, subj = r
        key = parsed["relation"]
        values = self._values252(eid, key)  # type: ignore[attr-defined]
        if any(v.lower() == val.lower() for v in values):
            return None  # V itself is stored: 154f removes it
        if hd.lower() != val.lower():
            for v in values:
                if v.lower() == hd.lower():
                    return self._remove252(eid, subj, key, v, turn)  # type: ignore[attr-defined]
        if F259.word_prefix259(hd, values) is not None:
            return self._ask252(  # type: ignore[attr-defined]
                F259.unstored_reply259(subj, F252._rel_surface(key), hd,
                                       values), "unstored")
        return None


def install_merge252c(loop) -> None:
    """259 first, then this glue, then 258 outermost (class swaps)."""
    F259.install_boundary259(loop)
    inner = getattr(loop, "_inner138j_ears", None)
    if inner is None:
        ears = getattr(loop, "ears", None)
        inner = getattr(ears, "inner", None) or ears
    if inner is None or not isinstance(inner, F259.Boundary259EarsMixin):
        raise RuntimeError("install_merge252c needs 259's mixin first")
    if isinstance(inner, F258.Comment258EarsMixin) and not isinstance(
            inner, Merge252cEarsMixin):
        raise RuntimeError("258 installed before the 252c glue")
    if not isinstance(inner, Merge252cEarsMixin):
        cls = inner.__class__
        inner.__class__ = type(f"Merge252c_{cls.__name__}",
                               (Merge252cEarsMixin, cls), {})
    F258.install_comment258(loop)
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("fix252c" in n for n in notes):
        notes.append("fix252c: Comment258 > Merge252c > Boundary259 > "
                     "Correct252 on inner ears (258's cut = 259 boundary "
                     "on the 154f route)")
