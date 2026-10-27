#!/usr/bin/env python3
"""Train the small record adapter for Experiment 53.

The SmolLM2 body is frozen except for its final transformer block and lm_head.
The only newly allocated input rows are the ten tagged record tokens.  The
script deliberately uses a short, deterministic CPU run; the brake remains the
authority at inference time.
"""
from __future__ import annotations

import argparse, json, os, random, time
from pathlib import Path

from fable_mouth53_mouth import MODEL_ID, SPEC_TOKENS, untie_lm_head


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--seed", type=int, default=5301)
    args = ap.parse_args(argv)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(1)
    random.seed(args.seed); torch.manual_seed(args.seed)
    data = Path(args.data)
    rows = [json.loads(x) for x in (data / "train.jsonl").read_text().splitlines() if x]
    tok = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, local_files_only=True,
                                                  trust_remote_code=False, torch_dtype=torch.float32)
    tok.add_special_tokens({"additional_special_tokens": SPEC_TOKENS})
    model.resize_token_embeddings(len(tok))
    untie_lm_head(model)  # OUR head: clone off the tied input embeddings
    for p in model.parameters(): p.requires_grad_(False)
    # SmolLM2 names its final block as model.layers[-1]; use a structural lookup
    # so this remains explicit without depending on a private transformers API.
    layers = model.model.layers
    for p in layers[-1].parameters(): p.requires_grad_(True)
    for p in model.lm_head.parameters(): p.requires_grad_(True)
    emb = model.get_input_embeddings()
    for p in emb.parameters(): p.requires_grad_(False)
    trainable = list(layers[-1].parameters()) + list(model.lm_head.parameters())
    # New rows are trained by a masked gradient hook, while old input rows stay frozen.
    row_start = len(tok) - len(SPEC_TOKENS)
    mask = torch.zeros_like(emb.weight); mask[row_start:] = 1
    emb.weight.requires_grad_(True)
    trainable.append(emb.weight)
    emb.weight.register_hook(lambda g: g * mask)
    opt = torch.optim.AdamW(trainable, lr=args.lr)
    model.train(); t0 = time.time(); losses = []
    for step in range(max(0, args.steps)):
        row = rows[step % len(rows)]
        prompt = __import__("fable_mouth53_mouth").serialize(row["record"])
        text = prompt + " " + row["sentence"] + tok.eos_token
        x = tok(text, return_tensors="pt", truncation=True, max_length=128)
        labels = x["input_ids"].clone()
        prefix = tok(prompt + " ", return_tensors="pt", truncation=True, max_length=128)["input_ids"].shape[1]
        labels[:, :min(prefix, labels.shape[1])] = -100
        opt.zero_grad(set_to_none=True)
        loss = model(**x, labels=labels).loss
        loss.backward(); torch.nn.utils.clip_grad_norm_(trainable, 1.0); opt.step()
        losses.append(float(loss.detach()))
    model.eval(); out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    torch.save({"model": {k: v.cpu() for k, v in model.state_dict().items()
                           if k.startswith("model.layers." + str(len(layers)-1) + ".")
                           or k.startswith("lm_head.") or k == "model.embed_tokens.weight"},
                "tokens": SPEC_TOKENS, "row_start": row_start}, out / "adapter.pt")
    n_last = sum(p.numel() for p in layers[-1].parameters())
    n_head = sum(p.numel() for p in model.lm_head.parameters())
    n_rows = len(SPEC_TOKENS) * emb.weight.shape[1]
    meta = {"model": MODEL_ID, "steps": args.steps, "seed": args.seed, "lr": args.lr,
            "train_pairs": len(rows),
            "trainable_parameters": n_last + n_head + n_rows,
            "trainable_breakdown": {"last_block": n_last, "lm_head": n_head,
                                    "new_embed_rows": n_rows,
                                    "n_new_rows": len(SPEC_TOKENS),
                                    "embed_dim": emb.weight.shape[1],
                                    "n_layers": len(layers)},
            "last_loss": losses[-1] if losses else None, "seconds": round(time.time()-t0, 2),
            "frozen_body": True, "adapter": "new input rows + last transformer block + lm_head"}
    (out / "train-meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta)); return 0


if __name__ == "__main__": raise SystemExit(main())
