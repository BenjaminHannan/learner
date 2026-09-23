#!/usr/bin/env python3
"""Experiment 103, S2-fresh builder: 200 NEW 4-hop cases, seed 10300.

Reads the SAME raw MQuAKE-Remastered CF-3k parquet as exp 92 (read-only)
and writes data/open/bench103/fable_edit103_s2fresh_4hop.jsonl using the
SAME builder logic (chain_linked filter + mquake_item, imported read-only
from scripts/fable_bench92_build.py, never edited).

Freshness: every exp-92 case_id (S1-S5; S6 is ours-fictitious, no case_id)
is excluded; the sample is drawn with a NEW seed (10300) and zero overlap
is proved by case id in the manifest.

Additive, offline, Mac CPU. Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with pandas --with pyarrow \\
    python -B scripts/fable_bench103_build_s2fresh.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench92_build as B92  # noqa: E402 (read-only; never edited)

ROOT = SCRIPTS.parent
DATA92 = ROOT / "data" / "open" / "bench92"
DATA = ROOT / "data" / "open" / "bench103"

SEED = 10300
N = 200


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def used_case_ids() -> set[int]:
    used: set[int] = set()
    for f in sorted(DATA92.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                if "case_id" in d:
                    used.add(int(d["case_id"]))
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
    print(f"fresh 4-hop chain-linked pool: {len(pool)} (used excluded: {len(used)})")
    assert len(pool) >= N, f"only {len(pool)} fresh 4-hop items, need {N}"
    chosen = sorted(rng.sample(pool, N), key=lambda r: int(r["case_id"]))
    items = []
    for k, r in enumerate(chosen, 1):
        item = B92.mquake_item(r, "s2fresh-4hop", k)
        item["id"] = f"bench103-s2fresh-4hop-{k:03d}"
        item["type"] = "mquake-s2fresh-4hop"
        items.append(item)
    overlap = [it["case_id"] for it in items if int(it["case_id"]) in used]
    assert not overlap, f"overlap with exp-92: {overlap}"
    assert len({it["id"] for it in items}) == len(items)
    assert len({int(it["case_id"]) for it in items}) == len(items)

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "fable_edit103_s2fresh_4hop.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "seed": SEED,
        "n": len(items),
        "sha256": sha256_of(out),
        "bytes": out.stat().st_size,
        "exp92_used_case_ids": len(used),
        "overlap_case_ids": overlap,
        "fresh_pool": len(pool),
        "raw": {p.name: {"sha256": sha256_of(p), "bytes": p.stat().st_size}
                for p in (B92.RAW_MQUAKE, B92.RAW_TWOHOP)},
    }
    (DATA / "fable_bench103_build_manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"{out.name}: n={len(items)} overlap={len(overlap)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
