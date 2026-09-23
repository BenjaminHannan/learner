#!/usr/bin/env python3
"""Experiment 120c — silence fix for the talker mouth (additive only).

Director finding: with our talker as the mouth, wire51's replay goes SILENT
(``said`` == ``""``) on "Where is Zed's city?" and "Where is Ana's city's
mother?", where wire51's TemplateMouth says "I don't know anyone called Zed."
and "Ana's city is Porto, which is not someone I can look up."

Cause: ``scripts/fable_talker120_mouth.py::fallback_say`` (lines 177-208)
knows only the six talker-training statuses (OK, UNKNOWN, ABSTAIN, CLARIFY,
SAVED, FORGOT) and ends with ``return ""`` for any other notebook status,
while wire51's ``TemplateMouth`` (``scripts/fable_wire51_adapters.py``,
lines 182-200) falls back to the notebook contract's own template
``C.Result(status, fields).say()`` for any non-OK answer status.

THE ONE CHANGE here: this module imports (never edits)
``fable_talker120_mouth`` and subclasses its ``TalkerMouth`` so that the
fallback for any status OUTSIDE the six uses the same contract template as
wire51's TemplateMouth — never an empty string. Decode path, brake,
six-status templates, and ``say_raw`` are inherited unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_talker120_mouth as M120  # noqa: E402

# The six statuses the talker was trained on; their templates stay exactly
# the 120 mouth's own (the contract does not know these names).
SIX_STATUSES = frozenset({"OK", "UNKNOWN", "ABSTAIN", "CLARIFY", "SAVED", "FORGOT"})


def fallback_say_c(record: dict) -> str:
    """120 fallback for the six, contract template for everything else."""
    kind = record.get("kind")
    if kind in ("write", "clarify", "note"):
        return record.get("text", "")
    if kind != "answer":
        return ""
    if record.get("status") in SIX_STATUSES:
        return M120.fallback_say(record)
    # Same contract template wire51's TemplateMouth uses (never "").
    return C.Result(record.get("status"), dict(record.get("fields") or {})).say()


class _ContractFallbackMouth:
    """say(record) -> str via fallback_say_c (same Protocol shape as the
    120 mouth's _FallbackMouth)."""

    def say(self, record: dict) -> str:
        return fallback_say_c(record)


class Talker120cMouth(M120.TalkerMouth):
    """120 mouth + contract-template fallback for non-six statuses.

    Only ``self._fallback`` is replaced; ``_decode_raw``, ``say_raw``,
    ``say`` (brake logic), ``says``/``fallbacks``/``reasons`` accounting are
    inherited verbatim, so the safety shape is unchanged.
    """

    def __init__(self, ckpt_path=None, tok_path=None) -> None:
        super().__init__(ckpt_path, tok_path)
        self._fallback = _ContractFallbackMouth()
