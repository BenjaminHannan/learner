#!/usr/bin/env python3
"""lis-317 part 2 (report only, CPU): how many DEV facts could the live compiler ever write,
even if the reader were perfect?

For every gold teach/correct fact of the e2e DEV bank it builds the best frame a perfect reader
could give under the frame spec: owner "me" for USER, else the owner as typed in the turn (or
the previous reply); value as typed; the bank relation mapped to the closest table name with a
generous hand map (MAP below; e.g. girlfriend -> partner, manager -> boss). Then it runs the live
structural check (claude_lis300_compiler.check_fact, read-only) and counts the reasons.
No reader, no GPU. The gate (confidence >= 0.995) is not applied here, so this is an upper bound.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis300_compiler as CMP  # noqa: E402

MAP = {"job": "occupation", "former job": "occupation", "coworker": "colleague", "neighbor": "neighbour",
       "best friend": "best_friend", "mother-in-law": "mother_in_law", "girlfriend": "partner",
       "boyfriend": "partner", "fiancee": "fiance", "manager": "boss", "college": "school",
       "twin sister": "sister", "pet tortoise": "pet", "pet bird": "pet", "residence": "home",
       "university city": "city", "running buddy": "friend", "studies": None, "major": None,
       "species": None, "breed": None, "interest": None, "unit": None, "subject": None}


def typed(x, turn, prev):
    for h in (turn, prev or ""):
        m = re.search(re.escape(x), h, re.I)
        if m:
            return m.group(0)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="artifacts/claude-lis317-20260925/rows_e2edev.jsonl")
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding="utf-8").splitlines() if x.strip()]
    c, norel = Counter(), Counter()
    for r in rows:
        if r["kind"] not in ("teach", "correct"):
            continue
        for f in r["facts"]:
            rel = f["relation"]
            rel = MAP.get(rel, rel.replace(" ", "_").replace("-", "_"))
            if rel is None:
                rel = "other"
            ff = {"owner": "me" if f["owner"] == "USER" else typed(f["owner"], r["turn"], r["prev_reply"]),
                  "rel": rel, "value": typed(f["value"], r["turn"], r["prev_reply"]),
                  "mode": "CORRECT" if r["kind"] == "correct" else "ASSERT"}
            why = CMP.check_fact(ff, r["turn"], r["prev_reply"])
            c[why or "writable"] += 1
            if why == "rel_not_in_table":
                norel[f["relation"]] += 1
    n = sum(c.values())
    print(f"gold facts {n}")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print("  relations with no table name:", dict(norel))
    print(f"ceiling with a perfect reader and no gate: {c['writable']}/{n}")


if __name__ == "__main__":
    main()
