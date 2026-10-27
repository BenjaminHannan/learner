#!/usr/bin/env python3
"""Experiment 193 -- THE ONE CHANGE: missing-apostrophe possessives on known names.

Director probe 09:56 on loop138h: after "Kofi's city is Lagos.", the asks
"What is kofis city?" and "What is Kofis city?" reply "I have no opinions."
(the small-talk/opinion route grabs the turn, because nothing splits the
owner from the relation without the apostrophe). Exp 165 covers
"who is toms boss" but only for person-relations, and its own agent also
fails "kofis city" ("city" is not a person relation).

THE ONE CHANGE (behaviour): Apos193Mixin, stacked OUTERMOST over the whole
loop138h ears stack (before every small-talk/opinion route). A word token
that equals, ignoring case, a name ALREADY IN THE NOTEBOOK plus a trailing
"s" ("kofis", "Kofis", "toms", "Juans"; also "s'" forms such as "Kofis'"),
immediately followed by a relation word the base can already parse, is read
as that name's possessive ("Kofi's city"), silently (Ben's ruling: typos
are fixed silently), and the rewritten turn is parsed by the unchanged
base. Gates (all must hold per token):

  (a) the candidate token itself carries no apostrophe except one
      trailing "s'" form (turns whose every token already parses -- e.g.
      "Kofi's city" -- yield no candidate and are untouched: the base
      owns them byte-identical);
  (b) the stem (token minus trailing "s" / "s'") matches the DISPLAY name
      of exactly one known notebook entity case-insensitively, and that
      display name is a single word (alias-only matches never fire);
  (c) the token itself is not a known entity and not the final word of a
      known multi-word entity (plural real words such as "cats", "bus",
      or "Wills" when Will is not in the notebook stay untouched);
  (d) the next word token (whitespace-adjacent) is a known relation:
      a person relation (the base's PERSON_RELATIONS), "city" (sealed 138h
      rows show the base saves and answers it, e.g. G3h-5a/b), a relation
      key already taught into the notebook, or the possessive-stripped
      form of one of those ("boss's" counts as "boss", so 2-hop
      "Kofis boss's city" and of-chain "city of Kofis boss" work).

Everything else -- unknown stems, real plurals, known stems followed by a
non-relation, opinion questions ("What is your favourite city?"), every
turn that already parses -- falls through to super().hear() untouched, so
the base owns those turns byte-identical.

No existing file is edited. Base modules are imported read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (PERSON_RELATIONS, read-only)

# Static relation inventory: the base's person relations plus "city".
# "city" is included on sealed evidence: loop138h saves "Kwame's city is
# Accra." and answers "Kwame's city is Accra." (138h PASSMARKS G3h-5a/b),
# and the director probe teaches "Kofi's city is Lagos.". Every other
# non-person relation must already be taught into the notebook (dynamic
# set below); anything else never matches, so those turns take the base
# path byte-identical.
REL193_STATIC: frozenset = frozenset(A.PERSON_RELATIONS) | frozenset({"city"})

_REL_STOP193 = frozenset({"of", "the", "a", "an"})

_WORD193_RE = re.compile(r"[A-Za-z]+'?")


def _norm193(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _notebook_relations193(nb) -> set[str]:
    """Lowercase relation words already taught into the notebook.

    Single-word keys match directly; multi-word keys (stored with "_" or
    spaces, e.g. "place_of_birth") contribute their non-stopword
    components, so a taught relation is recognised in surface position.
    Read-only over the notebook.
    """
    rels: set[str] = set()
    try:
        import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
        triples = L90.notebook_triples(nb)
    except Exception:
        return rels
    for _subj, rel, _val in triples:
        for tok in str(rel).lower().replace("_", " ").split():
            tok = tok.strip()
            if tok and tok not in _REL_STOP193:
                rels.add(tok)
    return rels


def _canonical193(nb, stem: str) -> str | None:
    """Notebook display name for stem, or None.

    The stem must resolve to exactly one entity AND equal that entity's
    display name case-insensitively (alias-only matches never fire), and
    the display name must be a single word.
    """
    try:
        found = nb.resolve(stem)
    except Exception:
        return None
    if found is None or getattr(found, "status", None) != "OK":
        return None
    ent_id = (getattr(found, "detail", None) or {}).get("entity_id")
    if not ent_id:
        return None
    try:
        canon = (getattr(nb, "entities", {}) or {}).get(ent_id)
    except Exception:
        return None
    if not canon or len(str(canon).split()) != 1:
        return None
    if _norm193(canon) != _norm193(stem):
        return None
    return str(canon)


def _stem_blocked193(nb, w: str, stem: str) -> bool:
    """True iff the full token W is itself notebook-known (plural/name)."""
    wn = _norm193(w.rstrip("'"))
    try:
        aliases = getattr(nb, "aliases", {}) or {}
    except Exception:
        aliases = {}
    if wn in aliases:
        return True
    try:
        displays = list((getattr(nb, "entities", {}) or {}).values())
    except Exception:
        displays = []
    for display in displays:
        toks = _norm193(display).split()
        if len(toks) > 1 and toks[-1] == wn:
            return True
    return False


def _strip_poss193(word: str) -> str:
    low = word.lower()
    # Lone trailing apostrophe first: "boss'" -> "boss" (checking "s'"
    # first would mis-strip to "bos").
    for suf in ("'s", "\u2019s", "'", "s'", "s\u2019"):
        if low.endswith(suf) and len(word) > len(suf):
            return word[:-len(suf)]
    return word


def rewrite_apos193(turn: str, nb) -> str | None:
    """Missing-apostrophe possessives -> canonical "Name's" forms, or None.

    Returns the rewritten turn when at least one token qualifies, else
    None (the caller must delegate the original turn untouched).
    """
    text = str(turn)
    if not text.strip():
        return None
    if nb is None:
        return None
    toks = [(m.group(0), m.start(), m.end())
            for m in _WORD193_RE.finditer(text)]
    if not toks:
        return None
    rels = set(REL193_STATIC) | _notebook_relations193(nb)
    edits: list[tuple[int, int, str]] = []
    for i, (w, _s, _e) in enumerate(toks):
        stem: str | None = None
        trailing_sprime = False
        if re.fullmatch(r"[A-Za-z]+[sS]", w) and len(w) >= 3:
            stem = w[:-1]
        elif re.fullmatch(r"[A-Za-z]+[sS]'", w) and len(w) >= 4:
            stem = w[:-2]
            trailing_sprime = True
        if stem is None or len(stem) < 2 or not stem.isalpha():
            continue
        if trailing_sprime and i > 0 and toks[i - 1][0].lower() == "the":
            continue  # 162b owns "The Xs' ..." plural teaches, untouched
        canon = _canonical193(nb, stem)
        if canon is None:
            continue
        if _stem_blocked193(nb, w, stem):
            continue
        if i + 1 >= len(toks):
            continue
        nxt, ns, _ne = toks[i + 1]
        gap = text[toks[i][2]:ns]
        if not re.fullmatch(r"\s+", gap):
            continue  # not immediately followed: untouched
        nxt_stem = _strip_poss193(nxt)
        if not nxt_stem or nxt_stem.lower() not in rels:
            continue
        edits.append((toks[i][1], toks[i][2], "%s's" % canon))
    if not edits:
        return None
    out: list[str] = []
    pos = 0
    for s, e, rep in edits:
        out.append(text[pos:s])
        out.append(rep)
        pos = e
    out.append(text[pos:])
    return "".join(out)


class Apos193Mixin:
    """Stackable mixin: missing-apostrophe possessives before the base hear.

    Cooperative: only turns with at least one qualifying token are
    rewritten (silently -- the reply shows the reading, exactly like the
    apostrophe twin's) and delegated to super().hear(); every other turn
    falls through untouched, so the base owns those turns byte-identical.
    """

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        nb = getattr(self, "nb", None)
        if nb is not None:
            fixed = rewrite_apos193(turn, nb)
            if fixed is not None:
                return super().hear(fixed)  # type: ignore[misc]
        return super().hear(turn)  # type: ignore[misc]
