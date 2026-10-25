"""Stage-1 "borrowed backbone" experiment: Qwen3.5 + LoRA on village QA rows (see PREREG-stage1.md).

Arms:  --arm a0   no training, 3-shot prompt, greedy
       --arm a    LoRA, answer-only loss
       --arm b    arm a + a looped middle block (layers [L, L+4) run --loops times, shared weights and LoRA)
Evaluation always runs on dev + validation (greedy, <= 24 new tokens, exact match after normalisation).
`--eval-loops N` forces another loop count at evaluation (the 1-pass lesion). `--load-adapter DIR` skips
training and evaluates a saved adapter. `--smoke` runs everything on CPU with a tiny random qwen3_5 config.
The village `test` split is never touched: the data dir only holds train/dev/validation rows.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import re
import sys
import os
import time
from pathlib import Path

import torch
import torch.nn.functional as F

PROMPT_TAIL = " [answer]"
MAX_NEW = 24
LORA_TARGETS = (r".*\.layers\.\d+\.(self_attn\.(q_proj|k_proj|v_proj|o_proj)"
                r"|linear_attn\.(in_proj_qkv|in_proj_z|in_proj_a|in_proj_b|out_proj)"
                r"|mlp\.(gate_proj|up_proj|down_proj))")


# ---------------------------------------------------------------- data

def read_jsonl(path, limit=None):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def normalise(s: str) -> str:
    s = " ".join(s.strip().lower().split())
    return s[:-1].strip() if s.endswith(".") else s


class Encoder:
    """Rows -> token ids. Prompt = [left-truncated context + "\\n"] + [question + " [answer]"]; target = " answer" + EOS."""

    def __init__(self, tok, max_len, prefix_ids=()):
        self.tok, self.max_len, self.prefix = tok, max_len, list(prefix_ids)
        self.eos = tok.eos_token_id

    def ids(self, text):
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def prompt(self, row, reserve=0):
        ctx = self.ids(row["context"] + "\n") if row["context"] else []
        tail = self.ids(row["question"] + PROMPT_TAIL)
        room = self.max_len - len(self.prefix) - len(tail) - reserve
        truncated = len(ctx) > room
        if truncated:
            ctx = ctx[len(ctx) - max(room, 0):]
        return self.prefix + ctx + tail, truncated

    def train_example(self, row):
        ans = self.ids(" " + row["answer"]) + [self.eos]
        p, _ = self.prompt(row, reserve=len(ans))
        return p, ans


# ---------------------------------------------------------------- model

K2_TYPE = "k2_horizon"  # IFM K2-Horizon: remote code (trust_remote_code), K2HorizonForCausalLM with .model.layers and the same q/k/v/o + gate/up/down Linear names


def is_k2(args):
    """True when args.model is a K2-Horizon repo. Real run: config.json's model_type, read as plain JSON (no remote code runs). Smoke run: only a model name
    containing "k2-horizon" asks for the K2 smoke, so the default (Qwen) smoke never touches the network."""
    name = getattr(args, "model", None) or ""
    if getattr(args, "smoke", False):
        return "k2-horizon" in name.lower()
    from transformers import PretrainedConfig
    return PretrainedConfig.get_config_dict(name, revision=getattr(args, "revision", None))[0].get("model_type") == K2_TYPE


MOE_TYPE = "qwen3_5_moe"  # Qwen3.5 / Qwen3.6 MoE (e.g. Qwen3.6-35B-A3B): a vision-language checkpoint; AutoModelForCausalLM loads its text part as Qwen3_5MoeForCausalLM (fused 3-D experts)


def is_moe(args):
    """True when args.model is a Qwen3.5-MoE repo. Real run: config.json's model_type, read as plain JSON. Smoke run: only a model name containing "a3b" or "moe" asks for the MoE smoke
    (tiny random Qwen3_5MoeForCausalLM, byte tokenizer), so the default smoke never touches the network."""
    name = getattr(args, "model", None) or ""
    if getattr(args, "smoke", False):
        return "a3b" in name.lower() or "moe" in name.lower()
    from transformers import PretrainedConfig
    return str(PretrainedConfig.get_config_dict(name, revision=getattr(args, "revision", None))[0].get("model_type")).startswith(MOE_TYPE)


def load_model(args, device, dtype):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    rev = getattr(args, "revision", None)
    k2 = is_k2(args)
    moe = (not k2) and is_moe(args)
    kw = {**({"revision": rev} if rev else {}), **({"trust_remote_code": True} if k2 else {})}  # Qwen: no extra arguments
    if args.smoke and k2:  # tiny random K2HorizonForCausalLM built from the repo's real config + remote code, with the real tokenizer (and so its chat template)
        from transformers import AutoConfig
        tok = AutoTokenizer.from_pretrained(args.model, **kw)
        cfg = AutoConfig.from_pretrained(
            args.model, vocab_size=len(tok), hidden_size=64, intermediate_size=128, num_hidden_layers=4, num_attention_heads=4,
            num_key_value_heads=2, head_dim=16, rope_head_dim=16, max_position_embeddings=2048, eos_token_id=250019, pad_token_id=1, **kw)
        torch.manual_seed(args.seed)
        lm = AutoModelForCausalLM.from_config(cfg, trust_remote_code=True, **({"code_revision": rev} if rev else {})).to(dtype=dtype)
    elif args.smoke and moe:  # tiny random Qwen3_5MoeForCausalLM: 3 linear-attention + 1 full-attention layers, fused 3-D experts (8, top 2) + a shared expert
        from transformers import Qwen3_5MoeTextConfig, Qwen3_5MoeForCausalLM
        cfg = Qwen3_5MoeTextConfig(
            vocab_size=512, hidden_size=64, num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2, head_dim=16,
            linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=16, linear_value_head_dim=16, linear_conv_kernel_dim=4,
            moe_intermediate_size=32, shared_expert_intermediate_size=32, num_experts=8, num_experts_per_tok=2,
            max_position_embeddings=2048, eos_token_id=1, pad_token_id=0, tie_word_embeddings=False,
            layer_types=["linear_attention"] * 3 + ["full_attention"])
        torch.manual_seed(args.seed)
        lm = Qwen3_5MoeForCausalLM(cfg).to(dtype=dtype)
        tok = ByteTok(cfg.vocab_size)
    elif args.smoke:
        from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
        cfg = Qwen3_5TextConfig(
            vocab_size=512, hidden_size=64, intermediate_size=128, num_hidden_layers=8, num_attention_heads=4,
            num_key_value_heads=2, head_dim=16, linear_num_key_heads=2, linear_num_value_heads=4,
            linear_key_head_dim=16, linear_value_head_dim=16, linear_conv_kernel_dim=4, full_attention_interval=4,
            max_position_embeddings=2048, eos_token_id=1, pad_token_id=0, tie_word_embeddings=True,
            layer_types=["linear_attention"] * 3 + ["full_attention"] + ["linear_attention"] * 3 + ["full_attention"])
        torch.manual_seed(args.seed)
        lm = Qwen3_5ForCausalLM(cfg).to(dtype=dtype)
        tok = ByteTok(cfg.vocab_size)
    else:
        tok = AutoTokenizer.from_pretrained(args.model, **kw)
        if moe and device.type == "cuda":  # ~70 GB of bf16 weights: straight onto the GPU, not staged in host RAM first
            kw["device_map"] = {"": device.index or 0}
        lm = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype, **kw)
        if "ForCausalLM" not in type(lm).__name__ or not hasattr(lm.model, "layers"):
            raise SystemExit(f"unexpected model class {type(lm).__name__}; expected a text-only Qwen3_5ForCausalLM, Qwen3_5MoeForCausalLM (or K2HorizonForCausalLM)")
    lm.to(device).eval()
    for p in lm.parameters():
        p.requires_grad_(False)
    return lm, tok


class ByteTok:
    """Smoke-test tokenizer: one token per byte (ids 4..259), eos = 1."""
    eos_token_id = 1

    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [4 + b for b in text.encode("utf-8")]}

    def decode(self, ids, skip_special_tokens=True):
        return bytes(i - 4 for i in ids if 4 <= i < 260).decode("utf-8", "replace")


def block_order(n_layers, start, loops, size=4):
    """Layer visiting order: the block [start, start+size) is run `loops` times."""
    return list(range(start)) + list(range(start, start + size)) * loops + list(range(start + size, n_layers))


def default_start(n_layers):
    return ((n_layers // 2 - 2) // 4) * 4  # n//2-2 rounded down to a whole linear/full group boundary


class Runner:
    """Drives the decoder layers manually so a block can be repeated; mirrors Qwen3_5TextModel.forward."""

    def __init__(self, lm, loops=1, start=None, size=4):
        self.lm = lm  # a Qwen3_5ForCausalLM (possibly with peft LoRA modules inside)
        self.cfg = lm.config
        self.n = self.cfg.num_hidden_layers
        self.start = default_start(self.n) if start is None else start
        self.size, self.loops = size, loops
        self.checkpoint = False
        assert self.start % 1 == 0 and self.start + size <= self.n

    @property
    def order(self):
        return block_order(self.n, self.start, self.loops, self.size)

    def _virtual(self, order):
        """Layer modules for each position of `order`, each with its own cache index (shared weights)."""
        layers = self.lm.model.layers
        out = []
        for j, i in enumerate(order):
            base = layers[i]
            if j == i:
                out.append(base)
                continue
            v = copy.copy(base)
            v._modules = dict(base._modules)
            attn_name = "linear_attn" if base.block_type == "linear_attention" else "self_attn"
            a = copy.copy(base._modules[attn_name])
            a.layer_idx = j
            v._modules[attn_name] = a
            out.append(v)
        return out

    def new_cache(self, order):
        from transformers import DynamicCache
        cfg = copy.deepcopy(self.cfg)
        cfg.num_hidden_layers = len(order)
        cfg.layer_types = [self.cfg.layer_types[i] for i in order]
        return DynamicCache(config=cfg)

    def hidden(self, input_ids, attention_mask, position_ids, cache=None, order=None):
        from transformers.masking_utils import create_causal_mask, create_recurrent_attention_mask
        m = self.lm.model
        order = order or self.order
        layers = self._virtual(order) if cache is not None else [m.layers[i] for i in order]
        x = m.embed_tokens(input_ids)
        pos = position_ids[None].expand(3, *position_ids.shape)  # text/height/width positions (equal for text)
        pe = m.rotary_emb(x, pos)
        kw = dict(config=self.cfg, inputs_embeds=x, attention_mask=attention_mask, past_key_values=cache,
                  position_ids=position_ids)
        masks = {"full_attention": create_causal_mask(**kw), "linear_attention": create_recurrent_attention_mask(**kw)}
        types = [self.cfg.layer_types[i] for i in order]
        for layer, t in zip(layers, types):
            if self.checkpoint and torch.is_grad_enabled():
                x = torch.utils.checkpoint.checkpoint(
                    lambda h, layer=layer, t=t: layer(h, position_embeddings=pe, attention_mask=masks[t],
                                                      position_ids=position_ids, past_key_values=None, use_cache=False),
                    x, use_reentrant=False)
            else:
                x = layer(x, position_embeddings=pe, attention_mask=masks[t], position_ids=position_ids,
                          past_key_values=cache, use_cache=cache is not None)
        return m.norm(x)

    def logits(self, h):
        return self.lm.lm_head(h)


def right_pad(seqs, pad=0):
    n = max(map(len, seqs))
    ids = torch.full((len(seqs), n), pad, dtype=torch.long)
    mask = torch.zeros((len(seqs), n), dtype=torch.long)
    for i, s in enumerate(seqs):
        ids[i, :len(s)] = torch.tensor(s)
        mask[i, :len(s)] = 1
    return ids, mask


def left_pad(seqs, pad=0):
    n = max(map(len, seqs))
    ids = torch.full((len(seqs), n), pad, dtype=torch.long)
    mask = torch.zeros((len(seqs), n), dtype=torch.long)
    for i, s in enumerate(seqs):
        ids[i, n - len(s):] = torch.tensor(s)
        mask[i, n - len(s):] = 1
    return ids, mask


def answer_loss_sum(runner, batch, device):
    """Summed CE over answer tokens, and their count. batch: list of (prompt_ids, answer_ids)."""
    seqs = [p + a for p, a in batch]
    ids, mask = right_pad(seqs)
    ids, mask = ids.to(device), mask.to(device)
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    h = runner.hidden(ids, mask, pos)
    sel_b, sel_t, tgt = [], [], []
    for b, (p, a) in enumerate(batch):
        for k, t in enumerate(a):
            sel_b.append(b)
            sel_t.append(len(p) + k - 1)  # hidden at t predicts token t+1
            tgt.append(t)
    hs = h[torch.tensor(sel_b, device=device), torch.tensor(sel_t, device=device)]
    logits = runner.logits(hs).float()
    return F.cross_entropy(logits, torch.tensor(tgt, device=device), reduction="sum"), len(tgt)


@torch.no_grad()
def greedy(runner, prompts, device, eos, stop_ids=frozenset(), cache=True, order=None):
    """Greedy decode a batch of prompts (lists of ids). Returns generated id lists (without EOS)."""
    order = order or runner.order
    ids, mask = left_pad(prompts)
    ids, mask = ids.to(device), mask.to(device)
    B = ids.shape[0]
    pos = (mask.cumsum(1) - 1).clamp(min=0)
    kv = runner.new_cache(order) if cache else None
    out = [[] for _ in range(B)]
    done = torch.zeros(B, dtype=torch.bool, device=device)
    cur_ids, cur_mask, cur_pos = ids, mask, pos
    for step in range(MAX_NEW):
        h = runner.hidden(cur_ids, cur_mask, cur_pos, cache=kv, order=order)
        nxt = runner.logits(h[:, -1]).argmax(-1)
        last_pos = cur_pos[:, -1]
        for b in range(B):
            if not done[b]:
                t = int(nxt[b])
                if t == eos or t in stop_ids:
                    done[b] = True
                else:
                    out[b].append(t)
        if bool(done.all()):
            break
        nxt = torch.where(done, torch.full_like(nxt, eos), nxt)
        if cache:
            mask = torch.cat([mask, torch.ones((B, 1), dtype=mask.dtype, device=device)], 1)
            cur_ids, cur_mask, cur_pos = nxt[:, None], mask, (last_pos + 1)[:, None]
        else:
            ids = torch.cat([ids, nxt[:, None]], 1)
            mask = torch.cat([mask, torch.ones((B, 1), dtype=mask.dtype, device=device)], 1)
            cur_ids, cur_mask = ids, mask
            cur_pos = (mask.cumsum(1) - 1).clamp(min=0)
    return out


def evaluate(runner, enc, rows, device, args, name, train_templates, prefix_note=""):
    runner_loops = runner.loops
    if args.eval_loops is not None:
        runner.loops = args.eval_loops
    order = runner.order
    stop_ids = set()
    if args.arm == "a0":
        tok = enc.tok
        if not args.smoke:
            stop_ids = {i for i in range(len(tok)) if "\n" in tok.decode([i])}
    preds = [None] * len(rows)
    items = []
    truncated = 0
    for i, r in enumerate(rows):
        p, tr = enc.prompt(r, reserve=0)
        truncated += tr
        items.append((i, p))
    items.sort(key=lambda x: -len(x[1]))
    k = 0
    t0 = time.time()
    while k < len(items):
        bs = max(1, min(args.eval_bsz, args.eval_tokens // len(items[k][1])))
        chunk = items[k:k + bs]
        gen = greedy(runner, [p for _, p in chunk], device, enc.eos, stop_ids, cache=not args.no_cache, order=order)
        for (i, _), g in zip(chunk, gen):
            text = enc.tok.decode(g, skip_special_tokens=True)
            if args.arm == "a0":
                text = text.split("\n")[0].split(" [feedback]")[0]
            preds[i] = text
        k += bs
        if (k // bs) % 20 == 0:
            print(f"[eval {name}] {k}/{len(items)} {time.time() - t0:.0f}s", flush=True)
    runner.loops = runner_loops
    hit = [normalise(p) == normalise(r["answer"]) for p, r in zip(preds, rows)]
    res = {"n": len(rows), "accuracy": sum(hit) / len(rows), "frac_context_truncated": truncated / len(rows),
           "eval_seconds": time.time() - t0, "eval_loops": runner.loops if args.eval_loops is None else args.eval_loops}
    for axis in ("qtype", "bank", "style", "rule_family", "action", "long_range", "visible", "template_seen"):
        groups = {}
        for h, r in zip(hit, rows):
            key = r["template"] in train_templates if axis == "template_seen" else r.get(axis)
            groups.setdefault(str(key), []).append(h)
        res[f"by_{axis}"] = {k2: {"n": len(v), "accuracy": sum(v) / len(v)} for k2, v in sorted(groups.items())}
    res["examples"] = [{"id": r["id"], "qtype": r["qtype"], "answer": r["answer"], "pred": p}
                       for r, p in list(zip(rows, preds))[:40]]
    return res


# ---------------------------------------------------------------- main

def few_shot_prefix(enc, train_rows, k=3):
    """k short train examples of different qtypes, each as 'context\\nquestion [answer] answer', blank-line separated."""
    seen, picks = set(), []
    for r in sorted(train_rows, key=lambda r: (len(r["context"]), r["id"])):
        if r["qtype"] not in seen and r["context"]:
            seen.add(r["qtype"])
            picks.append(r)
        if len(picks) == k:
            break
    text = "".join(f"{r['context']}\n{r['question']}{PROMPT_TAIL} {r['answer']}\n\n" for r in picks)
    return enc.ids(text), [r["id"] for r in picks]


def cosine_lr(step, total, base, warmup):
    if step < warmup:
        return base * (step + 1) / warmup
    return base * 0.5 * (1 + math.cos(math.pi * (step - warmup) / max(1, total - warmup)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["a0", "a", "b"], required=True)
    ap.add_argument("--model", default="Qwen/Qwen3.5-0.8B")
    ap.add_argument("--data", default="data", help="dir with train.jsonl dev.jsonl validation.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--bsz", type=int, default=16)
    ap.add_argument("--micro-bsz", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--loops", type=int, default=3)
    ap.add_argument("--loop-start", type=int, default=None)
    ap.add_argument("--eval-loops", type=int, default=None)
    ap.add_argument("--eval-bsz", type=int, default=64)
    ap.add_argument("--eval-tokens", type=int, default=32768)
    ap.add_argument("--no-cache", action="store_true", help="cache-free greedy decoding (slow; for checking)")
    ap.add_argument("--load-adapter", default=None, help="skip training; evaluate this saved adapter")
    ap.add_argument("--no-grad-ckpt", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit-eval", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--extra-eval", action="append", default=[], help="NAME=rows.jsonl, scored after dev/validation")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.smoke else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    t_start = time.time()
    lm, tok = load_model(args, device, dtype)
    n_layers = lm.config.num_hidden_layers

    ddir = Path(args.data)
    lim = 20 if args.smoke else None
    train_rows = read_jsonl(ddir / "train.jsonl", limit=lim)
    dev_rows = read_jsonl(ddir / "dev.jsonl", limit=lim)
    val_rows = read_jsonl(ddir / "validation.jsonl", limit=lim)
    if args.limit_eval:
        dev_rows, val_rows = dev_rows[:args.limit_eval], val_rows[:args.limit_eval]
    train_templates = {r["template"] for r in train_rows}

    prefix, shots = [], []
    if args.arm == "a0":
        enc0 = Encoder(tok, args.max_len)
        prefix, shots = few_shot_prefix(enc0, train_rows)
    enc = Encoder(tok, args.max_len, prefix)

    loops = args.loops if args.arm == "b" else 1
    runner = Runner(lm, loops=loops, start=args.loop_start)
    runner.checkpoint = not args.no_grad_ckpt
    result = {"arm": args.arm, "model": args.model, "tag": args.tag, "steps": 0, "bsz": args.bsz, "max_len": args.max_len,
              "loops": loops, "loop_block": [runner.start, runner.start + runner.size] if args.arm == "b" else None,
              "eval_loops": args.eval_loops, "seed": args.seed, "few_shot_ids": shots, "n_train_rows": len(train_rows),
              "loss_curve": []}

    if args.arm != "a0":
        from peft import LoraConfig, PeftModel, get_peft_model
        if args.load_adapter:
            pm = PeftModel.from_pretrained(lm, args.load_adapter)
        else:
            pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0,
                                               target_modules=LORA_TARGETS, bias="none"))
        n_tr = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        result["trainable_params"] = n_tr
        print(f"[lora] trainable params {n_tr:,}", flush=True)
        runner.lm = pm.base_model.model

    if args.arm != "a0" and not args.load_adapter:
        params = [p for p in pm.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0, betas=(0.9, 0.999))
        encoded = [enc.train_example(r) for r in train_rows]
        rng = random.Random(args.seed)
        order_idx = []
        pm.train()
        runner.lm.train()
        t0 = time.time()
        window = []
        budget_s = float(os.environ.get("TRAIN_MINUTES", "0")) * 60
        result["steps_requested"] = args.steps
        step = -1
        while step + 1 < args.steps:
            step += 1
            if budget_s and step == 20:  # fit the step count to the time budget once, so the cosine schedule still completes
                fit = int(budget_s / ((time.time() - t0) / 20))
                if fit < args.steps:
                    print(f"[train] time budget {budget_s:.0f}s: steps {args.steps} -> {max(fit, 21)}", flush=True)
                    args.steps = max(fit, 21)
            if not order_idx:
                order_idx = list(range(len(encoded)))
                rng.shuffle(order_idx)
            take = [order_idx.pop() for _ in range(min(args.bsz, len(order_idx)))]
            batch = [encoded[i] for i in take]
            n_ans = sum(len(a) for _, a in batch)
            for g in opt.param_groups:
                g["lr"] = cosine_lr(step, args.steps, args.lr, min(args.warmup, args.steps // 10 or 1))
            total = 0.0
            for k in range(0, len(batch), args.micro_bsz):
                s, _ = answer_loss_sum(runner, batch[k:k + args.micro_bsz], device)
                (s / n_ans).backward()
                total += s.item()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
            window.append(total / n_ans)
            if (step + 1) % 10 == 0 or step + 1 == args.steps:
                result["loss_curve"].append([step + 1, sum(window) / len(window)])
                window = []
                if (step + 1) % 50 == 0 or step + 1 == args.steps:
                    print(f"[train] step {step + 1}/{args.steps} loss {result['loss_curve'][-1][1]:.4f} "
                          f"{time.time() - t0:.0f}s", flush=True)
        result["steps"] = args.steps
        result["train_seconds"] = time.time() - t0
        pm.eval()
        runner.lm.eval()
        pm.save_pretrained(out / "adapter")
    elif args.load_adapter:
        result["adapter_loaded_from"] = str(args.load_adapter)
        pm.eval()
    runner.checkpoint = False

    if device.type == "cuda":
        result["peak_gpu_mem_gb_after_train"] = torch.cuda.max_memory_allocated() / 2**30
    extra = [(spec.split("=", 1)[0], read_jsonl(spec.split("=", 1)[1])) for spec in args.extra_eval]
    for name, rows in (("dev", dev_rows), ("validation", val_rows), *extra):
        result[name] = evaluate(runner, enc, rows, device, args, name, train_templates)
        print(f"[result] {args.arm} {name} acc {result[name]['accuracy']:.4f} (n={result[name]['n']})", flush=True)
    result["gap_dev_minus_validation"] = result["dev"]["accuracy"] - result["validation"]["accuracy"]
    result["wall_seconds"] = time.time() - t_start
    if device.type == "cuda":
        result["peak_gpu_mem_gb"] = torch.cuda.max_memory_allocated() / 2**30
    name = f"result_{args.arm}" + (f"_eval{args.eval_loops}" if args.eval_loops is not None else "") + ".json"
    (out / name).write_text(json.dumps(result, indent=1))
    print(f"[done] wrote {out / name}", flush=True)


if __name__ == "__main__":
    main()
