#!/usr/bin/env python3
"""Exp 119 — length-coverage training wave for BensPC (Muse PREP).

Runs on BensPC ONLY (Python, torch+cu128, NO transformers):
    python fable_ears119_train.py --seed 11901 --pool C:\\Users\\benja\\ears119\\pool119.jsonl \\
        --snapshot <scibert-snapshot> --cal <47-cal.json> \\
        --out C:\\Users\\benja\\ears119\\runs\\w-11901

Same rung-2 architecture + encoder + recipe as exp 47 (SciBERT + FrameEars,
batch 32, 2 epochs, AdamW lr 3e-5 cosine, wd 0.01, clip 1.0, bf16 autocast on
CUDA, freeze 0, CAL golden-section temperatures + 47 tau rule in the scorer).
THE ONE CHANGE vs 47 (see fable_ears119_data.py): MAX_LEN 192 and the synth
pool rows length-matched to the WebRED length histogram.

Implementation-only deviation D2 (declared in PASSMARKS): per-batch dynamic
padding instead of static MAX_LEN padding in the training loop. Masked padding
is mathematically identical compute; it exists so the 3-seed wave fits the
45-minute budget at the wider window. Step count, order RNG, schedule grid and
loss are unchanged: total = 2 * ceil(pool_n / 32).

Additive only: fable_ears47_{data,model,encoder,train} imported read-only.
MAX override (D.MAX_LEN = 192, _wp_encode default) is applied BEFORE importing
fable_ears47_train so its module-level MAX_LEN (= D.MAX_LEN at import) is 192
for to_pack (CAL fit) and fit_temperatures.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402
import fable_ears119_data as D119  # noqa: E402  (applies the MAX_LEN override)
import fable_ears47_model as M  # noqa: E402
import fable_ears47_encoder as E  # noqa: E402
import fable_ears47_train as T47  # noqa: E402  (load_pool/fit_temperatures; MAX=192)

assert T47.MAX_LEN == D119.MAX119 == 192, T47.MAX_LEN

SEEDS119 = (11901, 11902, 11903)


def collate(rows: list[dict], idx: torch.Tensor, device=None) -> dict:
    """Pad this batch to its own longest row (multiple of 8), not to MAX_LEN."""
    sub = [rows[int(i)] for i in idx]
    L = max(len(r["ids"]) for r in sub)
    L = min(((L + 7) // 8) * 8, T47.MAX_LEN)
    ids = torch.zeros(len(sub), L, dtype=torch.long)
    mask = torch.zeros(len(sub), L, dtype=torch.bool)
    for i, r in enumerate(sub):
        n = min(len(r["ids"]), L)
        ids[i, :n] = torch.tensor(r["ids"][:n])
        mask[i, :n] = True
    out = {"ids": ids, "mask": mask,
           "act": torch.tensor([r["act"] for r in sub]),
           "rel": torch.tensor([r["rel"] for r in sub]),
           "subj": torch.tensor([r["subj"] for r in sub]),
           "obj": torch.tensor([r["obj"] for r in sub]),
           "dir": torch.tensor([r["dir"] for r in sub]),
           "flags": torch.tensor([r["flags"] for r in sub], dtype=torch.float)}
    if device is not None:
        out = {k: v.to(device) for k, v in out.items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--cal", required=True,
                    help="sealed exp-47 CAL panel json (same calibration as 47)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--freeze-layers", type=int, default=0)
    ap.add_argument("--steps-cap", type=int, default=0)
    a = ap.parse_args()
    assert a.seed in SEEDS119, f"registered seeds are {SEEDS119}"
    assert a.epochs == 2 and a.batch == 32 and abs(a.lr - 3e-5) < 1e-12 \
        and a.freeze_layers == 0 and not a.steps_cap, \
        "registered recipe is fixed (2 epochs, batch 32, lr 3e-5, freeze 0)"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    assert device.type == "cuda", "registered wave runs on the BensPC GPU"
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    t0 = time.time()
    rows = T47.load_pool(a.pool)
    print(f"[{a.seed}] pool rows={len(rows)}", flush=True)
    enc, tok, info = E.load(a.snapshot)
    order = list(range(len(rows)))
    random.Random(a.seed).shuffle(order)
    rows = [rows[i] for i in order]
    cal_rows = []
    for r in json.loads(Path(a.cal).read_text(encoding="utf-8")):
        e = D.encode_row(r, tok)
        if e is not None:
            cal_rows.append(e)
    cal_pack = T47.to_pack(cal_rows)
    print(f"[{a.seed}] cal encodable={len(cal_rows)}", flush=True)
    data_s = time.time() - t0

    torch.manual_seed(a.seed)
    model = M.FrameEars(enc, D.N_REL,
                        freeze_layers=a.freeze_layers).to(device)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                            lr=a.lr, weight_decay=0.01)
    total = a.epochs * math.ceil(len(rows) / a.batch)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(total, 1))
    log = []
    step = 0
    t_start = time.time()
    tokens_at_200 = None
    done = False
    model.train()
    while not done:
        for s in range(0, len(rows), a.batch):
            if step >= total:
                done = True
                break
            idx = torch.arange(s, min(s + a.batch, len(rows)))
            b = collate(rows, idx, device)
            t_b = time.time()
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16,
                                enabled=True):
                o = model(b["ids"], b["mask"])
                loss = M.loss_fn(o, b)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1.0)
            opt.step()
            sched.step()
            step += 1
            if step == 200:
                elapsed = time.time() - t_start
                tokens_at_200 = int(b["mask"].sum()) * (200 / 1.0) / elapsed
                proj = elapsed / 200 * total
                print(f"[{a.seed}] step200 tokens/s={tokens_at_200:.0f} "
                      f"sec/step={elapsed / 200:.3f} projected_total={proj / 60:.1f}min",
                      flush=True)
            if step % 200 == 0 or step == total:
                print(f"[{a.seed}] step {step}/{total} loss {float(loss.detach()):.4f} "
                      f"{(time.time() - t_start) / step:.3f}s/step", flush=True)
                log.append({"step": step, "loss": float(loss.detach())})
    train_s = time.time() - t_start

    model.eval()
    with torch.no_grad():
        sub = {k: v[:2048].to(device) for k, v in T47.to_pack(rows).items()}
        o = model(sub["ids"], sub["mask"])
        cor = int((o["act"].argmax(-1) == sub["act"]).sum())
        tot = sub["ids"].shape[0]
    temps = T47.fit_temperatures(model, cal_pack)
    model.temps.copy_(temps)
    torch.save({"state": model.state_dict(), "seed": a.seed,
                "temps": temps, "encoder_params": info["params"],
                "freeze_layers": a.freeze_layers}, out / "ear.pt")
    meta = {"seed": a.seed, "exp": 119, "epochs": a.epochs, "batch": a.batch,
            "lr": a.lr, "steps": step, "max_len": T47.MAX_LEN,
            "params": M.n_params(model),
            "params_trainable": M.n_params_trainable(model),
            "pool": len(rows), "pool_file": a.pool, "cal_file": a.cal,
            "device": str(device),
            "sec_per_step": train_s / max(step, 1), "train_sec": train_s,
            "data_sec": data_s, "dev_act_acc": cor / max(tot, 1),
            "tokens_per_sec_200": tokens_at_200,
            "temps": [float(x) for x in temps],
            "freeze_layers": a.freeze_layers, "loss_log": log}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "loss_log"}, indent=1))


if __name__ == "__main__":
    main()
