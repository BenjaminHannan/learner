#!/usr/bin/env python3
"""Experiment 120d — don't-know routing fix for the talker mouth (additive only).

Director finding (verified 05:52): wire51's 40-turn chat replay with the
mask-fixed talker as the mouth gives 0 wrong writes, 12/12 correct, 6/6
two-hop, but abstentions 1 vs wire51's 3. The two missed turns:

  "Where is Zed's city?"      -> talker "I don't know Zed's city."
                                 (wire51: "I don't know anyone called Zed.")
  "Where is Ana's city's mother?" -> talker "I don't know Porto's city -- ..."
                                 (wire51: "Ana's city is Porto, which is not
                                  someone I can look up.")

Step-1 cause (file:line):
  * Zed turn: Notebook.ask falls through to resolve miss,
    scripts/fable_notebook_contract.py:238
    ``return Result(UNKNOWN_ENTITY, {"name": name})``.
  * Ana turn: the hop loop hits a literal value (Porto, no "entity" key),
    scripts/fable_notebook_contract.py:405
    ``return Result(BROKEN_CHAIN, {...})``.
    Contract templates (same file, lines 81/83) give exactly wire51's two
    sentences.
  * The talker's training records use only six statuses
    (scripts/fable_talker120_data.py:251-252 TEMPLATES keys; mix lines
    256-261; also scripts/fable_talker120_mouth.py:19):
    OK, UNKNOWN, ABSTAIN, CLARIFY, SAVED, FORGOT. UNKNOWN_ENTITY and
    BROKEN_CHAIN never appear in training.
  * scripts/fable_talker120_mouth.py:177-208 fallback_say knows only the six
    and ends with ``return ""`` (line 208) for anything else; say_raw
    (lines 397-404) and say (lines 406-422) also return "" for non-answer
    kinds, and brake_check (lines 215-216) rejects empty decodes. Hence the
    silence on both turns (older talker120 ckpt said "" on both).
  * Why the brake PASSED "I don't know Porto's city -- that is beyond what I
    was taught.": brake_check is an allowlist, not a status match. Every word
    is allowed: porto/city/mother come from the record (name Ana, relations
    [city, mother], fields subject Ana / relation city / value Porto) via
    record_content_words, and beyond/taught are in the FUNCTION_WORDS
    extension (mouth.py lines 94-98). classify() reads UNKNOWN, but nothing
    compares that to the record's BROKEN_CHAIN, so the unfaithful sentence
    (drops "mother", invents "city") passes.

THE ONE CHANGE here (vs 120c, which still decoded first and only fixed the
fallback): this module imports (never edits) fable_talker120_mouth and
subclasses TalkerMouth so that any answer record whose status is NOT in the
six training statuses goes STRAIGHT to the notebook-contract template
``C.Result(status, fields).say()`` — no talker decode at all, never an empty
string. The six trained statuses go through the talker + brake exactly as now
(inherited say path, inherited fallback for those six).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402
import fable_talker120_mouth as M120  # noqa: E402

# Statuses present in the talker120 training records
# (scripts/fable_talker120_data.py:251-252, mix lines 256-261).
SIX_STATUSES = frozenset({"OK", "UNKNOWN", "ABSTAIN", "CLARIFY", "SAVED", "FORGOT"})


def contract_say(record: dict) -> str:
    """Notebook-contract sentence for any answer record; never ""."""
    kind = record.get("kind")
    if kind in ("write", "clarify", "note"):
        return record.get("text", "")
    if kind != "answer":
        return ""
    status = record.get("status")
    try:
        s = C.Result(status, dict(record.get("fields") or {})).say()
    except Exception:
        s = ""
    if not s:
        # Result.say falls back to str(status) on unknown statuses, but guard
        # anyway so this path can never be silent.
        s = str(status) if status else "I can't answer that."
    return s


def fallback_say_d(record: dict) -> str:
    """120 fallback for the six, contract template for everything else."""
    if record.get("kind") == "answer" and record.get("status") not in SIX_STATUSES:
        return contract_say(record)
    return M120.fallback_say(record)


class _ContractFallbackMouth:
    """say(record) -> str via fallback_say_d (same Protocol shape as the 120
    mouth's _FallbackMouth). Belt-and-braces: say() below short-circuits
    non-six statuses before any decode, so this only matters if called
    directly."""

    def say(self, record: dict) -> str:
        return fallback_say_d(record)


class Talker120dMouth(M120.TalkerMouth):
    """120 mouth + no-decode contract routing for non-six statuses.

    Only change vs the inherited mouth: say() short-circuits answer records
    with untrained statuses straight to the contract template (no decode, no
    brake, never ""). Everything else — _decode_raw, say_raw, the six-status
    say path with brake + fallback, says/fallbacks/reasons accounting — is
    inherited verbatim. wire51 files untouched.
    """

    def __init__(self, ckpt_path=None, tok_path=None) -> None:
        super().__init__(ckpt_path, tok_path)
        self._fallback = _ContractFallbackMouth()
        self.contract_routed = 0

    def say(self, record: dict, max_new: int = 32) -> str:
        if record.get("kind") == "answer" and record.get("status") not in SIX_STATUSES:
            self.says += 1
            self.contract_routed += 1
            return contract_say(record)
        return super().say(record, max_new=max_new)
