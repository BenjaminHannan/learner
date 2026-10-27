"""Exp 246 fix (cause A of diagnosis 243): mention-guided walk fallback.

B92.compose_n_hop (scripts/fable_bench92_english_arm.py:198) walks the
single-outgoing-relation chain to its END and stops at once when the start
entity has 2+ kinds of fact. It is the only reader of "Who is X married
to?" / "What country is X a citizen of?", so those questions decline as
soon as X (or X's spouse) has another fact.

MentionWalk246Mixin overrides Loop138Ears._hear_question ONLY for turns
where compose_n_hop returns None AND the unchanged base branch ends in a
not-understood miss (every action a clarify containing "didn't
understand"). Everything the base claims is returned untouched.

The walk (mention_walk246):
  1. exactly one notebook entity is mentioned (word-bounded, longest
     span first; no "whose");
  2. from it, follow the ONE outgoing relation the question mentions
     (relation cues = B92.REL_CUES92, as the base uses); stop when the
     current entity has no mentioned outgoing relation; 2+ candidates,
     a repeated relation, a loop or a middle hop with 2+ values -> None;
     the walk must end after exactly ONE hop (a longer walk -> None, as
     rt143 S1 requires for star-shaped starts), and a fact pointing from
     the end back to the start (a 2-cycle, rt143 S5) -> None;
  3. every mentioned relation must be used: each of its cue hits (minus
     113c's scaffolding cues) must overlap a used relation's cue hit, and
     each used relation is hit in exactly one place (one hop per phrase);
  4. safety checks (new, all decline-direction):
     - agent relations (employer, founded_by, author, ...) need the cue
       BEFORE the entity with no "by" between ("Who employs X?"), so
       "Who does X employ?" / "Who is employed by X?" never give X's
       employer;
     - "where" questions must end on a place relation; "who" questions
       must not end on one;
     - "X the R of?" (inverse) shapes decline;
     - every leftover word (not entity, not a used cue, not scaffolding)
       must be a small function word, so "Who does X work with?" or an
       unknown second name declines;
  5. then the existing 113c frame_consumes_question gate and the 113
     compound_subject_hit guard, exactly as the base n-hop branch.
The accepted frame becomes the same "ask" action the base n-hop branch
emits. Question turns never write (ask actions only).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench92_english_arm as B92  # noqa: E402 (read-only)
import fable_loop102_agent as L102  # noqa: E402 (read-only)
import fable_loop113_agent as L113  # noqa: E402 (read-only)
import fable_loop113c_agent as L113C  # noqa: E402 (read-only)
import fable_loop138_agent as L138  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

STAGE246 = "loop246-mentionwalk"

AGENT_RELS246 = frozenset({
    "employer", "founded_by", "founder", "creator", "developer",
    "manufacturer", "author", "performer", "director_manager", "head_coach",
    "chairperson", "chief_executive_officer", "head_of_government",
    "head_of_state", "original_broadcaster", "officeholder"})

PLACE_RELS246 = frozenset({
    "city", "place_of_birth", "place_of_death", "work_location",
    "location_of_formation", "headquarters_location", "country_of_origin",
    "country_of_citizenship", "capital", "continent"})

FUNC246 = frozenset({
    "who", "whom", "what", "which", "where", "when", "is", "was", "are",
    "were", "does", "did", "do", "the", "a", "an", "of", "to", "in", "at",
    "on", "please", "hi", "hello", "hey", "can", "could", "would", "will",
    "you", "tell", "me", "now", "know", "remind", "again", "country",
    "city", "place", "person", "oh", "ok", "okay", "so", "and", "s"})

_TOK = re.compile(r"[a-z0-9]+")


def _wb_spans(q: str, needle: str) -> list[tuple[int, int]]:
    """Word-bounded occurrences of needle in q (both lowercased)."""
    out = []
    rx = re.compile(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])")
    for m in rx.finditer(q):
        out.append((m.start(), m.end()))
    return out


def entity_mentions246(q: str, entities) -> list[tuple[str, int, int]]:
    """Word-bounded, longest-first entity spans (a kept span blocks any
    span it contains). Returns (entity, start, end) per kept span."""
    spans = []
    for e in sorted(set(entities), key=len, reverse=True):
        el = " ".join(str(e).split()).lower()
        if not el:
            continue
        for s, t in _wb_spans(q, el):
            spans.append((s, t, e))
    spans.sort(key=lambda x: (-(x[1] - x[0]), x[0]))
    kept: list[tuple[int, int, str]] = []
    for s, t, e in spans:
        if not any(s < kt and t > ks for ks, kt, _ in kept):
            kept.append((s, t, e))
    return [(e, s, t) for s, t, e in kept]


def cue_hits246(q: str) -> dict[str, list[tuple[int, int, str]]]:
    """relation -> list of (start, end, cue) substring hits (B92 rule)."""
    hits: dict[str, list[tuple[int, int, str]]] = {}
    for rel, cues in B92.REL_CUES92.items():
        for cue in cues:
            c = cue.lower()
            if not c:
                continue
            i = q.find(c)
            while i >= 0:
                hits.setdefault(rel, []).append((i, i + len(c), c))
                i = q.find(c, i + 1)
    return hits


def _clusters(spans) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for s, t, _ in sorted(spans):
        if out and s < out[-1][1]:
            out[-1][1] = max(out[-1][1], t)
        else:
            out.append([s, t])
    return [(a, b) for a, b in out]


def _overlaps(a, b) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def mention_walk246(question: str, triples) -> tuple[str, list[str]] | None:
    """The fix-A walk. Returns (start, relations) or None (decline)."""
    q = " ".join(str(question).split()).lower()
    if not q or re.search(r"(?<![a-z])whose(?![a-z])", q):
        return None
    ents = []
    for s, _, o in triples:
        ents.extend([s, o])
    ment = entity_mentions246(q, ents)
    if len({e for e, _, _ in ment}) != 1:
        return None
    start, es, et = ment[0]
    ent_spans = [(s, t) for _, s, t in ment]
    hits = cue_hits246(q)
    # cue hits inside an entity name are not relation phrases
    hits = {r: [h for h in hs if not any(_overlaps(h, sp) for sp in ent_spans)]
            for r, hs in hits.items()}
    hits = {r: hs for r, hs in hits.items() if hs}
    mentioned = set(hits)
    rels: list[str] = []
    cur = start
    seen = {start}
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        cand = list(dict.fromkeys(r for r, _ in outs
                                  if r in mentioned and r not in rels))
        if not cand:
            break
        if len(cand) != 1:
            return None
        r1 = cand[0]
        objs = list(dict.fromkeys(o for (r, o) in outs if r == r1))
        rels.append(r1)
        if len(objs) != 1:
            # a middle hop must be single-valued; the last hop may be multi
            nxt_mentioned = any(s2 in objs and r2 in mentioned
                                and r2 not in rels
                                for (s2, r2, _) in triples)
            if nxt_mentioned:
                return None
            break
        mid = objs[0]
        if mid in seen:
            return None
        seen.add(mid)
        cur = mid
        if len(rels) > 6:
            return None
    if len(rels) != 1:
        # one hop only: rt143 S1 fixes that a multi-hop walk starting from
        # (or passing) a node with 2+ kinds of fact must abstain; pure
        # chains stay with compose_n_hop.
        return None
    end_objs = {o for (s, r, o) in triples if s == start and r == rels[0]}
    if any(s in end_objs and o == start for (s, _, o) in triples):
        # 2-cycle back to the start (rt143 S5): abstain like compose_n_hop
        return None
    used_spans = [h for r in rels for h in hits[r]]
    # every mentioned relation used or explained by a used cue hit
    for rel, hs in hits.items():
        if rel in rels:
            continue
        for h in hs:
            if h[2] in L113C._DROP_CUES:
                continue
            if not any(_overlaps(h, u) for u in used_spans):
                return None
    # one hop per phrase: each used relation hit in exactly one place
    for r in rels:
        non_drop = [h for h in hits[r] if h[2] not in L113C._DROP_CUES]
        if len(_clusters(non_drop or hits[r])) != 1:
            return None
    # agent relations: cue before the entity, no "by" in between
    for r in rels:
        if r not in AGENT_RELS246:
            continue
        for s, t, _ in hits[r]:
            if s >= es:
                return None
            if re.search(r"(?<![a-z])by(?![a-z])", q[t:es]):
                return None
    # wh-word vs answer kind
    first = _TOK.findall(q)
    wh = next((w for w in first if w in ("who", "whom", "where", "what",
                                         "which")), None)
    if wh == "where" and rels[-1] not in PLACE_RELS246:
        return None
    if wh in ("who", "whom") and rels[-1] in PLACE_RELS246:
        return None
    # inverse "X the R of?" shape
    if re.search(r"^\s*(the|a|an)\s+[a-z ]+\s+of\s*\?*\s*$", q[et:]) and \
            not re.search(r"\bcitizen\b", q[et:]):
        return None
    # leftover words must be function words
    mask = [False] * len(q)
    for s, t in ent_spans:
        for i in range(s, t):
            mask[i] = True
    for rel, hs in hits.items():
        for s, t, c in hs:
            if rel in rels or c in L113C._DROP_CUES:
                for i in range(s, t):
                    mask[i] = True
    for m in _TOK.finditer(q):
        if any(mask[m.start():m.end()]):
            continue
        if m.group(0) not in FUNC246:
            return None
    return (start, rels)


def base_missed246(actions) -> bool:
    if not actions:
        return True
    for a in actions:
        if a.get("act") != "clarify":
            return False
        if L138.NOT_UNDERSTOOD not in str(a.get("text", "")):
            return False
    return True


class MentionWalk246Mixin:
    """Fallback over Loop138Ears._hear_question (see module doc)."""

    def _hear_question(self, text: str, turn: str) -> list[dict]:
        base = super()._hear_question(text, turn)
        if self.nb is None or L102.is_hearsay(text):
            return base
        if not base_missed246(base):
            return base
        triples = L90.notebook_triples(self.nb)
        if B92.compose_n_hop(text, triples) is not None:
            return base
        frame = mention_walk246(text, triples)
        if frame is None:
            return base
        rels = list(frame[1])
        if not L113C.frame_consumes_question(text, rels, triples):
            return base
        if L113.compound_subject_hit(triples, frame[0], rels) is not None:
            return base
        self.last_stage, self.last_score = STAGE246, 1.0
        return [{"act": "ask", "name": frame[0], "relations": rels,
                 "stage": "loop138"}]
