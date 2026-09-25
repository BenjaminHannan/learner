#!/usr/bin/env python3
"""rv-385 count: re-checks every result from the raw files (thought-memory thread, 2026-09-25).

Reads <dir>/puzzles-seed<S>.jsonl and <dir>/<arm>-seed<S>.jsonl, re-checks each "solved" final grid against the
puzzle from scratch, and prints per seed and arm: grids solved, steps, and two report-only numbers:
  first_right : share of first choices at a newly reached cell that match the grid's unique solution
  note_repeat : in revert_note, share of choices made at a state with notes that repeat a number already noted
                there, against the share blind guessing would give (noted numbers / grid size)

  python -B scripts/claude_rv385_count.py DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ARMS = ["restart", "revert_ban", "revert_note"]


def full_ok(puz, g):
    s = len(puz)
    full = set(range(1, s + 1))
    if any(puz[r][c] and puz[r][c] != g[r][c] for r in range(s) for c in range(s)):
        return False
    return all(set(g[r]) == full for r in range(s)) and all({g[r][c] for r in range(s)} == full for c in range(s))


def replay_notes(res, puz):
    """walk the log to get, for every choice, the numbers already noted at that state (revert_note only)."""
    s = len(puz)
    noted = {}                      # position -> set of noted numbers
    rep = chance = n = 0
    for pos, v, _p, what in res["log"]:
        if what == "back":          # pos is the state we went back to; the popped number is noted there
            for j in [k for k in noted if k > pos]:
                noted.pop(j)
            noted.setdefault(pos, set()).add(v)
            continue
        ns = noted.get(pos, set())
        if ns:
            n += 1
            rep += v in ns
            chance += len(ns) / s
        if what == "conflict":
            noted.setdefault(pos, set()).add(v)
        else:                       # moved forward: states beyond are new
            for j in [k for k in noted if k > pos]:
                noted.pop(j)
    return rep, chance, n


def main():
    d = Path(sys.argv[1])
    table = {}
    for pf in sorted(d.glob("puzzles-seed*.jsonl")):
        seed = pf.stem.split("seed")[1]
        puzzles = {p["pid"]: p for p in map(json.loads, pf.read_text().splitlines())}
        for arm in ARMS:
            f = d / f"{arm}-seed{seed}.jsonl"
            if not f.exists():
                continue
            rows = [json.loads(x) for x in f.read_text().splitlines()]
            assert {r["pid"] for r in rows} == set(puzzles), f"{f}: puzzle set differs"
            solved = 0
            first = first_ok = 0
            rep = chance = nrep = 0
            for r in rows:
                p = puzzles[r["pid"]]
                ok = full_ok(p["puz"], r["final"])
                if r["solved"] != ok:
                    raise SystemExit(f"MISMATCH {f} {r['pid']}: reported {r['solved']}, re-check {ok}")
                solved += ok
                cells = [(i, j) for i in range(p["size"]) for j in range(p["size"]) if p["puz"][i][j] == 0]
                seen = set()
                for pos, v, _p, what in r["log"]:
                    if what == "back":
                        continue
                    key = pos
                    if key not in seen:
                        seen.add(key)
                        first += 1
                        i, j = cells[pos]
                        first_ok += v == p["sol"][i][j]
                if arm == "revert_note":
                    a, b, c = replay_notes(r, p["puz"])
                    rep, chance, nrep = rep + a, chance + b, nrep + c
            row = {"solved": solved, "n": len(rows), "steps": sum(r["steps"] for r in rows),
                   "first_right": round(first_ok / max(first, 1), 3)}
            if arm == "revert_note":
                row["note_repeat"] = round(rep / max(nrep, 1), 3)
                row["note_repeat_chance"] = round(chance / max(nrep, 1), 3)
                row["note_choices"] = nrep
            table[(seed, arm)] = row
            print(json.dumps({"seed": seed, "arm": arm, **row}))
    return table


if __name__ == "__main__":
    main()
