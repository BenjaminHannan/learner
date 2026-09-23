#!/usr/bin/env python3
"""Exp 290-diag summary: integer counts from rows.jsonl. Prints shape x arm
kind tables per agent, k-vs-l equality, void-batch check, d224/q1c audit,
write audit. New file only; additive. Read-only over rows.jsonl."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
ART = Path(__file__).resolve().parent.parent / "artifacts" / "claude-diag290-20260923"
rows = [json.loads(x) for x in (ART / "rows.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
print(f"total rows={len(rows)}")
by_agent = Counter(r["agent"] for r in rows)
print("rows per agent:", dict(sorted(by_agent.items())))

VOID = "138m-no224"  # first attempt leaked wrappers; superseded by v2
good = [r for r in rows if r["agent"] != VOID]
print(f"void-excluded rows={len(good)}")

# k vs l equality on the full matrix
k = {(r["id"]): r for r in good if r["agent"] == "138k"}
l = {(r["id"]): r for r in good if r["agent"] == "138l"}
assert set(k) == set(l) and len(k) == 42, (len(k), len(l))
diff = [i for i in k if k[i]["reply"] != l[i]["reply"] or k[i]["kind"] != l[i]["kind"]]
print(f"138k-vs-138l reply diffs={len(diff)} {diff}")

# void batch check: leaked stack should equal full 138m on same ids
m = {(r["id"]): r for r in good if r["agent"] == "138m"}
v = [r for r in rows if r["agent"] == VOID]
veq = sum(1 for r in v if r["id"] in m and m[r["id"]]["reply"] == r["reply"])
print(f"void-batch rows={len(v)} identical-to-138m={veq}")

# shape x arm kind tables
for tag in ["138k", "138l", "138m", "138l+224", "138l+224+224c", "138m-no224v2"]:
    sub = [r for r in good if r["agent"] == tag] + ([r for r in rows if r["agent"] == tag] if tag.startswith("138m-no224v2") or tag.startswith("138l+") else [])
    sub = [r for r in rows if r["agent"] == tag and (tag not in ("138k", "138l", "138m") or True)]
    if tag in ("138k", "138l", "138m"):
        sub = [r for r in sub if True]
    t = Counter((r["shape"], r["arm"], r["kind"]) for r in sub)
    print(f"--- {tag} n={len(sub)}")
    for key in sorted(t):
        print(f"  {key}: {t[key]}")

# d224 audit on 138m
m224 = [r for r in good if r["agent"] == "138m" and r["d224"]]
print(f"138m turns with d224 entry={len(m224)}; kinds=",
      Counter(r["d224"]["kind"] for r in m224),
      "qbranchTrue=", sum(1 for r in m224 if r["d224"]["qbranch"]),
      "acts=", Counter(tuple(r["d224"]["acts"]) for r in m224))
m_q1c = [r for r in good if r["agent"] == "138m" and r["q1c"]]
print(f"138m turns engaging 224c (q1c log)={len(m_q1c)}")
s224 = [r for r in rows if r["agent"] in ("138l+224", "138l+224+224c") and r["d224"]]
print(f"bisect S1/S2 d224 entries={len(s224)} kinds=", Counter(r["d224"]["kind"] for r in s224))
s_q1c = [r for r in rows if r["agent"] == "138l+224+224c" and r["q1c"]]
print(f"S2 q1c entries={len(s_q1c)}")

# write audit: question turns must not write
writes = [(r["agent"], r["id"]) for r in rows if r["ev0"] != r["ev1"]]
print(f"question-turn writes={len(writes)} {writes}")

# ask parity across k/l/m on full matrix
for i in sorted(set(k)):
    aks = {t: next(r for r in good if r["agent"] == t and r["id"] == i)["has_ask"] for t in ("138k", "138l", "138m")}
    if len(set(aks.values())) != 1:
        print("ASK-MISMATCH", i, aks)
print("ask-parity check done")

# list every unparsed (ask=False) final turn and its reply per agent
print("--- unparsed turns (ask=False) ---")
for r in good:
    if r["agent"] in ("138k", "138l", "138m") and not r["has_ask"]:
        print(f'{r["agent"]} {r["id"]} [{r["arm"]}/{r["shape"]}] kind={r["kind"]} reply={r["reply"][:60]}...')
