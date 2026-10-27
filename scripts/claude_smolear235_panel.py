#!/usr/bin/env python3
"""Exp 235 -- panel loader (schema-tolerant) shared by the arm-B runner and scorer.

The blind panel is written by another agent; its exact field names are not
known before the seal, so this loader accepts the common shapes:
  turn text:   turn | text | input | message | utterance | user | prompt
  family:      family | category | group
  id:          id | case_id | qid (else the line number)
  context:     context | history | setup | previous | prior_turns (str or list)
  gold frames: gold | frames | gold_frames | expected | gold_frame (list/dict/str)
  per frame:   act/type/kind/frame/op, subject/subj/x, relation/rel/relations/chain,
               value/val/y/object, relation_aliases/aliases
Returns items: {id, family, turn, context: [str], gold: [frame]} where each
frame = {act, subject, relation: [str,...] (hops), value, aliases: [[...] per hop]}.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _first(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def _hops(rel):
    if isinstance(rel, (list, tuple)):
        return [str(x).strip() for x in rel]
    s = str(rel)
    if ">" in s:
        return [p.strip() for p in s.split(">")]
    return [s.strip()]


def _frame(f, item_aliases=None):
    if isinstance(f, str):
        parts = [p.strip() for p in f.split("|")]
        act = parts[0].upper()
        if act == "NONE":
            return None
        if act == "TEACH" and len(parts) >= 4:
            return dict(act="TEACH", subject=parts[1], relation=_hops(parts[2]), value=parts[3],
                        aliases=[list(item_aliases or [])])
        if act == "ASK" and len(parts) >= 3:
            h = _hops(parts[2])
            return dict(act="ASK", subject=parts[1], relation=h, value=None,
                        aliases=[list(item_aliases or []) if len(h) == 1 else [] for _ in h])
        return dict(act="BAD", subject="", relation=[""], value=None, aliases=[[]])
    act = str(_first(f, ["act", "type", "kind", "frame", "op", "action"], "")).upper()
    if act in ("NONE", "NO_SAVE", "NOSAVE", ""):
        if act == "" and _first(f, ["subject", "subj"]) is not None:
            act = "TEACH" if _first(f, ["value", "val", "object", "y"]) is not None else "ASK"
        else:
            return None
    if act.startswith("TEACH") or act in ("SAVE", "STORE", "WRITE", "FACT"):
        act = "TEACH"
    elif act.startswith("ASK") or act in ("QUESTION", "QUERY"):
        act = "ASK"
    rel = _first(f, ["relation", "rel", "relations", "chain", "r"], "")
    hops = _hops(rel)
    al = _first(f, ["relation_aliases", "aliases", "rel_aliases"], item_aliases or [])
    if isinstance(al, dict):
        al = [list(al.get(h, [])) for h in hops]
    elif al and all(isinstance(x, (list, tuple)) for x in al):
        al = [list(x) for x in al] + [[] for _ in range(len(hops) - len(al))]
    else:
        al = [list(al)] + [[] for _ in range(len(hops) - 1)] if len(hops) == 1 else \
            [list(al) for _ in hops]
    return dict(act=act, subject=str(_first(f, ["subject", "subj", "x", "entity"], "")),
                relation=hops, value=_first(f, ["value", "val", "y", "object", "answer_value"]),
                aliases=al)


def load_panel(path):
    items = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        turn = _first(d, ["turn", "text", "input", "message", "utterance", "user", "prompt"])
        ctx = _first(d, ["context", "history", "setup", "previous", "prior_turns"], [])
        if isinstance(ctx, str):
            ctx = [ctx] if ctx.strip() else []
        ctx = [c if isinstance(c, str) else str(_first(c, ["turn", "text", "user", "message"], ""))
               for c in ctx]
        gold = _first(d, ["gold", "frames", "gold_frames", "expected", "gold_frame"], [])
        if isinstance(gold, dict) and any(k in gold for k in ("frames", "gold")):
            gold = _first(gold, ["frames", "gold"], [])
        if isinstance(gold, (dict, str)):
            gold = [gold]
        item_al = _first(d, ["relation_aliases", "aliases"], None)
        frames = [x for x in (_frame(g, item_al) for g in gold) if x is not None]
        items.append(dict(id=str(_first(d, ["id", "case_id", "qid"], n)),
                          family=str(_first(d, ["family", "category", "group"], "?")),
                          turn=str(turn), context=ctx, gold=frames))
    return items


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="write turns-only file (no gold) for the GPU run")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--turns-out", required=True)
    a = ap.parse_args()
    its = load_panel(a.panel)
    Path(a.turns_out).write_text(json.dumps([{"id": i["id"], "turn": i["turn"]} for i in its],
                                            indent=1), encoding="utf-8")
    print(f"{len(its)} turns written")
