#!/usr/bin/env python3
"""Exp 78 helper (NOT the registered selector): build fresh CAL draws.

Structural verdict (see design doc 78): exp 64/76 CAL and test panels are
utterance-disjoint (0 shared utterances) with distinct PANEL_SEEDS, i.e.
structurally distinct distributions. Per doc 59 sec 5 ("never move test
sentences into FIT/VAL") NO test sentence may enter CAL, so the shareable
pool is the CAL pool only. A same-size redraw from a same-size pool is only
possible with replacement: per fresh seed, draw N=5000 indices with
replacement from range(5000) and apply the SAME index multiset to both arms
(so tape and bigru score the same sentences). Test panels are copied
byte-identical (sha-verified).

Label-free: this script uses only len(rows) and the RNG. No score, candidate
status, gold, or ok value guides the draw.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SRC = Path("artifacts/fable-abstain76-20260921")
ARMS = ("tape", "bigru")
TEST_PANELS = ("t_seen", "t_new", "t_hard")
N_CAL = 5000


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    # The draw uses NOTHING but N and the seed (label-free by construction).
    n = len(json.loads((SRC / "per_sentence_tape_cal.json").read_text()))
    assert n == N_CAL, f"CAL size changed: {n}"
    rng = random.Random(a.seed)
    idx = [rng.randrange(n) for _ in range(n)]
    uniq = len(set(idx))
    print(f"seed {a.seed}: bootstrap indices n={n}, unique={uniq} "
          f"({uniq / n:.3f})")

    manifest = {"seed": a.seed, "rule": "bootstrap with replacement, "
                "shared index multiset across arms", "sources": {}}
    for arm in ARMS:
        src_rows = json.loads((SRC / f"per_sentence_{arm}_cal.json").read_text())
        assert len(src_rows) == n
        fresh = [src_rows[i] for i in idx]
        (out / f"per_sentence_{arm}_cal.json").write_text(json.dumps(fresh))
    for arm in ARMS:
        for panel in TEST_PANELS:
            src = SRC / f"per_sentence_{arm}_{panel}.json"
            dst = out / f"per_sentence_{arm}_{panel}.json"
            dst.write_bytes(src.read_bytes())
            assert sha(dst) == sha(src), f"test copy mismatch {dst.name}"
            manifest["sources"][dst.name] = sha(dst)
    for arm in ARMS:
        manifest["sources"][f"per_sentence_{arm}_cal.json"] = \
            sha(out / f"per_sentence_{arm}_cal.json")
    (out / "RESPLIT_MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {out}: fresh CAL + byte-identical test copies")


if __name__ == "__main__":
    main()
