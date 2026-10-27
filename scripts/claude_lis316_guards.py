#!/usr/bin/env python3
"""lis-316 code guards: per-fact checks that turn a reading the reader is "sure" of into an UNSURE
one (confidence set to 0.0), so it is confirmed before it is saved (lis-314 pending store, or
turn310's ask-back when lis-314 is not installed). A guard never saves and never drops a fact.

Guards (Ben's 01:37 fit report, item 6; each is checked against the code of
scripts/claude_lis300_compiler.py):
  G1 me_prev    owner "me" passes check_fact when a first-person word is only in the PREVIOUS
                reply, but that reply is the assistant's, so its "I" means the assistant. Guard:
                owner "me" with no first-person word in the turn, unless the previous reply
                speaks about the user ("you"/"your": a short answer or a correction of it).
  G2 prev_owner an owner found only in the previous reply passes check_fact. Guard: owner not in
                the turn, no third-person pronoun in the turn, the previous reply was not a
                question, and the turn has no correction cue (no, not, meant, actually, ...).
  G3 comma      the 263 comma family: an owner that contains a comma ("Wow, Tamsin").
  G4 mixed_case the 261b typo family: an owner or value mixing a Capitalised word with a
                lowercase word that is not a name particle or title function word ("Lenn
                tomorow"); number tokens ("3rd") are skipped. Values of lowercase-word relations
                (jobs, hobbies, colours, ...) are exempt, like 261b's value_kind exemption.

guard_fact(f, turn, prev) -> list of guard names that fire.
apply_guards(frame, confs, turn, prev) -> (new_confs, fired) with confs of guarded facts = 0.0.
"""
from __future__ import annotations

import re

ME_WORDS = re.compile(r"\b(i|i'm|im|i've|ive|me|my|mine|myself)\b", re.I)
YOU_WORDS = re.compile(r"\b(you|your|yours)\b", re.I)
THIRD = re.compile(r"\b(he|she|his|her|hers|him|they|their|theirs|them|it|its)\b", re.I)
PARTICLES = {"de", "da", "van", "von", "der", "la", "le", "del", "di", "bin", "al",
             # title function words ("Bells of Ashgrove", "Salt and Silver"): not typos
             "of", "and", "the", "a", "an", "in", "on", "at", "to", "for", "with", "by", "&"}
CORRECTION_CUE = re.compile(r"\b(no|not|nope|meant|actually|sorry|oops|wait|instead|rather)\b", re.I)
LOWER_VALUE_RELS = {"occupation", "hobby", "favorite_color", "color", "favorite_food",
                    "favorite_drink", "favorite_sport", "mood", "genre", "sport", "instrument",
                    "language", "religion_or_worldview", "title", "position_played_on_team_speciality",
                    "toy", "age", "code", "nickname"}


def _in(needle, hay):
    if not needle or not needle.strip():
        return False
    pat = r"(?<![A-Za-z0-9])" + re.escape(needle.strip()) + r"(?:'s|’s|s)?(?![A-Za-z0-9])"
    return re.search(pat, hay or "") is not None


def _mixed(span):
    # words that start with a letter; "3rd", "9th" and other number tokens are skipped
    words = [w for w in re.findall(r"[^\s]+", str(span or "")) if w[:1].isalpha()]
    cap = any(w[0].isupper() for w in words)
    low = any(w[0].islower() and w.lower() not in PARTICLES for w in words)
    return cap and low


def guard_fact(f, turn, prev):
    fired = []
    owner = str(f.get("owner", ""))
    prev = prev or ""
    asked_user = prev.strip().endswith("?")
    if owner.lower() == "me":
        # the previous reply is the assistant's: "you/your" there is the user, "I/my" is not
        if not ME_WORDS.search(turn) and not YOU_WORDS.search(prev):
            fired.append("me_prev")
    elif owner.lower() != "we":
        if (not _in(owner, turn) and _in(owner, prev) and not THIRD.search(turn)
                and not asked_user and not CORRECTION_CUE.search(turn)):
            fired.append("prev_owner")
        if "," in owner:
            fired.append("comma")
    if ((owner.lower() not in ("me", "we") and _mixed(owner))
            or (str(f.get("rel", "")) not in LOWER_VALUE_RELS and _mixed(f.get("value", "")))):
        fired.append("mixed_case")
    return fired


def apply_guards(frame, confs, turn, prev):
    facts = frame.get("facts") or [] if isinstance(frame, dict) else []
    new = list(confs) + [0.0] * max(0, len(facts) - len(confs))
    fired = []
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            continue
        g = guard_fact(f, turn, prev)
        if g:
            new[i] = 0.0
            fired.append({"i": i, "guards": g})
    return new, fired
