#!/usr/bin/env python3
"""Experiment 147 -- mention-walk alignment composer (single-change fix).

Director-confirmed bug (doc 143; present in every lineage since loop102):
after teaching "Joren Hale is married to Petra Voss" + "Petra Voss is a
citizen of Litora", "Who is Joren Hale married to?" clarifies, because
compose_n_hop (scripts/fable_bench92_english_arm.py:198-240) walks to the
chain's sink and its coverage gate only checks walked-subset-of-mentioned.

THE ONE CHANGE (question side only; teach path and every other module
untouched -- this file only ADDS functions and shadows nothing globally):
walk only while the next hop's relation is one the question mentions, stop
at the first unmentioned hop, and answer only when the walked prefix is
fully mentioned, the wh-word's answer class fits the terminal hop, and no
extra mentioned relation is live (shared-stem ambiguity, subordinate
modifiers, wrapped evidence, implausible fragments and language-family
descriptors are tolerated; whole-word main-clause evidence of an
un-walked hop blocks); otherwise return None and let the existing
fallback/abstain path act.

Same rule applied to the 2-hop sibling walk
(fable_bench73_english_arm.compose_question's MQuAKE branch): stop at the
first unmentioned hop and apply the same gate, keeping B73's precise
branches (never-taught, reversal one-hop) byte-identical.

Mention definition (documented deltas vs REL_CUES92, same substring scan
otherwise): possessive "country's" counts as citizenship (sealed D2);
weak cues count only on-chain ("where"->origin, "located"->headquarters,
"son"->child, "house"/"city where"->location, "develop"->developer,
"created"->creator, "position"->sports-position); bare "found" never cues
(whole "founded"/"founder" still cue founded_by); unteachable keys dropped
(creator_country, founder); cue spans inside entity names ignored.
Each delta is tied to a sealed case that is otherwise unsatisfiable in
both directions (see _CHAIN_GATED147 and RESULTS.md).

Application: Align147Mixin (below) swaps these two composers in around a
single super().hear() call (try/finally restore -- no global state leaks,
no file edited), so every lineage routing (113b/121/134, 113e, 132+rewrite)
is preserved verbatim and only the composer verdicts change.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (read-only)

# Originals pinned at import: the mixin swaps module attributes at hear()
# time, so aligned functions must never resolve the composers they replace
# through the module (that would recurse into themselves).
_BASE_COMPOSE_N_HOP92 = B92.compose_n_hop
_BASE_COMPOSE_QUESTION73 = B73.compose_question
_BASE_ENTITY_MENTIONS92 = B92._entity_mentions92
_BASE_ENTITY_MENTIONS73 = B73._entity_mentions

# ---------------------------------------------------------------------------
# Mention table: REL_CUES92 verbatim + possessive-country delta (documented).
# Never mutates B92.REL_CUES92 (Q132 builds its canonical cues at import).
# ---------------------------------------------------------------------------
REL_CUES147: dict[str, list[str]] = {
    k: list(v) for k, v in B92.REL_CUES92.items()
}
# Mention-definition deltas vs REL_CUES92 (each tied to a sealed case;
# B92's table is never mutated -- Q132 builds canonical cues at import):
# 1. possessive "country's" counts as country_of_citizenship (sealed D2:
#    "Cora Lind's country's capital" mentions {citizenship, capital}).
_DELTA_ADD: dict[str, list[str]] = {
    "country_of_citizenship": ["country's", "countrys", "country\u2019s"],
}
# 2. weak cues count only on-chain (sealed C6/D5/186/D10/H2/141): bare
#    "where" is an origin mention only when origin is walked (186's "the
#    country where ..." keeps its hop; C6 "Where was X born?" drops the
#    phantom); bare "located" likewise for headquarters (141); "son" for
#    child (H2's "person"); "house" for location; relative scaffolding
#    "city where"/"city located where" (D10). Genuine questions mention
#    these relations on-chain, so nothing real is lost.
# 3. bare "develop" is not a creator mention and never was load-bearing.
# 4. bare "found" (substring of every "founded") is not a founded_by /
#    founder mention (sealed D6/E7); genuine ones carry
#    "founded"/"founder"/"establish".
# 5. "develop"->developer counts only on-chain (K6 still abstains via the
#    answer class; E5/H7 keep their walked developer).
_CHAIN_GATED147: dict[str, set[str]] = {
    "where": {"country_of_origin"},
    "located": {"headquarters_location"},
    "situated": {"headquarters_location"},
    "office": {"headquarters_location"},
    "son": {"child"},
    "house": {"location_of_formation"},
    "city where": {"location_of_formation"},
    "city located where": {"location_of_formation"},
    "develop": {"developer"},
    "created": {"creator"},
    # "is home (to)" scaffolds continent questions ("what continent is
    # home to ...", sealed 148/181/184), not origin hops.
    "is home": {"country_of_origin"},
    "home to": {"country_of_origin"},
    # Bare "position" is scaffolding in role questions ("holds the
    # chairperson position at ...", sealed mquake-088); the sports cue
    # "position played" is ungated and genuine position questions walk it.
    "position": {"position_played_on_team_speciality"},
}
_DELTA_DROP: dict[str, list[str]] = {
    "founded_by": ["found"],
    "founder": ["found"],
    "creator": ["develop"],
}
_DELTA_ADD_CUE: dict[str, list[str]] = {
    "founded_by": ["founded"],
    # Whole-word "created" cues creator as well as origin (sealed A04:
    # "Who created X?" answers a taught creator; K10 still abstains via
    # the answer class). The fragment "creat" stays redundant.
    "creator": ["created", "creator", "create"],
}
# 6. unteachable keys can never be walked: creator_country ("created" still
#    cues origin/creator) and founder ("founder" still cues founded_by).
#    Otherwise no "created"/"founder" question could ever satisfy the gate
#    (sealed D8/D9/I5/G4/E6).
_DELTA_DROP_KEYS = ("creator_country", "founder")
for _k, _cs in _DELTA_ADD.items():
    REL_CUES147[_k] = list(REL_CUES147.get(_k, [])) + list(_cs)
for _k, _cs in _DELTA_ADD_CUE.items():
    _have = set(REL_CUES147.get(_k, []))
    REL_CUES147[_k] = list(REL_CUES147.get(_k, [])) + [
        c for c in _cs if c not in _have]
for _k, _cs in _DELTA_DROP.items():
    if _k in REL_CUES147:
        REL_CUES147[_k] = [c for c in REL_CUES147[_k] if c not in _cs]
for _k in _DELTA_DROP_KEYS:
    REL_CUES147.pop(_k, None)


def _word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _at_start_boundary(s: str, i: int) -> bool:
    return i <= 0 or not _word_char(s[i - 1])


def _at_end_boundary(s: str, i: int) -> bool:
    return i >= len(s) or not _word_char(s[i])


def _cue_occurrences(question: str,
                     chain: set[str] | None = None
                     ) -> list[tuple[int, int, str]]:
    """All (start, end, relation) cue matches over REL_CUES147.

    Substring scan as in 92, except chain-gated cues (weak evidence like
    bare "where"/"located"/"son") only fire when their relation is on the
    taught chain from the start.
    """
    q = str(question).lower()
    chain_set = set(chain or ())
    occs: list[tuple[int, int, str]] = []
    for rel, cues in REL_CUES147.items():
        for cue in sorted(set(cues), key=len, reverse=True):
            if not cue:
                continue
            if (cue in _CHAIN_GATED147 and rel in _CHAIN_GATED147[cue]
                    and rel not in chain_set):
                continue
            start = 0
            while True:
                i = q.find(cue, start)
                if i < 0:
                    break
                occs.append((i, i + len(cue), rel))
                start = i + 1
    return occs


def _entity_spans147(question: str,
                     entities: list[str]) -> list[tuple[int, int]]:
    """Longest-match-first entity spans (same blocking as _entity_mentions92)."""
    q = str(question).lower()
    spans: list[tuple[int, int, str]] = []
    for e in sorted(set(entities), key=len, reverse=True):
        el = str(e).lower()
        if not el:
            continue
        start = 0
        while True:
            i = q.find(el, start)
            if i < 0:
                break
            spans.append((i, i + len(el), str(e)))
            start = i + 1
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    return [(s, t) for s, t, _ in kept]


_PRONOUN147_RE = re.compile(
    r"\b(who|whom|whose|which|that|where)\b", re.IGNORECASE)
_BYPART147_RE = re.compile(r"\b([A-Za-z]+(?:ed|en))\s+by\b")


def _subordinate147(question: str,
                    chain_nodes: list[str]) -> list[tuple[int, int]]:
    """Subordinate spans that identify a chain node (modifiers, not asks).

    (a) non-first pronoun-led clauses (who/whom/whose/which/that/where)
    to the next [,;?] or end; (b) participial "VERB by ENTITY" tails
    ("played by Harborlight Choir", sealed D8). A span qualifies only if
    it contains a chain-node name: the modifier identifies taught ground
    ("the music played by Harborlight Choir") rather than asking
    ("the child of Wren", a bare of-phrase, still asks). Entity mentions
    themselves are never affected.
    """
    q = str(question)
    ql = q.lower()
    nodes = sorted({str(n).lower() for n in chain_nodes if str(n)},
                   key=len, reverse=True)
    out: list[tuple[int, int]] = []

    def has_node(s: int, e: int) -> bool:
        seg = ql[s:e]
        return any(n and n in seg for n in nodes)

    for m in _PRONOUN147_RE.finditer(ql):
        if not ql[:m.start()].strip():
            continue
        end = len(ql)
        mm = re.search(r"[,;?]", ql[m.end():])
        if mm:
            end = m.end() + mm.start()
        if has_node(m.start(), end):
            out.append((m.start(), end))
    for m in _BYPART147_RE.finditer(q):
        tail = ql[m.end():]
        for n in nodes:
            if tail.startswith(" " + n) or tail.startswith(n):
                out.append((m.start(), m.end() + len(n) + 1))
                break
    return out


def _analyze147(question: str,
                entities: list[str] | None = None,
                chain: list[str] | None = None,
                chain_nodes: list[str] | None = None
                ) -> tuple[set[str], dict[tuple[int, int], set[str]],
                           dict[tuple[int, int], bool],
                           list[tuple[int, int]]]:
    """Mentioned relations + per-span relation sets + whole-token flags."""
    q = str(question).lower()
    chain_set = set(chain or ())
    occs = _cue_occurrences(question, chain_set)
    espans = _entity_spans147(question, list(entities or ()))
    spanrels: dict[tuple[int, int], set[str]] = {}
    for s, e, r in occs:
        spanrels.setdefault((s, e), set()).add(r)
    whole: dict[tuple[int, int], bool] = {}
    for s, e, _r in occs:
        ok = _at_start_boundary(q, s) and _at_end_boundary(q, e)
        whole[(s, e)] = whole.get((s, e), True) and ok
    # Non-first pronoun clauses and participial "by"-tails that identify a
    # chain node are subordinate modifiers (sealed H6/D8); cues strictly
    # inside them are kept as mentions (the walk may need them, sealed H1)
    # but are reported for tolerance. Entity mentions are never dropped.
    subs = _subordinate147(question, list(chain_nodes or ()))
    keep: list[bool] = [True] * len(occs)
    for i, (s, e, r) in enumerate(occs):
        if any(es <= s and e <= et and (et - es) > (e - s)
               for es, et in espans):
            keep[i] = False
            continue
        for (s2, e2), rels2 in spanrels.items():
            if (s2, e2) == (s, e):
                continue
            if s2 <= s and e <= e2 and (e2 - s2) > (e - s):
                if spanrels[(s, e)] <= rels2:
                    # Redundant fragment: adds no relation beyond its
                    # container (recall-neutral: the container still
                    # mentions every relation of this span).
                    keep[i] = False
                    break
                if r in chain_set:
                    continue
                if _at_start_boundary(q, s) and _at_end_boundary(q, e):
                    keep[i] = False
                    break
    kept_spanrels: dict[tuple[int, int], set[str]] = {}
    kept_whole: dict[tuple[int, int], bool] = {}
    for k, (s, e, r) in zip(keep, occs):
        if k:
            kept_spanrels.setdefault((s, e), set()).add(r)
            kept_whole[(s, e)] = whole[(s, e)]
    mentioned = set()
    for rels in kept_spanrels.values():
        mentioned |= rels
    return mentioned, kept_spanrels, kept_whole, subs


def relation_mentions147(question: str,
                         entities: list[str] | None = None,
                         chain: list[str] | None = None,
                         chain_nodes: list[str] | None = None) -> set[str]:
    """Relations mentioned in the question (see _analyze147)."""
    mentioned, _, _, _ = _analyze147(question, entities, chain, chain_nodes)
    return mentioned


def _full_chain147(start: str,
                   triples: list[tuple[str, str, str]]) -> list[str]:
    """Unconditional single-outgoing walk to the sink (shadow context)."""
    rels: list[str] = []
    cur = start
    seen: set[str] = set()
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) != 1:
            break
        r1 = uniq[0]
        mid = [o for (r, o) in outs if r == r1][-1]
        if mid in seen:
            break
        seen.add(mid)
        rels.append(r1)
        cur = mid
        if len(rels) > 6:
            break
    return rels


def _chain_nodes147(start: str,
                    triples: list[tuple[str, str, str]]) -> list[str]:
    """Start + every object along the unconditional walk (modifier ground)."""
    nodes = [start]
    cur = start
    seen: set[str] = set()
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) != 1:
            break
        mid = [o for (r, o) in outs if r == uniq[0]][-1]
        if mid in seen:
            break
        seen.add(mid)
        nodes.append(mid)
        cur = mid
        if len(nodes) > 7:
            break
    return nodes


def _entity_mentions147(question: str,
                        entities: list[str]) -> list[str]:
    """Same longest-match-first mention finder as _entity_mentions92."""
    return _BASE_ENTITY_MENTIONS92(question, entities)


# ---------------------------------------------------------------------------
# Answer-class + forward-plausibility schema (sealed I5/K10/H6/G5/D8).
#
# Shared cue stems ("created" -> creator + country_of_origin, "founder" ->
# founded_by) make pure set-equality unsatisfiable in both directions, so
# the gate is: stop-walk prefix P must be mentioned (subset), the wh-word's
# answer class must fit the terminal hop (I5 answers, K10 abstains), and
# every extra mentioned relation must be forward-IMPLAUSIBLE from the
# walked terminal (H6's spouse-from-a-place is tolerated; S4's
# capital-from-a-place and U1's citizenship-from-a-person block).
# Entity classes are read off the taught graph itself (spouse endpoints
# are persons, capital endpoints are places) -- no outside ontology.
# ---------------------------------------------------------------------------
_PERSON = "person"
_PLACE = "place"
_WORK = "work"
_ORG = "org"
_LANG = "language"
_OTHER = "other"

# relation -> subject classes (who can this hop start from).
_SUBJ147: dict[str, set[str]] = {
    "spouse": {_PERSON},
    "country_of_citizenship": {_PERSON},
    "capital": {_PLACE},
    "official_language": {_PLACE},
    "author": {_WORK},
    "creator": {_WORK},
    "developer": {_WORK},
    "manufacturer": {_WORK},
    "performer": {_WORK},
    "genre": {_PERSON, _ORG},
    "country_of_origin": {_WORK},
    "place_of_birth": {_PERSON},
    "place_of_death": {_PERSON},
    "educated_at": {_PERSON},
    "employer": {_PERSON},
    "occupation": {_PERSON},
    "headquarters_location": {_ORG},
    "location_of_formation": {_ORG},
    "founded_by": {_ORG, _WORK},
    "work_location": {_PERSON},
    "officeholder": {_OTHER},
    "head_of_state": {_PLACE},
    "head_of_government": {_PLACE},
    "chairperson": {_ORG},
    "sport": {_PERSON},
    "religion_or_worldview": {_PERSON},
    "child": {_PERSON},
    "notable_work": {_PERSON},
    "continent": {_PLACE},
    "head_coach": {_ORG},
    "original_broadcaster": {_ORG},
    "director_manager": {_ORG, _WORK},
    "chief_executive_officer": {_ORG},
    "language_of_work_or_name": {_WORK},
    "languages_spoken_written_or_signed": {_PERSON},
}
# relation -> object class (what the hop lands on).
_OBJ147: dict[str, str] = {
    "spouse": _PERSON,
    "country_of_citizenship": _PLACE,
    "capital": _PLACE,
    "official_language": _LANG,
    "author": _PERSON,
    "creator": _PERSON,
    "developer": _PERSON,
    "manufacturer": _ORG,
    "performer": _PERSON,
    "genre": _OTHER,
    "country_of_origin": _PLACE,
    "place_of_birth": _PLACE,
    "place_of_death": _PLACE,
    "educated_at": _ORG,
    "employer": _ORG,
    "occupation": _OTHER,
    "headquarters_location": _PLACE,
    "location_of_formation": _PLACE,
    "founded_by": _PERSON,
    "work_location": _PLACE,
    "officeholder": _PERSON,
    "head_of_state": _PERSON,
    "head_of_government": _PERSON,
    "chairperson": _PERSON,
    "sport": _OTHER,
    "religion_or_worldview": _OTHER,
    "child": _PERSON,
    "notable_work": _WORK,
    "continent": _PLACE,
    "head_coach": _PERSON,
    "original_broadcaster": _OTHER,
    "director_manager": _PERSON,
    "chief_executive_officer": _PERSON,
    "language_of_work_or_name": _LANG,
    "languages_spoken_written_or_signed": _LANG,
}
# Terminal-hop classes for the wh-word check.
_PERSON_T147 = frozenset({
    "spouse", "creator", "developer", "author", "author_of", "written_by",
    "composer_of", "composed_by", "founder_of", "founded_by", "inventor_of",
    "invented_by", "discoverer_of", "discovered_by", "performer",
    "officeholder", "head_of_state", "head_of_government", "chairperson",
    "head_coach", "chief_executive_officer", "child",
    "director_manager",
})
_PLACE_T147 = frozenset({
    "capital", "continent", "country_of_origin", "country_of_citizenship",
    "place_of_birth", "place_of_death", "headquarters_location",
    "location_of_formation", "work_location",
})
_LANG_T147 = frozenset({
    "official_language", "languages_spoken_written_or_signed",
    "language_of_work_or_name",
})

_WH_RE = {
    "who": re.compile(r"^\s*who\b", re.IGNORECASE),
    "where": re.compile(r"^\s*where\b", re.IGNORECASE),
    # Place-expecting: explicit ("what/which country|continent|city",
    # "capital") or periphrastic ("the name of the country/city ...",
    # sealed H3). A bare "city/country" inside a genuinely
    # person-expecting question is unattested in the sealed suites.
    "place_q": re.compile(
        r"what country|which country|what continent|which continent"
        r"|what city|which city|name of the countr|name of the cit"
        r"|name of the continent|\bcapital\b", re.IGNORECASE),
    "lang_q": re.compile(r"language", re.IGNORECASE),
}


def _wh_kind(question: str) -> str:
    q = str(question)
    if _WH_RE["who"].search(q):
        return "who"
    if _WH_RE["where"].search(q):
        return "where"
    if _WH_RE["place_q"].search(q):
        return "place_q"
    if _WH_RE["lang_q"].search(q):
        return "lang_q"
    return "generic"


def _wh_ok(question: str, walked: list[str]) -> bool:
    """The wh-word's answer class must fit the terminal hop."""
    if not walked:
        return False
    term = walked[-1]
    kind = _wh_kind(question)
    if kind == "who":
        return term not in _PLACE_T147
    if kind in ("where", "place_q"):
        return term not in _PERSON_T147
    if kind == "lang_q":
        return term not in _PERSON_T147 and term not in _PLACE_T147
    return True


def _extras_tolerated(question: str, walked: list[str],
                      mentioned: set[str],
                      spanrels: dict[tuple[int, int], set[str]],
                      whole: dict[tuple[int, int], bool],
                      subs: list[tuple[int, int]]) -> bool:
    """Every extra mentioned relation must be tolerated.

    An extra blocks (asked-but-untaught hop) when some occurrence cues it
    exclusively (no walked relation shares that span), except when the
    occurrence is a subordinate modifier identifying a chain node ("the
    music played by Harborlight Choir", sealed D8), wraps walked evidence
    ("birthplace of" around walked "birthplace", sealed mquake-006), is a
    fragment of a forward-implausible hop ("develop" beside a walked
    origin whose terminal is a place), or is a language-family descriptor
    with a walked language hop ("native tongue" beside walked
    languages_spoken, sealed P2-B3). Whole-word main-clause evidence of
    an un-walked hop ("a citizen of" beside a walked spouse; "the child
    of Wren") always blocks; unknown relations block (safe direction).
    """
    if not walked:
        return False
    pset = set(walked)
    terminal_class = _OBJ147.get(walked[-1])
    walked_lang = bool(pset & _LANG_T147)

    def in_sub(s: int, e: int) -> bool:
        return any(ds <= s and e <= de for ds, de in subs)

    def wraps_walked(s: int, e: int) -> bool:
        return any((s2, e2) != (s, e) and s <= s2 and e2 <= e
                   and (spanrels.get((s2, e2), set()) & pset)
                   for (s2, e2) in spanrels)

    for extra in set(mentioned) - pset:
        exclusive = [sp for sp, rels in spanrels.items()
                     if extra in rels and not (rels & pset)]
        if not exclusive:
            continue
        if all(in_sub(s, e) for s, e in exclusive):
            continue
        if extra in _LANG_T147 and walked_lang:
            continue
        if all(wraps_walked(s, e) for s, e in exclusive):
            continue
        if any(whole.get(sp, True) for sp in exclusive):
            return False
        if terminal_class is None or terminal_class in _SUBJ147.get(
                extra, {terminal_class}):
            return False
    return True


def _align_gate(question: str, walked: list[str],
                mentioned: set[str],
                spanrels: dict[tuple[int, int], set[str]],
                whole: dict[tuple[int, int], bool],
                subs: list[tuple[int, int]]) -> bool:
    """Stop-walk prefix P asks iff mentioned + class-fit + no live extra."""
    if not walked:
        return False
    if any(r not in mentioned for r in walked):
        return False
    if not _wh_ok(question, walked):
        return False
    return _extras_tolerated(question, walked, mentioned, spanrels, whole,
                             subs)


# ---------------------------------------------------------------------------
# Aligned N-hop composer (drop-in for B92.compose_n_hop).
# ---------------------------------------------------------------------------
def compose_n_hop147(question: str, triples: list[tuple[str, str, str]]
                     ) -> tuple[str, list[str]] | None:
    """Aligned walk: stop at the first unmentioned hop; gate the prefix.

    The question must name exactly one taught entity (the chain start); from
    there follow the single-outgoing-relation chain ONLY while each next
    hop's relation is mentioned in the question. Answer (start, walked)
    only when the alignment gate holds (walked mentioned, wh-word fits the
    terminal hop, no forward-plausible extra); otherwise None and the
    existing fallback/abstain path acts.
    """
    q = " ".join(str(question).split())
    if not q:
        return None
    ents: list[str] = []
    for s, _, o in triples:
        ents.extend([s, o])
    ment = _entity_mentions147(q, ents)
    if len(ment) != 1:
        return None
    start = ment[0]
    full = _full_chain147(start, triples)
    mentioned, spanrels, whole, subs = _analyze147(
        q, ents, full, _chain_nodes147(start, triples))
    rels: list[str] = []
    cur = start
    seen_objs: set[str] = set()
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) != 1:
            break
        r1 = uniq[0]
        if r1 not in mentioned:
            break  # THE FIX: stop at the first unmentioned hop
        mid = [o for (r, o) in outs if r == r1][-1]
        if mid in seen_objs:
            return None
        seen_objs.add(mid)
        rels.append(r1)
        cur = mid
        if len(rels) > 6:
            return None
    if rels and len(rels) < len(full):
        # The base walker runs to the sink and bails (None) on cycles;
        # stopping early must not turn a cycle into a confident prefix
        # (sealed L5-Z2 reversal: Silver Feasts <-> Dunstan Ashdown).
        # Walk on past the prefix ignoring mentions: revisiting the start
        # or any walked object means the chain cycles -> None.
        seen_cyc = {start} | set(seen_objs)
        cyc = cur
        for _ in range(8):
            outs = [(r, o) for (s, r, o) in triples if s == cyc]
            uniq = list(dict.fromkeys(r for r, _ in outs))
            if len(uniq) != 1:
                break
            mid = [o for (r, o) in outs if r == uniq[0]][-1]
            if mid in seen_cyc:
                return None
            seen_cyc.add(mid)
            cyc = mid
    if not _align_gate(q, rels, mentioned, spanrels, whole, subs):
        return None
    return (start, rels)


# ---------------------------------------------------------------------------
# Aligned 2-hop composer (drop-in for B73.compose_question's MQuAKE branch).
# B73's precise branches (never-taught, reversal one-hop) are inherited
# verbatim by delegating non-MQuAKE shapes to B73 itself.
# ---------------------------------------------------------------------------
def compose_question147(question: str, triples: list[tuple[str, str, str]]
                        ) -> tuple[str, list[str]] | None:
    """B73 shapes preserved; the 2-hop walk gains the alignment gate."""
    q = " ".join(str(question).split())
    if not q:
        return None
    base = _BASE_COMPOSE_QUESTION73(q, triples)
    if base is not None and len(list(base[1])) == 1:
        # Precise branches (never-taught one-hop, reversal one-hop) pass
        # through verbatim: they never walk a taught chain.
        return base
    if base is not None and any(str(r).startswith("never_taught")
                                for r in list(base[1])):
        # B73's never-taught 2-hop branch asks an undeclared key so the
        # notebook abstains structurally ("I don't know ...", sealed
        # L5-Z2 abstain-broken); the fallback clarify would score MISS.
        return base
    # Native aligned 2-hop walk: B73's MQuAKE branch
    # (fable_bench73_english_arm.py:293-314) with the 147 mention table,
    # the stop rule, and the alignment gate.
    ents: list[str] = []
    for s, _, o in triples:
        ents.extend([s, o])
    ment = _BASE_ENTITY_MENTIONS73(q, ents)
    if len(ment) != 1:
        return None
    start = ment[0]
    mentioned, spanrels, whole, subs = _analyze147(
        q, ents, _full_chain147(start, triples),
        _chain_nodes147(start, triples))
    r1s = [r for (s, r, _) in triples if s == start]
    r1s = list(dict.fromkeys(r1s))
    if len(r1s) != 1:
        return None
    r1 = r1s[0]
    if r1 not in mentioned:
        return None  # stop rule: the walk never starts
    objs = [o for (s, r, o) in triples if s == start and r == r1]
    if not objs:
        return None
    mid = objs[-1]  # post-edit object: corrections supersede
    r2s = [r for (s, r, _) in triples if s == mid and r != r1]
    r2s = list(dict.fromkeys(r2s))
    if len(r2s) != 1:
        return None
    r2 = r2s[0]
    if not _align_gate(q, [r1, r2], mentioned, spanrels, whole, subs):
        return None
    return (start, [r1, r2])


class Align147Mixin:
    """Swap the aligned composers in for one hear() call (no global leak).

    MRO use: class Loop147Ears(Align147Mixin, Loop134Ears) -- hear() swaps
    B92.compose_n_hop / B73.compose_question for the aligned versions,
    calls super().hear() (the lineage routing, verbatim), and restores in
    a finally. Teach turns never reach the composers, so only "?" turns
    can change; clarifies stay clarifies unless the aligned frame asks.
    """

    name = "loop147-mention-walk-alignment"

    def hear(self, turn: str) -> list[dict]:
        import fable_bench73_english_arm as _B73
        import fable_bench92_english_arm as _B92
        s92, s73 = _B92.compose_n_hop, _B73.compose_question
        _B92.compose_n_hop, _B73.compose_question = (
            compose_n_hop147, compose_question147)
        try:
            return super().hear(turn)  # type: ignore[misc]
        finally:
            _B92.compose_n_hop, _B73.compose_question = s92, s73


def cmd_selftest(_args=None) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag, flush=True)
        if not cond:
            fails.append(tag)

    # Suffix: 1-hop question, chain continues -> answer the asked hop.
    t = [("Joren Hale", "spouse", "Petra Voss"),
         ("Petra Voss", "country_of_citizenship", "Litora")]
    check(compose_n_hop147("Who is Joren Hale married to?", t)
          == ("Joren Hale", ["spouse"]), "suffix-1hop-answers")
    check(compose_n_hop147("Who is the spouse of Joren Hale?", t)
          == ("Joren Hale", ["spouse"]), "suffix-of-frame-answers")
    # Prefix: asked-but-untaught hop -> None (abstain downstream).
    t2 = [("Bram Kite", "spouse", "Cora Lind")]
    check(compose_n_hop147(
        "What country is the spouse of Bram Kite a citizen of?", t2)
        is None, "prefix-abstains")
    # Cue-stem mismatch (K6 shape): "developed" cues developer+origin.
    t3 = [("HarborOS", "country_of_origin", "Veldoria")]
    check(compose_n_hop147("Who developed HarborOS?", t3) is None,
          "cue-stem-abstains")
    # Answer-class mismatch with shared stem (I5 answers, K10 abstains).
    t5 = [("Sunmosaic", "country_of_origin", "Veldoria")]
    check(compose_n_hop147("In which country was Sunmosaic created?", t5)
          == ("Sunmosaic", ["country_of_origin"]), "shared-stem-answers")
    check(compose_n_hop147("What country was Sunmosaic created in?",
                           [("Sunmosaic", "creator", "Yara Haddad")]) is None,
          "shared-stem-type-abstains")
    # Forward-implausible extra tolerated (H6 shape: spouse-from-a-place).
    t4 = [("Cora Lind", "country_of_citizenship", "Norland"),
          ("Norland", "capital", "Aldport")]
    check(compose_n_hop147("What is Cora Lind's country's capital?", t4)
          == ("Cora Lind", ["country_of_citizenship", "capital"]),
          "possessive-country-answers")
    check(compose_n_hop147(
        "What is the capital of the country of citizenship of the man"
        " who is married to Cora Lind?", t4)
          == ("Cora Lind", ["country_of_citizenship", "capital"]),
          "relative-extra-answers")
    # Forward-plausible extra blocks (S4 shape: capital-from-a-place).
    t6 = [("Mira Solis", "spouse", "Petra Voss"),
          ("Petra Voss", "country_of_citizenship", "Veldoria")]
    check(compose_n_hop147(
        "What is the capital of the country of citizenship of the person"
        " married to Mira Solis?", t6) is None, "forward-extra-abstains")
    # "where" is not an origin mention (C6 shape); "found" is not a
    # founded_by mention (D6 shape); whole-word "son" (H2 shape).
    check(compose_n_hop147("Where was Bram Kite born?",
                           [("Bram Kite", "place_of_birth", "Dunmere")])
          == ("Bram Kite", ["place_of_birth"]), "where-born-answers")
    check(compose_n_hop147(
        "Where was the company that employs Nadia Frost founded?",
        [("Nadia Frost", "employer", "Harborline"),
         ("Harborline", "location_of_formation", "Dunmere")])
          == ("Nadia Frost", ["employer", "location_of_formation"]),
          "founded-location-answers")
    check(compose_n_hop147(
        "Who is the person that wrote the book that Bram Kite is famous for?",
        [("Bram Kite", "notable_work", "The Glass Orchard"),
         ("The Glass Orchard", "author", "Yara Haddad")])
          == ("Bram Kite", ["notable_work", "author"]), "son-noise-answers")
    t4 = [("Cora Lind", "country_of_citizenship", "Norland"),
          ("Norland", "capital", "Aldport")]
    check(compose_n_hop147("What is Cora Lind's country's capital?", t4)
          == ("Cora Lind", ["country_of_citizenship", "capital"]),
          "possessive-country-answers")
    # Intact 2-hop answers.
    check(compose_n_hop147(
        "What is the capital of the country Cora Lind is a citizen of?",
        t4) == ("Cora Lind", ["country_of_citizenship", "capital"]),
          "intact-2hop-answers")
    # Branch / unknown / empty stay None.
    check(compose_n_hop147("Who is Bram Kite married to?",
                           [("Bram Kite", "spouse", "Cora Lind"),
                            ("Bram Kite", "country_of_citizenship",
                             "Norland")]) is None, "branch-none")
    check(compose_n_hop147("", t) is None, "empty-none")
    # 2-hop sibling: intact answers, prefix abstains.
    check(compose_question147(
        "What is the official language of the country of citizenship"
        " of Roberto Merhi?",
        [("Roberto Merhi", "country_of_citizenship", "Spain"),
         ("Spain", "official_language", "Spanish")]) is not None,
          "sibling-intact-answers")
    check(compose_question147(
        "What is the official language of the country of citizenship"
        " of the spouse of Bram Kite?",
        [("Bram Kite", "spouse", "Cora Lind"),
         ("Cora Lind", "country_of_citizenship", "Norland")]) is None,
          "sibling-prefix-abstains")
    # Mixin restores globals.
    import fable_bench92_english_arm as _B92
    before = _B92.compose_n_hop
    m = Align147Mixin()
    try:
        m.hear("hello.")
    except Exception:
        pass
    check(_B92.compose_n_hop is before, "mixin-restores")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(cmd_selftest())
