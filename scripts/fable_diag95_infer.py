#!/usr/bin/env python3
"""Exp 95 (design doc 95) — read-only diagnosis inference for the sealed exp-47 FAIL.

Reads sealed panels + sealed checkpoints, writes per-row compact decode records.
Never trains, never writes to exp-47 files.

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_diag95_infer.py --out artifacts/fable-diag95-20260921/fable_diag95_rows.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D          # noqa: E402 (read-only import; same additive markers)
import fable_ears47_model as M         # noqa: E402
import fable_ears47_encoder as ENC     # noqa: E402
import fable_ears47_score as S         # noqa: E402 (sealed decode/verdict logic)

SEEDS = (4701, 4702, 4703)
PANELS = ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard",
          "wneg", "wpos", "wclosed", "wnewrel")
SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")
RUNS = Path("artifacts/fable-ears47-20260921/runs")
PANEL_DIR = Path("artifacts/fable-ears47-20260921/panels")
BATCH = 64


def compact_frame(fr):
    if fr is None:
        return None
    return {"act": fr["act"], "rel": fr["rel"],
            "subj": list(fr["subj"]) if fr["subj"] else None,
            "obj": list(fr["obj"]) if fr["obj"] else None,
            "dir": fr["dir"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="4701,4702,4703")
    ap.add_argument("--panels", default=",".join(PANELS))
    a = ap.parse_args()
    seeds = tuple(int(s) for s in a.seeds.split(","))
    panels = tuple(a.panels.split(","))
    torch.set_num_threads(1)
    t0 = time.time()

    _, tok, _ = ENC.load(SNAP)
    unk_ids = {tok.unk}

    # encode requested panels once
    store = {}
    for name in panels:
        rows = json.loads((PANEL_DIR / f"{name}.json").read_text(encoding="utf-8"))
        encs = S.encode_panel(rows, tok)
        golds = [S.gold_frame_of(e) for e in encs]
        store[name] = (rows, encs, golds)
    print(f"encoded {[ (k, len(v[0])) for k, v in store.items() ]}", flush=True)

    out = {"panels": {}, "timing_s": None, "seeds": list(seeds)}
    for si, seed in enumerate(seeds):
        ck = torch.load(RUNS / f"c-{seed}" / "ear.pt", map_location="cpu",
                        weights_only=False)
        enc, _, _ = ENC.load(SNAP)
        model = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
        model.load_state_dict(ck["state"])
        model.eval()
        del ck
        for name in panels:
            rows, encs, _ = store[name]
            P = S.probs_for_model(model, encs, torch.device("cpu"), batch=BATCH)
            parses = [S.decode(rows[i], encs[i], P[i], unk_ids)
                      for i in range(len(rows))]
            rec = out["panels"].setdefault(name, {"n": len(rows), "rows": []})
            if si == 0:
                for i, r in enumerate(rows):
                    rec["rows"].append({
                        "n": r.get("n"), "family": r.get("family", "?"),
                        "text": D.row_text(r),
                        "gold": compact_frame(store[name][2][i]),
                        "relation": r.get("relation"),
                        "seeds": [],
                    })
            for i, p in enumerate(parses):
                rec["rows"][i]["seeds"].append({
                    "frame": compact_frame(p["frame"]), "conf": p["conf"],
                    "ok4": bool(p["ok4"]), "ok5": bool(p["ok5"]),
                    "forced_echo": bool(p["forced_echo"]),
                    "reason": p["reason"]})
            del P, parses
        del model
        import gc
        gc.collect()
        print(f"seed {seed} done, {time.time()-t0:.0f}s elapsed", flush=True)

    out["timing_s"] = time.time() - t0
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {a.out} in {out['timing_s']:.0f}s")


if __name__ == "__main__":
    main()
