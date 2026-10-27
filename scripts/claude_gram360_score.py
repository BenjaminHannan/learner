#!/usr/bin/env python3
"""gram-360 marks P360.1 / P360.2 from two blind graders' outputs (PASSMARKS.md).

  python -B scripts/claude_gram360_score.py GRADE_OUT
Reads GRADE_OUT/key_{A,B}.json and GRADE_OUT/grades_{A,B}.jsonl ({"id", "ok": true|false}). Prints counts only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    d = Path(sys.argv[1])
    res = {}
    for g in ("A", "B"):
        key = json.loads((d / f"key_{g}.json").read_text(encoding="utf-8"))
        ok = {}
        for l in (d / f"grades_{g}.jsonl").read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                ok[r["id"]] = bool(r["ok"])
        missing = [i for i in key if i not in ok]
        caught = sum(1 for i, k in key.items() if k["planted_error"] and ok.get(i) is False)
        kept = sum(1 for i, k in key.items() if k["planted_clean"] and ok.get(i) is True)
        r = {"missing": len(missing), "planted_caught": caught, "clean_kept": kept,
             "valid": caught >= 36 and kept >= 36 and not missing}
        for s in ("rule_raw", "rule_final", "all_final"):
            ids = [i for i, k in key.items() if s in k["sets"]]
            good = sum(1 for i in ids if ok.get(i) is True)
            r[s] = [good, len(ids), round(100.0 * good / max(1, len(ids)), 1)]
        r["gain"] = round(r["rule_final"][2] - r["rule_raw"][2], 1)
        res[g] = r
    v = [res[g] for g in ("A", "B")]
    res["P360.1"] = "PASS" if all(x["valid"] and x["rule_final"][2] >= 90.0 for x in v) else "FAIL"
    res["P360.2"] = "PASS" if all(x["valid"] and x["gain"] >= 20.0 for x in v) else "FAIL"
    res["proved_wrong"] = any(x["valid"] and x["gain"] < 5.0 for x in v)
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
