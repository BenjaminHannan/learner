#!/usr/bin/env python3
"""Blind recount of practice run r1 (claude-gr9-20260927).

Written independently of the owner's count code and logs. Standard library only.
Reads truth from dev/ and greedy reads from run-r1/, then prints counts and the
fixed pass marks. Run from anywhere: paths are relative to this file.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # artifacts/claude-gr9-20260927
DEV = os.path.join(BASE, "dev")
RUN = os.path.join(BASE, "run-r1")

HELDOUT_MARKS = (".", "*", "=", ":")

# (run file stem, truth split)
RUNS = [
    ("L9_squares", "squares"),
    ("L9_seen", "seen"),
    ("L9_heldout", "heldout"),
    ("L9_lookalikes", "lookalikes"),
    ("L7_heldout", "heldout"),
    ("L7_lookalikes", "lookalikes"),
]


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                rows.append(json.loads(line))
    return rows


def by_id(rows, label):
    out = {}
    dups = []
    for r in rows:
        if r["id"] in out:
            dups.append(r["id"])
        out[r["id"]] = r
    return out, dups


def size_of(grid):
    return None if grid is None else len(grid)


def main():
    truth = {}
    for split in ("squares", "seen", "heldout", "lookalikes"):
        rows = load(os.path.join(DEV, split + ".jsonl"))
        truth[split] = (rows, *by_id(rows, split))

    runs = {}
    for stem, split in RUNS:
        rows = load(os.path.join(RUN, stem + ".jsonl"))
        runs[stem] = (rows, *by_id(rows, stem))

    # ---- 1. id check -------------------------------------------------------
    print("== 1. ID CHECK (run ids == truth ids, no duplicates) ==")
    all_ok = True
    for stem, split in RUNS:
        t_rows, t_map, t_dups = truth[split]
        r_rows, r_map, r_dups = runs[stem]
        missing = sorted(set(t_map) - set(r_map))
        extra = sorted(set(r_map) - set(t_map))
        ok = (not missing and not extra and not t_dups and not r_dups
              and len(t_rows) == len(r_rows))
        same_order = [r["id"] for r in t_rows] == [r["id"] for r in r_rows]
        all_ok &= ok
        print(f"{stem:14s} vs dev/{split}.jsonl: rows {len(r_rows)}/{len(t_rows)} "
              f"missing={len(missing)} extra={len(extra)} "
              f"dup_run={len(r_dups)} dup_truth={len(t_dups)} "
              f"same_order={same_order} -> {'OK' if ok else 'MISMATCH'}")
        if missing:
            print("   missing ids:", missing)
        if extra:
            print("   extra ids:", extra)
    if not all_ok:
        print("ID CHECK FAILED - counts below would not be trustworthy; stopping.")
        sys.exit(1)
    print()

    # ---- 2. greedy-read counts --------------------------------------------
    print("== 2. GREEDY READ COUNTS (field 'grid' only) ==")
    counts = {}
    nonexact = {}
    for stem, split in RUNS:
        t_rows, t_map, _ = truth[split]
        r_rows, r_map, _ = runs[stem]
        if split == "lookalikes":
            fs = {"train": 0, "H": 0, "S": 0, "other": 0}
            n_fmt = {"train": 0, "H": 0, "S": 0, "other": 0}
            for tid, t in t_map.items():
                fmt = t["format"]
                key = ("train" if fmt == "train" else
                       "H" if fmt.startswith("H") else
                       "S" if fmt.startswith("S") else "other")
                n_fmt[key] += 1
                if r_map[tid]["grid"] is not None:
                    fs[key] += 1
            total = sum(fs.values())
            counts[stem] = {"false_squares": total, **fs}
            print(f"{stem:14s} n={len(t_map):3d}  false squares (grid not null) = {total}"
                  f"  [train {fs['train']}/{n_fmt['train']}, H {fs['H']}/{n_fmt['H']}, "
                  f"S {fs['S']}/{n_fmt['S']}"
                  + (f", other {fs['other']}/{n_fmt['other']}" if n_fmt['other'] else "")
                  + "]")
            continue
        exact = none = wrong = 0
        bad = []
        for t in t_rows:  # truth order
            tid = t["id"]
            g = r_map[tid]["grid"]
            if g is None:
                none += 1
                bad.append((tid, t, None))
            elif g == t["grid"]:
                exact += 1
            else:
                wrong += 1
                bad.append((tid, t, g))
        counts[stem] = {"exact": exact, "none": none, "wrong": wrong}
        nonexact[stem] = bad
        print(f"{stem:14s} n={len(t_rows):3d}  exact={exact:3d}  none={none:3d}  wrong={wrong:3d}")
    print()

    # ---- 3. heldout subset by mark ----------------------------------------
    print(f"== 3. HELDOUT EXACT, marks in {list(HELDOUT_MARKS)} only ==")
    t_rows, t_map, _ = truth["heldout"]
    sub = [t for t in t_rows if t["mark"] in HELDOUT_MARKS]
    for stem in ("L9_heldout", "L7_heldout"):
        r_map = runs[stem][1]
        ex = sum(1 for t in sub if r_map[t["id"]]["grid"] == t["grid"])
        per = []
        for m in HELDOUT_MARKS:
            items = [t for t in sub if t["mark"] == m]
            e = sum(1 for t in items if r_map[t["id"]]["grid"] == t["grid"])
            per.append(f"{m!r} {e}/{len(items)}")
        counts[stem]["exact_marks_subset"] = ex
        print(f"{stem:14s} exact {ex}/{len(sub)}   ({', '.join(per)})")
    print()

    # ---- 4. L9 pick field --------------------------------------------------
    print("== 4. L9 'pick' FIELD EXACT ==")
    for stem, split in (("L9_squares", "squares"), ("L9_seen", "seen"), ("L9_heldout", "heldout")):
        t_rows = truth[split][0]
        r_map = runs[stem][1]
        ex = sum(1 for t in t_rows if r_map[t["id"]].get("pick") == t["grid"])
        pnone = sum(1 for t in t_rows if r_map[t["id"]].get("pick") is None)
        print(f"{stem:14s} pick exact={ex:3d}/{len(t_rows)}  pick null={pnone}")
    print()

    # ---- 5. fixed marks ---------------------------------------------------
    print("== 5. FIXED MARKS ==")
    l9h = counts["L9_heldout"]["exact"]
    l7h = counts["L7_heldout"]["exact"]
    l9s = counts["L9_squares"]["exact"]
    l9n = counts["L9_seen"]["exact"]
    l9f = counts["L9_lookalikes"]["false_squares"]
    l7f = counts["L7_lookalikes"]["false_squares"]
    m1 = l9h >= 90
    m2 = l9s >= 199
    m3 = l9n >= 98
    m4 = l9f <= l7f + 1
    too_easy = l7h >= 85
    proved_wrong = (not too_easy) and (l9h - l7h) < 10
    print(f"M1  L9 heldout exact >= 90            : {l9h} -> {str(m1).lower()}")
    print(f"M2  L9 squares exact >= 199           : {l9s} -> {str(m2).lower()}")
    print(f"M3  L9 seen exact >= 98               : {l9n} -> {str(m3).lower()}")
    print(f"M4  L9 false sq <= L7 false sq + 1    : {l9f} <= {l7f} + 1 -> {str(m4).lower()}")
    print(f"TOO-EASY      L7 heldout exact >= 85  : {l7h} -> {str(too_easy).lower()}")
    print(f"PROVED-WRONG  not TOO-EASY and L9-L7 heldout < 10 : {l9h} - {l7h} = {l9h - l7h} -> {str(proved_wrong).lower()}")
    if too_easy:
        outcome = "TOO-EASY"
    elif proved_wrong:
        outcome = "PROVED-WRONG"
    elif m1 and m2 and m3 and m4:
        outcome = "DEV-PASS"
    else:
        outcome = "DEV-FAIL"
    print(f"OUTCOME: {outcome}")
    print()

    # ---- 6. L9 non-exact items --------------------------------------------
    print("== 6. L9 NON-EXACT ITEMS (greedy 'grid'; ids only) ==")
    for stem in ("L9_squares", "L9_seen", "L9_heldout"):
        bad = nonexact[stem]
        print(f"{stem} ({len(bad)}):")
        for tid, t, g in bad:
            ts = size_of(t["grid"])
            rs = "none" if g is None else str(size_of(g))
            line = f"  {tid}  truth_size={ts}  read_size={rs}"
            if stem == "L9_heldout":
                line += f"  mark={t['mark']!r}"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
