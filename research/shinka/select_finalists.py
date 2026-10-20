#!/usr/bin/env python3
"""Pick the finalists by the sealed rule (research/shinka/CARD.md section 6).

(a) the top 4 distinct correct evolved programs by evolution score;
(b) the 2 correct evolved programs whose behaviour descriptor is farthest (z-scored
    Euclidean, distance to the nearest of the (a) programs) from the 4, among programs
    scoring at least 0.497 - 0.06. The z-score reference set is the strange slot's:
    correct programs at or above that floor. (Both clarifications: CARD.md amendment
    2026-10-20.)

Writes each finalist's code and its diff against the seed to <run>/finalists/, and
prints the paths in the judge order of CARD.md section 8:
6(b)-1, 6(a)-1, 6(b)-2, 6(a)-2, 6(a)-3, 6(a)-4.

Usage: python select_finalists.py results/evo1
"""

from __future__ import annotations

import difflib
import json
import math
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from local_embed_server import code_tokens  # noqa: E402

SCORE_FLOOR = 0.497 - 0.06


def _valid_desc(d, dim=None) -> bool:
    return (isinstance(d, list) and d and all(isinstance(x, (int, float)) for x in d)
            and (dim is None or len(d) == dim))


def main() -> None:
    run = Path(sys.argv[1])
    db = sqlite3.connect(f"file:{run / 'programs.sqlite'}?mode=ro", uri=True)
    # ORDER BY makes ties reproducible: equal scores fall back to generation, then id
    rows = db.execute("SELECT id, generation, code, combined_score, private_metrics, metadata "
                      "FROM programs WHERE correct = 1 AND combined_score IS NOT NULL "
                      "ORDER BY combined_score DESC, generation ASC, id ASC").fetchall()
    progs, seen_code = [], set()
    for pid, gen, code, score, priv, meta in rows:
        if gen == 0:
            continue  # the seed is the baseline, not a finalist (CARD.md amendment 2026-10-20)
        norm = tuple(code_tokens(code))  # "distinct": comments, strings and spacing ignored
        if norm in seen_code:
            continue
        seen_code.add(norm)
        d = (json.loads(priv) if priv else {}).get("descriptor")
        name = (json.loads(meta) if meta else {}).get("patch_name", "")
        progs.append({"id": pid, "gen": gen, "code": code, "score": score,
                      "desc": d if _valid_desc(d) else None, "name": name})
    if not progs:
        raise SystemExit("no correct evolved programs: no finalists")
    top = progs[:4]
    # reference set for z-scoring = the strange slot's (run_evo._strange_parent): correct
    # programs at or above the floor that have a valid descriptor
    ref = [p for p in progs if p["desc"] and p["score"] >= SCORE_FLOOR]
    dim = len(ref[0]["desc"]) if ref else 0
    ref = [p for p in ref if _valid_desc(p["desc"], dim)]
    pool = [p for p in ref if p not in top]
    strange = []
    top_d = [t for t in top if t in ref]
    if ref and top_d and pool:
        mu = [sum(p["desc"][i] for p in ref) / len(ref) for i in range(dim)]
        sd = [math.sqrt(sum((p["desc"][i] - mu[i]) ** 2 for p in ref) / len(ref)) or 1.0
              for i in range(dim)]

        def z(p):
            return [(p["desc"][i] - mu[i]) / sd[i] for i in range(dim)]

        for p in pool:
            p["dist"] = min(math.dist(z(p), z(t)) for t in top_d)
        strange = sorted(pool, key=lambda p: -p["dist"])[:2]

    order = []
    labels = [("6b-1", strange, 0), ("6a-1", top, 0), ("6b-2", strange, 1),
              ("6a-2", top, 1), ("6a-3", top, 2), ("6a-4", top, 3)]
    out = run / "finalists"
    if out.exists():  # never mix finalists from an earlier selection
        for f in out.iterdir():
            f.unlink()
    out.mkdir(exist_ok=True)
    seed_code = (HERE / "task" / "initial.py").read_text()
    summary = []
    for label, group, i in labels:
        if i >= len(group):
            continue
        p = group[i]
        path = out / f"{label}_gen{p['gen']}.py"
        path.write_text(p["code"])
        diff = "".join(difflib.unified_diff(seed_code.splitlines(True), p["code"].splitlines(True),
                                            "task/initial.py", path.name))
        (out / f"{label}_gen{p['gen']}.diff").write_text(diff)
        order.append(str(path))
        summary.append({"label": label, "gen": p["gen"], "id": p["id"], "name": p["name"],
                        "evo_score": p["score"], "dist": p.get("dist")})
    (out / "finalists.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), file=sys.stderr)
    print(" ".join(order))


if __name__ == "__main__":
    main()
