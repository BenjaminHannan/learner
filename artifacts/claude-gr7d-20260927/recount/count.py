"""Separate recount for gr-7d (practice diagnosis), written from PLAN-gr7d.md's definitions.

Reads only the practice set and the run readings. Imports nothing from scripts/.
Run from the repo root:  python3 -B artifacts/claude-gr7d-20260927/recount/count.py
Prints only "name value" lines.
"""
import json
import os

BASE = os.path.join("artifacts", "claude-gr7d-20260927")
TASKS = ["squares", "unseen", "lookalikes"]
ARMS = ["L7", "G5"]


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def tok(v):
    return "_" if v == 0 else str(v)


def row_tokens(row):
    return [tok(v) for v in row]


def text_tokens(text, cell_idx):
    """T: every digit or '_' character in order, with a flag for cell tokens."""
    T, is_cell = [], []
    for i, ch in enumerate(text):
        if ch == "_" or ch.isdigit():
            T.append(ch)
            is_cell.append(i in cell_idx)
    return T, is_cell


def run_positions(T, r):
    """Start positions where tokens r occur as a contiguous exact run of T."""
    n = len(r)
    if n == 0:
        return []
    return [p for p in range(len(T) - n + 1) if T[p:p + n] == r]


def within_one(a, b):
    return len(a) == len(b) and sum(1 for x, y in zip(a, b) if x != y) <= 1


def is_far(r, truth_rows):
    return not any(within_one(r, t) for t in truth_rows if len(t) == len(r))


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(b)]


def wrong_kind(out_grid, truth_grid, T, is_cell):
    out_rows = [row_tokens(r) for r in out_grid]
    truth_rows = [row_tokens(r) for r in truth_grid]
    far = [r for r in out_rows if is_far(r, truth_rows)]
    for r in far:
        for p in run_positions(T, r):
            if any(not is_cell[q] for q in range(p, p + len(r))):
                return "A"
    flat_out = [x for r in out_rows for x in r]
    flat_truth = [x for r in truth_rows for x in r]
    if len(far) <= 1 or levenshtein(flat_out, flat_truth) <= 2:
        return "B"
    return "C"


def false_kind(out_grid, T):
    out_rows = [row_tokens(r) for r in out_grid]
    missing = sum(1 for r in out_rows if not run_positions(T, r))
    return "A" if missing <= 1 else "C"


def same_size(out_grid, n):
    return len(out_grid) == n and all(len(r) == n for r in out_grid)


def same_shape(out_grid, shape):
    rows, cols = shape
    return len(out_grid) == rows and all(len(r) == cols for r in out_grid)


def b(x):
    return "true" if x else "false"


def share(k, n):
    return "%.3f" % (k / n) if n else "nan"


def main():
    out = []

    def emit(name, value):
        out.append("%s %s" % (name, value))

    practice = {t: load(os.path.join(BASE, "practice", t + ".jsonl")) for t in TASKS}
    runs = {(a, t): load(os.path.join(BASE, "run", "%s_%s.jsonl" % (a, t))) for a in ARMS for t in TASKS}

    # ---- 1. checks
    for t in TASKS:
        emit("rows_practice_%s" % t, len(practice[t]))
    for a in ARMS:
        for t in TASKS:
            emit("rows_%s_%s" % (a, t), len(runs[(a, t)]))
    for t in TASKS:
        ids = [r["id"] for r in practice[t]]
        emit("dup_ids_practice_%s" % t, len(ids) - len(set(ids)))
    for a in ARMS:
        for t in TASKS:
            rids = [r["id"] for r in runs[(a, t)]]
            pids = [r["id"] for r in practice[t]]
            emit("dup_ids_%s_%s" % (a, t), len(rids) - len(set(rids)))
            ok = (set(rids) == set(pids) and len(rids) == len(set(rids)) and len(pids) == len(set(pids)))
            emit("ids_match_%s_%s" % (a, t), b(ok))
    for a in ARMS:
        emit("complete_false_%s" % a, sum(1 for t in TASKS for r in runs[(a, t)] if r.get("complete") is not True))
    # the maker's cell positions point at the truth grid's own tokens, one per cell
    cells_ok = True
    for t in ("squares", "unseen"):
        for r in practice[t]:
            n, g, text = r["size"], r["grid"], r["text"]
            seen = set()
            for idx, i, j in r["cells"]:
                if not (0 <= idx < len(text)) or text[idx] != tok(g[i][j]):
                    cells_ok = False
                seen.add((i, j))
            if len(r["cells"]) != n * n or len(seen) != n * n or len(g) != n or any(len(x) != n for x in g):
                cells_ok = False
    emit("cells_match_text", b(cells_ok))
    emit("lookalike_square_all_null", b(all(r.get("square") is None for r in practice["lookalikes"])))

    # ---- 2-5. counts
    totals = {}
    for a in ARMS:
        wrong = {"A": 0, "B": 0, "C": 0}
        size_split = {}
        groups = [("squares", "squares", None), ("unseen_sepseen", "unseen", True), ("unseen_sepnew", "unseen", False)]
        for label, t, sep in groups:
            truth = {r["id"]: r for r in practice[t]}
            c = {"exact": 0, "none": 0, "A": 0, "B": 0, "C": 0}
            ss = {"same": 0, "other": 0}
            n_rows = 0
            for rd in runs[(a, t)]:
                tr = truth.get(rd["id"])
                if tr is None:
                    continue
                if sep is not None and tr["sep_seen"] is not sep:
                    continue
                n_rows += 1
                g = rd["grid"]
                if g is None:
                    c["none"] += 1
                elif g == tr["grid"]:
                    c["exact"] += 1
                else:
                    T, is_cell = text_tokens(tr["text"], {x[0] for x in tr["cells"]})
                    k = wrong_kind(g, tr["grid"], T, is_cell)
                    c[k] += 1
                    wrong[k] += 1
                    ss["same" if same_size(g, tr["size"]) else "other"] += 1
            emit("%s_%s_rows" % (a, label), n_rows)
            emit("%s_%s_exact" % (a, label), c["exact"])
            emit("%s_%s_none" % (a, label), c["none"])
            for k in "ABC":
                emit("%s_%s_wrong_%s" % (a, label, k), c[k])
            size_split[label] = ss
        wt = sum(wrong.values())
        totals[a] = (wt, wrong)
        emit("%s_wrong_total" % a, wt)
        for k in "ABC":
            emit("%s_wrong_%s" % (a, k), wrong[k])
        emit("%s_wrong_A_share" % a, share(wrong["A"], wt))
        emit("%s_wrong_B_share" % a, share(wrong["B"], wt))

        # lookalikes
        fk = {}
        f_total, f_same = 0, 0
        f_by = {"A": 0, "C": 0}
        for kind in ("near", "nonsquare", "numbers"):
            fk[kind] = {"A": 0, "C": 0, "same": 0}
        truth = {r["id"]: r for r in practice["lookalikes"]}
        for rd in runs[(a, "lookalikes")]:
            tr = truth.get(rd["id"])
            if tr is None or rd["grid"] is None:
                continue
            T, _ = text_tokens(tr["text"], set())
            k = false_kind(rd["grid"], T)
            kind = tr["kind"]
            fk.setdefault(kind, {"A": 0, "C": 0, "same": 0})
            fk[kind][k] += 1
            f_by[k] += 1
            f_total += 1
            if same_shape(rd["grid"], tr["shape"]):
                fk[kind]["same"] += 1
                f_same += 1
        emit("%s_false_total" % a, f_total)
        emit("%s_false_A" % a, f_by["A"])
        emit("%s_false_C" % a, f_by["C"])
        for kind in fk:
            emit("%s_false_%s_A" % (a, kind), fk[kind]["A"])
            emit("%s_false_%s_C" % (a, kind), fk[kind]["C"])
            emit("%s_false_%s_same_shape" % (a, kind), fk[kind]["same"])
        emit("%s_false_same_shape" % a, f_same)
        emit("%s_false_other_shape" % a, f_total - f_same)
        # pooled (report only, per the plan): wrong grids + false squares
        emit("%s_pooled_bad_total" % a, wt + f_total)
        emit("%s_pooled_A" % a, wrong["A"] + f_by["A"])
        emit("%s_pooled_B" % a, wrong["B"])
        emit("%s_pooled_C" % a, wrong["C"] + f_by["C"])
        emit("%s_pooled_A_share" % a, share(wrong["A"] + f_by["A"], wt + f_total))

        for label in ("squares", "unseen_sepseen", "unseen_sepnew"):
            emit("%s_wrong_samesize_%s" % (a, label), size_split[label]["same"])
            emit("%s_wrong_othersize_%s" % (a, label), size_split[label]["other"])

    # ---- 6. decision (L7)
    wt, wrong = totals["L7"]
    emit("distractor_block_SUNK", b(wrong["A"] * 3 < wt and wt >= 10))
    emit("too_few", b(wt < 10))
    emit("lost_place_proved_wrong", b(wrong["B"] * 2 < wt))

    print("\n".join(out))


if __name__ == "__main__":
    main()
