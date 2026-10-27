#!/usr/bin/env python3
"""Exp 109 — Mac-CPU smoke (Muse PREP, NOT a registered seed).

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \\
      python -B scripts/fable_ears109_smoke.py --snapshot <scibert> \\
      --out artifacts/fable-ears109-20260921/smoke.json

Proves with the REAL SciBERT encoder + FrameEars head (fp32, CPU): (1) loss
falls over 100 updates on a small mixed WebRED-train + synth subset (same
loss_fn, same AdamW lr 3e-5 as the wave); (2) the panel-eval path (encode +
probs_for_model + decode) runs on 20 panel sentences. The panel is HELD-OUT:
the smoke reports ONLY that decoding ran (no gold comparison, no scores).

The checkpoint is discarded (not a registered seed).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears47_encoder as E  # noqa: E402
import fable_ears47_model as M  # noqa: E402
import fable_ears47_score as S47  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PANEL = REPO / "data" / "open" / "reading94" / "panel.jsonl"

SMOKE_MAXLEN = 48
SMOKE_N = 96
SMOKE_STEPS = 100
SMOKE_BATCH = 8
SMOKE_SEED = 10900


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(SMOKE_SEED)
    t0 = time.time()

    enc, tok, info = E.load(a.snapshot)
    print(f"encoder params {info['params']:,} weights {info.get('weights')}",
          flush=True)

    # small mixed subset: WebRED-train rows + synth rows, short only
    webred = [r for r in D.webred_pool_rows()]
    rng = random.Random(SMOKE_SEED)
    rng.shuffle(webred)
    cand = []
    for row in webred[:400] + D.synth_pool_rows(tok, random.Random(SMOKE_SEED))[:400]:
        e = D.encode_row(row, tok)
        if e is not None and len(e["ids"]) <= SMOKE_MAXLEN:
            e.pop("chspans", None)
            cand.append(e)
        if len(cand) >= SMOKE_N:
            break
    assert len(cand) >= SMOKE_N, f"only {len(cand)} short rows"
    n_wr = sum(1 for r in cand if r.get("source") == "webred")
    print(f"smoke rows={len(cand)} webred={n_wr} synth={len(cand) - n_wr} "
          f"maxlen={max(len(r['ids']) for r in cand)}", flush=True)
    pack = {"ids": torch.zeros(len(cand), D.MAX_LEN, dtype=torch.long),
            "mask": torch.zeros(len(cand), D.MAX_LEN, dtype=torch.bool),
            "act": torch.tensor([r["act"] for r in cand]),
            "rel": torch.tensor([r["rel"] for r in cand]),
            "subj": torch.tensor([r["subj"] for r in cand]),
            "obj": torch.tensor([r["obj"] for r in cand]),
            "dir": torch.tensor([r["dir"] for r in cand]),
            "flags": torch.tensor([r["flags"] for r in cand],
                                  dtype=torch.float)}
    for i, r in enumerate(cand):
        L = len(r["ids"])
        pack["ids"][i, :L] = torch.tensor(r["ids"])
        pack["mask"][i, :L] = True

    model = M.FrameEars(enc, D.N_REL)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0.01)

    def full_loss():
        model.eval()
        tot = 0.0
        with torch.no_grad():
            for s in range(0, len(cand), SMOKE_BATCH):
                idx = torch.arange(s, min(s + SMOKE_BATCH, len(cand)))
                b = {k: v[idx] for k, v in pack.items()}
                tot += float(M.loss_fn(model(b["ids"], b["mask"]), b)) \
                    * len(idx)
        model.train()
        return tot / len(cand)

    pre = full_loss()
    print(f"smoke full-subset loss before={pre:.4f}", flush=True)
    model.train()
    losses = []
    t_train = time.time()
    order = list(range(len(cand)))
    for step in range(1, SMOKE_STEPS + 1):
        random.Random(SMOKE_SEED + step).shuffle(order)
        idx = torch.tensor(order[:SMOKE_BATCH])
        b = {k: v[idx] for k, v in pack.items()}
        o = model(b["ids"], b["mask"])
        loss = M.loss_fn(o, b)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach()))
        if step in (1, 50, 100):
            print(f"smoke step {step}/{SMOKE_STEPS} loss {losses[-1]:.4f}",
                  flush=True)
    train_s = time.time() - t_train
    post = full_loss()
    print(f"smoke full-subset loss after={post:.4f}", flush=True)

    # panel-eval path runs on the FIRST 20 panel sentences; "runs" only
    panel = [json.loads(l) for l in PANEL.read_text(
        encoding="utf-8").splitlines()][:20]
    assert len(panel) == 20
    rows = [{"text": r["sentence"],
             "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None,
                        "obj": None, "dir": 0, "rep": False}} for r in panel]
    encs = [D.encode_row(r, tok) for r in rows]
    assert all(e is not None for e in encs)
    model.eval()
    P = S47.probs_for_model(model, encs, torch.device("cpu"), batch=16)
    parses = [S47.decode(rows[i], encs[i], P[i], {tok.unk})
              for i in range(len(rows))]
    assert len(parses) == 20 and all(p["frame"] is not None for p in parses)
    print("smoke panel-eval runs: 20/20 decoded (no scores reported)",
          flush=True)

    res = {"seed": SMOKE_SEED, "rows": len(cand), "webred_rows": n_wr,
           "steps": SMOKE_STEPS, "batch": SMOKE_BATCH,
           "loss_step1": losses[0], "loss_step50": losses[49],
           "loss_step100": losses[99],
           "loss_falls_50": losses[49] < losses[0],
           "full_loss_before": pre, "full_loss_after": post,
           "full_loss_falls": post < pre,
           "sec_per_step": train_s / SMOKE_STEPS, "train_sec": train_s,
           "load_plus_data_sec": t_train - t0,
           "panel_eval_runs": "20/20 decoded",
           "params": M.n_params(model)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print(f"elapsed {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
