"""Separate recount of the gr-8 dev run (claude-gr8d-20260927).

Written from the definitions given to the recounter and from PLAN-gr8d.md only.
Plain python3, no third-party packages, imports nothing from scripts/.
Run from the repo root:  python3 -B artifacts/claude-gr8d-20260927/recount/count.py
Prints only "name value" lines (integers, true/false, or one outcome word).
"""
import json
import os
from collections import Counter

D8 = "artifacts/claude-gr8d-20260927"
D7 = "artifacts/claude-gr7d-20260927"

PRACTICE_SQUARES = os.path.join(D8, "practice", "squares.jsonl")
PRACTICE_UNSEEN = os.path.join(D8, "practice", "unseen.jsonl")
PRACTICE_LOOK = os.path.join(D8, "practice", "lookalikes.jsonl")
RUN_SQUARES = os.path.join(D8, "run", "L8_squares.jsonl")
RUN_UNSEEN = os.path.join(D8, "run", "L8_unseen.jsonl")
RUN_LOOK = os.path.join(D8, "run", "L8_lookalikes.jsonl")
RUN_REPLAY = os.path.join(D8, "run", "L8_replay.jsonl")
GR7_UNSEEN = os.path.join(D7, "practice", "unseen.jsonl")
GR7_L7_UNSEEN = os.path.join(D7, "run", "L7_unseen.jsonl")


def out(name, value):
    if isinstance(value, bool):
        value = "true" if value else "false"
    print(f"{name} {value}")


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def by_id(rows):
    return {r["id"]: r for r in rows}


def check_ids(name, run_rows, truth_rows):
    """Row counts, duplicate ids, id-set equality, and complete==false rows."""
    run_ids = [r["id"] for r in run_rows]
    truth_ids = [r["id"] for r in truth_rows]
    run_dups = sum(c - 1 for c in Counter(run_ids).values() if c > 1)
    truth_dups = sum(c - 1 for c in Counter(truth_ids).values() if c > 1)
    missing = len(set(truth_ids) - set(run_ids))
    extra = len(set(run_ids) - set(truth_ids))
    sets_equal = set(run_ids) == set(truth_ids)
    out(f"{name}.run_rows", len(run_rows))
    out(f"{name}.truth_rows", len(truth_rows))
    out(f"{name}.run_dup_ids", run_dups)
    out(f"{name}.truth_dup_ids", truth_dups)
    out(f"{name}.ids_missing_from_run", missing)
    out(f"{name}.ids_extra_in_run", extra)
    out(f"{name}.id_sets_equal", sets_equal)
    if run_rows and "complete" in run_rows[0]:
        out(f"{name}.complete_false", sum(1 for r in run_rows if r.get("complete") is not True))
    ok = sets_equal and run_dups == 0 and truth_dups == 0 and len(run_rows) == len(truth_rows)
    out(f"{name}.ids_ok", ok)
    return ok


def nrows(grid):
    return len(grid)


def classify(reading, truth):
    """exact / none / wrong, per the definitions."""
    if reading is None:
        return "none"
    if reading == truth:
        return "exact"
    return "wrong"


def is_wrong_size(reading, truth):
    return classify(reading, truth) == "wrong" and nrows(reading) != nrows(truth)


def tally(prefix, items, run, field):
    """items: list of truth rows; run: dict id -> run row."""
    c = Counter()
    for t in items:
        r = run.get(t["id"])
        reading = r[field] if r is not None else None
        k = classify(reading, t["grid"])
        c[k] += 1
        if is_wrong_size(reading, t["grid"]):
            c["wrong_size"] += 1
    out(f"{prefix}.{field}.exact", c["exact"])
    out(f"{prefix}.{field}.wrong", c["wrong"])
    out(f"{prefix}.{field}.none", c["none"])
    out(f"{prefix}.{field}.wrong_size", c["wrong_size"])
    return c


def fixed_harmed(items, run):
    fixed = harmed = 0
    for t in items:
        r = run.get(t["id"])
        g = r["greedy"] if r is not None else None
        p = r["pick"] if r is not None else None
        g_exact = g is not None and g == t["grid"]
        p_exact = p is not None and p == t["grid"]
        if not g_exact and p_exact:
            fixed += 1
        if g_exact and not p_exact:
            harmed += 1
    return fixed, harmed


def main():
    sq_truth = load(PRACTICE_SQUARES)
    un_truth = load(PRACTICE_UNSEEN)
    lk_truth = load(PRACTICE_LOOK)
    sq_run_rows = load(RUN_SQUARES)
    un_run_rows = load(RUN_UNSEEN)
    lk_run_rows = load(RUN_LOOK)
    rp_run_rows = load(RUN_REPLAY)
    g7_truth = load(GR7_UNSEEN)
    l7_rows = load(GR7_L7_UNSEEN)

    # 1. Row counts and id checks.
    ids_ok = True
    ids_ok &= check_ids("ids.squares", sq_run_rows, sq_truth)
    ids_ok &= check_ids("ids.unseen", un_run_rows, un_truth)
    ids_ok &= check_ids("ids.lookalikes", lk_run_rows, lk_truth)
    ids_ok &= check_ids("ids.replay", rp_run_rows, g7_truth)
    ids_ok &= check_ids("ids.gr7d_L7_unseen", l7_rows, g7_truth)
    out("ids.all_ok", ids_ok)

    sq_run = by_id(sq_run_rows)
    un_run = by_id(un_run_rows)
    lk_run = by_id(lk_run_rows)
    rp_run = by_id(rp_run_rows)
    l7 = by_id(l7_rows)

    # 2. Fresh squares and fresh unseen, greedy and pick.
    tally("squares", sq_truth, sq_run, "greedy")
    sq_pick = tally("squares", sq_truth, sq_run, "pick")
    sq_greedy_exact = sum(
        1 for t in sq_truth
        if sq_run.get(t["id"]) is not None and sq_run[t["id"]]["greedy"] is not None
        and sq_run[t["id"]]["greedy"] == t["grid"]
    )
    un_greedy = tally("unseen", un_truth, un_run, "greedy")
    un_pick = tally("unseen", un_truth, un_run, "pick")
    for flag in (True, False):
        sub = [t for t in un_truth if t.get("sep_seen") is flag]
        name = "unseen_sep_seen_true" if flag else "unseen_sep_seen_false"
        out(f"{name}.items", len(sub))
        tally(name, sub, un_run, "greedy")
        tally(name, sub, un_run, "pick")

    # 3. Lookalikes.
    lk_greedy_nonnull = sum(
        1 for t in lk_truth if lk_run.get(t["id"]) is not None and lk_run[t["id"]]["greedy"] is not None
    )
    lk_pick_nonnull = sum(
        1 for t in lk_truth if lk_run.get(t["id"]) is not None and lk_run[t["id"]]["pick"] is not None
    )
    out("lookalikes.items", len(lk_truth))
    out("lookalikes.greedy.nonnull", lk_greedy_nonnull)
    out("lookalikes.pick.nonnull", lk_pick_nonnull)

    # 4. Replay.
    r0_matches = 0
    for t in g7_truth:
        r = rp_run.get(t["id"])
        old = l7.get(t["id"])
        if r is None or old is None:
            continue
        if r["greedy"] == old["grid"]:
            r0_matches += 1
    r0 = r0_matches == 200 and len(g7_truth) == 200
    out("replay.items", len(g7_truth))
    out("replay.R0_greedy_equals_L7", r0_matches)

    eleven = []
    for t in g7_truth:
        old = l7.get(t["id"])
        g = old["grid"] if old is not None else None
        if g is not None and g != t["grid"] and nrows(g) != nrows(t["grid"]):
            eleven.append(t)
    out("replay.wrong_size_set", len(eleven))
    el_pick_exact = el_pick_wrong_size = el_pick_too_big = el_pick_none = 0
    for t in eleven:
        r = rp_run.get(t["id"])
        p = r["pick"] if r is not None else None
        if p is None:
            el_pick_none += 1
            continue
        if p == t["grid"]:
            el_pick_exact += 1
        if nrows(p) != nrows(t["grid"]):
            el_pick_wrong_size += 1
        if nrows(p) > nrows(t["grid"]):
            el_pick_too_big += 1
    out("replay.set.pick_exact", el_pick_exact)
    out("replay.set.pick_none", el_pick_none)
    out("replay.set.pick_still_wrong_size", el_pick_wrong_size)
    out("replay.set.pick_still_too_big", el_pick_too_big)

    rp_greedy_exact = sum(
        1 for t in g7_truth
        if rp_run.get(t["id"]) is not None and rp_run[t["id"]]["greedy"] is not None
        and rp_run[t["id"]]["greedy"] == t["grid"]
    )
    rp_pick_exact = sum(
        1 for t in g7_truth
        if rp_run.get(t["id"]) is not None and rp_run[t["id"]]["pick"] is not None
        and rp_run[t["id"]]["pick"] == t["grid"]
    )
    out("replay.all.greedy_exact", rp_greedy_exact)
    out("replay.all.pick_exact", rp_pick_exact)

    # 5. Fixed and harmed, fresh squares + fresh unseen.
    sq_fixed, sq_harmed = fixed_harmed(sq_truth, sq_run)
    un_fixed, un_harmed = fixed_harmed(un_truth, un_run)
    out("fresh.squares.fixed", sq_fixed)
    out("fresh.squares.harmed", sq_harmed)
    out("fresh.unseen.fixed", un_fixed)
    out("fresh.unseen.harmed", un_harmed)
    out("fresh.both.fixed", sq_fixed + un_fixed)
    out("fresh.both.harmed", sq_harmed + un_harmed)

    # 6. Marks and outcome.
    p_mark = el_pick_wrong_size <= 3
    proved_wrong = el_pick_too_big >= 6
    gw = un_greedy["wrong"]
    pw = un_pick["wrong"]
    if gw < 8:
        d1 = "too_few"
    else:
        d1 = pw * 2 <= gw
    d2 = sq_pick["exact"] >= sq_greedy_exact
    d3 = lk_pick_nonnull <= lk_greedy_nonnull
    d4 = (sq_harmed + un_harmed) <= 2

    out("mark.R0", r0)
    out("mark.P", p_mark)
    out("mark.D1", d1)
    out("mark.D2", d2)
    out("mark.D3", d3)
    out("mark.D4", d4)
    out("proved_wrong", proved_wrong)

    if not r0:
        outcome = "MISMATCH"
    elif proved_wrong:
        outcome = "PROVED-WRONG"
    elif d1 == "too_few":
        outcome = "TOO-FEW"
    elif r0 and p_mark and d1 is True and d2 and d3 and d4:
        outcome = "DEV-PASS"
    else:
        outcome = "DEV-FAIL"
    out("outcome", outcome)


if __name__ == "__main__":
    main()
