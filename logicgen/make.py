"""CLI: python -m logicgen.make --kind logic|placebo --split SPLIT --n N --seed S --max-chars C --out FILE"""
import argparse
import json
from collections import Counter

from .generate import make_rows, SPLITS


def summary(rows):
    lab = Counter(r["label"] for r in rows)
    dep = Counter(r["depth"] for r in rows)
    mean = sum(r["chars"] for r in rows) / max(1, len(rows))
    key = lambda d: (d is None, d)
    return (f"n={len(rows)} labels={dict(sorted(lab.items()))} "
            f"depths={ {k: dep[k] for k in sorted(dep, key=key)} } mean_chars={mean:.1f}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["logic", "placebo"], default="logic")
    ap.add_argument("--split", choices=sorted(SPLITS), required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-chars", type=int, default=208)
    ap.add_argument("--depths", help="comma list overriding the split's depths, equal weights, e.g. 0,1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    depths = [int(x) for x in a.depths.split(",")] if a.depths else None
    rows = make_rows(a.kind, a.split, a.n, a.seed, a.max_chars, depths=depths)
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    st = make_rows.last_stats
    rej = 1 - st["accepted"] / st["attempts"]
    print(f"{a.kind}/{a.split} seed={a.seed} " + summary(rows) + f" reject_rate={rej:.3f}")


if __name__ == "__main__":
    main()
