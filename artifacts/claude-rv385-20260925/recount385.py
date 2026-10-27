#!/usr/bin/env python3
"""Independent blind recount of rv-385 from the raw run files (standard library only).

Written from PASSMARKS.md and the file format alone; does not use scripts/claude_rv385_count.py.
"""
import json
import random
import sys
from pathlib import Path

REPO = Path("/home/user/learner")
RUN = REPO / "artifacts/claude-rv385-20260925/run"
SEEDS = [385101, 385202]
ARMS = ["restart", "revert_ban", "revert_note"]
N, S, BUDGET = 80, 5, 60


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def is_latin_complete(g):
    full = set(range(1, S + 1))
    if len(g) != S or any(len(r) != S for r in g):
        return False
    for r in range(S):
        if sorted(g[r]) != sorted(full) or set(g[r]) != full:
            return False
    for c in range(S):
        col = [g[r][c] for r in range(S)]
        if sorted(col) != [1, 2, 3, 4, 5]:
            return False
    return True


def keeps_givens(final, puz):
    return all(puz[r][c] == 0 or final[r][c] == puz[r][c] for r in range(S) for c in range(S))


def my_solution_count(puz, limit=2):
    """Own backtracking counter on a 1..5 grid with 0 for blanks."""
    g = [row[:] for row in puz]
    for r in range(S):
        vals = [v for v in g[r] if v]
        if len(vals) != len(set(vals)):
            return 0
    for c in range(S):
        vals = [g[r][c] for r in range(S) if g[r][c]]
        if len(vals) != len(set(vals)):
            return 0
    empties = [(r, c) for r in range(S) for c in range(S) if g[r][c] == 0]
    count = 0

    def rec(i):
        nonlocal count
        if count >= limit:
            return
        if i == len(empties):
            count += 1
            return
        r, c = empties[i]
        used = set(g[r]) | {g[k][c] for k in range(S)}
        for v in range(1, S + 1):
            if v not in used:
                g[r][c] = v
                rec(i + 1)
                g[r][c] = 0

    rec(0)
    return count


def blank_cells(puz):
    return [(r, c) for r in range(S) for c in range(S) if puz[r][c] == 0]


def replay(row, puz, arm):
    """Replay the log against the puzzle. Returns (problems list, reconstructed grid)."""
    probs = []
    cells = blank_cells(puz)
    filled = []  # numbers at blank positions 0..len-1 (the state is always a prefix in row-major order)

    def grid():
        g = [r[:] for r in puz]
        for i, v in enumerate(filled):
            r, c = cells[i]
            g[r][c] = v
        return g

    for k, (p, n, prob, out) in enumerate(row["log"]):
        if out == "back":
            if arm == "restart":
                probs.append(f"back row in restart at {k}")
            if not (len(filled) >= 1 and p == len(filled) - 1 and filled[p] == n):
                probs.append(f"back mismatch at {k}: p={p} n={n} filled={filled}")
            filled = filled[:p]
            continue
        if out not in ("ok", "conflict"):
            probs.append(f"unknown outcome {out} at {k}")
            continue
        if p != len(filled):
            probs.append(f"choice at p={p} but state prefix len={len(filled)} at {k}")
            filled = filled[:p]
        if not (1 <= n <= S):
            probs.append(f"number out of range at {k}")
        g = grid()
        r, c = cells[p]
        clash = n in g[r] or n in [g[i][c] for i in range(S)]
        if clash and out == "ok":
            probs.append(f"ok but clashes at {k}")
        if not clash and out == "conflict":
            probs.append(f"conflict but no clash at {k}")
        if out == "ok":
            filled.append(n)
        elif arm == "restart":
            filled = []  # restart wipes everything the model wrote
    return probs, grid(), len(filled)


def noted_walk(log):
    """Item 5 bookkeeping. Returns (choices with non-empty noted set, repeats, baseline sum)."""
    noted = {}
    choices = repeats = 0
    base = 0.0
    for p, n, prob, out in log:
        if out == "back":
            noted.setdefault(p, set()).add(n)
            for q in [q for q in noted if q > p]:
                del noted[q]
            continue
        cur = noted.get(p, set())
        if cur:
            choices += 1
            repeats += n in cur
            base += len(cur) / S
        if out == "conflict":
            noted.setdefault(p, set()).add(n)
        elif out == "ok":
            for q in [q for q in noted if q > p]:
                del noted[q]
    return choices, repeats, base


def seal_check(seed, puzzles):
    sys.path.insert(0, str(REPO / "scripts"))
    import claude_rsn358a_envs as E
    rng = random.Random(seed)
    match = 0
    first_bad = None
    for i in range(N):
        sol, puz = E.make_latin_base(rng, S)
        sol1 = [[v + 1 for v in r] for r in sol]
        puz1 = [[v + 1 if v >= 0 else 0 for v in r] for r in puz]
        pr = puzzles[i]
        ok = pr["sol"] == sol1 and pr["puz"] == puz1 and pr["pid"] == f"{seed}-{i}"
        match += ok
        if not ok and first_bad is None:
            first_bad = i
    return match, first_bad


def main():
    out = {}
    for seed in SEEDS:
        puzzles = load(RUN / f"puzzles-seed{seed}.jsonl")
        pmap = {p["pid"]: p for p in puzzles}
        pz = {
            "n": len(puzzles),
            "distinct_pids": len(pmap),
            "sol_valid": sum(is_latin_complete(p["sol"]) and keeps_givens(p["sol"], p["puz"]) for p in puzzles),
            "unique": sum(my_solution_count(p["puz"]) == 1 for p in puzzles),
            "size5": sum(p["size"] == S for p in puzzles),
        }
        pz["seal_match"], pz["seal_first_bad"] = seal_check(seed, puzzles)
        seed_out = {"puzzles": pz, "arms": {}}
        pid_sets = {}
        for arm in ARMS:
            rows = load(RUN / f"{arm}-seed{seed}.jsonl")
            pid_sets[arm] = [r["pid"] for r in rows]
            a = {
                "rows": len(rows),
                "distinct_pids": len(set(r["pid"] for r in rows)),
                "arm_field_ok": sum(r["arm"] == arm for r in rows),
                "pids_in_file": sum(r["pid"] in pmap for r in rows),
                "same_order_as_file": [r["pid"] for r in rows] == [p["pid"] for p in puzzles],
                "size_ok": 0, "blanks_ok": 0, "givens_kept": 0,
                "solved_mine": 0, "solved_flag": 0, "flag_disagree": 0, "solved_eq_sol": 0,
                "max_steps": 0, "steps_eq_nonback": 0, "total_steps": 0, "over_budget": 0,
                "replay_clean": 0, "replay_final_match": 0, "replay_problems": [],
                "backs": 0,
            }
            ban_choices = ban_hits = 0
            ban_base = 0.0
            for r in rows:
                p = pmap.get(r["pid"])
                if p is None:
                    continue
                a["size_ok"] += r["size"] == p["size"] == S
                nb = sum(v == 0 for row in p["puz"] for v in row)
                a["blanks_ok"] += r["blanks"] == nb
                gk = keeps_givens(r["final"], p["puz"])
                a["givens_kept"] += gk
                mine = gk and is_latin_complete(r["final"])
                a["solved_mine"] += mine
                a["solved_flag"] += bool(r["solved"])
                a["flag_disagree"] += bool(r["solved"]) != mine
                a["solved_eq_sol"] += mine and r["final"] == p["sol"]
                nonback = sum(1 for e in r["log"] if e[3] != "back")
                a["backs"] += sum(1 for e in r["log"] if e[3] == "back")
                a["steps_eq_nonback"] += r["steps"] == nonback
                a["max_steps"] = max(a["max_steps"], r["steps"])
                a["total_steps"] += r["steps"]
                a["over_budget"] += r["steps"] > BUDGET or nonback > BUDGET
                probs, g, nf = replay(r, p["puz"], arm)
                a["replay_clean"] += not probs
                a["replay_final_match"] += g == r["final"]
                if probs:
                    a["replay_problems"].append((r["pid"], probs[:3]))
                if arm in ("revert_note", "revert_ban"):
                    c, h, b = noted_walk(r["log"])
                    ban_choices += c
                    ban_hits += h
                    ban_base += b
            if arm in ("revert_note", "revert_ban"):
                a["noted_choices"] = ban_choices
                a["noted_repeats"] = ban_hits
                a["repeat_share"] = ban_hits / ban_choices if ban_choices else None
                a["baseline"] = ban_base / ban_choices if ban_choices else None
            seed_out["arms"][arm] = a
        sets = {arm: frozenset(v) for arm, v in pid_sets.items()}
        seed_out["same_pids_all_arms"] = len(set(sets.values())) == 1 and len(sets["restart"]) == N
        seed_out["pids_equal_puzzle_file"] = all(s == frozenset(pmap) for s in sets.values())
        out[seed] = seed_out
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
