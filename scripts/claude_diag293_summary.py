#!/usr/bin/env python3
"""Exp 293-diag summary: integer counts from rows.jsonl. Prints shape x arm
kind table, stage table, ask/write audits, d224 audit. Read-only over
rows.jsonl. New file only; additive."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
ART = Path(__file__).resolve().parent.parent / "artifacts" / "claude-diag293-20260923"
rows = [json.loads(x) for x in (ART / "rows.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
print(f"total rows={len(rows)}")
print("--- shape x arm x kind ---")
t = Counter((r["shape"], r["arm"], r["kind"]) for r in rows)
for key in sorted(t):
    print(f"  {key}: {t[key]}")
print("--- shape x kind totals ---")
t2 = Counter((r["shape"], r["kind"]) for r in rows)
for key in sorted(t2):
    print(f"  {key}: {t2[key]}")
print("--- shape x stage ---")
t3 = Counter((r["shape"], r["stage"]) for r in rows)
for key in sorted(t3):
    print(f"  {key}: {t3[key]}")
print("--- unparsed (ask=False) final turns ---")
for r in rows:
    if not r["has_ask"]:
        print(f'  {r["id"]} [{r["arm"]}/{r["shape"]}] kind={r["kind"]} stage={r["stage"]!r} reply={r["reply"][:60]!r}')
print("--- parsed (ask=True) final turns ---")
for r in rows:
    if r["has_ask"]:
        print(f'  {r["id"]} [{r["arm"]}/{r["shape"]}] kind={r["kind"]} stage={r["stage"]!r} reply={r["reply"][:60]!r}')
writes = [(r["id"], r["ev0"], r["ev1"]) for r in rows if r["ev0"] != r["ev1"]]
print(f"question-turn writes={len(writes)} {writes}")
d224 = Counter((r["d224"] or {}).get("kind") for r in rows if r.get("d224"))
print(f"d224 kinds on final turns: {dict(d224)}")
q1c = sum(1 for r in rows if r.get("q1c"))
print(f"final turns engaging 224c (q1c log)={q1c}")
print("--- yes/no-shaped turns that answered vs didnt-understand ---")
yn = [r for r in rows if r["shape"] in ("does-have", "does-noart", "is-poss", "is-inv", "does-live", "does-work", "does-from", "has", "is-of")]
c = Counter((r["shape"], r["kind"]) for r in yn)
for key in sorted(c):
    print(f"  {key}: {c[key]}")
print(f"yesno-shape rows={len(yn)} answered(yes/no/not-that-i-know)={sum(1 for r in yn if r['kind'] in ('yes','no','not-that-i-know'))} didnt-understand={sum(1 for r in yn if r['kind']=='didnt-understand')}")
