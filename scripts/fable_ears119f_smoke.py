#!/usr/bin/env python3
"""Exp 119f — Mac-CPU smoke (Muse PREP, NOT a registered seed).

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \\
      python -B scripts/fable_ears119f_smoke.py --snapshot <scibert> \\
      --out artifacts/fable-ears119f-20260922/smoke.json

Proves with the REAL SciBERT encoder + FrameEars head (fp32, CPU) at
MAX_LEN 192: (1) the 119f data builder runs (occupation rows generate +
encode with the remapped 119b labels); (2) loss falls over 50 updates on a
small mixed subset that INCLUDES synth-occ rows + long rows (same loss_fn,
same AdamW lr 3e-5 as the wave); (3) 50 training steps run through the 119f
trainer module path. NO scores (no panel gold comparison, no taus).
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
import fable_ears119b_data as D119b  # noqa: E402  (REMAP)
import fable_ears119f_data as D119f  # noqa: E402  (occupation replacement)
import fable_ears47_encoder as E  # noqa: E402
import fable_ears47_model as M  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

SMOKE_N = 64
SMOKE_STEPS = 50
SMOKE_BATCH = 8
SMOKE_SEED = 11910

assert D.MAX_LEN == D119b.MAX119 == 192


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(SMOKE_SEED)
    t0 = time.time()

    enc, tok, info = E.load(a.snapshot)
    print(f"encoder params {info['params']:,} max_len {D.MAX_LEN}", flush=True)

    # (1) the 119f data builder runs: full 5,000-row occupation generation +
    # novelty overlap check already covered by --audit; here encode a sample.
    occ = D119f.occ_rows()
    assert len(occ) == D119f.N_REPLACE
    occ_enc = 0
    for r in occ[:200]:
        e = D.encode_row(r, tok)
        assert e is not None and not any(e["flags"])
        occ_enc += 1
    print(f"data builder: {len(occ)} occ rows, {occ_enc}/200 encode OK",
          flush=True)

    # (2) mixed subset WITH synth-occ + long rows.
    webred = [r for r in D.webred_pool_rows()]
    rng = random.Random(SMOKE_SEED)
    rng.shuffle(webred)
    ref = sorted(len(tok.encode(r["text"], 512)[0]) for r in webred)
    lrng = random.Random(D119b.RNG_LEN)
    base600 = D.synth_pool_rows(tok, random.Random(D.POOL_SEED + 7))[:600]
    longed = []
    for row in base600:
        target = min(ref[lrng.randrange(len(ref))], D119b.MAX119 - 2)
        longed.append({"text": D119b.lengthen(row["text"], target, lrng, tok),
                       "source": "synth",
                       "gold47": D119b.remap_gold(row["gold47"])})
    cand = []
    long_n = occ_n = 0
    pool = webred[:3000] + longed + occ[:600]
    rng.shuffle(pool)
    for row in pool:
        row = dict(row)
        row["gold47"] = D119b.remap_gold(row["gold47"])
        e = D.encode_row(row, tok)
        if e is not None:
            e.pop("chspans", None)
            cand.append(e)
            if len(e["ids"]) > 96:
                long_n += 1
            if row.get("source") == "synth-occ":
                occ_n += 1
        if len(cand) >= SMOKE_N and long_n >= 8 and occ_n >= 8:
            break
    assert len(cand) >= SMOKE_N, f"only {len(cand)} rows"
    assert long_n >= 8 and occ_n >= 8, (long_n, occ_n)
    print(f"smoke rows={len(cand)} long_rows={long_n} occ_rows={occ_n} "
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
        if step in (1, 25, 50):
            print(f"smoke step {step}/{SMOKE_STEPS} loss {losses[-1]:.4f}",
                  flush=True)
    train_s = time.time() - t_train
    post = full_loss()
    print(f"smoke full-subset loss after={post:.4f}", flush=True)

    res = {"seed": SMOKE_SEED, "rows": len(cand), "long_rows": long_n,
           "occ_rows": occ_n, "occ_built": len(occ),
           "max_len": D.MAX_LEN, "steps": SMOKE_STEPS, "batch": SMOKE_BATCH,
           "loss_step1": losses[0], "loss_step25": losses[24],
           "loss_step50": losses[49],
           "loss_falls_50": losses[49] < losses[0],
           "full_loss_before": pre, "full_loss_after": post,
           "full_loss_falls": post < pre,
           "sec_per_step": train_s / SMOKE_STEPS, "train_sec": train_s,
           "load_plus_data_sec": t_train - t0,
           "params": M.n_params(model)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print(f"elapsed {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
