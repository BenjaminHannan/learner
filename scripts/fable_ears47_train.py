#!/usr/bin/env python3
"""Rung 2 of design 47 -- train one arm-C seed.

    python fable_ears47_train.py --seed 4701 --pool pool.jsonl --snapshot <dir> --out runs/c-4701

Full fine-tune of SciBERT + frame head, bf16 autocast on CUDA, batch 32, seq <= 96,
2 epochs, AdamW lr 3e-5 cosine.  Tokens/s is measured at step 200 and the projected
wall-clock is printed (plan aborts a seed > 40 min -> freeze lower layers, registered).
Temperatures are fitted on the sealed CAL panel at the end (never a test panel).
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
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D                     # noqa: E402
import fable_ears47_model as M                    # noqa: E402
import fable_ears47_encoder as E                  # noqa: E402

MAX_LEN = D.MAX_LEN
HEADS = ("act", "rel", "subj", "obj", "dir")


def load_pool(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line))
    return rows


def to_pack(rows: list[dict]) -> dict:
    n = len(rows)
    ids = torch.zeros(n, MAX_LEN, dtype=torch.long)
    mask = torch.zeros(n, MAX_LEN, dtype=torch.bool)
    for i, r in enumerate(rows):
        L = min(len(r["ids"]), MAX_LEN)
        ids[i, :L] = torch.tensor(r["ids"][:L])
        mask[i, :L] = True
    return {"ids": ids, "mask": mask,
            "act": torch.tensor([r["act"] for r in rows]),
            "rel": torch.tensor([r["rel"] for r in rows]),
            "subj": torch.tensor([r["subj"] for r in rows]),
            "obj": torch.tensor([r["obj"] for r in rows]),
            "dir": torch.tensor([r["dir"] for r in rows]),
            "flags": torch.tensor([r["flags"] for r in rows], dtype=torch.float)}


def batch(pack: dict, idx: torch.Tensor, device=None) -> dict:
    out = {k: v[idx] for k, v in pack.items()}
    if device is not None:
        out = {k: v.to(device) for k, v in out.items()}
    return out


def _pad(z: torch.Tensor, width: int) -> torch.Tensor:
    if z.shape[-1] == width:
        return z
    pad = z.new_full((z.shape[0], width - z.shape[-1]), torch.finfo(z.dtype).min)
    return torch.cat([z, pad], -1)


@torch.no_grad()
def fit_temperatures(model, pack) -> torch.Tensor:
    """one scalar per scored head on CAL, golden-section on log-temperature (B.3/B.5)."""
    dev = next(model.parameters()).device
    logits = {h: [] for h in HEADS}
    tgts = {h: [] for h in HEADS}
    model.eval()
    n = pack["ids"].shape[0]
    for s in range(0, n, 64):
        b = batch(pack, torch.arange(s, min(s + 64, n)), dev)
        o = model(b["ids"], b["mask"])
        nb, t = b["ids"].shape
        logits["act"].append(o["act"]); tgts["act"].append(b["act"])
        logits["rel"].append(o["rel"]); tgts["rel"].append(b["rel"])
        logits["dir"].append(o["direction"]); tgts["dir"].append(b["dir"])
        ptr = o["ptr"]                                   # [B,4,T]
        logits["subj"].append(_pad(torch.cat([ptr[:, 0], ptr[:, 1]], 0), MAX_LEN))
        tgts["subj"].append(torch.cat([b["subj"][:, 0], b["subj"][:, 1]], 0))
        logits["obj"].append(_pad(torch.cat([ptr[:, 2], ptr[:, 3]], 0), MAX_LEN))
        tgts["obj"].append(torch.cat([b["obj"][:, 0], b["obj"][:, 1]], 0))
    temps = torch.ones(M.N_TEMPS)
    for i, h in enumerate(HEADS):
        L = torch.cat(logits[h], 0).float()
        Y = torch.cat(tgts[h], 0)

        def nll(logt, L=L, Y=Y):
            return F.cross_entropy(L / math.exp(logt), Y).item()

        lo, hi = -1.5, 1.5
        gr = (math.sqrt(5) - 1) / 2
        c, d_ = hi - gr * (hi - lo), lo + gr * (hi - lo)
        fc, fd = nll(c), nll(d_)
        for _ in range(30):
            if fc < fd:
                hi, d_, fd = d_, c, fc
                c = hi - gr * (hi - lo)
                fc = nll(c)
            else:
                lo, c, fc = c, d_, fd
                d_ = lo + gr * (hi - lo)
                fd = nll(d_)
        temps[i] = math.exp((lo + hi) / 2)
    return temps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--cal", required=True, help="sealed cal panel json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--freeze-layers", type=int, default=0)
    ap.add_argument("--steps-cap", type=int, default=0, help="0 = full epochs")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    t0 = time.time()
    rows = load_pool(a.pool)
    enc, tok, info = E.load(a.snapshot)
    if a.smoke:
        rows = rows[:2048]
        a.epochs = 1
        a.steps_cap = 200
    order = list(range(len(rows)))
    random.Random(a.seed).shuffle(order)
    rows = [rows[i] for i in order]
    pack = to_pack(rows)
    cal_rows = []
    for r in json.loads(Path(a.cal).read_text(encoding="utf-8")):
        e = D.encode_row(r, tok)
        if e is not None:
            cal_rows.append(e)
    cal_pack = to_pack(cal_rows)
    data_s = time.time() - t0

    torch.manual_seed(a.seed)
    model = M.FrameEars(enc, D.N_REL, freeze_layers=a.freeze_layers).to(device)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                            lr=a.lr, weight_decay=0.01)
    total = a.epochs * math.ceil(len(rows) / a.batch)
    if a.steps_cap:
        total = min(total, a.steps_cap)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(total, 1))
    g = torch.Generator().manual_seed(a.seed + 7)
    use_amp = device.type == "cuda"
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
            b = batch(pack, idx, device)
            t_b = time.time()
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16,
                                enabled=use_amp):
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
    # dev act accuracy (monitoring): first 2048 pool rows after the shuffled order
    with torch.no_grad():
        cor = tot = 0
        sub = {k: v[:2048].to(device) for k, v in pack.items()}
        o = model(sub["ids"], sub["mask"])
        cor = int((o["act"].argmax(-1) == sub["act"]).sum())
        tot = sub["ids"].shape[0]
    temps = fit_temperatures(model, cal_pack)
    model.temps.copy_(temps)
    torch.save({"state": model.state_dict(), "seed": a.seed,
                "temps": temps, "encoder_params": info["params"],
                "freeze_layers": a.freeze_layers}, out / "ear.pt")
    meta = {"seed": a.seed, "epochs": a.epochs, "batch": a.batch, "lr": a.lr,
            "steps": step, "params": M.n_params(model),
            "params_trainable": M.n_params_trainable(model),
            "pool": len(rows), "device": str(device),
            "sec_per_step": train_s / max(step, 1), "train_sec": train_s,
            "data_sec": data_s, "dev_act_acc": cor / max(tot, 1),
            "tokens_per_sec_200": tokens_at_200,
            "projected_min": (tokens_at_200 or 0) and
            (train_s / max(step, 1) * total / 60),
            "temps": [float(x) for x in temps],
            "freeze_layers": a.freeze_layers, "loss_log": log}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in meta.items() if k != "loss_log"}, indent=1))


if __name__ == "__main__":
    main()
