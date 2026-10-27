"""Fresh held-out village rows for FINAL loop claims (thinking-loop plan, critic's point 1): python3 backbone/think/build_fresh.py OUT_DIR [--workers 4]

Every screen so far reads validation shards 0-3 (visits 0-999), including their depth 4-6 rows. This builds validation shards 4-11
(visits 1,000-2,999) with the same v1 generator settings as backbone/build_data.py (learnlab.village.shards, seed 0, 250 visits per
shard), so the rows come from the validation distribution (depth 0-6) but no run has seen them. The village `test` split is never generated or read.

Writes OUT/raw/validation/shard-NNNNN.*, OUT/fresh.jsonl (all rows, build_data's row format) and OUT/FRESH_REPORT.json (counts by depth and the
sha256 of fresh.jsonl). Rule (PREREG-think2 Addendum F): these rows are scored only for a final claim on an arm that already passed on validation,
once per arm, and the report's sha256 is committed before that first scoring.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_data as BD  # noqa: E402

FRESH_SHARDS = range(4, 12)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    raw = out / "raw" / "validation"
    tasks = [("validation", s, raw) for s in FRESH_SHARDS]
    assert not set(FRESH_SHARDS) & set(BD.VAL_SHARDS), "fresh shards overlap the validation shards every screen reads"
    with multiprocessing.get_context("spawn").Pool(args.workers, initializer=BD._init) as pool:
        for i, _ in enumerate(pool.imap_unordered(BD.make_shard, tasks)):
            print(f"[fresh] {i + 1}/{len(tasks)} shards", flush=True)
    rows = [r for _, s, d in tasks for r in BD.shard_rows("validation", s, d)]
    BD.write_jsonl(out / "fresh.jsonl", rows)
    by = {}
    for r in rows:
        by[str(r["depth"])] = by.get(str(r["depth"]), 0) + 1
    report = dict(split="validation", shards=list(FRESH_SHARDS), visits=len({r["visit_id"] for r in rows}), questions=len(rows),
                  by_depth=dict(sorted(by.items())), depth_4_6=sum(r["depth"] in (4, 5, 6) for r in rows), sha256=BD.sha(out / "fresh.jsonl"),
                  seed=BD.SEED, per_shard=BD.PER_SHARD)
    (out / "FRESH_REPORT.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
