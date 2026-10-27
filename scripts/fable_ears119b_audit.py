#!/usr/bin/env python3
"""Exp 119b — label audit (Muse, CPU-only, no encoder, no training).

Samples 200 training-source rows (100 WebRED-train + 100 base synth, seed
11900), applies the 119b REMAP, and counts relation-label changes by pair.
Lengthening is skipped: it appends text only and never touches gold47, so
base-gold pair counts equal pool-gold pair counts. Checks the embedded
REMAP matches artifacts/fable-ears119b-20260922/remap.json mapping.

Reading94 is never opened here (only WebRED-train + synth generator).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119b_data as D119b  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REMAP_JSON = REPO / "artifacts" / "fable-ears119b-20260922" / "remap.json"
AUDIT_SEED = 11900


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    assert a.n == 200, "registered audit is 200 rows"
    table = json.loads(REMAP_JSON.read_text(encoding="utf-8"))
    assert D119b.REMAP == table["mapping"], "data.py REMAP != remap.json"
    rng = random.Random(AUDIT_SEED)
    webred = [r for r in D.webred_pool_rows()]
    rng.shuffle(webred)
    synth = D.synth_pool_rows(None, random.Random(D.POOL_SEED + 7))
    rng.shuffle(synth)
    sample = ([{"kind": "webred", "text": r["text"], "gold47": r["gold47"]}
               for r in webred[:100]]
              + [{"kind": "synth", "text": r["text"], "gold47": r["gold47"]}
                 for r in synth[:100]])
    pairs = Counter()
    changed = 0
    examples: dict[str, list] = {}
    for row in sample:
        before = row["gold47"]["rel"]
        after = D119b.remap_gold(row["gold47"])["rel"]
        pairs[(before, after)] += 1
        if before != after:
            changed += 1
            key = f"{before} -> {after}"
            examples.setdefault(key, []).append(row["text"][:160])
            if len(examples[key]) > 3:
                examples[key] = examples[key][:3]
    # targets must all be registered classes
    for (_b, aft) in pairs:
        assert aft in D.REL_INDEX, aft
    res = {"seed": AUDIT_SEED, "n": len(sample),
           "n_changed": changed, "n_unchanged": len(sample) - changed,
           "pair_counts": [{"before": b, "after": aft, "n": n}
                           for (b, aft), n in pairs.most_common()],
           "examples": examples}
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print(f"audit n=200 changed={changed} unchanged={len(sample) - changed}")
    for (b, aft), n in pairs.most_common():
        if b != aft:
            print(f"  CHANGED {n:4d}  {b} -> {aft}")
    print(json.dumps(res, indent=1, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
