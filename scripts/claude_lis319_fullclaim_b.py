#!/usr/bin/env python3
"""lis-319c-full addendum B (registered 2026-09-26 ~02:35 UTC, before any F data): stricter whole-claim scoring.

Changes from claude_lis319_fullclaim.py (answers the second outside review, 02:11 UTC):
  1. a narrower saved relation (e.g. mother for gold parent) is no longer "exact": it goes to the blind judges, who say
     same only if the turn states the narrower one (unsupported specialisation);
  2. one-to-one credit: each saved fact credits at most one gold fact and each gold fact is credited once (exact matches
     first, then judged-same); a second saved copy of an already-credited claim is counted as a duplicate, not right;
  3. unchanged: rows with no read or no parsable frame keep their gold in the denominator; gold facts are NOT passed
     through the compiler, so compiler rejections cannot remove gold (they only stop saves).
Everything else (save rule, judges, brief JUDGE_SAME.md) as claude_lis319_fullclaim.py.

pairs: python claude_lis319_fullclaim_b.py pairs --panel P --reads R --thresholds 0.995,0.98 --out PAIRS_B.jsonl
final: python claude_lis319_fullclaim_b.py final --panel P --reads R --thresholds 0.995,0.98 --pairs PAIRS_B.jsonl
           --verdicts J1.jsonl --verdicts J2.jsonl --out SCORE_FULL_B.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis317_gates import USER, e2e_match, n  # noqa: E402
from claude_lis319_fullclaim import key, load, saved_facts  # noqa: E402


def exact_b(f, g):
    go, fo = n(g["owner"]), n(f.get("owner"))
    own = (fo in USER) if go == "user" else fo == go
    return own and n(f.get("value")) == n(g["value"]) and str(f.get("rel", "")) == str(g.get("relation", g.get("rel", "")))


def walk(panel, reads, thresholds):
    rd = {r["id"]: r for r in reads}
    pairs, per_t = {}, {}
    for T in thresholds:
        c, rows = Counter(), []
        for row in panel:
            r = rd.get(row["id"])
            c["rows"] += 1
            c["gold"] += len(row["facts"])
            if r is None or r.get("frame") is None:
                c["no_read_or_parse_rows"] += 1
                c["no_read_or_parse_gold"] += len(row["facts"])
            items = []
            for f in (saved_facts(row, r, T) if r is not None else []):
                ex = [gi for gi, g in enumerate(row["facts"]) if exact_b(f, g)]
                ks = []
                for gi, g in enumerate(row["facts"]):
                    if gi in ex or not e2e_match(f, g):
                        continue
                    k = key(row["id"], f, g)
                    if k not in pairs:
                        pairs[k] = {"pid": len(pairs), "id": row["id"], "prev_reply": row.get("prev_reply", ""),
                                    "turn": row["turn"],
                                    "saved": {x: f.get(x) for x in ("owner", "rel", "value", "mode")},
                                    "gold": {"owner": g["owner"], "relation": g.get("relation", g.get("rel")),
                                             "value": g["value"]}}
                    ks.append((k, gi))
                items.append((ex, ks))
                c["saved"] += 1
                c["saved_exact"] += bool(ex)
                c["saved_needs_judge"] += (not ex and bool(ks))
                c["saved_nomatch"] += (not ex and not ks)
            rows.append((row["id"], bool(row["facts"]), items))
        per_t[T] = (c, rows)
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
    pairs, per_t = walk(load(a.panel), load(a.reads), Ts)
    if a.mode == "pairs":
        Path(a.out).write_text("".join(json.dumps(p) + "\n" for p in pairs.values()), encoding="utf-8")
        print(json.dumps({str(T): dict(c) for T, (c, _) in per_t.items()} | {"pairs": len(pairs)}, indent=1))
        return
    pid = {key(p["id"], p["saved"], p["gold"]): p["pid"] for p in load(a.pairs)}
    assert set(pid) == set(pairs), "pairs file does not match these reads"
    V = [{int(r["pid"]): bool(r["same"]) for r in load(vp)} for vp in a.verdicts]
    assert V and all(set(v) == set(pid.values()) for v in V), "a judge file does not cover every pair"
    same = {p for p in pid.values() if all(v[p] for v in V)}
    out = {"judges": len(V), "pairs": len(pid), "pairs_same_all_judges": len(same),
           "pairs_judges_disagree": sum(len({v[p] for v in V}) > 1 for p in pid.values())}
    for T, (c, rows) in per_t.items():
        right = wrong = dup = 0
        wrong_rows, nofact_rows = set(), set()
        for rid, has_gold, items in rows:
            taken = set()
            order = sorted(range(len(items)), key=lambda i: not items[i][0])   # exact matches claim gold first
            for i in order:
                ex, ks = items[i]
                ok = list(ex) + [gi for k, gi in ks if pid[k] in same]
                free = [gi for gi in ok if gi not in taken]
                if free:
                    taken.add(free[0])
                    right += 1
                elif ok:
                    dup += 1
                else:
                    wrong += 1
                    wrong_rows.add(rid)
                if not has_gold:
                    nofact_rows.add(rid)
        out[str(T)] = dict(c) | {"saved_right_full": right, "saved_wrong_full": wrong, "saved_duplicate": dup,
                                 "wrong_turns_full": len(wrong_rows), "nofact_rows_with_save": len(nofact_rows)}
    print(json.dumps(out, indent=1))
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
