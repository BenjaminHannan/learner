#!/usr/bin/env python3
"""Exp 261 -- candidate prompt variant B (sealed only if it wins the dev A/B;
otherwise left unused). Same fixed question as canon.build_prompt, plus two
targeted NO clauses found on dev: filler/chat words rendered into the fact,
and confirmation-seeking turns stated as fact.

Variant B question text (temperature 0, thinking off, same transport).
"""
from __future__ import annotations


def build_prompt_b(turn: str, claim: str) -> str:
    return (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        f"Claim: {str(claim).strip()}\n"
        "Does the message state this claim as a real, current fact that the "
        "speaker is telling (not checking, not pretending, not planning)?\n"
        "Answer NO if any of these holds:\n"
        "- the claim is only asked about, checked or confirmed (including "
        "a tag like \"..., right\", \"..., isn't it\", \"..., yeah?\", or "
        "a \"so ...\" confirmation), even without \"?\";\n"
        "- the claim is pretend or hypothetical (\"let's say\", \"imagine\", "
        "\"suppose\", \"what if\", \"pretend\", \"say that\");\n"
        "- the claim is a plan, goal or wish (\"training to be\", "
        "\"wants to\", \"hoping to\", \"is going to\", \"plans to\", "
        "\"will start\");\n"
        "- the claim is denied by the message;\n"
        "- the claim is about a different person than the message says;\n"
        "- the claim carries filler or chat words from the message into the "
        "fact itself (such as \"btw\", \"yeah\", \"or nah\", \"sorry\").\n"
        "Otherwise answer YES.\n"
        "Answer with one word: YES or NO.\n"
        "Answer:"
    )
