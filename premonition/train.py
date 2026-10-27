"""Training Premonition-mini (design/06 §3-4, §7-8; build steps 4-6).

`MiniTrainer` subclasses `learnlab.train.Trainer`, keeping its AdamW parameter groups (matrices decayed,
biases and norms not), linear warmup, gradient clipping, bf16 autocast on CUDA, `read_only` evaluation and the
GPU memory guard. It replaces the token-stream batching with whole-visit `VisitBatch`es and adds:

- The curriculum by share of the FLOP budget (`Curriculum`, §3): 0-5% "gold" (gold cards loaded before
  loop 1, 2 loops, L_lm + L_ans), 5-30% "teacher" (teacher-forced cards, ceil(|G| / 4) + 3 loops, all four
  losses), 30-100% "own" (8 loops; p_own rises 0 -> 0.75 by 60% of the budget, then stays flat).
- A FLOP-budget stop (§4): `calibrate` measures a few batches in every mode with `flops.measure_mini` (the
  FlopCounterMode convention that every contender is charged in) and fits FLOPs = a * padded tokens +
  b * sum(questions x loops); each step is charged the fitted cost of its batch (the loop count of a batch
  is known before the step), and training stops at the budget F, never past F * (1 + BUDGET_TOLERANCE).
- Logging every `log_every` steps: every loss, gold recall@4 of the model's own first ASK against the oracle
  gold, answer accuracy, loops per question, the HALT rate, tokens/s and FLOPs spent, plus the card
  diagnostics of `card_stats` (risks below).
- Validation (`validate`): own-retrieval exact match through `PremonitionMini.answer`, the same with the
  gold cards given (`answer_with_gold`; the teacher-forced number of build steps 5-6), recall@4 against a
  random-fetch baseline, loops and halting by depth, and per-slice accuracy when batches carry slice tags.
- Experiment-1 scoring for D (`d_scorer`, `evaluate_d_checkpoint`): exp1 only scores `Core` checkpoints, so
  D plugs its own scorer into `exp1.evaluate_directory` (items, tags, replay, attach and slice report are
  exp1's); the report has exp1's shape, so `exp1.verdict` takes it unchanged.
- Checkpoints through `learnlab.ckpt`, with the config, tokenizer digest, detector digest, data tag and the
  preprocessing identity of the visits D read (`premonition.preprocess.identity("label-free")`).
- Inputs (design/06 §9.1, §11): D trains and is scored on the label-free v2 visit cache
  (`premonition.data.load_or_build(..., regime="label-free")`), where answers and feedback were removed from
  the text before names were bound. `label_free` below is the LEGACY batch-level rule (it drops answer tokens
  after encoding, when names from labels have already been bound); it is kept for the toy task, whose
  question lines carry no names, and for comparison.
- `train_toy` (build step 4, `premonition.toy`), `train_d` (the village run a CLI calls) and `smoke` (CPU).

Risks watched (design/06 §7 and the model review), all from `card_stats`:
- the set cross-entropy is satisfied by ONE gold card in the top-4: we report the share of told questions
  whose FULL gold set was fetched, next to recall@4 and "any gold fetched";
- the 16-row first-in-first-out card rows evict early cards once more than 16 were inserted (|G| > ~10 in
  teacher mode, 4 gold + up to 2 distractors per loop): we count questions that overflowed and those that
  lost a gold card that way (the model still treats an evicted card as fetched);
- the L_ans early weight (x0.2 before the loop holding every gold card): we report the share of
  (question, loop) answer terms at the early weight and the questions that never reach full weight.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass, field
import itertools
import math
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence, Union

import torch
from torch import nn

from learnlab import step1
from learnlab.ckpt import load_checkpoint, read_config, save_checkpoint
from learnlab.core import IGNORE_INDEX
from learnlab.policy import BUDGET_TOLERANCE
from learnlab.train import MemoryGuardError, TrainConfig, Trainer
from premonition import data as pdata
from premonition import identity, preprocess
from premonition.batch import N_ENT, PAD_ID, NameTable, VisitBatch
from premonition.config import MiniConfig
from premonition.flops import FlopFit, fit_flops, measure_mini
from premonition.model import Answers, PremonitionMini
from premonition.pointer import answer_text

Log = Callable[[str], None]
FORMAT = "premonition-mini-checkpoint"
FORMAT_VERSION = 1


# ----------------------------------------------------------------------------- curriculum
@dataclass(frozen=True)
class Plan:
    phase: str          # "gold", "teacher" or "own"
    mode: str           # PremonitionMini.forward mode
    p_own: float


@dataclass(frozen=True)
class Curriculum:
    """design/06 §3, by share of the FLOP budget spent before the step."""

    gold_until: float = 0.05
    teacher_until: float = 0.30
    ramp_until: float = 0.60
    p_own_max: float = 0.75

    def __post_init__(self) -> None:
        if not 0.0 <= self.gold_until <= self.teacher_until <= self.ramp_until:
            raise ValueError("need 0 <= gold_until <= teacher_until <= ramp_until")
        if not 0.0 <= self.p_own_max <= 1.0:
            raise ValueError("p_own_max must be a probability")

    def plan(self, share: float) -> Plan:
        if share < self.gold_until:
            return Plan("gold", "gold", 0.0)
        if share < self.teacher_until:
            return Plan("teacher", "teacher", 0.0)
        span = self.ramp_until - self.teacher_until
        ramp = 1.0 if span <= 0 else min(1.0, (share - self.teacher_until) / span)
        return Plan("own", "own", self.p_own_max * ramp)


def planned_loops(batch: VisitBatch, mode: str, config: MiniConfig) -> torch.Tensor:
    """[Q] think loops `PremonitionMini.forward(batch, mode)` runs (no `loops` override), on the CPU."""
    count = batch.q_visit.shape[0]
    if mode == "gold":
        loops = torch.full((count,), 2, dtype=torch.long)
    elif mode == "teacher":
        told = (batch.gold_lines.cpu() >= 0).sum(1).clamp_min(1)
        loops = -(-told // config.top_k) + 3
    elif mode == "own":
        loops = torch.full((count,), config.max_loops, dtype=torch.long)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return loops.clamp(1, config.max_loops)


def mini_train_config(**overrides: Any) -> TrainConfig:
    """design/06 §3 optimisation: AdamW with Trainer's groups, lr 1e-3, warmup 100, clip 1.0.
    `batch` and `seq_len` are unused by MiniTrainer (batches are whole visits)."""
    settings: dict[str, Any] = dict(batch=1, seq_len=1, lr=1e-3, warmup_steps=100, grad_clip=1.0, log_every=50)
    settings.update(overrides)
    return TrainConfig(**settings)


# ----------------------------------------------------------------------------- card diagnostics
class InsertLog:
    """Records every card insertion of `model` (in `forward`, `answer` or `answer_with_gold`) while active.

    It shadows the bound `_insert` with a recording wrapper on the instance and removes it on exit, so the
    model is unchanged afterwards (and a surrounding `read_only` sees no difference).
    """

    def __init__(self, model: PremonitionMini) -> None:
        self.model = model
        self.calls: list[tuple[torch.Tensor, torch.Tensor]] = []

    def __enter__(self) -> InsertLog:
        original = self.model._insert

        def record(episode: Any, store: Any, index: torch.Tensor, cards: torch.Tensor) -> None:
            self.calls.append((index.detach().cpu(), cards.detach().cpu()))
            return original(episode, store, index, cards)

        self.model._insert = record  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: Any) -> None:
        del self.model._insert


def gold_sets(batch: VisitBatch) -> tuple[list[set[int]], list[bool]]:
    """Per question: G as score-vector indices (NULL = number of lines when never told), and told."""
    null = batch.line_start.shape[1]
    gold = batch.gold_lines.cpu()
    sets, told = [], []
    for row in gold:
        lines = set(row[row >= 0].tolist())
        told.append(bool(lines))
        sets.append(lines or {null})
    return sets, told


def card_stats(calls: Sequence[tuple[torch.Tensor, torch.Tensor]], batch: VisitBatch, loops: torch.Tensor,
               card_rows: int, *, offset: int) -> dict[str, Any]:
    """Risk counts from recorded insertions. `offset`: the loop from which call 0's cards are rows (0 when
    call 0 is a preload before loop 1, else 1: call c comes after loop c). `loops`: [Q] loops each ran."""
    sets, told = gold_sets(batch)
    count = len(sets)
    sequences: list[list[tuple[int, int]]] = [[] for _ in range(count)]
    for call, (index, cards) in enumerate(calls):
        for row, question in enumerate(index.tolist()):
            sequences[question].extend((card, call + offset) for card in cards[row].tolist() if card >= 0)
    loops = loops.cpu().tolist()
    out = dict(questions=count, told=sum(told), multi_gold=0, big_gold=0, any_gold=0, full_gold=0,
               multi_full=0, overflow=0, gold_evicted=0, early_terms=0, answer_terms=0, never_full=0)
    for q in range(count):
        gold, seq, n = sets[q], sequences[q], int(loops[q])
        got: set[int] = set()
        full_loop = None
        for card, loop in seq:
            got.add(card)
            if full_loop is None and gold <= got:
                full_loop = loop
        out["answer_terms"] += n
        out["early_terms"] += n if full_loop is None else min(max(full_loop, 0), n)
        out["never_full"] += full_loop is None or full_loop >= n
        overflow = max(0, len(seq) - card_rows)
        out["overflow"] += overflow > 0
        if overflow and gold & {card for card, _ in seq[:overflow]}:
            out["gold_evicted"] += 1
        if told[q]:
            out["any_gold"] += bool(gold & got)
            out["full_gold"] += gold <= got
            out["multi_gold"] += len(gold) > 1
            out["multi_full"] += len(gold) > 1 and gold <= got
            out["big_gold"] += len(gold) > 10
    return out


def summarize_cards(stats: dict[str, Any]) -> dict[str, Any]:
    """Shares from summed `card_stats` counts."""
    told, multi = max(stats["told"], 1), max(stats["multi_gold"], 1)
    return {
        "full_gold_fetched": stats["full_gold"] / told if stats["told"] else None,
        "any_gold_fetched": stats["any_gold"] / told if stats["told"] else None,
        "multi_gold_full_fetched": stats["multi_full"] / multi if stats["multi_gold"] else None,
        "questions_multi_gold": stats["multi_gold"],
        "questions_gold_over_10": stats["big_gold"],
        "fifo_overflow_questions": stats["overflow"],
        "fifo_gold_evicted_questions": stats["gold_evicted"],
        "ans_early_weight_share": stats["early_terms"] / max(stats["answer_terms"], 1),
        "ans_never_full_weight": stats["never_full"] / max(stats["questions"], 1),
    }


def _add(total: dict[str, Any], part: Mapping[str, Any]) -> None:
    for key, value in part.items():
        total[key] = total.get(key, 0) + value


# ----------------------------------------------------------------------------- the trainer
class MiniTrainer(Trainer):
    """`Trainer` for `PremonitionMini` on `VisitBatch` streams, stopped by a FLOP budget (module docstring)."""

    def __init__(self, model: PremonitionMini, config: TrainConfig, device: Union[str, torch.device] = "cpu", *,
                 flop_budget: float, curriculum: Curriculum = Curriculum(), tolerance: float = BUDGET_TOLERANCE,
                 seed: int = 0, fit: Optional[FlopFit] = None) -> None:
        if not flop_budget > 0:
            raise ValueError("flop_budget must be positive")
        super().__init__(model, config, device)
        self.flop_budget = float(flop_budget)
        self.curriculum = curriculum
        self.tolerance = float(tolerance)
        self.seed = seed
        self.fit = fit
        self.calibration: dict[str, Any] = {}
        self.flops = 0.0                  # fitted training FLOPs spent
        self.padded_tokens = 0            # [B, T] positions read
        self.question_loops = 0
        self.questions = 0
        self.generator = torch.Generator(device=self.device).manual_seed(seed)

    # ------------------------------------------------------------------ FLOPs
    def calibrate(self, batches: Sequence[VisitBatch], modes: Sequence[str] = ("gold", "teacher", "own")
                  ) -> FlopFit:
        """Fit the per-batch cost on `batches` measured in every mode (FlopCounterMode, forward + backward)."""
        samples = []
        started = time.perf_counter()
        for batch in batches:
            batch = batch.to(self.device)
            for mode in modes:
                samples.append(measure_mini(self.model, batch, mode=mode, p_own=0.5 if mode == "own" else 0.0,
                                            generator=self.generator))
        self.fit = fit_flops(samples)
        self.calibration = {"a": self.fit.a, "b": self.fit.b, "worst_residual": self.fit.worst,
                            "samples": [asdict(s) for s in samples], "seconds": time.perf_counter() - started}
        return self.fit

    def batch_cost(self, batch: VisitBatch, plan: Plan) -> tuple[float, torch.Tensor]:
        if self.fit is None:
            raise RuntimeError("call calibrate() or pass fit= before training")
        loops = planned_loops(batch, plan.mode, self.model.config)
        return self.fit(batch.tokens.numel(), int(loops.sum())), loops

    def plan(self) -> Plan:
        return self.curriculum.plan(self.flops / self.flop_budget)

    # ------------------------------------------------------------------ state
    def state_dict(self) -> dict[str, Any]:
        return {"step": self.step, "tokens": self.tokens, "padded_tokens": self.padded_tokens,
                "flops": self.flops, "question_loops": self.question_loops, "questions": self.questions,
                "generator": self.generator.get_state()}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.step, self.tokens = int(state["step"]), int(state["tokens"])
        self.padded_tokens, self.flops = int(state["padded_tokens"]), float(state["flops"])
        self.question_loops, self.questions = int(state["question_loops"]), int(state["questions"])
        self.generator.set_state(state["generator"].cpu())

    def _next_batch(self, stream: Iterator[VisitBatch]) -> Optional[VisitBatch]:   # type: ignore[override]
        return next(stream, None)

    # ------------------------------------------------------------------ one step
    def _train_step(self, batch: VisitBatch, plan: Plan, loops: torch.Tensor, track: bool) -> dict[str, Any]:
        model, config = self.model, self.model.config
        batch = batch.to(self.device)
        for group in self.optimizer.param_groups:
            group["lr"] = self.lr_at(self.step)
        alive: list[torch.Tensor] = []
        halts: list[torch.Tensor] = []
        hooks = []
        if track:
            hooks = [module.register_forward_hook(
                lambda _m, args, _o: alive.append((args[0] > 0).flatten(0, -2).any(0)))
                for module in model.modules() if isinstance(module, nn.GELU)]
            hooks.append(model.heads.halt.register_forward_hook(
                lambda _m, _a, out: halts.append(out.detach().float().flatten())))
        recorder = InsertLog(model) if track and config.store else None
        try:
            with recorder or nullcontext(), torch.autocast(self.device.type, dtype=torch.bfloat16,
                                                           enabled=self.device.type == "cuda"):
                out = model(batch, mode=plan.mode, p_own=plan.p_own, generator=self.generator)
        finally:
            for hook in hooks:
                hook.remove()
        loss = out["loss"]
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), self.config.grad_clip or math.inf)
        self.optimizer.step()
        self.step += 1
        result: dict[str, Any] = {name: out[name].detach().float() for name in ("loss", "lm", "ask", "ans", "halt")}
        result["grad_norm"] = grad_norm
        result["metrics"] = out["metrics"]
        if track:
            result["dead"] = 1.0 - torch.cat(alive).float().mean().item() if alive else None
            result["halt_rate"] = torch.cat(halts).gt(0).float().mean().item() if halts else None
            if recorder is not None:
                result["cards"] = card_stats(recorder.calls, batch, loops, config.card_rows,
                                             offset=0 if plan.mode == "gold" else 1)
        return result

    # ------------------------------------------------------------------ the loop
    def train(self, stream: Iterable[VisitBatch], *, max_seconds: Optional[float] = None,   # type: ignore[override]
              max_steps: Optional[int] = None, evaluate: Optional[Callable[[nn.Module], Any]] = None,
              on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
        """Train until the FLOP budget is spent (or the stream ends, `max_seconds`, `max_steps`).

        Never trains a batch that would take the spend past budget x (1 + tolerance). `evaluate(model)`
        runs every `eval_every` steps under `read_only`.
        """
        cfg, stream = self.config, iter(stream)
        if self.fit is None:
            raise RuntimeError("call calibrate() or pass fit= before training")
        budget, ceiling = self.flop_budget, self.flop_budget * (1.0 + self.tolerance)
        start_step, start_tokens, start_flops = self.step, self.tokens, self.flops
        started = window_start = time.perf_counter()
        window: dict[str, Any] = {}
        counts: dict[str, int] = {}
        window_steps = window_tokens = window_padded = window_questions = window_loops = 0
        final: dict[str, Optional[float]] = {}
        phases: dict[str, dict[str, Any]] = {}
        mismatched = 0
        stop = "stream ended"
        last: dict[str, Any] = {}

        def emit(record: dict[str, Any]) -> None:
            self.history.append(record)
            if on_log is not None:
                on_log(record)

        def accumulate(name: str, value: Optional[torch.Tensor]) -> None:
            if value is None:
                return
            window[name] = window.get(name, 0.0) + value.detach().float()
            counts[name] = counts.get(name, 0) + 1

        def log(plan: Plan) -> None:
            nonlocal window, counts, window_steps, window_tokens, window_padded, window_questions, window_loops
            nonlocal window_start
            seconds = max(time.perf_counter() - window_start, 1e-9)
            means = {name: (value / counts[name]).item() for name, value in window.items()}
            final.update(means)
            record: dict[str, Any] = {
                "step": self.step, "flops": self.flops, "flops_share": self.flops / budget, "phase": plan.phase,
                "p_own": plan.p_own, "lr": self.lr_at(self.step - 1), "tokens": self.tokens,
                "padded_tokens": self.padded_tokens, "tokens_per_s": window_tokens / seconds,
                "padded_tokens_per_s": window_padded / seconds,
                "loops_per_question": window_loops / max(window_questions, 1),
                **{name: means.get(name) for name in ("loss", "lm", "ask", "ans", "halt")},
                "gold_recall_at_4": means.get("recall_at_k"), "answer_acc": means.get("answer_acc"),
                "answer_acc_first": means.get("answer_acc_first"),
                "grad_norm": float(last["grad_norm"]), "weight_norm": self.weight_norm(),
                "dead_mlp_fraction": last.get("dead"), "halt_rate": last.get("halt_rate"),
            }
            if "cards" in last:
                record["cards"] = summarize_cards(last["cards"])
            emit(record)
            window, counts = {}, {}
            window_steps = window_tokens = window_padded = window_questions = window_loops = 0
            window_start = time.perf_counter()

        self.model.train()
        plan = self.plan()
        while True:
            if self.flops >= budget:
                stop = "flop budget"
                break
            if max_seconds is not None and time.perf_counter() - started >= max_seconds:
                stop = "max_seconds"
                break
            if max_steps is not None and self.step - start_step >= max_steps:
                stop = "max_steps"
                break
            batch = self._next_batch(stream)
            if batch is None:
                break
            plan = self.plan()
            cost, loops = self.batch_cost(batch, plan)
            if self.flops + cost > ceiling:
                stop = "flop budget (the next batch would pass the tolerance)"
                break
            track = (self.step + 1) % cfg.log_every == 0
            last = self._train_step(batch, plan, loops, track)
            ran = int(last["metrics"]["question_loops"])
            mismatched += ran != int(loops.sum())
            self.flops += cost
            real = int(batch.lengths.sum())
            self.tokens += real
            self.padded_tokens += batch.tokens.numel()
            self.question_loops += ran
            self.questions += batch.q_visit.shape[0]
            window_steps += 1
            window_tokens += real
            window_padded += batch.tokens.numel()
            window_questions += batch.q_visit.shape[0]
            window_loops += ran
            for name in ("loss", "lm", "ask", "ans", "halt"):
                accumulate(name, last[name])
            metrics = last["metrics"]
            for name in ("answer_acc", "answer_acc_first"):
                accumulate(name, metrics.get(name))
            if "recall_at_k" in metrics and bool((batch.gold_lines >= 0).any()):
                accumulate("recall_at_k", metrics["recall_at_k"])
            entry = phases.setdefault(plan.phase, {"steps": 0, "flops": 0.0, "first_step": self.step})
            entry["steps"] += 1
            entry["flops"] += cost
            if self.step == start_step + 1 or self.step % cfg.memory_check_every == 0:
                self._check_memory()
            if track:
                log(plan)
            if evaluate is not None and cfg.eval_every and self.step % cfg.eval_every == 0:
                paused = time.perf_counter()
                emit({"step": self.step, "flops": self.flops, "flops_share": self.flops / budget,
                      "eval": self.evaluate(evaluate)})
                window_start += time.perf_counter() - paused
        if window_steps:
            last.pop("cards", None)
            last.setdefault("dead", None)
            log(plan)
        seconds = time.perf_counter() - started
        share = self.flops / budget
        cuda = self.device.type == "cuda"
        return {
            "steps": self.step - start_step, "tokens": self.tokens - start_tokens, "seconds": seconds,
            "tokens_per_s": (self.tokens - start_tokens) / max(seconds, 1e-9), "stop": stop,
            "flops": self.flops - start_flops, "flops_total": self.flops, "flop_budget": budget,
            "flops_share": share, "tolerance": self.tolerance, "budget_ok": abs(share - 1.0) <= self.tolerance,
            "flops_per_token": self.flops / max(self.tokens, 1), "fit": self.calibration or (
                None if self.fit is None else {"a": self.fit.a, "b": self.fit.b, "worst_residual": self.fit.worst}),
            "loop_mismatches": mismatched, "phases": phases, "final": final,
            "peak_gpu_reserved_bytes": torch.cuda.max_memory_reserved(self.device) if cuda else None,
        }


def budget_for_steps(trainer: MiniTrainer, batches: Sequence[VisitBatch], steps: int,
                     curriculum: Optional[Curriculum] = None) -> float:
    """A FLOP budget of about `steps` batches like `batches` under the curriculum (for toys and smoke runs)."""
    curriculum = curriculum or trainer.curriculum
    config = trainer.model.config
    mean = 0.0
    for share in (0.02, 0.2, 0.7):
        plan = curriculum.plan(share)
        costs = [trainer.fit(b.tokens.numel(), int(planned_loops(b, plan.mode, config).sum())) for b in batches]
        weight = {0.02: curriculum.gold_until, 0.2: curriculum.teacher_until - curriculum.gold_until,
                  0.7: 1.0 - curriculum.teacher_until}[share]
        mean += weight * sum(costs) / len(costs)
    return steps * mean


# ----------------------------------------------------------------------------- answers and validation
@torch.no_grad()
def answer_with_gold(model: PremonitionMini, batch: VisitBatch, *, stop: Optional[Iterable[int]] = None,
                     max_loops: Optional[int] = None) -> Answers:
    """`PremonitionMini.answer` with the question's gold cards (NULL when never told) placed in its card rows
    before loop 1: the teacher-forced counterpart of own retrieval. Halting and further ASKs are the model's."""
    config = model.config
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    count = batch.q_visit.shape[0]
    device = hidden.device
    mentions = model._mentions(batch)
    episode = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(count, device=device)
    if store is not None and count:
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, config.card_rows)
        preload = torch.where(gold, torch.arange(gold.shape[1], device=device),
                              torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
        model._insert(episode, store, everyone, preload)
    limit = min(max_loops or config.max_loops, config.max_loops)
    running = torch.ones(count, dtype=torch.bool, device=device)
    used = torch.zeros(count, dtype=torch.long, device=device)
    halt_prob = torch.zeros(count, device=device)
    first_top = torch.full((count, config.top_k), -1, dtype=torch.long, device=device)
    for step in range(limit):
        index = torch.nonzero(running).squeeze(1)
        if index.numel() == 0:
            break
        rows, halt, ask, scores = model._step(episode, index, step, store)
        used[index] = step + 1
        prob = torch.sigmoid(halt)
        halt_prob[index] = prob
        done = (prob > 0.5) | (step + 1 == limit)
        if store is not None:
            top = store.top(scores, config.top_k)
            if step == 0:
                first_top = torch.where(top == store.null, torch.full_like(top, -1), top)
            model._insert(episode, store, index, top.masked_fill(((ask <= 0) | done).unsqueeze(1), -1))
        running[index[done]] = False
    tokens, lengths = model._greedy(batch, episode, mentions, stop)
    return Answers(tokens, lengths, used, first_top, episode.fetched, halt_prob)


def label_free(batch: VisitBatch) -> VisitBatch:
    """LEGACY design/06 §9.1 rule, on encoded batches: the reader stream without any answer or feedback span.

    Names bound from those spans stay bound (name table and entity numbering): use the label-free v2 cache
    for village data. Kept for the toy task and as the "before" of the milestone-1 leakage comparison.

    On every question line the tokens after "[answer]" are dropped except the line's last token (its
    newline), so the line reads "[question] ... [answer]\\n". Answers stay only as decoder targets. Token
    positions (tokens, line_of, card_end, lm_mask, line_start, q_span, lengths) are rebuilt; lm_mask also
    drops the "[answer]" -> newline transition. Every question line must be one of the batch's questions.
    """
    visits, width = batch.tokens.shape
    device = batch.tokens.device
    lines = batch.line_start.shape[1]
    starts = batch.line_start
    following = torch.cat([starts[:, 1:], torch.full_like(starts[:, :1], -1)], dim=1)
    ends = torch.where(following >= 0, following, batch.lengths.unsqueeze(1).expand(-1, lines))
    line_end = ends[batch.q_visit, batch.q_line]                     # [Q] first token after the line
    answer_at = batch.q_span[:, 1] - 1                               # [Q] the "[answer]" token
    asked = torch.zeros(visits, lines, dtype=torch.bool, device=device)
    asked[batch.q_visit, batch.q_line] = True
    if bool((batch.line_is_question & ~asked).any()):
        raise ValueError("label_free needs every question line of the batch among its questions")
    position = torch.arange(width, device=device)
    dropped = (position > answer_at.unsqueeze(1)) & (position < (line_end - 1).unsqueeze(1))
    drop = torch.zeros(visits, width, dtype=torch.long, device=device).index_add_(0, batch.q_visit, dropped.long()) > 0
    keep = (batch.line_of >= 0) & ~drop
    new_pos = keep.long().cumsum(1) - 1
    sizes = keep.sum(1)
    size = max(int(sizes.max()), 1)
    row = torch.arange(visits, device=device).unsqueeze(1).expand(-1, width)[keep]
    column = new_pos[keep]

    def moved(value: torch.Tensor, fill: Any) -> torch.Tensor:
        out = torch.full((visits, size), fill, dtype=value.dtype, device=device)
        out[row, column] = value[keep]
        return out

    lm_mask = moved(batch.lm_mask, False)
    lm_mask[batch.q_visit, new_pos[batch.q_visit, answer_at]] = False
    lm_mask &= torch.arange(size, device=device).unsqueeze(0) < (sizes - 1).unsqueeze(1)
    line_start = torch.where(starts >= 0, new_pos.gather(1, starts.clamp_min(0)), starts)
    q_start = new_pos[batch.q_visit, batch.q_span[:, 0]]
    return VisitBatch(
        tokens=moved(batch.tokens, PAD_ID), line_of=moved(batch.line_of, -1), card_end=moved(batch.card_end, False),
        lengths=sizes, lm_mask=lm_mask, line_is_question=batch.line_is_question, line_start=line_start,
        line_ents=batch.line_ents, q_visit=batch.q_visit, q_line=batch.q_line,
        q_span=torch.stack([q_start, new_pos[batch.q_visit, answer_at] + 1], dim=1),
        answer=batch.answer, gold_lines=batch.gold_lines, depth=batch.depth,
        question_ids=list(batch.question_ids), names=list(batch.names), slices=batch.slices)


def entity_text(ids: Iterable[int], table: Any, tokenizer: Any) -> str:
    """`pointer.answer_text`, except that an entity id the name table does not hold is written "<entK>" (it
    matches no answer) instead of raising (design/06 §9.12; `preprocess.prediction_text`)."""
    return preprocess.prediction_text(ids, table, tokenizer)[0]


def _strip(ids: Sequence[int], stop: set[int]) -> list[int]:
    out = []
    for token in ids:
        if token == IGNORE_INDEX:
            continue
        if token in stop:
            break
        out.append(int(token))
    return out


def judge(answers: Answers, batch: VisitBatch, *, tokenizer: Any = None, stop: Optional[Iterable[int]] = None,
          eos: int = 2) -> tuple[list[bool], list[str]]:
    """(exact match per question, prediction text). With a tokenizer: the prediction through
    `preprocess.prediction_text` (an unbound entity is a wrong answer) and the target through the strict
    `preprocess.target_text` (a malformed target raises MalformedTarget, never scores as wrong), compared by
    `step1.exact_match` (step 1's scoring); without: the ids up to the first stop id."""
    stops = set(stop) if stop is not None else {eos}
    predicted = answers.ids()
    gold = batch.answer.cpu().tolist()
    correct, texts = [], []
    for q, ids in enumerate(predicted):
        if tokenizer is None:
            mine, target = _strip(ids, stops), _strip(gold[q], stops | {eos})
            correct.append(bool(target) and mine == target)
            texts.append(" ".join(map(str, mine)))
            continue
        table = batch.names[int(batch.q_visit[q])]
        said = entity_text(ids, table, tokenizer)
        expected = preprocess.target_text([t for t in gold[q] if t != IGNORE_INDEX], table, tokenizer)
        correct.append(step1.exact_match(said, expected))
        texts.append(said)
    return correct, texts


def _eligible_cards(batch: VisitBatch) -> torch.Tensor:
    """[Q] cards a question may fetch at its first ASK (earlier non-question lines), NULL not counted."""
    card = (~batch.line_is_question) & (batch.line_start >= 0)
    before = torch.arange(card.shape[1], device=card.device).unsqueeze(0) < batch.q_line.unsqueeze(1)
    return (card[batch.q_visit] & before).sum(1)


@torch.no_grad()
def validate(model: PremonitionMini, batches: Iterable[VisitBatch], *, tokenizer: Any = None,
             stop: Optional[Iterable[int]] = None, gold_cards: bool = True,
             device: Optional[torch.device] = None) -> dict[str, Any]:
    """Own-retrieval and gold-card accuracy with retrieval, halting, loop and card diagnostics."""
    config = model.config
    device = device or next(model.parameters()).device
    stop = None if stop is None else sorted(set(stop))
    total: dict[str, Any] = {}
    cards: dict[str, Any] = {}
    slices: dict[str, list[int]] = {}
    depths: dict[str, list[float]] = {}
    started = time.perf_counter()
    for batch in batches:
        batch = batch.to(device)
        count = batch.q_visit.shape[0]
        if count == 0:
            continue
        recorder = InsertLog(model) if config.store else None
        with recorder or nullcontext():
            answers = model.answer(batch, stop=stop)
        correct, _ = judge(answers, batch, tokenizer=tokenizer, stop=stop, eos=config.eos_id)
        hit = torch.tensor(correct)
        _add(total, {"questions": count, "correct": int(hit.sum()), "loops": int(answers.loops.sum()),
                     "halted": int((answers.halt_prob > 0.5).sum())})
        if gold_cards and config.store:
            teacher = answer_with_gold(model, batch, stop=stop)
            forced, _ = judge(teacher, batch, tokenizer=tokenizer, stop=stop, eos=config.eos_id)
            _add(total, {"correct_gold_cards": sum(forced), "loops_gold_cards": int(teacher.loops.sum())})
        told = (batch.gold_lines >= 0).any(1).cpu()
        if config.store:
            _add(cards, card_stats(recorder.calls, batch, answers.loops, config.card_rows, offset=1))
            top = answers.first_top.cpu()
            gold = batch.gold_lines.cpu()
            size = (gold >= 0).sum(1).clamp_min(1)
            hits = ((top.unsqueeze(2) == gold.unsqueeze(1)) & (top.unsqueeze(2) >= 0)).any(1).sum(1)
            eligible = _eligible_cards(batch).cpu()
            chance = (config.top_k / (eligible + 1).float()).clamp(max=1.0)
            _add(total, {"told": int(told.sum()), "recall_sum": float((hits / size)[told].sum()),
                         "recall_any": int((hits > 0)[told].sum()), "recall_random_sum": float(chance[told].sum()),
                         "asked": int(answers.fetched[:, :-1].any(1).sum())})
        for name, tag in (batch.slices or {}).items():
            tag = tag.cpu()
            entry = slices.setdefault(name, [0, 0])
            entry[0] += int(hit[tag].sum())
            entry[1] += int(tag.sum())
        for q, depth in enumerate(batch.depth.cpu().tolist()):
            entry = depths.setdefault(str(depth), [0, 0, 0])
            entry[0] += int(correct[q])
            entry[1] += 1
            entry[2] += int(answers.loops[q])
    n = max(total.get("questions", 0), 1)
    out: dict[str, Any] = {
        "questions": total.get("questions", 0),
        "accuracy": total.get("correct", 0) / n,
        "loops_mean": total.get("loops", 0) / n,
        "halt_rate": total.get("halted", 0) / n,
        "by_depth": {d: {"n": v[1], "accuracy": v[0] / v[1], "loops_mean": v[2] / v[1]} for d, v in sorted(depths.items())},
        "slices": {name: {"n": v[1], "accuracy": v[0] / v[1] if v[1] else None} for name, v in sorted(slices.items())},
        "seconds": time.perf_counter() - started,
    }
    if gold_cards and config.store:
        out["accuracy_gold_cards"] = total.get("correct_gold_cards", 0) / n
        out["own_minus_gold_cards"] = out["accuracy"] - out["accuracy_gold_cards"]
        out["loops_mean_gold_cards"] = total.get("loops_gold_cards", 0) / n
    if config.store:
        told = max(total.get("told", 0), 1)
        out.update(gold_recall_at_4=total.get("recall_sum", 0.0) / told if total.get("told") else None,
                   gold_any_at_4=total.get("recall_any", 0) / told if total.get("told") else None,
                   random_recall_at_4=total.get("recall_random_sum", 0.0) / told if total.get("told") else None,
                   asked_rate=total.get("asked", 0) / n, cards=summarize_cards(cards) if cards else None)
    return out


def validation_hook(batches: Sequence[VisitBatch], **options: Any) -> Callable[[nn.Module], dict[str, Any]]:
    """An `evaluate` callback for `MiniTrainer.train` (it runs under `read_only`)."""
    return lambda model: validate(model, batches, **options)


# ----------------------------------------------------------------------------- checkpoints
def mini_config_dict(config: MiniConfig) -> dict[str, Any]:
    return asdict(config)


def mini_config_from(values: Mapping[str, Any]) -> MiniConfig:
    settings = dict(values)
    for name in ("reader", "distractors"):
        if name in settings:
            settings[name] = tuple(settings[name])
    return MiniConfig(**settings)


def checkpoint_config(trainer: MiniTrainer, *, contender: str, tokenizer: Optional[Mapping[str, Any]] = None,
                      detector: Optional[str] = None, data: Optional[Mapping[str, Any]] = None,
                      extra: Optional[Mapping[str, Any]] = None,
                      preprocess_identity: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """The JSON config a Premonition-mini checkpoint carries (enough to rebuild and audit the run).

    `preprocess_identity` is the identity of the visits it trained on (`preprocess.identity("label-free")`
    for village runs); without one the checkpoint is legacy/unknown and never scores a primary report.
    """
    return {
        "format": FORMAT, "format_version": FORMAT_VERSION, "contender": contender,
        "preprocess": None if preprocess_identity is None else dict(preprocess_identity),
        "mini": mini_config_dict(trainer.model.config), "parameters": trainer.model.num_parameters(),
        "train": asdict(trainer.config), "curriculum": asdict(trainer.curriculum), "seed": trainer.seed,
        "flops": {"budget": trainer.flop_budget, "spent": trainer.flops, "tolerance": trainer.tolerance,
                  "fit": None if trainer.fit is None else {"a": trainer.fit.a, "b": trainer.fit.b,
                                                           "worst_residual": trainer.fit.worst}},
        "tokenizer": dict(tokenizer or {}), "detector": {"sha256": detector}, "data": dict(data or {}),
        **dict(extra or {}),
    }


def save_mini_checkpoint(budget: Any, relative: Union[str, Path], trainer: MiniTrainer, config: Mapping[str, Any]
                         ) -> Path:
    """`learnlab.ckpt.save_checkpoint` with the optimizer and MiniTrainer state (never overwrites)."""
    return save_checkpoint(budget, relative, model=trainer.model, config=dict(config),
                           optimizer=trainer.optimizer, trainer_state=trainer.state_dict())


def load_mini(path: Union[str, Path], device: Union[str, torch.device] = "cpu", *,
              trainer_config: Optional[TrainConfig] = None) -> tuple[PremonitionMini, dict[str, Any], dict[str, Any]]:
    """(model in eval mode, checkpoint config, trainer state) from a Premonition-mini checkpoint; RNG untouched."""
    config = read_config(path)
    if config.get("format") != FORMAT:
        raise ValueError(f"{path} is not a {FORMAT} (format {config.get('format')!r})")
    model = PremonitionMini(mini_config_from(config["mini"]))
    loaded = load_checkpoint(path, model, map_location=device, restore_rng=False)
    return model.to(device).eval(), config, loaded["trainer"]


def resume_trainer(path: Union[str, Path], device: Union[str, torch.device] = "cpu") -> MiniTrainer:
    """A MiniTrainer restored with model, optimizer, trainer state and FLOP fit, ready to continue."""
    config = read_config(path)
    model = PremonitionMini(mini_config_from(config["mini"]))
    trainer_config = TrainConfig(**config["train"])
    fit = config["flops"]["fit"]
    trainer = MiniTrainer(model, trainer_config, device, flop_budget=config["flops"]["budget"],
                          curriculum=Curriculum(**config["curriculum"]), tolerance=config["flops"]["tolerance"],
                          seed=config["seed"], fit=None if fit is None else FlopFit(fit["a"], fit["b"],
                                                                                    fit["worst_residual"]))
    loaded = load_checkpoint(path, trainer.model, optimizer=trainer.optimizer, map_location=device,
                             restore_rng=True)
    trainer.load_state_dict(loaded["trainer"])
    return trainer


# ----------------------------------------------------------------------------- Experiment 1 scoring for D
def window_lines(items: Sequence[Any], cache: pdata.VisitCache) -> dict[str, int]:
    """Question id -> the within-visit line where A's window starts (`slices.window_start`), for wipes."""
    from premonition.slices import window_start
    position = {qid: i for i, qid in enumerate(cache.question_ids)}
    out = {}
    for item in items:
        q = item.question
        local = int(cache.q_line[position[q.id]])
        out[q.id] = window_start(item) - (q.line - local)
    return out


def d_scorer(cache: pdata.VisitCache, *, wipe: Optional[str] = None, max_tokens: int = 16_384,
             device: Union[str, torch.device] = "cpu", diagnostics: Optional[dict[str, Any]] = None,
             labels: Optional[bool] = None, regime: Optional[str] = None) -> Callable[..., list[dict[str, Any]]]:
    """A `scorer` for `exp1.evaluate_directory`: D's answers for the items, as `step1.score_items` rows.

    D reads each question's whole visit from `cache` (the directory's pointerized cache) up to its
    "[answer]". Label-free (§9.1, §11) unless `regime` / `labels` ask for the reported, never gated
    "with-labels" variant; the cache must be of that regime (a label-free run needs the v2 label-free
    cache, whose streams are audited here; the legacy v1 cache is the with-labels one). With `wipe`, A's
    window defines the wipe line. Exact match is step 1's; answerable plan questions whose world is known
    also count any plan the oracle accepts. `diagnostics` (a dict) receives recall, loop, halting and card
    statistics, the targets flagged unbound, and predictions naming an entity the table does not hold.
    """
    device = torch.device(device)
    regime = preprocess.regime_of(labels, regime)
    if cache.regime != regime:
        raise ValueError(f"a {regime} D evaluation needs a {regime} visit cache, not {cache.regime}")
    if regime != preprocess.WITH_LABELS:
        problems = preprocess.identity_problems(cache.preprocess_identity)
        if problems:
            raise ValueError("the visit cache: " + "; ".join(problems))

    def score(model: PremonitionMini, tokenizer: Any, items: Sequence[Any], *, max_new: int, batch_size: int,
              plans: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
        position = {qid: i for i, qid in enumerate(cache.question_ids)}
        wanted = {item.question.id for item in items}
        missing = wanted - position.keys()
        if missing:
            raise ValueError(f"{len(missing)} questions are not in the cache (e.g. {sorted(missing)[0]})")
        visits = sorted({v for v in range(len(cache)) for q in cache.questions_of(v)
                         if cache.question_ids[q] in wanted})
        windows = window_lines(items, cache) if wipe else {}
        lengths = cache.lengths.tolist()
        stops = sorted(step1.stop_ids(tokenizer)[0])
        predictions: dict[str, str] = {}
        stats: dict[str, Any] = {}
        cards: dict[str, Any] = {}
        groups = pdata.length_batches([lengths[v] for v in visits], max_tokens)
        for group in groups:
            batch = pdata.collate(cache, [visits[i] for i in group])
            if regime != preprocess.WITH_LABELS:
                for row in range(batch.size[0]):
                    preprocess.audit_stream(batch.tokens[row, :int(batch.lengths[row])].tolist(), tokenizer, regime)
            batch = batch.to(device)
            window = None
            if wipe:
                window = torch.tensor([windows.get(qid, 0) for qid in batch.question_ids], dtype=torch.long,
                                      device=device)
            recorder = InsertLog(model) if model.config.store and not wipe else None
            lesion = {} if not wipe else {"wipe": wipe, "window_line": window}
            with recorder or nullcontext():
                answers = model.answer(batch, stop=stops, **lesion)
            _, texts = judge(answers, batch, tokenizer=tokenizer, stop=stops)
            predictions.update(zip(batch.question_ids, texts))
            unbound = sum(preprocess.prediction_text(ids, batch.names[int(batch.q_visit[q])], tokenizer)[1]
                          for q, ids in enumerate(answers.ids()))
            _add(stats, {"questions": batch.q_visit.shape[0], "loops": int(answers.loops.sum()),
                         "halted": int((answers.halt_prob > 0.5).sum()), "unbound_predictions": unbound})
            if recorder is not None:
                _add(cards, card_stats(recorder.calls, batch, answers.loops, model.config.card_rows, offset=1))
        results = []
        for item in items:
            q = item.question
            prediction = predictions[q.id]
            exact = step1.exact_match(prediction, q.answer)
            plan = (plans or {}).get(q.id) if q.qtype == "Q12" else None
            results.append({
                "id": q.id, "split": q.split, "qtype": q.qtype, "depth": q.depth,
                "visible": q.visible, "knowable": q.knowable, "rule_families": list(q.rule_families),
                "heldout_family": item.heldout_family, "template": item.template,
                "style": q.style, "style_status": item.style_status, "name_answer": item.name_answer,
                "truncated": item.truncated, "evidence_kept": item.evidence_kept,
                "repeat_in_context": item.repeat_in_context, "changed_since_asked": item.changed_since_asked,
                "twin": q.twin, "answer": q.answer, "prediction": prediction,
                "exact": exact, "plan_checked": plan is not None,
                "correct": exact or (plan is not None and bool(prediction) and step1.plan_works(plan, prediction)),
            })
        if diagnostics is not None:
            n = max(stats.get("questions", 0), 1)
            flagged = 0
            if cache.target_unbound is not None:
                flagged = sum(bool(cache.target_unbound[position[qid]]) for qid in wanted)
            diagnostics.update(questions=stats.get("questions", 0), loops_mean=stats.get("loops", 0) / n,
                               halt_rate=stats.get("halted", 0) / n, regime=regime,
                               preprocess=cache.preprocess_identity, targets_unbound=flagged,
                               predictions_with_unbound_entity=stats.get("unbound_predictions", 0),
                               cards=summarize_cards(cards) if cards else None)
        return results

    return score


def d_checks(config: Mapping[str, Any], tokenizer: Any, model: PremonitionMini, detector_digest: Optional[str]
             ) -> list[str]:
    """`identity.checkpoint_problems` for a Premonition-mini checkpoint (see `premonition.identity`)."""
    mini = config.get("mini")
    problems: list[str] = []
    expected = None
    if mini is not None:
        full = MiniConfig.preset(config.get("contender", "D"), "full", vocab_size=int(mini["vocab_size"]),
                                 check_band=False)
        expected = {key: getattr(full, key) for key in ("d_model", "n_ent", "key_dim", "store", "pointers")}
    if model.config.pointers:
        recorded = (config.get("detector") or {}).get("sha256")
        if not recorded:
            problems.append("inputs: the checkpoint records no name detector digest")
        elif recorded != detector_digest:
            problems.append(f"inputs: name detector {str(detector_digest)[:12]} differs from the checkpoint's "
                            f"{recorded[:12]}")
    return problems + identity.checkpoint_problems(
        config, tokenizer, model_vocab=None if mini is None else int(mini["vocab_size"]), entity_ids=False,
        expected_shape=expected, shape=mini, reader="visit")


def evaluate_d_checkpoint(budget: Any, checkpoint: Union[str, Path], *, split: str = "validation",
                          wipe: Optional[str] = None, directories: Optional[Sequence[str]] = None,
                          data_rel: Optional[str] = None, tokenizer_path: Optional[str] = None,
                          device: str = "cpu", max_tokens: int = 16_384, replay: bool = True, workers: int = 1,
                          names: Optional[Iterable[str]] = None, regime: str = preprocess.LABEL_FREE,
                          purpose: Optional[str] = None, log: Log = print) -> dict[str, Any]:
    """Score a D / D-noask / D-noptr checkpoint like `exp1.evaluate_checkpoint` scores a Core one.

    Same report shape (so `exp1.verdict` pairs it with the others), plus "retrieval" diagnostics per
    directory. Label-free by default: the visit caches are the v2 label-free caches of
    `premonition.data.load_or_build` (built once through the budget); "with-labels" reads the legacy v1
    cache and is a diagnostic. The checkpoint must pass `premonition.identity`'s checks for `purpose`
    (tokenizer digest even with an override path, vocabulary, configuration, name detector, and a recorded
    label-free preprocessing identity) before anything is scored.
    """
    from learnlab.ckpt import read_config
    from premonition import exp1, slices
    preprocess.check_regime(regime)
    if regime == preprocess.GOLD_EVIDENCE:
        raise ValueError("gold-evidence D (D-gold) is built by the solvability diagnostic, not here")
    purpose = exp1.default_purpose(regime, purpose)
    root = Path(budget.root)
    path = Path(checkpoint) if Path(checkpoint).is_absolute() else root / checkpoint
    config = read_config(path)
    if config.get("format") != FORMAT:
        raise identity.CheckpointIncompatible(f"{path} is not a {FORMAT} (format {config.get('format')!r})")
    tokenizer_info = config.get("tokenizer") or {}
    if tokenizer_path is None and not tokenizer_info.get("path"):
        raise identity.CheckpointIncompatible(f"{checkpoint} records no tokenizer path; pass tokenizer_path")
    data = exp1.open_data(root, data_rel or config["data"]["dir"], tokenizer_path or tokenizer_info["path"])
    mini = mini_config_from(config["mini"]) if config.get("mini") else None
    detector = None
    if mini is not None and mini.pointers:
        detector = pdata.name_detector(budget, data.rel, workers=workers, log=log)
    probe = PremonitionMini(mini) if mini is not None else None
    if probe is None:
        raise identity.CheckpointIncompatible(f"{checkpoint} records no model configuration")
    problems = identity.admit(d_checks(config, data.tokenizer, probe, None if detector is None else detector.digest),
                              data.tokenizer, regime=regime, purpose=purpose)
    model, config, _ = load_mini(path, device)
    if directories is None:
        directories = [split] + ([slices.long_name(split)] if data.has(slices.long_name(split)) else [])
    cache_regime = None if regime == preprocess.WITH_LABELS else regime     # with labels: the legacy v1 cache
    reports: dict[str, Any] = {}
    items: dict[str, list[dict[str, Any]]] = {}
    fresh: list[Mapping[str, Any]] = []
    for directory in directories:
        cache = pdata.load_or_build(budget, data.rel, directory, data.tokenizer, detector, workers=workers,
                                    regime=cache_regime, log=log)
        diagnostics: dict[str, Any] = {}
        scorer = d_scorer(cache, wipe=wipe, max_tokens=max_tokens, device=device, diagnostics=diagnostics,
                          regime=regime)
        rows, info = exp1.evaluate_directory(model, data, directory, replay=replay, workers=workers,
                                             names=None if names is None else list(names), scorer=scorer,
                                             regime=regime, log=log)
        info["retrieval"] = diagnostics
        reports[directory] = info
        items[directory] = [{key: row[key] for key in exp1._ITEM_KEYS} for row in rows]
        if directory == split:
            fresh = [r for r in rows if "fresh_names" in r["slices"]]
        cell = info["summary"]["decision_cells"]
        log(f"premonition exp1 {config['contender']}{' W-' + wipe if wipe else ''} [{regime}] {directory}: "
            + ", ".join(f"{name} {exp1._pct(cell[name])}" for name in slices.DECISION_SLICES))
    return {
        "command": "premonition eval", "experiment": 1, "contender": config["contender"], "wipe": wipe,
        "regime": regime,
        "identity": identity.report_identity(
            regime=regime, purpose=purpose, tokenizer=data.tokenizer, tokenizer_path=data.tokenizer_path,
            model_kind="premonition-mini", model_config=config.get("mini") or {},
            parameters=model.num_parameters(), checkpoint=path, checkpoint_config=config, data_tag=data.tag,
            problems=problems),
        "checkpoint": str(checkpoint), "parameters": model.num_parameters(), "device": device,
        "config": config, "data": {"dir": data.rel, "tag": data.tag},
        "tokenizer": {"path": data.tokenizer_path, "sha256": data.tokenizer.digest},
        "cut": {"seq_len": slices.SEQ_LEN, "max_new": slices.MAX_NEW, "max_len": slices.CUT_MAX_LEN},
        "split": split, "directories": reports, "name_gap": {"fresh_names": exp1._cell(fresh)}, "items": items,
    }


# ----------------------------------------------------------------------------- runs
def format_record(record: Mapping[str, Any]) -> str:
    """One log line."""
    if "eval" in record:
        e = record["eval"]
        parts = [f"eval step {record['step']} ({record['flops_share']:.1%} of F): acc {e['accuracy']:.1%}"]
        if e.get("accuracy_gold_cards") is not None:
            parts.append(f"gold-cards {e['accuracy_gold_cards']:.1%}")
        if e.get("gold_recall_at_4") is not None:
            parts.append(f"recall@4 {e['gold_recall_at_4']:.1%} (random {e['random_recall_at_4']:.1%})")
        parts.append(f"loops {e['loops_mean']:.2f} halt {e['halt_rate']:.0%}")
        return ", ".join(parts)

    def num(name: str, spec: str = ".3f") -> str:
        value = record.get(name)
        return "-" if value is None else format(value, spec)

    return (f"step {record['step']} {record['phase']} p_own {record['p_own']:.2f} F {record['flops_share']:.1%}: "
            f"loss {num('loss')} (lm {num('lm')} ask {num('ask')} ans {num('ans')} halt {num('halt')}) "
            f"recall@4 {num('gold_recall_at_4', '.2f')} acc {num('answer_acc', '.2f')} "
            f"loops {num('loops_per_question', '.2f')} halt {num('halt_rate', '.2f')} "
            f"{record['tokens_per_s']:,.0f} tok/s")


def train_toy(variant: str = "D", *, spec: Any = None, steps: int = 200, visits: int = 16, seed: int = 0,
              eval_batches: int = 4, lr: float = 3e-3, warmup_steps: int = 20, log_every: int = 25,
              eval_every: int = 0, max_seconds: Optional[float] = None, config_overrides: Optional[dict] = None,
              on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
    """Build step 4: train D (or a control) at the tiny preset on the far-fact toy under the curriculum.

    The FLOP budget is `steps` batches' worth (`budget_for_steps`); the report holds the training report,
    the validation of a fixed held-out toy set and chance.
    """
    from premonition.toy import ToySpec, toy_set, toy_stream
    spec = spec or ToySpec()
    torch.manual_seed(seed)
    settings = dict(window=64)
    settings.update(config_overrides or {})
    model = PremonitionMini(MiniConfig.preset(variant, "tiny", vocab_size=spec.vocab_size, **settings))
    trainer = MiniTrainer(model, mini_train_config(lr=lr, warmup_steps=warmup_steps, log_every=log_every,
                                                   eval_every=eval_every), "cpu", flop_budget=1.0, seed=seed)
    stream = (label_free(b) for b in toy_stream(spec, visits, seed))
    head = [next(stream) for _ in range(2)]
    trainer.calibrate(head)
    trainer.flop_budget = budget_for_steps(trainer, head, steps)
    held_out = [label_free(b) for b in toy_set(spec, eval_batches, visits, seed + 1000)]
    report = trainer.train(itertools.chain(head, stream), max_seconds=max_seconds, on_log=on_log,
                           evaluate=validation_hook(held_out) if eval_every else None)
    result = trainer.evaluate(validation_hook(held_out))
    return {"variant": variant, "spec": asdict(spec), "chance": spec.chance, "parameters": model.num_parameters(),
            "train": report, "validation": result, "history": trainer.history, "trainer": trainer}


def _slice_tags_for(data: Any, directory: str, cache: pdata.VisitCache, visits: Sequence[int]
                    ) -> Optional[dict[str, torch.Tensor]]:
    """near / far / multi_hop / overall bool tags (A's cut) for the questions of `visits`, or None."""
    from premonition import exp1, slices
    wanted = {cache.question_ids[q] for v in visits for q in cache.questions_of(v)}
    questions = [q for q in exp1.split_questions(data, directory) if q.id in wanted]
    _, tags = slices.tag_questions(data.tokenizer, questions, seen=data.seen, source=directory)
    sets: dict[str, set[str]] = {}
    for qid, tag in tags.items():
        for name in tag.slices():
            if name in slices.DECISION_SLICES or name == "not_told":
                sets.setdefault(name, set()).add(qid)
    return cache.tags(sets)


def train_d(budget: Any, *, data_rel: str, tokenizer_path: str, flop_budget: float, variant: str = "D",
            size: str = "full", device: str = "cpu", seed: int = 0, max_tokens: int = 55_000,
            max_visits: Optional[int] = 48, lr: float = 1e-3, warmup_steps: int = 100, log_every: int = 50,
            eval_every: int = 1000, eval_visits: int = 256, calibration_batches: int = 4,
            max_seconds: Optional[float] = None, checkpoint: Optional[str] = None, workers: int = 1,
            log: Log = print) -> dict[str, Any]:
    """Train D (or D-noask / D-noptr) on a step-1 village build for `flop_budget` FLOPs (design/06 §3-4).

    `data_rel` is the data build (e.g. data/village/large-seed0-...), `tokenizer_path` the v2 tokenizer
    (relative to the budget root). Caches and the name detector are built once through the budget. The
    validation hook scores `eval_visits` validation visits every `eval_every` steps; with `checkpoint`
    (a relative path) the final model is saved through `learnlab.ckpt`. Returns a JSON-able report.
    """
    from learnlab.tokenizer import Tokenizer
    from premonition import exp1
    root = Path(budget.root)
    tokenizer = Tokenizer.load(root / tokenizer_path)
    detector = None if variant == "D-noptr" else pdata.name_detector(budget, data_rel, workers=workers, log=log)
    train_cache = pdata.load_or_build(budget, data_rel, "train", tokenizer, detector, workers=workers,
                                      regime=preprocess.LABEL_FREE, log=log)
    valid_cache = pdata.load_or_build(budget, data_rel, "validation", tokenizer, detector, workers=workers,
                                      regime=preprocess.LABEL_FREE, log=log)
    torch.manual_seed(seed)
    config = MiniConfig.preset(variant, size, vocab_size=tokenizer.vocab_size)
    model = PremonitionMini(config)
    trainer = MiniTrainer(model, mini_train_config(lr=lr, warmup_steps=warmup_steps, log_every=log_every,
                                                   eval_every=eval_every), device, flop_budget=flop_budget,
                          seed=seed)
    stream = pdata.batches(train_cache, max_tokens, seed=seed, epochs=None, max_visits=max_visits)   # label-free
    head = [next(stream) for _ in range(calibration_batches)]
    fit = trainer.calibrate(head)
    log(f"premonition train {variant}: {model.num_parameters():,} params, F = {flop_budget:.3e}; FLOP fit "
        f"a = {fit.a:.4g}/token, b = {fit.b:.4g}/(question x loop), worst residual {fit.worst:.1%}")
    chosen = list(range(min(eval_visits, len(valid_cache))))
    tags = None
    try:
        data = exp1.open_data(root, data_rel, tokenizer_path)
        tags = _slice_tags_for(data, "validation", valid_cache, chosen)
    except (FileNotFoundError, KeyError, ValueError) as error:
        log(f"premonition train: validation slices unavailable ({error}); reporting overall accuracy only")
    groups = pdata.length_batches(valid_cache.lengths[chosen].tolist(), max_tokens, max_visits=max_visits)
    eval_batches = [pdata.collate(valid_cache, [chosen[i] for i in g], slices=tags) for g in groups]
    stops = sorted(step1.stop_ids(tokenizer)[0])
    hook = validation_hook(eval_batches, tokenizer=tokenizer, stop=stops)
    report: dict[str, Any] = {"command": "premonition train", "contender": variant, "parameters": model.num_parameters(),
                              "device": device, "seed": seed, "data": {"dir": data_rel, "tag": Path(data_rel).name},
                              "tokenizer": {"path": tokenizer_path, "sha256": tokenizer.digest},
                              "detector": None if detector is None else detector.digest,
                              "preprocess": preprocess.identity(preprocess.LABEL_FREE)}
    try:
        report.update(status="completed", **trainer.train(itertools.chain(head, stream), max_seconds=max_seconds,
                                                           evaluate=hook, on_log=lambda r: log(format_record(r))))
    except MemoryGuardError as error:
        report.update(status="aborted", error=str(error), peak_gpu_reserved_bytes=error.peak)
    report["validation"] = trainer.evaluate(hook)
    log(format_record({"step": trainer.step, "flops_share": trainer.flops / flop_budget, "eval": report["validation"]}))
    report["history"] = trainer.history
    if checkpoint:
        ckpt_config = checkpoint_config(trainer, contender=variant,
                                        tokenizer={"path": tokenizer_path, "sha256": tokenizer.digest},
                                        detector=None if detector is None else detector.digest,
                                        data={"dir": data_rel, "tag": Path(data_rel).name},
                                        preprocess_identity=preprocess.identity(preprocess.LABEL_FREE))
        report["checkpoint"] = str(save_mini_checkpoint(budget, checkpoint, trainer, ckpt_config))
    return report


# ----------------------------------------------------------------------------- CPU smoke
def smoke(*, work_dir: Optional[Union[str, Path]] = None, train_visits: int = 60, heldout_visits: int = 24,
          steps: int = 120, max_seconds: float = 150.0, seed: int = 0, max_tokens: int = 12_000,
          log_every: int = 10, log: Log = print) -> dict[str, Any]:
    """design/06 §7 CPU smoke for D: a tiny village build in a temporary directory, the tiny preset (d = 32)
    through the whole curriculum on a small FLOP budget, then checks (the report's "checks", all True to pass):
    L_lm and L_ans fall, own gold recall@4 on the held-out visits beats random fetching, `answer()` answers
    every question, validation passes `read_only`, the exp1-style report has every decision slice, and a
    checkpoint round trip gives the same answers."""
    from learnlab.readonly import read_only
    from learnlab.tokenizer import Tokenizer
    from learnlab.village.names import SYLLABLES
    from learnlab.village.shards import write_shards
    from memorylab.storage import Budget
    from premonition import exp1, slices
    started = time.perf_counter()
    holder = None
    if work_dir is None:
        holder = tempfile.TemporaryDirectory(prefix="premonition-smoke-")
        work_dir = holder.name
    root = Path(work_dir)
    try:
        for split, count in (("train", train_visits), ("validation", heldout_visits)):
            write_shards(split, count, root / "d", 1, seed=seed, visits_per_shard=16, verbose=False)
        texts = [text.read_text(encoding="utf-8") for text, _ in step1.shard_files(root / "d" / "train")]
        tokenizer = Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES)
        detector = pdata.fit_detector(root / "d" / "train")
        train_cache = pdata.build_cache(root / "d" / "train", tokenizer, detector, regime=preprocess.LABEL_FREE)
        valid_cache = pdata.build_cache(root / "d" / "validation", tokenizer, detector, regime=preprocess.LABEL_FREE)
        built = time.perf_counter() - started
        torch.manual_seed(seed)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=tokenizer.vocab_size))
        trainer = MiniTrainer(model, mini_train_config(lr=3e-3, warmup_steps=10, log_every=log_every),
                              "cpu", flop_budget=1.0, seed=seed)
        stream = pdata.batches(train_cache, max_tokens, seed=seed, epochs=None)          # label-free v2 cache
        head = [next(stream) for _ in range(2)]
        trainer.calibrate(head)
        trainer.flop_budget = budget_for_steps(trainer, head, steps)
        valid = list(pdata.batches(valid_cache, max_tokens))
        stops = sorted(step1.stop_ids(tokenizer)[0])
        before = trainer.evaluate(validation_hook(valid, tokenizer=tokenizer, stop=stops))
        report = trainer.train(itertools.chain(head, stream), max_seconds=max_seconds,
                               on_log=lambda r: log(format_record(r)))
        after = trainer.evaluate(validation_hook(valid, tokenizer=tokenizer, stop=stops))
        log(format_record({"step": trainer.step, "flops_share": trainer.flops / trainer.flop_budget, "eval": after}))
        logged = [r for r in trainer.history if "eval" not in r and r.get("lm") is not None]
        first, last = logged[0], logged[-1]
        # exp1-style D report on the held-out visits (tags from the shards; this build has no oracle index).
        data = exp1.EvalData(root=root / "d", rel="d", tokenizer=tokenizer, tokenizer_path="(smoke)",
                             seen={"templates": set(), "styles": set(), "rule_families": set()})
        diagnostics: dict[str, Any] = {}
        rows, info = exp1.evaluate_directory(model, data, "validation", replay=False,
                                             scorer=d_scorer(valid_cache, diagnostics=diagnostics), log=log)
        answers = model.answer(valid[0], stop=stops)
        # A checkpoint round trip through learnlab.ckpt.
        budget = Budget(root, hard=10_000_000_000, steady=8_000_000_000)
        config = checkpoint_config(trainer, contender="D", tokenizer={"path": "(smoke)", "sha256": tokenizer.digest},
                                   detector=detector.digest, data={"dir": "d", "tag": "smoke"},
                                   preprocess_identity=preprocess.identity(preprocess.LABEL_FREE))
        save_mini_checkpoint(budget, "ckpt/smoke-D", trainer, config)
        loaded, loaded_config, _ = load_mini(root / "ckpt" / "smoke-D")
        with read_only(loaded):
            again = loaded.answer(valid[0], stop=stops)
        checks = {
            "lm_falls": last["lm"] < first["lm"],
            "ans_falls": last["ans"] < first["ans"],
            "recall_beats_random": (after["gold_recall_at_4"] or 0.0) > (after["random_recall_at_4"] or 1.0),
            "answer_works": tuple(answers.tokens.shape) == (valid[0].size[2], model.config.max_answer)
                            and bool((answers.lengths > 0).all()),
            "read_only_holds": True,        # every evaluation above ran under read_only without a violation
            "report_has_every_slice": set(slices.DECISION_SLICES) <= set(info["summary"]["decision_cells"]),
            "budget_ok": report["budget_ok"],
            "checkpoint_round_trip": torch.equal(again.tokens, answers.tokens)
                                     and loaded_config["tokenizer"]["sha256"] == tokenizer.digest,
        }
        return {
            "passed": all(checks.values()), "checks": checks, "seconds": time.perf_counter() - started,
            "build_seconds": built, "parameters": model.num_parameters(),
            "visits": {"train": len(train_cache), "validation": len(valid_cache)},
            "questions": {"train": len(train_cache.question_ids), "validation": len(valid_cache.question_ids)},
            "train": report, "before": before, "after": after,
            "first_log": {k: first[k] for k in ("step", "lm", "ans", "ask", "halt", "gold_recall_at_4")},
            "last_log": {k: last[k] for k in ("step", "lm", "ans", "ask", "halt", "gold_recall_at_4")},
            "exp1": {"decision_cells": info["summary"]["decision_cells"], "retrieval": diagnostics},
        }
    finally:
        if holder is not None:
            holder.cleanup()


__all__ = [
    "Curriculum", "InsertLog", "MiniTrainer", "Plan", "answer_with_gold", "budget_for_steps", "card_stats",
    "checkpoint_config", "d_checks", "d_scorer", "entity_text", "evaluate_d_checkpoint", "format_record", "judge",
    "label_free",
    "load_mini",
    "mini_config_from", "mini_train_config", "planned_loops", "resume_trainer", "save_mini_checkpoint", "smoke",
    "summarize_cards", "train_d", "train_toy", "validate", "validation_hook",
]
