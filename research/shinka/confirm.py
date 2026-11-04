#!/usr/bin/env python3
"""Fresh-seed confirmation for trial finalists (research/shinka/CARD.md, "Pass marks").

Runs the baseline (task/initial.py), the strongest known reference
(MultiHeadPool) and each finalist on the FRESH seeds, which were never used
during evolution, then applies the pass marks fixed in CARD.md.

Usage: python confirm.py --out results/evo1/confirm.json prog1.py prog2.py ...
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "task"))
import toy  # noqa: E402
from evaluate import static_check  # noqa: E402

FRESH_SEEDS = (1001, 1002)
NOISE_BASELINE = 0.06      # CARD.md: > 2 x baseline seed sd (0.039) and > its 5-seed range (0.046)
NOISE_REFERENCE = 0.045    # CARD.md: max(2 x multihead-pool seed sd (0.042), 0.03), rounded up


def _spec(path: str):
    if path == "REF:MultiHeadPool":
        return (str(HERE / "task" / "references.py"), "MultiHeadPool", True)
    bad = static_check(Path(path).read_text())
    if bad:
        raise ValueError(f"rejected by sandbox: {bad}")
    return (str(Path(path).resolve()), "CardWriter", False)


def _one(path: str, seed: int):
    import torch
    torch.set_num_threads(1)
    toy.USE_CACHE = False  # fresh data, never a cache file an evolve-run candidate could touch
    try:
        return toy.run_seed(_spec(path), seed)
    except Exception as exc:  # noqa: BLE001 - one bad finalist must not lose the rest
        return {"error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("programs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)  # like the evolve run's 3 eval jobs
    a = ap.parse_args()
    base = str(HERE / "task" / "initial.py")
    paths = [base, "REF:MultiHeadPool"] + a.programs
    jobs = [(p, s) for p in paths for s in FRESH_SEEDS]
    res: dict = {p: {} for p in paths}
    # Each writer already runs in its own child process (toy.IsolatedWriter); the pool
    # only spreads the jobs over cores. A worker that dies costs only its own job.
    with ProcessPoolExecutor(a.workers, max_tasks_per_child=1) as ex:
        futs = {ex.submit(_one, p, s): (p, s) for p, s in jobs}
        for fut in as_completed(futs):
            p, s = futs[fut]
            try:
                res[p][s] = fut.result()
            except Exception as exc:  # noqa: BLE001 - e.g. BrokenProcessPool
                res[p][s] = {"error": f"{type(exc).__name__}: {exc}"}
    failed = {p: {s: r["error"] for s, r in res[p].items() if "error" in r} for p in paths}
    failed = {p: e for p, e in failed.items() if e}
    for p in (base, "REF:MultiHeadPool"):
        if p in failed:
            raise SystemExit(f"reference run failed: {p} {failed[p]}")
    table = []
    for p in a.programs:
        if p in failed:
            table.append({"program": p, "error": failed[p], "beats_baseline": False,
                          "beats_best_known": False, "novel_beats_multihead": False, "better": False})
            continue
        d_base = [res[p][s]["score"] - res[base][s]["score"] for s in FRESH_SEEDS]
        d_ref = [res[p][s]["score"] - res["REF:MultiHeadPool"][s]["score"] for s in FRESH_SEEDS]
        table.append({
            "program": p,
            "fresh_scores": [res[p][s]["score"] for s in FRESH_SEEDS],
            "delta_vs_baseline": d_base,
            "delta_vs_multihead": d_ref,
            "beats_baseline": all(x > NOISE_BASELINE for x in d_base),
            "beats_best_known": all(x > NOISE_REFERENCE for x in d_ref),
            # CARD.md section 9: a gain that is all on familiar names does not count
            "novel_beats_multihead": (sum(res[p][s]["acc_novel"] for s in FRESH_SEEDS)
                                      > sum(res["REF:MultiHeadPool"][s]["acc_novel"] for s in FRESH_SEEDS)),
            "acc_novel": [res[p][s]["acc_novel"] for s in FRESH_SEEDS],
            "err_person_lost_novel": [res[p][s]["err_person_lost_novel"] for s in FRESH_SEEDS],
        })
        table[-1]["better"] = table[-1]["beats_baseline"] and table[-1]["novel_beats_multihead"]
    summary = {
        "fresh_seeds": FRESH_SEEDS,
        "baseline": [res[base][s]["score"] for s in FRESH_SEEDS],
        "multihead": [res["REF:MultiHeadPool"][s]["score"] for s in FRESH_SEEDS],
        "finalists": table, "raw": {p: {str(s): r for s, r in v.items()} for p, v in res.items()},
    }
    Path(a.out).write_text(json.dumps(summary, indent=2))
    print("baseline", summary["baseline"], "multihead", summary["multihead"])
    for row in table:
        if "error" in row:
            print(row["program"], "FAILED", row["error"])
            continue
        print(row["program"], [round(x, 3) for x in row["fresh_scores"]],
              "BETTER" if row["better"] else "-",
              "beats_baseline" if row["beats_baseline"] else "-",
              "novel>multihead" if row["novel_beats_multihead"] else "-",
              "beats_best_known" if row["beats_best_known"] else "-")


if __name__ == "__main__":
    main()
