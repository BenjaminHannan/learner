#!/usr/bin/env python3
"""Experiment 43C: second rung of the length gate — SEGMENT-RELATIVE positions.

43A result: randomised positions lifted old skills at length 10 (0.18 -> 0.40-0.52) but
length 12 stayed ~0.  Probe: the failures are not early stops; the model writes a wrong
digit within the first 1-3 output places, i.e. it looks at the wrong input digit.  It
finds "which input digit do I need" by counting back across the whole sequence, and
that distance is new when the input is longer.

One change from the registered base: positions restart in the answer.
Input digit i and answer digit i get the SAME position number (offset + i), so
"copy the digit that has my number" is the same computation at every length.

  op token -> offset,  input digit i -> offset+1+i,  "=" -> offset+1+n,
  answer digit j -> offset+1+j,  end mark -> offset+1+n

The random offset (0..192) is kept from the registered base, so every position number
used at length 16 has been seen in training.  Same data, size, optimiser, 12,000 updates.
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
from torch import nn

import fable_cardfold_sleep as C
import fable_lengthgate43 as G

ARM = "segpos"
COPY_LIKE = ("OP1", "OP2", "OP3")      # ROTL1, INC3, SWAP: source digit is a fixed shift away
END_RELATIVE = ("OP0", "OP4", "OP5")   # REV, FOLD, REV+INC1: source digit is counted from the end


def segment_positions(n: int, total: int, offset: int) -> list[int]:
    """Positions for [op, n input digits, '=', answer digits..., eos], cut to `total` tokens."""
    full = [offset] + [offset + 1 + i for i in range(n)] + [offset + 1 + n]
    full += [offset + 1 + j for j in range(n)] + [offset + 1 + n]
    return full[:total]


def collate(examples: Sequence[C.Example], rng: random.Random):
    encoded = [C.encode_example(ex) for ex in examples]
    width = max(len(seq) for seq, _ in encoded)
    tokens = torch.full((len(examples), width), C.PAD_ID, dtype=torch.long)
    supervised = torch.zeros((len(examples), width), dtype=torch.bool)
    padding = torch.ones((len(examples), width), dtype=torch.bool)
    positions = torch.zeros((len(examples), width), dtype=torch.long)
    for row, ((seq, start), ex) in enumerate(zip(encoded, examples)):
        k = len(seq)
        tokens[row, :k] = torch.tensor(seq)
        padding[row, :k] = False
        supervised[row, start:k] = True
        offset = rng.randrange(C.POSITION_OFFSET_MAX + 1)
        positions[row, :k] = torch.tensor(segment_positions(len(ex.inp), k, offset))
    return tokens, supervised, padding, positions


@torch.inference_mode()
def score(model, examples: Sequence[C.Example], rng: random.Random) -> float:
    n = len(examples[0].inp)
    generated = torch.tensor([[C.op_token_id(ex.op)] + [C.digit_token_id(ch) for ch in ex.inp]
                              + [C.EQ_ID] for ex in examples])
    expected = torch.tensor([[C.digit_token_id(ch) for ch in ex.out] + [C.EOS_ID] for ex in examples])
    positions = torch.tensor([segment_positions(n, 2 * n + 3, rng.randrange(C.POSITION_OFFSET_MAX + 1))
                              for _ in examples])
    model.eval()
    out = []
    for _ in range(n + 1):
        nxt = model(generated, positions[:, :generated.shape[1]])[:, -1].argmax(dim=-1)
        out.append(nxt)
        generated = torch.cat((generated, nxt[:, None]), dim=1)
    return float((torch.stack(out, dim=1) == expected).all(dim=1).float().mean())


def evaluate(model, seed: int) -> dict:
    table = {}
    for length in G.EVAL_LENGTHS:
        row = {}
        for op, program in C.OLD_PROGRAMS:
            rng = C.make_rng(f"gate43/eval/{op}/{length}", seed)   # same test inputs as 43A
            inputs: set[str] = set()
            while len(inputs) < G.EVAL_PER_OP:
                inputs.add(C.random_digit_string(rng, length))
            ex = C.examples_for_program(op, program, sorted(inputs))
            row[op] = score(model, ex, C.make_rng(f"gate43c/eval-pos/{op}/{length}", seed))
        row["mean"] = sum(row[o] for o, _ in C.OLD_PROGRAMS) / len(C.OLD_PROGRAMS)
        row["copy_like"] = sum(row[o] for o in COPY_LIKE) / len(COPY_LIKE)
        row["end_relative"] = sum(row[o] for o in END_RELATIVE) / len(END_RELATIVE)
        table[str(length)] = row
    return table


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="20 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    splits = C.build_splits(a.seed)
    C.assert_split_disjointness(splits)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(C.derive_seed("gate43/model/randpos", a.seed) & ((1 << 63) - 1))
        model = G.PosDecoder(loop=False)                       # same initial weights as 43A randpos
    torch.manual_seed(C.derive_seed("gate43/torch", a.seed) & ((1 << 63) - 1))
    opt = torch.optim.AdamW(model.parameters(), lr=C.BASE_LR, weight_decay=C.WEIGHT_DECAY)
    updates = 20 if a.smoke else C.BASE_UPDATES
    t0 = time.time()
    losses = []
    for step in range(updates):
        rows = C.base_step_examples(a.seed, step, splits)
        batch = collate(rows, C.make_rng(f"gate43c/positions/{step}", a.seed))
        model.train()
        opt.zero_grad(set_to_none=True)
        loss = G.loss_fn(model, batch)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
        losses.append(float(loss.detach()))
    table = evaluate(model, a.seed)
    r = {"seed": a.seed, "arm": ARM, "updates": updates, "smoke": a.smoke,
         "tail_loss": sum(losses[-50:]) / len(losses[-50:]), "accuracy_by_length": table,
         "train_seconds": round(time.time() - t0, 1),
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{ARM}.json").write_text(json.dumps(r, indent=1))
    torch.save({"seed": a.seed, "arm": ARM, "state": model.state_dict()}, a.out / f"seed{a.seed}-{ARM}.pt")
    print(json.dumps({"seed": a.seed, "arm": ARM, "by_length": {
        k: {x: round(v[x], 3) for x in ("mean", "copy_like", "end_relative")} for k, v in table.items()}}))


if __name__ == "__main__":
    main()
