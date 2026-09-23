#!/usr/bin/env python3
"""Exp 264 -- post-seal reporting helper (NOT sealed, changes nothing).

The blind writer comma-joined risk tags in notes ("R13,R11,typo") while the
sealed 264 loader (like 261/261b) reads space-separated tokens, so the sealed
scorer's by_tag misses the comma-joined tags. Marks are unaffected (they
aggregate by family). This script re-buckets the ALREADY-RECORDED per-row
outcomes from panel264_score.json by comma-split tags for the RESULTS per-tag
table. It never reads turn/gold text (asserted): only notes tokens + the
recorded row numbers.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PANEL = Path("artifacts/claude-earpanel264-20260923/panel.jsonl")
SCORE = Path("artifacts/claude-earcheck264-20260923/panel264_score.json")


def main():
    tags = {}
    for line in PANEL.read_text().splitlines():
        d = json.loads(line)
        assert set(d) == {"id", "family", "turn", "gold", "clear", "notes"}
        toks = []
        for t in d["notes"].split():
            toks.extend(x for x in t.split(",") if x)
        keep = sorted({t for t in toks if re.fullmatch(r"R\d\w*", t)}
                      | ({t for t in toks} & {"lower", "typo", "noq", "correction"}))
        tags[d["id"]] = (d["family"], keep)
    res = json.loads(SCORE.read_text())
    rows = {r["id"]: r for r in res["rows"]}
    assert set(rows) == set(tags), "row/tag id mismatch"
    agg = {}
    for iid, (fam, ts) in tags.items():
        r = rows[iid]
        stmt = fam in ("plain_teach", "varied_teach", "full_names", "corrections")
        th = r["arms"]["A"]["teach_hit"]
        tn = r["arms"]["A"]["teach_gold"]
        wr = r["arms"]["A"]["wrong"]
        sv = r["arms"]["A"]["saved"]
        ah = r["arms"]["A"]["ask_hit"]
        an = r["arms"]["A"]["ask_gold"]
        for t in ts:
            key = f"{t}:{'stmt' if stmt else fam}"
            d = agg.setdefault(key, dict(n=0, th=0, tn=0, wrong=0, saved=0,
                                         ah=0, an=0, exact=0, unsure=0))
            d["n"] += 1
            d["th"] += th
            d["tn"] += tn
            d["wrong"] += wr
            d["saved"] += sv
            d["ah"] += ah
            d["an"] += an
            d["exact"] += r["arms"]["A"]["exact"]
            if stmt:
                d["unsure"] += r["unsure"]
    print(f"{'tag':22s} {'n':>3s} {'teach':>9s} {'wrong':>5s} {'ask':>7s} {'unsure':>6s}")
    for t in sorted(agg):
        d = agg[t]
        print(f"{t:22s} {d['n']:3d} {d['th']:>4d}/{d['tn']:<4d} {d['wrong']:5d} "
              f"{d['ah']:>3d}/{d['an']:<3d} {d['unsure']:6d}")
    Path("artifacts/claude-earcheck264-20260923/panel264comma_tags.json").write_text(
        json.dumps(agg, indent=1, sort_keys=True))
    print("wrote panel264comma_tags.json")


if __name__ == "__main__":
    sys.exit(main())
