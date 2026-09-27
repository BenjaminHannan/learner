#!/usr/bin/env python3
"""Blind recount of gr-5 (independent of the claude_gr*.py scripts and the score file).

Reads only: PASSMARKS-gr5.md / ADDENDUM-gr5-1.md definitions (written into this code by hand), the panel
(artifacts/claude-panel-gr5-20260926/{squares,lookalikes,unseen}.jsonl), the run files
(artifacts/claude-gr5-20260926/run/{L,P0}_{squares,lookalikes,unseen}.jsonl, run/L_general.jsonl) and the last line of
run/logs/devclean.log. Imports only scripts/claude_puzzle_reader.py (read_latin, arm C) and
scripts/claude_dl1_nights.py (harm_panel, the 300 general items), with their stdout/stderr silenced.

Prints only integers and true/false, one "name value" per line. Never prints message text or grids.
Run from the repo root: python3 -B artifacts/claude-gr5-20260926/recount/count.py
"""
import contextlib
import io
import json
import sys

sys.dont_write_bytecode = True

ROOT = "/home/user/learner"
PANEL = ROOT + "/artifacts/claude-panel-gr5-20260926"
RUN = ROOT + "/artifacts/claude-gr5-20260926/run"
DEVCLEAN = RUN + "/logs/devclean.log"

sys.path.insert(0, ROOT + "/scripts")
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import claude_puzzle_reader as PR  # noqa: E402
    import claude_dl1_nights as DL  # noqa: E402


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a)


def read_latin_grid(text):
    out = quiet(PR.read_latin, text)
    return None if out is None else norm(out["grid"])


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def norm(g):
    if g is None:
        return None
    return tuple(tuple(int(v) for v in row) for row in g)


def tf(b):
    return "true" if b else "false"


LINES = []


def out(name, value):
    if isinstance(value, bool):
        value = tf(value)
    else:
        value = int(value)
    LINES.append(f"{name} {value}")


def classify(read, truth):
    if read is None:
        return "none"
    return "exact" if read == truth else "wrong"


def side(g):
    return len(g)


def is_square_shape(g):
    return all(len(r) == len(g) for r in g)


def valid_partial_latin(g):
    n = len(g)
    if not is_square_shape(g):
        return False
    for r in g:
        if any(not (v == 0 or 1 <= v <= n) for v in r):
            return False
    for i in range(n):
        row = [v for v in g[i] if v]
        col = [g[j][i] for j in range(n) if g[j][i]]
        if len(row) != len(set(row)) or len(col) != len(set(col)):
            return False
    return True


# ---------------------------------------------------------------- load
panel = {t: load(f"{PANEL}/{t}.jsonl") for t in ("squares", "lookalikes", "unseen")}
runs = {}
for arm in ("L", "P0"):
    for t in ("squares", "lookalikes", "unseen"):
        runs[(arm, t)] = load(f"{RUN}/{arm}_{t}.jsonl")
runs[("L", "general")] = load(f"{RUN}/L_general.jsonl")

# ---------------------------------------------------------------- 1. checks
for t in ("squares", "lookalikes", "unseen"):
    ids = [r["id"] for r in panel[t]]
    out(f"rows_panel_{t}", len(panel[t]))
    out(f"dup_ids_panel_{t}", len(ids) - len(set(ids)))
for (arm, t), rows in runs.items():
    out(f"rows_run_{arm}_{t}", len(rows))
for (arm, t), rows in runs.items():
    ids = [r["id"] for r in rows]
    out(f"dup_ids_run_{arm}_{t}", len(ids) - len(set(ids)))
    if t == "general":
        want = {f"gen-{i:03d}" for i in range(300)}  # general rows carry ids gen-000 .. gen-299
    else:
        want = {r["id"] for r in panel[t]}
    out(f"ids_match_{arm}_{t}", set(ids) == want and len(ids) == len(set(ids)))
out("general_rows_is_300", len(runs[("L", "general")]) == 300)
for arm in ("L", "P0"):
    tot = 0
    for (a, t), rows in runs.items():
        if a != arm:
            continue
        n = sum(1 for r in rows if r.get("complete") is not True)
        out(f"incomplete_{arm}_{t}", n)
        tot += n
    out(f"incomplete_{arm}_total", tot)

# readings by arm, task, id
reads = {}
for (arm, t), rows in runs.items():
    reads[(arm, t)] = {r["id"]: norm(r["grid"]) for r in rows}
for t in ("squares", "lookalikes", "unseen"):
    reads[("C", t)] = {r["id"]: read_latin_grid(r["text"]) for r in panel[t]}
truth = {t: {r["id"]: norm(r["grid"]) for r in panel[t]} for t in ("squares", "unseen")}
truth["lookalikes"] = {r["id"]: norm(r["square"]) for r in panel["lookalikes"]}

# ---------------------------------------------------------------- 2. squares and unseen
res = {}
for t in ("squares", "unseen"):
    for arm in ("L", "P0", "C"):
        c = {"exact": 0, "wrong": 0, "none": 0, "missing": 0}
        by_size = {s: 0 for s in (4, 5, 6, 7)}
        for r in panel[t]:
            rd = reads[(arm, t)]
            if r["id"] not in rd:
                c["missing"] += 1
                continue
            k = classify(rd[r["id"]], truth[t][r["id"]])
            c[k] += 1
            if k == "exact":
                by_size[r["size"]] = by_size.get(r["size"], 0) + 1
        res[(arm, t)] = c
        for k in ("exact", "wrong", "none", "missing"):
            out(f"{t}_{arm}_{k}", c[k])
        for s in sorted(by_size):
            out(f"{t}_{arm}_exact_size{s}", by_size[s])
    for s in (4, 5, 6, 7):
        out(f"{t}_panel_n_size{s}", sum(1 for r in panel[t] if r["size"] == s))

# ---------------------------------------------------------------- 3. lookalikes
look_none = [r["id"] for r in panel["lookalikes"] if r["square"] is None]
look_sq = [r["id"] for r in panel["lookalikes"] if r["square"] is not None]
out("lookalikes_truth_none", len(look_none))
out("lookalikes_truth_square", len(look_sq))
false_sq = {}
for arm in ("L", "P0", "C"):
    rd = reads[(arm, "lookalikes")]
    false_sq[arm] = sum(1 for i in look_none if rd.get(i) is not None)
    out(f"lookalikes_false_squares_{arm}", false_sq[arm])
    out(f"lookalikes_read_as_square_all_{arm}", sum(1 for i in rd if rd[i] is not None))

# ---------------------------------------------------------------- 4. general
gen_L = sum(1 for r in runs[("L", "general")] if r["grid"] is not None)
items = quiet(DL.harm_panel)
gen_C = sum(1 for it in items if quiet(PR.read_latin, it["q"]) is not None)
out("general_items_n", len(items))
out("general_read_as_square_L", gen_L)
out("general_read_as_square_C", gen_C)

# ---------------------------------------------------------------- 5. marks (L)
R1 = res[("L", "squares")]["exact"] >= 97
R2 = false_sq["L"] <= 1
R3 = res[("L", "squares")]["wrong"] <= 1
R4 = gen_L == 0
U1 = res[("L", "unseen")]["exact"] >= 48
U2 = res[("L", "unseen")]["wrong"] <= 2
for name, v in (("R1", R1), ("R2", R2), ("R3", R3), ("R4", R4), ("U1", U1), ("U2", U2)):
    out(f"mark_{name}", v)
out("gr5_pass", R1 and R2 and R3 and R4)
out("gr5U_pass", U1 and U2)

# ---------------------------------------------------------------- 6. addendum-1 line 1
rl_text = reads[("C", "lookalikes")]
agree = sum(1 for i in look_sq if rl_text[i] == truth["lookalikes"][i])
out("addendum1_readlatin_agrees_stored_truth_n", agree)
out("addendum1_readlatin_agrees_stored_truth_all", agree == len(look_sq))
for arm in ("L", "P0"):
    rd = reads[(arm, "lookalikes")]
    out(f"addendum1_{arm}_read_as_square", sum(1 for i in look_sq if rd.get(i) is not None))
    out(f"addendum1_{arm}_same_as_readlatin_on_text", sum(1 for i in look_sq if rd.get(i) is not None
                                                          and rd.get(i) == rl_text[i]))
    out(f"addendum1_{arm}_same_as_stored_truth", sum(1 for i in look_sq if rd.get(i) is not None
                                                     and rd.get(i) == truth["lookalikes"][i]))
    out(f"addendum1_{arm}_read_as_none", sum(1 for i in look_sq if i in rd and rd[i] is None))

# ---------------------------------------------------------------- 7. extra report-only integers
rdL = reads[("L", "lookalikes")]
fl = [i for i in look_none if rdL.get(i) is not None]
out("lookalike_false_L_n", len(fl))
for k, i in enumerate(fl, 1):
    g = rdL[i]
    out(f"lookalike_false_L_size_{k}", side(g))
    out(f"lookalike_false_L_square_shape_{k}", is_square_shape(g))
    out(f"lookalike_false_L_blanks_{k}", sum(1 for row in g for v in row if v == 0))
    out(f"lookalike_false_L_valid_partial_latin_{k}", valid_partial_latin(g))

for t in ("unseen", "squares"):
    rd = reads[("L", t)]
    same = smaller = larger = diff_total = diff_max = nonsquare = 0
    for r in panel[t]:
        g, tr = rd.get(r["id"]), truth[t][r["id"]]
        if g is None or g == tr:
            continue
        if not is_square_shape(g):
            nonsquare += 1
        if side(g) == side(tr) and is_square_shape(g):
            same += 1
            d = sum(1 for a in range(len(tr)) for b in range(len(tr)) if g[a][b] != tr[a][b])
            diff_total += d
            diff_max = max(diff_max, d)
        elif side(g) < side(tr):
            smaller += 1
        else:
            larger += 1
    out(f"{t}_L_wrong_same_size", same)
    out(f"{t}_L_wrong_smaller", smaller)
    out(f"{t}_L_wrong_larger", larger)
    out(f"{t}_L_wrong_nonsquare_shape", nonsquare)
    out(f"{t}_L_wrong_same_size_cells_differ_total", diff_total)
    out(f"{t}_L_wrong_same_size_cells_differ_max", diff_max)

rdU = reads[("L", "unseen")]
for b in (True, False):
    sub = [r for r in panel["unseen"] if r["broken"] is b]
    out(f"unseen_broken_{tf(b)}_n", len(sub))
    out(f"unseen_L_none_broken_{tf(b)}", sum(1 for r in sub if r["id"] in rdU and rdU[r["id"]] is None))
    out(f"unseen_L_exact_broken_{tf(b)}",
        sum(1 for r in sub if classify(rdU.get(r["id"]), truth["unseen"][r["id"]]) == "exact" and r["id"] in rdU))

if all("token_clash" in r for r in panel["unseen"]):
    sub = [r for r in panel["unseen"] if r["token_clash"] is True]
    out("unseen_token_clash_true_n", len(sub))
    for k in ("exact", "wrong", "none"):
        out(f"unseen_L_{k}_token_clash_true",
            sum(1 for r in sub if r["id"] in rdU and classify(rdU[r["id"]], truth["unseen"][r["id"]]) == k))

# ---------------------------------------------------------------- 8. devclean.log last line
with open(DEVCLEAN) as f:
    last = [line for line in f.read().splitlines() if line.strip()][-1]
for k, v in json.loads(last).items():
    out(f"devclean_{k}", v)

print("\n".join(LINES))
