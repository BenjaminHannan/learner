#!/usr/bin/env python3
"""Experiment 43A: the LENGTH GATE (architecture, not sleep).

Probe before this experiment: the registered CardFold base models lose even their OLD,
fully practised skills on inputs longer than they trained on (length 10: 0-0.6,
length 12: 0.0).  No sleep rule can give a new skill a length reach the model does
not have for any skill.  So before testing a new sleep rule we ask one architecture
question: what is the smallest change that lets old skills work on longer inputs?

Same data, size, optimiser and 12,000 updates as the CardFold base.  Arms:

  randpos       ONE change: instead of positions offset, offset+1, offset+2, ... each
                sequence gets a sorted random sample of positions from 0..255
                (randomised positional encoding, Ruoss et al. 2023).  The model can
                then only use ORDER, and has already seen every position number.
  randpos-loop  second change on top: ONE transformer block applied 4 times with
                the input re-added each time (shared weights, same compute,
                a quarter of the block parameters).

Control = the saved registered bases (positions = offset + 0,1,2,...).
Imports the CardFold script read-only.  One CPU thread per process.
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

import fable_cardfold_sleep as C

ARMS = ("randpos", "randpos-loop")
LOOPS = 4
EVAL_LENGTHS = (4, 5, 6, 7, 8, 9, 10, 12, 16)
EVAL_PER_OP = 100


class PosDecoder(nn.Module):
    """TinyDecoder with explicit positions; optionally one shared block looped."""

    def __init__(self, loop: bool) -> None:
        super().__init__()
        self.loop = loop
        self.token_embedding = nn.Embedding(C.VOCAB_SIZE, C.D_MODEL, padding_idx=C.PAD_ID)
        block = nn.TransformerEncoderLayer(
            d_model=C.D_MODEL, nhead=C.N_HEADS, dim_feedforward=C.D_FF, dropout=C.DROPOUT,
            activation="gelu", batch_first=True, norm_first=True,
        )
        if loop:
            self.block = block
        else:
            self.blocks = nn.TransformerEncoder(block, num_layers=C.MODEL_LAYERS,
                                                enable_nested_tensor=False)
        self.final_norm = nn.LayerNorm(C.D_MODEL)
        self.output = nn.Linear(C.D_MODEL, C.VOCAB_SIZE)
        self.register_buffer("position_table",
                             C.make_sinusoidal_table(C.MAX_POSITIONS, C.D_MODEL), persistent=False)

    def forward(self, tokens: Tensor, positions: Tensor, padding_mask: Tensor | None = None) -> Tensor:
        steps = tokens.shape[1]
        inp = self.token_embedding(tokens) + self.position_table[positions]
        causal = torch.triu(torch.ones(steps, steps, dtype=torch.bool), diagonal=1)
        if self.loop:
            hidden = inp
            for i in range(LOOPS):
                hidden = self.block(hidden if i == 0 else hidden + inp,
                                    src_mask=causal, src_key_padding_mask=padding_mask)
        else:
            hidden = self.blocks(inp, mask=causal, src_key_padding_mask=padding_mask)
        return self.output(self.final_norm(hidden))


def random_positions(rng: random.Random, count: int) -> list[int]:
    return sorted(rng.sample(range(C.MAX_POSITIONS), count))


def collate(examples: Sequence[C.Example], rng: random.Random):
    encoded = [C.encode_example(ex) for ex in examples]
    width = max(len(seq) for seq, _ in encoded)
    tokens = torch.full((len(examples), width), C.PAD_ID, dtype=torch.long)
    supervised = torch.zeros((len(examples), width), dtype=torch.bool)
    padding = torch.ones((len(examples), width), dtype=torch.bool)
    positions = torch.zeros((len(examples), width), dtype=torch.long)
    for row, (seq, start) in enumerate(encoded):
        n = len(seq)
        tokens[row, :n] = torch.tensor(seq)
        padding[row, :n] = False
        supervised[row, start:n] = True
        positions[row, :n] = torch.tensor(random_positions(rng, n))
    return tokens, supervised, padding, positions


def loss_fn(model: PosDecoder, batch) -> Tensor:
    tokens, supervised, padding, positions = batch
    logits = model(tokens[:, :-1], positions[:, :-1], padding[:, :-1])
    targets, mask = tokens[:, 1:], supervised[:, 1:]
    losses = nn.functional.cross_entropy(
        logits.reshape(-1, C.VOCAB_SIZE), targets.reshape(-1), reduction="none").reshape_as(targets)
    return losses[mask].mean()


@torch.inference_mode()
def score(model: PosDecoder, examples: Sequence[C.Example], rng: random.Random) -> float:
    """Closed-book greedy exact match; all examples share one input length."""
    n = len(examples[0].inp)
    prompts = [[C.op_token_id(ex.op)] + [C.digit_token_id(ch) for ch in ex.inp] + [C.EQ_ID]
               for ex in examples]
    expected = torch.tensor([[C.digit_token_id(ch) for ch in ex.out] + [C.EOS_ID] for ex in examples])
    generated = torch.tensor(prompts, dtype=torch.long)
    total = 2 * n + 3
    positions = torch.tensor([random_positions(rng, total) for _ in examples])
    model.eval()
    out = []
    for _ in range(n + 1):
        nxt = model(generated, positions[:, :generated.shape[1]])[:, -1].argmax(dim=-1)
        out.append(nxt)
        generated = torch.cat((generated, nxt[:, None]), dim=1)
    return float((torch.stack(out, dim=1) == expected).all(dim=1).float().mean())


def evaluate(model: PosDecoder, seed: int) -> dict:
    table = {}
    for length in EVAL_LENGTHS:
        row = {}
        for op, program in C.OLD_PROGRAMS:
            rng = C.make_rng(f"gate43/eval/{op}/{length}", seed)
            inputs: set[str] = set()
            while len(inputs) < EVAL_PER_OP:
                inputs.add(C.random_digit_string(rng, length))
            ex = C.examples_for_program(op, program, sorted(inputs))
            row[op] = score(model, ex, C.make_rng(f"gate43/eval-pos/{op}/{length}", seed))
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
        torch.manual_seed(C.derive_seed(f"gate43/model/{a.arm}", a.seed) & ((1 << 63) - 1))
        model = PosDecoder(loop=a.arm == "randpos-loop")
    torch.manual_seed(C.derive_seed("gate43/torch", a.seed) & ((1 << 63) - 1))
    opt = torch.optim.AdamW(model.parameters(), lr=C.BASE_LR, weight_decay=C.WEIGHT_DECAY)
    updates = 20 if a.smoke else C.BASE_UPDATES
    t0 = time.time()
    losses = []
    for step in range(updates):
        rows = C.base_step_examples(a.seed, step, splits)  # identical data to the registered base
        batch = collate(rows, C.make_rng(f"gate43/positions/{step}", a.seed))
        model.train()
        opt.zero_grad(set_to_none=True)
        loss = loss_fn(model, batch)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
        losses.append(float(loss.detach()))
    table = evaluate(model, a.seed)
    r = {
        "seed": a.seed, "arm": a.arm, "updates": updates, "smoke": a.smoke,
        "parameters": sum(q.numel() for q in model.parameters()),
        "tail_loss": sum(losses[-50:]) / len(losses[-50:]), "accuracy_by_length": table,
        "train_seconds": round(time.time() - t0, 1),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    torch.save({"seed": a.seed, "arm": a.arm, "state": model.state_dict()},
               a.out / f"seed{a.seed}-{a.arm}.pt")
    print(json.dumps({"seed": a.seed, "arm": a.arm,
                      "mean_by_length": {k: round(v["mean"], 3) for k, v in table.items()},
                      "seconds": r["train_seconds"]}))


if __name__ == "__main__":
    main()
