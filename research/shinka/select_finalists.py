#!/usr/bin/env python3
"""Pick the finalists by the sealed rule (research/shinka/CARD.md section 6).

(a) the top 4 distinct correct programs by evolution score;
(b) the 2 correct programs whose behaviour descriptor is farthest (z-scored Euclidean,
    distance to the nearest of the (a) programs) from the 4, among programs scoring
    at least 0.497 - 0.06.

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
SCORE_FLOOR = 0.497 - 0.06


def main() -> None:
    run = Path(sys.argv[1])
    db = sqlite3.connect(f"file:{run / 'programs.sqlite'}?mode=ro", uri=True)
    rows = db.execute("SELECT id, generation, code, combined_score, private_metrics, metadata "
                      "FROM programs WHERE correct = 1").fetchall()
    progs, seen_code = [], set()
    for pid, gen, code, score, priv, meta in sorted(rows, key=lambda r: -(r[3] or 0)):
        norm = "\n".join(l.rstrip() for l in code.strip().splitlines())
        if norm in seen_code:  # "distinct": identical code counts once
            continue
        seen_code.add(norm)
        d = (json.loads(priv) if priv else {}).get("descriptor")
        name = (json.loads(meta) if meta else {}).get("patch_name", "")
        progs.append({"id": pid, "gen": gen, "code": code, "score": score, "desc": d, "name": name})
    seed = progs and min(progs, key=lambda p: p["gen"])
    top = [p for p in progs if p["gen"] != 0][:4]
    pool = [p for p in progs if p not in top and p["gen"] != 0 and p["desc"] and p["score"] >= SCORE_FLOOR]
    with_d = [p for p in progs if p["desc"]]
    dim = len(with_d[0]["desc"])
    mu = [sum(p["desc"][i] for p in with_d) / len(with_d) for i in range(dim)]
    sd = [math.sqrt(sum((p["desc"][i] - mu[i]) ** 2 for p in with_d) / len(with_d)) or 1.0 for i in range(dim)]

    def z(p):
        return [(p["desc"][i] - mu[i]) / sd[i] for i in range(dim)]

    for p in pool:
        p["dist"] = min(math.dist(z(p), z(t)) for t in top if t["desc"])
    strange = sorted(pool, key=lambda p: -p["dist"])[:2]

    order = []
    labels = [("6b-1", strange, 0), ("6a-1", top, 0), ("6b-2", strange, 1),
              ("6a-2", top, 1), ("6a-3", top, 2), ("6a-4", top, 3)]
    out = run / "finalists"
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
