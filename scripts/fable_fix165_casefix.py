#!/usr/bin/env python3
"""One-off post-seal case fix for exp 165 (reported in RESULTS.md).

Bug: typo rows teach a setup fact + the typo fact, but `expect` listed only
the typo triple, so exact-equality scoring (correctly) flagged WRONG-WRITE.
Fix: expect = [setup triple, typo triple] (still exact, still 0 extra
writes). Re-run of the probe after this fix is the open re-run.
"""

import json
import re
from pathlib import Path

ART165 = Path("artifacts/fable-typo165-20260922")
PAT = re.compile(r"^([A-Za-z]+)'s\s+([A-Za-z]+)\s+is\s+(.+?)\.\s*$")


def main() -> int:
    p = ART165 / "cases165.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    n = 0
    for r in rows:
        if r["group"] == "typo" and isinstance(r["expect"], list) \
                and (not r["expect"] or isinstance(r["expect"][0], str)):
            m = PAT.match(r["teaches"][0])
            assert m, r["id"]
            setup = [m.group(1), m.group(2).lower(), m.group(3)]
            r["expect"] = [setup, list(r["expect"])]
            n += 1
    p.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    print(f"patched {n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
