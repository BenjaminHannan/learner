"""Step 0: prove each bench check catches a planted flaw and passes a clean case.

Nothing here measures learning. The paired checks live in `learnlab.checks`,
one module per bench area; Step 0 passes only if every one of them behaves.
An area whose checks crash counts as failed, with the error recorded.
"""
from __future__ import annotations

import importlib
import math
import time
import traceback
from typing import Any

AREAS = ("readonly", "splits", "leaks", "ablation")


def run_area(area: str) -> tuple[list[dict[str, Any]], float]:
    started = time.monotonic()
    try:
        checks = importlib.import_module(f"learnlab.checks.{area}").checks()
    except Exception as error:  # a crashing area is a failed area, not a crashed bench
        checks = [{
            "check": f"{area}: checks ran",
            "passed": False,
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(limit=8),
        }]
    for item in checks:
        item.setdefault("area", area)
    return checks, time.monotonic() - started


def jsonable(value: Any) -> Any:
    """Evidence as strict JSON: sets sorted, tuples as lists, non-finite floats and objects as text."""
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((jsonable(item) for item in value), key=repr)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return repr(value)


def run_step0() -> dict[str, Any]:
    started = time.monotonic()
    checks: list[dict[str, Any]] = []
    seconds: dict[str, float] = {}
    for area in AREAS:
        area_checks, seconds[area] = run_area(area)
        checks.extend(area_checks)
    return jsonable({
        "step": 0,
        "status": "passed" if checks and all(c["passed"] for c in checks) else "failed",
        "checks": checks,
        "area_seconds": seconds,
        "elapsed_seconds": time.monotonic() - started,
    })


__all__ = ["AREAS", "jsonable", "run_area", "run_step0"]
