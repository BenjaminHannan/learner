"""Streaming trainer for the core: one optimizer step per microbatch, never per token.

The stream yields token-id sequences, or `(tokens, loss_mask)` pairs whose
mask is False for tokens that must not be trained as targets (later: the
model's own wrong answers). Sequences are concatenated and cut into
microbatches of `batch` rows of `seq_len + 1` tokens. Consecutive rows overlap
by one token, so every token after the first is a target exactly once;
leftovers carry over to the next microbatch and are saved with the trainer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import time
from typing import Any, Callable, Iterable, Iterator, Optional, Union

import torch
from torch import nn

from learnlab.core import Core, CoreConfig, lm_loss
from learnlab.readonly import read_only

GIB = 2 ** 30
Item = Union[Any, tuple[Any, Any]]


class MemoryGuardError(RuntimeError):
    """Peak reserved GPU memory passed the limit; the run was stopped."""

    def __init__(self, message: str, peak: int, limit: int) -> None:
        super().__init__(message)
        self.peak, self.limit = peak, limit


@dataclass(frozen=True)
class TrainConfig:
    batch: int = 32
    seq_len: int = 512
    lr: float = 3e-4
    beta1: float = 0.9
    beta2: float = 0.99
    eps: float = 1e-8
    weight_decay: float = 0.1       # matrices only; biases and norms are not decayed
    grad_clip: float = 1.0          # 0 disables clipping (the norm is still logged)
    warmup_steps: int = 0           # 0 = constant LR, else linear warmup then constant
    log_every: int = 50
    eval_every: int = 0             # 0 = never
    memory_limit_bytes: int = 14 * GIB
    memory_check_every: int = 50

    def __post_init__(self) -> None:
        for name in ("batch", "seq_len", "log_every", "memory_check_every"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.lr <= 0 or self.warmup_steps < 0 or self.eval_every < 0 or self.grad_clip < 0:
            raise ValueError("lr must be positive; warmup_steps, eval_every, grad_clip nonnegative")


def reserved_bytes(device: torch.device) -> int:
    """Peak bytes the CUDA caching allocator has reserved in this process (0 off CUDA)."""
    return torch.cuda.max_memory_reserved(device) if device.type == "cuda" else 0


def _segment(item: Item) -> tuple[torch.Tensor, torch.Tensor]:
    if isinstance(item, tuple) and len(item) == 2 and not isinstance(item[0], int):
        tokens, mask = item
    else:
        tokens, mask = item, None
    tokens = torch.as_tensor(tokens, dtype=torch.long).reshape(-1).cpu()
    if mask is None:
        return tokens, torch.ones(tokens.shape, dtype=torch.bool)
    mask = torch.as_tensor(mask, dtype=torch.bool).reshape(-1).cpu()
    if mask.shape != tokens.shape:
        raise ValueError(f"loss mask has {mask.numel()} entries for {tokens.numel()} tokens")
    return tokens, mask


class Trainer:
    """AdamW training of a logits model on a token stream, with health logging."""

    def __init__(self, model: nn.Module, config: TrainConfig,
                 device: Union[str, torch.device] = "cpu") -> None:
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.config = config
        params = list(self.model.parameters())
        self.optimizer = torch.optim.AdamW(
            [{"params": [p for p in params if p.dim() >= 2], "weight_decay": config.weight_decay},
             {"params": [p for p in params if p.dim() < 2], "weight_decay": 0.0}],
            lr=config.lr, betas=(config.beta1, config.beta2), eps=config.eps,
            fused=True if self.device.type == "cuda" else None,
        )
        self.step = 0       # optimizer steps == microbatches trained
        self.tokens = 0     # target positions trained, masked ones included
        self.history: list[dict[str, Any]] = []
        self._carry_tokens = torch.empty(0, dtype=torch.long)
        self._carry_mask = torch.empty(0, dtype=torch.bool)

    def lr_at(self, step: int) -> float:
        warmup = self.config.warmup_steps
        return self.config.lr * (min(1.0, (step + 1) / warmup) if warmup else 1.0)

    def weight_norm(self) -> float:
        with torch.no_grad():
            norms = [torch.linalg.vector_norm(p.float()) for p in self.model.parameters()]
            return torch.linalg.vector_norm(torch.stack(norms)).item()

    def evaluate(self, fn: Callable[[nn.Module], Any]) -> Any:
        """Run `fn(model)` under `read_only`; ReadOnlyViolation if it changed any state."""
        with read_only(self.model, optimizers=[self.optimizer]):
            return fn(self.model)

    def state_dict(self) -> dict[str, Any]:
        return {"step": self.step, "tokens": self.tokens,
                "carry_tokens": self._carry_tokens.clone(), "carry_mask": self._carry_mask.clone()}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.step, self.tokens = int(state["step"]), int(state["tokens"])
        self._carry_tokens = state["carry_tokens"].to("cpu", torch.long)
        self._carry_mask = state["carry_mask"].to("cpu", torch.bool)

    def _next_batch(self, stream: Iterator[Item]) -> Optional[tuple[torch.Tensor, ...]]:
        """(inputs, targets, target_mask), each [batch, seq_len]; None when the stream ends."""
        batch, length = self.config.batch, self.config.seq_len
        need = batch * length + 1
        tokens, masks = [self._carry_tokens], [self._carry_mask]
        count = self._carry_tokens.numel()
        while count < need:
            item = next(stream, None)
            if item is None:
                break
            segment, mask = _segment(item)
            tokens.append(segment)
            masks.append(mask)
            count += segment.numel()
        flat_tokens, flat_mask = torch.cat(tokens), torch.cat(masks)
        if count < need:
            self._carry_tokens, self._carry_mask = flat_tokens, flat_mask
            return None
        self._carry_tokens, self._carry_mask = flat_tokens[need - 1:], flat_mask[need - 1:]
        rows = flat_tokens[:need].unfold(0, length + 1, length)
        row_mask = flat_mask[:need].unfold(0, length + 1, length)
        return rows[:, :-1], rows[:, 1:], row_mask[:, 1:]

    def _step(self, inputs: torch.Tensor, targets: torch.Tensor, mask: torch.Tensor,
              track: bool) -> tuple[torch.Tensor, torch.Tensor, Optional[float]]:
        inputs, targets, mask = (t.to(self.device, non_blocking=True)
                                 for t in (inputs, targets, mask))
        for group in self.optimizer.param_groups:
            group["lr"] = self.lr_at(self.step)
        # A unit is dead on this microbatch if its GELU input is never positive.
        alive: list[torch.Tensor] = []
        hooks = [
            module.register_forward_hook(
                lambda _module, args, _out: alive.append((args[0] > 0).flatten(0, -2).any(0)))
            for module in self.model.modules() if isinstance(module, nn.GELU)
        ] if track else []
        try:
            with torch.autocast(self.device.type, dtype=torch.bfloat16,
                                enabled=self.device.type == "cuda"):
                logits = self.model(inputs)
        finally:
            for hook in hooks:
                hook.remove()
        loss = lm_loss(logits, targets, mask)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            self.model.parameters(), self.config.grad_clip or math.inf)
        self.optimizer.step()
        self.step += 1
        self.tokens += targets.numel()
        dead = 1.0 - torch.cat(alive).float().mean().item() if alive else None
        return loss.detach(), grad_norm, dead

    def _check_memory(self) -> None:
        peak, limit = reserved_bytes(self.device), self.config.memory_limit_bytes
        if peak > limit:
            raise MemoryGuardError(
                f"peak reserved GPU memory {peak / GIB:.2f} GiB exceeds the {limit / GIB:.2f} GiB "
                "limit; stopping now because Windows silently spills GPU memory to system RAM "
                "at about 1/30 speed. Reduce the batch, sequence length or model size.",
                peak, limit)

    def train(self, stream: Iterable[Item], *, max_tokens: Optional[int] = None,
              max_seconds: Optional[float] = None,
              evaluate: Optional[Callable[[nn.Module], Any]] = None,
              on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
        """Train until the stream ends, `max_tokens` more tokens, or `max_seconds` pass.

        Never trains past `max_tokens`. `evaluate(model)` runs every `eval_every`
        steps under `read_only`. Raises MemoryGuardError after the step that
        pushed peak reserved GPU memory over the limit (checked after the first
        step and every `memory_check_every` steps).
        """
        cfg, stream = self.config, iter(stream)
        per_step = cfg.batch * cfg.seq_len
        start_step, start_tokens = self.step, self.tokens
        started = window_start = time.perf_counter()
        window_tokens, window_steps = self.tokens, 0
        loss_sum = torch.zeros((), device=self.device)
        final_loss: Optional[float] = None
        grad_norm = torch.zeros(())
        stop = "stream ended"

        def emit(record: dict[str, Any]) -> None:
            self.history.append(record)
            if on_log is not None:
                on_log(record)

        def log(dead: Optional[float]) -> None:
            nonlocal window_start, window_tokens, window_steps, loss_sum, final_loss
            final_loss = loss_sum.item() / window_steps   # synchronizes the device
            seconds = time.perf_counter() - window_start
            emit({"step": self.step, "tokens": self.tokens,
                  "tokens_per_s": (self.tokens - window_tokens) / max(seconds, 1e-9),
                  "loss": final_loss, "grad_norm": grad_norm.item(),
                  "weight_norm": self.weight_norm(), "dead_mlp_fraction": dead,
                  "lr": self.lr_at(self.step - 1)})
            window_tokens, window_steps = self.tokens, 0
            loss_sum = torch.zeros((), device=self.device)
            window_start = time.perf_counter()

        self.model.train()
        while True:
            if max_tokens is not None and self.tokens - start_tokens + per_step > max_tokens:
                stop = "max_tokens"
                break
            if max_seconds is not None and time.perf_counter() - started >= max_seconds:
                stop = "max_seconds"
                break
            batch = self._next_batch(stream)
            if batch is None:
                break
            track = (self.step + 1) % cfg.log_every == 0
            loss, grad_norm, dead = self._step(*batch, track=track)
            loss_sum += loss
            window_steps += 1
            if self.step == start_step + 1 or self.step % cfg.memory_check_every == 0:
                self._check_memory()
            if track:
                log(dead)
            if evaluate is not None and cfg.eval_every and self.step % cfg.eval_every == 0:
                paused = time.perf_counter()
                emit({"step": self.step, "eval": self.evaluate(evaluate)})
                window_start += time.perf_counter() - paused
        if window_steps:
            log(None)
        seconds = time.perf_counter() - started
        tokens = self.tokens - start_tokens
        cuda = self.device.type == "cuda"
        return {
            "steps": self.step - start_step, "tokens": tokens, "seconds": seconds,
            "tokens_per_s": tokens / max(seconds, 1e-9), "final_loss": final_loss, "stop": stop,
            "peak_gpu_reserved_bytes": reserved_bytes(self.device) if cuda else None,
        }


def pattern_stream(vocab_size: int, seed: int = 0, *, phrase: int = 16, max_stride: int = 7,
                   chunk: int = 256) -> Iterator[torch.Tensor]:
    """Endless deterministic pattern language for smoke runs and tests.

    Token 0 starts each phrase; a phrase is an arithmetic progression over
    tokens 1..vocab_size-1 (mod vocab_size-1) with a random start and a random
    stride in 1..max_stride, so all but its first two tokens are predictable.
    Yields `chunk` phrases at a time.
    """
    if vocab_size < 3:
        raise ValueError("vocab_size must be at least 3")
    generator = torch.Generator().manual_seed(seed)
    span, offsets = vocab_size - 1, torch.arange(phrase)
    separators = torch.zeros(chunk, 1, dtype=torch.long)
    while True:
        start = torch.randint(0, span, (chunk, 1), generator=generator)
        stride = torch.randint(1, max_stride + 1, (chunk, 1), generator=generator)
        body = (start + stride * offsets) % span + 1
        yield torch.cat((separators, body), dim=1).reshape(-1)


def smoke_run(*, size: str = "4M", device: str = "cpu", seconds: float = 60.0,
              max_tokens: Optional[int] = None, seq_len: int = 512, batch: int = 32,
              lr: float = 1e-3, seed: int = 0, vocab_size: int = 2048,
              on_log: Optional[Callable[[dict[str, Any]], None]] = None,
              ) -> tuple[dict[str, Any], Trainer, dict[str, Any]]:
    """Train a preset core on `pattern_stream`: (report, trainer, checkpoint config)."""
    torch.manual_seed(seed)
    core_config = CoreConfig.preset(size, vocab_size=vocab_size, context=seq_len)
    train_config = TrainConfig(batch=batch, seq_len=seq_len, lr=lr)
    model = Core(core_config)
    trainer = Trainer(model, train_config, device)
    config = {
        "core": asdict(core_config), "train": asdict(train_config),
        "stream": {"kind": "pattern_stream", "vocab_size": vocab_size, "seed": seed}, "seed": seed,
    }
    report: dict[str, Any] = {
        "command": "train-lm", "size": size, "device": device, "parameters": model.num_parameters(),
        "limits": {"seconds": seconds, "max_tokens": max_tokens}, "config": config,
    }
    try:
        report.update(status="completed", **trainer.train(
            pattern_stream(vocab_size, seed), max_tokens=max_tokens, max_seconds=seconds,
            on_log=on_log))
    except MemoryGuardError as error:
        report.update(status="aborted", error=str(error), peak_gpu_reserved_bytes=error.peak,
                      steps=trainer.step, tokens=trainer.tokens)
    report["history"] = trainer.history
    return report, trainer, config


__all__ = [
    "GIB", "MemoryGuardError", "TrainConfig", "Trainer", "pattern_stream", "reserved_bytes",
    "smoke_run",
]
