#!/usr/bin/env python3
"""gr-9 design check (Thread manager 11:5x, point 5), practice data only, report only: are the reader's row errors in
" . " and " * " formats concentrated in rows where blanks sit next to each other ("_ . _"), where the blank marker and
the separator alternate? Greedy reads of gr-7's reader: gr-7d unseen (L7) and gr-8 dev fresh unseen (L8 "greedy").
  python3 -B artifacts/claude-gr9-20260927/design/blanks.py
"""
import json
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def load(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def adjacent_blanks(row):
    return any(a == 0 and b == 0 for a, b in zip(row, row[1:]))


st = Counter()
for name, pd, run, key in (("gr7d", R / "claude-gr7d-20260927/practice", R / "claude-gr7d-20260927/run/L7_unseen.jsonl", "grid"),
                           ("gr8d", R / "claude-gr8d-20260927/practice", R / "claude-gr8d-20260927/run/L8_unseen.jsonl", "greedy")):
    fm = {f["id"]: f for f in json.loads((pd / "formats.json").read_text())}
    truth = {r["id"]: r for r in load(pd / "unseen.jsonl")}
    for r in load(run):
        t = truth[r["id"]]
        g = r[key]
        sep = fm[t["format_id"]]["sep"].strip()
        grp = "dotstar" if sep in (".", "*") else ("othernew" if not t["sep_seen"] else "seen")
        if g is None or len(g) != len(t["grid"]):
            st[f"{name}_{grp}_items_not_right_size_or_none"] += 1
            continue
        for row, trow in zip(g, t["grid"]):
            k = "adj" if adjacent_blanks(trow) else "noadj"
            st[f"{name}_{grp}_rows_{k}"] += 1
            st[f"{name}_{grp}_rows_{k}_wrong"] += int(row != trow)
for k, v in sorted(st.items()):
    print(k, v)
