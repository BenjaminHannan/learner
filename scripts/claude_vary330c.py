#!/usr/bin/env python3
"""vary330c: wording variety for two fixed lines in the joined agent (month-end line, 2026-09-24).

Why: in the 330c DEV rehearsal (rent-330c-dev) two fixed lines were 76 of 194 replies: 338b's honest
"I'm not sure. I don't think you've told me that yet." (48) and lis-314's pending-fact acknowledgement "Okay." (28).
336's variety mark M8a allows the most common reply at most 5% of user turns, and the 338 judges called repeated
replies robotic.

What: install_vary330c(loop) wraps loop.turn. When the whole reply is exactly one of those two lines, it is swapped
for a variant with the same meaning, picked by a hash of the user's text, never the same variant twice in a row.
Every HONEST variant contains one of the 336 scorer's abstain markers and none of its clarify or confirm markers;
no ACK variant claims anything was saved. Nothing else changes: no notebook access, no other reply touched.
Install it after 338b and before the nb-323 turn log (so the log records what the user saw).
"""
from __future__ import annotations

import hashlib

HONEST_LINE = "I'm not sure. I don't think you've told me that yet."
ACK_LINE = "Okay."
HONEST_VARIANTS = [
    "I'm not sure. I don't think you've told me that yet.",
    "Honestly, I don't know. I don't think that's come up yet.",
    "I don't have that from you yet, so I won't guess.",
    "I'm not sure about that one. You haven't mentioned it to me.",
    "I don't remember you telling me that, so I'd rather not guess.",
    "That hasn't come up between us yet, so I don't know.",
    "I don't know that one. I'd only be guessing.",
    "I'm not sure, and I don't want to make something up.",
]
ACK_VARIANTS = ["Okay.", "Got it.", "Mm-hm.", "Okay, thanks for telling me.", "Right.", "Thanks.", "Oh, okay.",
                "Sure."]


def _pick(variants: list[str], text: str, last: dict, key: str) -> str:
    i = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % len(variants)
    if last.get(key) == i:
        i = (i + 1) % len(variants)
    last[key] = i
    return variants[i]


def install_vary330c(loop) -> None:
    inner = loop.turn
    last: dict = {}
    loop.vary330c_stats = {"honest": 0, "ack": 0}

    def turn_vary(text: str) -> list[str]:
        parts = inner(text)
        if parts and len([p for p in parts if p]) == 1:
            p = [p for p in parts if p][0]
            if p == HONEST_LINE:
                loop.vary330c_stats["honest"] += 1
                return [_pick(HONEST_VARIANTS, text, last, "h")]
            if p == ACK_LINE:
                loop.vary330c_stats["ack"] += 1
                return [_pick(ACK_VARIANTS, text, last, "a")]
        return parts

    turn_vary.__name__ = "turn_vary330c"
    loop.turn = turn_vary
