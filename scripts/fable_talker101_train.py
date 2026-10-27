"""Exp 101 training: bf16 autocast (CUDA) / fp32 (CPU), AdamW, cosine+warmup, 1 pass.

Checkpoints every 10% of the planned run, val loss every 5%, resumable from a
checkpoint dir, JSON-lines logs. Flags: --device --max-steps --out (+ hyperparams).
No `transformers` import.
"""
import argparse, json, math, os, time
import numpy as np
import torch

from fable_talker101_model import Talker101, CFG


def batch_gen(bin_path, n_tok, ctx, bs, seed, start_pos=0):
    rng = np.random.default_rng(seed)
    data = np.memmap(bin_path, dtype=np.uint16, mode="r")
    n = len(data) if n_tok is None else min(n_tok, len(data))
    pos = start_pos
    while True:
        ix = rng.integers(0, max(1, n - ctx - 1), size=bs)
        x = np.stack([data[i:i + ctx + 1] for i in ix]).astype(np.int64)
        pos += bs * ctx
        yield torch.from_numpy(x[:, :-1]), torch.from_numpy(x[:, 1:]), pos


@torch.no_grad()
def val_loss(model, val_path, ctx, bs, n_batches, device):
    model.eval()
    data = np.memmap(val_path, dtype=np.uint16, mode="r")
    n = len(data)
    tot, cnt = 0.0, 0
    for b in range(n_batches):
        i = (b * bs * ctx) % max(1, n - ctx - 1)
        x = torch.from_numpy(np.stack(
            [data[(i + k * ctx) % (n - ctx - 1):][:ctx + 1] for k in range(bs)]).astype(np.int64))
        xb, yb = x[:, :-1].to(device), x[:, 1:].to(device)
        use_amp = device.startswith("cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
            out = model(xb, yb)
        tot += out["loss"].item() * xb.numel()
        cnt += xb.numel()
    model.train()
    return tot / max(1, cnt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", default="artifacts/fable-talker101-20260921")
    ap.add_argument("--ctx", type=int, default=512)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--resume", default=None)
    ap.add_argument("--full-tokens", type=int, default=None,
                    help="planned full-run train tokens; ckpt every 10%%, val every 5%% of it")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    os.makedirs(args.out, exist_ok=True)
    log = open(os.path.join(args.out, "fable_talker101_log.jsonl"), "a")
    device = args.device

    model = Talker101({**CFG, "ctx": args.ctx}).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    step, tokens_seen = 0, 0
    if args.resume:
        ck = torch.load(os.path.join(args.resume, "fable_talker101_ckpt_last.pt"),
                        map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step, tokens_seen = ck["step"], ck["tokens_seen"]
        print(f"resumed at step={step} tokens={tokens_seen}", flush=True)

    train_bin = os.path.join(args.data_dir, "fable_talker101_train.bin")
    val_bin = os.path.join(args.data_dir, "fable_talker101_val.bin")
    info = json.load(open(os.path.join(args.data_dir, "fable_talker101_token_counts.json")))
    total_tokens = args.full_tokens or info["train_tokens"]
    ckpt_every = max(1, int((args.max_steps or total_tokens // (args.bs * args.ctx)) * 0.10)) \
        if args.max_steps else max(1, int(total_tokens / (args.bs * args.ctx) * 0.10))
    val_every = max(1, ckpt_every // 2)
    if args.max_steps:
        total_steps = args.max_steps
    else:
        total_steps = total_tokens // (args.bs * args.ctx)  # one pass
    gen = batch_gen(train_bin, None, args.ctx, args.bs, args.seed + step)
    model.train()
    t0 = time.time()
    next_ckpt, next_val = ((step // ckpt_every) + 1) * ckpt_every, ((step // val_every) + 1) * val_every
    last_ckpt10 = -1
    while step < total_steps:
        xb, yb, _ = next(gen)
        xb, yb = xb.to(device), yb.to(device)
        frac = step / max(1, total_steps)
        lr = args.lr * min(1.0, (step + 1) / max(1, args.warmup)) * \
            (0.5 * (1 + math.cos(math.pi * min(1.0, max(0.0, (frac * total_steps - args.warmup) /
                                                        max(1, total_steps - args.warmup))))))
        for g in opt.param_groups:
            g["lr"] = lr
        opt.zero_grad()
        use_amp = device.startswith("cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
            out = model(xb, yb)
        out["loss"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step += 1
        tokens_seen += xb.numel()
        rec = {"step": step, "loss": round(out["loss"].item(), 4),
               "lr": round(lr, 8), "tokens_seen": tokens_seen,
               "p_gen": round(float(out["p_gen_mean"]), 4),
               "tok_per_s": round(tokens_seen / max(1e-6, time.time() - t0), 1)}
        if step % 10 == 0 or step == total_steps:
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print(rec, flush=True)
        done_frac = step / total_steps
        if step >= next_val or step == total_steps:
            vl = val_loss(model, val_bin, args.ctx, args.bs, 10, device)
            rec2 = {"step": step, "val_loss": round(vl, 4), "tokens_seen": tokens_seen}
            log.write(json.dumps(rec2) + "\n")
            log.flush()
            print(rec2, flush=True)
            next_val += val_every
        if (step >= next_ckpt or step == total_steps) and int(done_frac * 10) > last_ckpt10:
            last_ckpt10 = int(done_frac * 10)
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                        "step": step, "tokens_seen": tokens_seen},
                       os.path.join(args.out, f"fable_talker101_ckpt_{last_ckpt10:02d}.pt"))
            next_ckpt += ckpt_every
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                    "step": step, "tokens_seen": tokens_seen},
                   os.path.join(args.out, "fable_talker101_ckpt_last.pt"))
    log.close()
    print(json.dumps({"done": True, "step": step, "tokens_seen": tokens_seen}))


if __name__ == "__main__":
    main()
