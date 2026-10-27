#!/usr/bin/env python3
"""Score the sealed 500-record held-out mouth panel (Experiment 53).

One batched decoder pass over all records (batch_size=8), then the plain-
software brake + rule-based status classifier per record. Reports before-brake
violations (raw decoder) and after-brake violations (final sentences), status
recoverability (O2), OK answer presence (O3), and 10 verbatim examples.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fable_mouth53_mouth import Mouth, brake_check, classify


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=8)
    args = ap.parse_args(argv)
    rows = [json.loads(x) for x in (Path(args.data) / "heldout.jsonl").read_text().splitlines() if x]
    mouth = Mouth(args.adapter)
    t0 = time.time()
    raws = mouth._decode_raw_batched([r["record"] for r in rows], batch_size=args.batch_size)
    decode_s = round(time.time() - t0, 2)
    before = after = ok_answer = ok_total = 0
    statuses = 0
    fallbacks = 0
    examples = []
    for row, raw in zip(rows, raws):
        rec = row["record"]
        good, _ = brake_check(raw, rec) if raw else (False, "empty")
        before += int(not good)
        said = raw if (raw and good) else mouth._fallback.say(rec)
        if not (raw and good):
            fallbacks += 1
        after += int(not brake_check(said, rec)[0])
        statuses += int(classify(said) == rec["status"])
        if rec["status"] == "OK":
            ok_total += 1
            ok_answer += int(str(rec["fields"]["answer"]).lower() in said.lower())
        if len(examples) < 10:
            examples.append({"status": rec["status"], "raw": raw, "sentence": said,
                             "reference": row.get("reference")})
    result = {"records": len(rows), "before_brake_violations": before,
              "after_brake_violations": after,
              "status_correct": statuses, "status_total": len(rows),
              "ok_answer_present": ok_answer, "ok_total": ok_total,
              "fallbacks": fallbacks, "decode_seconds": decode_s,
              "seconds": round(time.time() - t0, 2), "examples": examples}
    Path(args.out).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
