#!/usr/bin/env python3
"""Experiment 132 -- deterministic question REWRITER (question-phrasing cover).

Diagnosis (exps 121/113, dev splits data/open/bench103 + data/open/bench121,
400 four-hop items, fresh loop121 notebooks): loop121 answers ~294 and its
abstains are dominated by the loop's own "I didn't understand that"
(CHAIN_MISS_TEXT). Three mechanical classes, all on the QUESTION side:

  A. intact walk, cue gap (dev ~35): the N-hop walk from the single mentioned
     entity reaches the sink, but the question phrases a hop with words the
     code cue tables never list ("head coach" for the taught-as-officeholder
     compound hop, "calls home" / "is home to" for citizenship, "faith" /
     "adheres" for religion, "performance" for performer, "produced the
     work ... known for" for origin).
  B. island walk (dev ~55): teaches of the shape "The R of X is Y" are stored
     as compound subjects ("director of The Beatles", "head coach of X",
     "origianl broadcaster of X" -- typo as in the raw data -- all with
     relation officeholder), so the plain walk stops after a prefix (then the
     compound-subject guard clarifies) or finds no entity at all. The full
     chain exists as compound islands linked by string containment.
  C. unfixable question-side (dev ~16): loop-guarded repeats, genuinely
     ambiguous templates -- passed through unchanged.

THE ONE CHANGE (this module + the loop132 wrapper, no existing file edited):
rewrite_question(question, triples) resolves the question's nested
"R of ..." descriptions against the NOTEBOOK (verbatim entities, compound
subjects with typo-normalised prefixes, single-outgoing triple hops), walks
the resolved chain to the sink (island-hopping via string containment), checks
that every content word of the original is consumed (entity spans, relation
cue phrases from the code tables plus a small extended evidence map, or
scaffolding/glue), emits the canonical nested-"of" form the composers already
accept ("What is the <cue> of ... of <START>?"), and VERIFIES it with the
unchanged composers (compose_n_hop on the canonical text returns exactly
(START, rels) with no compound-subject hit). Exactly one verified candidate
wins; anything uncertain returns the question UNCHANGED -- never a guess.

Plain software, no model, no downloads. Mac CPU, offline.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (cues, read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (composer, read-only)
import fable_loop113_agent as L113  # noqa: E402 (guard fn, read-only)

# Only multi-hop rewrites (1-2 hop turns keep the exact base path).
MIN_RELS = 3
MAX_WALK = 6

# Symmetric typo normalisation (raw MQuAKE spells "origianl" in teaches and in
# the code tables; questions spell "original"). Applied to both sides when
# matching spans to notebook subjects -- never emitted.
_TYPO = (("origianl", "original"),)


def _typonorm(s: str) -> str:
    s = str(s).lower()
    for a, b in _TYPO:
        s = s.replace(a, b)
    return s


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(s).lower())


# Canonical emitted cue per relation: MUST be a substring cue already in the
# code tables (asserted in selftest), so the unchanged composer re-parses it.
CANONICAL_CUE: dict[str, str] = {}
for _rel, _cues in B92.REL_CUES92.items():
    _pick = None
    for _c in _cues:
        if " " not in _c:
            _pick = _c
            break
    CANONICAL_CUE[_rel] = _pick or _cues[0]
# Prefer the most explicit multi-word cue where the single word is ambiguous.
_CANONICAL_OVERRIDE = {
    "country_of_citizenship": "country of citizenship",
    "country_of_origin": "country of origin",
    "official_language": "official language",
    "place_of_birth": "place of birth",
    "place_of_death": "place of death",
    "head_of_state": "head of state",
    "head_of_government": "head of government",
    "chief_executive_officer": "chief executive officer",
    "original_broadcaster": "broadcaster",
    "position_played_on_team_speciality": "position",
    "manufacturer": "producer",
    "founded_by": "founder",
    "creator": "creator",
    "officeholder": "officeholder",
    "employer": "employer",
    "notable_work": "notable work",
}
for _rel, _cue in _CANONICAL_OVERRIDE.items():
    if _rel in B92.REL_CUES92:
        assert any(_cue == c or _cue in c or c in _cue
                   for c in B92.REL_CUES92[_rel]), _rel
        CANONICAL_CUE[_rel] = _cue

# Extended EVIDENCE phrases per relation (recall-biased; used only to account
# for question words -- the emitted canonical text uses CANONICAL_CUE only, so
# looseness here can only cost a verification failure, never a wrong frame).
EXTRA_EVIDENCE: dict[str, list[str]] = {
    "officeholder": ["head coach", "prime minister", "director",
                     "original broadcaster", "broadcaster", "chairperson",
                     "head of", "coach", "manager"],
    "head_coach": ["head coach", "coach"],
    "country_of_citizenship": ["calls home", "is home to", "is home",
                               "home to", "home", "citizen", "country"],
    "country_of_origin": ["produced the work", "produced", "originated",
                          "gave birth", "houses", "house", "country"],
    "religion_or_worldview": ["faith", "adheres", "adhere", "religion"],
    "performer": ["performance", "performed", "performs"],
    "manufacturer": ["company that produced", "company that produce",
                     "produced", "producer"],
    "developer": ["company that developed", "company that develop",
                  "developed", "developer"],
    "employer": ["company that employs", "company employing", "employs"],
    "founded_by": ["person who founded", "founded", "founder"],
    "founder": ["founder", "found"],
    "spouse": ["person married to", "married to", "married", "husband/wife",
               "husband", "wife"],
    "notable_work": ["work", "known for", "famous"],
    "author": ["author", "wrote", "written"],
    "creator": ["creator", "created", "creat"],
    "continent": ["continent"],
    "capital": ["capital"],
    "official_language": ["language", "tongue", "spoken", "official"],
    "director_manager": ["director", "manager"],
    "sport": ["sport"],
    "child": ["child", "son", "daughter"],
    "occupation": ["field", "works in", "job", "profession"],
    "genre": ["genre", "music", "played"],
    "chairperson": ["chairperson", "chair"],
    "head_of_state": ["headed by", "head of state", "leader"],
    "educated_at": ["educated", "education", "studied"],
    "headquarters_location": ["headquarters", "located", "situated"],
    "place_of_birth": ["born", "birth"],
    "place_of_death": ["died", "death", "demise", "passed away"],
}

# Relation words usable as the "R" of an "R of ..." description step, mapped
# to the notebook relations they may evidence. Notebook-grounded: a step is
# taken only if the triple hop (or compound subject) with one of these
# relations actually exists.
RWORD_MAP: dict[str, set[str]] = {
    "director": {"director_manager", "officeholder"},
    "manager": {"director_manager", "officeholder"},
    "coach": {"officeholder", "head_coach"},
    "head coach": {"officeholder", "head_coach"},
    "head": {"officeholder"},
    "original broadcaster": {"officeholder", "original_broadcaster"},
    "broadcaster": {"officeholder", "original_broadcaster"},
    "prime minister": {"officeholder"},
    "minister": {"officeholder"},
    "chairperson": {"chairperson", "officeholder"},
    "chair": {"chairperson", "officeholder"},
    "performer": {"performer"},
    "performance": {"performer"},
    "entity that performed": {"performer"},
    "person who performed": {"performer"},
    "company that produced": {"manufacturer"},
    "company that developed": {"developer"},
    "company employing": {"employer"},
    "company that employs": {"employer"},
    "person who founded": {"founded_by", "founder"},
    "founder": {"founded_by", "founder"},
    "founded": {"founded_by"},
    "author": {"author"},
    "creator": {"creator"},
    "spouse": {"spouse"},
    "person married to": {"spouse"},
    "husband/wife": {"spouse"},
    "husband": {"spouse"},
    "wife": {"spouse"},
    "child": {"child"},
    "son": {"child"},
    "daughter": {"child"},
    "ceo": {"chief_executive_officer"},
    "chief executive officer": {"chief_executive_officer"},
    "citizen": {"country_of_citizenship"},
    "faith": {"religion_or_worldview"},
    "work": {"notable_work"},
    "capital": {"capital"},
    "continent": {"continent"},
    "country": {"country_of_citizenship", "country_of_origin"},
    "city": {"capital", "place_of_birth", "headquarters_location"},
    "language": {"official_language", "language_of_work_or_name"},
    "sport": {"sport"},
    "position": {"position_played_on_team_speciality"},
    "headquarters": {"headquarters_location"},
    "university": {"educated_at"},
    "employer": {"employer"},
    "officeholder": {"officeholder"},
}

# Tokens that never need accounting (interrogatives, copulas, articles,
# prepositions, relative scaffolding, generic verbs of the templates).
SCAFFOLD = frozenset({
    "what", "which", "where", "who", "whom", "whose", "when", "how",
    "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "by", "with",
    "from", "that", "which", "where", "who", "whom", "as", "it", "its",
    "and", "or", "but", "than", "then", "there", "here", "this", "these",
    "s", "location", "located", "situated", "associated", "connected",
    "s", "location", "located", "situated", "associated", "connected",
    "linked", "serves", "serve", "serving", "service", "housed",
    "entity", "person", "company", "faith", "home", "calls",
    "university", "team", "broadcaster", "director", "coach",
    "city", "cities", "town", "towns",
    "mentioned", "mention", "met", "named", "called",
    "he", "she", "they", "them", "their", "theirs", "his", "her", "hers",
    "him", "whoever", "houses", "house",
    "contains", "contain", "containing", "contained",
})


# Stopwords for compound-prefix matching (content words must be evidenced).
_STOP = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "by", "with",
    "from", "that", "which", "who", "as", "and", "or",
})


def _word_intervals(ql: str, phrase: str) -> list[tuple[int, int]]:
    """Occurrence intervals of a (possibly multi-word) phrase in ql."""
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        i = ql.find(phrase, start)
        if i < 0:
            return out
        out.append((i, i + len(phrase)))
        start = i + 1


def _content_spans(ql: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"[a-z0-9']+", ql):
        if m.group(0) not in SCAFFOLD:
            spans.append((m.start(), m.end()))
    return spans


def _covered(iv: tuple[int, int], cov: list[tuple[int, int]]) -> bool:
    return any(c[0] <= iv[0] and iv[1] <= c[1] for c in cov)


def _cues_for(rel: str) -> list[str]:
    cues = [c.lower() for c in B92.REL_CUES92.get(rel, [])]
    cues += [c.lower() for c in EXTRA_EVIDENCE.get(rel, [])]
    seen: set[str] = set()
    out: list[str] = []
    for c in cues:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _build_index(triples: list[tuple[str, str, str]]):
    out: dict[str, list[str]] = {}
    objs: dict[str, list[str]] = {}
    order: list[str] = []
    for s, r, o in triples:
        s, r, o = str(s), str(r), str(o)
        out.setdefault(s, []).append((r, o))
        objs.setdefault(o, []).append((s, r))
        if s not in order:
            order.append(s)
    return out, objs, order


def _uniq_out(out: dict, subj: str):
    return out.get(subj, [])


def _single_chain(out: dict, start: str, cap: int = MAX_WALK + 2):
    """Single-outgoing walk; (rels, end, ok) with loop guard."""
    rels: list[str] = []
    cur = start
    seen = {start}
    while len(rels) < cap:
        outs = _uniq_out(out, cur)
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) != 1:
            break
        r1 = uniq[0]
        nxt = [o for r, o in outs if r == r1][-1]
        if nxt in seen:
            return rels, cur, False
        seen.add(nxt)
        rels.append(r1)
        cur = nxt
    return rels, cur, True


def _split_of(subj: str) -> tuple[str, str] | None:
    low = str(subj).lower()
    idx = low.rfind(" of ")
    if idx < 0:
        return None
    return subj[:idx], subj[idx + 4:]


def _evidence_ok(question: str, rels: list[str]) -> bool:
    """Every walked hop has a cue phrase in the question (base + extra)."""
    ql = str(question).lower()
    for rel in rels:
        if not any(c in ql for c in _cues_for(rel)):
            return False
    return True


def _consumption_ok(question: str, rels: list[str],
                    spans: list[tuple[int, int]]) -> bool:
    """Every content word is inside an entity span, a walked-hop cue phrase,
    an island prefix span, or scaffolding (dropped before this check)."""
    ql = str(question).lower()
    cov = list(spans)
    for rel in rels:
        for cue in _cues_for(rel):
            cov.extend(_word_intervals(ql, cue))
    for tok in _tok(question):
        if tok in SCAFFOLD:
            cov.extend(_word_intervals(ql, tok))
    return all(_covered(iv, cov) for iv in _content_spans(ql))


def _span_of(ql: str, text: str) -> tuple[int, int] | None:
    i = ql.find(str(text).lower())
    if i < 0:
        return None
    return (i, i + len(str(text)))


def _decomp_span(ql: str, subject: str) -> tuple[int, int] | None:
    """Question span of a 'P of T' subject, allowing the origianl typo and a
    leading 'the': matches '<pre-words> of <target>' against the text."""
    parts = _split_of(subject)
    if parts is None:
        return None
    pre, tgt = parts
    pre_words = [t for t in _tok(pre) if t not in _STOP]
    if not pre_words:
        return None
    words = [(m.group(0), m.start(), m.end())
             for m in re.finditer(r"[a-z0-9']+", ql)]
    norm = [_typonorm(w) for w, _, _ in words]
    tn = _typonorm(tgt)
    tgt_words = _tok(tgt)
    first = _typonorm(tgt_words[0]) if tgt_words else tn
    for i, (w, s, e) in enumerate(words):
        if _typonorm(w) != first:
            continue
        # target may be multi-word: extend while it keeps matching
        if [_typonorm(x) for x in norm[i:i + len(tgt_words)]] != \
                [_typonorm(x) for x in tgt_words]:
            continue
        j = i - 1
        if j >= 0 and norm[j] == "of":
            j -= 1
        else:
            continue
        k = len(pre_words) - 1
        while j >= 0 and k >= 0 and norm[j] == _typonorm(pre_words[k]):
            j -= 1
            k -= 1
        if k < 0:
            start = words[j + 1][1]
            if j >= 0 and norm[j] == "the":
                start = words[j][1]
            return (start, words[i + len(tgt_words) - 1][2])
    return None


def _trial_start(question: str, triples, out: dict,
                 start: str) -> tuple[str, list[str]] | None:
    """Walk + island-hop from a seed subject; verified (canonical, guard)."""
    ql = str(question).lower()
    qtok = set(_tok(question))
    visited = {start}
    rels: list[str] = []
    cur = start
    spans: list[tuple[int, int]] = []
    sp = _span_of(ql, start)
    if sp is not None and _split_of(start) is not None:
        spans.append(sp)
    if sp is None:
        dsp = _decomp_span(ql, start)
        if dsp is not None:
            spans.append(dsp)
    # The unchanged composer cannot island-hop, so the canonical form starts
    # at the first island subject (when any island step is used) with the
    # hops from there; the seed-to-island resolution is evidence, not text.
    island_start: str | None = None
    island_rels: list[str] = []
    steps = 0
    while steps < MAX_WALK + 2:
        steps += 1
        outs = _uniq_out(out, cur)
        uniq = list(dict.fromkeys(r for r, _ in outs))
        if len(uniq) == 1:
            r1 = uniq[0]
            nxt = [o for r, o in outs if r == r1][-1]
            if nxt in visited:
                return None
            visited.add(nxt)
            rels.append(r1)
            island_rels.append(r1)
            cur = nxt
            continue
        if len(uniq) > 1:
            return None
        # Island step: exactly one notebook subject containing cur whose
        # prefix words are all evidenced in the question.
        cand = []
        for (s2, r2, _o2) in triples:
            s2 = str(s2)
            if s2 in visited or s2 == cur:
                continue
            if cur.lower() not in s2.lower():
                continue
            parts = _split_of(s2)
            if parts is None:
                continue
            pre, _tgt = parts
            pw = [t for t in _tok(pre) if t not in _STOP]
            if not pw:
                continue
            if all(w in qtok or _typonorm(w) in {_typonorm(t) for t in qtok}
                   for w in pw):
                cand.append(s2)
        if len(cand) != 1:
            break  # sink (or unresolvable gap: consumption/verify decides)
        s2 = cand[0]
        outs2 = _uniq_out(out, s2)
        uniq2 = list(dict.fromkeys(r for r, _ in outs2))
        if len(uniq2) != 1:
            return None
        r2 = uniq2[0]
        nxt2 = [o for r, o in outs2 if r == r2][-1]
        if nxt2 in visited:
            return None
        visited.add(s2)
        visited.add(nxt2)
        rels.append(r2)
        if island_start is None:
            island_start = s2
            island_rels = [r2]
        else:
            island_rels.append(r2)
        cur = nxt2
        sp2 = _span_of(ql, s2)
        if sp2 is not None:
            spans.append(sp2)
    if island_start is not None:
        full_rels = list(rels)
        start, rels = island_start, island_rels
    else:
        full_rels = list(rels)
    if len(rels) < MIN_RELS:
        return None
    # Full-consumption certainty on the ORIGINAL question.
    for _s, _r, _o in triples:
        for ent in (_s, _o):
            ent = str(ent)
            if len(ent) >= 4:
                sp = _span_of(ql, ent)
                # Only spans of walk nodes / resolved compounds count.
                if sp is not None and (ent in visited):
                    spans.append(sp)
    if not _evidence_ok(question, full_rels):
        return None
    if not _consumption_ok(question, full_rels, spans):
        return None
    canon = _canonical(start, rels)
    got = B92.compose_n_hop(canon, triples)
    if got is None or got[0] != start or list(got[1]) != list(rels):
        return None
    if L113.compound_subject_hit(triples, got[0], list(got[1])) is not None:
        return None
    return canon, list(rels)


def _seed_subjects(question: str, triples) -> list[str]:
    """Verbatim notebook subjects in the question (longest-match set)."""
    ql = str(question).lower()
    subs = sorted({str(s) for s, _, _ in triples}, key=len, reverse=True)
    spans: list[tuple[int, int, str]] = []
    for s in subs:
        sl = s.lower()
        start = 0
        while True:
            i = ql.find(sl, start)
            if i < 0:
                break
            spans.append((i, i + len(sl), s))
            start = i + 1
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


def _decomp_subjects(question: str, triples) -> list[str]:
    """Notebook 'P of T' subjects whose target T is in the question and whose
    prefix words (typo-normalised) are all in the question."""
    qtok = set(_tok(question))
    qn = {_typonorm(t) for t in qtok}
    ql = str(question).lower()
    out: list[str] = []
    for (s, _r, _o) in triples:
        s = str(s)
        parts = _split_of(s)
        if parts is None:
            continue
        pre, tgt = parts
        if tgt.lower() not in ql:
            continue
        pw = [t for t in _tok(pre) if t not in _STOP]
        if not pw:
            continue
        if all(_typonorm(w) in qn for w in pw):
            if s not in out:
                out.append(s)
    return out


def _canonical(start: str, rels: list[str]) -> str:
    chain = " of ".join(["the " + CANONICAL_CUE[r] for r in reversed(rels)])
    return f"What is {chain} of {start}?"


def rewrite_question(question: str, triples: list[tuple[str, str, str]]
                     ) -> tuple[str, dict]:
    """Rewrite or pass through unchanged. Never guesses.

    Returns (question_text, info) where info records the decision. Tries each
    seed subject (verbatim, then decomposed compounds); exactly one verified
    candidate wins, else the input is returned unchanged.
    """
    info: dict = {"fired": False}
    q = " ".join(str(question).split())
    if not q:
        return question, info
    triples = [(str(s), str(r), str(o)) for s, r, o in triples]
    out, _objs, _order = _build_index(triples)
    cands: list[tuple[str, list[str]]] = []
    tried: set[str] = set()
    for seed in _seed_subjects(q, triples) + _decomp_subjects(q, triples):
        if seed in tried:
            continue
        tried.add(seed)
        try:
            got = _trial_start(q, triples, out, seed)
        except Exception:
            got = None
        if got is not None and got[0] != q:
            cands.append(got)
    uniq = [c for i, c in enumerate(cands)
            if all(c[0] != d[0] for d in cands[:i])]
    if len(uniq) != 1:
        info["candidates"] = len(uniq)
        return question, info
    canon, rels = uniq[0]
    info.update({"fired": True, "start": None, "rels": rels,
                 "canonical": canon})
    return canon, info


def cmd_selftest(_args) -> int:
    fails: list[str] = []

    def check(cond: bool, tag: str) -> None:
        print(("ok  " if cond else "FAIL"), tag)
        if not cond:
            fails.append(tag)

    for rel, cue in CANONICAL_CUE.items():
        base = [c.lower() for c in B92.REL_CUES92.get(rel, [])]
        check(any(cue.lower() == c or cue.lower() in c or c in cue.lower()
                  for c in base), f"canon-cue-{rel}")
    # Tiny grammar fixtures (notebook-grounded, no external data).
    t1 = [("Ford Probe", "manufacturer", "Hon Hai"),
          ("Hon Hai", "founded_by", "Terry Gou"),
          ("Terry Gou", "country_of_citizenship", "Taiwan"),
          ("Taiwan", "capital", "Taipei")]
    q1 = ("What is the capital of the country that the founder of the "
          "company that produced Ford Probe calls home?")
    check(B92.compose_n_hop(q1, t1) is None, "fixture1-base-none")
    r1, i1 = rewrite_question(q1, t1)
    check(r1 != q1 and i1.get("fired"), "fixture1-rewrite-fires")
    check(B92.compose_n_hop(r1, t1) is not None, "fixture1-verify")
    t2 = [("Back Song", "performer", "The Ensemble"),
          ("director of The Ensemble", "officeholder", "Maestro"),
          ("Maestro", "country_of_citizenship", "Terra"),
          ("Terra", "continent", "Eurasia")]
    q2 = ("Which continent is the country in, where the director of the "
          "performer of Back Song is a citizen?")
    r2, i2 = rewrite_question(q2, t2)
    check(r2 != q2 and i2.get("fired"), "fixture2-island-fires")
    t3 = [("Happy Show", "performer", "Band"),
          ("origianl broadcaster of Happy Show", "officeholder", "Net"),
          ("director of Net", "officeholder", "Boss"),
          ("Boss", "country_of_citizenship", "Terra"),
          ("Terra", "capital", "Capitol City")]
    q3 = ("What city is the capital of the country where the director of "
          "the original broadcaster of Happy Show is a citizen?")
    r3, i3 = rewrite_question(q3, t3)
    check(r3 != q3 and i3.get("fired"), "fixture3-typo-island-fires")
    # Never-guess fixtures.
    r4, i4 = rewrite_question("Who is Mira's city?", [("Mira", "city", "Oslo")])
    check(r4 == "Who is Mira's city?" and not i4.get("fired"),
          "fixture4-short-passthrough")
    r5, i5 = rewrite_question("Blorpt zzz?", t1)
    check(r5 == "Blorpt zzz?" and not i5.get("fired"),
          "fixture5-garbled-passthrough")
    t6 = [("A", "performer", "B"), ("director of B", "officeholder", "C"),
          ("director of Bee", "officeholder", "Z"),
          ("C", "country_of_citizenship", "L"), ("L", "capital", "K")]
    q6 = ("What is the capital of the country whose citizen is the "
          "director of the performer of A?")
    r6, i6 = rewrite_question(q6, t6)
    check(r6 == q6 and not i6.get("fired"), "fixture6-ambiguous-passthrough")
    print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
    return 1 if fails else 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 132 question rewriter")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rewrite", default=None)
    args = ap.parse_args(argv)
    if args.selftest:
        return cmd_selftest(args)
    if args.rewrite is not None:
        print(rewrite_question(args.rewrite, [])[0])
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
