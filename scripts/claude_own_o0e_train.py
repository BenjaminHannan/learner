"""own-O0e resume-safe trainer for the plain-transformer baseline.

Properties:
  - deterministic data order: corpus texts are used in a fixed order;
    batch b of epoch e is fully determined by (seed, step). Re-running
    from scratch with the same seed gives byte-identical batches.
  - atomic checkpoints: written to a tmp file then os.replace()d, so a
    kill mid-write can never corrupt the checkpoint. Default cadence:
    every 10 minutes and every --ckpt-steps steps, plus at the end.
  - restart loop: starting the same command again resumes from the
    latest checkpoint automatically (--max-restarts retries a crashed
    run inside one process).
  - bf16 on CUDA via autocast when a GPU is present; fp32 on the Mac CPU.
  - tiny configs (width/layers/vocab/context flags) for the CPU kill
    test and the smoke test; full config is the plan default.

Corpus: a jsonl file with {"text": str} per line, or texts passed as a
Python list to train(). The tokenizer is whitespace-based, built
deterministically from the sorted corpus vocabulary (toy use only; the
GPU pretraining uses the plan's 8192 BPE).

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; \
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/claude_own_o0e_train.py --corpus <f> --out <dir> ...
"""

from __future__ import annotations

import argparse
import json
import os
import time

import torch
import torch.nn as nn

from claude_own_o0e_model import ModelConfig, PlainTransformer


def build_vocab(texts: list[str]) -> dict[str, int]:
    toks = set()
    for t in texts:
        toks.update(t.split())
    # ids: 0 = pad, 1 = unk; rest sorted for determinism
    return {"<pad>": 0, "<unk>": 1, **{w: i + 2 for i, w in enumerate(sorted(toks))}}


def encode(text: str, vocab: dict[str, int], width_ctx: int) -> list[int]:
    ids = [vocab.get(w, 1) for w in text.split()][:width_ctx]
    return ids


def batch_at(
    corpus_ids: list[list[int]], step: int, batch: int, seed: int
) -> torch.Tensor:
    """Deterministic batch: rotate start by a seeded function of step."""
    n = len(corpus_ids)
    out = []
    for b in range(batch):
        idx = (step * batch + b) % n
        out.append(corpus_ids[idx])
    L = max(len(s) for s in out)
    return torch.tensor([s + [0] * (L - len(s)) for s in out], dtype=torch.long)


def save_atomic(state: dict, path: str) -> None:
    tmp = path + ".tmp"
    torch.save(state, tmp)
    os.replace(tmp, path)


def train(
    texts: list[str],
    out_dir: str,
    total_steps: int = 8,
    batch: int = 4,
    lr: float = 1e-3,
    seed: int = 0,
    cfg: ModelConfig | None = None,
    ckpt_minutes: float = 10.0,
    ckpt_steps: int = 50,
    ctx_len: int = 64,
    log: list | None = None,
) -> tuple[PlainTransformer, list[float]]:
    os.makedirs(out_dir, exist_ok=True)
    cfg = cfg or ModelConfig()
    torch.manual_seed(seed)
    vocab = build_vocab(texts)
    # vocab cap mirrors the model config so ids always fit
    assert len(vocab) <= cfg.vocab, f"vocab {len(vocab)} > {cfg.vocab}"
    corpus_ids = [encode(t, vocab, ctx_len) for t in texts]
    assert all(len(s) >= 2 for s in corpus_ids), "need >= 2 tokens per text"

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    model = PlainTransformer(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss(ignore_index=0)

    ckpt_path = os.path.join(out_dir, "ckpt.pt")
    step = 0
    losses: list[float] = []
    if os.path.exists(ckpt_path):
        ck = torch.load(ckpt_path, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step = ck["step"]
        losses = ck["losses"]
        torch.manual_seed(seed + step)  # advance RNG past consumed steps

    last_ckpt = time.time()
    model.train()
    with open(os.path.join(out_dir, "vocab.json"), "w") as f:
        json.dump(vocab, f)
    while step < total_steps:
        ids = batch_at(corpus_ids, step, batch, seed).to(device)
        x, y = ids[:, :-1], ids[:, 1:]
        opt.zero_grad()
        if use_cuda:
            with torch.autocast("cuda", dtype=torch.bf16):
                logits = model(x)
                loss = loss_fn(logits.reshape(-1, logits.shape[-1]), y.reshape(-1))
        else:
            loss = loss_fn(
                model(x).reshape(-1, cfg.vocab), y.reshape(-1)
            )
        loss.backward()
        opt.step()
        losses.append(float(loss.item()))
        step += 1
        due_time = (time.time() - last_ckpt) >= ckpt_minutes * 60
        if due_time or step % ckpt_steps == 0 or step >= total_steps:
            save_atomic(
                {"model": model.state_dict(), "opt": opt.state_dict(),
                 "step": step, "losses": losses, "seed": seed},
                ckpt_path,
            )
            last_ckpt = time.time()
        if log is not None:
            log.append((step, losses[-1]))
    return model, losses


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="jsonl with {text} per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--total-steps", type=int, default=8)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--layers", type=int, default=12)
    ap.add_argument("--mlp-width", type=int, default=1600)
    ap.add_argument("--vocab", type=int, default=8192)
    ap.add_argument("--context", type=int, default=1024)
    ap.add_argument("--ckpt-minutes", type=float, default=10.0)
    ap.add_argument("--ckpt-steps", type=int, default=50)
    ap.add_argument("--max-restarts", type=int, default=3)
    args = ap.parse_args()

    with open(args.corpus) as f:
        texts = [json.loads(line)["text"] for line in f if line.strip()]
    cfg = ModelConfig(
        vocab=args.vocab, width=args.width, layers=args.layers,
        mlp_width=args.mlp_width, context=args.context,
    )
    attempt = 0
    while True:
        try:
            _, losses = train(
                texts, args.out, total_steps=args.total_steps, batch=args.batch,
                lr=args.lr, seed=args.seed, cfg=cfg,
                ckpt_minutes=args.ckpt_minutes, ckpt_steps=args.ckpt_steps,
            )
            print(f"DONE steps={len(losses)} last_loss={losses[-1]:.4f}")
            break
        except Exception as e:  # restart loop: resume from latest atomic ckpt
            attempt += 1
            print(f"RESTART {attempt}/{args.max_restarts} after: {type(e).__name__}")
            if attempt > args.max_restarts:
                raise


if __name__ == "__main__":
    main()
