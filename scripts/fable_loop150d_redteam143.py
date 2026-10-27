#!/usr/bin/env python3
"""Exp 150d G3-143 driver -- question red team 143 through loop150d.

Follows the scripts/fable_loop138b_redteam143.py PATTERN (sealed cases +
judge from scripts/fable_redteam143_run.py by import, scratch dir per
case); only the 150d arm runs, compared per-case against loop138b's OWN
frozen rows (read-only). Bar: 0 new WRONG-ANSWER vs loop138b; every move
predicted in writing before the run (predicted: none).

Outputs into artifacts/fable-hedgecase150d-20260922/.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop150d_agent as L150d  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hedgecase150d-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cfg = copy.deepcopy(L150d.DEFAULT_CONFIG150D)
    cfg["sleep_threshold"] = 100000
    R143.Loop132Daemon = L150d.Loop150dDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(cfg)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop150d"
    rows: list[dict] = []
    for case in suite["cases"]:
        rows.append(R143.run_case(case, scratch / case["id"], markers))
    (ART / "redteam143-loop150d.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads((ART138B / "redteam143-loop138b.json").read_text(
        encoding="utf-8"))["rows"]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop138b": b["verdict"], "loop150d": r["verdict"]})
            if r["verdict"] == "WRONG-ANSWER" \
                    and b["verdict"] != "WRONG-ANSWER":
                new_wrong += 1
    out = {"seconds": round(time.time() - t0, 1),
           "loop150d": dict(Counter(r["verdict"] for r in rows)),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves}
    (ART / "redteam143-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3-143: loop150d {out['loop150d']} new_wrong={new_wrong} "
          f"moves={len(moves)} in {out['seconds']}s", flush=True)
    for m in moves:
        print(f"  MOVE {m['id']} [{m['family']}]: "
              f"{m['loop138b']} -> {m['loop150d']}", flush=True)
    return 1 if (new_wrong or moves) else 0


if __name__ == "__main__":
    sys.exit(main())
