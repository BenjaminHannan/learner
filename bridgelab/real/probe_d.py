"""Quick real-model check (no creative training): does frozen D's think state carry the count c of its question?
Linear probes train->dev/validation on D's final-loop registers, plus D's own answer accuracy and the guess-the-common-count baseline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

from bridgelab.real import data as D
from bridgelab.real.train import HERE, fit_probe, subsample_items

ROOT, TRAIN_N, EVAL_N, SEED = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), 0
tok, splits = D.open_village(ROOT, str(HERE.parent.parent / "data/tokenizer/premonition-tok-v2.json"), workers=2)
items = {"train": subsample_items(splits["train"], TRAIN_N, SEED)}
items.update({s: subsample_items(splits[s], EVAL_N, SEED + 1) for s in ("dev", "validation")})
msgs = {}
for s, it in items.items():
    hits = [p for p in (HERE / "ckpt").glob(f"dmsg-*-{s}.pt") if len(torch.load(p, weights_only=False)["d_int"]) == len(it)]
    msgs[s] = torch.load(max(hits, key=lambda p: p.stat().st_mtime), weights_only=False)
out = {}
for s in ("dev", "validation"):
    c, ctr = items[s].c, items["train"].c
    prior = float((c == torch.bincount(ctr).argmax()).float().mean())
    m, mt = msgs[s], msgs["train"]
    row = {"n": len(c), "prior": prior, "d_own": float(m["d_correct"].float().mean()),
           "d_answer_hist": torch.bincount(m["d_int"].clamp(min=-1) + 1).tolist(), "c_hist": torch.bincount(c).tolist()}
    for name, f in [("reg0", lambda x: x["reg0"]), ("all_regs", lambda x: x["regs"].flatten(1))]:
        row[f"probe_{name}"] = fit_probe(f(mt), ctr, f(m), c)
    perm = torch.randperm(len(ctr), generator=torch.Generator().manual_seed(0))
    row["probe_all_regs_shuffled_labels"] = fit_probe(mt["regs"].flatten(1), ctr[perm], m["regs"].flatten(1), c)
    out[s] = row
    print(s, json.dumps(row))
Path(HERE / "results" / "probe_d.json").write_text(json.dumps(out, indent=1))
