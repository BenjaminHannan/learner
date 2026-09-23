#!/usr/bin/env python3
"""Experiment 44 depth stress -- MEASUREMENT ONLY, written after the seal, not a registered mark.

Every registered depth (4, 6, 8, 10) came out at 1.000, so this asks the obvious next question:
how deep can the hard-coded hop loop go before the soft routing mixture loses the 0.9 answer
threshold?  Nothing is trained here; it loads the sealed base checkpoints and evaluates.
Resolvable chains get rare fast (0.85^k), so this uses the N=200 village and rejection sampling.

    python -B scripts/fable_reasoner44_stress.py artifacts/fable-reasoner44-20260921/runs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

import fable_reasoner44 as E

SEEDS = (4102, 4103, 4104)
DEPTHS = (12, 16, 20, 24, 32)
COUNT = 100


def main() -> None:
    runs = Path(sys.argv[1])
    torch.set_num_threads(1)
    out = {}
    for seed in SEEDS:
        v = E.make_village("big200", seed, E.BIG_N, "B")
        m = E.notebook_matrices(v)
        model = E.Reasoner()
        model.load_state_dict(torch.load(runs / f"base-seed{seed}.pt", map_location="cpu",
                                         weights_only=True)["state"])
        row = {}
        for d in DEPTHS:
            qs = E.sample_set(v, f"stress/depth{d}", seed, COUNT, (d,), "resolvable")
            preds = E.predict(model, v, m, qs, chunk=25)
            want = E.truth(qs)
            row[str(d)] = {
                "exact": sum(p == t for p, t in zip(preds, want)) / COUNT,
                "argmax_right_ignoring_threshold": None,
                "said_unknown": sum(p == E.UNKNOWN for p in preds) / COUNT,
                "confident_wrong": sum(p != E.UNKNOWN and p != t for p, t in zip(preds, want)),
            }
            # how much probability actually survives on the right person
            starts, stages, targets = encode_all(v, qs)
            with torch.inference_mode():
                x = E.run_tape(model.effective(m), starts, stages, v.n)
            row[str(d)]["mean_prob_on_answer"] = round(float(x.gather(1, targets[:, None]).mean()), 6)
            row[str(d)]["min_prob_on_answer"] = round(float(x.gather(1, targets[:, None]).min()), 6)
            row[str(d)]["argmax_right_ignoring_threshold"] = float(
                (x[:, :v.n].argmax(-1) == targets).float().mean())
        out[str(seed)] = row
    print(json.dumps(out, indent=1))


def encode_all(v, qs):
    return E.encode(v, qs)


if __name__ == "__main__":
    main()
