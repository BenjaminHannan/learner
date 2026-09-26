#!/usr/bin/env python3
"""lis-319c-full: full-claim re-scoring of reader panels (counts only; never prints panel text).

Why: claude_lis318_score / claude_lis319_score match a saved fact to gold on owner + value only (relation ignored,
first name accepted for a full name) and skip rows with no read before counting their gold. This scorer keeps the
same save rule (per-fact release: live structural check + conf >= T) but a saved fact is RIGHT only if it states the
same claim as a gold fact of its row:
  exact  = owner equal (USER <-> me, else the whole normalised name), value equal, relation equal or narrower
           (claude_lis300_score.NARROWER), so no judgement is needed;
  judged = owner + value matched by the old rule but not exact (relation words differ, or first name only):
           two blind judges answer "same claim?" and it counts RIGHT only if both say yes;
  wrong  = everything else.
Rows with no read keep their gold in the denominator (reported as missing).

pairs: python claude_lis319_fullclaim.py pairs --panel P --reads R --thresholds 0.995,0.98 --out PAIRS.jsonl
       writes the judged pairs (TEST-ONLY: holds panel text; judges only) and prints counts.
final: python claude_lis319_fullclaim.py final --panel P --reads R --thresholds 0.995,0.98 --pairs PAIRS.jsonl
           --verdicts J1.jsonl --verdicts J2.jsonl --out SCORE_FULL.json
       verdict rows {"pid": int, "same": true|false}.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402
from claude_lis300_score import NARROWER  # noqa: E402
from claude_lis317_gates import USER, e2e_match, n  # noqa: E402

WRITABLE = {"ASSERT", "CORRECT"}


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def exact(f, g):
    go, fo = n(g["owner"]), n(f.get("owner"))
    own = (fo in USER) if go == "user" else fo == go
    pr, gr = str(f.get("rel", "")), str(g.get("relation", g.get("rel", "")))
    return own and n(f.get("value")) == n(g["value"]) and (pr == gr or pr in NARROWER.get(gr, ()))


def saved_facts(row, r, T):
    fr = (r or {}).get("frame") or {}
    facts = [f for f in (fr.get("facts") or []) if isinstance(f, dict)]
    confs = (r or {}).get("conf") or []
    return [f for i, f in enumerate(facts)
            if CMP.check_fact(f, row["turn"], row.get("prev_reply", "")) is None
            and (confs[i] if i < len(confs) else 0.0) >= T]


def key(row_id, f, g):
    return json.dumps([row_id, n(f.get("owner")), f.get("rel"), n(f.get("value")), n(g["owner"]),
                       g.get("relation", g.get("rel")), n(g["value"])])


def walk(panel, reads, thresholds):
    rd = {r["id"]: r for r in reads}
    pairs = {}
    per_t = {}
    for T in thresholds:
        c = Counter()
        items = []   # (row_id, saved fact, [candidate gold with class])
        for row in panel:
            r = rd.get(row["id"])
            c["rows"] += 1
            c["gold"] += len(row["facts"])
            if r is None:
                c["missing_rows"] += 1
                c["missing_gold"] += len(row["facts"])
                continue
            for f in saved_facts(row, r, T):
                ex = [gi for gi, g in enumerate(row["facts"]) if exact(f, g)]
                loose = [(gi, g) for gi, g in enumerate(row["facts"]) if not exact(f, g) and e2e_match(f, g)]
                ks = []
                for gi, g in loose:
                    k = key(row["id"], f, g)
                    if k not in pairs:
                        pairs[k] = {"pid": len(pairs), "id": row["id"], "prev_reply": row.get("prev_reply", ""),
                                    "turn": row["turn"], "saved": {x: f.get(x) for x in ("owner", "rel", "value", "mode")},
                                    "gold": {"owner": g["owner"], "relation": g.get("relation", g.get("rel")),
                                             "value": g["value"]}}
                    ks.append((k, gi))
                items.append((row["id"], bool(row["facts"]), f, ex, ks))
                c["saved"] += 1
                c["saved_exact"] += bool(ex)
                c["saved_needs_judge"] += (not ex and bool(ks))
                c["saved_nomatch"] += (not ex and not ks)
        per_t[T] = (c, items)
    return pairs, per_t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pairs", "final"])
    ap.add_argument("--panel", required=True)
    ap.add_argument("--reads", required=True)
    ap.add_argument("--thresholds", default="0.995,0.98")
    ap.add_argument("--pairs")
    ap.add_argument("--verdicts", action="append", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Ts = [float(x) for x in a.thresholds.split(",")]
    panel, reads = load(a.panel), load(a.reads)
    pairs, per_t = walk(panel, reads, Ts)
    if a.mode == "pairs":
        Path(a.out).write_text("".join(json.dumps(p) + "\n" for p in pairs.values()), encoding="utf-8")
        print(json.dumps({str(T): dict(c) for T, (c, _) in per_t.items()} | {"pairs": len(pairs)}, indent=1))
        return
    old = {key(p["id"], {"owner": p["saved"]["owner"], "rel": p["saved"]["rel"], "value": p["saved"]["value"]},
               {"owner": p["gold"]["owner"], "relation": p["gold"]["relation"], "value": p["gold"]["value"]}): p["pid"]
           for p in load(a.pairs)}
    assert len(old) == len(pairs), "pairs file does not match these reads"
    V = []
    for vp in a.verdicts:
        V.append({int(r["pid"]): bool(r["same"]) for r in load(vp)})
    for v in V:
        assert set(v) == set(old.values()), "a judge file does not cover every pair"
    same = {pid for pid in old.values() if all(v[pid] for v in V)}
    out = {"judges": len(V), "pairs": len(old), "pairs_same_all_judges": len(same),
           "pairs_judges_disagree": sum(len({v[pid] for v in V}) > 1 for pid in old.values())}
    for T, (c, items) in per_t.items():
        right_gold, wrong_rows, nofact_rows, wrong = set(), set(), set(), 0
        for rid, has_gold, f, ex, ks in items:
            good = list(ex) + [gi for k, gi in ks if old[k] in same]
            if good:
                right_gold.update((rid, gi) for gi in good)
            else:
                wrong += 1
                wrong_rows.add(rid)
            if not has_gold:
                nofact_rows.add(rid)
        out[str(T)] = dict(c) | {"saved_right_full": len(right_gold), "saved_wrong_full": wrong,
                                 "wrong_turns_full": len(wrong_rows), "nofact_rows_with_save": len(nofact_rows)}
    print(json.dumps(out, indent=1))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
