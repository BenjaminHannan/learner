#!/usr/bin/env python3
"""Blind recount of gr-7 (L7 vs G5 vs C=read_latin) on the gr-6 panel.

Written independently. Reads only: the panel files, the gr-7 run files, the last line of run/logs/dev.log,
and imports only scripts/claude_puzzle_reader.read_latin and scripts/claude_dl1_nights.harm_panel.
Prints only "name value" lines whose values are integers, numbers from dev.log, or true/false.
Never prints message text or grids.
"""
import contextlib
import io
import json
import os
import sys

ROOT = "/home/user/learner"
PANEL = ROOT + "/artifacts/claude-panel-gr6-20260927"
RUN = ROOT + "/artifacts/claude-gr7-20260927/run"
DEVLOG = RUN + "/logs/dev.log"

TASKS = ["squares", "lookalikes", "unseen"]
MODEL_ARMS = ["L7", "G5"]


def out(name, value):
    if isinstance(value, bool):
        value = "true" if value else "false"
    print(f"{name} {value}")


@contextlib.contextmanager
def silenced():
    """Silence Python-level and fd-level stdout/stderr."""
    sys.stdout.flush()
    sys.stderr.flush()
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved_out, saved_err = os.dup(1), os.dup(2)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        os.close(devnull)


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def norm(grid):
    if grid is None:
        return None
    return [[int(v) for v in row] for row in grid]


def classify(read, truth):
    if read is None:
        return "none"
    return "exact" if read == truth else "wrong"


def side(grid):
    return len(grid)


def is_square_shape(grid):
    n = len(grid)
    return n > 0 and all(len(r) == n for r in grid)


# ---------------------------------------------------------------- imports (silenced)
sys.path.insert(0, ROOT + "/scripts")
with silenced():
    from claude_puzzle_reader import read_latin  # noqa: E402
    from claude_dl1_nights import harm_panel  # noqa: E402


def arm_c(text):
    with silenced():
        r = read_latin(text)
    if r is None:
        return None
    return norm(r["grid"])


# ---------------------------------------------------------------- load
panel = {t: load(f"{PANEL}/{t}.jsonl") for t in TASKS}
run = {(a, t): load(f"{RUN}/{a}_{t}.jsonl") for a in MODEL_ARMS for t in TASKS}
general = load(f"{RUN}/L7_general.jsonl")

# ---------------------------------------------------------------- 1. checks
for t in TASKS:
    out(f"panel_{t}_rows", len(panel[t]))
for a in MODEL_ARMS:
    for t in TASKS:
        out(f"run_{a}_{t}_rows", len(run[(a, t)]))
out("run_L7_general_rows", len(general))

all_ids_ok = True
for a in MODEL_ARMS:
    for t in TASKS:
        rids = [r["id"] for r in run[(a, t)]]
        pids = [p["id"] for p in panel[t]]
        no_dup = len(rids) == len(set(rids))
        same_set = set(rids) == set(pids)
        panel_no_dup = len(pids) == len(set(pids))
        out(f"ids_{a}_{t}_match_panel_set", same_set)
        out(f"ids_{a}_{t}_no_duplicates", no_dup)
        out(f"ids_panel_{t}_no_duplicates", panel_no_dup)
        all_ids_ok = all_ids_ok and same_set and no_dup and panel_no_dup
gids = [r["id"] for r in general]
out("L7_general_has_300_rows", len(general) == 300)
out("L7_general_ids_no_duplicates", len(gids) == len(set(gids)))
out("all_panel_ids_match", all_ids_ok)

for a in MODEL_ARMS:
    total = 0
    for t in TASKS:
        n = sum(1 for r in run[(a, t)] if r.get("complete") is False)
        out(f"incomplete_{a}_{t}", n)
        total += n
    if a == "L7":
        n = sum(1 for r in general if r.get("complete") is False)
        out("incomplete_L7_general", n)
        total += n
    out(f"incomplete_{a}_total", total)

# ---------------------------------------------------------------- readings keyed by id
reads = {}
for a in MODEL_ARMS:
    for t in TASKS:
        reads[(a, t)] = {r["id"]: norm(r.get("grid")) for r in run[(a, t)]}
for t in TASKS:
    reads[("C", t)] = {p["id"]: arm_c(p["text"]) for p in panel[t]}

ARMS = ["L7", "G5", "C"]
tally = {}

# ---------------------------------------------------------------- 2. squares and unseen
for t in ["squares", "unseen"]:
    rows = panel[t]
    out(f"{t}_n", len(rows))
    for s in range(4, 8):
        out(f"{t}_n_size{s}", sum(1 for p in rows if p["size"] == s))
    out(f"{t}_n_size_outside_4_7", sum(1 for p in rows if not 4 <= p["size"] <= 7))
    for a in ARMS:
        c = {"exact": 0, "wrong": 0, "none": 0}
        by_size = {s: 0 for s in range(4, 8)}
        for p in rows:
            k = classify(reads[(a, t)].get(p["id"]), norm(p["grid"]))
            c[k] += 1
            if k == "exact" and p["size"] in by_size:
                by_size[p["size"]] += 1
        tally[(a, t)] = c
        for k in ["exact", "wrong", "none"]:
            out(f"{a}_{t}_{k}", c[k])
        for s in range(4, 8):
            out(f"{a}_{t}_exact_size{s}", by_size[s])

# ---------------------------------------------------------------- 3. unseen by separator
for flag in [True, False]:
    tag = "sepseen" if flag else "sepunseen"
    rows = [p for p in panel["unseen"] if p["sep_seen"] is flag]
    out(f"unseen_{tag}_n", len(rows))
    for a in MODEL_ARMS:
        c = {"exact": 0, "wrong": 0, "none": 0}
        for p in rows:
            c[classify(reads[(a, "unseen")].get(p["id"]), norm(p["grid"]))] += 1
        for k in ["exact", "wrong", "none"]:
            out(f"{a}_unseen_{tag}_{k}", c[k])

# ---------------------------------------------------------------- 4. lookalikes: false squares
look = panel["lookalikes"]
look_none = [p for p in look if p["square"] is None]
look_sq = [p for p in look if p["square"] is not None]
out("lookalikes_truth_none", len(look_none))
out("lookalikes_truth_square", len(look_sq))
false_sq = {}
for a in ARMS:
    ids = [p["id"] for p in look_none if reads[(a, "lookalikes")].get(p["id"]) is not None]
    false_sq[a] = ids
    out(f"{a}_lookalikes_false_squares", len(ids))

# ---------------------------------------------------------------- 5. lookalikes that hold a square
for a in MODEL_ARMS:
    as_sq = same = none = 0
    for p in look_sq:
        g = reads[(a, "lookalikes")].get(p["id"])
        if g is None:
            none += 1
        else:
            as_sq += 1
            if g == norm(p["square"]):
                same += 1
    out(f"{a}_lookalikes_holding_square_read_as_square", as_sq)
    out(f"{a}_lookalikes_holding_square_same_as_truth", same)
    out(f"{a}_lookalikes_holding_square_read_none", none)
agree = sum(1 for p in look_sq if reads[("C", "lookalikes")].get(p["id"]) == norm(p["square"]))
out("C_lookalikes_holding_square_agree_with_stored", agree)
out("C_lookalikes_holding_square_all_agree", agree == len(look_sq))
agree_none = sum(1 for p in look_none if reads[("C", "lookalikes")].get(p["id"]) is None)
out("C_lookalikes_truth_none_agree_with_stored", agree_none)

# ---------------------------------------------------------------- 6. general items
out("L7_general_read_as_square", sum(1 for r in general if r.get("grid") is not None))
with silenced():
    items = harm_panel()
out("general_items_n", len(items))
out("C_general_read_as_square", sum(1 for it in items if arm_c(it["q"]) is not None))

# ---------------------------------------------------------------- 7. marks for L7
L7_sq = tally[("L7", "squares")]
L7_un = tally[("L7", "unseen")]
G5_un = tally[("G5", "unseen")]
L7_gen_sq = sum(1 for r in general if r.get("grid") is not None)
R1 = L7_sq["exact"] >= 97
R2 = len(false_sq["L7"]) <= 1
R3 = L7_sq["wrong"] <= 1
R4 = L7_gen_sq == 0 and len(general) == 300
U1 = L7_un["exact"] >= 48
U2 = L7_un["wrong"] <= 2
for name, v in [("R1", R1), ("R2", R2), ("R3", R3), ("R4", R4), ("U1", U1), ("U2", U2)]:
    out(name, v)
out("gr7_pass", R1 and R2 and R3 and R4)
out("gr7U_pass", U1 and U2)
out("proved_wrong", not (L7_un["exact"] > G5_un["exact"]))
out("plus6", L7_un["exact"] >= G5_un["exact"] + 6)
out("L7_minus_G5_unseen_exact", L7_un["exact"] - G5_un["exact"])

# ---------------------------------------------------------------- 8. report-only: shapes of L7's errors
for t in ["squares", "unseen"]:
    same = smaller = larger = 0
    diff_cells = 0
    ragged = 0
    for p in panel[t]:
        truth = norm(p["grid"])
        g = reads[("L7", t)].get(p["id"])
        if classify(g, truth) != "wrong":
            continue
        if not is_square_shape(g):
            ragged += 1
        if side(g) == side(truth):
            same += 1
            for i in range(side(truth)):
                tr, gr = truth[i], g[i]
                for j in range(max(len(tr), len(gr))):
                    tv = tr[j] if j < len(tr) else None
                    gv = gr[j] if j < len(gr) else None
                    if tv != gv:
                        diff_cells += 1
        elif side(g) < side(truth):
            smaller += 1
        else:
            larger += 1
    out(f"L7_{t}_wrong_same_side", same)
    out(f"L7_{t}_wrong_smaller", smaller)
    out(f"L7_{t}_wrong_larger", larger)
    out(f"L7_{t}_wrong_not_square_shaped", ragged)
    out(f"L7_{t}_wrong_same_side_cells_differing", diff_cells)

sides = sorted(side(reads[("L7", "lookalikes")][i]) for i in false_sq["L7"])
out("L7_false_lookalike_count", len(sides))
for k, s in enumerate(sides, 1):
    out(f"L7_false_lookalike_{k}_side", s)
out("L7_false_lookalike_not_square_shaped",
    sum(1 for i in false_sq["L7"] if not is_square_shape(reads[("L7", "lookalikes")][i])))

# ---------------------------------------------------------------- 9. dev.log last line
with open(DEVLOG) as f:
    last = [line for line in f if line.strip()][-1]
dev = json.loads(last)
for k, v in dev.items():
    if k == "outcome":
        out("outcome_is_PASS", v == "PASS")
    elif k == "dev_gate":
        out("dev_gate_is_PASS", v == "PASS")
    elif isinstance(v, bool):
        out(f"dev_{k}", v)
    elif isinstance(v, (int, float)):
        out(f"dev_{k}", v)
