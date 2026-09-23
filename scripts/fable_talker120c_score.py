#!/usr/bin/env python3
"""Experiment 120c — score the sealed 500-record held-out panel with the new
mouth (copy of scripts/fable_talker120_score.py; only the mouth class
changed from TalkerMouth to Talker120cMouth). Same metric names, same brake,
same rule-based status classifier, greedy mixture decoding. Every seed/case
reported, never averaged.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fable_talker120_mouth import brake_check, classify
from fable_talker120c_mouth import Talker120cMouth


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tok", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    rows = [json.loads(x) for x in (Path(args.data) / "heldout.jsonl").read_text(
        encoding="utf-8").splitlines() if x]
    if args.limit is not None:
        rows = rows[:args.limit]
    mouth = Talker120cMouth(args.ckpt, args.tok)
    t0 = time.time()
    before = after = ok_answer = ok_total = 0
    statuses = fallbacks = non_empty = 0
    pgs: list[float] = []
    examples = []
    for row in rows:
        rec = row["record"]
        try:
            raw, pg = mouth._decode_raw(rec, args.max_new)
        except Exception as exc:
            raw, pg = "", []
            print(json.dumps({"decode_error": str(exc)[:120]}))
        if raw:
            non_empty += 1
        pgs.extend(pg)
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
              "fallbacks": fallbacks, "non_empty_decodes": non_empty,
              "p_gen_mean": round(sum(pgs) / max(1, len(pgs)), 4),
              "seconds": round(time.time() - t0, 2), "examples": examples}
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
