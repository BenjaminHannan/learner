#!/usr/bin/env python3
"""gr-7d post hoc, report only (written after the count): for every wrong grid on squares and unseen, was the size
wrong, and were the cells that overlap the truth (the top-left block of the smaller size) all right? Practice data only.
  python3 -B artifacts/claude-gr7d-20260927/posthoc/size.py
"""
import json
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parents[1]


def load(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


st = Counter()
for arm in ("L7", "G5"):
    for task in ("squares", "unseen"):
        truth = {r["id"]: r for r in load(D / "practice" / f"{task}.jsonl")}
        for r in load(D / "run" / f"{arm}_{task}.jsonl"):
            it, g = truth[r["id"]], r["grid"]
            if g is None or g == it["grid"]:
                continue
            t = it["grid"]
            grp = task if task == "squares" else ("sepseen" if it["sep_seen"] else "sepnew")
            size = "right" if len(g) == len(t) else ("bigger" if len(g) > len(t) else "smaller")
            m = min(len(g), len(t))
            overlap = all(g[i][j] == t[i][j] for i in range(m) for j in range(m))
            st[f"{arm}_{grp}_size_{size}"] += 1
            st[f"{arm}_{grp}_size_{size}_overlap_exact"] += int(overlap)
            if size == "bigger":
                extra_blank = all(g[i][j] == 0 for i in range(len(g)) for j in range(len(g)) if i >= m or j >= m)
                extra_cols_blank = all(g[i][j] == 0 for i in range(m) for j in range(m, len(g)))
                st[f"{arm}_{grp}_bigger_extra_cols_all_blank"] += int(extra_cols_blank)
                st[f"{arm}_{grp}_bigger_all_extra_cells_blank"] += int(extra_blank)
for k, v in sorted(st.items()):
    print(k, v)


# second pass (added after the first output was read): is one grid's cell sequence, read row by row, a subsequence of
# the other's (only cells added or dropped), and what are the added cells?
def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j - 1] + (x != y), prev[j] + 1, cur[j - 1] + 1))
        prev = cur
    return prev[-1]


st2 = Counter()
for arm in ("L7", "G5"):
    for task in ("squares", "unseen"):
        truth = {r["id"]: r for r in load(D / "practice" / f"{task}.jsonl")}
        for r in load(D / "run" / f"{arm}_{task}.jsonl"):
            it, g = truth[r["id"]], r["grid"]
            if g is None or g == it["grid"]:
                continue
            t = it["grid"]
            o = [v for row in g for v in row]
            f = [v for row in t for v in row]
            only_added_or_dropped = lev(o, f) == abs(len(o) - len(f)) and len(o) != len(f)
            st2[f"{arm}_wrong"] += 1
            st2[f"{arm}_wrong_only_cells_added_or_dropped"] += int(only_added_or_dropped)
            if only_added_or_dropped and len(o) > len(f):
                added = Counter(o) - Counter(f)
                st2[f"{arm}_added_cells_blank"] += added[0]
                st2[f"{arm}_added_cells_digit"] += sum(v for k, v in added.items() if k)
print("# second pass")
for k, v in sorted(st2.items()):
    print(k, v)
