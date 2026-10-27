#!/usr/bin/env python3
"""Experiment 43G/43H: the outside reviewer's "boundary-addressed transport network"
and "continuous compositional sleep", built exactly as specified, as a CONTROL.

HONEST LABEL: this model is handed the address vocabulary.  For output place t of an
n-digit input it may only read six given places:
    (t-1) mod n,  t,  (t+1) mod n,  n-1-t,  floor(t/2),  n-1-floor(t/2)
and it is told two facts about t: "t is odd" and "t is the last place of an odd-length
input".  It LEARNS which place each of the six old skills should read (a soft choice
among the six) and what to do to the digit (a learned 10x10 table).  Output length is
supplied by the wiring (n digits then the end mark), not learned.  It cannot carry.

43G base:   F_o(X) = A_(o,n) X D_o   trained on the registered base data, 12,000 updates.
43H sleep:  the six skills are frozen; a new skill is 21 numbers phi[3,7]:
            X <- sum_k softmax(phi_r)_k F_k(X)  for r = 0,1,2   (F_0 = leave unchanged).
            Probability tapes are passed between stages (no rounding in between).
            Checkpoint is chosen by 4-fold cross-validation on the episodes themselves.
Everything in sleep is gradient arithmetic on 21 numbers; nothing proposes a rule.
Imports CardFold, exp 42 and 43A read-only.  One CPU thread per process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import torch
from torch import Tensor, nn

import fable_cardfold_sleep as C
import fable_autosleep42 as A42
import fable_lengthgate43 as G

OPS = tuple(op for op, _ in C.OLD_PROGRAMS)
SLOT_HEAD = (0, 0, 0, 1, 2, 3)
BITS = torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
CHECKPOINTS = (0, 25, 50, 100, 200, 400)
FOLDS, SLEEP_BATCH, SLEEP_LR = 4, 24, 0.05
LONG_LENGTHS = (12, 16)


def sources(n: int) -> Tensor:
    return torch.tensor([[(t - 1) % n, t, (t + 1) % n, n - 1 - t, t // 2, n - 1 - t // 2] for t in range(n)])


def bit_combo(n: int) -> Tensor:
    return torch.tensor([(t % 2) + 2 * int(n % 2 == 1 and t == n - 1) for t in range(n)])


def one_hot(strings) -> Tensor:
    return nn.functional.one_hot(torch.tensor([[int(ch) for ch in s] for s in strings]), 10).float()


class Transport(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.op_embedding = nn.Embedding(len(OPS), 160)
        self.query = nn.Sequential(nn.Linear(162, 640), nn.GELU(), nn.Linear(640, 160))
        self.keys = nn.Parameter(torch.randn(6, 40))
        self.digit_logits = nn.Parameter(torch.zeros(len(OPS), 10, 10))
        nn.init.normal_(self.op_embedding.weight, std=0.02)
        for layer in (self.query[0], self.query[2]):
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def address(self) -> Tensor:
        """[op, bit combo, slot] soft choice among the six given source places."""
        inp = torch.cat((self.op_embedding.weight[:, None].expand(-1, 4, -1),
                         BITS[None].expand(len(OPS), -1, -1)), dim=-1)
        q = self.query(inp).reshape(len(OPS), 4, 4, 40)[:, :, SLOT_HEAD]        # [op, combo, slot, 40]
        return ((q * self.keys).sum(-1) / math.sqrt(40)).softmax(-1)

    def matrices(self, n: int) -> tuple[Tensor, Tensor]:
        weights = self.address()[:, bit_combo(n)]                                # [op, n, slot]
        a = torch.zeros(len(OPS), n, n).scatter_add(2, sources(n)[None].expand(len(OPS), -1, -1), weights)
        return a, self.digit_logits.softmax(-1)                                  # A [op,n,n], D [op,10,10]

    def forward(self, x: Tensor, ops: Tensor) -> Tensor:
        a, d = self.matrices(x.shape[1])
        return a[ops] @ x @ d[ops]                                               # [B, n, 10]


def by_length(examples):
    groups: dict[int, list] = {}
    for ex in examples:
        groups.setdefault(len(ex.inp), []).append(ex)
    return groups.values()


def digit_nll(prob: Tensor, outs) -> Tensor:
    target = torch.tensor([[int(ch) for ch in s] for s in outs])
    return -prob.clamp_min(1e-12).log().gather(2, target[:, :, None]).squeeze(2)  # [B, n]


# ---------------------------------------------------------------- 43G base
@torch.inference_mode()
def score_old(model: Transport, examples) -> tuple[float, float]:
    hits = total = 0
    prob_sum = digits = 0.0
    for rows in by_length(examples):
        prob = model(one_hot([r.inp for r in rows]), torch.tensor([OPS.index(r.op) for r in rows]))
        target = torch.tensor([[int(ch) for ch in r.out] for r in rows])
        hits += int((prob.argmax(-1) == target).all(1).sum())
        total += len(rows)
        prob_sum += float(prob.gather(2, target[:, :, None]).sum())
        digits += target.numel()
    return hits / total, prob_sum / digits


def evaluate_old(model: Transport, seed: int) -> dict:
    table = {}
    for length in G.EVAL_LENGTHS:
        row = {}
        for op, program in C.OLD_PROGRAMS:
            rng = C.make_rng(f"gate43/eval/{op}/{length}", seed)                 # same test inputs as 43A/C/D
            inputs: set[str] = set()
            while len(inputs) < G.EVAL_PER_OP:
                inputs.add(C.random_digit_string(rng, length))
            acc, prob = score_old(model, C.examples_for_program(op, program, sorted(inputs)))
            row[op] = acc
            row[op + "_prob"] = prob
        row["mean"] = sum(row[op] for op in OPS) / len(OPS)
        table[str(length)] = row
    return table


def stage_base(seed: int, out: Path, smoke: bool) -> None:
    splits = C.build_splits(seed)
    C.assert_split_disjointness(splits)
    torch.manual_seed(C.derive_seed("transport43g/model", seed) & ((1 << 63) - 1))
    model = Transport()
    opt = torch.optim.AdamW(model.parameters(), lr=C.BASE_LR, weight_decay=C.WEIGHT_DECAY)
    updates = 200 if smoke else C.BASE_UPDATES
    t0 = time.time()
    for step in range(updates):
        rows = C.base_step_examples(seed, step, splits)                          # identical data to the registered base
        losses = [digit_nll(model(one_hot([r.inp for r in g]), torch.tensor([OPS.index(r.op) for r in g])),
                            [r.out for r in g]).reshape(-1) for g in by_length(rows)]
        loss = torch.cat(losses).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
    seconds = round(time.time() - t0, 1)
    table = evaluate_old(model, seed)
    choice = model.address().detach()
    r = {"seed": seed, "updates": updates, "smoke": smoke, "train_seconds": seconds,
         "parameters": sum(p.numel() for p in model.parameters()), "final_loss": float(loss.detach()),
         "accuracy_by_length": table,
         "chosen_slot": {op: choice[i].argmax(-1).tolist() for i, op in enumerate(OPS)},
         "chosen_slot_weight": {op: [round(v, 4) for v in choice[i].max(-1).values.tolist()] for i, op in enumerate(OPS)},
         "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out.mkdir(parents=True, exist_ok=True)
    (out / f"base-seed{seed}.json").write_text(json.dumps(r, indent=1))
    torch.save({"seed": seed, "state": model.state_dict()}, out / f"base-seed{seed}.pt")
    print(json.dumps({"seed": seed, "seconds": seconds,
                      "mean_by_length": {k: round(v["mean"], 3) for k, v in table.items()}}))


# ---------------------------------------------------------------- 43H sleep
class Router(nn.Module):
    """A new skill = 21 numbers.  The frozen skill bank is part of the same saved model."""

    def __init__(self, bank: Transport) -> None:
        super().__init__()
        self.bank = bank.requires_grad_(False)
        self.phi = nn.Parameter(torch.zeros(3, len(OPS) + 1))

    def forward(self, x: Tensor) -> Tensor:
        with torch.no_grad():
            a, d = self.bank.matrices(x.shape[1])
        for r in range(3):
            p = self.phi[r].softmax(-1)
            moved = torch.einsum("ktj,bjd,kde->kbte", a, x, d)                   # every frozen skill applied to the tape
            x = p[0] * x + (p[1:, None, None, None] * moved).sum(0)
        return x


def predict(router: Router, examples) -> dict[str, str]:
    out = {}
    with torch.inference_mode():
        for rows in by_length(examples):
            digits = router(one_hot([r.inp for r in rows])).argmax(-1)
            out.update({r.inp: "".join(map(str, d.tolist())) for r, d in zip(rows, digits)})
    return out


def mean_ce(router: Router, examples) -> float:
    with torch.inference_mode():
        per = [digit_nll(router(one_hot([r.inp for r in g])), [r.out for r in g]).mean(1) for g in by_length(examples)]
    return float(torch.cat(per).mean())


def accuracy(router: Router, examples) -> float:
    pred = predict(router, examples)
    return sum(pred[r.inp] == r.out for r in examples) / len(examples)


def fit(bank: Transport, episodes, updates: int, seed: int, tag: str, snapshots=()):
    router = Router(bank)
    opt = torch.optim.Adam([router.phi], lr=SLEEP_LR, betas=(0.9, 0.999), eps=1e-8)
    saved = {0: router.phi.detach().clone()} if 0 in snapshots else {}
    for step in range(updates):
        rng = C.make_rng(f"sleep43h/{tag}/{step}", seed)
        rows = [episodes[rng.randrange(len(episodes))] for _ in range(SLEEP_BATCH)]
        per = [digit_nll(router(one_hot([r.inp for r in g])), [r.out for r in g]).mean(1) for g in by_length(rows)]
        loss = torch.cat(per).mean()                                             # mean per-episode mean digit CE
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_([router.phi], 1.0)
        opt.step()
        if step + 1 in snapshots:
            saved[step + 1] = router.phi.detach().clone()
    return router, saved


def stage_sleep(seed: int, episodes_n: int, out: Path) -> None:
    splits = C.build_splits(seed)
    C.assert_split_disjointness(splits)
    bank = Transport()
    bank.load_state_dict(torch.load(out / f"base-seed{seed}.pt", map_location="cpu", weights_only=True)["state"])
    bank.eval()
    old = [ex for _, rows in splits.regression for ex in rows]
    old_before, _ = score_old(bank, old)
    episodes = list(A42.awake_log(seed, splits, episodes_n))
    order = list(range(episodes_n))
    C.make_rng("sleep43h/folds", seed).shuffle(order)
    t0 = time.time()
    oof = {t: {} for t in CHECKPOINTS}                                           # checkpoint -> input -> prediction
    oof_ce = {t: [] for t in CHECKPOINTS}
    for f in range(FOLDS):
        held = [episodes[i] for k, i in enumerate(order) if k % FOLDS == f]
        train = [episodes[i] for k, i in enumerate(order) if k % FOLDS != f]
        _, saved = fit(bank, train, max(CHECKPOINTS), seed, f"fold{f}", CHECKPOINTS)
        probe = Router(bank)
        for t in CHECKPOINTS:
            probe.phi.data.copy_(saved[t])
            oof[t].update(predict(probe, held))
            oof_ce[t].append(mean_ce(probe, held) * len(held))
    truth = {ex.inp: ex.out for ex in episodes}
    table = {t: {"match": sum(oof[t][x] == y for x, y in truth.items()) / episodes_n,
                 "ce": sum(oof_ce[t]) / episodes_n} for t in CHECKPOINTS}
    eligible = [t for t in CHECKPOINTS if table[t]["match"] >= 0.80]
    r = {"seed": seed, "episodes": episodes_n, "cv_table": {str(t): v for t, v in table.items()},
         "old_skills_before": old_before}
    if not eligible:
        r.update(installed=False, reason="no checkpoint reached 0.80 cross-validated exact match")
    else:
        best = min(table[t]["ce"] for t in eligible)
        chosen = min(t for t in eligible if table[t]["ce"] <= best + 1e-6)
        router, _ = fit(bank, episodes, chosen, seed, "refit")
        refit = predict(router, episodes)
        agreement = sum(refit[x] == oof[chosen][x] for x in truth) / episodes_n
        old_after, _ = score_old(router.bank, old)
        path = out / f"sleep-seed{seed}-ep{episodes_n}.pt"
        torch.save(router.state_dict(), path)                                    # weights only: bank + 21 numbers
        fresh_pred = predict(router, splits.test_fresh)
        reloaded = Router(Transport())
        reloaded.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        reload_ok = predict(reloaded.eval(), splits.test_fresh) == fresh_pred
        longs = {}
        for n in LONG_LENGTHS:
            rng = C.make_rng(f"sleep43h/long/{n}", seed)
            xs: set[str] = set()
            while len(xs) < 100:
                xs.add(C.random_digit_string(rng, n))
            longs[str(n)] = accuracy(router, C.examples_for_program(C.CARDFOLD_OP, C.CARDFOLD, sorted(xs)))
        p = router.phi.detach().softmax(-1)
        r.update(chosen_updates=chosen, refit_agreement=agreement, old_skills_after=old_after,
                 reload_identical=reload_ok, fresh=accuracy(router, splits.test_fresh),
                 long_9_10=accuracy(router, splits.test_long), long=longs,
                 seen=accuracy(router, episodes),
                 routing=[[round(v, 3) for v in row] for row in p.tolist()],
                 routing_names=["keep"] + [" -> ".join(prog) for _, prog in C.OLD_PROGRAMS],
                 installed=bool(agreement >= 0.90 and abs(old_after - old_before) < 1e-9 and reload_ok))
    r.update(sleep_seconds=round(time.time() - t0, 1),
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / f"sleep-seed{seed}-ep{episodes_n}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r.get(k) for k in ("seed", "episodes", "installed", "chosen_updates", "fresh", "long", "sleep_seconds")}))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=("base", "sleep"), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="base only: 200 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    if a.stage == "base":
        stage_base(a.seed, a.out, a.smoke)
    else:
        stage_sleep(a.seed, a.episodes, a.out)


if __name__ == "__main__":
    main()
