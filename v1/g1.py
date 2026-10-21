"""G1 guard for the creative module (custom_io `ledger` B2), ported from mainbrain/ (written for the `tool` model).

G1 (spec line 14; coordinator ruling: creative side only) = three parts, all measured on the model's OWN old answers:
  1. K-FAC hard lock: after every optimizer step the change of each Linear/Conv1d [W|b] is projected so it cannot move the
     directions the old answers depend on (mainbrain.kf; energy 0.99, hard mask as in L14 "NK30");
  2. every parameter that is not the weight/bias of such a module (embeddings, LayerNorm, the output bias) is frozen
     (mainbrain.gp.freeze_unprojected);
  3. + KL_WEIGHT x mean KL(parent || model) over KL_ROWS diary rows per update (the L14 recipe: 30x KL on 32 rows).
The parent is the frozen pre-V1 creative model. The diary is the parent's own greedy answers to skills TRAIN prompts.
What is new here (the mainbrain KL only knows the `tool` heads): `kl_to_parent` for the ledger heads.
"""
from __future__ import annotations

import copy
import random
from typing import Any, Optional

import torch
import torch.nn.functional as F

from custom_io.data import Dataset, collate, to_device
from mainbrain import gp, kf
from v1.joint import clone_model

KL_WEIGHT = 30.0
KL_ROWS = 32
ENERGY = 0.99
DIARY_SIZE = 4096     # the s200 sheet run's diary size (domain/far/learn_probe.py GUARD_CONSTANTS note)


def frozen_copy(m: torch.nn.Module) -> torch.nn.Module:
    p = clone_model(m)
    for k in ("loss", "load_state_dict"):
        p.__dict__.pop(k, None)
    p.eval()
    for q in p.parameters():
        q.requires_grad_(False)
    return p


def _gold_from(o: dict[str, Any], M: int) -> dict[str, torch.Tensor]:
    """Teacher forcing that reproduces the parent's own greedy program: op index and one-hot allowed operand slots."""
    ops, a, b = o["prog"]
    oh = lambda t: F.one_hot(t, M).bool()
    return {"op": ops, "a": oh(a), "b": oh(b)}


def _kl(lp: torch.Tensor, lq: torch.Tensor) -> torch.Tensor:
    """KL(P || Q) over the last dim from log-probs."""
    return (lp.exp() * (lp - lq)).sum(-1)


def kl_to_parent(model, parent, batch) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Forward KL from the frozen parent to `model` over every output distribution of the ledger loss, on the parent's own
    greedy path (both see the same forced program). Weighting follows `Ledger.loss`: ops weighted 1 / w_noop, operand
    pointers on call rows, mode on all rows, answer pointer on mode-0 rows, word pointer on mode-1 rows, GEN registers on
    mode-2 rows up to the first EOS. Equals 0 (and has zero gradient) when model == parent."""
    dev = batch["prompt_ids"].device
    with torch.no_grad():
        op_ = parent.run(batch)                       # greedy: the parent's own answer path
        M = op_["valid"].shape[1]
        gold = _gold_from(op_, M)
    om = model.run(batch, gold=gold)
    with torch.no_grad():
        opg = parent.run(batch, gold=gold)            # same path, forced; identical logits to the greedy run
        pg = parent.gen_copy(opg["R"], opg["X"], opg["xm"], batch["prompt_ids"])[0] if parent.copy else None
    B = batch["prompt_ids"].shape[0]
    has = gold["op"] > 0                              # [B, L] rows that call at step s
    w_row = torch.where(has, torch.ones((), device=dev), torch.full((), float(parent.w_noop), device=dev))
    parts: dict[str, torch.Tensor] = {}
    kop = kptr = torch.zeros((), device=dev)
    for s, ((lgm, lam, lbm), (lgp, lap, lbp)) in enumerate(zip(om["steps"], opg["steps"])):
        kop = kop + (_kl(lgp.float().log_softmax(-1), lgm.float().log_softmax(-1)) * w_row[:, s]).mean()
        kptr = kptr + ((_kl(lap.float().log_softmax(-1), lam.float().log_softmax(-1))
                        + _kl(lbp.float().log_softmax(-1), lbm.float().log_softmax(-1))) * has[:, s]).sum() / B
    parts["op"], parts["ptr"] = kop, kptr
    mode = opg["lmode"].float().argmax(-1)
    parts["mode"] = _kl(opg["lmode"].float().log_softmax(-1), om["lmode"].float().log_softmax(-1)).mean()
    parts["ans"] = (_kl(opg["lans"].float().log_softmax(-1), om["lans"].float().log_softmax(-1)) * (mode == 0)).sum() / B
    parts["word"] = (_kl(opg["lword"].float().log_softmax(-1), om["lword"].float().log_softmax(-1)) * (mode == 1)).sum() / B
    if parent.copy and pg is not None:
        pm = model.gen_copy(om["R"], om["X"], om["xm"], batch["prompt_ids"])[0]
        eos = 2
        first_eos = (pg.argmax(-1) == eos).float().cumsum(1)          # positions up to and including the first EOS
        live = (first_eos <= 1).float() * (mode == 2).float()[:, None]
        per = (pg * (torch.log(pg + 1e-6) - torch.log(pm + 1e-6))).sum(-1)
        n_t = live.sum(1).clamp(min=1)
        parts["gen"] = ((per * live).sum(1) / n_t).sum() / B
    total = sum(parts.values())
    return total, {k: v.detach() for k, v in parts.items()}


def build_diary(parent, rows: list[dict], n: int = DIARY_SIZE, seed: int = 0, bs: int = 64, device: str = "cpu") -> list[dict]:
    """The parent's own greedy answers to `n` skills TRAIN prompts (seeded shuffle): rows with prompt + the parent's answer.
    Only prompts of the skills train file are used; no dev/sealed row can enter."""
    pool = list(rows)
    random.Random(f"{seed}-diary").shuffle(pool)
    pool = pool[:n]
    out: list[dict] = []
    parent.eval()
    with torch.no_grad():
        for s in range(0, len(pool), bs):
            chunk = pool[s:s + bs]
            ds = Dataset([{"id": f"d{s + i}", "prompt": r["prompt"], "answer": "", "accepted": [], "family": r.get("family", ""),
                           "level": r.get("level", 0)} for i, r in enumerate(chunk)], parent.vocab, strict=False)
            b = to_device(collate([ds[i] for i in range(len(chunk))]), device)
            ans = parent.generate(b)
            for i, r in enumerate(chunk):
                out.append({"id": f"diary:{s + i}", "prompt": r["prompt"], "answer": ans[i], "accepted": [ans[i]],
                            "family": r.get("family", ""), "level": r.get("level", 0), "source": "diary", "steps": []})
    return out


class G1:
    """Per-sleep-phase guard. `begin(model, device)` measures K-FAC factors on the CURRENT weights over the diary (on a CPU copy;
    the statistics code is CPU-only), freezes unprojected tensors, and returns the projected optimizer wrapper factory.
    `extra_loss(model, step)` is the KL term. Log fields in `self.log` (kl_mean, kl_parts, frozen count, protected share)."""

    def __init__(self, parent, diary: list[dict], vocab, kl_weight: float = KL_WEIGHT, kl_rows: int = KL_ROWS,
                 energy: float = ENERGY, seed: int = 0, device: str = "cpu") -> None:
        self.parent, self.diary, self.vocab = parent, diary, vocab
        self.kl_weight, self.kl_rows, self.energy, self.seed, self.device = kl_weight, kl_rows, energy, seed, device
        self.rng = random.Random(f"{seed}-klrows")
        self.F: Optional[dict] = None
        self.frozen: list[str] = []
        self.info: dict[str, Any] = {}
        self.kls: list[float] = []
        self.kl_parts_last: dict[str, float] = {}

    def begin(self, model) -> dict[str, Any]:
        cpu = clone_model(model).to("cpu")
        if model.__dict__.get("bridge_in") is not None:      # the statistics code is CPU-only: freeze the bridge vector as a CPU constant
            with torch.no_grad():
                vec = model.bridge_in().detach().cpu()
            cpu.bridge_in = lambda v=vec: v
            cpu.bridge_out = None
        stats = kf.kfac_stats(cpu, self.diary[:1024], bs=64)       # hard mask measured on the model's own old answers
        F, info = kf.factors(stats, self.energy, soft=None)
        self.F = {n: tuple(t.to(self.device) for t in f) for n, f in F.items()}
        for p in model.parameters():
            p.requires_grad_(True)
        self.frozen = gp.freeze_unprojected(model)
        free = [v["free_share"] for v in info.values()]
        self.info = {"layers": len(info), "frozen_tensors": len(self.frozen), "mean_free_share": sum(free) / max(len(free), 1),
                     "energy": self.energy}
        return self.info

    def wrap_optimizer(self, model, base):
        return _DeviceKFOptimizer(model, base, self.F)

    def extra_loss(self, model) -> torch.Tensor:
        rows = self.rng.sample(self.diary, min(self.kl_rows, len(self.diary)))
        ds = Dataset(rows, self.vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(rows))]), self.device)
        was = model.training
        model.eval()                                                # no drills / dropout in the KL pass, as in mainbrain.klreplay
        kl, parts = kl_to_parent(model, self.parent, batch)
        model.train(was)
        self.kls.append(float(kl.detach()))
        self.kl_parts_last = {k: float(v) for k, v in parts.items()}
        return self.kl_weight * kl


class _DeviceKFOptimizer(kf.KFOptimizer):
    """mainbrain.kf.KFOptimizer with the bias-less fallback created on the weight's device (the original assumes CPU)."""

    def step(self):
        old = [_aug(mod).detach().clone() for _, mod, _ in self.mods]
        self.base.step()
        for (n, mod, f), A0 in zip(self.mods, old):
            _set_aug(mod, A0 + kf.project(_aug(mod).detach() - A0, f))
        self.n += 1


def _aug(mod):
    W = mod.weight.reshape(mod.weight.shape[0], -1)
    b = mod.bias if mod.bias is not None else torch.zeros(W.shape[0], device=W.device, dtype=W.dtype)
    return torch.cat([W, b[:, None]], 1)


def _set_aug(mod, A):
    with torch.no_grad():
        mod.weight.copy_(A[:, :-1].reshape(mod.weight.shape))
        if mod.bias is not None:
            mod.bias.copy_(A[:, -1])
