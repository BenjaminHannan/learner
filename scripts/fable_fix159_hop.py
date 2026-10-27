#!/usr/bin/env python3
"""Experiment 159 -- THE ONE CHANGE: hop through known names mid-chain.

Base: loop150 (scripts/fable_loop150_agent.py: loop129b + 139b value guard +
150 subject guard; reasoner QualifierAwareReasoner77 from
scripts/fable_fix77_core.py, imported read-only, never edited).

The exp-152 red team (class N9) found: after "Biscuit's color is brown." and
"Ana's pet is Biscuit.", "Who is Ana's pet's color?" replies "Ana's pet is
Biscuit, which is not someone I can look up." The walk stops at the literal
mid-value "Biscuit" even though Biscuit heads live taught facts. Same for
152 turn 26 "Who is Biscuit's owner's pet?" (judged OK by mistake).

THE RULE (the only behaviour delta, inside the reasoner's hop loop): when
the walk stands on a mid-chain LITERAL value, the walk CONTINUES from the
matching entity iff the literal exactly equals -- after the loop's own name
normalisation (C._norm: lowercase, collapse whitespace,
fable_notebook_contract.py:116-117) -- the display name of EXACTLY ONE
entity that heads at least one LIVE taught fact (source == "taught" and
nb.active); otherwise the old BROKEN_CHAIN reply is returned byte-identical.
Zero matches, alias-only matches, or ambiguous (two entities, one name)
matches all keep the old reply, so no new wrong answer can be produced: a
continued walk can only land on taught values.

Stackable: Hop159Reasoner77 subclasses QualifierAwareReasoner77 and
overrides answer() with the parent's hop loop verbatim except the two
``kind != "entity"`` branches (hop-top and in-option), which now try the
bridge first. Teaches, corrections, forgets, qualifiers, learned-word
stages, multi-value answers, conf threshold, and final-literal answers are
untouched (line-identical execution whenever the walk never stands on a
mid-chain literal). No existing file is edited.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (statuses + _norm, read-only)
import fable_fix77_core as F77  # noqa: E402 (parent reasoner, read-only)
import fable_qual56_reasoner as Q56  # noqa: E402 (hop_requirements, read-only)

ANS = F77.ANS
ANS_IDX = F77.ANS_IDX
ANSWER_THRESHOLD = F77.ANSWER_THRESHOLD
MAX_HOPS = F77.MAX_HOPS


def _norm159(text: str) -> str:
    """The loop's own name normalisation (identical to C._norm)."""
    return " ".join(str(text).strip().lower().split())


def live_taught_subjects159(nb) -> dict[str, list[str]]:
    """Normalised display name -> entity ids heading a LIVE taught fact."""
    out: dict[str, list[str]] = {}
    for fid, fact in nb.facts.items():
        if fact.get("source") != "taught" or not nb.active(fid):
            continue
        subj = fact.get("subject")
        name = nb.entities.get(subj)
        if name is None:
            continue
        bucket = out.setdefault(_norm159(name), [])
        if subj not in bucket:
            bucket.append(subj)
    return out


def bridge159(nb, lit_text: str) -> str | None:
    """Mid-chain literal -> entity id, or None (keep the old reply).

    Exactly one live-taught-subject match continues the walk; zero,
    alias-only, or ambiguous matches return None.
    """
    eids = live_taught_subjects159(nb).get(_norm159(lit_text), [])
    return eids[0] if len(eids) == 1 else None


class Hop159Reasoner77(F77.QualifierAwareReasoner77):
    """QualifierAwareReasoner77 + the exp-159 hop-through-known-names bridge.

    answer() is the parent's hop loop verbatim except the two
    ``kind != "entity"`` branches, which bridge a mid-chain literal to its
    uniquely-matching live taught subject instead of breaking.
    """

    def answer(self, question: dict, notebook) -> dict:
        nb = notebook
        self._sync(nb)
        name = question.get("name", "")
        relations = list(question.get("relations") or [])
        eid = question.get("entity_id")

        def rec(status: str, fields: dict) -> dict:
            return {"kind": "answer", "status": status, "name": name,
                    "relations": relations, "fields": fields}

        if not relations or len(relations) > MAX_HOPS:
            return rec(C.BAD_REQUEST, {"reason": f"need 1-{MAX_HOPS} hops"})
        try:
            hop_req = Q56.hop_requirements(relations, question.get("qualifiers"))
        except Q56.BadQualifiers:
            return rec(C.BAD_REQUEST, {
                "reason": "qualifiers must be None, a dict, or a list parallel to relations"})

        if eid is None:
            found = nb.resolve(name)
            if found.status != C.OK:
                return rec(found.status, dict(found.detail))
            eid = found.detail["entity_id"]
        elif eid not in nb.entities:
            return rec(C.BAD_REQUEST, {"reason": "unknown entity id"})

        views: dict[tuple, tuple] = {}

        def view_at(hop: int, rel: str):
            key = (hop, rel)
            if key not in views:
                views[key] = F77.filtered_view77(nb, rel, hop_req[hop])
            return views[key]

        def known(rel: str) -> bool:
            for fid, fact in nb.facts.items():
                if fact["relation"] == rel:
                    return True
            return rel in nb.functional

        def stages(tok: str, hop: int):
            if tok in self.words:
                return self.stage_options(self.words[tok])
            if known(tok):
                return [("skill", tok, 1.0)]
            return None

        def bridge_or_none():
            """THE ONE CHANGE: continue iff the literal names one live subject."""
            return bridge159(nb, lit_text)

        trail: list[int] = []
        trail_src: list[int] = []
        subject = eid
        kind = "entity"
        lit_text = lit_producer = None
        conf = 1.0

        def fields_missing(hop: int, rel: str, qualified: bool) -> dict:
            detail = {"subject": nb.entities[subject], "relation": rel,
                      "hop": hop, "trail": [F77.fid_str77(n) for n in trail]}
            if qualified:
                detail["reason"] = "qualified"
            return detail

        def fields_broken(hop: int) -> dict:
            return {"subject": nb.entities[subject], "relation": lit_producer,
                    "value": lit_text, "hop": hop,
                    "trail": [F77.fid_str77(n) for n in trail]}

        for hop, tok in enumerate(relations):
            if kind != "entity":
                bridged = bridge_or_none()
                if bridged is None:
                    return rec(C.BROKEN_CHAIN, fields_broken(hop))
                subject, kind = bridged, "entity"
                lit_text = lit_producer = None
            stage_list = stages(tok, hop)
            if stage_list is None:
                return rec(C.MISSING_FACT, fields_missing(hop + 1, tok, False))
            for opt, arg, weight in stage_list:
                if kind != "entity":
                    bridged = bridge_or_none()
                    if bridged is None:
                        return rec(C.BROKEN_CHAIN, fields_broken(hop))
                    subject, kind = bridged, "entity"
                    lit_text = lit_producer = None
                if opt == "keep":
                    continue
                conf *= weight
                out, dropped = view_at(hop, arg)
                entry = out.get(subject)
                if entry is None:
                    return rec(C.MISSING_FACT, fields_missing(hop + 1, arg, dropped))
                tag = entry[0]
                if tag == "M":
                    shows, src = entry[1], entry[2]
                    return rec(C.OK, {"answer": ", ".join(s for s, _ in shows),
                                      "trail": [F77.fid_str77(n) for n in trail]
                                      + [F77.fid_str77(n) for _, n in shows],
                                      "source": ANS[src], "multi": True})
                trail.append(entry[2])
                trail_src.append(entry[3])
                if tag == "L":
                    kind, lit_text, lit_producer = "literal", entry[1], arg
                else:
                    subject = entry[1]

        if kind != "entity":
            return rec(C.OK, {"answer": lit_text,
                              "trail": [F77.fid_str77(n) for n in trail],
                              "source": ANS[trail_src[-1]]})
        if conf < ANSWER_THRESHOLD:
            return rec(C.MISSING_FACT,
                       fields_missing(len(relations), relations[-1], False))
        return rec(C.OK, {"answer": nb.entities[subject],
                          "trail": [F77.fid_str77(n) for n in trail],
                          "source": ANS[trail_src[-1]]})
