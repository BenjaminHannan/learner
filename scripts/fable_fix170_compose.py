#!/usr/bin/env python3
"""Experiment 170 -- index-backed composers for the loop138d stack.

THE ONE CHANGE (this file only; no existing file is edited): every
per-ask full-notebook scan in the loop138d "?" path reads the incremental
index (142's per-(subject, relation) structures, maintained on every
notebook append) instead of rescanning all facts, so each ask costs work
proportional to the facts it touches.

Scans fixed (all read-only; same call sites, same order, same decisions):
  C1 fable_loop90_agent.py:101 notebook_triples() full facts scan per hear
     (loop138_agent.py:121 every "?" turn; loop138b_agent.py:214 on every
     "?" clarify via the 132 rewriter) -> cached list from inner._triples
     (verified element-for-element in dev + S2 states).
  C2 whole-word entity mentions (fable_wordmatch149_core, applied in the
     138d process): re.compile PER ENTITY per ask inside B92/B73 composers
     and Q132 rewrite leaves -> prefilter with str.find (C speed) + one
     cached compiled pattern per entity string used as the oracle, so the
     spans are produced by the very same regexes (byte-identical).
  C3 fable_bench92_english_arm.py:198 compose_n_hop() per-step triple scans
     (+ ents build) -> walk over inner._sro/_srel (same order, same gates).
  C4 fable_bench73_english_arm.py:246 compose_question() MQuAKE section
     (ents build + per-step scans; Who/never-taught branches kept verbatim,
     _one_hop served from a lazily built per-version reverse map) -> index.
  C5 fable_loop113c_agent.py:112 frame_consumes_question() names-set build
     + sort over all triples per ask -> cached sorted names per version.
  C6 fable_loop113_agent.py:123 compound_subject_hit() triple scan with
     per-row normalization per ask -> index walk + precomputed subjects.
  C7 fable_loop148b_agent.py:141 _screen148b_kind() 30k-name exemption
     scan per "?" turn -> sealed trigger regexes first; the exemption scan
     runs only when a trigger fires (exemptions can only remove hits).
  (Loop113._walk_nodes (only reached via rewrite fallbacks) keeps scanning
  the CACHED triples list. _rewrite132, _trial_start island steps and the
  consumption loop all run over the same cached list with the fast leaves.)

Fallback rule: whenever the triples object is not our cached list (foreign
caller, version change mid-call), each fast function delegates to the
original it saved at install time. Replies are therefore identical by
construction on unknown shapes and identical by index-equivalence on the
loop path (checked empirically: S1/S2 byte-identity + G1/G2/G3 zero moves).

Install: install_index170() rebinds module attributes process-locally (the
same pattern WM149.apply_wordmatch uses). Called once from
scripts/fable_loop170_agent.py after the loop138d import (so the wordmatch
rebinding is already in place and what we wrap is the sealed behaviour).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (patched leaves, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (patched leaves, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop113_agent as L113  # noqa: E402 (walk/compound, read-only)
import fable_loop113c_agent as L113C  # noqa: E402 (consumption gate, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen kind, read-only)
import fable_qrewrite132 as Q132  # noqa: E402 (rewrite leaves, read-only)
import fable_screen148_mixin as S148  # noqa: E402 (trigger regexes, read-only)
import fable_wordmatch149_core as WM149  # noqa: E402 (pattern oracle, read-only)
from fable_thought49_notebook import ThoughtNotebook  # noqa: E402

# -- saved originals (fallback) -------------------------------------------
_ORIG_TRIPLES = L90.notebook_triples
_ORIG_NHOP = B92.compose_n_hop
_ORIG_COMPOSE = B73.compose_question
_ORIG_FCQ = L113C.frame_consumes_question
_ORIG_M92 = B92._entity_mentions92
_ORIG_M73 = B73._entity_mentions
_ORIG_SPANS = WM149.entity_spans
_ORIG_WORDM = WM149.word_mentions
_ORIG_SPAN_OF = Q132._span_of
_ORIG_SEED = Q132._seed_subjects
_ORIG_DECOMP = Q132._decomp_subjects
_ORIG_COMPOUND = L113.compound_subject_hit
_ORIG_SCREEN_KIND = L148b.ScreenStatusMixin148b._screen148b_kind

_INSTALLED = False

# -- caches ----------------------------------------------------------------
_PAT_CACHE: dict[str, object] = {}
_TRIPLES: dict[int, list] = {}   # id(inner) -> [version, list, inner]
_SRC: dict[int, list] = {}       # id(triples list) -> [inner, version]
_NAMES: dict[int, list] = {}     # id(triples list) -> [inner, version, names]
_ONEHOP: dict[int, list] = {}    # id(triples list) -> [inner, version, revmap]
_SL: dict[int, list] = {}        # id(triples list) -> [inner, version, sl]
_SORTED: dict[int, list] = {}    # id(triples list) -> [version, sorted, low, inner]


def _pat_for(entity: str):
    """The sealed whole-word pattern for one entity string, cached."""
    pat = _PAT_CACHE.get(entity)
    if pat is None:
        pat = WM149._entity_pattern(entity)
        if len(_PAT_CACHE) > 131072:
            _PAT_CACHE.clear()
        _PAT_CACHE[entity] = pat
    return pat


def _inner_of(nb):
    try:
        return nb.nb if isinstance(nb, ThoughtNotebook) else nb
    except Exception:
        return None


def fast_notebook_triples(nb) -> list:
    """C1: cached (subject, relation, display) list from the index."""
    inner = _inner_of(nb)
    try:
        if (inner is not None and hasattr(inner, "_triples")
                and hasattr(inner, "events") and hasattr(inner, "facts")):
            v = len(inner.events)
            e = _TRIPLES.get(id(inner))
            if e is not None and e[2] is inner and e[0] == v:
                return e[1]
            lst = [(s, r, d) for (_, s, r, d) in inner._triples]
            if len(_TRIPLES) > 8:
                _TRIPLES.clear()
            if len(_SRC) > 8:
                _SRC.clear()
                _NAMES.clear()
                _ONEHOP.clear()
            _TRIPLES[id(inner)] = [v, lst, inner]
            _SRC[id(lst)] = [inner, v]
            return lst
    except Exception:
        pass
    return _ORIG_TRIPLES(nb)


def _src_of(triples):
    """Inner notebook behind our cached triples list, else None."""
    if isinstance(triples, list):
        e = _SRC.get(id(triples))
        if e is not None:
            inner, v = e
            try:
                if len(inner.events) == v:
                    return inner
            except Exception:
                pass
            _SRC.pop(id(triples), None)
    return None


def _sl_for(triples, inner):
    """Normalized subject strings parallel to the cached triples list."""
    try:
        v = len(inner.events)
    except Exception:
        return None
    e = _SL.get(id(triples))
    if e is not None and e[0] is inner and e[1] == v:
        return e[2]
    sl = [" ".join(str(s).split()).lower() for (s, _r, _o) in triples]
    if len(_SL) > 8:
        _SL.clear()
    _SL[id(triples)] = [inner, v, sl]
    return sl


def _spans_sorted(q: str, ql: str, srt: list, low: list) -> list:
    """Spans over a pre-sorted unique entity list with parallel lowers."""
    spans: list[tuple[int, int, str]] = []
    find = ql.find
    for e, el in zip(srt, low):
        if not e or find(el) < 0:
            continue
        pat = _pat_for(e)
        if pat is None:
            continue
        for m in pat.finditer(q):
            spans.append((m.start(), m.end(), e))
    return spans


def _tail92(spans: list) -> list:
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    return kept


def _tail73(spans: list) -> list:
    spans.sort()
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    return kept


# -- C2: whole-word spans with the sealed regexes as oracle -----------------
def fast_entity_spans(question: str, entities) -> list:
    """WM149.entity_spans over the same set, same order, same spans.

    Iteration replicates `sorted(set(entities), key=len, reverse=True)`
    exactly; entities with no case-insensitive substring hit skip the regex
    (the regex can only match where the lowered text contains the lowered
    entity, up to exotic Unicode casefold edge cases, covered empirically
    by S1/S2/G1/G2/G3 reply-identity). Every entity WITH a hit runs the
    sealed compiled pattern, so emitted spans are the regex's own.
    """
    q = str(question)
    ql = q.lower()
    srt = sorted(set(str(x) for x in entities), key=len, reverse=True)
    spans = _spans_sorted(q, ql, srt, [s.lower() for s in srt])
    return _tail92(spans)


def _seen_in_order(kept) -> list[str]:
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def fast_mentions92(question: str, entities: list[str]) -> list[str]:
    """B92 longest-span-wins tail over the fast spans."""
    return _seen_in_order(fast_entity_spans(question, entities))


def fast_mentions73(question: str, entities: list[str]) -> list[str]:
    """B73 earliest-span tail over the fast spans (verbatim tail)."""
    spans = fast_entity_spans(question, entities)
    return _seen_in_order(_tail73(spans))


def mentions92_indexed(q: str, triples, inner) -> list[str] | None:
    """Whole-word mentions over the triples' entity set (None on staleness).

    The set is built from the cached triples in original order, so
    `sorted(set, key=len, reverse=True)` iterates exactly as the sealed
    composers' `sorted(set(ents), ...)` -- same spans, same tails.
    """
    e = _SORTED.get(id(triples))
    try:
        v = len(inner.events)
    except Exception:
        return None
    if e is not None and e[3] is inner and e[0] == v:
        srt, low = e[1], e[2]
    else:
        ents: list[str] = []
        for s, _r, o in triples:
            ents.extend([s, o])
        srt = sorted(set(ents), key=len, reverse=True)
        low = [s.lower() for s in srt]
        if len(_SORTED) > 8:
            _SORTED.clear()
        _SORTED[id(triples)] = [v, srt, low, inner]
    return _seen_in_order(_tail92(_spans_sorted(q, q.lower(), srt, low)))


def mentions73_indexed(q: str, triples, inner) -> list[str] | None:
    """B73-tail mentions over the triples' entity set (None on staleness)."""
    e = _SORTED.get(id(triples))
    try:
        v = len(inner.events)
    except Exception:
        return None
    if e is not None and e[3] is inner and e[0] == v:
        srt, low = e[1], e[2]
    else:
        ents: list[str] = []
        for s, _r, o in triples:
            ents.extend([s, o])
        srt = sorted(set(ents), key=len, reverse=True)
        low = [s.lower() for s in srt]
        if len(_SORTED) > 8:
            _SORTED.clear()
        _SORTED[id(triples)] = [v, srt, low, inner]
    return _seen_in_order(_tail73(_spans_sorted(q, q.lower(), srt, low)))


def fast_span_of(ql: str, text: str):
    """Sealed Q132._span_of (post-wordmatch): whole-word span or None."""
    t = str(text)
    if not t:
        return None
    if str(ql).lower().find(t.lower()) < 0:
        return None
    pat = _pat_for(t)
    if pat is None:
        return None
    m = pat.search(str(ql))
    if m is None:
        return None
    return (m.start(), m.end())


def fast_seed_subjects(question: str, triples) -> list[str]:
    """Sealed WM149.seed_subjects with the find prefilter."""
    subs = sorted({str(s) for s, _, _ in triples}, key=len, reverse=True)
    q = str(question)
    ql = q.lower()
    spans: list[tuple[int, int, str]] = []
    for s in subs:
        if not s:
            continue
        if ql.find(s.lower()) < 0:
            continue
        pat = _pat_for(s)
        if pat is None:
            continue
        for m in pat.finditer(q):
            spans.append((m.start(), m.end(), s))
    spans.sort(key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    return _seen_in_order(kept)


def fast_decomp_subjects(question: str, triples) -> list[str]:
    """Sealed WM149.decomp_subjects (span_of resolves to the fast one)."""
    qtok = set(WM149._tok(question))
    qn = {Q132._typonorm(t) for t in qtok}
    ql = str(question).lower()
    out: list[str] = []
    for (s, _r, _o) in triples:
        s = str(s)
        parts = Q132._split_of(s)
        if parts is None:
            continue
        pre, tgt = parts
        if fast_span_of(ql, tgt) is None:
            continue
        pw = [t for t in WM149._tok(pre) if t not in Q132._STOP]
        if not pw:
            continue
        if all(Q132._typonorm(w) in qn for w in pw):
            if s not in out:
                out.append(s)
    return out


# -- C3: N-hop compose over the index ----------------------------------------
def fast_compose_n_hop(question: str, triples) -> tuple | None:
    """Sealed B92.compose_n_hop; the walk reads _sro/_srel (same order)."""
    inner = _src_of(triples)
    if inner is None:
        return _ORIG_NHOP(question, triples)
    q = " ".join(str(question).split())
    if not q:
        return None
    ment = mentions92_indexed(q, triples, inner)
    if ment is None:
        return _ORIG_NHOP(question, triples)
    if len(ment) != 1:
        return None
    start = ment[0]
    rels: list[str] = []
    cur = start
    seen_objs: set[str] = set()
    try:
        while True:
            srel = inner._srel.get(cur)
            if not srel:
                break
            uniq = list(dict.fromkeys(srel))
            if len(uniq) != 1:
                break
            r1 = uniq[0]
            outs = inner._sro.get((cur, r1), [])
            if not outs:
                break
            mid = outs[-1]
            if mid in seen_objs:
                return None
            seen_objs.add(mid)
            rels.append(r1)
            cur = mid
            if len(rels) > 6:
                return None
    except (AttributeError, TypeError):
        return _ORIG_NHOP(question, triples)
    if not rels:
        return None
    mentioned = B92._relation_mentions92(q)
    if any(r not in mentioned for r in rels):
        return None
    return (start, rels)


# -- C4: bench73 compose -------------------------------------------------------
def _onehop_map(triples, inner):
    e = _ONEHOP.get(id(triples))
    if e is not None and e[0] is inner:
        try:
            if len(inner.events) == e[1]:
                return e[2]
        except Exception:
            pass
    rev: dict[tuple[str, str], str] = {}
    for (s, r, o) in triples:
        rev.setdefault((str(r), str(o)), str(s))
    try:
        v = len(inner.events)
    except Exception:
        v = -1
    if len(_ONEHOP) > 8:
        _ONEHOP.clear()
    _ONEHOP[id(triples)] = [inner, v, rev]
    return rev


def fast_compose_question(question: str, triples) -> tuple | None:
    """Sealed B73.compose_question; MQuAKE walk over the index.

    Never-taught and Who branches are the original logic verbatim; only the
    underlying scans (ents build, per-step triple walks, _one_hop) read the
    index / cached structures.
    """
    inner = _src_of(triples)
    if inner is None:
        return _ORIG_COMPOSE(question, triples)
    q = " ".join(str(question).split())
    if not q:
        return None
    m = re.fullmatch(r"What is the never-taught relation (\d+) of (.+?)\??", q)
    if m:
        return (m.group(2).strip(), [f"never_taught_rel_{m.group(1)}"])
    m = re.fullmatch(
        r"What is the never-taught relation of the ([\w /-]+?) of (.+?)\??", q)
    if m:
        key = B73.REV_OF_NOUNS.get(m.group(1).strip().lower().replace(" ", "_"))
        if key is None:
            return None
        return (m.group(2).strip(), [key, "never_taught_rel"])
    m = re.fullmatch(r"Who is the ([\w /-]+?) of (.+?)\??", q)
    if m:
        label = m.group(1).strip().lower().replace(" ", "_")
        name = m.group(2).strip()
        if label in B73.REV_OF_NOUNS and B73._bare_name_ok(name):
            return _fast_one_hop(name, B73.REV_OF_NOUNS[label], triples, inner)
    m = re.fullmatch(r"Who (\w+) by (.+?)\??", q)
    if m:
        verb = m.group(1).strip().lower()
        name = m.group(2).strip()
        if verb in B73.REV_BY_VERBS and B73._bare_name_ok(name):
            return _fast_one_hop(name, B73.REV_BY_VERBS[verb], triples, inner)
    ment = mentions73_indexed(q, triples, inner)
    if ment is None:
        return _ORIG_COMPOSE(question, triples)
    if len(ment) != 1:
        return None
    start = ment[0]
    try:
        r1s = list(dict.fromkeys(inner._srel.get(start, ())))
        if len(r1s) != 1:
            return None
        r1 = r1s[0]
        objs = list(inner._sro.get((start, r1), ()))
        if not objs:
            return None
        mid = objs[-1]
        r2s = [r for r in inner._srel.get(mid, ()) if r != r1]
        r2s = list(dict.fromkeys(r2s))
        if len(r2s) != 1:
            return None
        r2 = r2s[0]
    except (AttributeError, TypeError):
        return _ORIG_COMPOSE(question, triples)
    mentioned = B73._relation_mentions(q)
    if r1 not in mentioned or r2 not in mentioned:
        return None
    return (start, [r1, r2])


def _fast_one_hop(name: str, rel: str, triples, inner) -> tuple:
    """Sealed B73._one_hop over a lazily built per-version reverse map."""
    try:
        if name in inner._srel and rel in inner._srel.get(name, ()):
            if inner._sro.get((name, rel)):
                return (name, [rel])
        rev = _onehop_map(triples, inner)
        hit = rev.get((rel, name))
        if hit is not None:
            return (hit, [rel])
        return (name, [rel])
    except (AttributeError, TypeError):
        return B73._one_hop(name, rel, triples)


# -- C6: compound-subject guard over the index --------------------------------
def fast_compound_hit(triples, start: str, rels: list) -> tuple | None:
    """Sealed L113.compound_subject_hit; walk via _sro, scan via cached sl.

    The final containment scan returns the first triple in triples order,
    replicated by scanning the cached list with precomputed normalized
    subjects (same order, same predicate).
    """
    inner = _src_of(triples)
    if inner is None:
        return _ORIG_COMPOUND(triples, start, rels)
    try:
        nodes = {" ".join(str(start).split()).lower()}
        cur = start
        for rel in rels:
            objs = inner._sro.get((cur, rel), [])
            if not objs:
                return None
            cur = objs[-1]
            nodes.add(" ".join(str(cur).split()).lower())
        end = cur
    except (AttributeError, TypeError):
        return _ORIG_COMPOUND(triples, start, rels)
    el = " ".join(str(end).split()).lower()
    sl = _sl_for(triples, inner)
    if sl is None:
        return _ORIG_COMPOUND(triples, start, rels)
    for (s, r, o), sll in zip(triples, sl):
        if sll != el and sll not in nodes and el in sll:
            return (s, r, o)
    return None
# -- C5: consumption gate over cached names ------------------------------------
def fast_frame_consumes(question: str, rels, triples=None) -> bool:
    """Sealed L113C.frame_consumes_question; names list cached per version."""
    if triples is None:
        return _ORIG_FCQ(question, rels, triples)
    inner = _src_of(triples)
    if inner is None:
        return _ORIG_FCQ(question, rels, triples)
    e = _NAMES.get(id(triples))
    names = None
    if e is not None and e[0] is inner:
        try:
            if len(inner.events) == e[1]:
                names = e[2]
        except Exception:
            names = None
    if names is None:
        names = sorted({str(s) for s, _, _ in triples}
                       | {str(o) for _, _, o in triples},
                       key=len, reverse=True)
        try:
            v = len(inner.events)
        except Exception:
            v = -1
        if len(_NAMES) > 8:
            _NAMES.clear()
        _NAMES[id(triples)] = [inner, v, names]
    q = L113C._norm_q(question)
    if L113C.has_trailing_qualifier(question):
        return False
    walked = [str(r) for r in (rels or [])]
    if not walked:
        return False
    cues: list[str] = []
    for rel in walked:
        cues.extend(B92.REL_CUES92.get(rel, []))
    work = q
    for cue in sorted(set(cues), key=len, reverse=True):
        c = cue.lower()
        if c:
            work = work.replace(c, " ")
    for name in names:
        n = " ".join(str(name).split()).lower()
        if n and len(n) <= len(work):
            work = work.replace(n, " ")
    walked_set = set(walked)
    for rel, rcues in B92.REL_CUES92.items():
        if rel in walked_set:
            continue
        for cue in rcues:
            c = cue.lower()
            if c in L113C._DROP_CUES:
                continue
            if " " in c:
                if c in work:
                    return False
            elif L113C._word_re(c).search(work):
                return False
    return True


# -- C7: 148b screen kind with a trigger pre-check ------------------------------
def _raw_trigger_hit(text: str) -> bool:
    """True iff any sealed 148 trigger regex fires on the raw text."""
    q = str(text)
    for rx in S148._NEG_RES:
        if rx.search(q):
            return True
    if S148._NO_ONE_RE.search(q) or S148._NT_RE.search(q):
        return True
    if S148._YEAR_RE.search(q):
        return True
    for rx in S148._TIME_RES:
        if rx.search(q):
            return True
    if S148._AS_OF_RE.search(q) or S148._USED_TO_RE.search(q):
        return True
    return False


def fast_screen148b_kind(self, text: str):
    """Sealed _screen148b_kind; skips the 30k-name exemption scan when no
    trigger fires on the raw text (exemptions can only remove hits)."""
    if text and text.rstrip().endswith("?") and self.nb is not None:
        try:
            if not _raw_trigger_hit(text):
                return None
        except Exception:
            pass
    return _ORIG_SCREEN_KIND(self, text)


# -- install -------------------------------------------------------------------
def install_index170() -> None:
    """Rebind the scanning leaves process-locally (no file edited)."""
    global _INSTALLED
    if _INSTALLED:
        return
    L90.notebook_triples = fast_notebook_triples
    B92._entity_mentions92 = fast_mentions92
    B73._entity_mentions = fast_mentions73
    WM149.entity_spans = fast_entity_spans
    WM149.word_mentions = lambda question, entities: _seen_in_order(
        fast_entity_spans(question, entities))
    Q132._span_of = fast_span_of
    Q132._seed_subjects = fast_seed_subjects
    Q132._decomp_subjects = fast_decomp_subjects
    B92.compose_n_hop = fast_compose_n_hop
    B73.compose_question = fast_compose_question
    L113.compound_subject_hit = fast_compound_hit
    L113C.frame_consumes_question = fast_frame_consumes
    L148b.ScreenStatusMixin148b._screen148b_kind = fast_screen148b_kind
    _INSTALLED = True


def is_installed() -> bool:
    return _INSTALLED
