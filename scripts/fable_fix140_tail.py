#!/usr/bin/env python3
"""Experiment 140 -- THE ONE CHANGE: one value-tail cleaner for every teach path.

Red team 136 (W4 + W7 + W8) showed stored values keep junk tails because the
exp-129 sanitizer (scripts/fable_fix129_punct.py, read-only, never edited)
only strips sentence punctuation ``.!?;:``:

  W4  emoji/symbol runs: "Tom's city is Rome <emoji>" stores 'Rome <emoji>'.
  W7  unmatched trailing quote: 'Kip Dune is a citizen of Peru."' stores 'Peru."'.
  W8  FakeEars' ``value.rstrip(".")`` (scripts/fable_agent_loop.py:136) eats
      abbreviation dots ("Washington, D.C.." -> 'Washington, D.C') because it
      runs BEFORE the exp-129 abbreviation-aware sanitizer.

THE RULE (extends exp 129, strip-then-restore):
  1. Trim outer whitespace; drop outer wrapping quotes/brackets first (129).
  2. Greedily drop trailing runs of sentence punctuation ``. ! ? ; :`` (129),
     trailing non-alphanumeric symbol/emoji runs (Unicode categories
     So/Sk/Sm/Sc/Cf, plus variation selectors U+FE00-FE0F/U+E0100-E01EF and
     the zero-width joiner U+200D), and unmatched trailing quote characters
     (``" ' ' ' " " << >>`` with no matching opener), in any order.
  3. Abbreviation restore identical to exp 129: if at least one '.' was
     dropped AND the stem's last token is abbreviation-shaped (internal '.',
     single uppercase initial, or known honorific/street/corporate word),
     put ONE '.' back. Internal symbols (``Either/Or``, ``A/UX``) are never
     touched: stripping only ever removes trailing characters.

Applied (subclass/wrap only, no existing file edited) at THREE levels so
every teach path is covered before the write:
  * ears hear(): sanitize the name/value of outgoing teach/correct actions;
  * loop _act(): sanitize again just before the notebook write;
  * FakeEars possessive path: TailFakeEars overrides hear() with the SAME
    cleaner instead of ``rstrip(".")`` (fixes W8 at the source; the old
    rstrip destroyed the abbreviation dot before any sanitizer could see it).

Subject spans get the same cleaner. Relation keys are never touched.
Forget/ask/clarify actions are never touched. Empty-after-strip spans are
left as-is (downstream guards still fire).
"""

from __future__ import annotations

import copy
import unicodedata

import fable_agent_loop as A  # noqa: E402 (base FakeEars, read-only)
import fable_fix129_punct as P129  # noqa: E402 (wrapped base, read-only)

# ---------------------------------------------------------------- cleaner

_TAIL_SYMBOL_CATS = frozenset({"So", "Sk", "Sm", "Sc", "Cf"})
_ZWJ = "\u200d"


def _is_tail_symbol(ch: str) -> bool:
    """True for trailing junk symbols/emoji; never for alphanumerics or '.'."""
    if ch == _ZWJ:
        return True
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF:
        return True  # variation selectors (e.g. the U+FE0F in heart emoji)
    return unicodedata.category(ch) in _TAIL_SYMBOL_CATS


def _strip_trailing_symbols(s: str) -> str:
    while s and _is_tail_symbol(s[-1]):
        s = s[:-1]
    return s.rstrip()


_QUOTE_PAIR = {
    '"': '"', "'": "'",
    "\u201d": "\u201c", "\u201c": "\u201d",
    "\u2019": "\u2018", "\u2018": "\u2019",
    "\u00bb": "\u00ab", "\u00ab": "\u00bb",
}
_QUOTES = frozenset(_QUOTE_PAIR)


def _strip_unmatched_trailing_quote(s: str) -> str:
    """Drop ONE trailing quote char with no matching opener in the span."""
    if s and s[-1] in _QUOTES:
        q = s[-1]
        opener = _QUOTE_PAIR[q]
        if opener == q:
            if s.count(q) % 2 == 1:
                return s[:-1].rstrip()
        elif s.count(q) > s.count(opener):
            return s[:-1].rstrip()
    return s


def clean_span(span: str) -> str:
    """Strip trailing sentence punct + symbol/emoji tails + unmatched quotes.

    Abbreviation-aware exactly like exp 129 (one '.' restored after an
    abbreviation-shaped token). Balance-aware: matched brackets/quotes are
    content; only unmatched closers/quotes and wrapping quotes are dropped.
    Internal symbols (``Either/Or``) pass through byte-identical.
    """
    s = " ".join(str(span).split())
    if not s:
        return s
    s = P129._strip_wrapping_quotes(s)
    s = P129._strip_unmatched_closer(s)
    s = _strip_unmatched_trailing_quote(s)
    s = _strip_trailing_symbols(s)
    dropped_dot = False
    while s and (s[-1] in P129._SENTENCE_PUNCT or s[-1].isspace()
                 or _is_tail_symbol(s[-1])):
        if s[-1] == ".":
            dropped_dot = True
        if _is_tail_symbol(s[-1]) and s[-1] not in P129._SENTENCE_PUNCT:
            s = _strip_trailing_symbols(s)
        else:
            s = s[:-1].rstrip()
        s = P129._strip_unmatched_closer(s)
        s = _strip_unmatched_trailing_quote(s)
        s = _strip_trailing_symbols(s)
    if not s:
        return " ".join(str(span).split())
    s = P129._strip_wrapping_quotes(s)
    if dropped_dot and P129._is_abbrev_token(P129._last_token(s)):
        s = s + "."
    return s


def sanitize_triple(triple: tuple[str, str, str]) -> tuple[str, str, str]:
    """Strip subject and value spans; relation key byte-identical."""
    subj, rel, obj = triple
    return (clean_span(subj), rel, clean_span(obj))


def sanitize_action(action: dict) -> dict:
    """Copy of a teach/correct action with name/value cleaned; else as-is."""
    if not isinstance(action, dict):
        return action
    if action.get("act") not in ("teach", "correct"):
        return action
    out = copy.copy(action)
    if "name" in out:
        cleaned = clean_span(out.get("name", ""))
        if cleaned:
            out["name"] = cleaned
    if "value" in out:
        cleaned = clean_span(out.get("value", ""))
        if cleaned:
            out["value"] = cleaned
    return out


def sanitize_actions(actions: list[dict]) -> list[dict]:
    return [sanitize_action(a) for a in list(actions)]


# ---------------------------------------------------------------- mixin


class ValueTailMixin:
    """One value-tail cleaner for every teach path (stackable, exp 138).

    Exposes the cleaner as methods so tonight's integration can stack this
    mixin onto another loop class without importing module-level functions.
    """

    @staticmethod
    def clean_span(span: str) -> str:
        return clean_span(span)

    @classmethod
    def sanitize_action(cls, action: dict) -> dict:
        return sanitize_action(action)

    @classmethod
    def sanitize_actions(cls, actions: list[dict]) -> list[dict]:
        return sanitize_actions(actions)


class TailFakeEars(ValueTailMixin, A.FakeEars):
    """FakeEars with the possessive-path rstrip(".") replaced by clean_span.

    Byte-identical to fable_agent_loop.FakeEars.hear except line 136: the raw
    ``value`` span goes through the exp-140 cleaner instead of
    ``value.rstrip(".")``, so abbreviation dots survive (W8) and emoji/symbol
    tails and unmatched quotes never reach the write (W4/W7). Question,
    pick, yes/no, correction and clarify paths are untouched.

    Guard-signal preservation (added after T2 run-1 showed 2 regressions):
    when the old rstrip result is empty or still carries a guard signal the
    downstream exp-91/121 screens decide on (``?``, ``;``, >6 words), the
    old span is kept verbatim so guards fire exactly as on the base loop.
    The cleaner then only ever touches spans the guards would let pass.
    """

    def hear(self, turn: str) -> list[dict]:
        turn = " ".join(str(turn).split())
        if not turn:
            return [A._clarify("I didn't catch anything.")]
        found = A._PICK.match(turn)
        if found:
            return [{"act": "answer", "value": "pick", "id": found.group(1)}]
        found = A._YESNO.match(turn)
        if found:
            return [{"act": "answer", "value": found.group(1).lower()}]
        found = A._QUESTION.match(turn)
        if found:
            parts = A._chain(found.group(1))
            if len(parts) < 2 or len(parts) > A.MAX_HOPS + 1:
                return [A._clarify(f"I can only follow 1 to {A.MAX_HOPS} steps, like "
                                   f"\"Who is Mira's mother's city?\".")]
            return [{"act": "ask", "name": parts[0],
                     "relations": [self._relation(p) for p in parts[1:]]}]
        correction = False
        found = A._CORRECTION.match(turn)
        if found and found.group(1):
            correction, turn = True, found.group(1)
        found = A._STATEMENT.match(turn)
        if found:
            raw_value = found.group(2)
            old_value = raw_value.rstrip(".")
            if (not old_value or "?" in old_value or ";" in old_value
                    or len(old_value.split()) > 6):
                value = old_value  # guard path identical to base FakeEars
            else:
                value = self.clean_span(raw_value)
                if not value:
                    value = old_value
            left = found.group(1)
            parts = A._chain(left)
            if len(parts) != 2:
                return [A._clarify("Please say it like \"Mira's city is Lisbon.\".")]
            name, relation = parts[0], self._relation(parts[1])
            if " " in name:
                return [A._clarify("I can only handle one-word names so far.")]
            if not value:
                return [A._clarify("I didn't get the value.")]
            return [{"act": "correct" if correction else "teach", "name": name,
                     "relation": relation, "value": value,
                     "is_person": relation in A.PERSON_RELATIONS}]
        return [A._clarify("I didn't understand that. Could you say it another way?")]
