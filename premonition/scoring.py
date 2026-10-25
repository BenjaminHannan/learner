"""Answer scoring that needs no torch: exact match, plus step 1's plan rule for Q12 (`plan_get`).

`train.evaluate` counts a plan answer right when it equals the canonical string OR the oracle's `check_plan` can act it
out (`step1.plan_works`, design/05 5b). `train.judge` used exact match only; it calls `score_answer` when it is given plans.
`step1` is imported inside the function so this module itself imports no torch.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

Plan = tuple[Any, str, str]            # (world, person, item), as `step1.load_oracle` returns it


def score_answer(expected: str, said: str, plan: Optional[Plan] = None) -> tuple[bool, bool]:
    """(exact, correct): `exact` is `step1.exact_match`; `correct` is `exact`, or, given a plan, a non-empty `said` that
    `step1.plan_works` accepts. Without a plan the two are equal."""
    from learnlab import step1
    exact = step1.exact_match(said, expected)
    if exact or plan is None or not said:
        return exact, exact
    return exact, bool(step1.plan_works(plan, said))


def plan_counts(question_ids: list[str], exact: list[bool], correct: list[bool],
                plans: Optional[Mapping[str, Plan]]) -> dict[str, int]:
    """Q12 totals over a scored list. Only Q12 questions have a plan world, so `qid in plans` selects them."""
    mine = [i for i, qid in enumerate(question_ids) if plans and qid in plans]
    return {"q12_questions": len(mine), "q12_exact": sum(bool(exact[i]) for i in mine),
            "q12_plan_checked": sum(bool(correct[i]) for i in mine)}
