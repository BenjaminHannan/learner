#!/usr/bin/env python3
"""338b person-question guard (month-end line, 2026-09-24). One change on top of 338.

Why: on the readable DEV bank, turning 338 on added 5 wrong answers to memory questions. 4 were non-answers
("I'm sorry, I can't help with that") and 1 was a real guess: a yes/no question about the user's friend was
answered "Yes, I'm sure about that." 338's guards check names and numbers, not yes/no.

What: install_chat338b(loop, gen) installs 338 with a generator stand-in. When 338's chat phase would ask the
1B about a turn that is a question about the user or their people (people_question below), the stand-in
returns HONEST338B instead of samples, so the reply is an honest "not sure" and the 1B never answers
about the user's own people. Every other turn goes to the 1B as in 338, except that samples with a
sentence-initial "Your <relation> <unknown Name>" are dropped first (338's G2 only matched a lowercase "your").
Counters: loop.chat338b_stats["diverted"], ["g2_capital"].

people_question(text, names): the text is a question ("?" anywhere, or a sentence that opens like a question)
AND either it asks to recall ("again", "remind me", "did I", "I told you", ...) or ends a statement with a check
tag ("..., right?", "yes?", "isn't he?"), or asks "who's the guy/girl/one ...", or it is not a request for advice ("should I", "how do I", "ideas",
"tips", "recommend", ...) or for writing or planning ("write", "poem", "plan", "gift", ...), and at least one of
  - it is about the user's own life (my, mine, our);
  - it names a relation (sister, friend, boss, dog, ...);
  - it uses he/she/him/her/his/hers or whose;
  - it has "<word>'s" where <word> is not a contraction word and is not right after a/an/the;
  - it names someone the notebook holds facts about (names = stored subjects, and values of relation facts).
"""
from __future__ import annotations

import re

import claude_chat338_agent as C38

HONEST338B = "I'm not sure. I don't think you've told me that yet."
QOPEN = re.compile(r"\s*(what|what's|whats|who|who's|whom|whose|where|where's|when|which|how|why|do|does|did|"
                   r"is|isn't|was|wasn't|are|were|has|have|can|could|would|will|should|remind|tell)\b")
SELF = re.compile(r"\b(my|mine|our)\b")
RECALL = re.compile(r"\b(remind me|(?<!that )(?<!it )(?<!this )again|did i|have i|i told you|i said|i mentioned|i tell you)\b")
ADVICE = re.compile(r"\b(should i|should we|how do i|how can i|how would i|how should i|what can i|what could i|"
                    r"any (ideas|tips|advice)|ideas? for|tips?|advice|recommend|suggest|help me|what do you think|"
                    r"how do you|how does|how to|write|make up|come up with|poem|story|song|lullaby|joke|toast|"
                    r"plan|draft|message|card for|gift)\b")
WHO_PERSON = re.compile(r"\bwho('s| is| was)? the (guy|girl|lady|woman|man|one|person|kid)\b")
PRON = re.compile(r"\b(he|she|him|her|his|hers|whose|he's|she's)\b")
RELW = re.compile(r"\b(" + C38.RELATIONS + r")s?\b")
POSS = re.compile(r"(?<![a-z'])([a-z]+)'s\b")
NOT_POSS = {"what", "that", "it", "there", "here", "who", "where", "when", "how", "why", "let", "he", "she",
            "everyone", "everybody", "someone", "somebody", "nobody", "one", "today", "tonight", "tomorrow",
            "yesterday", "this", "which", "name"}
ARTICLE_BEFORE = re.compile(r"\b(a|an|the)\s+$")
TAG = re.compile(r"\b(right|yes|correct|yeah|isn't (he|she|it|that)|aren't (they|you)|wasn't (he|she|it)|"
                 r"didn't (i|he|she)|don't (i|they))\s*\?")


def is_question(text: str) -> bool:
    return "?" in text or any(QOPEN.match(s) for s in re.split(r"[.!?]+", text.lower()))


def people_question(text: str, names: set[str]) -> bool:
    low = text.lower()
    if not is_question(low):
        return False
    if RECALL.search(low) or TAG.search(low) or WHO_PERSON.search(low):
        return True
    if ADVICE.search(low):
        return False                       # advice, how-to or writing about someone: the 1B answers, under 338's guards
    if SELF.search(low) or RELW.search(low) or PRON.search(low):
        return True
    for m in POSS.finditer(low):
        if m.group(1) not in NOT_POSS and not ARTICLE_BEFORE.search(low[:m.start()]):
            return True
    words = set(re.findall(r"[a-z][a-z']*", low))
    return any(n in words for n in names)


def notebook_names(loop) -> set[str]:
    import claude_cre333_agent as C
    out = set()
    rel = re.compile(r"\b(" + C38.RELATIONS + r")\b")
    for s, r, v in C._facts(loop):
        if s.lower() not in ("user", "me", "i"):
            out.add(s.lower())
        if rel.search(r.lower().replace("_", " ")):
            out.add(v.lower())
    return {n for n in out if n and " " not in n}


class PeopleGuard338b:
    """Stands in for 338's generator: honest line for questions about the user's people, else the 1B."""

    def __init__(self, gen, loop):
        self.gen, self.loop = gen, loop

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        text = msgs[-1]["content"] if msgs else ""
        if people_question(text, notebook_names(self.loop)):
            self.loop.chat338b_stats["diverted"] += 1
            return [HONEST338B]
        out = self.gen.sample_chat(msgs, n)
        known = C38._words([m["content"] for m in msgs])
        keep = [c for c in out if not _g2_capital(C38.trim(c), known)]
        self.loop.chat338b_stats["g2_capital"] += len(out) - len(keep)
        return keep


def _g2_capital(c: str, known: set[str]) -> bool:
    """338's G2 pattern only matches a lowercase "your"; check sentence-initial "Your <relation> <Name>" too."""
    if "Your " not in c:
        return False
    return C38.guard(re.sub(r"\bYour\b", "your", c), "", known) == "G2"


def install_chat338b(loop, gen, n: int = C38.N338) -> None:
    loop.chat338b_stats = {"diverted": 0, "g2_capital": 0}
    C38.install_chat338(loop, PeopleGuard338b(gen, loop), n)
