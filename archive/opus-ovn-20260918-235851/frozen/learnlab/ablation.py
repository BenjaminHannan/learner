"""The project rule: a component passes only if lesioning it removes its gain.

A component is judged on a fixed tuple of item IDs. The full system is scored,
then scored under the lesion, then scored again: the two full runs must agree
item by item, and the component's state fingerprint must change while the
lesion is active and be restored afterwards. The full system must beat every
required baseline (scored on exactly the same items, with audited budgets and
information that match) by a declared minimum effect, with exact or
permutation tests. The lesion must remove at least `gain_fraction` of the
advantage over the best baseline, tested per item, and a lesion that falls far
below the best baseline needs a control trained without the component.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field
import math
import random
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, Sequence

import torch

from .metrics import mean, paired_greater_pvalue, paired_permutation_greater
from .policy import ALPHA, BUDGET_TOLERANCE, LESION_GAIN_FRACTION, MIN_ITEMS

ItemScores = Mapping[str, float]
Evaluate = Callable[[tuple[str, ...]], ItemScores]

BUDGET_FIELDS = (
    "train_tokens",
    "updates",
    "flops",
    "parameters",
    "retrieved_items",
    "retrieved_tokens",
)


@dataclass(frozen=True)
class Account:
    """Audited budget of one arm and the information sources it could use."""

    run_id: str
    train_tokens: int = 0
    updates: int = 0
    flops: float = 0.0
    parameters: int = 0
    retrieved_items: int = 0
    retrieved_tokens: int = 0
    information: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("an account needs a non-empty run_id")
        for name in BUDGET_FIELDS:
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"account field {name} must be a finite number >= 0, got {value!r}")
        if isinstance(self.information, str):
            raise TypeError("information must be a collection of source names, not one string")
        object.__setattr__(self, "information", frozenset(self.information))

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"run_id": self.run_id}
        out.update({name: getattr(self, name) for name in BUDGET_FIELDS})
        out["information"] = sorted(self.information)
        return out


@dataclass(frozen=True)
class Arm:
    """Per-item scores of one system, with the account of the run that produced them."""

    name: str
    scores: ItemScores
    account: Account

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError(f"arm {self.name!r} needs an Account, got {type(self.account).__name__}")
        if not isinstance(self.scores, Mapping):
            raise TypeError(f"arm {self.name!r} scores must map item id -> score")
        object.__setattr__(self, "scores", MappingProxyType(dict(self.scores)))


@dataclass(frozen=True)
class Requirement:
    """The baselines a component kind must beat, and the budget fields they must match."""

    baselines: tuple[str, ...]
    match: tuple[str, ...] = ()
    same_information: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "baselines", tuple(self.baselines))
        object.__setattr__(self, "match", tuple(self.match))
        if not self.baselines:
            raise ValueError("a requirement needs at least one baseline")
        unknown = [name for name in self.match if name not in BUDGET_FIELDS]
        if unknown:
            raise ValueError(f"unknown budget fields {unknown}; choose from {BUDGET_FIELDS}")


# The design's baseline table (design/04-architecture.md, "Baselines (serious ones)").
# Every listed baseline must match the listed budget fields, so a baseline that
# cannot use a budget (for example no-thinking vs compute) is optional, not required.
REQUIREMENTS: dict[str, Requirement] = {
    # Same-encoder retrieval and a kNN external memory, equal retrieval budget and retrieved tokens.
    "episode_cards": Requirement(
        baselines=("same_encoder_retrieval", "knn_memory"),
        match=("flops", "retrieved_items", "retrieved_tokens"),
    ),
    # Core with equal parameters and compute; core + replay; external-memory-only; hash routing.
    "knowledge_slots": Requirement(
        baselines=("core_equal_params", "core_replay", "external_memory_only", "hash_routing"),
        match=("parameters", "flops", "train_tokens"),
    ),
    # FIFO, LRU, reservoir, surprise-only and teacher-flag-only gating at the same budget.
    "gating": Requirement(
        baselines=("fifo", "lru", "reservoir", "surprise_only", "teacher_flag_only"),
        match=("train_tokens", "updates", "retrieved_items", "retrieved_tokens"),
    ),
    # Fixed-K thinking at the same average compute (no-thinking may be added, but is not enough).
    "thinking_stop": Requirement(baselines=("fixed_k_thinking",), match=("flops",)),
    # Core + replay and external-memory-only, at equal tokens, updates and compute.
    "continual_learner": Requirement(
        baselines=("core_replay", "external_memory_only"),
        match=("train_tokens", "updates", "flops"),
    ),
    # An age-matched model given equal tokens, updates and compute on irrelevant or permuted
    # experience; its information differs by construction.
    "transfer": Requirement(
        baselines=("age_matched",),
        match=("train_tokens", "updates", "flops"),
        same_information=False,
    ),
    # Step 0 toy: the card store must beat a plain lookup over the same context with the
    # same retrieval budget (a stand-in for "same-encoder retrieval").
    "toy_store": Requirement(
        baselines=("plain_lookup",),
        match=("retrieved_items", "retrieved_tokens"),
    ),
}


@dataclass(frozen=True)
class Component:
    """A named part of the system, how to lesion it, and a fingerprint of what the lesion touches."""

    name: str
    kind: str
    lesion: Callable[[], AbstractContextManager[Any]]
    state: Callable[[], str]


@dataclass
class Verdict:
    """Every number behind a judgement; `passed` iff no reason was recorded."""

    component: str
    kind: str
    n_items: int = 0
    min_effect: float = 0.0
    alpha: float = ALPHA
    gain_fraction: float = LESION_GAIN_FRACTION
    full: Optional[float] = None
    lesioned: Optional[float] = None
    repeatable: Optional[bool] = None
    lesion_active: Optional[bool] = None
    lesion_restored: Optional[bool] = None
    baseline_means: dict[str, float] = field(default_factory=dict)
    baseline_pvalues: dict[str, float] = field(default_factory=dict)
    refused: dict[str, list[str]] = field(default_factory=dict)
    missing_baselines: list[str] = field(default_factory=list)
    best_baseline: Optional[str] = None
    beats_baselines: bool = False
    gain: Optional[float] = None
    lesion_drop: Optional[float] = None
    lesion_fraction: Optional[float] = None
    lesion_gain_pvalue: Optional[float] = None
    lesion_removes_gain: bool = False
    destructive_overshoot: Optional[float] = None
    destructive_pvalue: Optional[float] = None
    destructive: bool = False
    trained_without: Optional[float] = None
    trained_without_pvalue: Optional[float] = None
    accounts: dict[str, dict[str, Any]] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.reasons

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["passed"] = self.passed
        return out


def _preview(values: Sequence[str], limit: int = 5) -> str:
    shown = ", ".join(repr(v) for v in list(values)[:limit])
    return shown + (f" (+{len(values) - limit} more)" if len(values) > limit else "")


def _score_problems(scores: Any, items: Sequence[str]) -> list[str]:
    """Why `scores` is not exactly one score in [0, 1] for each of `items`."""
    if not isinstance(scores, Mapping):
        return [f"returned {type(scores).__name__}, not a mapping of item id -> score"]
    problems = []
    wanted = set(items)
    missing = [item for item in items if item not in scores]
    extra = sorted(str(key) for key in scores if key not in wanted)
    if missing:
        problems.append(f"missing {len(missing)} item(s): {_preview(missing)}")
    if extra:
        problems.append(f"{len(extra)} unrequested item(s): {_preview(extra)}")
    invalid = []
    for item in items:
        if item not in scores:
            continue
        value = scores[item]
        if isinstance(value, bool):
            continue
        if (
            not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0.0 <= value <= 1.0
        ):
            invalid.append(item)
    if invalid:
        problems.append(f"{len(invalid)} score(s) not finite numbers in [0, 1]: {_preview(invalid)}")
    return problems


def _close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance * max(abs(a), abs(b))


def _arm_problems(
    arm: Any,
    items: Sequence[str],
    full_account: Account,
    requirement: Requirement,
    tolerance: float,
) -> list[str]:
    """Why this arm may not be compared with the full system."""
    if not isinstance(arm, Arm):
        return [f"not an Arm but {type(arm).__name__}"]
    problems = [f"scores: {problem}" for problem in _score_problems(arm.scores, items)]
    if arm.account.run_id == full_account.run_id:
        problems.append(f"shares run id {arm.account.run_id!r} with the full system")
    for name in requirement.match:
        mine, theirs = getattr(full_account, name), getattr(arm.account, name)
        if not _close(mine, theirs, tolerance):
            problems.append(f"budget mismatch: {name} {theirs} vs full {mine} (tolerance {tolerance:g})")
    if requirement.same_information and arm.account.information != full_account.information:
        problems.append(
            f"information {sorted(arm.account.information)} vs full {sorted(full_account.information)}"
        )
    return problems


def _capture_rng() -> dict[str, Any]:
    state: dict[str, Any] = {"python": random.getstate(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        state["cuda"] = torch.cuda.get_rng_state_all()
    return state


def _restore_rng(state: Mapping[str, Any]) -> None:
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"])
    if "cuda" in state:
        torch.cuda.set_rng_state_all(state["cuda"])


def _check_settings(
    min_effect: float, alpha: float, min_items: int, gain_fraction: float, tolerance: float
) -> None:
    if (
        isinstance(min_effect, bool)
        or not isinstance(min_effect, (int, float))
        or not math.isfinite(min_effect)
        or min_effect <= 0
    ):
        raise ValueError(f"min_effect must be a finite number > 0, got {min_effect!r}")
    if not isinstance(alpha, (int, float)) or not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie strictly between 0 and 1, got {alpha!r}")
    if isinstance(min_items, bool) or not isinstance(min_items, int) or min_items < 1:
        raise ValueError(f"min_items must be a positive integer, got {min_items!r}")
    if not isinstance(gain_fraction, (int, float)) or not 0.0 < gain_fraction <= 1.0:
        raise ValueError(f"gain_fraction must lie in (0, 1], got {gain_fraction!r}")
    if not isinstance(tolerance, (int, float)) or not 0.0 <= tolerance < 1.0:
        raise ValueError(f"budget_tolerance must lie in [0, 1), got {tolerance!r}")


def _evaluate(
    evaluate: Evaluate,
    items: tuple[str, ...],
    rng: Mapping[str, Any],
    label: str,
    reasons: list[str],
) -> Optional[dict[str, float]]:
    """One evaluation from the same RNG state; None (with a reason) if it broke the protocol."""
    _restore_rng(rng)
    scores = evaluate(items)
    problems = _score_problems(scores, items)
    if problems:
        reasons.append(f"{label} evaluation: " + "; ".join(problems))
        return None
    return {item: float(scores[item]) for item in items}


def judge_component(
    component: Component,
    evaluate: Evaluate,
    items: Sequence[str],
    full_account: Account,
    baselines: Mapping[str, Arm],
    *,
    min_effect: float,
    trained_without: Optional[Arm] = None,
    alpha: float = ALPHA,
    min_items: int = MIN_ITEMS,
    gain_fraction: float = LESION_GAIN_FRACTION,
    budget_tolerance: float = BUDGET_TOLERANCE,
) -> Verdict:
    """Judge one component; every failure or refusal is a reason in the returned Verdict.

    `evaluate(items)` must score exactly the given item IDs, deterministically.
    Global python/torch RNG is reset to the same state before every call and
    restored afterwards, so evaluation randomness is paired across arms.
    `trained_without`, when supplied, must be beaten by `min_effect` as well;
    it is mandatory when the lesion is destructive.
    """
    _check_settings(min_effect, alpha, min_items, gain_fraction, budget_tolerance)
    if component.kind not in REQUIREMENTS:
        raise ValueError(f"unknown component kind {component.kind!r}; known: {sorted(REQUIREMENTS)}")
    if not isinstance(full_account, Account):
        raise TypeError("full_account must be an Account")
    if isinstance(items, str):
        raise TypeError("items must be a sequence of item IDs, not one string")
    requirement = REQUIREMENTS[component.kind]
    reasons: list[str] = []
    verdict = Verdict(
        component=component.name,
        kind=component.kind,
        min_effect=float(min_effect),
        alpha=float(alpha),
        gain_fraction=float(gain_fraction),
        reasons=reasons,
    )
    verdict.accounts["full"] = full_account.as_dict()

    # 1. Items: unique string IDs, enough of them.
    requested = list(items)
    not_str = [item for item in requested if not isinstance(item, str)]
    if not_str:
        raise TypeError(f"item IDs must be strings, got {_preview([repr(x) for x in not_str])}")
    ids = tuple(dict.fromkeys(requested))
    verdict.n_items = len(ids)
    if len(ids) != len(requested):
        reasons.append(f"item IDs are not unique: {len(requested) - len(ids)} duplicate(s)")
    if len(ids) < min_items:
        reasons.append(f"only {len(ids)} item(s); at least {min_items} are needed for a verdict")
    if not ids:
        return verdict

    # 2. Baselines: required ones present; every supplied arm aligned, budget- and information-matched.
    verdict.missing_baselines = [name for name in requirement.baselines if name not in baselines]
    if verdict.missing_baselines:
        reasons.append(
            f"refused: missing required baseline(s) for {component.kind!r}: {verdict.missing_baselines}"
        )
    accepted: dict[str, Arm] = {}
    for name, arm in baselines.items():
        problems = _arm_problems(arm, ids, full_account, requirement, budget_tolerance)
        if isinstance(arm, Arm):
            verdict.accounts[f"baseline:{name}"] = arm.account.as_dict()
            if arm.name != name:
                problems.append(f"registered as {name!r} but the arm is named {arm.name!r}")
        if problems:
            verdict.refused[name] = problems
            reasons.append(f"refused baseline {name!r}: " + "; ".join(problems))
        else:
            accepted[name] = arm
    control_ok = False
    if trained_without is not None:
        problems = _arm_problems(trained_without, ids, full_account, requirement, budget_tolerance)
        if isinstance(trained_without, Arm):
            verdict.accounts["trained_without"] = trained_without.account.as_dict()
        if problems:
            verdict.refused["trained_without"] = problems
            reasons.append("refused control trained without the component: " + "; ".join(problems))
        else:
            control_ok = True

    # 3. Evaluation protocol: full, lesioned, full again, with state fingerprints around the lesion.
    rng = _capture_rng()
    try:
        full = _evaluate(evaluate, ids, rng, "full", reasons)
        before = component.state()
        with component.lesion():
            during = component.state()
            lesioned = _evaluate(evaluate, ids, rng, "lesioned", reasons)
        after = component.state()
        repeat = _evaluate(evaluate, ids, rng, "repeated full", reasons)
    finally:
        _restore_rng(rng)
    verdict.lesion_active = during != before
    verdict.lesion_restored = after == before
    if not verdict.lesion_active:
        reasons.append("lesion changed no component state while active (state fingerprint unchanged)")
    if not verdict.lesion_restored:
        reasons.append("lesion did not restore component state on exit")
    if full is not None and repeat is not None:
        changed = [item for item in ids if full[item] != repeat[item]]
        verdict.repeatable = not changed
        if changed:
            reasons.append(
                f"evaluation not repeatable: {len(changed)} item score(s) differ between the two full runs: "
                + _preview(changed)
            )
    else:
        verdict.repeatable = False
    if full is None or lesioned is None:
        return verdict

    f = [full[item] for item in ids]
    les = [lesioned[item] for item in ids]
    verdict.full, verdict.lesioned = mean(f), mean(les)

    # 4. Beat every accepted baseline by min_effect.
    for name, arm in accepted.items():
        b = [float(arm.scores[item]) for item in ids]
        p = paired_greater_pvalue(f, b, margin=min_effect)
        verdict.baseline_means[name] = mean(b)
        verdict.baseline_pvalues[name] = p
        if p >= alpha:
            reasons.append(
                f"does not beat {name!r} by min_effect {min_effect:g}: "
                f"full {verdict.full:.4f} vs {mean(b):.4f}, p={p:.3g}"
            )
    verdict.beats_baselines = (
        bool(accepted)
        and not verdict.missing_baselines
        and len(accepted) == len(baselines)
        and all(p < alpha for p in verdict.baseline_pvalues.values())
    )
    if not accepted:
        reasons.append("no usable baseline, so the lesion gain cannot be judged")
        return verdict

    # 5. The lesion removes at least gain_fraction of the advantage over the best baseline, per item.
    best = max(accepted, key=lambda name: verdict.baseline_means[name])
    verdict.best_baseline = best
    bb = [float(accepted[best].scores[item]) for item in ids]
    verdict.gain = verdict.full - verdict.baseline_means[best]
    verdict.lesion_drop = verdict.full - verdict.lesioned
    verdict.lesion_fraction = verdict.lesion_drop / verdict.gain if verdict.gain > 0 else None
    d = [(fi - li) - gain_fraction * (fi - bi) for fi, li, bi in zip(f, les, bb)]
    verdict.lesion_gain_pvalue = paired_permutation_greater(d)
    verdict.lesion_removes_gain = verdict.lesion_gain_pvalue < alpha
    if not verdict.lesion_removes_gain:
        reasons.append(
            f"lesion does not remove {gain_fraction:.0%} of the gain over {best!r}: "
            f"drop {verdict.lesion_drop:.4f} of gain {verdict.gain:.4f}, p={verdict.lesion_gain_pvalue:.3g}"
        )

    # 6. A destructive lesion (far below the best baseline) needs a control trained without the component.
    verdict.destructive_overshoot = verdict.baseline_means[best] - verdict.lesioned
    verdict.destructive_pvalue = paired_greater_pvalue(bb, les, margin=min_effect)
    verdict.destructive = verdict.destructive_pvalue < alpha
    if verdict.destructive and trained_without is None:
        reasons.append(
            f"destructive lesion: lesioned system falls {verdict.destructive_overshoot:.4f} below "
            f"{best!r} (p={verdict.destructive_pvalue:.3g}); supply a control trained without the component"
        )
    if trained_without is not None and control_ok:
        tw = [float(trained_without.scores[item]) for item in ids]
        verdict.trained_without = mean(tw)
        verdict.trained_without_pvalue = paired_greater_pvalue(f, tw, margin=min_effect)
        if verdict.trained_without_pvalue >= alpha:
            reasons.append(
                "does not beat the control trained without the component by "
                f"min_effect {min_effect:g}: full {verdict.full:.4f} vs "
                f"{verdict.trained_without:.4f}, p={verdict.trained_without_pvalue:.3g}"
            )
    return verdict


__all__ = [
    "BUDGET_FIELDS",
    "REQUIREMENTS",
    "Account",
    "Arm",
    "Component",
    "Evaluate",
    "ItemScores",
    "Requirement",
    "Verdict",
    "judge_component",
]
