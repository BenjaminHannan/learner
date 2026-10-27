#!/usr/bin/env python3
"""Exp 142 -- port of exp-128's speed fix onto the loop134 lineage (not new science).

Loop134 = loop121 teach coverage (bench73 + bench92 EXTRA patterns + 121
value screen) over the loop113b N-hop question router + loop102 fallback, over
the loop96 guarded chain, with the three loop117 fixes as mixins. Exp-128's
index (scripts/fable_perf128_index.py) was built on loop102 and never indexed
the loop121/loop113b-specific paths. This file stacks 128's index on loop134
as mixins / runtime patches only -- no existing file is edited.

Unregistered profile of loop134 with 128's diag approach (diag.json in the
artifact dir) names every O(n)-per-turn scan with file:line. Shared with 128
(fixed here by REUSE of 128's classes, same file format, same decision logic):
  S1 fable_notebook_contract.py:244 current() full self.facts scan
     (assert_fact:296ff, ask:390/hop) -> IndexedContractNotebook.current
  S2 fable_listening_m1.py:61 _relation() full events scan per teach/correct
     -> _patch_relation (cached known-set)
  S5 fable_fix77_core.py:157 filtered_view77() full facts scan per ask hop;
     :244 known() same -> FastReasoner77 (per-subject index views + cached bit)
  S6 fable_agent_loop.py:262 _save() whole-experience dump 2x/turn
     (+ loop90_agent.py:334 advance_seal per save) -> tail-200 persist + seal
  S7 fable_loop102_agent.py:405/409 process_file set(facts)/set(entities)
     copies per turn -> count-sliced new ids
Loop121/loop113b-specific (indexed HERE, new in this file):
  T1 fable_loop90_agent.py:109 notebook_triples() full facts+active scan per
     hear (:133 every turn; :76/:182 on every "?" turn via loop113b/loop113)
     -> never built; composers read the incremental index instead
  T2 fable_bench92_english_arm.py:198 compose_n_hop() per "?" turn: ents build
     O(n) (:211), _entity_mentions92 O(E) finds (:145), per-step triple scans
     O(n.hops) (:222) -> _fast_compose_n_hop (bucket mentions + _sro walk)
  T3 fable_loop113_agent.py:109 _walk_nodes() + :123 compound_subject_hit()
     O(n) triple scans per "?" frame -> index-backed walk + subject scan
  T4 fable_bench73_english_arm.py:246 compose_question() MQuAKE section per
     "?" turn (ents build :258, mentions :293, walks :297/:302/:306) ->
     128's _index_compose (same frame, no triple list)
  T5 fable_loop90_agent.py:160 Bench73Stage._teach_action() linear facts scan
     per teach (reached twice on loop134: chain stage :146 AND
     loop121_agent.py:150 _bench73_action via stage.bind) ->
     _fast_teach_action142 (index read; stage tag loop121 preserved)
  T6 fable_loop102_agent.py:204 _resolve_forget_name() whole-entities prefix
     scan per forget turn -> LISTED, kept as-is (forget turns only; S1/S2
     shapes unaffected; identity risk exceeds the gain)
O(1) by inspection (no change): B73/B92 hear_teach regexes, is_hearsay,
strip_correction_prefix, strip_trailing_qualifier, screen_value_121,
GuardedEars screens, FakeEars/FakeMouth templates, nb.resolve (alias dict),
_thinking_tick (same thinker 128 left untouched), _relation_mentions cues.

Byte-identity argument: every fast path reads the same logical data through
the incremental index and returns the same frame/action/reply; doubtful
shapes (_needs_full_question) delegate to the original loop134 code. S2
(5000/5000 replies) + S3/S4 verdict identity check this empirically.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_agent_loop as A  # noqa: E402 (read-only)
import fable_bench73_english_arm as B73  # noqa: E402 (read-only)
import fable_bench92_english_arm as B92  # noqa: E402 (read-only)
import fable_fix77_core as F77  # noqa: E402 (read-only)
import fable_loop102_agent as L102  # noqa: E402 (read-only)
import fable_loop113_agent as L113  # noqa: E402 (read-only)
import fable_loop134_agent as L134  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (read-only)

# 128's index pieces, reused verbatim (same log format, same decision logic).
from fable_perf128_index import (  # noqa: E402
    ANS,
    FastReasoner77,
    IndexedLoopNotebook,
    _bucketed_mentions,
    _index_compose,
    _needs_full_question,
    _patch_relation,
    _show,
    patch_bench73_stage,
)


class FastReasoner142(FastReasoner77):
    """FastReasoner77 + the empty-subject guard 128 never needed.

    128's _entry_for indexes facts[0] unguarded: on a drop-cache HIT for a
    (relation, subject) pair with no surviving rows (e.g. rt81 M_hops-06:
    asking Ana's city when only her mother-link is taught, with the city's
    drop bit cached from an earlier turn at the same notebook version), the
    original filtered_view77 simply has no entry for that subject and the
    hop returns None (-> MISSING_FACT). Return None here too: same verdict,
    same reply, no scan. S2 shapes never hit this (no repeated-relation
    missing-subject hop at a cached version); S3's multi-hop suites do.
    """

    def _entry_for(self, nb, inner, subject: str, rel: str, req: dict):
        rows = []
        for fid in inner._sr.get((subject, rel), ()):
            fact = inner.facts[fid]
            if fact["source"] not in ANS or not inner.active(fid):
                continue
            thought = F77.thought_of77(fact)
            quals = thought.qualifiers if thought is not None else ()
            if quals and not F77.qualifiers_match77(quals, req):
                continue
            rows.append((fact, bool(quals)))
        if not rows:
            return None
        return super()._entry_for(nb, inner, subject, rel, req)


def _fast_teach_action142(nb, triple: tuple) -> dict:
    """Loop121's _bench73_action over the index (stage tag loop121 kept)."""
    subj, rel, obj = triple
    act = "teach"
    found = nb.resolve(subj)
    if found.status == C.OK:
        eid = found.detail["entity_id"]
        from fable_thought49_notebook import ThoughtNotebook
        inner = nb.nb if isinstance(nb, ThoughtNotebook) else nb
        for fid in inner._sr.get((eid, rel), ()):
            fact = inner.facts[fid]
            if (fact.get("source") == "taught"
                    and inner.active(fact["fact_id"])):
                if _show(inner.entities, fact["value"]) != obj:
                    act = "correct"
                break
    return {"act": act, "name": subj, "relation": rel, "value": obj,
            "is_person": True, "structured": True, "stage": "loop121"}


def _mention_spans(inner, ql: str) -> list[tuple]:
    """All (start, end, name) mention spans over the index set, scanned ONCE.

    The name set equals notebook_triples' ents set (subjects + active taught
    displays); iteration order is irrelevant (both consumers sort spans).
    Length-bucketed iteration keeps the single scan cheap.
    """
    spans: list[tuple] = []
    for ln in sorted(inner._ment_bkt.keys(), reverse=True):
        for s in inner._ment_bkt[ln]:
            el = s.lower()
            start = 0
            while True:
                i = ql.find(el, start)
                if i < 0:
                    break
                spans.append((i, i + len(el), s))
                start = i + 1
    return spans


def _spans92(spans: list[tuple]) -> list[str]:
    """B92._entity_mentions92 longest-first filter over shared spans."""
    ordered = sorted(spans, key=lambda t: (-(t[1] - t[0]), t[0]))
    kept: list[tuple] = []
    for s, t, e in ordered:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def _spans73(spans: list[tuple]) -> list[str]:
    """B73 longest-match filter over shared spans (== _bucketed_mentions tail)."""
    ordered = sorted(spans)
    kept: list[tuple] = []
    for s, t, e in ordered:
        if not any(s >= ks and t <= kt for ks, kt, _ in kept):
            kept.append((s, t, e))
    seen: list[str] = []
    for _, _, e in kept:
        if e not in seen:
            seen.append(e)
    return seen


def _mentions92(inner, question: str) -> list[str]:
    """B92._entity_mentions92 over the index's mention set (same set, same result).

    notebook_triples' ents (subjects + displays, active taught only) equal the
    index mention set by construction (incremental add/replace/drop on every
    FACT/RETRACT event); set() + longest-first containment logic is order-free.
    """
    return _spans92(_mention_spans(inner, question.lower()))


def _fast_compose_n_hop(inner, text: str, spans=None):
    """B92.compose_n_hop over the index (same frame, no triple list)."""
    q = " ".join(str(text).split())
    if not q:
        return None
    ment = _spans92(spans) if spans is not None else _mentions92(inner, q)
    if len(ment) != 1:
        return None
    start = ment[0]
    rels: list[str] = []
    cur = start
    seen_objs: set[str] = set()
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
    if not rels:
        return None
    mentioned = B92._relation_mentions92(q)
    if any(r not in mentioned for r in rels):
        return None
    return (start, rels)


def _fast_walk_nodes(inner, start: str, rels: list[str]):
    """L113._walk_nodes over the index (same nodes + end)."""
    nodes = {" ".join(str(start).split()).lower()}
    cur = start
    for rel in rels:
        objs = inner._sro.get((cur, rel), [])
        if not objs:
            return nodes, None
        cur = objs[-1]
        nodes.add(" ".join(str(cur).split()).lower())
    return nodes, cur


def _fast_compound_hit(inner, start: str, rels: list[str]):
    """L113.compound_subject_hit over the index (only None-ness is consumed)."""
    nodes, end = _fast_walk_nodes(inner, start, rels)
    if end is None:
        return None
    el = " ".join(str(end).split()).lower()
    for sname in inner._srel.keys():
        sl = " ".join(str(sname).split()).lower()
        if sl != el and sl not in nodes and el in sl:
            r0 = inner._srel[sname][0]
            return (sname, r0, inner._sro[(sname, r0)][0])
    return None


def _index_compose_spans(inner, text: str, spans) -> tuple | None:
    """128's _index_compose over shared spans (same frame, scan done once)."""
    mentioned = B73._relation_mentions(text)
    if not (mentioned & set(inner._rel.keys())):
        return None
    ment = _spans73(spans)
    if len(ment) != 1:
        return None
    start = ment[0]
    r1s = list(inner._srel.get(start, ()))
    if len(r1s) != 1:
        return None
    r1 = r1s[0]
    objs = list(inner._sro.get((start, r1), ()))
    if not objs:
        return None
    mid = objs[-1]
    r2s = [r for r in inner._srel.get(mid, ()) if r != r1]
    if len(r2s) != 1:
        return None
    r2 = r2s[0]
    if r1 not in mentioned or r2 not in mentioned:
        return None
    return (start, [r1, r2])


def _nb_version(nb) -> int:
    try:
        return len(nb.events)
    except (AttributeError, TypeError):
        return -1


def _find_chain(ears):
    """ChainEars object under the ears wrappers (via __dict__, no delegation)."""
    o = ears
    for _ in range(6):
        d = getattr(o, "__dict__", {})
        if isinstance(d.get("stages"), list):
            return o
        nxt = d.get("inner")
        if nxt is None:
            return None
        o = nxt
    return None


def _hint_stages(ears, text: str, version: int, frame2) -> None:
    """Publish this turn's 2-hop compose result to chain Bench73 stages."""
    chain = _find_chain(ears)
    if chain is None:
        return
    for stage in chain.__dict__.get("stages", []):
        if getattr(stage, "name", "") == "bench73":
            stage._c142_hint = (text, version, frame2)


def wrap_bench73_hint(stage) -> None:
    """Skip the fallback Bench73 recompose when this turn's hint covers it.

    The mixin already computed _index_compose for this exact text over this
    exact notebook version; same query + same state => same (None) frame, so
    the wrapper only runs the O(1) teach-template check. Anything else takes
    the original patched path.
    """
    orig_hear = stage.hear

    def hear(turn: str, tau: dict):
        text = " ".join(str(turn).split())
        hint = getattr(stage, "_c142_hint", None)
        if (hint is not None and hint[0] == text
                and hint[1] == _nb_version(getattr(stage, "nb", None))
                and hint[2] is None and text.rstrip().endswith("?")):
            triple = B73.hear_teach_template(text)
            if triple is not None:
                return ([stage._teach_action(triple)], 1.0)
            return None
        return orig_hear(turn, tau)

    stage.hear = hear


def _inner_nb(nb):
    from fable_thought49_notebook import ThoughtNotebook
    return nb.nb if isinstance(nb, ThoughtNotebook) else nb


class FastQuestionMixin142:
    """Index-backed "?" routing; non-"?" turns use the loop134 path untouched.

    Mirrors Loop113bEars.hear: F1 hearsay -> N-hop frame (+compound guard) ->
    2-hop explicit / non-explicit -> Loop102 fallback chain. Doubtful shapes
    (_needs_full_question: never-taught / Who-reverse probes) delegate to the
    original loop134 code, as does a missing notebook binding. Mention spans
    are scanned once per "?" turn and shared by both composers; the fallback
    chain's recompose is skipped via the per-turn hint.
    """

    def hear(self, turn: str) -> list[dict]:
        text = " ".join(str(turn).split())
        if not text or not text.rstrip().endswith("?"):
            return super().hear(turn)
        if L102.is_hearsay(text):
            self.last_stage, self.last_score = "loop113b-hearsay", 1.0
            return [{"act": "clarify", "text": L102.HEARSAY_MSG}]
        if self.nb is None:
            return super().hear(turn)
        if _needs_full_question(text):
            return super().hear(turn)
        inner = _inner_nb(self.nb)
        spans = _mention_spans(inner, text.lower())
        frame = _fast_compose_n_hop(inner, text, spans)
        if frame is not None:
            hit = _fast_compound_hit(inner, frame[0], list(frame[1]))
            if hit is None:
                self.last_stage, self.last_score = "loop113b-nhop", 1.0
                return [{"act": "ask", "name": frame[0],
                         "relations": list(frame[1]), "stage": "loop113b"}]
            self.last_stage, self.last_score = ("loop113b-compound-guard", 1.0)
            return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
        frame2 = _index_compose_spans(inner, text, spans)
        if frame2 is not None:
            if L113.is_explicit_question(text):
                self.last_stage, self.last_score = ("loop113b-explicit", 1.0)
                return [{"act": "ask", "name": frame2[0],
                         "relations": list(frame2[1]), "stage": "loop113b"}]
            self.last_stage, self.last_score = ("loop113b-nonexplicit", 1.0)
            return [{"act": "clarify", "text": L113.CHAIN_MISS_TEXT}]
        _hint_stages(self, text, _nb_version(self.nb), frame2)
        return L102.Loop102Ears.hear(self, turn)


def patch_loop121_teach(ears) -> None:
    """Loop121Ears._bench73_action via the index (same action, no facts scan)."""

    def fast_bench73_action(triple: tuple) -> dict:
        action = _fast_teach_action142(ears.nb, triple)
        return action

    ears._bench73_action = fast_bench73_action


def patch_chain142(chain) -> None:
    """Bench73Stage instances: 128's index-backed patch + the 142 hint skip."""
    for stage in getattr(chain, "stages", []):
        if getattr(stage, "name", "") == "bench73":
            patch_bench73_stage(stage)
            wrap_bench73_hint(stage)
