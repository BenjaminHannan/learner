#!/usr/bin/env python3
"""rd-378 evidence recall: does keeping notes beside the raw turns help find the turns that answer a question?
Counts only; never prints dialog, note or question text.

Items per dialog: "heard" = every non-assistant turn (chat) or every turn (overheard), text "<date> <speaker>: <text>",
turn_ids [t]; "note" (arm B only) = each written note, text "<date> <note text> (<when>)", turn_ids = the note's cites
mapped to turn numbers (offsets over non-assistant turns of chat dialogs count every turn, as the writer saw them).
Retriever: BM25 (claude_bm393_evrecall.bm25_rank) and the stack's frozen MiniLM (claude_bm393_evrecall.MiniLM, or
--no-minilm), fused by reciprocal rank (1/(60+rank)). A question is found@k when any of its evidence turns is among the
turn_ids of the top k items; all@k when all are. "none" questions are skipped.
Arms: A heard only; B heard + notes. Per type and total, k = 5, 10.
python claude_rd378_eval.py --dialogs D.jsonl --questions Q.jsonl --notes NOTES.jsonl --out OUT.json [--no-minilm]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
from claude_bm393_evrecall import MiniLM, bm25_rank  # noqa: E402

KS = (5, 10)


def items_for(d, notes_by_t, with_notes):
    items = []
    nums = [t["t"] for t in d["turns"]]
    for t in d["turns"]:
        if d["kind"] == "chat" and t["speaker"] == "assistant":
            continue
        items.append({"text": f"{d.get('date', '')} {t['speaker']}: {t['text']}", "ids": {t["t"]}})
    if with_notes:
        for t in d["turns"]:
            for n in notes_by_t.get(t["t"]) or []:
                k = nums.index(t["t"])
                ids = {nums[k + c] for c in (n.get("cites") or [0]) if isinstance(c, int) and 0 <= k + c <= k}
                when = f" ({n['when']})" if n.get("when") else ""
                items.append({"text": f"{d.get('date', '')} {n['text']}{when}", "ids": ids or {t['t']}})
    for x in items:
        x["toks"] = B._toks(x["text"])
    return items


def fused(items, q, ml):
    r = {i: 1 / (60 + p) for p, i in enumerate(bm25_rank(items, q))}
    if ml is not None:
        e, qe = ml.embed([x["text"] for x in items]), ml.embed([q])
        sims = (e @ qe[0]).tolist()
        for p, i in enumerate(sorted(range(len(items)), key=lambda j: (-sims[j], j))):
            r[i] = r.get(i, 0) + 1 / (60 + p)
    return sorted(r, key=lambda i: (-r[i], i))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dialogs", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-minilm", action="store_true")
    a = ap.parse_args()
    D = {d["dialog"]: d for d in map(json.loads, Path(a.dialogs).read_text(encoding="utf-8").splitlines()) if d}
    Q = [q for q in map(json.loads, Path(a.questions).read_text(encoding="utf-8").splitlines()) if q]
    notes = defaultdict(dict)
    c = Counter()
    for r in map(json.loads, Path(a.notes).read_text(encoding="utf-8").splitlines()):
        notes[r["dialog"]][int(r["t"])] = r.get("notes") or []
        c["turns_read"] += 1
        c["notes"] += len(r.get("notes") or [])
        c["unparsed"] += int(r.get("notes") is None)
    ml = None if a.no_minilm else MiniLM()
    res = {"A": Counter(), "B": Counter()}
    for arm, with_notes in (("A", False), ("B", True)):
        cache = {dd: items_for(D[dd], notes[dd], with_notes) for dd in D}
        for q in Q:
            if q["type"] == "none" or not q["evidence"]:
                continue
            items = cache[q["dialog"]]
            order = fused(items, q["question"], ml)
            ev = set(q["evidence"])
            for k in KS:
                got = set().union(*[items[i]["ids"] for i in order[:k]]) if order else set()
                for tag in ("all", q["type"]):
                    res[arm][f"{tag}:n@{k}"] += 1
                    res[arm][f"{tag}:found@{k}"] += int(bool(ev & got))
                    res[arm][f"{tag}:allfound@{k}"] += int(ev <= got)
    out = {"counts": dict(c), "retriever": "bm25" if ml is None else "bm25+minilm rrf",
           "A": dict(sorted(res["A"].items())), "B": dict(sorted(res["B"].items()))}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
