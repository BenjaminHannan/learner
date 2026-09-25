#!/usr/bin/env python3
"""381b: one follow-up to the stricter "is that right?" harness (month-end line, 2026-09-25). New file only.

381 (scripts/claude_e2e381_harness.py) gave 0 wrong "yes" on 73 held-out DEV questions but kept only 38/43 true
claims (VERIFY-381.md). 381b keeps 381's parser and adds four general rules for the causes found there:
  1. more alias groups (boss = manager = supervisor; sibling = sister/brother) and a claim that names the head
     word of a longer fact relation ("sister" for "twin sister", "dog" for "pet dog");
  2. an owner given as a relation word ("nan's dog", "your mum's cat") is resolved through the user's own facts;
  3. two family chains for the user: nephew/niece = a sibling's son/daughter, grandchild = a child's child;
  4. a shorter value that is the tail of the fact's value ("illustrator" for "freelance illustrator").
The 73 questions of 381's held-out set are now dev data for 381b.

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e381b_run.py <runner args>
"""
from __future__ import annotations

import re

import claude_e2e381_harness as H

H.ALIAS381.append({"boss", "manager", "supervisor"})
H.ALIAS381.append({"sibling", "sister", "brother"})
for _g in H.ALIAS381:
    if "grandmother" in _g:
        _g |= {"nan", "nana", "nanna", "nanny"}
SIBLING = {"sister", "brother", "sibling", "twin", "twin sister", "twin brother", "half sister", "half brother",
           "stepsister", "stepbrother"}
CHILD = {"son", "daughter", "child", "kid"}
CHAIN = {"nephew": ("son", "child"), "niece": ("daughter", "child"), "grandchild": CHILD, "grandson": ("son", "child"),
         "granddaughter": ("daughter", "child")}


def rel_match_b(claim: str, fact: str) -> bool:
    if H.rel_match(claim, fact):
        return True
    c, f = H.norm_rel(claim), H.norm_rel(fact)
    return bool(c) and c != "other" and len(f.split()) > 1 and f.split()[-1] == c


def value_match_b(want: str, have: str) -> bool:
    w, h = want.strip().lower(), have.strip().lower()
    return w == h or (len(h.split()) > len(w.split()) >= 1 and h.split()[-len(w.split()):] == w.split())


def _valid(truth, turn):
    return [f for f in truth if f["taught_turn"] <= turn
            and (f.get("valid_until_turn") is None or f["valid_until_turn"] > turn)]


def _owners(owner: str, valid: list[dict]) -> set[str]:
    """Fact owners the claim's owner can mean: USER, a name, or a relation word resolved through USER's facts."""
    o = owner.strip().lower()
    if o in H.YOUR:
        return {"USER"}
    if o.startswith("your "):
        o = o[5:]
    names = {str(f["owner"]) for f in valid if f["owner"] != "USER" and H.owner_match(o, str(f["owner"]))}
    names |= {str(f["value"]) for f in valid if f["owner"] == "USER" and rel_match_b(o, str(f["relation"]))}
    return names


def _match_owner(fact_owner: str, owners: set[str]) -> bool:
    if fact_owner == "USER":
        return "USER" in owners
    fo = fact_owner.lower()
    return any(fo == n.lower() or fo.split()[0] == n.lower().split()[0] for n in owners if n != "USER")


CHECK_B = re.compile(r"just to check: (?:is|are) (?P<rest>[^?]+?)\?\s*$")
OWNER_B = re.compile(r"(?P<o>your(?: [\w\u00c0-\u024f-]+?'s)?|[\w\u00c0-\u024f-]+(?: [\w\u00c0-\u024f-]+)?'s) (?P<tail>.+)$")


def parse381b(reply: str) -> list[tuple[str, str, str]]:
    """381's parse, plus every relation/value split of a "Just to check" question (381 split after one word)."""
    low = reply.lower()
    at = max(low.rfind(m) for m in H.MARKERS381)
    if at < 0:
        return []
    m = CHECK_B.match(low[at:].strip())
    if not m:
        one = H.parse381(reply)
        return [one] if one else []
    o = OWNER_B.match(m.group("rest"))
    if not o:
        return []
    owner = o.group("o")
    owner = owner[:-2] if owner.endswith("'s") else owner
    words = o.group("tail").split()
    return [(owner, " ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]


def confirm_answer381b(reply: str, truth: list[dict], turn_index: int) -> str:
    claims = parse381b(reply)
    return "yes" if any(_claim_true(c, truth, turn_index) for c in claims) else "no"


def _claim_true(claim, truth, turn_index) -> bool:
    owner, rel, val = claim
    want = H.values_of(val)
    if not want or not rel:
        return False
    valid = _valid(truth, turn_index)
    owners = _owners(owner, valid)
    have = [str(f["value"]) for f in valid
            if _match_owner(str(f["owner"]), owners) and rel_match_b(rel, str(f["relation"]))]
    r = H.norm_rel(rel)
    if not have and "USER" in owners and r in CHAIN:            # family chains through the user's own facts
        mids = [str(f["value"]) for f in valid if f["owner"] == "USER"
                and (H.norm_rel(f["relation"]) in (SIBLING if r in ("nephew", "niece") else CHILD))]
        have = [str(f["value"]) for f in valid if f["owner"] != "USER"
                and _match_owner(str(f["owner"]), set(mids)) and H.norm_rel(f["relation"]) in CHAIN[r]]
    return all(any(value_match_b(w, h) for h in have) for w in want)


def install381b() -> None:
    import claude_e2e336_run as R
    R.confirm_answer = confirm_answer381b
