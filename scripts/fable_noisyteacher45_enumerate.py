#!/usr/bin/env python3
"""Experiment 45 diagnostic (measurement only, written after the registered wave): score ALL 729 hard chains.

For each seed, word and number of wrong answers, every 3-stage chain over {keep + 8 relations} is scored with
the same robust likelihood on the same 20 episodes.  Question: is the true chain the best-scoring chain, and by
how much?  If yes where the trained router was rejected, the router's OPTIMISER is the weak part, not the signal.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import torch

import fable_noisyteacher45 as N
R44 = N.R44
N.ARM = "robust"
RUNS = Path(sys.argv[1])
out = []
for seed in (4102, 4103, 4104, 4105, 4106):
    train_v = R44.make_village("train60", seed, R44.TRAIN_N, "T")
    fresh_v = R44.make_village("fresh60", seed, R44.TRAIN_N, "F")
    m_train, m_fresh = R44.notebook_matrices(train_v), R44.notebook_matrices(fresh_v)
    model = R44.Reasoner()
    model.load_state_dict(torch.load(RUNS / f"base-seed{seed}.pt", weights_only=True)["state"])
    for w in range(R44.N_WORDS):
        fresh_qs = R44.sample_set(fresh_v, f"eval/word{w}/fresh60", seed, R44.EVAL_PER_SET, (1,), "resolvable",
                                  vocab=(R44.R + w,))
        for wrong in (2, 4, 6, 20):
            eps = N.episodes(train_v, w, seed, wrong)
            scored = []
            for chain in itertools.product(range(R44.R + 1), repeat=R44.STAGES):
                logits = torch.full((R44.STAGES, R44.R + 1), -30.0)
                for s, c in enumerate(chain):
                    logits[s, c] = 30.0
                model.words[w].data.copy_(logits)
                scored.append((N.word_nll(model, train_v, m_train, eps), chain))
            scored.sort()
            best_nll, best = scored[0]
            model.words[w].data.copy_(torch.full((R44.STAGES, R44.R + 1), -30.0))
            for s, c in enumerate(best):
                model.words[w].data[s, c] = 30.0
            acc = R44.accuracy(fresh_qs, R44.predict(model, fresh_v, m_fresh, fresh_qs))
            # margin to the best chain that behaves differently on the training episodes' start people
            ties = [c for v, c in scored if abs(v - best_nll) < 1e-9]
            runner = next(v for v, c in scored if v > best_nll + 1e-9)
            row = {"seed": seed, "word": R44.WORD_NAMES[w], "wrong": wrong, "best_chain": best, "tied": len(ties),
                   "best_nll": round(best_nll, 4), "next_nll": round(runner, 4), "best_fresh_accuracy": acc}
            out.append(row)
            print(json.dumps(row))
(RUNS.parent / "enumerate.json").write_text(json.dumps(out, indent=1))
