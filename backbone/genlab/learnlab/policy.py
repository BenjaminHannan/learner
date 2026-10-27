"""Default statistical settings for every Step 0 decision, recorded in one place.

Experiments may make these stricter (smaller alpha, larger minimum effect or
item count) but should never loosen them without recording why in the design.
"""
from __future__ import annotations

ALPHA = 0.01                  # one-sided significance level for every pass/flag decision
MIN_ITEMS = 100               # minimum paired items for any component verdict
MIN_EFFECT = 0.03             # default minimum meaningful absolute effect (3 points); experiments may raise it, never set 0
LESION_GAIN_FRACTION = 0.5    # lesion must remove at least this fraction of the advantage over the best baseline
LEAK_MARGIN = 0.05            # leak detectors: effect-size margin above their own null
LEAK_MIN_ITEMS = 100          # below this a leak report is "insufficient", never "clean"
BUDGET_TOLERANCE = 0.05       # relative tolerance for equal-compute/equal-retrieval matching

__all__ = [
    "ALPHA",
    "BUDGET_TOLERANCE",
    "LEAK_MARGIN",
    "LEAK_MIN_ITEMS",
    "LESION_GAIN_FRACTION",
    "MIN_EFFECT",
    "MIN_ITEMS",
]
