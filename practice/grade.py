"""Exact, automatic grading for Practice-1. normalize(answer, answer_type) and is_correct(pred, gold, answer_type)."""
import re

TYPES = ("int", "str", "grid")


def _lines(s):
    return [" ".join(l.split()) for l in str(s).strip().splitlines()]


def normalize(answer, answer_type):
    """int -> int (or None if unparsable); str -> lowercase, whitespace collapsed; grid -> tuple of row strings with no spaces."""
    if answer_type == "int":
        s = str(answer).strip().replace(",", "").replace("_", "")
        m = re.fullmatch(r"[+-]?\d+(\.0+)?", s)
        return int(float(s)) if m else None
    if answer_type == "str":
        return " ".join(str(answer).strip().lower().split())
    if answer_type == "grid":
        s = str(answer).strip()
        if s.startswith("```"):
            s = s.strip("`").strip()
        rows = [re.sub(r"[\s,\[\]]", "", l) for l in s.splitlines()]
        rows = tuple(r for r in rows if r)
        return rows
    raise ValueError(f"bad answer_type {answer_type!r}")


def is_correct(pred, gold, answer_type):
    if pred is None:
        return False
    try:
        p, g = normalize(pred, answer_type), normalize(gold, answer_type)
    except Exception:
        return False
    if answer_type == "int":
        return p is not None and p == g
    if answer_type == "grid":
        return len(p) > 0 and p == g
    return p == g


def check(p, ans):
    """Grade one try of puzzle dict `p`: Reasoning Gym puzzles (src "rg") use their own checker, the rest is_correct."""
    if ans is None:
        return False
    if p.get("src") == "rg":
        from . import rg_pool
        return rg_pool.grade(p, ans)
    return is_correct(ans, p["answer"], p["answer_type"])
