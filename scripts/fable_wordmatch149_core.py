#!/usr/bin/env python3
"""Experiment 149 -- whole-word entity matching core (the ONE change).

A taught entity counts as mentioned in a question only when it matches on
word boundaries: case-insensitive (as today), with a trailing possessive
"'s" (ascii or unicode) or bare trailing quote allowed, and any trailing
punctuation allowed (it is a non-word char, so the boundary holds).
Longer entity names still win over shorter ones when both match
(longest-match-first containment blocking, unchanged shape).

Nothing here edits an existing file: apply_wordmatch() rebinds module
attributes at import time in the importing process only (the same
process-wide override pattern loop134 uses for fable_agent_loop._APOS).
Callers: scripts/fable_loop149_agent.py (both variants).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Trailing possessive allowed after an entity: 's / ' / unicode variants.
_POSS = r"(?:['\u2019]s|['\u2019])?"


def _entity_pattern(entity: str) -> "re.Pattern[str] | None":
    text = " ".join(str(entity).split())
    if not text:
        return None
    return re.compile(r"(?<!\w)" + re.escape(text) + _POSS + r"(?!\w)",
                      re.IGNORECASE)


def entity_spans(question: str, entities: list[str]
                 ) -> list[tuple[int, int, str]]:
    """Whole-word occurrence spans, longest-match-first containment blocked."""
    q = str(question)
    spans: list[tuple[int, int, str]] = []
    for e in sorted(set(str(x) for x in entities), key=len, reverse=True):
        pat = _entity_pattern(e)
        if pat is None:
            continue
        for m in pat.finditer(q):
            spans.append((m.start(), m.end(), e))
    # longest first: a kept span blocks any span it contains
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    return kept


def word_mentions(question: str, entities: list[str]) -> list[str]:
    """Taught entity strings mentioned in the question (whole-word)."""
    seen: list[str] = []
    for _, _, e in entity_spans(question, entities):
        if e not in seen:
            seen.append(e)
    return seen


# -- patched replicas (same names/shape as the originals they replace) ------

def entity_mentions92(question: str, entities: list[str]) -> list[str]:
    """Drop-in for fable_bench92_english_arm._entity_mentions92."""
    return word_mentions(question, entities)


def entity_mentions73(question: str, entities: list[str]) -> list[str]:
    """Drop-in for fable_bench73_english_arm._entity_mentions."""
    return word_mentions(question, entities)


def span_of(ql: str, text: str) -> tuple[int, int] | None:
    """Drop-in for fable_qrewrite132._span_of (whole-word)."""
    pat = _entity_pattern(text)
    if pat is None:
        return None
    m = pat.search(str(ql))
    if m is None:
        return None
    return (m.start(), m.end())


def seed_subjects(question: str, triples) -> list[str]:
    """Drop-in for fable_qrewrite132._seed_subjects (whole-word)."""
    ql = str(question).lower()
    subs = sorted({str(s) for s, _, _ in triples}, key=len, reverse=True)
    spans: list[tuple[int, int, str]] = []
    for s in subs:
        pat = _entity_pattern(s)
        if pat is None:
            continue
        for m in pat.finditer(str(question)):
            spans.append((m.start(), m.end(), s))
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(s).lower())


def decomp_subjects(question: str, triples) -> list[str]:
    """Drop-in for fable_qrewrite132._decomp_subjects.

    Identical except the compound-target containment check
    (``tgt.lower() in ql``) becomes a whole-word span check.
    """
    import fable_qrewrite132 as Q132  # noqa: E402 (tables only, read-only)
    qtok = set(_tok(question))
    qn = {Q132._typonorm(t) for t in qtok}
    ql = str(question).lower()
    out: list[str] = []
    for (s, _r, _o) in triples:
        s = str(s)
        parts = Q132._split_of(s)
        if parts is None:
            continue
        pre, tgt = parts
        if span_of(ql, tgt) is None:
            continue
        pw = [t for t in _tok(pre) if t not in Q132._STOP]
        if not pw:
            continue
        if all(Q132._typonorm(w) in qn for w in pw):
            if s not in out:
                out.append(s)
    return out


_PATCHED = False


def apply_wordmatch() -> None:
    """Rebind the five substring entity-match sites (this process only)."""
    global _PATCHED
    import fable_bench73_english_arm as B73  # noqa: E402 (read-only target)
    import fable_bench92_english_arm as B92  # noqa: E402 (read-only target)
    import fable_qrewrite132 as Q132  # noqa: E402 (read-only target)
    B73._entity_mentions = entity_mentions73
    B92._entity_mentions92 = entity_mentions92
    Q132._seed_subjects = seed_subjects
    Q132._span_of = span_of
    Q132._decomp_subjects = decomp_subjects
    _PATCHED = True


def is_applied() -> bool:
    return _PATCHED


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag)
        if not cond:
            fails.append(tag)

    ents = ["Norland", "Aldport"]
    check(word_mentions("What is the capital of Norland?", ents)
          == ["Norland"], "plain-match")
    check(word_mentions("What is the capital of Norlandia?", ents)
          == [], "suffix-blocked")
    check(word_mentions("What is the capital of norland?", ents)
          == ["Norland"], "case-insensitive")
    check(word_mentions("What is Norland's capital?", ents)
          == ["Norland"], "possessive")
    check(word_mentions("What is the capital of Norland??", ents)
          == ["Norland"], "trailing-punct")
    check(word_mentions('What is the "capital" of Norland?', ents)
          == ["Norland"], "inner-quotes")
    check(word_mentions("What is the capital of Ann?", ["Ann", "Anna"])
          == ["Ann"], "shorter-asked")
    check(word_mentions("What is the capital of Anna?", ["Ann", "Anna"])
          == ["Anna"], "longer-wins")
    check(word_mentions("What is the capital of Anna?", ["Ann"])
          == [], "untaught-longer-abstains")
    check(word_mentions("What is the capital of Dara Fenner?",
                        ["Dara Fenn"]) == [], "phrase-suffix-blocked")
    check(word_mentions("What is the capital of Dara Fenn?",
                        ["Dara Fenn", "Dara Fenner"]) == ["Dara Fenn"],
          "phrase-exact")
    check(word_mentions("What is the capital of Notre-Dame?",
                        ["Notre-Dame"]) == ["Notre-Dame"], "hyphen")
    check(word_mentions("What is O'Neill's capital?", ["O'Neill"])
          == ["O'Neill"], "apostrophe-possessive")
    check(word_mentions("What is the capital of Lima?", ["Lima", "Limassol"])
          == ["Lima"], "lima")
    check(word_mentions("What is the capital of Limassol?",
                        ["Lima"]) == [], "limassol-blocked")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
    return 1 if fails else 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 149 whole-word core")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return cmd_selftest(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
