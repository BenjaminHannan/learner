"""D side: load a (frozen) D, read each count item's visit, and keep what D computed for the count question.

Per item we keep, for the question's FINAL think loop, all register rows [R, 128] (R = 4 for the d128 D) and register 0, plus D's own decoded answer
(the text, its integer if it is a number word, and whether it matches the village answer).  Nothing about D's outputs changes: the rows are read from
the episode object that D's own `answer()` hands to its greedy decoder (a wrapper around `_greedy`).

D checkpoints: v1's D-final.pt ({"model", "config": MiniConfig dict}), a learnlab/premonition checkpoint (load_mini), or `random` (smoke only: untrained,
optionally `train_count_d` pretrains it a few hundred steps on count questions only).
"""
from __future__ import annotations

import dataclasses
import time
from contextlib import contextmanager
from typing import Optional, Sequence

import torch

from learnlab import step1
from premonition import data as pdata
from premonition import preprocess
from premonition.batch import VisitBatch
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import mini_config_from, mini_config_dict

from .data import VillageItems, word_to_int


def load_d(ckpt: str, device, vocab_size: int, seed: int = 0) -> PremonitionMini:
    """A D in eval mode with every parameter frozen.  ckpt = path | 'random'."""
    if ckpt == "random":
        torch.manual_seed(seed)
        model = PremonitionMini(MiniConfig.preset("D", "full", vocab_size=vocab_size))
    else:
        payload = torch.load(ckpt, map_location="cpu", weights_only=False)
        if "config" in payload and isinstance(payload.get("config"), dict) and "mini" in payload["config"]:
            cfg = mini_config_from(payload["config"]["mini"])
        elif "config" in payload:
            cfg = mini_config_from(payload["config"])
        else:
            raise ValueError(f"{ckpt}: no D config in the checkpoint (expected D-final.pt with 'config')")
        model = PremonitionMini(cfg)
        model.load_state_dict(payload["model"])
    model = model.to(device).eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def freeze(model: torch.nn.Module) -> torch.nn.Module:
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return model


# ------------------------------------------------------------------ batches that hold only the chosen questions
def select_questions(batch: VisitBatch, keep: torch.Tensor) -> VisitBatch:
    """The same visits with only the questions where `keep` [Q] is True (questions are independent in D: each reads causally up to its own '[answer]')."""
    idx = keep.nonzero().squeeze(1)
    ids = idx.tolist()
    return dataclasses.replace(
        batch, q_visit=batch.q_visit[idx], q_line=batch.q_line[idx], q_span=batch.q_span[idx], answer=batch.answer[idx],
        gold_lines=batch.gold_lines[idx], depth=batch.depth[idx], question_ids=[batch.question_ids[i] for i in ids],
        slices=None if batch.slices is None else {k: v[idx] for k, v in batch.slices.items()})


def item_batches(items: VillageItems, which: Optional[Sequence[int]] = None, max_tokens: int = 60000, max_visits: int = 48,
                 seed: Optional[int] = None):
    """Yield (item indices, VisitBatch) covering `which` items (default all).  Each batch holds whole visits and only the chosen count questions.
    seed None = identity entity numbering (evaluation / message extraction).  Visits are length-bucketed."""
    which = list(range(len(items))) if which is None else list(which)
    by_visit: dict = {}
    for i in which:
        by_visit.setdefault(int(items.visit[i]), []).append(i)
    visits = sorted(by_visit)
    lengths = items.cache.lengths.tolist()
    groups = pdata.length_batches([lengths[v] for v in visits], max_tokens, max_visits=max_visits)
    qpos = {int(q): i for i, q in enumerate(items.q.tolist())}
    for g in groups:
        vs = [visits[k] for k in g]
        batch = pdata.collate(items.cache, vs)
        want = set(i for v in vs for i in by_visit[v])
        qglob = [int(items.q[i]) for i in sorted(want)]
        # batch questions are in (visit order of vs, stream order); map each to its item or drop it
        order = []
        keep = torch.zeros(batch.q_visit.shape[0], dtype=torch.bool)
        pos = 0
        for row, v in enumerate(vs):
            for q in items.cache.questions_of(v):
                if q in qpos and qpos[q] in want:
                    keep[pos] = True
                    order.append(qpos[q])
                pos += 1
        yield order, select_questions(batch, keep)


# ------------------------------------------------------------------ extraction
@contextmanager
def capture_final_rows(model: PremonitionMini):
    """While active, model.answer() records its episode rows when it starts decoding (= after each question's last think loop)."""
    box = {}
    orig = model._greedy

    def wrapped(batch, episode, mentions, stop):
        base = model._register_base
        box["regs"] = episode.x[:, base:base + model.config.registers].detach().float().clone()
        return orig(batch, episode, mentions, stop)

    model._greedy = wrapped
    try:
        yield box
    finally:
        del model._greedy


@torch.no_grad()
def extract(model: PremonitionMini, items: VillageItems, tokenizer, device, max_tokens: int = 60000, max_visits: int = 48, log=None) -> dict:
    """Run frozen D on every item.  -> dict(regs [N,R,128] fp32 cpu, reg0 [N,128], d_text list[str], d_int [N] (-1 = not a number), d_correct [N] bool, loops [N])."""
    N = len(items)
    R_, d = model.config.registers, model.config.d_model
    regs = torch.zeros(N, R_, d)
    d_int = torch.full((N,), -1, dtype=torch.long)
    d_ok = torch.zeros(N, dtype=torch.bool)
    loops = torch.zeros(N, dtype=torch.long)
    texts = [""] * N
    stops = sorted(step1.stop_ids(tokenizer)[0])
    done = 0
    t0 = time.time()
    for order, batch in item_batches(items, None, max_tokens, max_visits):
        batch = batch.to(device)
        with capture_final_rows(model) as box:
            ans = model.answer(batch, stop=stops)
        pred = []
        for q, ids in enumerate(ans.ids()):
            table = batch.names[int(batch.q_visit[q])]
            pred.append(preprocess.prediction_text(ids, table, tokenizer)[0])
        for k, i in enumerate(order):
            regs[i] = box["regs"][k].cpu()
            texts[i] = pred[k]
            d_int[i] = word_to_int(pred[k])
            d_ok[i] = d_int[i] == int(items.c[i])
            loops[i] = int(ans.loops[k])
        done += len(order)
        if log:
            log(f"  D read {done}/{N} items ({time.time() - t0:.0f}s)")
    return dict(regs=regs, reg0=regs[:, 0].clone(), d_text=texts, d_int=d_int, d_correct=d_ok, loops=loops)


def synthetic_messages(items: VillageItems, R: int = 4, d: int = 128, noise: float = 1.0, d_acc: float = 0.85, seed: int = 0) -> dict:
    """SMOKE ONLY (`--d-ckpt synthetic`): stand-in for D that does NOT read the story.  regs[r] = A[r, c] + noise (A fixed random, the same for every split),
    D's 'decoded answer' = c with probability d_acc, else another count.  It exists to prove that every arm and ablation of the pipeline can show information
    flow (real high, shuffle/mean/off/ema_const at the prior) when a message that carries c exists; it says nothing about D."""
    A = torch.randn(21, R, d, generator=torch.Generator().manual_seed(12345))
    g = torch.Generator().manual_seed(seed + 7)
    regs = A[items.c] + noise * torch.randn(len(items), R, d, generator=g)
    wrong = (items.c + 1 + torch.randint(0, 3, (len(items),), generator=g)) % 5
    d_int = torch.where(torch.rand(len(items), generator=g) < d_acc, items.c, wrong)
    return dict(regs=regs, reg0=regs[:, 0].clone(), d_text=[str(int(x)) for x in d_int], d_int=d_int, d_correct=d_int == items.c, loops=torch.ones(len(items), dtype=torch.long))


# ------------------------------------------------------------------ smoke-only: a quick D pretrain on count questions
def train_count_d(model: PremonitionMini, items: VillageItems, steps: int, device, lr: float = 2e-3, max_tokens: int = 6000, seed: int = 0,
                  log=print, max_visits: int = 4) -> list:
    """SMOKE ONLY.  A few hundred AdamW steps of D's own loss on the count questions of `items` (teacher mode, pointer numbering shuffled), so the
    pipeline has a D that is not pure noise.  Not the v1 training recipe; the full run uses the real D-final.pt."""
    import random
    for p in model.parameters():
        p.requires_grad_(True)
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    rng = random.Random(seed)
    hist, step = [], 0
    by_visit: dict = {}
    for i in range(len(items)):
        by_visit.setdefault(int(items.visit[i]), []).append(i)
    visits = sorted(by_visit)
    qpos = {int(q): i for i, q in enumerate(items.q.tolist())}
    lengths = items.cache.lengths.tolist()
    while step < steps:
        groups = pdata.length_batches([lengths[v] for v in visits], max_tokens, rng=rng, max_visits=max_visits)
        for g in groups:
            vs = [visits[k] for k in g]
            batch = pdata.collate(items.cache, vs, rng=rng)
            keep = torch.tensor([q in qpos for v in vs for q in items.cache.questions_of(v)])
            if not keep.any():
                continue
            batch = select_questions(batch, keep).to(device)
            out = model(batch, mode="teacher", weights={"lm": 0.0, "ask": 0.5, "ans": 1.0, "halt": 0.1})
            opt.zero_grad(set_to_none=True)
            out["loss"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            hist.append(float(out["loss"].detach()))
            step += 1
            if log and step % 25 == 0:
                log(f"  [D pretrain] step {step}/{steps} loss {sum(hist[-25:]) / 25:.3f}")
            if step >= steps:
                break
    return hist


if __name__ == "__main__":      # python -m bridgelab.real.dmsg --village-root ROOT --steps 400 --out bridgelab/real/ckpt/D_smoke_400.pt   (SMOKE ONLY)
    import argparse
    from pathlib import Path
    from . import data as D
    ap = argparse.ArgumentParser()
    ap.add_argument("--village-root", required=True)
    ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parents[2] / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    tok, splits = D.open_village(a.village_root, a.tokenizer, splits=("train",))
    m = load_d("random", a.device, tok.vocab_size, a.seed)
    train_count_d(m, splits["train"], a.steps, a.device, seed=a.seed)
    freeze(m)
    torch.save({"model": m.state_dict(), "config": mini_config_dict(m.config), "steps": a.steps, "smoke": True}, a.out)
    print("saved", a.out)
