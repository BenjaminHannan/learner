#!/usr/bin/env python3
"""FU2 (design/wordprob/PREREG.md): fine-tune pretrained SmolLM2-360M on the word-problem STEPS targets.

Prompt = question + "\\n"; target = scratchpad + EOS; loss on target only. bf16, AdamW, one epoch capped at --max-steps.
Eval = batched greedy generation on the same seeded 2,000-row samples as train_wp.py (same shuffle, same answer parser).

  python scripts/wordprob/train_smol.py --data DIR --out DIR [--max-steps 3000] [--device cuda]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_wp import SPLITS, lr_at, parse_answer, read_jsonl  # noqa: E402  same parser, schedule, splits

MODEL = "HuggingFaceTB/SmolLM2-360M"


def sample_rows(rows, eval_n, seed):
    """Identical to train_wp.evaluate's sampling."""
    rows = list(rows)
    random.Random(seed).shuffle(rows)
    return rows[:eval_n]


def encode_example(tok, row, eos_id):
    """-> (ids, n_prompt); loss applies to ids[n_prompt:] (scratchpad + EOS)."""
    p = tok.encode(row["question"] + "\n", add_special_tokens=False)
    t = tok.encode(row["scratchpad"], add_special_tokens=False) + [eos_id]
    return p + t, len(p)


def make_batch(examples, pad_id):
    """Right-padded. labels = -100 except target tokens. Returns input_ids, attention_mask, labels."""
    L = max(len(e[0]) for e in examples)
    x = torch.full((len(examples), L), pad_id, dtype=torch.long)
    am = torch.zeros((len(examples), L), dtype=torch.long)
    lab = torch.full((len(examples), L), -100, dtype=torch.long)
    for b, (ids, npr) in enumerate(examples):
        x[b, :len(ids)] = torch.tensor(ids)
        am[b, :len(ids)] = 1
        lab[b, npr:len(ids)] = torch.tensor(ids[npr:])
    return x, am, lab


def lm_loss_sum(model, x, am, lab):
    """Sum of token CE over target positions (shifted), and the target-token count."""
    logits = model(input_ids=x, attention_mask=am).logits
    sl, sy = logits[:, :-1].float(), lab[:, 1:]
    loss = F.cross_entropy(sl.reshape(-1, sl.size(-1)), sy.reshape(-1), ignore_index=-100, reduction="sum")
    return loss, int((sy != -100).sum())


@torch.no_grad()
def generate_batch(model, tok, prompts, device, max_new=120, bs=64, pad_id=0, eos_id=1):
    """Greedy, left-padded. Returns decoded continuations in input order."""
    model.eval()
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    out = [None] * len(prompts)
    for s in range(0, len(order), bs):
        idxs = order[s:s + bs]
        enc = [tok.encode(prompts[i], add_special_tokens=False) for i in idxs]
        P = max(len(e) for e in enc)
        ids = torch.full((len(enc), P), pad_id, dtype=torch.long)
        am = torch.zeros((len(enc), P), dtype=torch.long)
        for b, e in enumerate(enc):
            ids[b, P - len(e):] = torch.tensor(e)
            am[b, P - len(e):] = 1
        g = model.generate(input_ids=ids.to(device), attention_mask=am.to(device), max_new_tokens=max_new,
                           do_sample=False, pad_token_id=pad_id, eos_token_id=eos_id)
        for b, i in enumerate(idxs):
            out[i] = tok.decode(g[b, P:].tolist(), skip_special_tokens=True)
    return out


def n_steps_of(r):
    return int(r["n_steps"] if "n_steps" in r else r["steps"])


def evaluate(model, tok, rows, device, eval_n, seed, max_new=120, bs=64, pad_id=0, eos_id=1):
    rows = sample_rows(rows, eval_n, seed)
    preds = generate_batch(model, tok, [r["question"] + "\n" for r in rows], device, max_new, bs, pad_id, eos_id)
    hits, by, samples = 0, {}, []
    for r, p in zip(rows, preds):
        ok = parse_answer(p) == int(r["answer"])
        hits += ok
        c = by.setdefault(n_steps_of(r), [0, 0])
        c[0] += ok
        c[1] += 1
        if len(samples) < 10:
            samples.append({"id": r.get("id"), "question": r["question"], "gold": int(r["answer"]),
                            "pred_text": p, "correct": bool(ok)})
    n = len(rows)
    return {"n": n, "correct": hits, "accuracy": hits / n if n else None,
            "by_n_steps": {str(k): {"n": v[1], "correct": v[0], "accuracy": v[0] / v[1]}
                           for k, v in sorted(by.items())}}, samples


def train(args, model=None, tok=None):
    t0 = time.time()
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = args.device
    cuda = device.startswith("cuda")
    if model is None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(args.model)
        dtype = torch.bfloat16 if cuda else torch.float32
        if args.random_init:  # size control: same architecture and tokenizer, no pretrained weights
            from transformers import AutoConfig
            model = AutoModelForCausalLM.from_config(AutoConfig.from_pretrained(args.model), torch_dtype=dtype)
        else:
            model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype)
    eos_id = tok.eos_token_id
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else eos_id
    if args.grad_ckpt:
        model.gradient_checkpointing_enable()
    model.to(device)

    train_rows = read_jsonl(data / "train.jsonl")
    if args.train_n:
        train_rows = train_rows[:args.train_n]
    ex = [encode_example(tok, r, eos_id) for r in train_rows]
    rng.shuffle(ex)
    n_steps = min(args.max_steps, len(ex) // args.batch)        # one epoch at most
    params = sum(p.numel() for p in model.parameters())
    print(f"model={args.model} params={params} train_rows={len(ex)} steps={n_steps} batch={args.batch} micro={args.micro} "
          f"mean_len={sum(len(e[0]) for e in ex) / len(ex):.1f} device={device}", flush=True)

    decay = [p for p in model.parameters() if p.dim() >= 2]
    nodecay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": args.wd}, {"params": nodecay, "weight_decay": 0.0}],
                            lr=args.lr, betas=(0.9, 0.95))
    loss_log, step_times = [], []
    model.train()
    for step in range(n_steps):
        ts = time.time()
        for g in opt.param_groups:
            g["lr"] = lr_at(step, n_steps, args.lr, args.warmup)
        batch = ex[step * args.batch:(step + 1) * args.batch]
        n_tgt = sum(len(e[0]) - e[1] for e in batch)
        tot = 0.0
        for s in range(0, len(batch), args.micro):
            x, am, lab = make_batch(batch[s:s + args.micro], pad_id)
            loss, _ = lm_loss_sum(model, x.to(device), am.to(device), lab.to(device))
            (loss / n_tgt).backward()
            tot += loss.item() / n_tgt
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step_times.append(time.time() - ts)
        loss_log.append(tot)
        if (step + 1) % args.log_every == 0 or step == 0:
            r = loss_log[-args.log_every:]
            print(f"step {step + 1}/{n_steps} loss {sum(r) / len(r):.4f} lr {opt.param_groups[0]['lr']:.2e} "
                  f"{time.time() - t0:.0f}s", flush=True)

    manifest = data / "MANIFEST.json"
    msha = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None
    tail = loss_log[-50:]
    result = {"arm": "smolrand_steps" if args.random_init else "smol_steps", "random_init": args.random_init, "model": args.model, "steps": n_steps, "params": params, "seed": args.seed,
              "train_rows": len(ex), "final_train_loss": sum(tail) / len(tail) if tail else None,
              "mean_step_seconds": sum(step_times) / len(step_times) if step_times else None, "manifest_sha256": msha,
              "accuracy": {}, "by_n_steps": {}, "eval_n": {}, "samples": {}}
    for split in SPLITS:
        p = data / f"{split}.jsonl"
        if not p.is_file():
            result["accuracy"][split] = None
            continue
        r, samples = evaluate(model, tok, read_jsonl(p), device, args.eval_n, args.seed, args.max_new, args.eval_bs,
                              pad_id, eos_id)
        result["accuracy"][split] = r["accuracy"]
        result["by_n_steps"][split] = r["by_n_steps"]
        result["eval_n"][split] = r["n"]
        result["samples"][split] = samples
        print(f"EVAL {split}: {r['correct']}/{r['n']} = {r['accuracy']:.4f}", flush=True)
    result["wall_seconds"] = time.time() - t0
    (out / "final.json").write_text(json.dumps(result, indent=1))
    return result


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--max-steps", type=int, default=3000)
    ap.add_argument("--batch", type=int, default=64, help="rows per optimizer step")
    ap.add_argument("--micro", type=int, default=32, help="rows per forward (grad accumulation)")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--eval-n", type=int, default=2000)
    ap.add_argument("--eval-bs", type=int, default=64)
    ap.add_argument("--max-new", type=int, default=120)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--train-n", type=int, default=0)
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--grad-ckpt", action="store_true")
    ap.add_argument("--random-init", action="store_true", help="same architecture, randomly initialised (size control)")
    return ap.parse_args(argv)


if __name__ == "__main__":
    train(parse_args())
