"""D-side (village) step-driven training for V1. Reuses premonition.train.MiniTrainer's step, curriculum and validation;
replaces its FLOP-budget loop with a STEP budget (no FLOP-calibration pass, per spec), a memory guard read from the
detected card, a checkpoint every ~5% of steps and exact resume.

The sealed split (`test`) is never opened here. Data root layout (made by v1/split_dirs.py from the build):
  <root>/train       shards 0-379 (95,000 visits)      <root>/dev   shards 380-399 (5,000 visits, ~5%)
  <root>/validation  held-out families/names/templates <root>/test  SEALED (not touched by any code except v1/sealed_read.py)
"""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import torch

from learnlab import step1
from learnlab.tokenizer import Tokenizer
from memorylab.storage import Budget
from premonition import data as pdata
from premonition import preprocess
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import (Curriculum, MiniTrainer, Plan, planned_loops, mini_train_config, validation_hook,
                               format_record)
from v1 import ckpt as vckpt
from v1 import guard as vguard

SEALED = "test"


@dataclass
class DData:
    tokenizer: Tokenizer
    train: Any
    dev: Any
    validation: Any
    detector: Any


def open_data(root: Path, tokenizer_path: Path, workers: int = 1, log: Callable[[str], None] = print) -> DData:
    """Caches for train / dev / validation only. Refuses the sealed split by construction (it is never listed)."""
    root = Path(root)
    budget = Budget(root.parent, hard=100_000_000_000, steady=80_000_000_000)
    rel = root.name
    tok = Tokenizer.load(tokenizer_path)
    det = pdata.name_detector(budget, rel, workers=workers, log=log)     # fitted on the TRAIN dir only
    caches = {}
    for name in ("train", "dev", "validation"):
        caches[name] = pdata.load_or_build(budget, rel, name, tok, det, split="train" if name == "dev" else None,
                                           workers=workers, regime=preprocess.LABEL_FREE, log=log)
    return DData(tok, caches["train"], caches["dev"], caches["validation"], det)


class StepTrainer(MiniTrainer):
    """MiniTrainer driven by a step budget: the curriculum share is step / total_steps."""

    def __init__(self, model: PremonitionMini, config, device, *, total_steps: int, seed: int = 0,
                 curriculum: Curriculum = Curriculum(), guard_fraction: float = vguard.FRACTION,
                 optimizer: str = "adamw") -> None:
        if optimizer not in ("adamw", "muon"):
            raise ValueError("optimizer must be adamw or muon")
        super().__init__(model, config, device, flop_budget=1.0, curriculum=curriculum, seed=seed)
        self.optimizer_name = optimizer
        if optimizer == "muon":      # Muon on 2-D hidden matrices only; embeddings/head/norms/biases stay on AdamW
            from premonition.muon import MuonAdamW, muon_param_groups
            self.optimizer = MuonAdamW(muon_param_groups(self.model, config.weight_decay), lr=config.lr,
                                       betas=(config.beta1, config.beta2), eps=config.eps,
                                       fused=True if self.device.type == "cuda" else None)
        self.total_steps = int(total_steps)
        self.guard_limit = vguard.limit_bytes(self.device, guard_fraction)
        self.config = config

    def plan(self) -> Plan:
        return self.curriculum.plan(self.step / self.total_steps)

    def optimizer_grouping(self) -> dict[str, Any]:
        """Which parameters each optimizer group holds (printed and checked once in Gate S)."""
        names = {id(p): n for n, p in self.model.named_parameters()}
        out = {"optimizer": self.optimizer_name, "groups": []}
        for g in self.optimizer.param_groups:
            ps = g["params"]
            out["groups"].append({"muon": bool(g.get("muon", False)), "weight_decay": g.get("weight_decay"),
                                  "n_tensors": len(ps), "n_params": sum(p.numel() for p in ps),
                                  "names": [names[id(p)] for p in ps]})
        return out

    def checkpoint_payload(self, extra: Optional[dict] = None) -> dict[str, Any]:
        return {"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict(),
                "trainer": self.state_dict(), "extra": extra or {}}

    def restore(self, payload: dict[str, Any]) -> None:
        self.model.load_state_dict(payload["model"])
        self.optimizer.load_state_dict(payload["optimizer"])
        self.load_state_dict(payload["trainer"])
        vckpt.set_rng_state(payload["rng"])

    def run(self, stream, *, ckpt_dir: Optional[Path] = None, ckpt_every: int = 0, eval_fn: Optional[Callable] = None,
            eval_every: int = 0, log: Callable[[str], None] = print, stop_after: Optional[int] = None,
            on_step: Optional[Callable[[int, dict], None]] = None) -> dict[str, Any]:
        """Train to total_steps (or stop_after steps, for kill tests). `stream` must already be positioned at self.step."""
        self.model.train()
        started = time.perf_counter()
        done_tokens, losses = 0, []
        stream = iter(stream)
        first_step = self.step
        while self.step < self.total_steps:
            if stop_after is not None and self.step - first_step >= stop_after:
                break
            batch = next(stream)
            plan = self.plan()
            loops = planned_loops(batch, plan.mode, self.model.config)
            track = (self.step + 1) % self.config.log_every == 0
            out = self._train_step(batch, plan, loops, track)
            real = int(batch.lengths.sum())
            self.tokens += real
            self.padded_tokens += batch.tokens.numel()
            done_tokens += real
            loss = float(out["loss"])
            if loss != loss or loss in (float("inf"), float("-inf")):
                raise FloatingPointError(f"non-finite loss at step {self.step} (abort rule A1)")
            losses.append((self.step, loss))
            if on_step:
                on_step(self.step, out)
            if self.step == first_step + 1 or self.step % self.config.memory_check_every == 0:
                vguard.check(self.device, self.guard_limit)
            if track:
                log(f"step {self.step}/{self.total_steps} {plan.phase} loss {loss:.4f} lm {float(out['lm']):.3f} "
                    f"ans {float(out['ans']):.3f} {done_tokens / max(time.perf_counter() - started, 1e-9):,.0f} tok/s")
            if eval_fn and eval_every and self.step % eval_every == 0:
                log(f"eval step {self.step}: {json.dumps(eval_fn(self.model), default=float)[:300]}")
            if ckpt_dir is not None and ckpt_every and self.step % ckpt_every == 0:
                vckpt.save(ckpt_dir, self.step, self.checkpoint_payload())
        seconds = time.perf_counter() - started
        cuda = self.device.type == "cuda"
        return {"steps": self.step - first_step, "seconds": seconds, "tokens_per_s": done_tokens / max(seconds, 1e-9),
                "losses": losses, "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved(self.device) if cuda else None}


def train_stream(cache, max_tokens: int, seed: int, skip: int, max_visits: Optional[int] = 48):
    """The deterministic training stream, fast-forwarded past `skip` already-trained batches (resume)."""
    stream = pdata.batches(cache, max_tokens, seed=seed, epochs=None, max_visits=max_visits)
    return itertools.islice(stream, skip, None)
