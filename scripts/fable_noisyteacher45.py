#!/usr/bin/env python3
"""Experiment 45: can a slightly wrong teacher still teach a new word?  ONE change: the sleep loss.

Experiment 44 found that 2 wrong answers in 20 episodes made sleep refuse to learn the word at all.
Plain loss = -log p(answer): a wrong answer has p ~ 1e-12, so one bad episode pulls with enormous force.
Robust loss = -log(0.9 * p(answer) + 0.1 / N): "the teacher is wrong about 1 time in 10, and then says
anybody".  A wrong answer can now cost at most log(10 N) ~ 6.4 and its pull is bounded.
Everything else is Experiment 44 unchanged: router phi[3, 9], Adam, checkpoints, 4-fold gate (0.80 / 0.90),
0.9 answer threshold.  The same loss is used for training and for the gate's checkpoint choice.
Arms are paired: same base, same episodes, same wrong answers.  Imports Experiment 44 read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from torch import nn

import fable_reasoner44 as R44

EPS = 0.10
EPISODES = 20
WRONG_COUNTS = (0, 2, 4, 6, 20)
ARMS = ("plain", "robust")
ARM = "plain"


def nll(x: torch.Tensor, targets: torch.Tensor, n: int) -> torch.Tensor:
    p = x.gather(1, targets[:, None])
    if ARM == "robust":
        return -((1 - EPS) * p + EPS / n).log().mean()
    return -p.clamp_min(1e-12).log().mean()


def fit_word(base_state, w, eps, v, m, updates, seed, tag, snapshots=()):
    model = R44.Reasoner()
    model.load_state_dict(base_state)
    model.requires_grad_(False)
    model.words[w].requires_grad_(True)
    opt = torch.optim.Adam([model.words[w]], lr=R44.SLEEP_LR)
    saved = {0: model.words[w].detach().clone()} if 0 in snapshots else {}
    starts, stages, targets = R44.encode(v, eps)
    batch = min(R44.SLEEP_BATCH, len(eps))
    for step in range(updates):
        rng = R44.make_rng(f"sleep/{tag}/{step}", seed)
        pick = torch.tensor([rng.randrange(len(eps)) for _ in range(batch)], dtype=torch.long)
        x = R44.run_tape(model.effective(m), starts[pick], stages[pick], v.n)
        loss = nll(x, targets[pick], v.n)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_([model.words[w]], 1.0)
        opt.step()
        if step + 1 in snapshots:
            saved[step + 1] = model.words[w].detach().clone()
    return model, saved


@torch.inference_mode()
def word_nll(model, v, m, eps) -> float:
    starts, stages, targets = R44.encode(v, eps)
    return float(nll(R44.run_tape(model.effective(m), starts, stages, v.n), targets, v.n))


R44.fit_word, R44.word_nll = fit_word, word_nll


def episodes(v, w: int, seed: int, wrong: int) -> list:
    eps, _ = R44.make_episodes(v, w, EPISODES, seed, "true")
    rng = R44.make_rng(f"noisy45/{w}/{wrong}", seed)
    for i in rng.sample(range(len(eps)), wrong):
        bad = v.names[rng.randrange(v.n)]
        while bad == eps[i].answer:
            bad = v.names[rng.randrange(v.n)]
        eps[i].answer = bad
    return eps


def main() -> None:
    global ARM
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    if not (a.out / f"base-seed{a.seed}.pt").exists():
        R44.stage_base(a.seed, a.out, False)
    train_v = R44.make_village("train60", a.seed, R44.TRAIN_N, "T")
    fresh_v = R44.make_village("fresh60", a.seed, R44.TRAIN_N, "F")
    m_train, m_fresh = R44.notebook_matrices(train_v), R44.notebook_matrices(fresh_v)
    base_state = torch.load(a.out / f"base-seed{a.seed}.pt", map_location="cpu", weights_only=True)["state"]
    base_model = R44.Reasoner()
    base_model.load_state_dict(base_state)
    probe_qs = R44.base_probe(fresh_v, a.seed, R44.EVAL_PER_SET)
    before = R44.predict(base_model, fresh_v, m_fresh, probe_qs)
    rows = []
    for w in range(R44.N_WORDS):
        fresh_qs = R44.sample_set(fresh_v, f"eval/word{w}/fresh60", a.seed, R44.EVAL_PER_SET, (1,), "resolvable",
                                  vocab=(R44.R + w,))
        for wrong in WRONG_COUNTS:
            for ARM in ARMS:
                eps = episodes(train_v, w, a.seed, wrong)
                rec = R44.sleep_word(base_state, w, eps, train_v, m_train, a.seed, f"{ARM}-wrong{wrong}", before,
                                     probe_qs, fresh_v, m_fresh, fresh_qs, a.out)
                rec.pop("installed_logits", None)
                rec.update(arm=ARM, wrong=wrong, seed=a.seed)
                rows.append(rec)
                print(json.dumps({k: rec.get(k) for k in ("seed", "word", "arm", "wrong", "installed",
                                                          "fresh_accuracy", "routed_chain", "chosen_updates")}))
    (a.out / f"noisy-seed{a.seed}.json").write_text(json.dumps(
        {"seed": a.seed, "eps": EPS, "rows": rows,
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=1))


if __name__ == "__main__":
    main()
