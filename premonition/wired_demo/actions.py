"""Action record decoded from the heads (or given by the toy world as a gold label).

claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Action:
    kind: str                  # CALC | NOTE_WRITE | ANSWER | DONE
    op: str | None = None      # ADD | SUB | MUL | DIV           (CALC)
    ptr_a: int | None = None   # registry index                  (CALC, ANSWER)
    ptr_b: int | None = None   # registry index                  (CALC)
    slot: int | None = None    # slot index, len(slots) = NEW    (NOTE_WRITE)
    start: int | None = None   # question token span, inclusive  (NOTE_WRITE)
    end: int | None = None
