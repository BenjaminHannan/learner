#!/usr/bin/env python3
"""lis-300 fine-tune: MiniCPM5-1B -> listener (LoRA on every linear layer, loss on the frame only).

python claude_lis300_train.py --model DIR --data DIR --out DIR [--epochs 2] [--lr 2e-4] [--rank 32]
       [--batch 16] [--max-len 256] [--max-minutes 150] [--limit N] [--merge]

Writes OUT/adapter/, OUT/merged/ (with --merge), OUT/train_log.jsonl, OUT/summary.json.
Plain torch loop, no Trainer. bf16 on CUDA, fp32 on CPU (CPU only for smoke tests).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_rows(p, limit=None):
    rows = [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows[:limit] if limit else rows


def encode(tok, row, max_len):
    p = tok(row["prompt"], add_special_tokens=False)["input_ids"]
    t = tok(row["target"], add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    ids = ([tok.bos_token_id] if tok.bos_token_id is not None else []) + p + t
    labels = [-100] * (len(ids) - len(t)) + t
    return ids[:max_len], labels[:max_len]


def batches(encoded, bs, pad_id, shuffle, rng):
    idx = list(range(len(encoded)))
    if shuffle:
        rng.shuffle(idx)
    for i in range(0, len(idx), bs):
        chunk = [encoded[j] for j in idx[i:i + bs]]
        L = max(len(x[0]) for x in chunk)
        ids = torch.full((len(chunk), L), pad_id)
        lab = torch.full((len(chunk), L), -100)
        att = torch.zeros((len(chunk), L), dtype=torch.long)
        for k, (a, b) in enumerate(chunk):
            ids[k, :len(a)] = torch.tensor(a)
            lab[k, :len(b)] = torch.tensor(b)
            att[k, :len(a)] = 1
        yield ids, lab, att


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--max-minutes", type=float, default=150)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--seed", type=int, default=300)
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    rng = random.Random(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    tok = AutoTokenizer.from_pretrained(a.model)
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(a.model, dtype=dtype).to(dev)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    cfg = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, cfg)
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_all = sum(p.numel() for p in model.parameters())
    train = [encode(tok, r, a.max_len) for r in load_rows(Path(a.data) / "train.jsonl", a.limit)]
    devrows = [encode(tok, r, a.max_len) for r in load_rows(Path(a.data) / "dev.jsonl", a.limit and max(8, a.limit // 10))]
    steps_per_epoch = math.ceil(len(train) / a.batch)
    total = max(1, int(steps_per_epoch * a.epochs))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    warm = max(1, total // 30)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total))))
    log = open(out / "train_log.jsonl", "w")
    t0 = time.time()
    step, toks, stopped = 0, 0, None
    model.train()
    while step < total and stopped is None:
        for ids, lab, att in batches(train, a.batch, pad_id, True, rng):
            ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev)
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1
            toks += int(att.sum())
            if step % 20 == 0 or step == 1:
                el = time.time() - t0
                rec = {"step": step, "total": total, "loss": round(loss.item(), 4),
                       "lr": sched.get_last_lr()[0], "tok_per_s": round(toks / el, 1), "min": round(el / 60, 2)}
                log.write(json.dumps(rec) + "\n"); log.flush()
                print(rec, flush=True)
            if (time.time() - t0) / 60 > a.max_minutes:
                stopped = "time_cap"
                break
            if step >= total:
                break
    model.eval()
    dl, dn = 0.0, 0
    with torch.no_grad():
        for ids, lab, att in batches(devrows, a.batch, pad_id, False, rng):
            ids, lab, att = ids.to(dev), lab.to(dev), att.to(dev)
            dl += model(input_ids=ids, attention_mask=att, labels=lab).loss.item() * ids.shape[0]
            dn += ids.shape[0]
    model.save_pretrained(out / "adapter")
    tok.save_pretrained(out / "adapter")
    if a.merge:
        merged = model.merge_and_unload()
        merged.save_pretrained(out / "merged", safe_serialization=True)
        tok.save_pretrained(out / "merged")
    summ = {"steps": step, "planned_steps": total, "stopped": stopped, "train_rows": len(train),
            "dev_rows": len(devrows), "dev_loss": dl / max(1, dn), "trainable_params": n_train,
            "all_params": n_all, "minutes": round((time.time() - t0) / 60, 2),
            "tok_per_s": round(toks / max(1e-9, time.time() - t0), 1), "device": dev, "args": vars(a)}
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
