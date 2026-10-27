#!/usr/bin/env python3
"""CPU toy for testing a checker-authoritative creative stopping controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


# Frozen design defaults.
ENTITY_COUNT = 12
BASE_RELATION_COUNT = 6
STEP_VARIANTS = 12
PAIR_COUNT = 144
HYPOTHESIS_COUNT = 156

DREAMS_PER_ROUND = 8
CHECKS_PER_ROUND = 2
MAX_ROUNDS = 12
MAX_CANDIDATES = 96
MAX_CHECKS = 24
NEAR_MISS_SCORE = 0.70
PASS_SCORE = 1.0
MIN_GIVEUP_ROUNDS = 2
STALL_MIN_NEW_CLUSTERS = 2
STALL_IMPROVEMENT = 0.05
STALLS_TO_STOP = 99
BETA_ALPHA = 1.0
BETA_BETA = 3.0
NEAR_MISS_PRIOR_WEIGHT = 0.5
EV_STOP_THRESHOLD = 0.0
VALUE_ROUND_COST_MULTIPLIER = 5.0

REFINE_MAX_LEADS = 2
REFINE_MAX_STEPS = 3
REFINE_MUTATIONS = 4
REFINE_MIN_IMPROVEMENT = 0.05

TEMPERATURE_LEVELS = (0.7, 1.0, 1.3, 1.6)
START_TEMPERATURE = 1.0
NARROW_NEXT_ROUND_FRACTION = 0.5
WIDEN_DUPLICATE_FRACTION = 0.5
BORING_SCORE = 0.3
INCOHERENT_FRACTION = 0.5

UNCHECKABLE_MAX_ROUNDS = 3
UNCHECKABLE_MAX_CANDIDATES = 24
PROPOSAL_TOP_K = 3

FILTER_EXAMPLE_COUNT = 12
FILTER_POSITIVE_EXAMPLES = 6
FILTER_KEEP_THRESHOLD = 0.85
FILTER_NOISE_AMPLITUDE = 0.12
FILTER_FOUND_THRESHOLD = 0.85
FILTER_PRECISION_FAULT_RATIO = 0.5
RESCUE_EVERY_N_CHECKS = 8
EMBEDDING_DUPLICATE_COSINE = 0.90

QUESTION_MAX_LINES = 8
CREATIVE_ASKS_PER_DAY = 2
REASK_UNANSWERED_DAYS = 7
MAX_BLOCKING_QUESTIONS = 3

TEST_SOLVABLE_ITEMS = 120
TEST_UNSOLVABLE_ITEMS = 60
DEV_TOTAL_ITEMS = 60
DEV_SOLVABLE_ITEMS = 40
DEV_UNSOLVABLE_ITEMS = 20
DEFAULT_SEEDS = (3101, 3102, 3103)
DEV_WORLD_SEED = 2026092101
TEST_WORLD_SEED = 2026092102
DEV_NAMESPACE = "fable-creative-stop/dev/v1"
TEST_NAMESPACE = "fable-creative-stop/test/v1"

PASS2_SOLVE_RATIO = 0.95
PASS3_COMPUTE_RATIO = 0.70
PASS4_MORE_SOLVED = 5
PASS4_COMPUTE_SAVINGS = 0.15
PASS5_GIVEUP_FRACTION = 0.80
PASS5_CAP_FRACTION = 0.60

BASE_RELATION_DENSITY = 0.14
# dev calibration 2: relations come in sibling families so neighbouring rules overlap
RELATION_FAMILY_SIZE = 2
SIBLING_KEEP_PROBABILITY = 0.85
SIBLING_ADD_DENSITY = 0.02
RANDOM_TARGET_DENSITY = 0.17
MAX_GENERATION_ATTEMPTS = 1000
LOCAL_SAMPLE_PROBABILITIES = (0.90, 0.75, 0.50, 0.25)
LOCAL_MUTATION_OPS = (1, 1, 2, 3)
DEPTH_MUTATION_PROBABILITY = 0.25
# dev calibration 3 (Ben, 21 Sep): dreamer and filter are one model, so fresh dreams
# are drawn in proportion to exp(sharpness * filter score / temperature), not uniformly
DREAM_GUIDE_SHARPNESS = 10.0
# dev calibration 4: good ideas that were not checked this round stay in a backlog
CARRY_UNCHECKED_SURVIVORS = True
# dev calibration 5: 'out of ideas I believe in' stop. Good-Turing estimate of the
# dream-probability still sitting on never-dreamed ideas the filter would keep:
# (kept ideas dreamed exactly once) / (all dreams). 0 disables the rule.
COVERAGE_STOP_UNSEEN_MASS = 0.10
COVERAGE_MIN_KEPT_DREAMS = 14
INVERSION_MUTATION_PROBABILITY = 0.35

TUNE_MIN_ROUNDS = 1
TUNE_MAX_ROUNDS = 11
SELFTEST_TINY_ITEMS = 12
SELFTEST_SEARCH_ATTEMPTS = 40
SELFTEST_SEED = 99173

FROZEN_FILENAME = "DEFAULTS-FROZEN.json"
RESULTS_PREFIX = "results-"
REPORT_PREFIX = "report-"


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Rule:
    steps: tuple[int, ...]

    def signature(self) -> str:
        parts: list[str] = []
        for step in self.steps:
            rel = step // 2 + 1
            inv = step % 2
            parts.append(f"r{rel}{'^-1' if inv else ''}")
        return " -> ".join(parts)


@dataclass(frozen=True)
class Item:
    uid: str
    target: frozenset[int]
    predictions: tuple[frozenset[int], ...]
    examples: tuple[tuple[int, bool], ...]
    solvable: bool
    solution_indices: tuple[int, ...]
    decoy_index: int
    goal: str


@dataclass
class Meter:
    candidate_cap: int = MAX_CANDIDATES
    checker_cap: int = MAX_CHECKS
    candidates: int = 0
    checker_calls: int = 0

    def dream(self, count: int = 1) -> None:
        if self.candidates + count > self.candidate_cap:
            raise BudgetExceeded("candidate cap exceeded")
        self.candidates += count

    def check(self, count: int = 1) -> None:
        if self.checker_calls + count > self.checker_cap:
            raise BudgetExceeded("checker cap exceeded")
        self.checker_calls += count

    @property
    def hard_cap_hit(self) -> bool:
        return (
            self.candidates >= self.candidate_cap
            or self.checker_calls >= self.checker_cap
        )

    def cap_fraction(self) -> float:
        return max(
            self.candidates / self.candidate_cap,
            self.checker_calls / self.checker_cap,
        )


def stable_seed(*parts: object) -> int:
    text = "\x1f".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(text).digest()
    return int.from_bytes(digest[:8], "big")


def build_hypotheses() -> tuple[Rule, ...]:
    rules = [Rule((step,)) for step in range(STEP_VARIANTS)]
    rules.extend(
        Rule((left, right))
        for left in range(STEP_VARIANTS)
        for right in range(STEP_VARIANTS)
    )
    assert len(rules) == HYPOTHESIS_COUNT
    return tuple(rules)


HYPOTHESES = build_hypotheses()
RULE_TO_INDEX = {rule.steps: i for i, rule in enumerate(HYPOTHESES)}


def invert_relation(pairs: frozenset[int]) -> frozenset[int]:
    return frozenset(
        (pair % ENTITY_COUNT) * ENTITY_COUNT + (pair // ENTITY_COUNT)
        for pair in pairs
    )


def compose_relations(
    left: frozenset[int], right: frozenset[int]
) -> frozenset[int]:
    right_by_source: list[list[int]] = [[] for _ in range(ENTITY_COUNT)]
    for pair in right:
        source, dest = divmod(pair, ENTITY_COUNT)
        right_by_source[source].append(dest)
    out: set[int] = set()
    for pair in left:
        source, middle = divmod(pair, ENTITY_COUNT)
        for dest in right_by_source[middle]:
            out.add(source * ENTITY_COUNT + dest)
    return frozenset(out)


def step_relations(
    base_relations: tuple[frozenset[int], ...]
) -> tuple[frozenset[int], ...]:
    steps: list[frozenset[int]] = []
    for relation in base_relations:
        steps.append(relation)
        steps.append(invert_relation(relation))
    return tuple(steps)


def evaluate_steps(
    steps: Sequence[int], step_sets: tuple[frozenset[int], ...]
) -> frozenset[int]:
    result = step_sets[steps[0]]
    for step in steps[1:]:
        result = compose_relations(result, step_sets[step])
    return result


def all_predictions(
    base_relations: tuple[frozenset[int], ...]
) -> tuple[frozenset[int], ...]:
    step_sets = step_relations(base_relations)
    return tuple(evaluate_steps(rule.steps, step_sets) for rule in HYPOTHESES)


def exact_jaccard(predicted: frozenset[int], target: frozenset[int]) -> float:
    union = predicted | target
    if not union:
        return PASS_SCORE
    return len(predicted & target) / len(union)


def make_world(rng: random.Random) -> tuple[frozenset[int], ...]:
    relations: list[frozenset[int]] = []
    while len(relations) < BASE_RELATION_COUNT:
        pairs = {
            pair
            for pair in range(PAIR_COUNT)
            if rng.random() < BASE_RELATION_DENSITY
        }
        if not pairs:
            pairs.add(rng.randrange(PAIR_COUNT))
        relations.append(frozenset(pairs))
        for _ in range(RELATION_FAMILY_SIZE - 1):
            if len(relations) >= BASE_RELATION_COUNT:
                break
            sibling = {
                pair for pair in pairs if rng.random() < SIBLING_KEEP_PROBABILITY
            }
            sibling |= {
                pair
                for pair in range(PAIR_COUNT)
                if rng.random() < SIBLING_ADD_DENSITY
            }
            if not sibling or sibling == pairs:
                sibling.symmetric_difference_update({rng.randrange(PAIR_COUNT)})
            if not sibling:
                sibling.add(rng.randrange(PAIR_COUNT))
            relations.append(frozenset(sibling))
    return tuple(relations)


def random_target(rng: random.Random) -> frozenset[int]:
    pairs = {
        pair
        for pair in range(PAIR_COUNT)
        if rng.random() < RANDOM_TARGET_DENSITY
    }
    if not pairs:
        pairs.add(rng.randrange(PAIR_COUNT))
    return frozenset(pairs)


def choose_planted_examples(
    rng: random.Random,
    target: frozenset[int],
    predictions: tuple[frozenset[int], ...],
    solution_indices: set[int],
) -> tuple[tuple[tuple[int, bool], ...], int] | None:
    candidates = [i for i in range(HYPOTHESIS_COUNT) if i not in solution_indices]
    rng.shuffle(candidates)
    for idx in candidates:
        predicted = predictions[idx]
        agreements = [
            pair
            for pair in range(PAIR_COUNT)
            if ((pair in predicted) == (pair in target))
        ]
        positives = [pair for pair in agreements if pair in target]
        negatives = [pair for pair in agreements if pair not in target]
        negative_count = FILTER_EXAMPLE_COUNT - FILTER_POSITIVE_EXAMPLES
        if len(positives) < FILTER_POSITIVE_EXAMPLES or len(negatives) < negative_count:
            continue
        chosen = rng.sample(positives, FILTER_POSITIVE_EXAMPLES) + rng.sample(
            negatives, negative_count
        )
        examples = tuple((pair, pair in target) for pair in chosen)
        return examples, idx
    return None


def generate_item(
    namespace: str,
    world_seed: int,
    index: int,
    solvable: bool,
) -> Item:
    item_seed = stable_seed(namespace, world_seed, index, "solvable" if solvable else "unsolvable")
    rng = random.Random(item_seed)

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        world = make_world(rng)
        predictions = all_predictions(world)
        step_sets = step_relations(world)

        if solvable:
            nonempty = [i for i, pred in enumerate(predictions) if pred]
            if not nonempty:
                continue
            source_idx = rng.choice(nonempty)
            target = predictions[source_idx]
        else:
            target = frozenset()
            if attempt % 2 == 0:
                three_steps = tuple(rng.randrange(STEP_VARIANTS) for _ in range(3))
                target = evaluate_steps(three_steps, step_sets)
            else:
                target = random_target(rng)
            if not target or target in predictions:
                continue

        solutions = {
            i for i, predicted in enumerate(predictions) if predicted == target
        }
        if solvable and not solutions:
            continue
        if not solvable and solutions:
            continue

        planted = choose_planted_examples(rng, target, predictions, solutions)
        if planted is None:
            continue
        examples, decoy_idx = planted

        uid = f"{namespace}:{index:03d}"
        goal = (
            "Find a 1- or 2-step rule whose predicted relation exactly equals "
            f"the hidden target on all {PAIR_COUNT} ordered entity pairs."
        )
        item = Item(
            uid=uid,
            target=target,
            predictions=predictions,
            examples=examples,
            solvable=solvable,
            solution_indices=tuple(sorted(solutions)),
            decoy_index=decoy_idx,
            goal=goal,
        )
        if not solvable:
            assert all(pred != target for pred in predictions)
        return item

    raise RuntimeError(f"could not generate item {namespace}:{index}")


def generate_suite(suite: str) -> list[Item]:
    if suite == "dev":
        namespace = DEV_NAMESPACE
        world_seed = DEV_WORLD_SEED
        solvable_count = DEV_SOLVABLE_ITEMS
        unsolvable_count = DEV_UNSOLVABLE_ITEMS
    elif suite == "test":
        namespace = TEST_NAMESPACE
        world_seed = TEST_WORLD_SEED
        solvable_count = TEST_SOLVABLE_ITEMS
        unsolvable_count = TEST_UNSOLVABLE_ITEMS
    else:
        raise ValueError(f"unknown suite {suite}")

    items: list[Item] = []
    for i in range(solvable_count):
        items.append(generate_item(namespace, world_seed, i, True))
    for i in range(unsolvable_count):
        items.append(generate_item(namespace, world_seed, solvable_count + i, False))
    return items


class NoisyFilter:
    def __init__(self, seed: int) -> None:
        self.seed = seed

    def score(self, item: Item, rule_idx: int) -> float:
        predicted = item.predictions[rule_idx]
        correct = sum(
            (pair in predicted) == label
            for pair, label in item.examples
        )
        base = correct / FILTER_EXAMPLE_COUNT
        rng = random.Random(
            stable_seed("filter", self.seed, item.uid, HYPOTHESES[rule_idx].signature())
        )
        noise = rng.uniform(-FILTER_NOISE_AMPLITUDE, FILTER_NOISE_AMPLITUDE)
        return max(0.0, min(1.0, base + noise))


def rule_distance(left_idx: int, right_idx: int) -> int:
    left = HYPOTHESES[left_idx].steps
    right = HYPOTHESES[right_idx].steps
    shared = min(len(left), len(right))
    mismatch = sum(left[i] != right[i] for i in range(shared))
    return mismatch + abs(len(left) - len(right))


class Dreamer:
    def __init__(
        self,
        seed: int,
        item_uid: str,
        item: "Item | None" = None,
        judge: "NoisyFilter | None" = None,
    ) -> None:
        self.rng = random.Random(stable_seed("dreamer", seed, item_uid))
        self.item = item
        self.judge = judge
        self._scores: list[float] | None = None
        self._weights: dict[float, list[float]] = {}

    def _fresh(self, temperature: float) -> int:
        if self.item is None or self.judge is None or DREAM_GUIDE_SHARPNESS <= 0:
            return self.rng.randrange(HYPOTHESIS_COUNT)
        if self._scores is None:
            self._scores = [
                self.judge.score(self.item, idx) for idx in range(HYPOTHESIS_COUNT)
            ]
        if temperature not in self._weights:
            self._weights[temperature] = [
                math.exp(DREAM_GUIDE_SHARPNESS * score / temperature)
                for score in self._scores
            ]
        return self.rng.choices(
            range(HYPOTHESIS_COUNT), weights=self._weights[temperature]
        )[0]

    def propose(
        self,
        source_idx: int | None,
        temperature: float,
        force_local: bool = False,
    ) -> int:
        level = TEMPERATURE_LEVELS.index(temperature)
        local_probability = LOCAL_SAMPLE_PROBABILITIES[level]
        use_local = source_idx is not None and (
            force_local or self.rng.random() < local_probability
        )
        if not use_local:
            return self._fresh(temperature)
        return self._mutate(source_idx, LOCAL_MUTATION_OPS[level])

    def _mutate(self, source_idx: int, operations: int) -> int:
        steps = list(HYPOTHESES[source_idx].steps)
        for _ in range(operations):
            if len(steps) == 1 and self.rng.random() < DEPTH_MUTATION_PROBABILITY:
                steps.append(self.rng.randrange(STEP_VARIANTS))
                continue
            if len(steps) == 2 and self.rng.random() < DEPTH_MUTATION_PROBABILITY:
                del steps[self.rng.randrange(2)]
                continue

            pos = self.rng.randrange(len(steps))
            step = steps[pos]
            relation = step // 2
            inverse = step % 2
            if self.rng.random() < INVERSION_MUTATION_PROBABILITY:
                steps[pos] = relation * 2 + (1 - inverse)
            else:
                new_relation = self.rng.randrange(BASE_RELATION_COUNT)
                if new_relation == relation:
                    new_relation = (new_relation + 1) % BASE_RELATION_COUNT
                steps[pos] = new_relation * 2 + inverse

        return RULE_TO_INDEX[tuple(steps)]


class Gateway:
    """Owns the hard meter so arm logic cannot self-report compute."""

    def __init__(self, meter: Meter) -> None:
        self.meter = meter

    def dream(
        self,
        dreamer: Dreamer,
        source_idx: int | None,
        temperature: float,
        force_local: bool = False,
    ) -> int:
        self.meter.dream()
        return dreamer.propose(source_idx, temperature, force_local)

    def check(self, item: Item, rule_idx: int) -> float:
        self.meter.check()
        return exact_jaccard(item.predictions[rule_idx], item.target)


class ArmRunner:
    def __init__(self, item: Item, seed: int, arm: str, fixed_n: int) -> None:
        self.item = item
        self.seed = seed
        self.arm = arm
        self.fixed_n = fixed_n
        self.meter = Meter(MAX_CANDIDATES, MAX_CHECKS)
        self.gateway = Gateway(self.meter)
        self.filter = NoisyFilter(seed)
        self.dreamer = Dreamer(seed, item.uid, item, self.filter)
        self.audit_rng = random.Random(stable_seed("audit", seed, item.uid))

        self.temperature = START_TEMPERATURE
        self.seen: set[int] = set()
        self.dream_counts: dict[int, int] = {}
        self.seen_order: list[int] = []
        self.filter_scores: dict[int, float] = {}
        self.filter_rejected: list[int] = []
        self.checked: list[dict[str, object]] = []
        self.checked_indices: set[int] = set()
        self.refined: set[int] = set()

        self.best_filter_idx: int | None = None
        self.best_exact_idx: int | None = None
        self.best_exact_score = -1.0
        self.first_exact_score: float | None = None
        self.narrow_source: int | None = None
        self.consecutive_stalls = 0
        self.round_no = 0
        self.stop_reason = ""

    @property
    def checker_can_found(self) -> bool:
        return self.arm in {"A", "B", "C"}

    def _current_source(self) -> int | None:
        if self.best_exact_idx is not None:
            return self.best_exact_idx
        return self.best_filter_idx

    def _move_temperature(self, delta: int) -> None:
        index = TEMPERATURE_LEVELS.index(self.temperature)
        index = max(0, min(len(TEMPERATURE_LEVELS) - 1, index + delta))
        self.temperature = TEMPERATURE_LEVELS[index]

    def _dream_round(self) -> dict[str, object]:
        source = self._current_source()
        forced_source = self.narrow_source
        self.narrow_source = None
        narrow_count = round(DREAMS_PER_ROUND * NARROW_NEXT_ROUND_FRACTION)

        new_candidates: list[int] = []
        duplicate_count = 0
        boring_count = 0
        for slot in range(DREAMS_PER_ROUND):
            force_local = forced_source is not None and slot < narrow_count
            proposal_source = forced_source if force_local else source
            idx = self.gateway.dream(
                self.dreamer,
                proposal_source,
                self.temperature,
                force_local=force_local,
            )
            self.dream_counts[idx] = self.dream_counts.get(idx, 0) + 1
            if idx in self.seen:
                duplicate_count += 1
                continue

            self.seen.add(idx)
            self.seen_order.append(idx)
            score = self.filter.score(self.item, idx)
            self.filter_scores[idx] = score
            new_candidates.append(idx)

            if (
                source is not None
                and score < BORING_SCORE
                and rule_distance(idx, source) <= 1
            ):
                boring_count += 1
            if self.best_filter_idx is None or score > self.filter_scores[self.best_filter_idx]:
                self.best_filter_idx = idx

        survivors = [
            idx for idx in new_candidates
            if self.filter_scores[idx] >= FILTER_KEEP_THRESHOLD
        ]
        if CARRY_UNCHECKED_SURVIVORS:
            survivors.extend(
                idx for idx in self.seen_order
                if idx not in new_candidates
                and idx not in self.checked_indices
                and self.filter_scores[idx] >= FILTER_KEEP_THRESHOLD
            )
        survivors.sort(key=lambda i: (-self.filter_scores[i], i))
        rejected = [
            idx for idx in new_candidates
            if self.filter_scores[idx] < FILTER_KEEP_THRESHOLD
        ]
        self.filter_rejected.extend(rejected)

        return {
            "new": new_candidates,
            "survivors": survivors,
            "duplicates": duplicate_count,
            "boring": boring_count,
        }

    def _check_exact(self, rule_idx: int, route: str) -> dict[str, object]:
        score = self.gateway.check(self.item, rule_idx)
        record = {
            "idx": rule_idx,
            "signature": HYPOTHESES[rule_idx].signature(),
            "exact_score": score,
            "filter_score": self.filter_scores.get(rule_idx),
            "route": route,
        }
        self.checked.append(record)
        self.checked_indices.add(rule_idx)
        if self.first_exact_score is None:
            self.first_exact_score = score
        if score > self.best_exact_score:
            self.best_exact_score = score
            self.best_exact_idx = rule_idx
        return record

    def _probe_preferred(
        self, preferred_idx: int
    ) -> tuple[int | None, dict[str, object] | None]:
        next_check = self.meter.checker_calls + 1
        if next_check % RESCUE_EVERY_N_CHECKS == 0:
            rescue_pool = [
                idx for idx in self.filter_rejected
                if idx not in self.checked_indices
            ]
            if rescue_pool:
                audit_idx = self.audit_rng.choice(rescue_pool)
                audit = self._check_exact(audit_idx, "rescue-audit")
                if self.checker_can_found and audit["exact_score"] >= PASS_SCORE:
                    return audit_idx, None

        preferred = self._check_exact(preferred_idx, "filter-survivor")
        if self.checker_can_found and preferred["exact_score"] >= PASS_SCORE:
            return preferred_idx, preferred
        return None, preferred

    def _near_misses(self) -> list[dict[str, object]]:
        seen: set[int] = set()
        near: list[dict[str, object]] = []
        for record in sorted(
            self.checked,
            key=lambda rec: (-float(rec["exact_score"]), int(rec["idx"])),
        ):
            idx = int(record["idx"])
            score = float(record["exact_score"])
            if idx in seen or not (NEAR_MISS_SCORE <= score < PASS_SCORE):
                continue
            seen.add(idx)
            near.append(record)
        return near

    def _expected_round_pass(self) -> float:
        failed_checks = sum(float(rec["exact_score"]) < PASS_SCORE for rec in self.checked)
        near_misses = sum(
            NEAR_MISS_SCORE <= float(rec["exact_score"]) < PASS_SCORE
            for rec in self.checked
        )
        p = (
            BETA_ALPHA + NEAR_MISS_PRIOR_WEIGHT * near_misses
        ) / (
            BETA_ALPHA + BETA_BETA + failed_checks
        )
        return 1.0 - (1.0 - p) ** CHECKS_PER_ROUND

    def _unseen_kept_mass(self) -> float:
        """Good-Turing, restricted to ideas the filter keeps: of all the times a
        believable idea was dreamed, what share were first-and-only sightings?"""
        kept = [
            count for idx, count in self.dream_counts.items()
            if self.filter_scores.get(idx, 0.0) >= FILTER_KEEP_THRESHOLD
        ]
        total = sum(kept)
        if total < COVERAGE_MIN_KEPT_DREAMS:
            return 1.0
        return sum(1 for count in kept if count == 1) / total

    def _backlog_empty(self) -> bool:
        return not any(
            idx not in self.checked_indices
            and self.filter_scores[idx] >= FILTER_KEEP_THRESHOLD
            for idx in self.seen_order
        )

    def _filter_found(self, candidates: Iterable[int]) -> int | None:
        candidates = list(candidates)
        if not candidates:
            return None
        winner = max(candidates, key=lambda i: (self.filter_scores[i], -i))
        if self.filter_scores[winner] >= FILTER_FOUND_THRESHOLD:
            return winner
        return None

    def _refine(self, trigger: str) -> dict[str, object] | None:
        leads = [
            rec for rec in self._near_misses()
            if int(rec["idx"]) not in self.refined
        ][:REFINE_MAX_LEADS]
        if not leads:
            return None

        for initial in leads:
            lead_idx = int(initial["idx"])
            baseline = float(initial["exact_score"])
            self.refined.add(lead_idx)

            for _ in range(REFINE_MAX_STEPS):
                unique: list[int] = []
                for _ in range(REFINE_MUTATIONS):
                    idx = self.gateway.dream(
                        self.dreamer,
                        lead_idx,
                        TEMPERATURE_LEVELS[0],
                        force_local=True,
                    )
                    if idx in self.seen:
                        continue
                    self.seen.add(idx)
                    self.seen_order.append(idx)
                    score = self.filter.score(self.item, idx)
                    self.filter_scores[idx] = score
                    unique.append(idx)
                    if self.best_filter_idx is None or score > self.filter_scores[self.best_filter_idx]:
                        self.best_filter_idx = idx

                if not unique:
                    break

                if self.arm == "D":
                    filter_found = self._filter_found(unique)
                    if filter_found is not None:
                        return self._outcome("FOUND", filter_found, "filter")

                preferred = max(unique, key=lambda i: (self.filter_scores[i], -i))
                found, checked = self._probe_preferred(preferred)
                if found is not None:
                    return self._outcome("FOUND", found, "checker")

                if self.meter.hard_cap_hit:
                    self.stop_reason = "hard-cap-during-refine"
                    return self._outcome("BUDGET_OUT")

                if checked is None:
                    break
                score = float(checked["exact_score"])
                if score < baseline + REFINE_MIN_IMPROVEMENT:
                    break
                baseline = score
                lead_idx = preferred

        self.stop_reason = f"{trigger}-after-refine"
        return self._outcome("GIVEUP")

    def _make_parked_record(self, exit_kind: str) -> dict[str, object]:
        ranked: list[dict[str, object]] = []
        used: set[int] = set()

        for rec in sorted(
            self.checked,
            key=lambda r: (-float(r["exact_score"]), int(r["idx"])),
        ):
            idx = int(rec["idx"])
            score = float(rec["exact_score"])
            if idx in used or score >= PASS_SCORE:
                continue
            used.add(idx)
            ranked.append({
                "signature": HYPOTHESES[idx].signature(),
                "score": round(score, 6),
                "score_kind": "checker_jaccard",
                "reason": f"exact checker Jaccard {score:.3f} < {PASS_SCORE:.3f}",
            })

        for idx in sorted(
            self.seen_order,
            key=lambda i: (-self.filter_scores.get(i, -1.0), i),
        ):
            if idx in used:
                continue
            used.add(idx)
            score = self.filter_scores.get(idx, 0.0)
            ranked.append({
                "signature": HYPOTHESES[idx].signature(),
                "score": round(score, 6),
                "score_kind": "filter_heuristic",
                "reason": (
                    f"not checker-verified; filter score {score:.3f}, "
                    f"keep threshold {FILTER_KEEP_THRESHOLD:.3f}"
                ),
            })
            if len(ranked) >= PROPOSAL_TOP_K:
                break

        while len(ranked) < PROPOSAL_TOP_K:
            ranked.append({
                "signature": "<no additional distinct cluster>",
                "score": None,
                "score_kind": "none",
                "reason": "fewer than three distinct rejected ideas were produced",
            })

        best_failed = max(
            (
                float(rec["exact_score"])
                for rec in self.checked
                if float(rec["exact_score"]) < PASS_SCORE
            ),
            default=None,
        )
        if best_failed is not None:
            condition = (
                f"exact-match condition failed: best checked Jaccard "
                f"{best_failed:.3f} < {PASS_SCORE:.3f}"
            )
        else:
            best_filter = max(self.filter_scores.values(), default=0.0)
            condition = (
                f"filter-survivor condition failed before exact verification: "
                f"best heuristic score {best_filter:.3f}"
            )

        ask = (
            "Give one correct base-relation step for the target, or say that the "
            "1/2-step hypothesis-space restriction may be relaxed."
        )
        compute = (
            f"{self.meter.candidates} candidates, "
            f"{self.meter.checker_calls} checker calls"
        )
        trend_start = self.first_exact_score if self.first_exact_score is not None else 0.0
        trend_end = max(self.best_exact_score, 0.0)

        question = [
            f"Goal: {self.item.goal}",
            (
                f"Tried: {self.meter.candidates} ideas, {len(self.seen)} distinct "
                f"clusters, {self.meter.checker_calls} checked; {compute}."
            ),
            (
                "Best rejected: "
                + "; ".join(
                    f"{idea['signature']}={idea['score']}: {idea['reason']}"
                    for idea in ranked[:PROPOSAL_TOP_K]
                )
            ),
            f"Unblocker: {condition}. {ask}",
            (
                "Options: (a) give the fact/hint, (b) relax exact-match or "
                "hypothesis-space condition, (c) grant extra budget, (d) drop."
            ),
        ]
        assert len(question) <= QUESTION_MAX_LINES

        record: dict[str, object] = {
            "goal": self.item.goal,
            "tried": {
                "ideas": self.meter.candidates,
                "distinct_clusters": len(self.seen),
                "checked": self.meter.checker_calls,
                "compute_spent": {
                    "candidates": self.meter.candidates,
                    "checker_calls": self.meter.checker_calls,
                },
                "cluster_signatures": [
                    HYPOTHESES[idx].signature() for idx in self.seen_order
                ],
            },
            "best_rejected": ranked[:PROPOSAL_TOP_K],
            "unblocker": {
                "condition": condition,
                "ask": ask,
                "real_failed_condition": True,
            },
            "options": {
                "a": "give the fact/hint",
                "b": "relax the named condition",
                "c": "grant extra budget",
                "d": "drop the job",
            },
            "question_lines": question,
            "stop_reason": self.stop_reason,
        }
        if exit_kind == "BUDGET_OUT":
            record["trend"] = f"best checker score {trend_start:.3f} -> {trend_end:.3f}"
            record["exact_extra_budget_requested"] = {
                "candidates": DREAMS_PER_ROUND,
                "checker_calls": CHECKS_PER_ROUND,
            }
        return record

    def _outcome(
        self,
        exit_kind: str,
        found_idx: int | None = None,
        found_via: str | None = None,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "exit": exit_kind,
            "found_idx": found_idx,
            "found_signature": (
                HYPOTHESES[found_idx].signature() if found_idx is not None else None
            ),
            "found_via": found_via,
            "checker_calls": self.meter.checker_calls,
            "candidates": self.meter.candidates,
            "cap_fraction": self.meter.cap_fraction(),
            "record": None,
        }
        if exit_kind in {"GIVEUP", "BUDGET_OUT"}:
            result["record"] = self._make_parked_record(exit_kind)
        return result

    def run(self) -> dict[str, object]:
        try:
            while self.round_no < MAX_ROUNDS:
                self.round_no += 1
                before_best = self.best_exact_score
                before_checks = len(self.checked)
                batch = self._dream_round()
                new_candidates = list(batch["new"])
                survivors = list(batch["survivors"])

                if self.arm == "D":
                    filter_found = self._filter_found(new_candidates)
                    if filter_found is not None:
                        return self._outcome("FOUND", filter_found, "filter")

                for idx in survivors[:CHECKS_PER_ROUND]:
                    found, _ = self._probe_preferred(idx)
                    if found is not None:
                        return self._outcome("FOUND", found, "checker")

                if self.meter.hard_cap_hit:
                    self.stop_reason = "hard-cap"
                    return self._outcome("BUDGET_OUT")

                new_check_records = self.checked[before_checks:]
                near_appeared = any(
                    NEAR_MISS_SCORE <= float(rec["exact_score"]) < PASS_SCORE
                    for rec in new_check_records
                )
                if near_appeared:
                    best_near = max(
                        (
                            rec for rec in new_check_records
                            if NEAR_MISS_SCORE <= float(rec["exact_score"]) < PASS_SCORE
                        ),
                        key=lambda rec: float(rec["exact_score"]),
                    )
                    self.narrow_source = int(best_near["idx"])
                    self._move_temperature(-1)
                else:
                    duplicate_fraction = int(batch["duplicates"]) / DREAMS_PER_ROUND
                    boring_fraction = int(batch["boring"]) / DREAMS_PER_ROUND
                    all_rejected = not survivors
                    if all_rejected and (
                        duplicate_fraction > WIDEN_DUPLICATE_FRACTION
                        or boring_fraction > WIDEN_DUPLICATE_FRACTION
                    ):
                        self._move_temperature(+1)
                    # All generated rules are structured, so incoherent_fraction is 0 in v1.

                after_best = self.best_exact_score
                if before_best < 0.0:
                    improvement = max(after_best, 0.0)
                else:
                    improvement = max(0.0, after_best - before_best)
                dry = not survivors
                stall = dry or (
                    len(new_candidates) < STALL_MIN_NEW_CLUSTERS
                    and improvement < STALL_IMPROVEMENT
                )
                self.consecutive_stalls = (
                    self.consecutive_stalls + 1 if stall else 0
                )

                if self.arm == "B":
                    if self.round_no >= self.fixed_n:
                        self.stop_reason = f"fixed-{self.fixed_n}-rounds"
                        return self._outcome("GIVEUP")
                    continue

                if self.arm == "C":
                    continue

                if self.round_no < MIN_GIVEUP_ROUNDS:
                    continue

                stop_reason: str | None = None
                if self.consecutive_stalls >= STALLS_TO_STOP:
                    stop_reason = "stall"
                elif (
                    COVERAGE_STOP_UNSEEN_MASS > 0
                    and self._backlog_empty()
                    and self._unseen_kept_mass() < COVERAGE_STOP_UNSEEN_MASS
                ):
                    stop_reason = "coverage"
                elif self._expected_round_pass() < EV_STOP_THRESHOLD:
                    stop_reason = "expected-value"

                if stop_reason is not None:
                    self.stop_reason = stop_reason
                    refined = self._refine(stop_reason)
                    if refined is not None:
                        return refined
                    return self._outcome("GIVEUP")

            self.stop_reason = "round-cap"
            return self._outcome("BUDGET_OUT")

        except BudgetExceeded:
            self.stop_reason = "meter-raised"
            return self._outcome("BUDGET_OUT")


def record_complete(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    required = {"goal", "tried", "best_rejected", "unblocker", "options"}
    if not required.issubset(record):
        return False
    tried = record["tried"]
    unblocker = record["unblocker"]
    best = record["best_rejected"]
    if not isinstance(tried, dict) or "cluster_signatures" not in tried:
        return False
    if not isinstance(best, list) or len(best) != PROPOSAL_TOP_K:
        return False
    if not isinstance(unblocker, dict):
        return False
    return bool(unblocker.get("condition")) and bool(unblocker.get("ask"))


def aggregate_arm(
    items: Sequence[Item],
    seed: int,
    arm: str,
    fixed_n: int,
) -> dict[str, object]:
    solved = 0
    false_found = 0
    correct_giveups = 0
    wrong_giveups = 0
    budget_outs = 0
    checker_calls = 0
    candidates = 0
    unsolvable_cap_fractions: list[float] = []
    records: list[dict[str, object]] = []

    for item in items:
        outcome = ArmRunner(item, seed, arm, fixed_n).run()
        checker_calls += int(outcome["checker_calls"])
        candidates += int(outcome["candidates"])

        if not item.solvable:
            unsolvable_cap_fractions.append(float(outcome["cap_fraction"]))

        if outcome["exit"] == "FOUND":
            found_idx = int(outcome["found_idx"])
            if found_idx in item.solution_indices:
                solved += 1
            else:
                false_found += 1
        elif outcome["exit"] == "GIVEUP":
            if item.solvable:
                wrong_giveups += 1
            else:
                correct_giveups += 1
        elif outcome["exit"] == "BUDGET_OUT":
            budget_outs += 1

        if outcome["record"] is not None:
            records.append({
                "item_id": item.uid,
                "solvable_for_evaluation": item.solvable,
                "exit": outcome["exit"],
                **dict(outcome["record"]),
            })

    complete_count = sum(record_complete(record) for record in records)
    valid_unblockers = sum(
        bool(record["unblocker"].get("real_failed_condition"))
        for record in records
    )
    total_records = len(records)

    return {
        "solved": solved,
        "false_found": false_found,
        "correct_giveups": correct_giveups,
        "wrong_giveups": wrong_giveups,
        "budget_outs": budget_outs,
        "checker_calls": checker_calls,
        "candidates": candidates,
        "mean_fraction_of_cap_used_on_unsolvable_items": (
            sum(unsolvable_cap_fractions) / len(unsolvable_cap_fractions)
            if unsolvable_cap_fractions else 0.0
        ),
        "giveup_record_completeness": (
            complete_count / total_records if total_records else 1.0
        ),
        "giveup_records_complete": complete_count,
        "giveup_records_total": total_records,
        "unblocker_valid_fraction": (
            valid_unblockers / total_records if total_records else 1.0
        ),
        "giveup_records": records,
    }


def tune_fixed_n(
    items: Sequence[Item],
    seeds: Sequence[int],
) -> tuple[int, dict[str, object]]:
    trials: dict[str, object] = {}
    best_n = TUNE_MIN_ROUNDS
    best_key: tuple[int, int, int, int] | None = None

    for n in range(TUNE_MIN_ROUNDS, TUNE_MAX_ROUNDS + 1):
        total_solved = 0
        total_candidates = 0
        total_checks = 0
        per_seed: dict[str, object] = {}
        for seed in seeds:
            metrics = aggregate_arm(items, seed, "B", n)
            per_seed[str(seed)] = {
                "solved": metrics["solved"],
                "candidates": metrics["candidates"],
                "checker_calls": metrics["checker_calls"],
            }
            total_solved += int(metrics["solved"])
            total_candidates += int(metrics["candidates"])
            total_checks += int(metrics["checker_calls"])

        trials[str(n)] = {
            "solved": total_solved,
            "candidates": total_candidates,
            "checker_calls": total_checks,
            "per_seed": per_seed,
        }
        key = (total_solved, -total_candidates, -total_checks, -n)
        if best_key is None or key > best_key:
            best_key = key
            best_n = n

    return best_n, {
        "criterion": "maximize dev solved; ties use fewer candidates, then checks, then rounds",
        "trials": trials,
    }


def componentwise_compute_at_most(
    left: dict[str, object],
    right: dict[str, object],
    ratio: float,
) -> bool:
    return (
        int(left["candidates"]) <= ratio * int(right["candidates"])
        and int(left["checker_calls"]) <= ratio * int(right["checker_calls"])
    )


def pass_marks_for_seed(
    arms: dict[str, dict[str, object]],
    unsolvable_count: int,
) -> list[dict[str, object]]:
    a, b, c, d = (arms[name] for name in ("A", "B", "C", "D"))

    mark1 = (
        int(a["false_found"]) == 0
        and int(b["false_found"]) == 0
        and int(c["false_found"]) == 0
        and int(d["false_found"]) > 0
    )
    mark2 = int(a["solved"]) >= PASS2_SOLVE_RATIO * int(c["solved"])
    mark3 = componentwise_compute_at_most(a, c, PASS3_COMPUTE_RATIO)

    more_solved = (
        int(a["solved"]) >= int(b["solved"]) + PASS4_MORE_SOLVED
        and componentwise_compute_at_most(a, b, 1.0)
    )
    equal_but_cheaper = (
        int(a["solved"]) == int(b["solved"])
        and componentwise_compute_at_most(a, b, 1.0 - PASS4_COMPUTE_SAVINGS)
    )
    mark4 = more_solved or equal_but_cheaper

    required_giveups = math.ceil(PASS5_GIVEUP_FRACTION * unsolvable_count)
    mark5 = (
        int(a["correct_giveups"]) >= required_giveups
        and float(a["mean_fraction_of_cap_used_on_unsolvable_items"])
        <= PASS5_CAP_FRACTION
    )
    mark6 = all(
        math.isclose(float(metrics["giveup_record_completeness"]), 1.0)
        and math.isclose(float(metrics["unblocker_valid_fraction"]), 1.0)
        for metrics in arms.values()
    )

    return [
        {
            "id": 1,
            "pass": mark1,
            "detail": (
                f"false FOUND A/B/C={a['false_found']}/{b['false_found']}/"
                f"{c['false_found']}; D={d['false_found']} (>0 required)"
            ),
        },
        {
            "id": 2,
            "pass": mark2,
            "detail": f"A solved {a['solved']} vs C {c['solved']} (>=95%)",
        },
        {
            "id": 3,
            "pass": mark3,
            "detail": (
                f"A compute {a['candidates']} cand/{a['checker_calls']} checks vs "
                f"C {c['candidates']}/{c['checker_calls']} (both <=70%)"
            ),
        },
        {
            "id": 4,
            "pass": mark4,
            "detail": (
                f"A vs B solved {a['solved']} vs {b['solved']}; compute "
                f"{a['candidates']}/{a['checker_calls']} vs "
                f"{b['candidates']}/{b['checker_calls']}"
            ),
        },
        {
            "id": 5,
            "pass": mark5,
            "detail": (
                f"A correct give-ups {a['correct_giveups']}/{unsolvable_count} "
                f"(>={required_giveups}); mean cap fraction "
                f"{float(a['mean_fraction_of_cap_used_on_unsolvable_items']):.3f}"
            ),
        },
        {
            "id": 6,
            "pass": mark6,
            "detail": "all parked records complete; unblockers name a failed condition",
        },
    ]


def run_suite(
    suite: str,
    seeds: Sequence[int],
    fixed_n: int,
    tuning: dict[str, object] | None = None,
) -> dict[str, object]:
    items = generate_suite(suite)
    unsolvable_count = sum(not item.solvable for item in items)
    per_seed: dict[str, object] = {}

    for seed in seeds:
        arms = {
            arm: aggregate_arm(items, seed, arm, fixed_n)
            for arm in ("A", "B", "C", "D")
        }
        marks = pass_marks_for_seed(arms, unsolvable_count)
        per_seed[str(seed)] = {
            "arms": arms,
            "pass_marks": marks,
            "seed_verdict": (
                "KEEP_RULE" if all(bool(mark["pass"]) for mark in marks)
                else "KEEP_FIXED_N"
            ),
        }

    overall = (
        "KEEP_RULE"
        if all(
            seed_result["seed_verdict"] == "KEEP_RULE"
            for seed_result in per_seed.values()
        )
        else "KEEP_FIXED_N"
    )
    result: dict[str, object] = {
        "suite": suite,
        "seeds": list(seeds),
        "fixed_n_rounds": fixed_n,
        "item_counts": {
            "total": len(items),
            "solvable": len(items) - unsolvable_count,
            "unsolvable": unsolvable_count,
        },
        "per_seed": per_seed,
        "overall_verdict": overall,
        "verdict_rule": "all six pass marks must pass independently for every seed",
    }
    if tuning is not None:
        result["dev_fixed_n_tuning"] = tuning
    return result


def render_report(result: dict[str, object]) -> str:
    lines = [
        f"Suite: {result['suite']}",
        f"Seeds: {', '.join(str(seed) for seed in result['seeds'])}",
        f"Fixed-N baseline: N={result['fixed_n_rounds']} rounds",
        "",
        (
            "seed arm solved false_found correct_giveups wrong_giveups "
            "budget_outs checker_calls candidates unsolv_cap_fraction record_complete"
        ),
    ]

    per_seed = dict(result["per_seed"])
    for seed in result["seeds"]:
        seed_result = dict(per_seed[str(seed)])
        arms = dict(seed_result["arms"])
        for arm in ("A", "B", "C", "D"):
            metrics = dict(arms[arm])
            lines.append(
                f"{seed} {arm} {metrics['solved']} {metrics['false_found']} "
                f"{metrics['correct_giveups']} {metrics['wrong_giveups']} "
                f"{metrics['budget_outs']} {metrics['checker_calls']} "
                f"{metrics['candidates']} "
                f"{float(metrics['mean_fraction_of_cap_used_on_unsolvable_items']):.3f} "
                f"{float(metrics['giveup_record_completeness']):.3f}"
            )

    lines.extend(["", "Pre-fixed pass marks (evaluated per seed; never averaged across seeds):"])
    for seed in result["seeds"]:
        seed_result = dict(per_seed[str(seed)])
        lines.append(f"Seed {seed}:")
        for mark in seed_result["pass_marks"]:
            status = "PASS" if mark["pass"] else "FAIL"
            lines.append(f"  {mark['id']}. {status} - {mark['detail']}")
        lines.append(f"  Seed verdict: {seed_result['seed_verdict']}")

    if result["suite"] == "dev":
        lines.extend([
            "",
            (
                "DEV NOTE: mark 5 preserves the pre-fixed 48/60 = 80% give-up "
                "rate on the 20 unsolvable dev items; test uses the exact 48/60 count."
            ),
        ])

    lines.extend([
        "",
        f"OVERALL VERDICT: {result['overall_verdict']}",
        (
            "Interpretation: KEEP_RULE supports only 'the stopping controller is "
            "sensible on a toy'; it says nothing about creativity or a neural dreamer."
        ),
    ])
    return "\n".join(lines) + "\n"


def frozen_constants() -> dict[str, object]:
    return {
        "ENTITY_COUNT": ENTITY_COUNT,
        "BASE_RELATION_COUNT": BASE_RELATION_COUNT,
        "STEP_VARIANTS": STEP_VARIANTS,
        "PAIR_COUNT": PAIR_COUNT,
        "HYPOTHESIS_COUNT": HYPOTHESIS_COUNT,
        "DREAMS_PER_ROUND": DREAMS_PER_ROUND,
        "CHECKS_PER_ROUND": CHECKS_PER_ROUND,
        "MAX_ROUNDS": MAX_ROUNDS,
        "MAX_CANDIDATES": MAX_CANDIDATES,
        "MAX_CHECKS": MAX_CHECKS,
        "NEAR_MISS_SCORE": NEAR_MISS_SCORE,
        "PASS_SCORE": PASS_SCORE,
        "MIN_GIVEUP_ROUNDS": MIN_GIVEUP_ROUNDS,
        "STALL_MIN_NEW_CLUSTERS": STALL_MIN_NEW_CLUSTERS,
        "STALL_IMPROVEMENT": STALL_IMPROVEMENT,
        "STALLS_TO_STOP": STALLS_TO_STOP,
        "BETA_ALPHA": BETA_ALPHA,
        "BETA_BETA": BETA_BETA,
        "NEAR_MISS_PRIOR_WEIGHT": NEAR_MISS_PRIOR_WEIGHT,
        "EV_STOP_THRESHOLD": EV_STOP_THRESHOLD,
        "VALUE_ROUND_COST_MULTIPLIER": VALUE_ROUND_COST_MULTIPLIER,
        "REFINE_MAX_LEADS": REFINE_MAX_LEADS,
        "REFINE_MAX_STEPS": REFINE_MAX_STEPS,
        "REFINE_MUTATIONS": REFINE_MUTATIONS,
        "REFINE_MIN_IMPROVEMENT": REFINE_MIN_IMPROVEMENT,
        "TEMPERATURE_LEVELS": list(TEMPERATURE_LEVELS),
        "START_TEMPERATURE": START_TEMPERATURE,
        "NARROW_NEXT_ROUND_FRACTION": NARROW_NEXT_ROUND_FRACTION,
        "WIDEN_DUPLICATE_FRACTION": WIDEN_DUPLICATE_FRACTION,
        "BORING_SCORE": BORING_SCORE,
        "INCOHERENT_FRACTION": INCOHERENT_FRACTION,
        "UNCHECKABLE_MAX_ROUNDS": UNCHECKABLE_MAX_ROUNDS,
        "UNCHECKABLE_MAX_CANDIDATES": UNCHECKABLE_MAX_CANDIDATES,
        "PROPOSAL_TOP_K": PROPOSAL_TOP_K,
        "FILTER_EXAMPLE_COUNT": FILTER_EXAMPLE_COUNT,
        "FILTER_POSITIVE_EXAMPLES": FILTER_POSITIVE_EXAMPLES,
        "FILTER_KEEP_THRESHOLD": FILTER_KEEP_THRESHOLD,
        "FILTER_NOISE_AMPLITUDE": FILTER_NOISE_AMPLITUDE,
        "FILTER_FOUND_THRESHOLD": FILTER_FOUND_THRESHOLD,
        "FILTER_PRECISION_FAULT_RATIO": FILTER_PRECISION_FAULT_RATIO,
        "RESCUE_EVERY_N_CHECKS": RESCUE_EVERY_N_CHECKS,
        "EMBEDDING_DUPLICATE_COSINE": EMBEDDING_DUPLICATE_COSINE,
        "QUESTION_MAX_LINES": QUESTION_MAX_LINES,
        "CREATIVE_ASKS_PER_DAY": CREATIVE_ASKS_PER_DAY,
        "REASK_UNANSWERED_DAYS": REASK_UNANSWERED_DAYS,
        "MAX_BLOCKING_QUESTIONS": MAX_BLOCKING_QUESTIONS,
        "TEST_SOLVABLE_ITEMS": TEST_SOLVABLE_ITEMS,
        "TEST_UNSOLVABLE_ITEMS": TEST_UNSOLVABLE_ITEMS,
        "DEV_TOTAL_ITEMS": DEV_TOTAL_ITEMS,
        "DEV_SOLVABLE_ITEMS": DEV_SOLVABLE_ITEMS,
        "DEV_UNSOLVABLE_ITEMS": DEV_UNSOLVABLE_ITEMS,
        "DEFAULT_SEEDS": list(DEFAULT_SEEDS),
        "DEV_WORLD_SEED": DEV_WORLD_SEED,
        "TEST_WORLD_SEED": TEST_WORLD_SEED,
        "DEV_NAMESPACE": DEV_NAMESPACE,
        "TEST_NAMESPACE": TEST_NAMESPACE,
        "PASS2_SOLVE_RATIO": PASS2_SOLVE_RATIO,
        "PASS3_COMPUTE_RATIO": PASS3_COMPUTE_RATIO,
        "PASS4_MORE_SOLVED": PASS4_MORE_SOLVED,
        "PASS4_COMPUTE_SAVINGS": PASS4_COMPUTE_SAVINGS,
        "PASS5_GIVEUP_FRACTION": PASS5_GIVEUP_FRACTION,
        "PASS5_CAP_FRACTION": PASS5_CAP_FRACTION,
        "BASE_RELATION_DENSITY": BASE_RELATION_DENSITY,
        "DREAM_GUIDE_SHARPNESS": DREAM_GUIDE_SHARPNESS,
        "CARRY_UNCHECKED_SURVIVORS": CARRY_UNCHECKED_SURVIVORS,
        "COVERAGE_STOP_UNSEEN_MASS": COVERAGE_STOP_UNSEEN_MASS,
        "COVERAGE_MIN_KEPT_DREAMS": COVERAGE_MIN_KEPT_DREAMS,
        "RELATION_FAMILY_SIZE": RELATION_FAMILY_SIZE,
        "SIBLING_KEEP_PROBABILITY": SIBLING_KEEP_PROBABILITY,
        "SIBLING_ADD_DENSITY": SIBLING_ADD_DENSITY,
        "RANDOM_TARGET_DENSITY": RANDOM_TARGET_DENSITY,
        "MAX_GENERATION_ATTEMPTS": MAX_GENERATION_ATTEMPTS,
        "LOCAL_SAMPLE_PROBABILITIES": list(LOCAL_SAMPLE_PROBABILITIES),
        "LOCAL_MUTATION_OPS": list(LOCAL_MUTATION_OPS),
        "DEPTH_MUTATION_PROBABILITY": DEPTH_MUTATION_PROBABILITY,
        "INVERSION_MUTATION_PROBABILITY": INVERSION_MUTATION_PROBABILITY,
        "TUNE_MIN_ROUNDS": TUNE_MIN_ROUNDS,
        "TUNE_MAX_ROUNDS": TUNE_MAX_ROUNDS,
    }


def script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def write_frozen(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_items = generate_suite("dev")
    fixed_n, tuning = tune_fixed_n(dev_items, DEFAULT_SEEDS)
    payload = {
        "script_sha256": script_sha256(),
        "constants": frozen_constants(),
        "fixed_n_rounds": fixed_n,
        "tuning_criterion": tuning["criterion"],
    }
    path = out_dir / FROZEN_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_frozen(out_dir: Path) -> dict[str, object]:
    path = out_dir / FROZEN_FILENAME
    if not path.exists():
        raise SystemExit(
            f"test suite refused: missing {path}; run this script with --freeze first"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"test suite refused: invalid {path}: {exc}") from exc

    if payload.get("script_sha256") != script_sha256():
        raise SystemExit("test suite refused: script sha256 does not match frozen file")
    if payload.get("constants") != frozen_constants():
        raise SystemExit("test suite refused: constants do not match frozen file")

    fixed_n = payload.get("fixed_n_rounds")
    if not isinstance(fixed_n, int) or not (TUNE_MIN_ROUNDS <= fixed_n <= TUNE_MAX_ROUNDS):
        raise SystemExit("test suite refused: frozen fixed_n_rounds is invalid")
    return payload


def write_outputs(out_dir: Path, suite: str, result: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / f"{RESULTS_PREFIX}{suite}.json"
    report_path = out_dir / f"{REPORT_PREFIX}{suite}.txt"
    results_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(render_report(result), encoding="utf-8")


def run_selftest() -> None:
    # Exact checker on a hand-built 12-entity world.
    base = [frozenset() for _ in range(BASE_RELATION_COUNT)]
    base[0] = frozenset({0 * ENTITY_COUNT + 1})
    base[1] = frozenset({1 * ENTITY_COUNT + 2})
    predictions = all_predictions(tuple(base))
    chain_idx = RULE_TO_INDEX[(0, 2)]
    target = frozenset({0 * ENTITY_COUNT + 2})
    assert predictions[chain_idx] == target
    assert exact_jaccard(predictions[chain_idx], target) == PASS_SCORE
    assert exact_jaccard(predictions[RULE_TO_INDEX[(0,)]], target) < PASS_SCORE

    # Generator's unsolvable label is exhaustive over all 156 hypotheses.
    unsolvable = generate_item(
        "selftest/unsolvable",
        SELFTEST_SEED,
        0,
        False,
    )
    assert not unsolvable.solution_indices
    assert all(pred != unsolvable.target for pred in unsolvable.predictions)

    # Meter itself, not an arm, rejects an over-cap request.
    meter = Meter(candidate_cap=2, checker_cap=1)
    meter.dream(2)
    try:
        meter.dream()
        raise AssertionError("candidate meter failed to raise at cap")
    except BudgetExceeded:
        pass
    meter.check()
    try:
        meter.check()
        raise AssertionError("checker meter failed to raise at cap")
    except BudgetExceeded:
        pass

    # Find a deterministic tiny suite exposing the weak-filter negative control.
    tiny_items: list[Item] | None = None
    d_metrics: dict[str, object] | None = None
    for attempt in range(SELFTEST_SEARCH_ATTEMPTS):
        candidate_items = [
            generate_item(
                f"selftest/decoy/{attempt}",
                SELFTEST_SEED + attempt,
                i,
                False,
            )
            for i in range(SELFTEST_TINY_ITEMS)
        ]
        candidate_d = aggregate_arm(candidate_items, SELFTEST_SEED, "D", 3)
        if int(candidate_d["false_found"]) > 0:
            tiny_items = candidate_items
            d_metrics = candidate_d
            break
    assert tiny_items is not None and d_metrics is not None
    assert int(d_metrics["false_found"]) > 0
    a_metrics = aggregate_arm(tiny_items, SELFTEST_SEED, "A", 3)
    assert int(a_metrics["false_found"]) == 0

    # Identical seed and inputs must produce identical JSON-serializable results.
    det_items = tiny_items[:4]
    first = aggregate_arm(det_items, SELFTEST_SEED, "A", 3)
    second = aggregate_arm(det_items, SELFTEST_SEED, "A", 3)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("dev", "test"), default="dev")
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=list(DEFAULT_SEEDS),
        help="stochastic proposer/filter seeds",
    )
    parser.add_argument("--out", type=Path, default=Path("."))
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="tune fixed-N on dev, write DEFAULTS-FROZEN.json, and exit",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="run fast assertions and exit without writing suite outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.freeze and args.selftest:
        raise SystemExit("--freeze and --selftest are mutually exclusive")
    if args.freeze and args.suite == "test":
        raise SystemExit("--freeze is a dev-only action; freeze before running test")

    if args.selftest:
        run_selftest()
        print("selftest: PASS")
        return

    if args.freeze:
        path = write_frozen(args.out)
        print(f"frozen defaults: {path}")
        return

    if args.suite == "test":
        frozen = load_frozen(args.out)
        fixed_n = int(frozen["fixed_n_rounds"])
        tuning = None
    else:
        dev_items = generate_suite("dev")
        fixed_n, tuning = tune_fixed_n(dev_items, args.seeds)

    result = run_suite(args.suite, args.seeds, fixed_n, tuning)
    write_outputs(args.out, args.suite, result)
    print(render_report(result), end="")


if __name__ == "__main__":
    main()
