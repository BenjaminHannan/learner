"""Exp 63 (doc 68): pure canonicaliser over open relation strings. Plain software.

canon(relation_string) -> (canonical_name | None, relation_id | None, inverse_flag)

Pipeline (all deterministic, exact-match only):
  1. norm via norm_relation (lowercase, strip, collapse whitespace).
  2. Inverse marker: a trailing "(inverse)" / "[inverse]" or a leading
     "inverse of " names the INVERSE of the base string. The base is looked
     up; if it resolves to R and the inverse table declares R -> R_inv, return
     (R_inv, pid(R_inv), True). Anything unresolvable -> UNKNOWN.
     (inverse_flag=True therefore always means "output is the declared
     inverse of the relation you named", which is what the reasoner needs
     when it traverses a stored hop backwards.)
  3. Denylist: a normalised string claimed as an alias by > 1 Wikidata
     property abstains -> (None, None, False). Ambiguity never guesses.
  4. Exception list (doc 58 section 7): fragile pairs such as
     "follows"/"followed by" and "has part"/"part of" are looked up EXACTLY
     as written; rule normalisation must never merge or strip them.
  5. Rule normalisation: strip leading auxiliaries (is/are/was/were/be/been)
     and leading articles (the/a/an), then re-check the table. One pass,
     fixed word lists, no stemming (stemming would merge distinct relations).
  6. Alias table: exact lookup of each candidate in turn.
  7. UNKNOWN -> (None, None, False). The reasoner abstains on UNKNOWN.

Tables are frozen JSON under data/open/wikidata-props/ (written once by
scripts/fable_relcanon63_build.py from CC0 Wikidata property data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
PROPS_DIR = ROOT / "data" / "open" / "webred" / "frames"
TABLE_DIR = ROOT / "data" / "open" / "wikidata-props"


def norm_relation(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def _load_json(name: str) -> dict:
    try:
        return json.loads((TABLE_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


ALIAS_TABLE: dict = _load_json("alias_table.json")
DENYLIST: set = set(_load_json("denylist.json") or [])
INVERSE_TABLE: dict = _load_json("inverse_table.json")

# The 521 canonical WebRED names (exact-match-first, today's behaviour).
CANONICAL: set = set()
try:
    _rel = json.loads((ROOT / "data" / "open" / "webred" / "frames"
                       / "relations.json").read_text(encoding="utf-8"))
    CANONICAL = set((_rel.get("counts") or {}).keys())
except (OSError, ValueError):
    CANONICAL = set()

NAME_TO_PID: dict = {}
for _split in ("train", "dev", "heldout"):
    try:
        with open(PROPS_DIR / f"{_split}.jsonl", encoding="utf-8") as _fh:
            for _line in _fh:
                try:
                    _r = json.loads(_line)
                except ValueError:
                    continue
                _n, _p = _r.get("relation"), _r.get("relation_id")
                if _n and _p and _n not in NAME_TO_PID:
                    NAME_TO_PID[_n] = _p
    except OSError:
        break

# Strings rules must never transform (doc 58 section 7 exception list).
# Each pair below would be merged or mangled by stripping/stemming.
EXCEPTIONS = frozenset({
    "follows",
    "followed by",
    "has part",
    "part of",
})

_LEAD_AUX = ("is", "are", "was", "were", "be", "been")
_LEAD_ART = ("the", "a", "an")


def _rule_variants(normed: str) -> list:
    """Deterministic normalisation candidates, most-specific first."""
    out = [normed]
    toks = normed.split()
    while toks and toks[0] in _LEAD_AUX:
        toks = toks[1:]
    while toks and toks[0] in _LEAD_ART:
        toks = toks[1:]
    stripped = " ".join(toks)
    if stripped and stripped != normed:
        out.append(stripped)
    return out


def _direct_lookup(normed: str) -> Optional[str]:
    """Exact alias-table hit, respecting the denylist. Returns canonical or None."""
    if normed in DENYLIST:
        return None
    return ALIAS_TABLE.get(normed)


def _resolve(normed: str) -> Optional[str]:
    """Canonical-first, then denylist-abstain, then alias table."""
    if normed in CANONICAL:
        return normed
    return _direct_lookup(normed)


def _pid_for(canonical: str) -> Optional[str]:
    return NAME_TO_PID.get(canonical)


def canon(relation_string: str) -> Tuple[Optional[str], Optional[str], bool]:
    """Map an open relation string to (canonical WebRED name, pid, inverse_flag).

    UNKNOWN -> (None, None, False).
    """
    normed = norm_relation(relation_string)
    if not normed:
        return (None, None, False)

    # Canonical names first: an exact match against the 521 always wins
    # (today's suggest_relation_id behaviour). The denylist only governs
    # non-canonical aliases, so it can never nuke a canonical name.
    if normed in CANONICAL:
        return (normed, _pid_for(normed), False)

    # Inverse marker: name the inverse of the base relation.
    base = None
    if normed.startswith("inverse of ") and len(normed) > len("inverse of "):
        base = normed[len("inverse of "):]
    elif normed.endswith(" (inverse)"):
        base = normed[: -len(" (inverse)")].strip()
    elif normed.endswith(" [inverse]"):
        base = normed[: -len(" [inverse]")].strip()
    if base is not None:
        if not base:
            return (None, None, False)
        hit = _resolve(base)
        if hit is None and base not in EXCEPTIONS:
            for variant in _rule_variants(base)[1:]:
                hit = _resolve(variant)
                if hit is not None:
                    break
        if hit is None:
            return (None, None, False)
        edge = INVERSE_TABLE.get(hit)
        if not edge:
            return (None, None, False)
        inv_name = edge["inverse_name"]
        return (inv_name, _pid_for(inv_name), True)

    # Exception list: exact lookup only, no rule transforms.
    if normed in EXCEPTIONS:
        hit = _resolve(normed)
        if hit is None:
            return (None, None, False)
        return (hit, _pid_for(hit), False)

    # Direct hit first (covers canonical names and listed aliases verbatim).
    hit = _resolve(normed)
    if hit is not None:
        return (hit, _pid_for(hit), False)

    # Rule normalisation, then re-check.
    for variant in _rule_variants(normed)[1:]:
        hit = _resolve(variant)
        if hit is not None:
            return (hit, _pid_for(hit), False)
    return (None, None, False)
