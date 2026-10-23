#!/usr/bin/env python3
"""Word-problem trainer (design/wordprob/PREREG.md): a small char-level decoder-only transformer trained from scratch.

ANSWER arm target = "Answer: N"; STEPS arm target = the code-written scratchpad. Same data/steps/seed/optimizer.
Loss only on target tokens (+EOS). Eval = greedy decode, exact match on the integer after the final "Answer:".

  python scripts/wordprob/train_wp.py --data DIR --arm answer|steps --out DIR --steps N [--device cuda]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

PAD, EOS, UNK = 0, 1, 2
SPECIALS = ["<pad>", "<eos>", "<unk>"]
BASE_CHARS = "0123456789+-*/=().,:%$ \n"
SPLITS = ("dev", "heldout_template", "heldout_structure")
ANSWER_RE = re.compile(r"Answer:\s*(-?\d+)")


# ----------------------------------------------------------------------------- data
def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def target_text(row, arm):
    if arm == "answer":
        return f"Answer: {int(row['answer'])}"
    if arm == "steps":
        return row["scratchpad"]
    raise ValueError(arm)


def build_vocab(rows):
    chars = set(BASE_CHARS)
    for r in rows:
        chars.update(r["question"])
        chars.update(r["scratchpad"])
        chars.update(f"Answer: {int(r['answer'])}")
    chars.update("Answer:")
    return SPECIALS + sorted(chars)


class Tok:
    def __init__(self, vocab):
        self.vocab = list(vocab)
        self.idx = {c: i for i, c in enumerate(self.vocab)}

    def encode(self, s):
        return [self.idx.get(c, UNK) for c in s]

    def decode(self, ids):
        out = []
        for i in ids:
            if i == EOS:
                break
            if i > UNK:
                out.append(self.vocab[i])
        return "".join(out)


def encode_example(tok, row, arm):
    """-> (ids, n_prompt). Loss applies to ids[n_prompt:] (target chars + EOS)."""
    p = tok.encode(row["question"] + "\n")
    t = tok.encode(target_text(row, arm)) + [EOS]
    return p + t, len(p)


def make_batch(examples, ctx):
    """examples: list of (ids, n_prompt). Returns x, y, mask (mask=True only where y is a target token)."""
    L = min(max(len(e[0]) for e in examples), ctx + 1)
    B = len(examples)
    x = torch.full((B, L - 1), PAD, dtype=torch.long)
    y = torch.full((B, L - 1), PAD, dtype=torch.long)
    m = torch.zeros((B, L - 1), dtype=torch.bool)
    for b, (ids, npr) in enumerate(examples):
        ids = ids[:L]
        n = len(ids) - 1
        x[b, :n] = torch.tensor(ids[:-1])
        y[b, :n] = torch.tensor(ids[1:])
        m[b, max(npr - 1, 0):n] = True       # label j is ids[j+1]; the target starts at ids[npr]
    return x, y, m


# ----------------------------------------------------------------------------- model
class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.proj = nn.Linear(d, d, bias=False)
        self.fc1 = nn.Linear(d, 4 * d, bias=False)
        self.fc2 = nn.Linear(4 * d, d, bias=False)

    def forward(self, x, mask=None, cache=None):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        if cache is not None:
            if "k" in cache:
                k, v = torch.cat([cache["k"], k], 2), torch.cat([cache["v"], v], 2)
            cache["k"], cache["v"] = k, v
        if mask is None:
            a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        else:
            a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        return x + self.fc2(F.gelu(self.fc1(self.ln2(x))))


class GPT(nn.Module):
    def __init__(self, vocab, d=384, layers=6, heads=6, ctx=512):
        super().__init__()
        self.ctx = ctx
        self.tok = nn.Embedding(vocab, d)
        self.pos = nn.Embedding(ctx, d)
        self.blocks = nn.ModuleList(Block(d, heads) for _ in range(layers))
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab, bias=False)
        self.head.weight = self.tok.weight           # tied
        self.apply(self._init)
        for n, p in self.named_parameters():
            if n.endswith("proj.weight") or n.endswith("fc2.weight"):
                nn.init.normal_(p, std=0.02 / math.sqrt(2 * layers))

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, ids, pos=None, mask=None, caches=None):
        B, T = ids.shape
        if pos is None:
            pos = torch.arange(T, device=ids.device)[None]
        x = self.tok(ids) + self.pos(pos)
        for i, b in enumerate(self.blocks):
            x = b(x, mask, None if caches is None else caches[i])
        return self.head(self.ln(x))


def n_params(model):
    return sum(p.numel() for p in model.parameters())


# ----------------------------------------------------------------------------- decode / eval
def parse_answer(text):
    """Integer after the final 'Answer:' or None."""
    ms = ANSWER_RE.findall(text)
    return int(ms[-1]) if ms else None


@torch.no_grad()
def greedy(model, tok, prompts, device, max_new=200, bs=128, autocast=False):
    """prompts: list of str. Returns decoded strings. Left-padded batches with a KV cache."""
    model.eval()
    ctx = model.ctx
    order = sorted(range(len(prompts)), key=lambda i: len(prompts[i]))
    out = [None] * len(prompts)
    for s in range(0, len(order), bs):
        idxs = order[s:s + bs]
        enc = [tok.encode(prompts[i])[-(ctx - 1):] for i in idxs]
        B, P = len(enc), max(len(e) for e in enc)
        new = max(1, min(max_new, ctx - P))
        ids = torch.full((B, P), PAD, dtype=torch.long)
        valid = torch.zeros((B, P), dtype=torch.bool)
        for b, e in enumerate(enc):
            ids[b, P - len(e):] = torch.tensor(e)
            valid[b, P - len(e):] = True
        ids, valid = ids.to(device), valid.to(device)
        npad = (~valid).sum(1, keepdim=True)
        pos = (torch.arange(P, device=device)[None] - npad).clamp(min=0)
        causal = torch.tril(torch.ones(P, P, dtype=torch.bool, device=device))
        mask = (causal[None, None] & valid[:, None, None, :]) | torch.eye(P, dtype=torch.bool, device=device)[None, None]
        caches = [dict() for _ in model.blocks]
        gen = []
        done = torch.zeros(B, dtype=torch.bool, device=device)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=autocast):
            logits = model(ids, pos, mask, caches)[:, -1]
            for t in range(new):
                nxt = logits.float().argmax(-1)
                nxt = torch.where(done, torch.full_like(nxt, PAD), nxt)
                gen.append(nxt)
                done = done | (nxt == EOS)
                if bool(done.all()) or t == new - 1:
                    break
                valid = torch.cat([valid, torch.ones(B, 1, dtype=torch.bool, device=device)], 1)
                p1 = (P + t - npad).clamp(min=0)
                logits = model(nxt[:, None], p1, valid[:, None, None, :], caches)[:, -1]
        g = torch.stack(gen, 1).cpu().tolist()
        for b, i in enumerate(idxs):
            out[i] = tok.decode(g[b])
    return out


def evaluate(model, tok, rows, device, eval_n, seed, autocast=False, bs=128, max_new=200):
    rows = list(rows)
    random.Random(seed).shuffle(rows)
    rows = rows[:eval_n]
    preds = greedy(model, tok, [r["question"] + "\n" for r in rows], device, max_new=max_new, bs=bs, autocast=autocast)
    hits, by, samples = 0, {}, []
    for r, p in zip(rows, preds):
        ok = parse_answer(p) == int(r["answer"])
        hits += ok
        c = by.setdefault(str(r.get("steps")), [0, 0])
        c[0] += ok
        c[1] += 1
        if len(samples) < 10:
            samples.append({"id": r.get("id"), "question": r["question"], "gold": int(r["answer"]),
                            "pred_text": p, "correct": bool(ok)})
    n = len(rows)
    return {"n": n, "correct": hits, "accuracy": hits / n if n else None,
            "by_steps": {k: {"n": v[1], "correct": v[0], "accuracy": v[0] / v[1]} for k, v in sorted(by.items())}}, samples


# ----------------------------------------------------------------------------- train
def lr_at(step, total, base, warmup):
    if step < warmup:
        return base * (step + 1) / warmup
    prog = (step - warmup) / max(1, total - warmup)
    return base * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, prog))))     # cosine down to 10% of peak


def save_ckpt(path, model, vocab, args, step):
    torch.save({"model": model.state_dict(), "vocab": vocab, "step": step,
                "cfg": {"d": args.d, "layers": args.layers, "heads": args.heads, "ctx": args.ctx}}, path)


def train(args):
    t0 = time.time()
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    device = args.device
    use_amp = device.startswith("cuda")

    train_rows = read_jsonl(data / "train.jsonl")
    if args.train_n:
        train_rows = train_rows[: args.train_n]
    vocab = build_vocab(train_rows)
    tok = Tok(vocab)
    (out / "vocab.json").write_text(json.dumps(vocab))
    ex = [encode_example(tok, r, args.arm) for r in train_rows]
    dropped = sum(len(e[0]) > args.ctx + 1 for e in ex)
    ex = [e for e in ex if len(e[0]) <= args.ctx + 1]
    if not ex:
        raise SystemExit("no training examples")
    mean_len = sum(len(e[0]) for e in ex) / len(ex)
    rows_per_step = max(1, int(args.tokens_per_step / mean_len))
    micro = max(1, min(rows_per_step, int(args.micro_tokens / mean_len)))

    model = GPT(len(vocab), args.d, args.layers, args.heads, args.ctx).to(device)
    params = n_params(model)
    fwd = torch.compile(model) if args.compile else model
    decay = [p for p in model.parameters() if p.dim() >= 2]
    nodecay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": args.wd}, {"params": nodecay, "weight_decay": 0.0}],
                            lr=args.lr, betas=(0.9, 0.95))
    print(f"arm={args.arm} params={params} vocab={len(vocab)} train_rows={len(ex)} dropped_long={dropped} mean_len={mean_len:.1f} "
          f"rows/step={rows_per_step} micro={micro} device={device}", flush=True)

    ckpt_at = {max(1, round(args.steps * f)) for f in (0.25, 0.5, 0.75)}
    tokens_seen, loss_log, step_times = 0, [], []
    model.train()
    for step in range(args.steps):
        ts = time.time()
        for g in opt.param_groups:
            g["lr"] = lr_at(step, args.steps, args.lr, args.warmup)
        batch = [ex[rng.randrange(len(ex))] for _ in range(rows_per_step)]
        n_tgt = sum(len(e[0]) - e[1] for e in batch)
        tot = 0.0
        for s in range(0, len(batch), micro):
            x, y, m = make_batch(batch[s:s + micro], args.ctx)
            x, y, m = x.to(device), y.to(device), m.to(device)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=use_amp):
                logits = fwd(x)
            loss = F.cross_entropy(logits.float().view(-1, logits.size(-1)), y.view(-1), reduction="none")
            loss = (loss * m.view(-1)).sum() / n_tgt
            loss.backward()
            tot += loss.item()
            tokens_seen += int((x != PAD).sum())
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step_times.append(time.time() - ts)
        loss_log.append(tot)
        if (step + 1) % args.log_every == 0 or step == 0:
            recent = loss_log[-args.log_every:]
            print(f"step {step + 1}/{args.steps} loss {sum(recent) / len(recent):.4f} lr {opt.param_groups[0]['lr']:.2e} "
                  f"tokens {tokens_seen} {time.time() - t0:.0f}s", flush=True)
        if (step + 1) in ckpt_at:
            save_ckpt(out / f"ckpt-{step + 1}.pt", model, vocab, args, step + 1)
    save_ckpt(out / "final.pt", model, vocab, args, args.steps)

    manifest = data / "MANIFEST.json"
    msha = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else None
    tail = loss_log[-50:]
    result = {"arm": args.arm, "steps": args.steps, "params": params, "tokens_seen": tokens_seen, "seed": args.seed,
              "train_rows": len(ex), "dropped_long": dropped, "final_train_loss": sum(tail) / len(tail),
              "mean_step_seconds": sum(step_times) / len(step_times), "manifest_sha256": msha,
              "accuracy": {}, "by_steps": {}, "eval_n": {}, "samples": {}}
    for split in SPLITS:
        p = data / f"{split}.jsonl"
        if not p.is_file():
            result["accuracy"][split] = None
            continue
        r, samples = evaluate(model, tok, read_jsonl(p), device, args.eval_n, args.seed, autocast=use_amp)
        result["accuracy"][split] = r["accuracy"]
        result["by_steps"][split] = r["by_steps"]
        result["eval_n"][split] = r["n"]
        result["samples"][split] = samples
        print(f"EVAL {split}: {r['correct']}/{r['n']} = {r['accuracy']:.4f}", flush=True)
    result["wall_seconds"] = time.time() - t0
    (out / "final.json").write_text(json.dumps(result, indent=1))
    return result


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--arm", choices=("answer", "steps"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--eval-n", type=int, default=2000)
    ap.add_argument("--d", type=int, default=384)
    ap.add_argument("--layers", type=int, default=6)
    ap.add_argument("--heads", type=int, default=6)
    ap.add_argument("--ctx", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--tokens-per-step", type=int, default=65536)
    ap.add_argument("--micro-tokens", type=int, default=32768)
    ap.add_argument("--train-n", type=int, default=0, help="use only the first N train rows (tests)")
    ap.add_argument("--log-every", type=int, default=100)
    ap.add_argument("--compile", action="store_true")
    return ap.parse_args(argv)


if __name__ == "__main__":
    train(parse_args())
