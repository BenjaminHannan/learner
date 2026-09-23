#!/usr/bin/env python3
"""Experiment 120b — fixed fine-tune trainer (frozen copy of
scripts/fable_talker120_train.py with EXACTLY ONE change).

THE ONE CHANGE (the whole fix): the target loss mask boundary.
  BEFORE (fable_talker120_train.py:150-151):
      tgt_mask = (pos > pre) & (pos <= torch.tensor(...))
  AFTER (this file, search FIX-120b):
      tgt_mask = (pos >= pre) & (pos <= torch.tensor(...))

Why: token predictions cover sequence positions 1..T-1, and the first target
token sits at index pre (0-based) of ids = prefix + target. `pos > pre`
excluded pos == pre from the loss, so the FIRST target token of every pair
was never supervised in exp 120's GPU fine-tune. At decode, step 0's mixture
is unsupervised (p_gen saturates to 1.0, copy attention diffuse) and greedy
emits vocab junk ("ing", ":", "s") — the boundary-junk bucket (303/313 of the
unfaithful raw decodes, diag-full.json). Everything else — recipe, data,
seeds, hyper-parameters — is identical to exp 120.

Usage (Mac smoke, seed 12001, 100 steps):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \\
    scripts/fable_talker120b_train.py --ckpt <talker101 ckpt> \\
    --tok artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json \\
    --data artifacts/fable-talker120-20260922/data --out <dir> \\
    --steps 100 --bs 2 --ctx 256 --lr 1e-4 --seed 12001
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_talker120_mouth import Codec, serialize  # noqa: E402
from fable_talker101_model import Talker101  # noqa: E402


def encode_pair(codec: Codec, record: dict, sentence: str, ctx: int):
    pre = codec.encode(serialize(record))
    tgt = codec.encode(" " + sentence) + [codec.eos]
    # keep the whole target; truncate the prefix from the left if needed
    if len(pre) + len(tgt) > ctx:
        pre = pre[-(ctx - len(tgt)):]
        assert len(pre) > 0
    ids = pre + tgt
    return ids, len(pre)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tok", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--bs", type=int, default=2)
    ap.add_argument("--ctx", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--warmup", type=int, default=None)
    ap.add_argument("--seed", type=int, default=12001)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args(argv)

    import torch
    torch.set_num_threads(1)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    os.makedirs(args.out, exist_ok=True)
    device = args.device
    use_amp = device.startswith("cuda")

    codec = Codec(args.tok)
    rows = [json.loads(x) for x in
            (Path(args.data) / "train.jsonl").read_text(encoding="utf-8").splitlines() if x]
    pairs = [encode_pair(codec, r["record"], r["sentence"], args.ctx) for r in rows]
    max_pre = max(p for _, p in pairs)
    max_len = max(len(ids) for ids, _ in pairs)
    print(json.dumps({"pairs": len(pairs), "max_prefix": max_pre,
                      "max_len": max_len, "ctx": args.ctx}), flush=True)

    ck = torch.load(args.ckpt, map_location=device, weights_only=False)
    model = Talker101().to(device)
    model.load_state_dict(ck["model"])
    if ck.get("cfg", {}).get("ctx", 512) != 512:
        print(json.dumps({"warning": "base ckpt ctx differs; ours fixed at 512-table model"}))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr,
                            betas=(0.9, 0.95), weight_decay=0.1)

    steps_per_epoch = max(1, (len(pairs) + args.bs - 1) // args.bs)
    if args.steps is not None:
        total_steps = args.steps
    elif args.epochs is not None:
        total_steps = args.epochs * steps_per_epoch
    else:
        raise ValueError("pass --steps or --epochs")
    warmup = args.warmup if args.warmup is not None else max(1, total_steps // 10)

    log = open(os.path.join(args.out, "fable_talker120b_log.jsonl"), "a")
    model.train()
    t0 = time.time()
    step, first20, last20 = 0, [], []
    order = list(range(len(pairs)))
    while step < total_steps:
        random.shuffle(order)
        for b0 in range(0, len(order), args.bs):
            if step >= total_steps:
                break
            batch = [pairs[i] for i in order[b0:b0 + args.bs]]
            L = max(len(ids) for ids, _ in batch)
            xb = torch.zeros(len(batch), L, dtype=torch.long)
            pre_len = []
            for bi, (ids, pl) in enumerate(batch):
                xb[bi, :len(ids)] = torch.tensor(ids, dtype=torch.long)
                pre_len.append(pl)
            xb = xb.to(device)
            frac = step / max(1, total_steps)
            lr = args.lr * min(1.0, (step + 1) / max(1, warmup)) * (
                0.5 * (1 + math.cos(math.pi * min(1.0, max(
                    0.0, (frac * total_steps - warmup) / max(1, total_steps - warmup))))))
            for g in opt.param_groups:
                g["lr"] = lr
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
                out = model(xb)
                logp = torch.log_softmax(out["logits"], dim=-1)
                T = xb.shape[1]
                # predict positions 1..T-1 from states 0..T-2
                pv = logp[:, :-1, :].gather(-1, xb[:, 1:].unsqueeze(-1)).squeeze(-1).exp()
                attn = out["copy_attn"][:, :-1, :]
                match = (xb[:, 1:].unsqueeze(-1) == xb.unsqueeze(1))
                kk = torch.arange(T, device=device).unsqueeze(0)
                jj = torch.arange(1, T, device=device).unsqueeze(1)
                causal = (kk < jj)
                pc = (attn * match * causal).sum(-1).clamp_min(1e-12)
                pg = out["p_gen"][:, :-1, 0]
                mix = (pg * pv + (1 - pg) * pc).clamp_min(1e-12)
                nll = -torch.log(mix)
                pre = torch.tensor(pre_len, device=device).unsqueeze(1)
                # predictions cover sequence positions 1..T-1
                pos = torch.arange(1, T, device=device).unsqueeze(0)
                # FIX-120b (the ONE change): target span = positions >= pre_len.
                # Token ids[pre_len] is the first target token, predicted at
                # pos == pre_len; `pos > pre` dropped it from every loss.
                # (Right-pad is id 0 = <eos>; only the length mask excludes it.)
                tgt_mask = (pos >= pre) & (pos <= torch.tensor(
                    [len(ids) for ids, _ in batch], device=device).unsqueeze(1))
                loss = (nll * tgt_mask).sum() / tgt_mask.sum().clamp_min(1)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            step += 1
            lv = float(loss.detach())
            if len(first20) < 20:
                first20.append(lv)
            last20.append(lv)
            if len(last20) > 20:
                last20.pop(0)
            if step % 10 == 0 or step == total_steps:
                rec = {"step": step, "loss": round(lv, 4), "lr": round(lr, 8),
                        "p_gen": round(float(out["p_gen"].mean().detach()), 4),
                        "tok_per_s": round(sum(len(ids) for ids, _ in batch)
                                           / max(1e-6, time.time() - t0), 1)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(rec, flush=True)
            if step % 50 == 0 or step == total_steps:
                torch.save({"model": {k: v.cpu() for k, v in model.state_dict().items()},
                            "opt": opt.state_dict(), "step": step,
                            "seed": args.seed, "lr": args.lr},
                           os.path.join(args.out, "fable_talker120b_ckpt_last.pt"))
    log.close()
    summary = {"done": True, "step": step, "seed": args.seed,
               "first20_mean": round(sum(first20) / max(1, len(first20)), 4),
               "last20_mean": round(sum(last20) / max(1, len(last20)), 4),
               "seconds": round(time.time() - t0, 2)}
    print(json.dumps(summary))
    (Path(args.out) / "train-summary.json").write_text(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
