"""Step 0 paired checks, one module per bench area.

Each module exposes `checks() -> list[dict]`. Every check is paired in
spirit: a planted flaw must be caught and its clean control must not be
flagged. `step0.run_step0` runs them all.
"""
from __future__ import annotations

from typing import Any


def check(name: str, passed: bool, **detail: Any) -> dict[str, Any]:
    """One check result: its name, whether the bench behaved, and the evidence."""
    return {"check": name, "passed": bool(passed), **detail}


__all__ = ["check"]
