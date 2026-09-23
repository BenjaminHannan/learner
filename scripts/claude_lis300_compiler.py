#!/usr/bin/env python3
"""lis-300 write compiler: the ONLY code that decides what the listener may save.

The fine-tuned reader (MiniCPM5-1B) proposes a frame (design/v3/60-listener/frame-spec.md).
This plain code turns it into a decision:
  write      facts to save now (all of a turn's writable facts, or none)
  ask_whose  facts owned by "we" (Ben's our/we ruling: ask whose, never save as me)
  ask_back   facts that would be writable but fall below the confidence threshold
  held       facts that can't be written, each with a reason
  question   the reader's ask object when act == ASK

A fact is written only when ALL hold: mode ASSERT/CORRECT; owner "me" or a whole-word span
of the turn or previous reply; value a whole-word span of the turn; relation in the table;
confidence >= threshold. If any writable-looking fact in the turn fails a check, the whole
turn writes nothing (all-or-nothing) and the failing facts go to ask_back or held.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REL_NAMES = set((ROOT / "design/v3/60-listener/relation-names.txt").read_text().split())
WRITE_MODES = {"ASSERT", "CORRECT"}
PRONOUNS = {"he", "she", "his", "her", "hers", "him", "they", "them", "their", "it", "its",
            "i", "my", "our", "us", "you", "your"}
ME_WORDS = re.compile(r"\b(i|i'm|im|i've|ive|me|my|mine|myself)\b", re.I)


def whole_word_span(needle: str, hay: str) -> bool:
    """True if needle occurs in hay as whole words (exact case; typos kept as typed)."""
    if not needle or not needle.strip():
        return False
    # a possessive or "is" contraction typed without an apostrophe is allowed: "anas boss", "hals my cousin"
    pat = r"(?<![A-Za-z0-9])" + re.escape(needle.strip()) + r"(?:'s|’s|s)?(?![A-Za-z0-9])"
    return re.search(pat, hay) is not None


def check_fact(f: dict, turn: str, prev: str) -> str | None:
    """Return None if structurally writable, else the reason it is not."""
    mode = f.get("mode")
    if mode not in WRITE_MODES:
        return f"mode:{mode}"
    owner = str(f.get("owner", ""))
    if owner.lower() == "we":
        return "we"
    if f.get("rel") not in REL_NAMES:
        return "rel_not_in_table"
    if owner.strip().lower() in PRONOUNS:
        return "pronoun_owner"
    if owner.lower() == "me":
        if not ME_WORDS.search(turn) and not ME_WORDS.search(prev or ""):
            return "me_without_first_person"
    elif not (whole_word_span(owner, turn) or whole_word_span(owner, prev or "")):
        return "owner_not_span"
    val = str(f.get("value", ""))
    asked = (prev or "").strip().endswith("?")  # short answers: "Who is Kai?" -> "my cousin"
    if not (whole_word_span(val, turn) or (asked and whole_word_span(val, prev))):
        return "value_not_span"
    if owner.strip().lower() == str(f.get("value", "")).strip().lower():
        return "owner_equals_value"
    return None


def compile_frame(frame: dict, turn: str, prev: str = "", conf: list | None = None,
                  threshold: float = 0.0) -> dict:
    out = {"write": [], "ask_whose": [], "ask_back": [], "held": [],
           "question": None, "act": None}
    if not isinstance(frame, dict):
        out["held"].append({"reason": "unparsed"})
        return out
    out["act"] = frame.get("act")
    if frame.get("act") == "ASK" and isinstance(frame.get("ask"), dict):
        out["question"] = frame["ask"]
    facts = frame.get("facts") or []
    conf = conf if conf is not None else [1.0] * len(facts)
    cand, blocked = [], False
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            blocked = True
            out["held"].append({"fact": f, "reason": "bad_fact"})
            continue
        why = check_fact(f, turn, prev)
        c = conf[i] if i < len(conf) else 0.0
        if why == "we":
            out["ask_whose"].append(f)
        elif why is None:
            if c >= threshold:
                cand.append(f)
            else:
                blocked = True
                out["ask_back"].append({"fact": f, "conf": c})
        elif why.startswith("mode:"):
            out["held"].append({"fact": f, "reason": why})
        else:
            # looked writable (ASSERT/CORRECT) but failed a structural check -> ask back
            blocked = True
            out["ask_back"].append({"fact": f, "conf": c, "reason": why})
    if out["ask_whose"]:
        blocked = True  # a turn that needs "whose?" saves nothing until answered
    if blocked:
        out["ask_back"] = [{"fact": f, "conf": None, "reason": "turn_blocked"} for f in cand] + out["ask_back"]
    else:
        out["write"] = cand
    return out


if __name__ == "__main__":
    import json
    tests = [
        ({"act": "STATE", "facts": [{"owner": "me", "rel": "sister", "value": "mira", "mode": "ASSERT"},
                                   {"owner": "me", "rel": "sister", "value": "tal", "mode": "ASSERT"}], "ask": None},
         "my sisters are mira and tal", 2),
        ({"act": "STATE", "facts": [{"owner": "we", "rel": "dog", "value": "Pip", "mode": "ASSERT"}], "ask": None},
         "our dog is Pip", 0),
        ({"act": "NEGATE", "facts": [{"owner": "Mira", "rel": "dog", "value": "Pip", "mode": "NEGATED"}], "ask": None},
         "Mira doesn't have a dog named Pip", 0),
        ({"act": "STATE", "facts": [{"owner": "Mira", "rel": "dog", "value": "Pipp", "mode": "ASSERT"}], "ask": None},
         "Mira's dog is Pip", 0),
        ({"act": "STATE", "facts": [{"owner": "me", "rel": "sister", "value": "Mira Stil", "mode": "ASSERT"}], "ask": None},
         "my sister is Mira Stil", 1),
    ]
    ok = 0
    for fr, turn, n in tests:
        d = compile_frame(fr, turn)
        good = len(d["write"]) == n
        ok += good
        print("OK " if good else "BAD", turn, "->", json.dumps(d["write"]))
    print(f"{ok}/{len(tests)} self-tests")
