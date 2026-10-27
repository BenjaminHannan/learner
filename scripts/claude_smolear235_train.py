#!/usr/bin/env python3
"""Exp 235 -- fine-tune SmolLM2-360M-Instruct as the ear (runs on BensPC GPU).

Full fine-tune (all weights), AdamW, bf16 autocast over fp32 master weights,
loss on the frame tokens only. Then: dev-split eval (held-out templates) with
the brake, GPU latency, and a bf16 safetensors checkpoint + its SHA-256.

python claude_smolear235_train.py --base DIR --data DIR --out DIR [--epochs 2]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402


def load_rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def encode(tok, row, max_len=192):
    p = tok.enc(E.prompt_text(row["turn"]))
    t = tok.enc(E.target_text(row["frames"]))
    ids = (p + t)[:max_len]
    lab = ([-100] * len(p) + t)[:max_len]
    return ids, lab


def batches(enc, bs, rng):
    idx = list(range(len(enc)))
    rng.shuffle(idx)
    for i in range(0, len(idx) - bs + 1, bs):
        yield [enc[j] for j in idx[i:i + bs]]


def collate(b, device):
    L = max(len(x[0]) for x in b)
    L = ((L + 31) // 32) * 32  # few fixed shapes (avoids slow re-tuning on new shapes)
    ids = torch.full((len(b), L), 2, dtype=torch.long)
    lab = torch.full((len(b), L), -100, dtype=torch.long)
    msk = torch.zeros((len(b), L), dtype=torch.bool)
    for i, (x, y) in enumerate(b):
        ids[i, :len(x)] = torch.tensor(x)
        lab[i, :len(y)] = torch.tensor(y)
        msk[i, :len(x)] = True
    return ids.to(device), lab.to(device), msk.to(device)


def frames_equal(pred_lines_kept, gold_lines):
    g = sorted(l for l in gold_lines if l != "NONE")
    return sorted(pred_lines_kept) == sorted(g)


def as_line(f):
    if f["act"] == "TEACH":
        return f"TEACH | {f['subject']} | {f['relation']} | {f['value']}"
    return f"ASK | {f['subject']} | {' > '.join(f['relation'])}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=4e-5)
    ap.add_argument("--seed", type=int, default=235)
    ap.add_argument("--dev-n", type=int, default=800)
    ap.add_argument("--max-train-min", type=float, default=22.0)
    ap.add_argument("--accum", type=int, default=2,
                    help="gradient accumulation steps; micro-batch = bs // accum")
    ap.add_argument("--speed-limit", type=float, default=1.0,
                    help="stop if optimizer steps 200-300 average above this many s/step")
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    rng = random.Random(a.seed)
    dev = "cuda"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = Path(a.base)
    tok = E.Tok(base / "tokenizer.json")
    model = E.load_state(E.SmolLM(), base / "model.safetensors").to(dev).float()
    train = load_rows(Path(a.data) / "train.jsonl")
    devrows = load_rows(Path(a.data) / "dev.jsonl")
    enc = [encode(tok, r) for r in train]
    steps_per_epoch = len(enc) // a.bs
    total = int(steps_per_epoch * a.epochs)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.0, betas=(0.9, 0.95))
    warm = max(20, total // 30)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total))))
    log = open(out / "train_log.txt", "w")
    t0 = time.time()
    step = 0
    model.train()
    done = False
    mb = a.bs // a.accum
    t200 = None
    while not done:
        for b in batches(enc, a.bs, rng):
            opt.zero_grad(set_to_none=True)
            ntok = sum(sum(1 for y in x[1][1:] if y != -100) for x in b)
            loss_sum = 0.0
            for k in range(a.accum):
                ids, lab, msk = collate(b[k * mb:(k + 1) * mb], dev)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    hid = model(ids, pad_mask=msk, hidden_only=True)
                    tgt = lab[:, 1:]
                    sel = tgt != -100
                    logits = F.linear(hid[:, :-1][sel], model.embed_tokens.weight)
                l = F.cross_entropy(logits.float(), tgt[sel], reduction="sum") / ntok
                l.backward()
                loss_sum += float(l)
                del hid, logits, l
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            step += 1
            if step == 200:
                t200 = time.time()
            if step % 25 == 0:
                msg = (f"step {step}/{total} loss {loss_sum:.4f} t {time.time() - t0:.0f}s "
                       f"alloc {torch.cuda.memory_allocated() / 2**20:.0f}MiB "
                       f"reserved {torch.cuda.memory_reserved() / 2**20:.0f}MiB "
                       f"peak {torch.cuda.max_memory_allocated() / 2**20:.0f}MiB")
                print(msg, flush=True)
                log.write(msg + "\n")
                log.flush()
            if step == 300 and t200 is not None:
                sps = (time.time() - t200) / 100
                if sps > a.speed_limit:
                    msg = (f"SPEED STOP: steps 200-300 averaged {sps:.2f} s/step > {a.speed_limit}; "
                           f"alloc {torch.cuda.memory_allocated() / 2**20:.0f}MiB reserved "
                           f"{torch.cuda.memory_reserved() / 2**20:.0f}MiB peak "
                           f"{torch.cuda.max_memory_allocated() / 2**20:.0f}MiB")
                    print(msg, flush=True)
                    log.write(msg + "\n")
                    log.close()
                    raise SystemExit(3)
            if step >= total or (time.time() - t0) / 60 > a.max_train_min:
                done = True
                break
    loss = torch.tensor(loss_sum)
    train_s = time.time() - t0
    model.eval()
    # save bf16 checkpoint
    from safetensors.torch import save_file
    sd = {k: v.detach().to(torch.bfloat16).contiguous().cpu() for k, v in model.state_dict().items()}
    ck = out / "smolear235.safetensors"
    save_file(sd, str(ck))
    h = hashlib.sha256(ck.read_bytes()).hexdigest()
    (out / "CKPT.sha256.txt").write_text(f"{h}  smolear235.safetensors\n")
    # dev eval in bf16 (same dtype as the frozen checkpoint)
    model = model.to(torch.bfloat16)
    rows = devrows[:a.dev_n] if len(devrows) > a.dev_n else devrows
    rng2 = random.Random(7)
    rows = rng2.sample(devrows, min(a.dev_n, len(devrows)))
    res, lat = [], []
    gd = E.GraphDecoder(model, tok)
    agree = 0
    for r in rows[:100]:
        agree += gd.generate(r["turn"]) == E.generate(model, tok, r["turn"], device=dev)
    for r in rows:
        torch.cuda.synchronize()
        t = time.perf_counter()
        raw = gd.generate(r["turn"])
        kept, dropped = E.brake(E.parse_frames(raw), r["turn"])
        torch.cuda.synchronize()
        lat.append((time.perf_counter() - t) * 1000)
        kl = [as_line(f) for f in kept]
        res.append(dict(turn=r["turn"], gold=r["frames"], raw=raw, kept=kl, family=r["family"],
                        tid=r["tid"], ok=frames_equal(kl, r["frames"])))
    fam = {}
    for x in res:
        fam.setdefault(x["family"], [0, 0])
        fam[x["family"]][0] += x["ok"]
        fam[x["family"]][1] += 1
    summary = dict(steps=step, total_planned=total, train_seconds=round(train_s, 1),
                   final_loss=float(loss.item()), ckpt_sha256=h,
                   graph_vs_eager_agree_of_100=agree,
                   dev_exact=sum(x["ok"] for x in res), dev_n=len(res), dev_by_family=fam,
                   gpu_median_ms=statistics.median(lat), gpu_p90_ms=sorted(lat)[int(0.9 * len(lat))],
                   device=torch.cuda.get_device_name(0))
    (out / "dev_eval.json").write_text(json.dumps(dict(summary=summary, rows=res), indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
