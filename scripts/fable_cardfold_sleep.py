#!/usr/bin/env python3
"""One-thread CPU experiment: awake log -> symbolic lesson -> sleep practice -> closed-book exam."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F

# Runtime/model budgets.  Four 160-wide layers are ~1.24M parameters; 1200 base
# updates plus 3*300 sleep updates are intended to stay under 20 min on one laptop
# CPU thread.  Selftest performs only one update.
DEFAULT_SEED = 4101
MODEL_LAYERS = 4
D_MODEL = 160
N_HEADS = 4
D_FF = 640
DROPOUT = 0.0
MAX_POSITIONS = 256
POSITION_OFFSET_MAX = 192
BASE_UPDATES = 12000
SLEEP_UPDATES = 3000
BATCH_SIZE = 48
BASE_LR = 2.0e-3
SLEEP_LR = 1.0e-3
WEIGHT_DECAY = 1.0e-2
GRAD_CLIP = 1.0
EVAL_BATCH_SIZE = 256
REGRESSION_PER_OP = 200
AWAKE_COUNT = 20
PRACTICE_COUNT = 400
TEST_FRESH_COUNT = 200
TEST_LONG_COUNT = 200
TRAIN_LENGTHS = (4, 5, 6, 7, 8)
LONG_LENGTHS = (9, 10)
SELFTEST_BATCH_SIZE = 12
SELFTEST_UPDATES = 1
SELFTEST_LR = 1.0e-3

M1_S_FRESH_MIN = 0.80
M2_S_MINUS_R_MIN = 0.20
M3_S_LONG_MIN = 0.50
M4_MAX_REGRESSION_DROP = 0.03
M5_BASE_REGRESSION_MIN = 0.95
PASS_CLAIM = (
    "A PASS supports only: a software-compiled lesson can be trained into a tiny "
    "model's weights on this toy; the abstraction step was done by program search, "
    "not by the model."
)

# Program tuples are applied left-to-right.  Thus CARDFOLD is
# INC3(FOLD(ROTL1(x))).  PRIMITIVE_NAMES is also the fixed induction tie order;
# this order makes CARDFOLD the canonical first representative among variants that
# only commute INC3 through those position permutations.
PRIMITIVE_NAMES = (
    "ROTL1", "FOLD", "INC3", "REV", "ROTL2", "INC1", "SWAP", "MIRROR_EVEN",
)
CARDFOLD = ("ROTL1", "FOLD", "INC3")
OLD_PROGRAMS = (
    ("OP0", ("REV",)),
    ("OP1", ("ROTL1",)),
    ("OP2", ("INC3",)),
    ("OP3", ("SWAP",)),
    ("OP4", ("FOLD",)),
    ("OP5", ("REV", "INC1")),
)
OLD_OP_NAMES = tuple(name for name, _ in OLD_PROGRAMS)
CARDFOLD_OP = "CARDFOLD"

# pad, eos, "=", ten digit tokens, six old op tokens, one reserved CardFold token.
PAD_ID, EOS_ID, EQ_ID = 0, 1, 2
DIGIT_ID_BASE = 3
OP_ID_BASE = 13
CARDFOLD_ID = 19
VOCAB_SIZE = 20
Program = tuple[str, ...]


@dataclass(frozen=True)
class Example:
    op: str
    inp: str
    out: str


@dataclass(frozen=True)
class Splits:
    regression: tuple[tuple[str, tuple[Example, ...]], ...]
    awake: tuple[Example, ...]
    practice_inputs: tuple[str, ...]
    test_fresh: tuple[Example, ...]
    test_long: tuple[Example, ...]

    def reserved_short_inputs(self) -> frozenset[str]:
        values: set[str] = set()
        for _, rows in self.regression:
            values.update(ex.inp for ex in rows)
        values.update(ex.inp for ex in self.awake)
        values.update(self.practice_inputs)
        values.update(ex.inp for ex in self.test_fresh)
        return frozenset(values)


@dataclass(frozen=True)
class InductionResult:
    program: Program | None
    consistent_count: int
    verified: bool


class ExperimentError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Deterministic RNGs
# ---------------------------------------------------------------------------

def derive_seed(namespace: str, seed: int) -> int:
    payload = f"{namespace}\\0{seed}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def make_rng(namespace: str, seed: int) -> random.Random:
    return random.Random(derive_seed(namespace, seed))


def make_model(seed: int, namespace: str) -> "TinyDecoder":
    # Module initialization internally consumes PyTorch's CPU generator.  fork_rng
    # restores outside state; all init draws therefore come from this SHA256 seed.
    torch_seed = derive_seed(namespace, seed) & ((1 << 63) - 1)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(torch_seed)
        model = TinyDecoder()
    return model


# ---------------------------------------------------------------------------
# DSL
# ---------------------------------------------------------------------------

def rev(s: str) -> str:
    return s[::-1]


def rotl1(s: str) -> str:
    return s[1:] + s[:1] if s else s


def rotl2(s: str) -> str:
    if not s:
        return s
    k = 2 % len(s)
    return s[k:] + s[:k]


def inc_digits(s: str, amount: int) -> str:
    return "".join(str((int(ch) + amount) % 10) for ch in s)


def swap_adjacent(s: str) -> str:
    chars = list(s)
    for i in range(0, len(chars) - 1, 2):
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)


def fold(s: str) -> str:
    """Interleave first half with reversed second half; odd middle char is last."""
    half = len(s) // 2
    if len(s) % 2 == 0:
        left, right = s[:half], s[half:][::-1]
        return "".join(a + b for a, b in zip(left, right))
    left, middle, right = s[:half], s[half], s[half + 1 :][::-1]
    return "".join(a + b for a, b in zip(left, right)) + middle


def mirror_even(s: str) -> str:
    """Reverse the subsequence at zero-based even positions 0,2,4,... only."""
    chars = list(s)
    positions = list(range(0, len(chars), 2))
    values = [chars[i] for i in positions][::-1]
    for i, value in zip(positions, values):
        chars[i] = value
    return "".join(chars)


def apply_primitive(name: str, s: str) -> str:
    if name == "REV":
        return rev(s)
    if name == "ROTL1":
        return rotl1(s)
    if name == "ROTL2":
        return rotl2(s)
    if name == "INC1":
        return inc_digits(s, 1)
    if name == "INC3":
        return inc_digits(s, 3)
    if name == "SWAP":
        return swap_adjacent(s)
    if name == "FOLD":
        return fold(s)
    if name == "MIRROR_EVEN":
        return mirror_even(s)
    raise ValueError(f"unknown primitive {name!r}")


def apply_program(program: Program, s: str) -> str:
    value = s
    for primitive in program:
        value = apply_primitive(primitive, value)
    return value


def enumerate_programs(max_depth: int = 3) -> Iterable[Program]:
    for depth in range(1, max_depth + 1):
        yield from itertools.product(PRIMITIVE_NAMES, repeat=depth)


def induce_lesson(log: Sequence[Example]) -> InductionResult:
    consistent: list[Program] = []
    for program in enumerate_programs(3):
        if all(apply_program(program, ex.inp) == ex.out for ex in log):
            consistent.append(program)
    chosen = consistent[0] if consistent else None
    verified = chosen is not None and all(
        apply_program(chosen, ex.inp) == ex.out for ex in log
    )
    return InductionResult(chosen, len(consistent), verified)


def corrupt_one_episode(
    log: Sequence[Example],
) -> tuple[tuple[Example, ...], InductionResult]:
    # Keep the corruption length-preserving and search deterministically for one
    # contradictory digit.  Usually the first candidate already rules out all 584.
    for ex_i, ex in enumerate(log):
        for pos, old in enumerate(ex.out):
            for delta in range(1, 10):
                repl = str((int(old) + delta) % 10)
                bad = ex.out[:pos] + repl + ex.out[pos + 1 :]
                changed = list(log)
                changed[ex_i] = Example(ex.op, ex.inp, bad)
                result = induce_lesson(changed)
                if result.program is None:
                    return tuple(changed), result
    raise AssertionError("could not make one corrupted episode DSL-inconsistent")


# ---------------------------------------------------------------------------
# Split construction
# ---------------------------------------------------------------------------

def random_digit_string(rng: random.Random, length: int) -> str:
    return "".join(str(rng.randrange(10)) for _ in range(length))


def generate_unique_inputs(
    rng: random.Random,
    count: int,
    lengths: Sequence[int],
    forbidden: set[str] | frozenset[str],
) -> tuple[str, ...]:
    used = set(forbidden)
    output: list[str] = []
    while len(output) < count:
        length = lengths[rng.randrange(len(lengths))]
        value = random_digit_string(rng, length)
        if value not in used:
            used.add(value)
            output.append(value)
    return tuple(output)


def examples_for_program(
    op: str, program: Program, inputs: Sequence[str],
) -> tuple[Example, ...]:
    return tuple(Example(op, x, apply_program(program, x)) for x in inputs)


def build_splits(seed: int) -> Splits:
    # Closed-book tests are generated first, in their own namespaces, before model
    # creation/training.  All named splits are input-disjoint.
    used_short: set[str] = set()
    regression: list[tuple[str, tuple[Example, ...]]] = []
    for op, program in OLD_PROGRAMS:
        rng = make_rng(f"test/regression/{op}", seed)
        inputs = generate_unique_inputs(rng, REGRESSION_PER_OP, TRAIN_LENGTHS, used_short)
        used_short.update(inputs)
        regression.append((op, examples_for_program(op, program, inputs)))

    fresh_rng = make_rng("test/cardfold-fresh", seed)
    fresh_inputs = generate_unique_inputs(
        fresh_rng, TEST_FRESH_COUNT, TRAIN_LENGTHS, used_short
    )
    used_short.update(fresh_inputs)
    test_fresh = examples_for_program(CARDFOLD_OP, CARDFOLD, fresh_inputs)

    long_rng = make_rng("test/cardfold-long", seed)
    long_inputs = generate_unique_inputs(long_rng, TEST_LONG_COUNT, LONG_LENGTHS, set())
    test_long = examples_for_program(CARDFOLD_OP, CARDFOLD, long_inputs)

    awake_rng = make_rng("awake/log", seed)
    awake_inputs = generate_unique_inputs(awake_rng, AWAKE_COUNT, TRAIN_LENGTHS, used_short)
    used_short.update(awake_inputs)
    awake = examples_for_program(CARDFOLD_OP, CARDFOLD, awake_inputs)

    practice_rng = make_rng("sleep/practice-inputs", seed)
    practice_inputs = generate_unique_inputs(
        practice_rng, PRACTICE_COUNT, TRAIN_LENGTHS, used_short
    )
    return Splits(tuple(regression), awake, practice_inputs, test_fresh, test_long)


def assert_split_disjointness(splits: Splits) -> None:
    regression_inputs: set[str] = set()
    for _, rows in splits.regression:
        values = [ex.inp for ex in rows]
        assert len(values) == len(set(values))
        regression_inputs.update(values)
    groups = {
        "regression": regression_inputs,
        "awake": {ex.inp for ex in splits.awake},
        "practice": set(splits.practice_inputs),
        "test_fresh": {ex.inp for ex in splits.test_fresh},
        "test_long": {ex.inp for ex in splits.test_long},
    }
    expected = {
        "awake": AWAKE_COUNT,
        "practice": PRACTICE_COUNT,
        "test_fresh": TEST_FRESH_COUNT,
        "test_long": TEST_LONG_COUNT,
    }
    for name, count in expected.items():
        assert len(groups[name]) == count
    names = tuple(groups)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            assert not (groups[left] & groups[right]), f"{left}/{right} overlap"


def op_token_id(op: str) -> int:
    if op == CARDFOLD_OP:
        return CARDFOLD_ID
    for i, name in enumerate(OLD_OP_NAMES):
        if op == name:
            return OP_ID_BASE + i
    raise ValueError(f"unknown op {op!r}")


def digit_token_id(ch: str) -> int:
    if not ("0" <= ch <= "9"):
        raise ValueError(f"not a digit: {ch!r}")
    return DIGIT_ID_BASE + int(ch)


def encode_example(ex: Example) -> tuple[list[int], int]:
    # Logical format: "<op-token> input = output <eos>".
    tokens = [op_token_id(ex.op)]
    tokens.extend(digit_token_id(ch) for ch in ex.inp)
    tokens.append(EQ_ID)
    output_start = len(tokens)
    tokens.extend(digit_token_id(ch) for ch in ex.out)
    tokens.append(EOS_ID)
    return tokens, output_start


def sample_train_input(rng: random.Random, forbidden: frozenset[str]) -> str:
    while True:
        length = TRAIN_LENGTHS[rng.randrange(len(TRAIN_LENGTHS))]
        value = random_digit_string(rng, length)
        if value not in forbidden:
            return value


def base_step_examples(seed: int, step: int, splits: Splits) -> tuple[Example, ...]:
    if BATCH_SIZE % len(OLD_PROGRAMS):
        raise ExperimentError("BATCH_SIZE must be divisible by six")
    rng = make_rng(f"base/data/{step}", seed)
    forbidden = splits.reserved_short_inputs()
    rows: list[Example] = []
    for op, program in OLD_PROGRAMS:
        for _ in range(BATCH_SIZE // len(OLD_PROGRAMS)):
            x = sample_train_input(rng, forbidden)
            rows.append(Example(op, x, apply_program(program, x)))
    rng.shuffle(rows)
    return tuple(rows)


def replay_half(seed: int, step: int, splits: Splits) -> tuple[Example, ...]:
    half = BATCH_SIZE // 2
    if half % len(OLD_PROGRAMS):
        raise ExperimentError("half BATCH_SIZE must be divisible by six")
    rng = make_rng(f"sleep/replay/{step}", seed)
    forbidden = splits.reserved_short_inputs()
    rows: list[Example] = []
    for op, program in OLD_PROGRAMS:
        for _ in range(half // len(OLD_PROGRAMS)):
            x = sample_train_input(rng, forbidden)
            rows.append(Example(op, x, apply_program(program, x)))
    rng.shuffle(rows)
    return tuple(rows)


def sample_pool(
    pool: Sequence[Example], count: int, rng: random.Random,
) -> tuple[Example, ...]:
    return tuple(pool[rng.randrange(len(pool))] for _ in range(count))


def sleep_step_examples(
    arm: str,
    seed: int,
    step: int,
    splits: Splits,
    practice: Sequence[Example],
) -> tuple[Example, ...]:
    half = BATCH_SIZE // 2
    if arm == "S":
        rng = make_rng(f"sleep/new/S/{step}", seed)
        return sample_pool(practice, half, rng) + replay_half(seed, step, splits)
    if arm == "R":
        rng = make_rng(f"sleep/new/R/{step}", seed)
        return sample_pool(splits.awake, half, rng) + replay_half(seed, step, splits)
    if arm == "S0":
        rng = make_rng(f"sleep/new/S0/{step}", seed)
        return sample_pool(practice, BATCH_SIZE, rng)
    raise ValueError(f"unknown arm {arm!r}")


# ---------------------------------------------------------------------------
# Decoder-only causal transformer
# ---------------------------------------------------------------------------

def make_sinusoidal_table(max_positions: int, width: int) -> Tensor:
    positions = torch.arange(max_positions, dtype=torch.float32).unsqueeze(1)
    dims = torch.arange(0, width, 2, dtype=torch.float32)
    scales = torch.exp(-math.log(10000.0) * dims / width)
    angles = positions * scales.unsqueeze(0)
    table = torch.zeros(max_positions, width)
    table[:, 0::2] = torch.sin(angles)
    table[:, 1::2] = torch.cos(angles)
    return table


class TinyDecoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.token_embedding = nn.Embedding(VOCAB_SIZE, D_MODEL, padding_idx=PAD_ID)
        block = nn.TransformerEncoderLayer(
            d_model=D_MODEL,
            nhead=N_HEADS,
            dim_feedforward=D_FF,
            dropout=DROPOUT,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.blocks = nn.TransformerEncoder(block, num_layers=MODEL_LAYERS)
        self.final_norm = nn.LayerNorm(D_MODEL)
        self.output = nn.Linear(D_MODEL, VOCAB_SIZE)
        self.register_buffer(
            "position_table",
            make_sinusoidal_table(MAX_POSITIONS, D_MODEL),
            persistent=False,
        )

    def forward(
        self,
        tokens: Tensor,
        offsets: Tensor,
        padding_mask: Tensor | None = None,
    ) -> Tensor:
        batch, steps = tokens.shape
        if offsets.shape != (batch,):
            raise ValueError("offsets must have shape [batch]")
        relative = torch.arange(steps, device=tokens.device).unsqueeze(0)
        positions = offsets.unsqueeze(1) + relative
        if int(positions.max()) >= MAX_POSITIONS:
            raise ValueError("position exceeds MAX_POSITIONS")
        # Fixed sinusoids plus random training offsets reduce reliance on absolute
        # token positions and are the standard trick used for length generalization.
        hidden = self.token_embedding(tokens) + self.position_table[positions]
        causal = torch.triu(
            torch.ones(steps, steps, dtype=torch.bool, device=tokens.device), diagonal=1
        )
        hidden = self.blocks(hidden, mask=causal, src_key_padding_mask=padding_mask)
        return self.output(self.final_norm(hidden))


def parameter_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def collate(
    examples: Sequence[Example],
    rng: random.Random,
    random_offsets: bool = True,
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    encoded = [encode_example(ex) for ex in examples]
    max_len = max(len(seq) for seq, _ in encoded)
    tokens = torch.full((len(examples), max_len), PAD_ID, dtype=torch.long)
    supervised = torch.zeros((len(examples), max_len), dtype=torch.bool)
    padding = torch.ones((len(examples), max_len), dtype=torch.bool)
    offsets = torch.zeros(len(examples), dtype=torch.long)
    for row, (seq, output_start) in enumerate(encoded):
        n = len(seq)
        tokens[row, :n] = torch.tensor(seq)
        padding[row, :n] = False
        # Loss is only on output-side tokens; EOS is included as the terminator.
        supervised[row, output_start:n] = True
        if random_offsets:
            offsets[row] = rng.randrange(POSITION_OFFSET_MAX + 1)
    return tokens, supervised, padding, offsets


def masked_loss(
    model: TinyDecoder,
    batch: tuple[Tensor, Tensor, Tensor, Tensor],
) -> Tensor:
    tokens, supervised, padding, offsets = batch
    logits = model(tokens[:, :-1], offsets, padding[:, :-1])
    targets = tokens[:, 1:]
    mask = supervised[:, 1:]
    losses = F.cross_entropy(
        logits.reshape(-1, VOCAB_SIZE),
        targets.reshape(-1),
        reduction="none",
    ).reshape_as(targets)
    if not bool(mask.any()):
        raise ExperimentError("no supervised output tokens")
    return losses[mask].mean()


def make_optimizer(model: TinyDecoder, lr: float) -> torch.optim.Optimizer:
    return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)


def train_step(
    model: TinyDecoder,
    optimizer: torch.optim.Optimizer,
    batch: tuple[Tensor, Tensor, Tensor, Tensor],
) -> float:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    loss = masked_loss(model, batch)
    loss.backward()
    nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
    optimizer.step()
    return float(loss.detach())


def train_base(model: TinyDecoder, splits: Splits, seed: int) -> dict[str, float]:
    optimizer = make_optimizer(model, BASE_LR)
    losses: list[float] = []
    for step in range(BASE_UPDATES):
        rows = base_step_examples(seed, step, splits)
        rng = make_rng(f"base/positions/{step}", seed)
        losses.append(train_step(model, optimizer, collate(rows, rng)))
    tail = losses[-50:]
    return {
        "first_loss": losses[0],
        "last_loss": losses[-1],
        "tail_mean_loss": sum(tail) / len(tail),
    }


def train_arm(
    base_model: TinyDecoder,
    arm: str,
    splits: Splits,
    practice: Sequence[Example],
    seed: int,
) -> tuple[TinyDecoder, dict[str, float]]:
    model = copy.deepcopy(base_model)
    optimizer = make_optimizer(model, SLEEP_LR)
    losses: list[float] = []
    for step in range(SLEEP_UPDATES):
        rows = sleep_step_examples(arm, seed, step, splits, practice)
        # S/R share the exact replay examples and exact replay position offsets.
        ns = (
            f"sleep/positions/shared/{step}"
            if arm in ("S", "R")
            else f"sleep/positions/S0/{step}"
        )
        losses.append(train_step(model, optimizer, collate(rows, make_rng(ns, seed))))
    tail = losses[-50:]
    return model, {
        "first_loss": losses[0],
        "last_loss": losses[-1],
        "tail_mean_loss": sum(tail) / len(tail),
    }


# ---------------------------------------------------------------------------
# Closed-book greedy exact-match scoring
# ---------------------------------------------------------------------------

def greedy_correct_batch(model: TinyDecoder, examples: Sequence[Example]) -> list[bool]:
    if not examples:
        return []
    n = len(examples[0].inp)
    if any(len(ex.inp) != n or len(ex.out) != n for ex in examples):
        raise ValueError("evaluation batch must contain one length-preserving length")
    prompts, targets = [], []
    for ex in examples:
        prompt = [op_token_id(ex.op)]
        prompt.extend(digit_token_id(ch) for ch in ex.inp)
        prompt.append(EQ_ID)
        prompts.append(prompt)
        targets.append([digit_token_id(ch) for ch in ex.out] + [EOS_ID])
    generated = torch.tensor(prompts, dtype=torch.long)
    expected = torch.tensor(targets, dtype=torch.long)
    offsets = torch.zeros(len(examples), dtype=torch.long)
    predictions: list[Tensor] = []
    model.eval()
    with torch.inference_mode():
        for _ in range(n + 1):
            next_token = model(generated, offsets)[:, -1].argmax(dim=-1)
            predictions.append(next_token)
            generated = torch.cat((generated, next_token[:, None]), dim=1)
    predicted = torch.stack(predictions, dim=1)
    return [bool(x) for x in (predicted == expected).all(dim=1).tolist()]


def exact_flags(model: TinyDecoder, examples: Sequence[Example]) -> list[bool]:
    flags = [False] * len(examples)
    groups: dict[int, list[tuple[int, Example]]] = {}
    for i, ex in enumerate(examples):
        groups.setdefault(len(ex.inp), []).append((i, ex))
    for length in sorted(groups):
        group = groups[length]
        for start in range(0, len(group), EVAL_BATCH_SIZE):
            chunk = group[start : start + EVAL_BATCH_SIZE]
            found = greedy_correct_batch(model, [ex for _, ex in chunk])
            for (index, _), flag in zip(chunk, found):
                flags[index] = flag
    return flags


def score(model: TinyDecoder, examples: Sequence[Example]) -> float:
    flags = exact_flags(model, examples)
    return sum(flags) / len(flags)


def score_regression(model: TinyDecoder, splits: Splits) -> tuple[dict[str, float], float]:
    rows: list[Example] = []
    owners: list[str] = []
    for op, examples in splits.regression:
        rows.extend(examples)
        owners.extend([op] * len(examples))
    flags = exact_flags(model, rows)
    good = {op: 0 for op in OLD_OP_NAMES}
    total = {op: 0 for op in OLD_OP_NAMES}
    for op, flag in zip(owners, flags):
        good[op] += int(flag)
        total[op] += 1
    by_op = {op: good[op] / total[op] for op in OLD_OP_NAMES}
    return by_op, sum(by_op.values()) / len(by_op)


def evaluate_arm(
    model: TinyDecoder, splits: Splits, base_mean: float,
) -> dict[str, object]:
    by_op, regression_mean = score_regression(model, splits)
    return {
        "test_fresh": score(model, splits.test_fresh),
        "test_long": score(model, splits.test_long),
        "awake": score(model, splits.awake),
        "regression_by_op": by_op,
        "regression_mean": regression_mean,
        "regression_drop": max(0.0, base_mean - regression_mean),
    }


# ---------------------------------------------------------------------------
# Persistence/reporting
# ---------------------------------------------------------------------------

def constants_record() -> dict[str, object]:
    return {
        "model_layers": MODEL_LAYERS,
        "d_model": D_MODEL,
        "n_heads": N_HEADS,
        "d_ff": D_FF,
        "dropout": DROPOUT,
        "max_positions": MAX_POSITIONS,
        "position_offset_max": POSITION_OFFSET_MAX,
        "base_updates": BASE_UPDATES,
        "sleep_updates": SLEEP_UPDATES,
        "batch_size": BATCH_SIZE,
        "base_lr": BASE_LR,
        "sleep_lr": SLEEP_LR,
        "weight_decay": WEIGHT_DECAY,
        "grad_clip": GRAD_CLIP,
        "regression_per_op": REGRESSION_PER_OP,
        "awake_count": AWAKE_COUNT,
        "practice_count": PRACTICE_COUNT,
        "test_fresh_count": TEST_FRESH_COUNT,
        "test_long_count": TEST_LONG_COUNT,
        "train_lengths": list(TRAIN_LENGTHS),
        "long_lengths": list(LONG_LENGTHS),
        "M1": M1_S_FRESH_MIN,
        "M2": M2_S_MINUS_R_MIN,
        "M3": M3_S_LONG_MIN,
        "M4": M4_MAX_REGRESSION_DROP,
        "M5": M5_BASE_REGRESSION_MIN,
        "selftest_updates": SELFTEST_UPDATES,
    }


def judge(base_mean: float, arms: dict[str, dict[str, object]]) -> tuple[dict[str, bool], str]:
    s, r = arms["S"], arms["R"]
    marks = {
        "M1": float(s["test_fresh"]) >= M1_S_FRESH_MIN,
        "M2": float(s["test_fresh"]) - float(r["test_fresh"]) >= M2_S_MINUS_R_MIN,
        "M3": float(s["test_long"]) >= M3_S_LONG_MIN,
        "M4": float(s["regression_drop"]) < M4_MAX_REGRESSION_DROP,
        "M5": base_mean >= M5_BASE_REGRESSION_MIN,
    }
    if not marks["M5"]:
        return marks, "VOID"
    return marks, "PASS" if all(marks.values()) else "FAIL"


def script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def save_base(model: TinyDecoder, seed: int, out: Path) -> None:
    torch.save(
        {
            "seed": seed,
            "state": model.state_dict(),
            "shape": (MODEL_LAYERS, D_MODEL, N_HEADS, D_FF, VOCAB_SIZE),
        },
        out / "base.pt",
    )


def load_base(seed: int, out: Path) -> TinyDecoder:
    path = out / "base.pt"
    if not path.exists():
        raise ExperimentError(f"missing {path}; run --stage base or --stage all first")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if int(payload["seed"]) != seed:
        raise ExperimentError(f"base.pt seed {payload['seed']} != requested seed {seed}")
    expected = (MODEL_LAYERS, D_MODEL, N_HEADS, D_FF, VOCAB_SIZE)
    if tuple(payload["shape"]) != expected:
        raise ExperimentError("base.pt architecture does not match this script")
    model = make_model(seed, "model/load")
    model.load_state_dict(payload["state"], strict=True)
    return model


def format_program(program: Program | None) -> str:
    return "NONE" if program is None else " -> ".join(program)


def build_report(r: dict[str, object]) -> str:
    lines = [
        "fable_cardfold_sleep",
        f"seed: {r['seed']}",
        f"stage: {r['stage']}",
        f"model parameters: {r['model_parameters']}",
        f"budgets: base={BASE_UPDATES}, sleep={SLEEP_UPDATES}/arm, batch={BATCH_SIZE}",
        "",
    ]
    if r.get("selftest"):
        d = r["selftest_details"]
        lines += [
            "SELFTEST: PASS",
            f"one-step loss: {d['loss_before']:.6f} -> {d['loss_after']:.6f}",
            f"induced lesson: {d['induced_program']} (consistent={d['consistent_count']})",
            f"corrupted-log consistent programs: {d['corrupt_count']}",
            "",
            PASS_CLAIM,
        ]
        return "\n".join(lines) + "\n"

    base = r["base"]
    lines.append("BASE REGRESSION")
    for op in OLD_OP_NAMES:
        lines.append(f"  {op}: {float(base['regression_by_op'][op]):.4f}")
    lines += [f"  mean: {float(base['regression_mean']):.4f}", ""]

    if isinstance(r.get("induction"), dict):
        d = r["induction"]
        lines += [
            "LESSON INDUCTION",
            f"  selected: {d['selected']}",
            f"  consistent programs: {d['consistent_count']}",
            f"  verified: {d['verified']}",
            f"  corrupted-log consistent programs: {d['corrupted_consistent_count']}",
            "",
        ]

    arms = r.get("arms", {})
    if arms:
        lines.append("ARM  TEST-FRESH  TEST-LONG  AWAKE  REGRESSION  REG-DROP")
        for arm in ("S", "R", "S0"):
            x = arms[arm]
            lines.append(
                f"{arm:<3}  {float(x['test_fresh']):>10.4f}  "
                f"{float(x['test_long']):>9.4f}  {float(x['awake']):>5.4f}  "
                f"{float(x['regression_mean']):>10.4f}  "
                f"{float(x['regression_drop']):>8.4f}"
            )
        lines.append("")

    marks = r.get("pass_marks", {})
    if all(key in marks for key in ("M1", "M2", "M3", "M4", "M5")):
        delta = float(arms["S"]["test_fresh"]) - float(arms["R"]["test_fresh"])
        lines += [
            "PASS MARKS",
            f"  M1 S TEST-FRESH >= 0.80: {marks['M1']}",
            f"  M2 S-R TEST-FRESH >= 0.20: {marks['M2']} (delta={delta:.4f})",
            f"  M3 S TEST-LONG >= 0.50: {marks['M3']}",
            f"  M4 S regression drop < 0.03: {marks['M4']}",
            f"  M5 base regression >= 0.95: {marks['M5']}",
            "",
        ]
    lines += [f"VERDICT: {r['verdict']}", "", PASS_CLAIM]
    return "\n".join(lines) + "\n"


def write_results(r: dict[str, object], out: Path) -> None:
    (out / "results.json").write_text(
        json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "report.txt").write_text(build_report(r), encoding="utf-8")


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def primitive_selftest() -> None:
    assert rev("1234") == "4321"
    assert rotl1("1234") == "2341"
    assert rotl2("12345") == "34512"
    assert inc_digits("908", 1) == "019"
    assert inc_digits("789", 3) == "012"
    assert swap_adjacent("12345") == "21435"
    assert fold("123456") == "162534"
    assert fold("12345") == "15243"
    assert mirror_even("123456") == "523416"
    assert apply_program(CARDFOLD, "12345") == "54687"


def lesson_selftest(splits: Splits) -> tuple[InductionResult, InductionResult]:
    for program in enumerate_programs(2):
        assert any(apply_program(program, ex.inp) != ex.out for ex in splits.awake)
    result = induce_lesson(splits.awake)
    assert result.program == CARDFOLD, (result.program, result.consistent_count)
    assert result.verified
    _, corrupt = corrupt_one_episode(splits.awake)
    assert corrupt.program is None and corrupt.consistent_count == 0
    return result, corrupt


def one_step_selftest(seed: int) -> tuple[float, float]:
    model = make_model(seed, "selftest/model")
    optimizer = torch.optim.AdamW(model.parameters(), lr=SELFTEST_LR, weight_decay=0.0)
    rng = make_rng("selftest/examples", seed)
    rows: list[Example] = []
    for i in range(SELFTEST_BATCH_SIZE):
        op, program = OLD_PROGRAMS[i % len(OLD_PROGRAMS)]
        n = TRAIN_LENGTHS[rng.randrange(len(TRAIN_LENGTHS))]
        x = random_digit_string(rng, n)
        rows.append(Example(op, x, apply_program(program, x)))
    batch = collate(rows, make_rng("selftest/positions", seed))
    model.eval()
    with torch.no_grad():
        before = float(masked_loss(model, batch))
    train_step(model, optimizer, batch)
    model.eval()
    with torch.no_grad():
        after = float(masked_loss(model, batch))
    assert after < before, f"loss did not fall: {before} -> {after}"
    return before, after


def run_selftest(seed: int, out: Path) -> dict[str, object]:
    started = time.perf_counter()
    primitive_selftest()
    splits = build_splits(seed)
    assert_split_disjointness(splits)
    induction, corrupt = lesson_selftest(splits)
    before, after = one_step_selftest(seed)
    params = parameter_count(make_model(seed, "selftest/count"))
    assert 1_000_000 <= params <= 3_000_000 and MODEL_LAYERS == 4
    elapsed = time.perf_counter() - started
    assert elapsed < 60.0, f"selftest took {elapsed:.2f}s"
    r: dict[str, object] = {
        "seed": seed,
        "stage": "selftest",
        "selftest": True,
        "selftest_details": {
            "loss_before": before,
            "loss_after": after,
            "induced_program": format_program(induction.program),
            "consistent_count": induction.consistent_count,
            "corrupt_count": corrupt.consistent_count,
            "split_disjointness": True,
            "primitive_checks": True,
        },
        "model_parameters": params,
        "constants": constants_record(),
        "script_sha256": script_sha256(),
        "torch_version": torch.__version__,
        "wall_seconds": {"selftest": elapsed, "total": elapsed},
        "verdict": "SELFTEST_PASS",
    }
    write_results(r, out)
    return r


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def evaluate_base(
    model: TinyDecoder,
    splits: Splits,
    training: dict[str, float] | None,
) -> dict[str, object]:
    by_op, mean = score_regression(model, splits)
    return {"training": training, "regression_by_op": by_op, "regression_mean": mean}


def run_experiment(seed: int, out: Path, stage: str) -> dict[str, object]:
    total_started = time.perf_counter()
    split_started = time.perf_counter()
    splits = build_splits(seed)
    assert_split_disjointness(splits)
    timings: dict[str, float] = {
        "split_build": time.perf_counter() - split_started
    }
    params = parameter_count(make_model(seed, "model/count"))
    if not 1_000_000 <= params <= 3_000_000:
        raise ExperimentError(f"parameter count outside 1-3M: {params}")
    r: dict[str, object] = {
        "seed": seed,
        "stage": stage,
        "selftest": False,
        "model_parameters": params,
        "constants": constants_record(),
        "script_sha256": script_sha256(),
        "torch_version": torch.__version__,
        "split_sizes": {
            "regression_per_op": REGRESSION_PER_OP,
            "regression_total": REGRESSION_PER_OP * len(OLD_PROGRAMS),
            "awake": AWAKE_COUNT,
            "practice": PRACTICE_COUNT,
            "test_fresh": TEST_FRESH_COUNT,
            "test_long": TEST_LONG_COUNT,
        },
    }

    if stage in ("base", "all"):
        started = time.perf_counter()
        base_model = make_model(seed, "model/base")
        training = train_base(base_model, splits, seed)
        save_base(base_model, seed, out)
        r["base"] = evaluate_base(base_model, splits, training)
        timings["base"] = time.perf_counter() - started
    else:
        started = time.perf_counter()
        base_model = load_base(seed, out)
        r["base"] = evaluate_base(base_model, splits, None)
        timings["base_load_and_eval"] = time.perf_counter() - started

    base_mean = float(r["base"]["regression_mean"])
    if stage == "base":
        r["induction"] = None
        r["arms"] = {}
        r["pass_marks"] = {"M5": base_mean >= M5_BASE_REGRESSION_MIN}
        r["verdict"] = "BASE_VALID" if base_mean >= M5_BASE_REGRESSION_MIN else "BASE_VOID"
        timings["total"] = time.perf_counter() - total_started
        r["wall_seconds"] = timings
        write_results(r, out)
        return r

    sleep_started = time.perf_counter()
    induction = induce_lesson(splits.awake)
    if induction.program is None or not induction.verified:
        raise ExperimentError("awake log did not induce a verified lesson")
    _, corrupt = corrupt_one_episode(splits.awake)
    if corrupt.program is not None:
        raise ExperimentError("corrupted log unexpectedly induced a lesson")

    # Critically, S labels are generated from the induced lesson, not CARDFOLD.
    practice = examples_for_program(CARDFOLD_OP, induction.program, splits.practice_inputs)
    r["induction"] = {
        "selected": format_program(induction.program),
        "selected_primitives": list(induction.program),
        "consistent_count": induction.consistent_count,
        "verified": induction.verified,
        "corrupted_consistent_count": corrupt.consistent_count,
    }

    arms: dict[str, dict[str, object]] = {}
    arm_seconds: dict[str, float] = {}
    for arm in ("S", "R", "S0"):
        started = time.perf_counter()
        model, training = train_arm(base_model, arm, splits, practice, seed)
        metrics = evaluate_arm(model, splits, base_mean)
        metrics["training"] = training
        arms[arm] = metrics
        arm_seconds[arm] = time.perf_counter() - started
        del model
    r["arms"] = arms
    r["pass_marks"], r["verdict"] = judge(base_mean, arms)
    timings["sleep"] = time.perf_counter() - sleep_started
    timings.update({f"arm_{k}": v for k, v in arm_seconds.items()})
    timings["total"] = time.perf_counter() - total_started
    r["wall_seconds"] = timings
    write_results(r, out)
    return r


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CardFold sleep-as-compiler toy experiment")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stage", choices=("base", "sleep", "all"), default="all")
    parser.add_argument("--selftest", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.use_deterministic_algorithms(True)
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    if args.selftest:
        r = run_selftest(args.seed, out)
        d = r["selftest_details"]
        print(
            f"SELFTEST PASS | params={r['model_parameters']} | "
            f"loss={d['loss_before']:.4f}->{d['loss_after']:.4f} | "
            f"wall={r['wall_seconds']['total']:.2f}s"
        )
        return

    r = run_experiment(args.seed, out, args.stage)
    print(
        f"{r['verdict']} | base-reg={r['base']['regression_mean']:.4f} | "
        f"params={r['model_parameters']} | wall={r['wall_seconds']['total']:.1f}s"
    )
    if r["arms"]:
        s, raw = r["arms"]["S"], r["arms"]["R"]
        print(
            f"S fresh={s['test_fresh']:.4f} long={s['test_long']:.4f} "
            f"reg-drop={s['regression_drop']:.4f} | R fresh={raw['test_fresh']:.4f}"
        )


if __name__ == "__main__":
    main()
