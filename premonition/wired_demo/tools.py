"""Calculator with the real registry rules: operands point only at question literals or earlier results.

Exact Fraction arithmetic, no floats. MUL and DIV are DEMO-ONLY extensions (the real pipeline has ADD/SUB).
claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re

MAX_LITERALS, MAX_RESULTS, MAX_CALLS, MAX_ABS = 8, 3, 4, 10 ** 6


@dataclass
class Entry:
    id: str
    value: Fraction
    token_indices: list      # rows of the question (literals) or of the tool-result segment (results)
    source: str              # "literal" | "result"
    char_span: tuple = None


@dataclass
class Trace:
    status: str              # "OK" | "ERROR"
    value: Fraction | None
    error_code: str | None
    op: str = ""
    ref_a: int = -1
    ref_b: int = -1


def build_registry(question: str, tok) -> list:
    """Integer literals of the question, in order, at most 8. token_indices point at question token rows."""
    ids, offsets = tok.encode(question)
    entries = []
    for row, (s, e) in enumerate(offsets):
        piece = question[s:e]
        if piece.isdigit() and len(entries) < MAX_LITERALS:
            entries.append(Entry(f"literal:{len(entries)}", Fraction(int(piece)), [row], "literal", (s, e)))
    return entries


def execute(op: str, ref_a: int, ref_b: int, registry: list, call_index: int) -> Trace:
    err = lambda code: Trace("ERROR", None, code, op, ref_a, ref_b)
    if call_index >= MAX_CALLS: return err("MAX_CALLS")
    if op not in ("ADD", "SUB", "MUL", "DIV"): return err("BAD_OP")
    if not (0 <= ref_a < len(registry)) or not (0 <= ref_b < len(registry)): return err("BAD_REFERENCE")
    if ref_a == ref_b: return err("DUPLICATE_REFERENCE")
    a, b = registry[ref_a].value, registry[ref_b].value
    if op == "DIV" and b == 0: return err("DIV_BY_ZERO")
    v = {"ADD": lambda: a + b, "SUB": lambda: a - b, "MUL": lambda: a * b, "DIV": lambda: a / b}[op]()
    assert isinstance(v, Fraction)
    if abs(v) > MAX_ABS: return err("VALUE_RANGE")
    return Trace("OK", v, None, op, ref_a, ref_b)


def render(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def parse(s: str) -> Fraction:
    return Fraction(s)
