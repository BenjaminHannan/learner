#!/usr/bin/env python3
"""383: plain questions go straight to the 1B (month-end line, 2026-09-26). New file only; one change on the
336b G arm (scripts/claude_e2e360.py:build_360).

Why: bm-390 found that 0.1's wrapper drops the 1B's own GSM8K score from 191/300 (plain 1B) to 29/300 and gives no
MMLU letter on 134/300: questions that are not about the user end in "I'm not sure" (think299b's vote split, the
rule agent's lookups) or a clarify line, and 338b's chat layer only steps in on clarify lines.
What: route383 wraps the joined agent. When the final reply abstains or asks to rephrase (the 336 scorer's markers),
the turn is a question (338b is_question), it is NOT a question about the user or their people (about_user383:
recall/check wording, my/mine/our, a name the notebook holds, or a name heard in an EARLIER turn of this chat,
kept in <state_dir>/route383_names.json; added 01:40 UTC before any run after Benchmarks found that on LoCoMo,
with no names held, 1 of 1,540 questions counted as about a person), and the turn wrote nothing to the notebook, the base 1B answers it
plainly (SYSTEM383; 338's guards, strict when the turn says my/I). Questions about the user keep the honest line.
Nothing here writes the notebook (checked). Layer order: ... chat338b -> route383 -> vary330c -> gram360 -> turnlog.
Counters: loop.route383_stats (tried; replaced by the kind of line replaced: think_split / other; all_failed).

build_383   = G + route383 (the registered arm R).
build_383e  = G + ep-382 (k = 20, as 382b) + route383 (report only: both changes; memory is tried first).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

N383 = 4
SYSTEM383 = ("You are a helpful, knowledgeable assistant. Answer the user's question directly and correctly. For "
             "math, work it out step by step and end with the final answer. For a multiple-choice question, end "
             "with the letter of the answer. Never make up facts about the user or people they know.")
THINK_SPLIT = "worked it out a few times"


MIDCAP383 = re.compile(r"(?<![.!?\"\n]\s)(?<!^)(?<=\s)([A-Z][a-z]{2,})\b")
SPEAKER383 = re.compile(r"^\s*([A-Z][a-z]{2,})\s+said\b")
MONTHS383 = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
             "november", "december", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


def heard_names383(text: str) -> set[str]:
    """Names of people heard in a turn: a capitalised word inside a sentence (not its first word), or the speaker in
    '<Name> said, ...'. Month and day names and common sentence starters are left out."""
    import claude_e2e382 as E382
    out = {w.lower() for w in MIDCAP383.findall(text)}
    m = SPEAKER383.match(text)
    if m:
        out.add(m.group(1).lower())
    return {w for w in out if w not in E382.STARTERS382 and w not in MONTHS383}


def about_user383(text: str, names: set[str]) -> bool:
    """A question about the user's own life or people: it asks to recall or check ("again", "did I", "..., right?"),
    says my/mine/our, or names someone the notebook holds facts about. Narrower than 338b's people_question, which
    also fires on any relation word, pronoun or "<name>'s" and so on nearly every math word problem."""
    import claude_chat338b_agent as C38B
    low = text.lower()
    if C38B.RECALL.search(low) or C38B.TAG.search(low) or C38B.WHO_PERSON.search(low) or C38B.SELF.search(low):
        return True
    words = set(re.findall(r"[a-z][a-z']*", low))
    return any(n in words for n in names)


def install_route383(loop, gen, n: int = N383) -> None:
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_e2e382 as E382
    inner = loop.turn
    npath = Path(getattr(loop, "dir", ".")) / "route383_names.json"
    heard = set(json.loads(npath.read_text(encoding="utf-8"))) if npath.exists() else set()
    loop.route383_stats = {"turns": 0, "tried": 0, "replaced_think_split": 0, "replaced_other": 0,
                           "all_failed": 0, "people_kept": 0, "G1": 0, "G2": 0, "G3": 0, "G4": 0}

    def route383(text: str) -> list[str]:
        loop.route383_stats["turns"] += 1
        ev0 = len(loop.nb.events)
        parts = inner(text)
        names = C38B.notebook_names(loop) | heard
        new = heard_names383(text) - heard
        if new and getattr(loop, "dir", None) is not None:
            heard.update(new)
            npath.write_text(json.dumps(sorted(heard)), encoding="utf-8")
        reply = " ".join(p for p in (parts or []) if p)
        if not (E382.abstains(reply) and C38B.is_question(text) and len(loop.nb.events) == ev0
                and getattr(loop, "lis314_confirming", None) is None):
            return parts
        if about_user383(text, names):
            loop.route383_stats["people_kept"] += 1
            return parts
        loop.route383_stats["tried"] += 1
        known = C38._words([text])
        msgs = [{"role": "system", "content": SYSTEM383}, {"role": "user", "content": text}]
        for c in gen.sample_chat(msgs, n):
            c = C38.trim(c)
            g = C38.guard(c, text, known)
            if g is not None:
                loop.route383_stats[g] += 1
                continue
            if len(loop.nb.events) != ev0:
                raise RuntimeError("383: route phase wrote to the notebook")
            loop.route383_stats["replaced_think_split" if THINK_SPLIT in reply else "replaced_other"] += 1
            return [c]
        loop.route383_stats["all_failed"] += 1
        return parts

    route383.__name__ = "route383"
    loop.turn = route383


def _build(state_dir, args, memory_k):
    import claude_chat338_agent as C38
    import claude_chat338b_agent as C38B
    import claude_cre333b_agent as C333B
    import claude_cre333d_agent as C333D
    import claude_e2e330_arms as A
    import claude_e2e330c as E330C
    import claude_e2e382 as E382
    import claude_gram360 as GR
    import claude_nb323_turnlog as NB
    import claude_think299b_agent as T299B
    import claude_vary330c as VARY
    if args.gen_model not in A._GEN:
        A._GEN[args.gen_model] = C333B.Gen333b(args.gen_model)
    one_b = A._GEN[args.gen_model]
    if args.gen_model not in E330C._G338B:
        E330C._G338B[args.gen_model] = C38.Gen338(share=one_b)
    gen = E330C._G338B[args.gen_model]
    store = None
    if memory_k:
        import importlib
        store = importlib.import_module(E382.STORE382).MemoryStore(state_dir)
    loop = A.build_330a_334(state_dir, args)
    GR.record_inner360(loop)
    C333D.install_creative333d(loop, gen)
    T299B.install_think299b(loop, one_b)
    C38B.install_chat338b(loop, gen)
    layers = ["330a_334", "rec360", "cre333d", "think299b", "chat338b"]
    if store is not None:
        E382.install_answer382(loop, gen, store, k=memory_k)
        layers.append("answer382")
    install_route383(loop, gen)
    VARY.install_vary330c(loop)
    GR.install_gram360(loop)
    layers += ["route383", "vary330c", "gram360"]
    if store is not None:
        E382.install_heard382(loop, store)
        loop.store382 = store
        layers.append("heard382")
    NB.install_turnlog323(loop, str(Path(state_dir) / E330C.TURNLOG330C))
    loop.layers330c = layers + ["turnlog323"]
    return loop


def build_383(state_dir, args):
    return _build(state_dir, args, 0)


def build_383e(state_dir, args):
    return _build(state_dir, args, 20)
