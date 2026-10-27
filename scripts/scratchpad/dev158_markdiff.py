#!/usr/bin/env python3
"""DEV-ONLY analysis (not a registered run): diff marks158 vs sealed marks150."""

import json
from pathlib import Path

ROOT = Path("artifacts")
M150 = ROOT / "fable-fix150-20260922/marks150"
M158 = ROOT / "fable-qform158-20260922/marks158"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


# p2 per-case
a = {r["id"]: r["agent_verdict"] for r in load(M150 / "p2-report.json")["rows"]}
b = {r["id"]: r["agent_verdict"] for r in load(M158 / "p2-report.json")["rows"]}
print("P2 moves:", [(k, a[k], b[k]) for k in a if a[k] != b.get(k)])
print("P2 final-only-in-158:", [k for k in b if k not in a])

# q1
print("Q1-150:", {k: load(M150 / "q1-report.json")[k] for k in ("f5_ok", "m5_ok", "f5_reply", "m5_reply")})
print("Q1-158:", {k: load(M158 / "q1-report.json")[k] for k in ("f5_ok", "m5_ok", "f5_reply", "m5_reply")})

# rt81 per-case
a = {c["id"]: (c["verdict"], c["observed"]) for c in load(M150 / "rt81-report.json")["cases"]}
b = {c["id"]: (c["verdict"], c["observed"]) for c in load(M158 / "rt81-report.json")["cases"]}
moves = [(k, a[k], b[k]) for k in a if a[k] != b.get(k)]
print(f"RT81 moves: {len(moves)}")
for m in moves:
    print("  ", m[0], "150:", m[1], "158:", m[2])

# rt110 per-case
a = {r["id"]: r["agent_verdict"] for r in load(M150 / "rt110-report.json")["rows"]}
b = {r["id"]: r["agent_verdict"] for r in load(M158 / "rt110-report.json")["rows"]}
print("RT110 moves:", [(k, a[k], b[k]) for k in a if a[k] != b.get(k)])

# p4 per-case
a = {r["id"]: (r["pass"], r.get("replies")) for r in load(M150 / "p4-report.json")["rows"]}
b = {r["id"]: (r["pass"], r.get("replies")) for r in load(M158 / "p4-report.json")["rows"]}
print("P4 moves:", [k for k in a if a[k] != b.get(k)])

# bench rows
for tag in ("fable_edit_200", "s2fresh_4hop"):
    a = [json.loads(l) for l in (M150 / f"bench-rows-{tag}.jsonl").read_text().splitlines()]
    b = [json.loads(l) for l in (M158 / f"bench-rows-{tag}.jsonl").read_text().splitlines()]
    da, db = {r["id"]: r for r in a}, {r["id"]: r for r in b}
    vm = [k for k in da if da[k]["verdict"] != db[k]["verdict"]]
    rm = [k for k in da if da[k]["reply"] != db[k]["reply"]]
    print(tag, "verdict_moves:", vm, "reply_moves:", len(rm))

# p3
print("P3-150:", load(M150 / "p3-report.json")["marks"])
print("P3-158:", load(M158 / "p3-report.json")["marks"])

# q4
print("Q4-150 leaks:", load(M150 / "q4-report.json")["leaks"])
print("Q4-158 leaks:", load(M158 / "q4-report.json")["leaks"])

# soak
for d, p in (("150", M150 / "soak-report.json"), ("158", M158 / "soak-report.json")):
    r = load(p)
    print(f"SOAK-{d}:", {k: r[k] for k in ("turns", "completed", "kill9s", "lost", "wrong", "dupes_allowed", "doubled_replies", "audit_lost_pairs", "audit_dup_pairs", "audit_wrong_pairs")})

# sleep
print("SLEEP-150:", load(M150 / "sleep-report.json").get("reason", "")[:100])
print("SLEEP-158:", load(M158 / "sleep-report.json").get("reason", "")[:100])
