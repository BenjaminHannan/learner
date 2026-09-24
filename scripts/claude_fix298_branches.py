#!/usr/bin/env python3
"""rsn-298: a middle hop with several values follows every branch.

Bug (nb-320, 118/2000 two-hop probes; reproduced on 292 2026-09-24): when a NON-final hop of a
chain question has several values ("Ana's friend" = Bo, Cy), the reasoner returns the hop-1
list as the answer to the whole question ("Where does Ana's friend live?" -> "Cy, Bo"), and
154b's mouth then asks "Which one do you mean?", which the ears cannot take an answer to.

298 (one change): wrap the agent's reasoner. When a chain question stops at a multi-valued
middle hop, ask the rest of the chain for each value (oldest first), up to MAX_BRANCHES:
  - every branch gives the same answer          -> that answer ("Oslo")
  - branches differ                             -> "Oslo for Bo and Rome for Cy"
  - some branches unknown                       -> "Oslo for Bo (I don't know it for Cy)"
  - every branch unknown                        -> MISSING_FACT for "Bo or Cy"
  - more than MAX_BRANCHES values -> unchanged (292 asks "Which one do you mean?").
A value stored as a plain name (a literal) is asked about by name, the way 292 already resolves
single-valued chains.
Single-hop questions, single-valued chains and every other record pass through untouched.
Everything is read from the notebook; nothing is written.

  build_agent298(cfg) = build_agent292(cfg) + install298
  install298(loop)    = wraps loop.reasoner in place (works for any 292-lineage loop, e.g. 292t)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_notebook_contract as C  # noqa: E402

MAX_BRANCHES = 4


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _entity_by_name(notebook, name):
    if not name:
        return None
    hits = [e for e, n in notebook.entities.items() if str(n).casefold() == str(name).casefold()]
    return hits[0] if len(hits) == 1 else None


class Reasoner298:
    def __init__(self, inner):
        self.inner = inner

    def __getattr__(self, item):                      # sleep hooks etc. reach the inner reasoner
        if item == "inner":
            raise AttributeError(item)
        return getattr(self.inner, item)

    def answer(self, question: dict, notebook) -> dict:
        rec = self.inner.answer(question, notebook)
        rels = list(question.get("relations") or [])
        f = rec.get("fields") or {}
        if not (rec.get("status") == C.OK and f.get("multi") and len(rels) > 1):
            return rec
        # which hop stopped?  the shortest prefix that already comes back multi
        hop = None
        for i in range(1, len(rels)):
            pre = self.inner.answer(dict(question, relations=rels[:i]), notebook)
            pf = pre.get("fields") or {}
            if pre.get("status") == C.OK and pf.get("multi"):
                hop, pre_rec = i, pre
                break
        if hop is None:                                  # the multi hop IS the last hop
            return rec
        trail = (pre_rec.get("fields") or {}).get("trail") or []
        facts = [x for x in (notebook.facts.get(fid) for fid in trail) if x]
        # the multi hop's facts all share one subject: the person the single-valued hops before it reached
        if hop == 1:
            subj = facts[0].get("subject") if facts else None
            if any(x.get("relation") == rels[0] and x.get("subject") != subj for x in facts):
                return rec
        else:
            head = self.inner.answer(dict(question, relations=rels[:hop - 1]), notebook)
            ht = (head.get("fields") or {}).get("trail") or []
            last = notebook.facts.get(ht[-1]) if ht else None
            hv = (last or {}).get("value") or {}
            subj = hv.get("entity") or _entity_by_name(notebook, hv.get("literal"))
        vals = [x for x in facts if x.get("relation") == rels[hop - 1] and x.get("subject") == subj]
        vals.sort(key=lambda x: x.get("n", 0))                        # oldest first
        if subj is None or len(vals) < 2 or len(vals) > MAX_BRANCHES:
            return rec
        rest = rels[hop:]
        known, unknown = [], []
        for x in vals:
            v = x.get("value") or {}
            eid = v.get("entity")
            who = notebook.entities.get(eid, eid) if eid else str(v.get("literal", ""))
            q = {"name": who, "relations": rest}
            if eid:
                q["entity_id"] = eid                   # a literal value is looked up by name, as 292 does
            sub = self.inner.answer(q, notebook)
            sf = sub.get("fields") or {}
            if sub.get("status") == C.OK and not sf.get("multi") and sf.get("answer"):
                known.append((who, sf["answer"], sf.get("trail") or []))
            else:
                unknown.append(who)
        fields = {"branches": [{"via": w, "answer": a} for w, a, _ in known] +
                  [{"via": w, "answer": None} for w in unknown],
                  "trail": [fid for _, _, t in known for fid in t], "source": f.get("source"),
                  "branched298": True}
        if not known:
            return {"kind": "answer", "status": C.MISSING_FACT, "name": question.get("name"),
                    "relations": rels, "fields": dict(fields, subject=" or ".join(unknown),
                                                      relation=rest[-1], hop=hop + 1)}
        if len({a for _, a, _ in known}) == 1 and not unknown:
            text = known[0][1]
        else:
            text = _join([f"{a} for {w}" for w, a, _ in known])
            if unknown:
                text += f" (I don't know it for {_join(unknown)})"
        return {"kind": "answer", "status": C.OK, "name": question.get("name"),
                "relations": rels, "fields": dict(fields, answer=text)}


def install298(loop):
    if not isinstance(loop.reasoner, Reasoner298):
        loop.reasoner = Reasoner298(loop.reasoner)
    return loop


def build_agent298(cfg: dict | None = None):
    import claude_loop292_agent as A
    return install298(A.build_agent292(cfg))
