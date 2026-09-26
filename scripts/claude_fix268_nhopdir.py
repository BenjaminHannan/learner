"""Exp 268 THE ONE CHANGE: n-hop direction guard (question side only).

Cause (design/v3/30-modes/268-nhop-direction-guard.md; diagnosis
artifacts/claude-nhopdiag-20260923/DIAG.md): after teaching a chain
A R B + B R V on a cued relation, a backwards question about the middle
value V ("Whose spouse is V?", "Who is married to V?",
"What has V written?", "What did V found?") is claimed by
scripts/fable_bench92_english_arm.py compose_n_hop, which takes the single
mentioned entity as `start` and walks only forward, with a coverage gate
that checks the relation is mentioned but never its direction. The reply
is V's own forward fact. Stored facts are never damaged; only the reply.

THE RULE (question side only; teach/correct/forget/ask paths untouched):
after the sealed compose_n_hop returns (start, rels), detect a
REVERSE-shaped question about `start` -- the value slot -- and return None
so the turn falls through UNCHANGED to the layers below (190 reverse /
153 reverse / table paths), which already answer these shapes. Forward
n-hop questions are untouched. No writes (this stage only suppresses a
frame; clarify/ask actions downstream never write on questions).

Reverse shapes about START (case-insensitive, trailing "?" required):
  R1 "Whose <R> is|was START?"            (any R; definitionally reverse)
  R2 "Who is|was|are|were <w> to START?"  where <w> is "married" or a cue
       of one of the walked relations (the relation's own participle)
  R3 "Who has START as their|his|her|its <R>?"
  R4 "What has|have|had|did START <verb>...?" where the remainder names
       the relation's own verb (a cue substring of a walked relation, the
       same substring semantics as the composer gate) and carries no
       forward marker ("'s", " of ", relative cues).

Installed process-locally by rebinding the module global
fable_bench92_english_arm.compose_n_hop (the same pattern 228 uses for
fix170's _src_of): no existing file is edited. The rebind is safe because
every question-side caller in the agent process reaches the composer by
module attribute (scripts/fable_loop138_agent.py:122
`B92.compose_n_hop(...)`); the composer has no other in-process callers
on the question path.

Falsifier: any reverse_chain item still answered with V's own forward
fact, any forward n-hop reply change, or any new wrong value.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench92_english_arm as B92  # noqa: E402 (rebound leaf, read-only)

_ORIG_COMPOSE_N_HOP = B92.compose_n_hop
_INSTALLED = False

STAGE268 = "nhopdir268-guard"

# Remainder markers that make a what-has/did shape forward-looking
# (possessive / partitive / relative clause): never blocked.
_FORWARD_MARKERS = ("'s", "\u2019s", " of ", " that ", " who ", " which ",
                    " where ", " and ", ",", ";")


def _norm(text: str) -> str:
    return " ".join(str(text).split())


def _cues_of(rels) -> set[str]:
    out: set[str] = set()
    for r in rels or []:
        for cue in B92.REL_CUES92.get(r, []):
            out.add(str(cue).lower())
    return out


def reverse_shape268(question: str, start: str,
                     rels) -> str | None:
    """(question, composer start, walked rels) -> shape tag or None.

    Pure predicate: no notebook access, no writes. Returns one of
    "R1-whose" | "R2-married-to" | "R3-who-has-as" | "R4-what-verb"
    when the question is backwards-shaped about `start`.
    """
    q = _norm(question)
    if not q.rstrip().endswith("?"):
        return None
    body = q.rstrip()[:-1].strip()
    slow = _norm(start).lower().strip().rstrip(".")
    if not slow:
        return None
    esc = re.escape(slow)
    # R1: "Whose <R> is|was START?"
    if re.fullmatch(r"whose\s+.+\s+(?:is|was)\s+" + esc, body,
                    re.IGNORECASE | re.DOTALL):
        return "R1-whose"
    # R2: "Who is|was|are|were <w> to START?" with the relation's own word.
    m = re.fullmatch(r"who\s+(?:is|was|are|were)\s+(\w+)\s+to\s+" + esc,
                     body, re.IGNORECASE | re.DOTALL)
    if m:
        w = m.group(1).lower()
        if w == "married" or w in _cues_of(rels):
            return "R2-married-to"
        return None
    # R3: "Who has START as their|his|her|its <R>?"
    if re.fullmatch(r"who\s+has\s+" + esc
                    + r"\s+as\s+(?:their|his|her|its)\s+.+",
                    body, re.IGNORECASE | re.DOTALL):
        return "R3-who-has-as"
    # R4: "What has|have|had|did START <verb>...?" with the relation's own
    # verb in the remainder and no forward marker.
    m = re.fullmatch(r"what\s+(?:has|have|had|did)\s+" + esc + r"\s+(.+)",
                     body, re.IGNORECASE | re.DOTALL)
    if m:
        rest = m.group(1).lower()
        low = f" {rest} "
        if any(mark in low or mark in rest for mark in _FORWARD_MARKERS):
            return None
        cues = _cues_of(rels)
        if any(cue and cue in rest for cue in cues):
            return "R4-what-verb"
        return None
    return None


_N_BLOCKED = 0
_LAST_SHAPE = ""


def compose_n_hop268(question: str, triples):
    """Sealed compose_n_hop + the direction guard (None on reverse)."""
    global _N_BLOCKED, _LAST_SHAPE
    frame = _ORIG_COMPOSE_N_HOP(question, triples)
    if frame is None:
        return None
    start, rels = frame
    shape = reverse_shape268(question, start, list(rels))
    if shape is not None:
        _N_BLOCKED += 1
        _LAST_SHAPE = shape
        return None
    return frame


def install_nhopdir268() -> None:
    """Rebind B92.compose_n_hop process-locally (idempotent)."""
    global _INSTALLED
    if _INSTALLED:
        return
    B92.compose_n_hop = compose_n_hop268
    _INSTALLED = True


def is_installed() -> bool:
    return _INSTALLED and B92.compose_n_hop is compose_n_hop268


def block_stats() -> dict:
    return {"n_blocked": _N_BLOCKED, "last_shape": _LAST_SHAPE}


def selftest268() -> int:
    fails: list[str] = []
    rels_sp = ["spouse"]
    rels_au = ["author"]
    rels_fo = ["founder"]

    def check(got, want, tag):
        ok = (got == want)
        print(("ok  " if ok else "FAIL"), tag, repr(got))
        if not ok:
            fails.append(tag)

    # reverse shapes fire
    check(reverse_shape268("Whose spouse is Dana Holt?", "Dana Holt",
                           rels_sp), "R1-whose", "r1")
    check(reverse_shape268("Whose spouse was Dana Holt?", "Dana Holt",
                           rels_sp), "R1-whose", "r1-was")
    check(reverse_shape268("Whose husband is Bex Marlowe?", "Bex Marlowe",
                           rels_sp), "R1-whose", "r1-husband")
    check(reverse_shape268("Whose author is Petra Quinn?", "Petra Quinn",
                           rels_au), "R1-whose", "r1-author")
    check(reverse_shape268("Who is married to Dana Holt?", "Dana Holt",
                           rels_sp), "R2-married-to", "r2")
    check(reverse_shape268("Who was married to Bram Kolb?", "Bram Kolb",
                           rels_sp), "R2-married-to", "r2-was")
    check(reverse_shape268("Who has Bram Kolb as their spouse?",
                           "Bram Kolb", rels_sp), "R3-who-has-as", "r3")
    check(reverse_shape268("Who has Cleo Drane as her spouse?",
                           "Cleo Drane", rels_sp), "R3-who-has-as", "r3-her")
    check(reverse_shape268("What has Dana Holt written?", "Dana Holt",
                           rels_au), "R4-what-verb", "r4-author")
    check(reverse_shape268("What had Ines Halvors written?",
                           "Ines Halvors", rels_au), "R4-what-verb",
          "r4-had")
    check(reverse_shape268("What did Sela Voss found?", "Sela Voss",
                           rels_fo), "R4-what-verb", "r4-founder")
    check(reverse_shape268("What has Liora Sen founded?", "Liora Sen",
                           rels_fo), "R4-what-verb", "r4-founded")
    # forward shapes never fire
    check(reverse_shape268("Who is Bex Marlowe's spouse?", "Bex Marlowe",
                           rels_sp), None, "fwd-possessive")
    check(reverse_shape268("Who is Bex Marlowe married to?", "Bex Marlowe",
                           rels_sp), None, "fwd-married-to")
    check(reverse_shape268("Who is Bram Kolb married to?", "Bram Kolb",
                           rels_sp), None, "fwd-married-to-2")
    check(reverse_shape268("Who is Bram Kolb's husband?", "Bram Kolb",
                           rels_sp), None, "fwd-husband")
    check(reverse_shape268("Who wrote Salt Harbor?", "Salt Harbor",
                           rels_au + rels_au), None, "fwd-wrote")
    check(reverse_shape268("Who founded Ember Bay?", "Ember Bay",
                           rels_fo + rels_fo), None, "fwd-founded")
    check(reverse_shape268("Who founded Liora Sen?", "Liora Sen",
                           rels_fo), None, "fwd-founded-value")
    check(reverse_shape268("Who is Ines Halvors's author?", "Ines Halvors",
                           rels_au), None, "fwd-author-poss")
    check(reverse_shape268("Who is Priya Nair's employer?", "Priya Nair",
                           ["employer"]), None, "fwd-employer")
    check(reverse_shape268("Who is the head of the government of Detroit?",
                           "Detroit", ["head_of_government"]), None,
          "fwd-mquake")
    check(reverse_shape268("What has Petra Quinn's author written?",
                           "Petra Quinn", rels_au), None,
          "fwd-relative-possessive")
    check(reverse_shape268("Did Petra Quinn write Salt Harbor?",
                           "Petra Quinn", rels_au), None, "yn-2subj")
    check(reverse_shape268("Whose spouse is Dana Holt", "Dana Holt",
                           rels_sp), None, "no-question-mark")
    print(f"selftest268 {len(fails)} fails")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest268())
