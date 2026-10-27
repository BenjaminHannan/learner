"""Metrics for continual learning, retrieval, calibration and learning speed.

Scores are kept per item wherever possible so that systems can be compared on
exactly the same test items. Pass/fail decisions use the exact or permutation
tests here (`binomial_greater`, `mcnemar_greater`, `paired_permutation_greater`,
`paired_greater_pvalue`); the percentile bootstrap is descriptive only, because
it under-covers for small binary samples.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import itertools
import math
import random
from statistics import NormalDist
from typing import Any, Callable, Iterable, Optional, Sequence

# Grouped sign-flip enumeration is exact; above this many magnitude-count
# combinations the permutation test falls back to Monte Carlo sampling.
EXACT_PERMUTATION_LIMIT = 200_000


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def _finite(value: Any, what: str) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"{what} must be a number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{what} must be finite, got {value!r}")
    return number


def _positive_int(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{what} must be a positive integer, got {value!r}")
    return value


def _check_alpha(alpha: float) -> float:
    alpha = _finite(alpha, "alpha")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly between 0 and 1, got {alpha}")
    return alpha


def is_binary(values: Iterable[float]) -> bool:
    """True when every value is exactly 0 or 1."""
    return all(float(value) in (0.0, 1.0) for value in values)


def accuracy_by(records: Iterable[dict[str, Any]], key: str) -> dict[str, float]:
    """Accuracy of records with a boolean 'correct' field, grouped by `key`."""
    groups: dict[str, list[float]] = defaultdict(list)
    for record in records:
        groups[str(record[key])].append(1.0 if record["correct"] else 0.0)
    return {group: mean(values) for group, values in sorted(groups.items())}


def bootstrap_ci(
    values: Sequence[float],
    *,
    stat: Callable[[Sequence[float]], float] = mean,
    samples: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(estimate, low, high) percentile bootstrap interval; descriptive only."""
    if not values:
        raise ValueError("bootstrap needs at least one value")
    samples = _positive_int(samples, "samples")
    alpha = _check_alpha(alpha)
    values = [_finite(value, "value") for value in values]
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(
        stat([values[rng.randrange(n)] for _ in range(n)]) for _ in range(samples)
    )
    low = draws[int(math.floor(alpha / 2 * (samples - 1)))]
    high = draws[int(math.ceil((1 - alpha / 2) * (samples - 1)))]
    return stat(values), low, high


def _paired(a: Sequence[float], b: Sequence[float]) -> tuple[list[float], list[float]]:
    if len(a) != len(b):
        raise ValueError("paired comparison needs scores on the same items")
    if not a:
        raise ValueError("paired comparison needs at least one item")
    return [_finite(x, "score") for x in a], [_finite(y, "score") for y in b]


def paired_difference_ci(
    a: Sequence[float],
    b: Sequence[float],
    **kwargs: Any,
) -> tuple[float, float, float]:
    """Bootstrap interval of mean(a - b) over the same items; descriptive only."""
    a, b = _paired(a, b)
    return bootstrap_ci([x - y for x, y in zip(a, b)], **kwargs)


def binomial_greater(hits: int, n: int, p: float) -> float:
    """Exact one-sided p-value P(X >= hits) for X ~ Binomial(n, p)."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"n must be a non-negative integer, got {n!r}")
    if isinstance(hits, bool) or not isinstance(hits, int) or not 0 <= hits <= n:
        raise ValueError(f"hits must be an integer in [0, n], got {hits!r}")
    p = _finite(p, "p")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must lie in [0, 1], got {p}")
    if hits == 0:
        return 1.0
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    if p == 0.5:
        # Exact rational arithmetic for the sign/McNemar case.
        tail = sum(math.comb(n, k) for k in range(hits, n + 1))
        return float(Fraction(tail, 2**n))
    log_p, log_q = math.log(p), math.log1p(-p)
    log_n = math.lgamma(n + 1)
    tail = sum(
        math.exp(log_n - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * log_p + (n - k) * log_q)
        for k in range(hits, n + 1)
    )
    return min(1.0, tail)


def mcnemar_greater(a: Sequence[float], b: Sequence[float]) -> float:
    """Exact one-sided sign test on discordant binary pairs: is `a` right more often than `b`?"""
    a, b = _paired(a, b)
    if not (is_binary(a) and is_binary(b)):
        raise ValueError("McNemar's test needs binary (0/1) scores")
    a_only = sum(1 for x, y in zip(a, b) if x > y)
    b_only = sum(1 for x, y in zip(a, b) if y > x)
    return binomial_greater(a_only, a_only + b_only, 0.5)


def paired_permutation_greater(
    diffs: Sequence[float],
    *,
    samples: int = 10000,
    seed: int = 0,
) -> float:
    """One-sided sign-flip permutation p-value for mean(diffs) > 0.

    Equal magnitudes are grouped, so the null distribution is enumerated
    exactly whenever the grouped combinations fit EXACT_PERMUTATION_LIMIT
    (always when n <= 16); otherwise `samples` random sign flips are drawn and
    the add-one estimate (1 + hits) / (samples + 1) is returned.
    """
    if not diffs:
        raise ValueError("permutation test needs at least one difference")
    samples = _positive_int(samples, "samples")
    values = [_finite(value, "difference") for value in diffs]
    observed = sum(values)
    groups = sorted(Counter(abs(v) for v in values if v != 0.0).items())
    if not groups:
        return 1.0
    # Tolerance absorbs float summation-order differences between the observed
    # statistic and the grouped null statistic.
    tolerance = 1e-9 * max(1.0, sum(abs(v) for v in values))
    threshold = observed - tolerance
    combinations = math.prod(size + 1 for _, size in groups)
    total = sum(size for _, size in groups)
    if combinations <= EXACT_PERMUTATION_LIMIT:
        options = [
            [(magnitude * (2 * k - size), math.comb(size, k)) for k in range(size + 1)]
            for magnitude, size in groups
        ]
        hits = 0
        for combo in itertools.product(*options):
            if sum(value for value, _ in combo) >= threshold:
                hits += math.prod(weight for _, weight in combo)
        return float(Fraction(hits, 2**total))
    rng = random.Random(seed)
    hits = 0
    for _ in range(samples):
        statistic = sum(
            magnitude * (2 * rng.getrandbits(size).bit_count() - size) for magnitude, size in groups
        )
        if statistic >= threshold:
            hits += 1
    return (hits + 1) / (samples + 1)


def paired_greater_pvalue(
    a: Sequence[float],
    b: Sequence[float],
    *,
    margin: float = 0.0,
    samples: int = 10000,
    seed: int = 0,
) -> float:
    """One-sided p-value for mean(a - b) > margin over the same items.

    Binary scores with margin 0 use the exact McNemar test; anything else uses
    the sign-flip permutation test on (a - b - margin), which is conservative
    for shifted binary differences.
    """
    a, b = _paired(a, b)
    margin = _finite(margin, "margin")
    if margin == 0.0 and is_binary(a) and is_binary(b):
        return mcnemar_greater(a, b)
    return paired_permutation_greater(
        [x - y - margin for x, y in zip(a, b)], samples=samples, seed=seed
    )


def wilson_interval(hits: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Two-sided (1 - alpha) Wilson score interval for a binomial proportion."""
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    if isinstance(hits, bool) or not isinstance(hits, int) or not 0 <= hits <= n:
        raise ValueError(f"hits must be an integer in [0, n], got {hits!r}")
    alpha = _check_alpha(alpha)
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    phat = hits / n
    denominator = 1.0 + z * z / n
    centre = (phat + z * z / (2 * n)) / denominator
    half = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4 * n * n)) / denominator
    low = 0.0 if hits == 0 else max(0.0, centre - half)
    high = 1.0 if hits == n else min(1.0, centre + half)
    return low, high


FORGETTING_KINDS = ("post_acquisition", "chaudhry")


class ContinualMatrix:
    """R[i][j] = score on task j after finishing training stage i (0-based)."""

    def __init__(self, tasks: int) -> None:
        if isinstance(tasks, bool) or not isinstance(tasks, int) or tasks <= 0:
            raise ValueError("need at least one task")
        self.tasks = tasks
        self.scores: list[list[Optional[float]]] = [[None] * tasks for _ in range(tasks)]

    def _index(self, value: Any, what: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{what} index must be an integer, got {value!r}")
        if not 0 <= value < self.tasks:
            raise IndexError(f"{what} index {value} outside 0..{self.tasks - 1}")
        return value

    def record(self, stage: int, task: int, score: float) -> None:
        stage = self._index(stage, "stage")
        task = self._index(task, "task")
        self.scores[stage][task] = _finite(score, "score")

    def _get(self, stage: int, task: int) -> float:
        value = self.scores[self._index(stage, "stage")][self._index(task, "task")]
        if value is None:
            raise ValueError(f"missing score for stage {stage}, task {task}")
        return value

    def average_accuracy(self) -> float:
        last = self.tasks - 1
        return mean([self._get(last, task) for task in range(self.tasks)])

    def backward_transfer(self) -> float:
        """Mean change on earlier tasks from just-learned to the end; negative = forgetting."""
        if self.tasks < 2:
            return 0.0
        last = self.tasks - 1
        return mean(
            [self._get(last, task) - self._get(task, task) for task in range(last)]
        )

    def forgetting_per_task(self, kind: str = "post_acquisition") -> list[float]:
        """Per earlier task: best earlier score minus the final score.

        "post_acquisition": best over stages task..T-2 (after the task was trained).
        "chaudhry": best over all stages 0..T-2 (Chaudhry et al. 2018), so a score
        reached before training the task (forward transfer) also counts.
        """
        if kind not in FORGETTING_KINDS:
            raise ValueError(f"forgetting kind must be one of {FORGETTING_KINDS}, got {kind!r}")
        last = self.tasks - 1
        result = []
        for task in range(last):
            first = task if kind == "post_acquisition" else 0
            best = max(self._get(stage, task) for stage in range(first, last))
            result.append(best - self._get(last, task))
        return result

    def forgetting(self, kind: str = "post_acquisition") -> float:
        """Mean forgetting over earlier tasks; see `forgetting_per_task` for the kinds."""
        per_task = self.forgetting_per_task(kind)
        return mean(per_task) if per_task else 0.0

    def forgetting_report(self) -> dict[str, Any]:
        """Both forgetting variants, per task and averaged, plus BWT and final accuracy."""
        report: dict[str, Any] = {}
        for kind in FORGETTING_KINDS:
            report[kind] = self.forgetting(kind)
            report[f"{kind}_per_task"] = self.forgetting_per_task(kind)
        report["backward_transfer"] = self.backward_transfer()
        report["average_accuracy"] = self.average_accuracy()
        return report

    def forward_transfer(self, reference: Sequence[float]) -> float:
        """Mean score on task j just before training it, minus a reference score for task j.

        The reference should be a matched control (for example an age-matched
        model given equal experience), not a freshly initialised network.
        """
        if len(reference) != self.tasks:
            raise ValueError("need one reference score per task")
        reference = [_finite(value, "reference score") for value in reference]
        if self.tasks < 2:
            return 0.0
        return mean(
            [self._get(task - 1, task) - reference[task] for task in range(1, self.tasks)]
        )

    def as_dict(self) -> dict[str, Any]:
        return {"tasks": self.tasks, "scores": [list(row) for row in self.scores]}


def steps_to_threshold(
    curve: Sequence[tuple[int, float]],
    threshold: float,
    *,
    sustain: int = 1,
) -> Optional[int]:
    """First step of the earliest run of `sustain` consecutive evaluations at or above `threshold`.

    The curve is sorted by step first; duplicate steps are rejected. A run cut
    short by the end of the curve does not count.
    """
    sustain = _positive_int(sustain, "sustain")
    threshold = _finite(threshold, "threshold")
    points = sorted((_finite(step, "step"), _finite(score, "score"), step) for step, score in curve)
    for (a, _, _), (b, _, _) in zip(points, points[1:]):
        if a == b:
            raise ValueError(f"duplicate step {a} in learning curve")
    run = 0
    for index, (_, score, step) in enumerate(points):
        run = run + 1 if score >= threshold else 0
        if run == sustain:
            return points[index - sustain + 1][2]
    return None


def recall_at_k(ranked: Sequence[Sequence[Any]], targets: Sequence[Any], k: int) -> float:
    if len(ranked) != len(targets) or not targets:
        raise ValueError("need one ranking per target")
    k = _positive_int(k, "k")
    return mean([1.0 if target in list(rank)[:k] else 0.0 for rank, target in zip(ranked, targets)])


def expected_calibration_error(
    confidences: Sequence[float],
    correct: Sequence[bool],
    *,
    bins: int = 10,
) -> float:
    """Weighted mean |accuracy - confidence| over equal-width confidence bins."""
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("need one correctness flag per confidence")
    bins = _positive_int(bins, "bins")
    total = len(confidences)
    buckets: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for confidence, flag in zip(confidences, correct):
        confidence = _finite(confidence, "confidence")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidences must lie in [0,1]")
        buckets[min(int(confidence * bins), bins - 1)].append((confidence, bool(flag)))
    error = 0.0
    for items in buckets.values():
        accuracy = mean([1.0 if flag else 0.0 for _, flag in items])
        confidence = mean([c for c, _ in items])
        error += len(items) / total * abs(accuracy - confidence)
    return error


__all__ = [
    "EXACT_PERMUTATION_LIMIT",
    "FORGETTING_KINDS",
    "ContinualMatrix",
    "accuracy_by",
    "binomial_greater",
    "bootstrap_ci",
    "expected_calibration_error",
    "is_binary",
    "mcnemar_greater",
    "mean",
    "paired_difference_ci",
    "paired_greater_pvalue",
    "paired_permutation_greater",
    "recall_at_k",
    "steps_to_threshold",
    "wilson_interval",
]
