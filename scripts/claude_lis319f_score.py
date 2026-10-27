#!/usr/bin/env python3
"""lis-319f: count former facts saved as current (panel: counts only; dev: report only).

panel: python claude_lis319f_score.py panel --panel P --reads R --threshold 0.995 --out OUT.json
       P rows carry "facts" (current, stated as true) and "former" (no longer true). A saved fact (same live save rule
       as claude_lis319_fullclaim.saved_facts) is FORMER-AS-CURRENT when its owner and value match a former item of its
       row (claude_lis317_gates.e2e_match) and match no current fact of that row.
dev:   python claude_lis319f_score.py dev --dev DEV.jsonl --pred PRED.jsonl [--pred PRED2.jsonl] --threshold 0.995 --out OUT.json
       Same count on built dev rows whose gold frame has a FORMER fact (rows missing from PRED are skipped and
       counted), plus right/wrong saves on those rows by claude_lis300_score.match.
subset: python claude_lis319f_score.py subset --dev DEV.jsonl --src-prefix former319 --out ROWS.jsonl
       writes the dev rows whose src starts with the prefix (to read them with the old reader).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis300_score import match  # noqa: E402
from claude_lis317_gates import e2e_match  # noqa: E402
from claude_lis319_fullclaim import load, saved_facts  # noqa: E402


def panel(a):
    rd = {r["id"]: r for r in load(a.reads)}
    c = Counter()
    for row in load(a.panel):
        former = row.get("former") or []
        c["rows"] += 1
        c["former_rows"] += bool(former)
        c["former_items"] += len(former)
        r = rd.get(row["id"])
        if r is None:
            c["missing_rows"] += 1
            continue
        hit = 0
        for f in saved_facts(row, r, a.threshold):
            if any(e2e_match(f, g) for g in former) and not any(e2e_match(f, g) for g in row["facts"]):
                hit += 1
        c["former_as_current"] += hit
        c["former_rows_with_such_save"] += bool(hit)
    out = dict(sorted(c.items())) | {"threshold": a.threshold}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out))


def dev(a):
    P = {r["id"]: r for p in a.pred for r in load(p)}
    c = Counter()
    for row in load(a.dev):
        fr = json.loads(row["target"].split("<END>")[0])
        gold = fr.get("facts") or []
        former = [g for g in gold if g.get("mode") == "FORMER"]
        if not former:
            continue
        c[f"former_rows:{row['src']}"] += 1
        r = P.get(row["id"])
        if r is None:
            c["missing_pred"] += 1
            continue
        c["former_rows_scored"] += 1
        cur = [g for g in gold if g.get("mode") in ("ASSERT", "CORRECT")]
        fake = {"turn": row["turn"], "prev_reply": row.get("prev_reply", "")}
        for f in saved_facts(fake, r, a.threshold):
            if any(match(f, g) for g in cur):
                c["saved_right"] += 1
            elif any(str(f.get("owner", "")).lower() == str(g.get("owner", "")).lower()
                     and str(f.get("value", "")).lower() == str(g.get("value", "")).lower() for g in former):
                c["former_as_current"] += 1
            else:
                c["saved_other_wrong"] += 1
    out = dict(sorted(c.items())) | {"threshold": a.threshold}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out))


def subset(a):
    rows = [r for r in load(a.dev) if str(r.get("src", "")).startswith(a.src_prefix)]
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows)}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["panel", "dev", "subset"])
    ap.add_argument("--panel")
    ap.add_argument("--reads")
    ap.add_argument("--dev")
    ap.add_argument("--pred", action="append", default=[])
    ap.add_argument("--src-prefix")
    ap.add_argument("--threshold", type=float, default=0.995)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    {"panel": panel, "dev": dev, "subset": subset}[a.mode](a)


if __name__ == "__main__":
    main()
