#!/usr/bin/env python3
"""333d: creative replies generated the way 338 chat does (month-end line, 2026-09-24). One change on 333c.

Why: 333b/333c (VERIFY-333.md) were judged useful on 3/40 and 2/40 creative items. 333's pick rule keeps the most
grounded of 11 candidates and breaks ties by the SHORTER one, so with no taught fact to use, the shortest candidate
(usually a refusal or a one-line non-answer) wins. 338's chat generation (a friendly system prompt, 4 samples, the
first that passes its guards) was judged natural and helpful on 193/300 of its turns.

What: install_creative333d(loop, gen) keeps 333c's routing (is_creative333c) and 333's guarantees (a creative turn
never reaches the reader, never writes to the notebook; a WORK entry in loop.experience). The reply comes from
gen.sample_chat (338's Gen338) with SYSTEM333D plus the notebook's context facts (333's context_facts, read-only),
4 samples, the first that passes 338's guard (G1 no memory claims, G2 no invented "your <relation> <Name>", G4
length, capped at MAX_WORDS333D words) and G5 (not a refusal or a request for more details instead of an answer). If none passes: 333's FALLBACK line.
"""
from __future__ import annotations

import claude_chat338_agent as C38
import claude_cre333_agent as C
import claude_cre333b_agent as CB

N333D = 4
MAX_WORDS333D = 140
SYSTEM333D = ("You are a friendly, creative assistant. The user is asking for ideas, a plan, or a short piece of "
              "writing. Give it directly and concretely: specific ideas in 2 to 6 sentences, or the short piece "
              "itself. Use the facts below about the user and the people they mention when they fit; never invent "
              "facts about real people (if you know nothing about someone, keep the ideas general). Don't refuse, "
              "don't ask a question instead of answering, and never say you will remember something.")


REFUSAL333D = C38.re.compile(
    r"\b(i can'?t|i cannot|i'?m unable|i am unable|i don'?t have (any |specific |enough )?(information|details|info)|"
    r"please provide|could you (tell|share|give) me|can you (tell|share|give) me|once i have|without (more|knowing)|"
    r"i'?m sorry,? but|as an ai)\b")


def guard333d(c: str, text: str, known: set[str]) -> str | None:
    if len(c.split()) > MAX_WORDS333D:
        return "G4"
    if REFUSAL333D.search(c.lower()):
        return "G5"
    old = C38.MAX_WORDS338
    try:
        C38.MAX_WORDS338 = MAX_WORDS333D
        c2 = C38.re.sub(r"\bYour\b", "your", c)          # 338's G2 pattern is lowercase-only
        return C38.guard(c2, "", known, strict=False)   # "": no G3 name/number check (brands, places are fine)
    finally:
        C38.MAX_WORDS338 = old


def install_creative333d(loop, gen, n: int = N333D) -> None:
    inner = loop.turn
    loop.cre333_stats = {"creative_turns": 0, "fallbacks": 0, "passed_through": 0,
                         "G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}

    def turn333d(text: str) -> list[str]:
        if not CB.is_creative333c(text):
            loop.cre333_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        ctx = C.context_facts(loop, text)
        facts = " ".join(C._sentence(f) for f in ctx)
        known = C38._words([text, facts])
        system = SYSTEM333D + (" Facts the user has told you: " + facts if facts else "")
        reply = None
        for c in gen.sample_chat([{"role": "system", "content": system}, {"role": "user", "content": text}], n):
            c = C38.trim(c)
            g = guard333d(c, text, known)
            if g is None:
                reply = c
                break
            loop.cre333_stats[g] += 1
        loop.cre333_stats["creative_turns"] += 1
        if reply is None:
            loop.cre333_stats["fallbacks"] += 1
            reply = C.FALLBACK
        loop.counters["work"] = loop.counters.get("work", 0) + 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "creative333d",
                                "n": n, "context_facts": len(ctx)})
        loop._save()
        if len(loop.nb.events) != ev0:
            raise RuntimeError("333d: creative turn wrote to the notebook")
        return [reply]

    turn333d.__name__ = "turn333d"
    loop.turn = turn333d
