#!/usr/bin/env python3
"""Experiment 132, STEP 1 builder: 200 NEW 4-hop cases, seed 132.

Reads the SAME raw MQuAKE-Remastered CF-3k parquet as exps 92/103/121
(read-only) and writes data/open/bench132/fable_edit132_4hop.jsonl using the
SAME builder logic (chain_linked filter + mquake_item, imported read-only
from scripts/fable_bench92_build.py, never edited).

Freshness: every case_id used in data/open/bench103/fable_edit103_s2fresh_4hop.jsonl
AND data/open/bench121/fable_edit121_4hop.jsonl (and bench65, superset) is
excluded; the sample is drawn with a NEW seed (132) and zero overlap is
proved by case id in the manifest.

BLINDING: this script NEVER prints or reads sentence_en/question strings. It
prints only the item count, the structured-relation histogram (relation keys,
not sentences), and hashes.

Additive, offline, Mac CPU. Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with pandas --with pyarrow \\
    --with torch --with numpy python -B scripts/fable_bench132_build.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench92_build as B92  # noqa: E402 (read-only; never edited)

ROOT = SCRIPTS.parent
DATA103 = ROOT / "data" / "open" / "bench103"
DATA121 = ROOT / "data" / "open" / "bench121"
DATA65 = ROOT / "data" / "open" / "bench65"
DATA = ROOT / "data" / "open" / "bench132"

SEED = 132
N = 200


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def used_case_ids() -> set[int]:
    used: set[int] = set()
    for d in (DATA103, DATA121, DATA65):
        for f in sorted(d.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    dd = json.loads(line)
                    if "case_id" in dd:
                        used.add(int(dd["case_id"]))
    return used


def main() -> int:
    rng = random.Random(SEED)
    used = used_case_ids()
    import pandas as pd
    df = pd.read_parquet(B92.RAW_MQUAKE)
    pool = []
    for _, r in df.iterrows():
        rew, newt = B92.L(r["requested_rewrite"]), B92.L(r["new_triples"])
        nh = B92.L(r["new_single_hops"])
        if len(nh) != 4 or len(newt) != 4:
            continue
        if not B92.chain_linked([list(t) for t in newt]):
            continue
        if int(r["case_id"]) in used:
            continue
        pool.append(r)
    print(f"fresh 4-hop chain-linked pool: {len(pool)} "
          f"(excluded used: {len(used)})")
    assert len(pool) >= N, f"only {len(pool)} fresh 4-hop items, need {N}"
    chosen = sorted(rng.sample(pool, N), key=lambda r: int(r["case_id"]))
    items = []
    for k, r in enumerate(chosen, 1):
        item = B92.mquake_item(r, "132-4hop", k)
        item["id"] = f"bench132-4hop-{k:03d}"
        item["type"] = "mquake-132-4hop"
        items.append(item)
    overlap = [it["case_id"] for it in items if int(it["case_id"]) in used]
    assert not overlap, f"overlap with bench103/bench121/bench65: {overlap}"
    assert len({it["id"] for it in items}) == len(items)
    assert len({int(it["case_id"]) for it in items}) == len(items)

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "fable_edit132_4hop.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False, sort_keys=True) + "\n")
    # Structured-relation histogram only (relation keys, never sentences).
    rel_hist = Counter(t["relation"] for it in items for t in it["taught"])
    manifest = {
        "seed": SEED,
        "n": len(items),
        "sha256": sha256_of(out),
        "bytes": out.stat().st_size,
        "excluded_case_ids": len(used),
        "overlap_case_ids": overlap,
        "fresh_pool": len(pool),
        "relation_histogram": dict(sorted(rel_hist.items())),
        "raw": {p.name: {"sha256": sha256_of(p), "bytes": p.stat().st_size}
                for p in (B92.RAW_MQUAKE, B92.RAW_TWOHOP)},
    }
    (DATA / "fable_bench132_build_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"{out.name}: n={len(items)} overlap={len(overlap)}")
    print(f"relation_histogram: {json.dumps(dict(sorted(rel_hist.items())), sort_keys=True)}")
    print(f"sha256: {manifest['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
