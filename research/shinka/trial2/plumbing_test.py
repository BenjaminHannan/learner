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
    print(f"worst case for one call: ${gc.worst({'model': prosecute.MODEL, 'max_tokens': prosecute.MAX_TOKENS, 'system': prosecute.SYSTEM, 'messages': [{'role': 'user', 'content': json.dumps(CARD)}], 'tools': [prosecute.TOOL]}):.4f}")
    out = prosecute.prosecute(gc, "0", CARD, (HERE.parent / "KNOWN_SHORT.md").read_text(), "plumbing")
    rows = [r for r in g._rows() if r["tag"].startswith("plumbing")]
    print(json.dumps({"result": out, "calls": len(rows), "usd_measured": sum(r["usd"] for r in rows),
                      "usage": [r["usage"] for r in rows], "stage0_spent": g.spent("0")}, indent=2))
