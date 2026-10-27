#!/usr/bin/env python3
"""381: a stricter simulated user for "is that right?" questions (month-end line, 2026-09-25). New file only.

Why: 336's harness (scripts/claude_e2e336_run.py:confirm_answer) says "yes" when the WHOLE reply names any true
value and its owner, whatever the relation. All 33 wrong saves in 336 came right after such a "yes"
(VERIFY-336.md). On DEV it said yes to "is your snack uriah?" (Uriah is the brother) and to "your roommate is
Zelda" (Zelda is the grandmother). A real person would say no.

What: confirm_answer381 reads only the confirm question (the text from the last "I think you told me" or
"Just to check:" to the end), parses owner, relation and value, and says "yes" only if one fact valid at that turn
has the same owner, a matching relation (alias groups below) and the same value(s). Anything it cannot parse is "no".

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e381_run.py <same args as claude_e2e336_run.py>
"""
from __future__ import annotations

import ast
import re

import claude_e2e336_run as R

ALIAS381 = [
    {"job", "occupation", "profession", "work"},
    {"employer", "work location", "workplace", "company", "works at", "work place"},
    {"school", "college", "university", "uni"},
    {"city", "town", "home city", "hometown", "home town", "lives in"},
    {"partner", "spouse", "husband", "wife", "girlfriend", "boyfriend", "fiance", "fiancee", "fiancé", "fiancée"},
    {"friend", "best friend", "buddy", "mate", "best mate", "old friend", "close friend"},
    {"coworker", "co-worker", "colleague", "workmate"},
    {"mother", "mom", "mum"},
    {"father", "dad"},
    {"child", "children", "kid", "kids", "son", "sons", "daughter", "daughters"},
    {"grandmother", "grandma", "gran", "granny"},
    {"grandfather", "grandpa", "granddad"},
]
PET381 = {"pet", "pets", "dog", "cat", "bird", "pet dog", "pet cat", "pet bird", "parrot", "parakeet", "hamster",
          "rabbit", "fish", "pet fish", "pet rabbit", "pet hamster", "puppy", "kitten", "horse", "pet horse"}
MARKERS381 = ("i think you told me", "just to check:")
YOUR = {"your", "you", "yours"}


def norm_rel(r: str) -> str:
    return re.sub(r"\s+", " ", str(r).lower().replace("_", " ").replace("-", " ")).strip()


def rel_match(claim: str, fact: str) -> bool:
    c, f = norm_rel(claim), norm_rel(fact)
    if not c or c == "other" or f == "other":
        return False
    if c == f or c.rstrip("s") == f.rstrip("s"):
        return True
    if c in PET381 and (f in PET381 or f.startswith("pet ")):
        return c in ("pet", "pets") or c == f or c in f.split() or f.endswith(" " + c)
    return any(c in g and f in g for g in ALIAS381)


def owner_match(claim_owner: str, fact_owner: str) -> bool:
    o = claim_owner.strip().lower()
    if o in YOUR:
        return fact_owner == "USER"
    if fact_owner == "USER":
        return False
    fo = fact_owner.lower()
    return o == fo or o == fo.split()[0]


def values_of(v: str) -> list[str]:
    v = v.strip().strip(".").strip()
    if v.startswith("[") and v.endswith("]"):
        try:
            got = ast.literal_eval(v)
            if isinstance(got, list):
                return [str(x).strip().lower() for x in got]
        except (ValueError, SyntaxError):
            pass
    return [v.lower()]


CLAIM_TOLD = re.compile(r"i think you told me (?P<o>your|[\w'À-ɏ -]+?)'s (?P<r>[\w \-]+?) (?:is|are) (?P<v>.+?),? is that right\??\s*$")
CLAIM_TOLD_YOUR = re.compile(r"i think you told me your (?P<r>[\w \-]+?) (?:is|are) (?P<v>.+?),? is that right\??\s*$")
CLAIM_CHECK = re.compile(r"just to check: (?:is|are) (?P<o>your|[\w'À-ɏ -]+?)(?:'s)? (?P<r>[\w \-]+?) (?P<v>[^?]+?)\?\s*$")


def parse381(reply: str):
    low = reply.lower()
    at = max(low.rfind(m) for m in MARKERS381)
    if at < 0:
        return None
    q = low[at:].strip()
    m = CLAIM_TOLD_YOUR.match(q)
    if m:
        return "your", m.group("r"), m.group("v")
    m = CLAIM_TOLD.match(q)
    if m:
        return m.group("o"), m.group("r"), m.group("v")
    m = CLAIM_CHECK.match(q)
    if m:
        o = m.group("o")
        if o.startswith("your "):                     # "is your best_mate Tavish?"
            return "your", o[5:] + " " + m.group("r"), m.group("v")
        return o, m.group("r"), m.group("v")
    return None


def confirm_answer381(reply: str, truth: list[dict], turn_index: int) -> str:
    claim = parse381(reply)
    if claim is None:
        return "no"
    owner, rel, val = claim
    want = values_of(val)
    valid = [f for f in truth if f["taught_turn"] <= turn_index
             and (f.get("valid_until_turn") is None or f["valid_until_turn"] > turn_index)
             and owner_match(owner, str(f["owner"])) and rel_match(rel, str(f["relation"]))]
    have = {str(f["value"]).strip().lower() for f in valid}
    return "yes" if want and all(w in have for w in want) else "no"


def install381() -> None:
    R.confirm_answer = confirm_answer381
