#!/usr/bin/env python3
"""bm-394: public puzzle tests for the reasoner line (benchmarks thread, 2026-09-25). New file only.

Two published small-model benchmarks, run the published way (exact whole-grid match, one try):
  Sudoku-Extreme  HF sapientinc/sudoku-extreme @58942f96, 9x9, 81 characters, "." = blank. Published test = all
                  422,786 test puzzles; here a seeded 10,000 sample (seed 394), so about +/-1 point.
  Maze-Hard       HF sapientinc/maze-30x30-hard-1k @549754de, 30x30, 900 characters: "#" wall, " " open, "S" start,
                  "G" goal; the answer marks the shortest path's cells with "o". Test = all 1,000 test mazes.
Published results (TRM paper, arXiv 2510.04871, Table 4; HRM and the others from the HRM paper), % exact:
  Sudoku-Extreme: HRM 27M 55.0, TRM-Att 7M 74.7, TRM-MLP 5M 87.4, direct prediction 27M 0.0, DeepSeek R1 0.0.
  Maze-Hard:      HRM 27M 74.5, TRM-Att 7M 85.3, direct prediction 27M 0.0, DeepSeek R1 0.0.
Their protocol: 1,000 training puzzles (Sudoku: 1,000 rule-keeping shuffles each; Maze: 8 rotations/flips each).
`fetch` writes a seeded 1,000-puzzle practice set from each train file for that protocol; the practice sets and
the test sets never share a puzzle (checked and printed). The hub files carry no licence tag; this is for
measurement, and nothing here trains.

  python -B scripts/claude_bm394_grid.py fetch --data DIR
  python -B scripts/claude_bm394_grid.py run   --data DIR --task sudoku|maze --arm SPEC --name NAME --out DIR [--limit N]
  python -B scripts/claude_bm394_grid.py score --data DIR --runs DIR [--pair A,B] [--out DIR]
  python -B scripts/claude_bm394_grid.py selftest

Arm SPEC
  py:<module>:<function>  function(puzzles: list[str], task: str) -> list[str], one answer string per puzzle, same
                          length and alphabet as the dataset's answers (the reasoner line's nets plug in here).
  ref:solve               an exact search solver (Sudoku: constraint propagation + backtracking; Maze: breadth-first
                          search). Checks the checker: it must score 100% valid.
  ref:copy                returns each puzzle unchanged. Floor check: it must score 0%.
Scores: "exact" = the published metric (answer string equal to the dataset's); "valid" = obeys every rule (Sudoku:
givens kept, every row, column and box 1-9; Maze: walls, S and G kept, the "o" cells form one path from S to G,
and it is a shortest path). A maze can have more than one shortest path, so valid can exceed exact; the headline
is always exact. Outputs hold qid and reply only; puzzle and answer text stay in DATA.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import random
import sys
import time
import urllib.request
from collections import deque
from pathlib import Path

SEED = 394
N_SUDOKU_TEST = 10000
N_PRACTICE = 1000
HF = "https://huggingface.co/datasets/{repo}/resolve/{rev}/{name}"
SOURCES = {
    "sudoku": {"repo": "sapientinc/sudoku-extreme", "rev": "58942f96baeb572ca3127e2a9e9c70f330783d6b",
               "files": {"test.csv": "a2fd52aea23d331d5b4ee723c856236e838a9fb9a70e66f4e0e0cf26c338c6a8",
                         "train.csv": "64b46674db0148e0d73a16346dadeb2b1c00824d3fca3f85b2ae7037f6b4b38e"}},
    "maze": {"repo": "sapientinc/maze-30x30-hard-1k", "rev": "549754de3d67eebe57b6b22c7d226b9412d55b07",
             "files": {"test.csv": "5120d52088fb3f8036e62e90103808a79ba58847d8601f9451f40991b0903a62",
                       "train.csv": "25f9e39b5aee16967da41ba63b2d1d75cf608c2360d8a1419d827f9859dbafa0"}},
}
PUBLISHED = {"sudoku": {"HRM 27M": 55.0, "TRM-Att 7M": 74.7, "TRM-MLP 5M": 87.4, "direct 27M": 0.0},
             "maze": {"HRM 27M": 74.5, "TRM-Att 7M": 85.3, "direct 27M": 0.0}}
csv.field_size_limit(1 << 20)


# ======================================================================= data
def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _rows(p: Path):
    with open(p, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def _write(p: Path, rows: list[dict]) -> None:
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows))


def fetch(data: Path) -> int:
    data.mkdir(parents=True, exist_ok=True)
    out = {"fetch": "OK"}
    for task, src in SOURCES.items():
        for name, want in src["files"].items():
            dest = data / f"{task}_{name}"
            if not (dest.exists() and _sha(dest) == want):
                urllib.request.urlretrieve(HF.format(repo=src["repo"], rev=src["rev"], name=name), dest)
            if _sha(dest) != want:
                print(json.dumps({"fetch": "DATA-MISMATCH", "file": dest.name}))
                return 1
        test = [dict(r, idx=i) for i, r in enumerate(_rows(data / f"{task}_test.csv"))]
        n_test_file = len(test)
        if task == "sudoku":
            pick = sorted(random.Random(SEED).sample(range(len(test)), N_SUDOKU_TEST))
            test = [test[i] for i in pick]
        tset = {r["question"] for r in test}
        n_train, overlap, train_pick = 0, 0, []
        rng = random.Random(SEED + 1)
        for i, r in enumerate(_rows(data / f"{task}_train.csv")):     # reservoir sample, one pass
            n_train += 1
            overlap += r["question"] in tset
            if r["question"] in tset:
                continue
            if len(train_pick) < N_PRACTICE:
                train_pick.append((i, r))
            else:
                j = rng.randrange(n_train)
                if j < N_PRACTICE:
                    train_pick[j] = (i, r)
        train_pick.sort(key=lambda z: z[0])
        _write(data / f"{task}_test.jsonl", [{"qid": f"{task}-test-{r['idx']}", "puzzle": r["question"],
                                              "answer": r["answer"], "rating": r["rating"]} for r in test])
        _write(data / f"{task}_practice.jsonl", [{"qid": f"{task}-train-{i}", "puzzle": r["question"],
                                                  "answer": r["answer"], "rating": r["rating"]}
                                                 for i, r in train_pick])
        answers_valid = sum(check(task, r["question"], r["answer"]) for r in test)
        out[task] = {"test_file_rows": n_test_file, "train_file_rows": n_train,
                     "test_used": len(test), "practice": len(train_pick), "test_puzzles_found_in_train": overlap,
                     "dataset_answers_valid": answers_valid,
                     "test_sha256": _sha(data / f"{task}_test.jsonl"),
                     "practice_sha256": _sha(data / f"{task}_practice.jsonl")}
    print(json.dumps(out), flush=True)
    return 0


def load(data: Path, task: str, split: str = "test") -> list[dict]:
    with open(data / f"{task}_{split}.jsonl", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


# ======================================================================= checkers
def sudoku_valid(puzzle: str, reply: str) -> bool:
    if not isinstance(reply, str) or len(reply) != 81 or any(c not in "123456789" for c in reply):
        return False
    if any(p not in ".0" and p != r for p, r in zip(puzzle, reply)):
        return False
    units = ([[r * 9 + c for c in range(9)] for r in range(9)] + [[r * 9 + c for r in range(9)] for c in range(9)]
             + [[(br + r) * 9 + bc + c for r in range(3) for c in range(3)] for br in (0, 3, 6) for bc in (0, 3, 6)])
    return all(len({reply[i] for i in u}) == 9 for u in units)


def _nbrs(i: int, n: int = 30):
    r, c = divmod(i, n)
    if r > 0:
        yield i - n
    if r < n - 1:
        yield i + n
    if c > 0:
        yield i - 1
    if c < n - 1:
        yield i + 1


def maze_shortest(puzzle: str) -> tuple[int, list[int]]:
    """Breadth-first search from S to G through non-wall cells: (number of steps, cell path S..G)."""
    s, g = puzzle.index("S"), puzzle.index("G")
    prev = {s: None}
    q = deque([s])
    while q:
        u = q.popleft()
        if u == g:
            break
        for v in _nbrs(u):
            if v not in prev and puzzle[v] != "#":
                prev[v] = u
                q.append(v)
    if g not in prev:
        return -1, []
    path, u = [], g
    while u is not None:
        path.append(u)
        u = prev[u]
    return len(path) - 1, path[::-1]


def maze_valid(puzzle: str, reply: str) -> bool:
    if not isinstance(reply, str) or len(reply) != len(puzzle) or any(c not in " #oSG" for c in reply):
        return False
    for p, r in zip(puzzle, reply):
        if (p in "#SG" or r in "#SG") and p != r:
            return False
    cells = {i for i, r in enumerate(reply) if r in "oSG"}
    s, g = puzzle.index("S"), puzzle.index("G")
    deg = {i: sum(v in cells for v in _nbrs(i)) for i in cells}
    if deg[s] != 1 or deg[g] != 1 or any(deg[i] != 2 for i in cells if i not in (s, g)):
        return False
    seen, stack = {s}, [s]                     # one connected simple path covering every marked cell
    while stack:
        u = stack.pop()
        for v in _nbrs(u):
            if v in cells and v not in seen:
                seen.add(v)
                stack.append(v)
    steps, _ = maze_shortest(puzzle)
    return seen == cells and len(cells) - 1 == steps


def check(task: str, puzzle: str, reply: str) -> bool:
    return sudoku_valid(puzzle, reply) if task == "sudoku" else maze_valid(puzzle, reply)


# ======================================================================= reference arms
_UNITS = None


def _sudoku_units():
    global _UNITS
    if _UNITS is None:
        rows = [[r * 9 + c for c in range(9)] for r in range(9)]
        cols = [[r * 9 + c for r in range(9)] for c in range(9)]
        boxes = [[(br + r) * 9 + bc + c for r in range(3) for c in range(3)] for br in (0, 3, 6) for bc in (0, 3, 6)]
        peers = [sorted({j for u in rows + cols + boxes if i in u for j in u} - {i}) for i in range(81)]
        _UNITS = peers
    return _UNITS


def sudoku_solve(puzzle: str) -> str:
    peers = _sudoku_units()
    grid = [0 if ch in ".0" else int(ch) for ch in puzzle]

    def cands(g, i):
        used = 0
        for j in peers[i]:
            if g[j]:
                used |= 1 << g[j]
        return [d for d in range(1, 10) if not used >> d & 1]

    def dfs(g):
        best, best_c = -1, None
        for i in range(81):
            if not g[i]:
                c = cands(g, i)
                if not c:
                    return None
                if best_c is None or len(c) < len(best_c):
                    best, best_c = i, c
                    if len(c) == 1:
                        break
        if best < 0:
            return g
        for d in best_c:
            g[best] = d
            r = dfs(g)
            if r is not None:
                return r
        g[best] = 0
        return None

    out = dfs(grid)
    return "".join(map(str, out)) if out else puzzle


def maze_solve(puzzle: str) -> str:
    """Breadth-first search from S taking neighbours in the order down, left, right, up (first parent found wins).
    That order reproduces the dataset's own answers exactly (every Maze-Hard maze has 96 or more shortest paths,
    median about 3.8 million, so exact match means this tie-break; checked 1,000 of 1,000 test mazes)."""
    s, g = puzzle.index("S"), puzzle.index("G")
    prev = {s: None}
    q = deque([s])
    while q:
        u = q.popleft()
        r, c = divmod(u, 30)
        for v in ((u + 30) if r < 29 else -1, (u - 1) if c > 0 else -1, (u + 1) if c < 29 else -1,
                  (u - 30) if r > 0 else -1):
            if v >= 0 and v not in prev and puzzle[v] != "#":
                prev[v] = u
                q.append(v)
    path, u = [], g
    while u is not None:
        path.append(u)
        u = prev.get(u)
        if u is None and path[-1] != s:
            return puzzle
    out = list(puzzle)
    for i in path[1:-1]:
        out[i] = "o"
    return "".join(out)


def ref_solve(puzzles: list[str], task: str) -> list[str]:
    return [sudoku_solve(p) if task == "sudoku" else maze_solve(p) for p in puzzles]


def ref_copy(puzzles: list[str], task: str) -> list[str]:
    return list(puzzles)


def resolve_arm(spec: str):
    kind, _, rest = spec.partition(":")
    if kind == "ref":
        return {"solve": ref_solve, "copy": ref_copy}[rest]
    if kind == "py":
        mod, _, fn = rest.partition(":")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        return getattr(importlib.import_module(mod), fn)
    raise SystemExit(f"bm394: arm must be py:<module>:<function> or ref:solve|copy, not {spec!r}")


# ======================================================================= run and score
def run(a) -> int:
    items = load(Path(a.data), a.task)[: a.limit or None]
    fn = resolve_arm(a.arm)
    t0 = time.time()
    replies = fn([it["puzzle"] for it in items], a.task)
    secs = time.time() - t0
    if len(replies) != len(items):
        raise SystemExit(f"bm394: arm returned {len(replies)} answers for {len(items)} puzzles")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / f"{a.task}_{a.name}.jsonl", [{"qid": it["qid"], "reply": r} for it, r in zip(items, replies)])
    print(f"wrote {a.task}_{a.name}.jsonl rows={len(items)} seconds={secs:.1f}", flush=True)
    return 0


def _wilson(k: int, n: int) -> list[float]:
    if not n:
        return [0.0, 0.0]
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 2), round(100 * (c + h), 2)]


def score_file(data: Path, task: str, path: Path) -> tuple[dict, dict]:
    gold = {it["qid"]: it for it in load(data, task)}
    per = {}
    with open(path, encoding="utf-8") as fh:
        for x in fh:
            if x.strip():
                r = json.loads(x)
                it = gold[r["qid"]]
                per[r["qid"]] = (int(r["reply"] == it["answer"]), int(check(task, it["puzzle"], r["reply"])))
    n = len(per)
    ex, va = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    return ({"n": n, "of": len(gold), "exact": ex, "exact_pct": round(100 * ex / max(1, n), 2),
             "exact_ci95": _wilson(ex, n), "valid": va, "valid_pct": round(100 * va / max(1, n), 2)}, per)


def score(a) -> int:
    data, runs = Path(a.data), Path(a.runs)
    res, pers = {}, {}
    for p in sorted(runs.glob("*.jsonl")):
        task, _, name = p.stem.partition("_")
        if task not in SOURCES:
            continue
        s, per = score_file(data, task, p)
        res[f"{task}_{name}"] = s
        pers[f"{task}_{name}"] = per
        print(json.dumps({"arm": f"{task}_{name}", **s, "published": PUBLISHED[task]}), flush=True)
    if a.pair:
        x, y = a.pair.split(",")
        for task in SOURCES:
            ka, kb = f"{task}_{x}", f"{task}_{y}"
            if ka in pers and kb in pers:
                ids = sorted(set(pers[ka]) & set(pers[kb]))
                d = [pers[ka][q][0] - pers[kb][q][0] for q in ids]
                rng = random.Random(SEED)
                means = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(2000))
                res[f"{task}_{x}-{y}"] = {"n": len(ids), "diff": round(100 * sum(d) / len(d), 2),
                                          "ci95": [round(100 * means[49], 2), round(100 * means[1949], 2)]}
                print(json.dumps({"pair": f"{task} {x}-{y}", **res[f"{task}_{x}-{y}"]}), flush=True)
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "score.json").write_text(json.dumps({"arms": res, "published": PUBLISHED}, indent=1),
                                                encoding="utf-8")
    return 0


def selftest() -> int:
    ok = {}
    sol = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    puz = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    ok["sudoku_solve"] = sudoku_solve(puz) == sol
    ok["sudoku_valid"] = sudoku_valid(puz, sol)
    ok["sudoku_rejects_changed_given"] = not sudoku_valid(puz, "6" + sol[1:])
    ok["sudoku_rejects_copy"] = not sudoku_valid(puz, puz)
    m = list(" " * 900)
    for i in range(30):
        m[30 * 15 + i] = "#" if i not in (3, 20) else " "      # a wall with two gaps: two different routes
    m[0], m[899] = "S", "G"
    mz = "".join(m)
    solved = maze_solve(mz)
    ok["maze_solve_valid"] = maze_valid(mz, solved)
    ok["maze_rejects_copy"] = not maze_valid(mz, mz)
    longer = list(solved)
    k = next(i for i, c in enumerate(solved) if c == "o")
    ok["maze_rejects_broken_path"] = not maze_valid(mz, "".join(longer[:k] + [" "] + longer[k + 1:]))
    ok["maze_rejects_wall_change"] = not maze_valid(mz, solved.replace("#", " ", 1))
    for k2, v in ok.items():
        print(("PASS " if v else "FAIL ") + k2)
    print("BM394-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "run", "score", "selftest"])
    ap.add_argument("--data", default="")
    ap.add_argument("--task", default="", choices=["", "sudoku", "maze"])
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--runs", default="")
    ap.add_argument("--pair", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if not a.data:
        raise SystemExit("bm394: --data is required")
    if a.cmd == "fetch":
        return fetch(Path(a.data))
    if a.cmd == "run":
        if not (a.task and a.arm and a.name and a.out):
            raise SystemExit("bm394: run needs --task, --arm, --name and --out")
        return run(a)
    return score(a)


if __name__ == "__main__":
    sys.exit(main())
