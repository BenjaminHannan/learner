#!/usr/bin/env python3
"""Exp 261 -- speaker canonicaliser, claim renderer and checker prompt.

Additive-only: imports 257/235 modules read-only, never edits them.

Canonicaliser (brief section 1): for subjects of TEACH and ASK frames, map these
words to "me", ignoring case, before anything else (i.e. first of the NEW steps):
i, me, my, myself, mine, we, us, our, ours, ourselves. Nothing else changes.

ORDER NOTE (piloted 2026-09-22): the canonicaliser runs AFTER the brake, not
before it. The unchanged brake requires a literal span in the turn, so mapping
"Our" -> "me" first would drop the frame as subject_not_in_turn (verified:
brake keeps subject "Our" on "Our dog is Rex." but drops subject "me" on the
same turn). Canon-after-brake turns 257's "Our"-subject wrong saves into
speaker matches under the sealed scorer's FIRST set. ASK subjects too.
"""
from __future__ import annotations

CANON_WORDS = frozenset({
    "i", "me", "my", "myself", "mine",
    "we", "us", "our", "ours", "ourselves",
})

_ME = "me"


def canon_subject(subject: str) -> str:
    s = str(subject).strip()
    if s.lower() in CANON_WORDS:
        return _ME
    return subject


def canonicalise(frames):
    """Return a new list with TEACH/ASK subjects canonicalised. Never mutates."""
    out = []
    for f in frames:
        if isinstance(f, dict) and f.get("act") in ("TEACH", "ASK") and "subject" in f:
            g = dict(f)
            g["subject"] = canon_subject(f["subject"])
            out.append(g)
        else:
            out.append(f)
    return out


# ------------------------------------------------------------------ rendering
# Fixed templates written before the seal from relation table v2 names only
# (never from any panel). Default: "<S>'s <relation words> is <V>."
# Short fixed list of nicer verbs where the verb is entailed by the relation
# for any value: city (residence), occupation, employer, school, language.
NICE_TEMPLATES = {
    "city": "{S} lives in {V}.",
    "occupation": "{S} works as {V}.",
    "employer": "{S} works for {V}.",
    "school": "{S} goes to {V}.",
    "language": "{S} speaks {V}.",
}


def render_claim(subject: str, relation: str, value: str) -> str:
    s = "the speaker" if str(subject).strip() == _ME else str(subject).strip()
    v = str(value).strip()
    tmpl = NICE_TEMPLATES.get(str(relation).strip())
    if tmpl is not None:
        return tmpl.format(S=s, V=v)
    relwords = str(relation).strip().replace("_", " ")
    return f"{s}'s {relwords} is {v}."


# ------------------------------------------------------------------ prompt
# Fixed yes/no question (brief section 2b), temperature 0, thinking off
# ("/no_think" prefix for Qwen3). Ends with "Answer:" so the first sampled
# token is the YES/NO verdict whose logprobs give p(YES).
def build_prompt(turn: str, claim: str) -> str:
    return (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        f"Claim: {str(claim).strip()}\n"
        "Does the message state this claim as a real, current fact that the "
        "speaker believes?\n"
        "Answer NO if the claim is only asked about or checked (including "
        "a tag like \"..., right\" or a \"so ...\" check without \"?\"), "
        "pretend or hypothetical (\"let's say\", \"imagine\", \"suppose\", "
        "\"what if\"), a plan, goal or wish (\"training to be\", "
        "\"wants to\", \"is going to\"), denied, or about a different "
        "person than the message says.\n"
        "Answer with one word: YES or NO.\n"
        "Answer:"
    )
