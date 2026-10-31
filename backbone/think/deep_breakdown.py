"""What the depth 4-6 slice is made of, from results already on disk (no GPU, no training):
python3 backbone/think/deep_breakdown.py DATA_DIR RESULT_JSON [RESULT_JSON ...] > backbone/results/think2/DEEP_BREAKDOWN.txt

DATA_DIR holds validation.jsonl (and train.jsonl for the per-bank train counts). Each RESULT_JSON is a think1 result scored on all of
validation; its "eval.validation" tags (main, r1, r2, ...) are reported as NAME:TAG. Prints:
  1. accuracy by depth slice for every tag;
  2. the depth 4-6 slice by question bank, with the same bank's depth 1-3 accuracy beside it (is the bank hard at every depth, or only deep?);
  3. accuracy by depth inside the banks that have rows at both depth <= 3 and depth >= 4;
  4. oracle-over-tags (a row counts if any tag of that group gets it right) for each result file, so a looped arm's "pick the best loop count
     per row" headroom can be compared with the same oracle over separately trained plain models.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

SLICES = {"all": None, "d1-3": (1, 2, 3), "d4-6": (4, 5, 6)}


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_hits(paths, n):
    """{NAME:TAG: hit string} for every validation tag in every result file that was scored on all n rows."""
    out, groups = {}, {}
    for p in paths:
        name = Path(p).parent.name
        v = json.loads(Path(p).read_text())["eval"]["validation"]
        tags = [t for t in v if "hits" in v[t] and len(v[t]["hits"]) == n]
        loops = [t for t in tags if t[:1] == "r" and t[1:].isdigit()]
        tags = loops or tags[:1]  # a looped arm's main repeats one of its r tags; a plain arm keeps its first (main) tag
        for t in tags:
            out[f"{name}:{t}"] = v[t]["hits"]
        groups[name] = [f"{name}:{t}" for t in tags]
    return out, groups


def acc(ix, h):
    return 100 * sum(h[i] == "1" for i in ix) / len(ix) if ix else float("nan")


def oracle(ix, hs):
    return 100 * sum(any(h[i] == "1" for h in hs) for i in ix) / len(ix) if ix else float("nan")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("data")
    ap.add_argument("results", nargs="+")
    a = ap.parse_args(argv)
    rows = read_jsonl(Path(a.data) / "validation.jsonl")
    train = Path(a.data) / "train.jsonl"
    tr_banks = collections.Counter(r["bank"] for r in read_jsonl(train)) if train.exists() else {}
    H, groups = load_hits(a.results, len(rows))
    if not H:
        raise SystemExit("no result file was scored on all validation rows")
    by = {s: [i for i, r in enumerate(rows) if d is None or r["depth"] in d] for s, d in SLICES.items()}
    tags = list(H)

    print("== 1. accuracy by depth slice")
    print(f"{'tag':22s} " + " ".join(f"{s:>7s}" for s in SLICES))
    for t in tags:
        print(f"{t:22s} " + " ".join(f"{acc(by[s], H[t]):7.2f}" for s in SLICES))
    print("   n                   " + " ".join(f"{len(by[s]):7d}" for s in SLICES))

    print("\n== 2. depth 4-6 by question bank (deep acc / same bank at depth 1-3)")
    deep = collections.Counter(rows[i]["bank"] for i in by["d4-6"])
    for b, c in deep.most_common():
        dx = [i for i in by["d4-6"] if rows[i]["bank"] == b]
        sx = [i for i in by["d1-3"] if rows[i]["bank"] == b]
        cells = " ".join(f"{t.split(':')[-1] if len(groups) == 1 else t}={acc(dx, H[t]):.1f}/{acc(sx, H[t]):.1f}" for t in tags)
        print(f"{b:20s} deep n={c:4d} ({100 * c / len(by['d4-6']):4.1f}%) shallow n={len(sx):4d} train n={tr_banks.get(b, 0):5d}  {cells}")

    print("\n== 3. accuracy by depth inside banks with rows on both sides of depth 3 (n >= 20 per cell)")
    for b, _ in deep.most_common():
        cells = []
        for d in range(1, 7):
            ix = [i for i, r in enumerate(rows) if r["bank"] == b and r["depth"] == d]
            if len(ix) >= 20:
                cells.append(f"d{d}(n={len(ix)}): " + " ".join(f"{acc(ix, H[t]):.1f}" for t in tags))
        if len(cells) >= 2:
            print(f"{b}\n  " + "\n  ".join(cells))
    print("   (columns: " + ", ".join(tags) + ")")

    print("\n== 4. oracle over tags (a row counts if any tag in the group is right)")
    for s in SLICES:
        cells = [f"{g}={oracle(by[s], [H[t] for t in ts]):.2f} (of {len(ts)})" for g, ts in groups.items() if len(ts) > 1]
        plain = [ts[0] for ts in groups.values() if len(ts) == 1]
        if len(plain) > 1:
            cells.append(f"plain models {'+'.join(p.split(':')[0] for p in plain)}={oracle(by[s], [H[t] for t in plain]):.2f}")
        print(f"{s:5s} " + "; ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
