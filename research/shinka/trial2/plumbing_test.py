#!/usr/bin/env python3
"""Stage 0 plumbing test: ONE prosecutor call on a known-paraphrased card. Cap: Stage 0 = $0.50.

NOT RUN in the build session (no API key). The coordinator runs it, or the next session does once the
key exists. It prints the measured cost and the usage figures so the tally can be checked against the
console bill. Usage: python plumbing_test.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prosecute  # noqa: E402
from money import Guard  # noqa: E402

CARD = {
    "core_operation": "Pool each line's token states with several learned queries and concatenate the heads.",
    "mechanism": "Learn H query vectors; each attends over the line's tokens; concatenate the H pooled vectors "
                 "and project to key and value.",
    "why_novel_names": "Different heads can attend to different roles, so the unseen person token is kept.",
    "nearest_known": "none claimed",
    "prediction": "person-lost errors on novel names fall",
    "fits_interface": "yes",
}

if __name__ == "__main__":
    g = Guard()
    gc = prosecute.make_client(g)
    known = (HERE.parent / "KNOWN_SHORT.md").read_text()
    print(f"worst case for one call (same payload as the real call): ${gc.worst(prosecute.build_params(CARD, known)):.4f}")
    out = prosecute.prosecute(gc, "0", CARD, known, "plumbing")
    rows = [r for r in g._rows() if r["tag"].startswith("plumbing") and r["usd"] > 0]
    print(json.dumps({"result": out, "charged_rows": len(rows), "usd_measured": sum(r["usd"] for r in rows),
                      "usage": [r.get("usage") for r in rows],
                      "unknown_outcome": [r.get("unknown_outcome") for r in rows if r.get("unknown_outcome")],
                      "stage0_spent": g.spent("0")}, indent=2))
