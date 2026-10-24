"""Creative-only sleep A/B (design/v1/dream2/PREREG.md). One arm per run, creative module only, no D, no village data.

  python -m v1.creative_ab --arm control|treat --b2 PATH --skills DIR --out DIR [--device cuda]

Both arms: B2_s200 parent, bridge zero (a fresh Bridge, never trained, as in Gate S's sleeptime), G1 on (diary v1.g1.DIARY_SIZE, seed 0),
C2b sleep recipe of v1/creative_sleep.py, FULL pool (1,024), production tries (32/480), seed 0.
Only change: control dream2=0; treat dream2=256, dream2_max_steps=4. Writes OUT/final.json. Dev only: creative/data/c2/test.jsonl is never read.
--smoke is a hidden CPU wiring check (tiny pool/dev/updates); its numbers mean nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import torch

from v1 import creative_sleep, g1 as g1mod
from v1.joint import Bridge

SEED = 0
ARMS = {"control": dict(dream2=0, dream2_max_steps=2), "treat": dict(dream2=256, dream2_max_steps=4)}


def dreams_used(out: Path) -> dict:
    """kind_overlap (creative/dream2.py) on the dream rows that actually went into each night's records (and both nights together)."""
    from creative import dream2 as D
    from creative.c2b import load_recs
    per, allrows = {}, []
    for n in (1, 2):
        p = out / f"rec_W{n}.pt"
        if not p.exists():
            continue
        rows = [r for r in load_recs(str(p))["records"] if "dream" in r]
        per[f"night{n}"] = D.kind_overlap(rows)
        allrows += rows
    return dict(per_night=per, both_nights=D.kind_overlap(allrows) if allrows else None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARMS), required=True)
    ap.add_argument("--b2", required=True)
    ap.add_argument("--skills", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    out = Path(a.out)
    cdir = out / "creative"
    cdir.mkdir(parents=True, exist_ok=True)
    kw = dict(ARMS[a.arm])
    diary = g1mod.DIARY_SIZE
    if a.smoke:
        kw.update(updates_cap=2, pool_limit=16, dev_limit=16, n1=2, n2=4, T=1.0)
        kw["dream2"] = 16 if kw["dream2"] else 0
        diary = 32
    else:
        kw.update(n1=32, n2=480)
    bridge = Bridge(128, 256).to(a.device)          # zero bridge: never trained, and V1's creative path is the same attach
    bridge.frozen_ctx = True

    def g1_factory(raw, replay):
        parent = g1mod.frozen_copy(raw)
        return g1mod.G1(parent, g1mod.build_diary(parent, replay, n=diary, seed=SEED, device=a.device), raw.vocab, device=a.device, seed=SEED)

    t0 = time.time()
    info = creative_sleep.run_creative(str(cdir), a.b2, os.path.join(a.skills, "train.jsonl"), a.skills, device=a.device, seed=SEED,
                                       g1_factory=g1_factory, attach=bridge.attach_creative, **kw)
    sleep_s = time.time() - t0
    res = dict(arm=a.arm, smoke=a.smoke, settings=dict(kw, diary=diary, g1=True, bridge="zero", seed=SEED, b2=os.path.basename(a.b2)),
               seconds_by_stage=info["seconds"], total_sleep_seconds=round(sleep_s, 1), stages=info["stages"],
               records_per_night=dict(night1=info.get("night1_records"), night2=info.get("night2_records")),
               dream2_info=info.get("dream2"), stop=info.get("stop"))
    if (cdir / "W2.pt").exists():
        t1 = time.time()
        res["creative_dev"] = creative_sleep.dev_report(str(cdir / "W2.pt"), a.device, attach=bridge.attach_creative)
        res["creative_dev"]["model"] = "W2.pt"
        res["seconds_by_stage"]["dev_report"] = round(time.time() - t1, 1)
    if kw["dream2"]:
        res["creative"] = {"dream2": {"kind_overlap": dreams_used(cdir)}}
    (out / "final.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
