#!/usr/bin/env python3
"""Experiment 60: doc 65, ONE change per arm vs experiment 59's rig.

Imports experiment 59's script (scripts/fable_counter59_signed.py -- itself the
43K-v2 wide-length 4-12 rig with the counter step overridden) and overrides ONLY
the counter step again, plus one loss line for SIGNED-SAT:

DICT arm (`DictCounter`, new): per counter a FIXED dictionary of two dense 2x2
matrices {I, FLIP=[[0,1],[1,0]]} (no learned matrix entries) combined by a
learned 2-way selector logit s_c (softmax over {stay, flip}):
    M_c = p_stay * I + p_flip * FLIP,  x_0 = [1,0],  x_t = x_0 @ M_c^t,
emitted as the pseudo-distribution x_t itself (same [n, 2*N_COUNTERS*K] shape,
K=2, same one-hot endpoints as the rig, so the readout table is untouched).
p=[1,0] is exactly the stay counter; p=[0,1] is exactly the flip counter.
Init: s_c ~ N(0,1) (plain torch.randn; random sign, no hand balance).
HARD=1: selector hardened to argmax (exactly I or exactly FLIP).

SIGNED-SAT arm (`SignedSat`, subclasses exp59's SignedCounter unchanged): the
scalar lam_c = tanh(w_c) verbatim, plus a saturation penalty 0.01*(1-lam^2)
(mean over counters) added to the per-batch loss. Training loop is a copy of
T.stage_base with that one added line (data, optimiser, seeds, updates
identical); everything else inherited.

CONTROL arm (`BalancedStart` from fable_widelengths43k_v2, unchanged).

Select with FABLE60_ARM=dict|signedsat|control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import torch
from torch import Tensor, nn

import fable_learnedparity43j as J
import fable_transport43g as T
import fable_counter59_signed as S59  # the exp-59 rig (wide 4-12 data + SignedCounter)

C = T.C


class DictCounter(J.LearnedParity):
    def __init__(self) -> None:
        super().__init__()
        assert J.K == 2
        # Remove the softmax counter params; keep table + digit_logits untouched.
        del self.start
        del self.step
        # Selector logits s_c ~ N(0,1); column 0 = stay (I), column 1 = flip (FLIP).
        self.sel = torch.nn.Parameter(torch.randn(2 * J.N_COUNTERS, 2))

    def probs(self) -> Tensor:  # [2*N, 2] -- soft (train) or argmax-hardened (eval)
        p = self.sel.softmax(-1)
        if J.HARD:
            p = nn.functional.one_hot(p.argmax(-1), 2).float()
        return p

    def cases(self, n: int) -> Tensor:  # [n, 2*N_COUNTERS*K] -- THE override
        p = self.probs()
        ps, pf = p[:, 0], p[:, 1]
        m0 = torch.stack((ps, pf), dim=-1)
        m1 = torch.stack((pf, ps), dim=-1)
        m = torch.stack((m0, m1), dim=-2)  # [2N, 2, 2]: p_stay*I + p_flip*FLIP
        s = torch.zeros(2 * J.N_COUNTERS, 2, dtype=self.sel.dtype, device=self.sel.device)
        s[:, 0] = 1.0  # fixed start [1,0]
        tape = []
        for _ in range(n):
            tape.append(s)
            s = torch.einsum("ck,ckj->cj", s, m)
        tape = torch.stack(tape)  # [n, counter, state]
        tape = torch.cat((tape[:, : J.N_COUNTERS], tape[:, J.N_COUNTERS :].flip(0)), dim=1)
        return tape.flatten(1)


class SignedSat(S59.SignedCounter):
    def sat_penalty(self) -> Tensor:
        lam = torch.tanh(self.w)
        return 0.01 * (1 - lam ** 2).mean()


ARM = os.environ.get("FABLE60_ARM", "dict")
if ARM == "dict":
    T.Transport = DictCounter
elif ARM == "signedsat":
    T.Transport = SignedSat
else:
    T.Transport = S59.V2.BalancedStart


def stage_base60(seed: int, out: Path, smoke: bool) -> None:
    """Copy of T.stage_base with ONE added line: the saturation penalty for
    arms whose model defines sat_penalty() (SIGNED-SAT only)."""
    splits = C.build_splits(seed)
    C.assert_split_disjointness(splits)
    torch.manual_seed(C.derive_seed("transport43g/model", seed) & ((1 << 63) - 1))
    model = T.Transport()
    opt = torch.optim.AdamW(model.parameters(), lr=C.BASE_LR, weight_decay=C.WEIGHT_DECAY)
    updates = 200 if smoke else C.BASE_UPDATES
    t0 = time.time()
    for step in range(updates):
        rows = C.base_step_examples(seed, step, splits)  # identical data to the registered base
        losses = [T.digit_nll(model(T.one_hot([r.inp for r in g]), torch.tensor([T.OPS.index(r.op) for r in g])),
                              [r.out for r in g]).reshape(-1) for g in T.by_length(rows)]
        loss = torch.cat(losses).mean()
        pen = model.sat_penalty() if hasattr(model, "sat_penalty") else torch.zeros((), device=loss.device)
        loss = loss + pen  # <-- THE loss change (0 for arms without sat_penalty)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
    seconds = round(time.time() - t0, 1)
    table = T.evaluate_old(model, seed)
    choice = model.address().detach()
    r = {"seed": seed, "arm": ARM, "updates": updates, "smoke": smoke, "train_seconds": seconds,
         "parameters": sum(p.numel() for p in model.parameters()), "final_loss": float(loss.detach()),
         "accuracy_by_length": table,
         "chosen_slot": {op: choice[i].argmax(-1).tolist() for i, op in enumerate(T.OPS)},
         "chosen_slot_weight": {op: [round(v, 4) for v in choice[i].max(-1).values.tolist()] for i, op in enumerate(T.OPS)},
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with torch.inference_mode():
        if hasattr(model, "sel"):
            r["selector_probs"] = [[round(float(v), 4) for v in row] for row in model.sel.softmax(-1).tolist()]
        if hasattr(model, "w"):
            r["lams"] = [round(float(v), 4) for v in torch.tanh(model.w).tolist()]
            if hasattr(model, "sat_penalty"):
                r["final_sat_penalty"] = round(float(model.sat_penalty()), 6)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"base-seed{seed}.json").write_text(json.dumps(r, indent=1))
    torch.save({"seed": seed, "arm": ARM, "state": model.state_dict()}, out / f"base-seed{seed}.pt")
    print(json.dumps({"seed": seed, "arm": ARM, "seconds": seconds,
                      "mean_by_length": {k: round(v["mean"], 3) for k, v in table.items()}}))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("base",), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="base only: 200 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    stage_base60(a.seed, a.out, a.smoke)


if __name__ == "__main__":
    main()
