#!/usr/bin/env python3
"""Experiment 43D: third rung of the length gate — RELATIVE-POSITION ATTENTION.

43A and 43C offered the model better position numbers; it still learned a
length-dependent way to find digits.  Here the length-dependent option is removed:
NO position is added to the token vectors at all.  Position enters only as a learned
bonus on the attention score that depends on the DIFFERENCE between two tokens'
place numbers, clipped to -4..+4 ("far" beyond that), so every difference the model
ever needs has been trained, at any length.

Place numbers (both segments count from 0 at their first token):
  start index: op=0, input digit i = i+1;   "="=0, answer digit j = j+1, end mark = n+1
  end index:   distance to the end of the segment's digits: input digit i = n-i, op = n+1;
               answer digit j = n-j, "=" = n+1, end mark = 0.
               (n is the INPUT length, known before the answer is written. No answer leak.)

Arms:
  rel-start  bonus depends on (my start index - your start index)
  rel-both   the above plus (my start index - your END index)   -> "count from the end"

Tokens also get a learned 2-way "input side / answer side" vector.  Same data, width,
depth, heads, optimiser and 12,000 updates as the registered base and 43A/43C.
Imports CardFold and 43A read-only.  One CPU thread per process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F

import fable_cardfold_sleep as C
import fable_lengthgate43 as G

ARMS = ("rel-start", "rel-both")
CLIP = 4
BUCKETS = 2 * CLIP + 1


def indices(n: int, total: int) -> tuple[list[int], list[int], list[int]]:
    start = [0] + [i + 1 for i in range(n)] + [0] + [j + 1 for j in range(n)] + [n + 1]
    end = [n + 1] + [n - i for i in range(n)] + [n + 1] + [n - j for j in range(n)] + [0]
    seg = [0] * (n + 1) + [1] * (n + 2)
    return start[:total], end[:total], seg[:total]


class RelBlock(nn.Module):
    def __init__(self, both: bool) -> None:
        super().__init__()
        self.both = both
        d, h = C.D_MODEL, C.N_HEADS
        self.norm1, self.norm2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.proj = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, C.D_FF), nn.GELU(), nn.Linear(C.D_FF, d))
        # bonus tables: [head, key side (input/answer), bucket]
        self.bias_start = nn.Parameter(torch.zeros(h, 2, BUCKETS))
        self.bias_end = nn.Parameter(torch.zeros(h, 2, BUCKETS)) if both else None

    def bonus(self, start: Tensor, end: Tensor, seg: Tensor) -> Tensor:
        b, t = start.shape
        key_side = seg[:, None, :].expand(b, t, t)                      # [B, Tq, Tk]
        def look(table: Tensor, diff: Tensor) -> Tensor:
            bucket = diff.clamp(-CLIP, CLIP) + CLIP
            return table[:, key_side, bucket].permute(1, 0, 2, 3)       # [B, H, Tq, Tk]
        out = look(self.bias_start, start[:, :, None] - start[:, None, :])
        if self.both:
            out = out + look(self.bias_end, start[:, :, None] - end[:, None, :])
        return out

    def forward(self, x: Tensor, start: Tensor, end: Tensor, seg: Tensor, blocked: Tensor) -> Tensor:
        b, t, d = x.shape
        h = C.N_HEADS
        q, k, v = self.qkv(self.norm1(x)).reshape(b, t, 3, h, d // h).permute(2, 0, 3, 1, 4)
        mask = self.bonus(start, end, seg).masked_fill(blocked[:, None], float("-inf"))
        att = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.proj(att.transpose(1, 2).reshape(b, t, d))
        return x + self.ff(self.norm2(x))


class RelDecoder(nn.Module):
    def __init__(self, both: bool) -> None:
        super().__init__()
        self.token_embedding = nn.Embedding(C.VOCAB_SIZE, C.D_MODEL, padding_idx=C.PAD_ID)
        self.side_embedding = nn.Embedding(2, C.D_MODEL)
        self.blocks = nn.ModuleList(RelBlock(both) for _ in range(C.MODEL_LAYERS))
        self.final_norm = nn.LayerNorm(C.D_MODEL)
        self.output = nn.Linear(C.D_MODEL, C.VOCAB_SIZE)

    def forward(self, tokens: Tensor, start: Tensor, end: Tensor, seg: Tensor,
                padding: Tensor | None = None) -> Tensor:
        t = tokens.shape[1]
        blocked = torch.triu(torch.ones(t, t, dtype=torch.bool), diagonal=1)[None].expand(len(tokens), t, t)
        if padding is not None:
            blocked = blocked | padding[:, None, :]
        x = self.token_embedding(tokens) + self.side_embedding(seg)
        for block in self.blocks:
            x = block(x, start, end, seg, blocked)
        return self.output(self.final_norm(x))


def collate(examples: Sequence[C.Example]):
    encoded = [C.encode_example(ex) for ex in examples]
    width = max(len(seq) for seq, _ in encoded)
    shape = (len(examples), width)
    tokens = torch.full(shape, C.PAD_ID, dtype=torch.long)
    supervised = torch.zeros(shape, dtype=torch.bool)
    padding = torch.ones(shape, dtype=torch.bool)
    start, end, seg = (torch.zeros(shape, dtype=torch.long) for _ in range(3))
    for row, ((seq, first), ex) in enumerate(zip(encoded, examples)):
        k = len(seq)
        tokens[row, :k] = torch.tensor(seq)
        padding[row, :k] = False
        supervised[row, first:k] = True
        s, e, g = indices(len(ex.inp), k)
        start[row, :k], end[row, :k], seg[row, :k] = torch.tensor(s), torch.tensor(e), torch.tensor(g)
    return tokens, supervised, padding, start, end, seg


def loss_fn(model: RelDecoder, batch) -> Tensor:
    tokens, supervised, padding, start, end, seg = batch
    logits = model(tokens[:, :-1], start[:, :-1], end[:, :-1], seg[:, :-1], padding[:, :-1])
    targets, mask = tokens[:, 1:], supervised[:, 1:]
    losses = F.cross_entropy(logits.reshape(-1, C.VOCAB_SIZE), targets.reshape(-1),
                             reduction="none").reshape_as(targets)
    return losses[mask].mean()


@torch.inference_mode()
def score(model: RelDecoder, examples: Sequence[C.Example]) -> float:
    n = len(examples[0].inp)
    generated = torch.tensor([[C.op_token_id(ex.op)] + [C.digit_token_id(ch) for ch in ex.inp]
                              + [C.EQ_ID] for ex in examples])
    expected = torch.tensor([[C.digit_token_id(ch) for ch in ex.out] + [C.EOS_ID] for ex in examples])
    s, e, g = (torch.tensor(x)[None].expand(len(examples), -1) for x in indices(n, 2 * n + 3))
    model.eval()
    out = []
    for _ in range(n + 1):
        t = generated.shape[1]
        nxt = model(generated, s[:, :t], e[:, :t], g[:, :t])[:, -1].argmax(dim=-1)
        out.append(nxt)
        generated = torch.cat((generated, nxt[:, None]), dim=1)
    return float((torch.stack(out, dim=1) == expected).all(dim=1).float().mean())


def evaluate(model: RelDecoder, seed: int) -> dict:
    table = {}
    for length in G.EVAL_LENGTHS:
        row = {}
        for op, program in C.OLD_PROGRAMS:
            rng = C.make_rng(f"gate43/eval/{op}/{length}", seed)        # same test inputs as 43A/43C
            inputs: set[str] = set()
            while len(inputs) < G.EVAL_PER_OP:
                inputs.add(C.random_digit_string(rng, length))
            row[op] = score(model, C.examples_for_program(op, program, sorted(inputs)))
        row["mean"] = sum(row.values()) / len(C.OLD_PROGRAMS)
        table[str(length)] = row
    return table


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="20 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    splits = C.build_splits(a.seed)
    C.assert_split_disjointness(splits)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(C.derive_seed(f"gate43d/model/{a.arm}", a.seed) & ((1 << 63) - 1))
        model = RelDecoder(both=a.arm == "rel-both")
    opt = torch.optim.AdamW(model.parameters(), lr=C.BASE_LR, weight_decay=C.WEIGHT_DECAY)
    updates = 20 if a.smoke else C.BASE_UPDATES
    t0 = time.time()
    losses = []
    for step in range(updates):
        batch = collate(C.base_step_examples(a.seed, step, splits))     # identical data to the registered base
        model.train()
        opt.zero_grad(set_to_none=True)
        loss = loss_fn(model, batch)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
        losses.append(float(loss.detach()))
    seconds = round(time.time() - t0, 1)
    table = evaluate(model, a.seed)
    r = {"seed": a.seed, "arm": a.arm, "updates": updates, "smoke": a.smoke,
         "parameters": sum(q.numel() for q in model.parameters()),
         "tail_loss": sum(losses[-50:]) / len(losses[-50:]), "accuracy_by_length": table,
         "train_seconds": seconds,
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    torch.save({"seed": a.seed, "arm": a.arm, "state": model.state_dict()}, a.out / f"seed{a.seed}-{a.arm}.pt")
    print(json.dumps({"seed": a.seed, "arm": a.arm, "seconds": seconds,
                      "mean_by_length": {k: round(v["mean"], 3) for k, v in table.items()}}))


if __name__ == "__main__":
    main()
