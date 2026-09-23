#!/usr/bin/env python3
"""Exp 119g — trainer: 119f recipe verbatim, seeds 11911-11913 (Muse BUILD).

Runs on BensPC ONLY for the registered wave (Python, torch+cu128):
    python fable_ears119g_train.py --seed 11911 --pool C:\\Users\\benja\\ears119g\\pool119f.jsonl \\
        --snapshot <scibert-snapshot> --cal <47-cal.json> \\
        --out C:\\Users\\benja\\ears119g\\runs\\w-11911

Recipe sealed (119/119b/119f verbatim): batch 32, 2 epochs, AdamW lr 3e-5
cosine, wd 0.01, clip 1.0, bf16 autocast on CUDA, freeze 0, shuffle-by-seed,
CAL golden-section temperatures, total = 2*ceil(pool/32) asserted == 8838.
THE ONLY DIFFERENCE vs 119f: the head is RelCondEars
(scripts/fable_ears119g_model.py) and the gold relation is teacher-forced
(``rel_override=batch["rel"]``), so each relation trains its own span
pointers. The pool file is built by fable_ears119f_data.py (same 1:1
occupation replacement, same steps). Reading94/reading94b never touched here.

Smoke path (Mac CPU, NOT a registered seed): --steps-cap N --allow-cpu runs
N updates in fp32 on the CPU. Any --steps-cap > 0 forces --allow-cpu
semantics and is rejected for the registered wave.

Additive only: collate + recipe constants mirror fable_ears119_train.py by
import; fable_ears47_*/fable_ears119f_data imported read-only.
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
import fable_ears119f_data as D119f  # noqa: E402  (pool builder + MAX_LEN override)
import fable_ears119_train as T119  # noqa: E402  (collate + recipe mirror)
import fable_ears119g_model as M119g  # noqa: E402  (RelCondEars; the one change)
import fable_ears47_model as M  # noqa: E402  (loss_fn, n_params)
import fable_ears47_encoder as E  # noqa: E402
import fable_ears47_train as T47  # noqa: E402

assert T47.MAX_LEN == D119f.B.MAX119 == 192, T47.MAX_LEN

SEEDS119G = (11911, 11912, 11913)
STEPS119G = 8838  # 2 * ceil(141398 / 32); pool identical to 119f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--cal", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--freeze-layers", type=int, default=0)
    ap.add_argument("--steps-cap", type=int, default=0)
    ap.add_argument("--allow-cpu", action="store_true")
    a = ap.parse_args()
    assert a.seed in SEEDS119G, f"registered seeds are {SEEDS119G}"
    assert a.epochs == 2 and a.batch == 32 and abs(a.lr - 3e-5) < 1e-12 \
        and a.freeze_layers == 0, \
        "registered recipe is fixed (2 epochs, batch 32, lr 3e-5, freeze 0)"
    smoke = bool(a.steps_cap)
    if not smoke:
        assert not a.allow_cpu, "registered wave runs on the BensPC GPU"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not smoke:
        assert device.type == "cuda", "registered wave runs on the BensPC GPU"
    else:
        assert a.allow_cpu, "CPU training only with --allow-cpu (smoke)"
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
    model = M119g.RelCondEars(enc, D.N_REL,
                              freeze_layers=a.freeze_layers).to(device)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                            lr=a.lr, weight_decay=0.01)
    total = a.epochs * math.ceil(len(rows) / a.batch)
    if not smoke:
        assert total == STEPS119G, f"steps {total} != {STEPS119G} (pool changed?)"
    else:
        total = min(total, a.steps_cap)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(total, 1))
    log = []
    step = 0
    t_start = time.time()
    tokens_at_200 = None
    done = False
    use_amp = (device.type == "cuda")
    model.train()
    while not done:
        for s in range(0, len(rows), a.batch):
            if step >= total:
                done = True
                break
            idx = torch.arange(s, min(s + a.batch, len(rows)))
            b = T119.collate(rows, idx, device)
            t_b = time.time()
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16,
                                enabled=use_amp):
                # THE ONE CHANGE: teacher-forced gold relation for the pointers.
                o = model(b["ids"], b["mask"], rel_override=b["rel"])
                loss = M.loss_fn(o, b)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                (p for p in model.parameters() if p.requires_grad), 1.0)
            opt.step()
            sched.step()
            step += 1
            if step % 200 == 0 or step == total:
                print(f"[{a.seed}] step {step}/{total} loss {float(loss.detach()):.4f} "
                      f"{(time.time() - t_start) / step:.3f}s/step", flush=True)
                log.append({"step": step, "loss": float(loss.detach())})
    train_s = time.time() - t_start

    if smoke:
        meta = {"seed": a.seed, "exp": "119g-smoke", "steps": step,
                "pool": len(rows), "device": str(device),
                "sec_per_step": train_s / max(step, 1), "train_sec": train_s,
                "data_sec": data_s, "loss_log": log}
        (out / "meta-smoke.json").write_text(json.dumps(meta, indent=1),
                                             encoding="utf-8")
        print(json.dumps(meta, indent=1))
        return

    model.eval()
    with torch.no_grad():
        sub = {k: v[:2048].to(device) for k, v in T47.to_pack(rows).items()}
        o = model(sub["ids"], sub["mask"])
        cor = int((o["act"].argmax(-1) == sub["act"]).sum())
        tot = sub["ids"].shape[0]
    # Temperatures by the unchanged 47 rule on CAL (base pointers; same rule).
    temps = T47.fit_temperatures(model, cal_pack)
    model.temps.copy_(temps)
    torch.save({"state": model.state_dict(), "seed": a.seed,
                "temps": temps, "encoder_params": info["params"],
                "freeze_layers": a.freeze_layers}, out / "ear.pt")
    meta = {"seed": a.seed, "exp": "119g", "epochs": a.epochs, "batch": a.batch,
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
