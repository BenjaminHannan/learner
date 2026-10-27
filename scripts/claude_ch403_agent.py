#!/usr/bin/env python3
"""ch-403: a stock non-answer goes out only on a recall question (everyday-chat thread, 2026-09-26). New file only.

One change on 0.2c's X (claude_e2e02c:build_02c): the chat layer's decision of which turns keep a stock non-answer.

Why (0.2c chat panel, counts only, artifacts/claude-ch403-20260926/DIAG.md): 46 of 335 turns got a stock non-answer on
a turn that saved nothing, in 32 of 60 conversations; the plain twin won 20 of those 32 and X won 18 of the other 28.
28 of the 46 come from the two places this change touches:
  - 338b's people guard (claude_chat338b_agent.PeopleGuard338b) answers HONEST338B ("I'm not sure. I don't think
    you've told me that yet.") instead of asking the 1B whenever a question has my/our, he/she, a relation word or a
    possessive and no advice word: 18 advice, explain and follow-up turns. On the readable DEV practice chats
    (artifacts/claude-chatdev-20260926, 336 turns) it fires on 23 advice, explain and follow-up questions ("why
    does my phone battery die faster in the cold") and 8 think questions, besides the 13 memory asks.
  - the 137c pretend rule's HYPO_REPLY ("OK, I'll treat that as pretend, so I won't save it.") is not one of 338's
    give-up lines, so a follow-up that opens with "what if" never reaches the 1B: 10 turns.
The other 18 (think299b's vote split) belong to route 383 (month-end) and are not touched here.

What: install_chat403(loop, gen) replaces install_chat338b(loop, gen) in the same place. It is 338's turn (copied,
same guards, prompt, history, sampling and fail-closed fallback) with one decision changed, made by one test,
recall403(text, names):
  1. the stand-in generator answers HONEST338B instead of sampling only when recall403 is true (338b: people_question);
  2. a wrapped reply that is exactly HYPO_REPLY counts as a give-up for the hand-off, under 338's own conditions
     (no notebook event this turn, same lis-314 pending store, no confirm question open). Nothing about saving
     changes: the pretend rule still stores nothing, and the chat phase never writes (checked, as in 338).
recall403: the turn asks the assistant to recall something about the user or their people. It is 338b's
people_question with its three broad clauses removed (a question that merely says my/our, he/she, or a relation word)
and narrow ones added. Kept from 338b: check tags ("..., right?"), "who's the guy ...", the advice/writing/planning
exit, "<someone>'s ..." possessives, and names the notebook holds. Narrowed: its recall wording ("did i" alone, "i said"
alone and "again" after any word no longer count). Added:
  - recall wording: "(do|did|can) you remember/recall", "if you remember", "did/have i (say|tell|mention|give)",
    "i (just) (told|said|mentioned) (you|earlier|before)", "what did i (say|tell|call|name)", "remind me",
    "you know my"; "again" only in a what/who/where/when/which question;
  - a value question about the user or their people: what/who/where/when/which/how old/how many (+ is/was/are/does/
    did/do/of) + my/our/his/her/their ("what's my manager's name?", "which of my coworkers ...");
  - a question opening with "whose" or "is/does/did he/she/they ...".
  A turn with recall wording or a value question counts even without a "?".
  On the DEV practice chats (336 turns) it fires on 1 of the 290 everyday turns (338b: 31) and on all 14 memory asks
  (338b: 13); on the DEV memory bank (artifacts/claude-e2e331-dev-20260924) on 70 of 71 asks (338b: 70).
  Every other question that 338b diverted (my/our/he/she or a relation word alone) now goes to the 1B under 338's
  guards, which stay strict on personal questions (G3: every capitalised word and number must be known).
Counters: loop.chat338_stats and loop.chat338b_stats as before (same keys), plus loop.chat403_stats:
  recall_kept (honest line on a recall question), released (a question 338b would have diverted went to the 1B),
  pretend_handed (a HYPO_REPLY turn handed to the chat phase), pretend_replaced (the 1B's reply went out instead).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import claude_chat338_agent as C38
import claude_chat338b_agent as C38B

HYPO_REPLY = "OK, I'll treat that as pretend, so I won't save it."   # fable_fix137c_hypo.HYPO_REPLY, byte-identical

POSSESSOR = r"(?:my|our|his|her|their)"
RECALL_WORDS = re.compile(
    r"\b(?:(?:do|did|can|could|will|would)\s+(?:you|u|ya)\s+(?:still\s+)?(?:remember|recall)|"
    r"(?:you|u)\s+(?:remember|recall)\s+(?:what|which|who|where|when|how|my|our|his|her|the name|i)|"
    r"remind me|(?:did|have|had)\s+i\s+(?:ever\s+|already\s+)?"
    r"(?:say|said|tell|told|mention|mentioned|give|gave|name|named)|"
    r"i\s+(?:just\s+|already\s+)?(?:told|said|mentioned)\s+(?:to\s+)?(?:you|u|earlier|before|already)|"
    r"what\s+did\s+i\s+(?:say|tell|call|name)|you\s+know\s+" + POSSESSOR + r"|if\s+(?:you|u)\s+(?:remember|recall))\b")
WH = r"(?:what|what's|whats|who|who's|whos|whom|whose|where|where's|wheres|when|when's|whens|which|how old|how many)"
LEAD = r"(?:^|[.!?,;]\s*|\b(?:and|so|but|oh|ok|okay|wait|btw|hey|um|also|now|quick q|quick question)\s+)"
AGAIN = re.compile(LEAD + WH + r"\b[^.!?]*\bagain\b")
VALUE_Q = re.compile(LEAD + WH + r"(?:\s+(?:is|was|are|were|does|did|do|of))?\s+" + POSSESSOR + r"\b")
PERSON_Q = re.compile(LEAD + r"(?:whose\b|(?:is|was|are|were|does|did|has|had|will)\s+(?:he|she|they)\b)")


def recall403(text: str, names: set[str]) -> bool:
    """True when the turn asks the assistant to recall something about the user or their people.

    338b's people_question with its three broad clauses removed (a question that merely says my/our, he/she, or a
    relation word) and its recall wording narrowed ("did i" alone, "i said" alone no longer count), plus a value
    question about my/our/his/her ... and a question opening with whose or is/does/did he/she/they. Its check tags,
    who-the-guy clause, advice exit, possessive clause and notebook-name clause are kept."""
    low = " ".join(text.lower().replace("\u2019", "'").split())
    if not (C38B.is_question(low) or RECALL_WORDS.search(low) or VALUE_Q.search(low)):
        return False
    if (RECALL_WORDS.search(low) or AGAIN.search(low) or C38B.TAG.search(low) or C38B.WHO_PERSON.search(low)):
        return True
    if C38B.ADVICE.search(low):
        return False
    if VALUE_Q.search(low) or PERSON_Q.search(low):
        return True
    for m in C38B.POSS.finditer(low):
        if m.group(1) not in C38B.NOT_POSS and not C38B.ARTICLE_BEFORE.search(low[:m.start()]):
            return True
    words = set(re.findall(r"[a-z][a-z']*", low))
    return any(n in words for n in names)


class RecallGuard403:
    """Stands in for 338's generator: the honest line for recall questions, else the 1B (338b's G2 capital check)."""

    def __init__(self, gen, loop):
        self.gen, self.loop = gen, loop

    def sample_chat(self, msgs: list[dict], n: int) -> list[str]:
        text = msgs[-1]["content"] if msgs else ""
        names = C38B.notebook_names(self.loop)
        if recall403(text, names):
            self.loop.chat338b_stats["diverted"] += 1
            self.loop.chat403_stats["recall_kept"] += 1
            return [C38B.HONEST338B]
        if C38B.people_question(text, names):
            self.loop.chat403_stats["released"] += 1
        out = self.gen.sample_chat(msgs, n)
        known = C38._words([m["content"] for m in msgs])
        keep = [c for c in out if not C38B._g2_capital(C38.trim(c), known)]
        self.loop.chat338b_stats["g2_capital"] += len(out) - len(keep)
        return keep


def install_chat403(loop, gen, n: int = C38.N338) -> None:
    """338's install_chat338 with RecallGuard403 as the generator and HYPO_REPLY counted as a give-up."""
    import claude_cre333_agent as C
    loop.chat338b_stats = {"diverted": 0, "g2_capital": 0}
    loop.chat403_stats = {"recall_kept": 0, "released": 0, "pretend_handed": 0, "pretend_replaced": 0}
    guard = RecallGuard403(gen, loop)
    inner = loop.turn
    path = Path(loop.dir) / C38.STATE_NAME338
    state = {"history": []}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    loop.chat338_stats = {"turns": 0, "gave_up": 0, "replaced": 0, "kept_all_failed": 0,
                          "G1": 0, "G2": 0, "G3": 0, "G4": 0}

    def save() -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def pending():
        return json.dumps(getattr(loop, "lis314_store", None), sort_keys=True, ensure_ascii=False)

    def turn403(text: str) -> list[str]:
        loop.chat338_stats["turns"] += 1
        ev0, p0 = len(loop.nb.events), pending()
        parts = inner(text)
        reply = " ".join(p for p in (parts or []) if p)
        out = parts
        miss = C38.topic_miss(reply, text)
        pretend = reply.strip() == HYPO_REPLY                       # the one new give-up line
        if ((C38.gave_up(reply) or miss or pretend) and len(loop.nb.events) == ev0 and pending() == p0
                and getattr(loop, "lis314_confirming", None) is None):
            loop.chat338_stats["gave_up"] += 1
            if pretend:
                loop.chat403_stats["pretend_handed"] += 1
            ctx = C.context_facts(loop, text)
            facts = " ".join(C._sentence(f) for f in ctx)
            hist = state["history"][-C38.HISTORY338:]
            known = C38._words([text, facts] + [h["content"] for h in hist])
            system = C38.SYSTEM338 + (" Facts the user has told you: " + facts if facts else "")
            msgs = [{"role": "system", "content": system}] + hist + [{"role": "user", "content": text}]
            pick = None
            for c in guard.sample_chat(msgs, n):
                c = C38.trim(c)
                g = C38.guard(c, text, known, strict=miss)
                if g is None:
                    pick = c
                    break
                loop.chat338_stats[g] += 1
            if pick is None:
                loop.chat338_stats["kept_all_failed"] += 1
            else:
                loop.chat338_stats["replaced"] += 1
                if pretend:
                    loop.chat403_stats["pretend_replaced"] += 1
                out = [pick]
                reply = pick
            if len(loop.nb.events) != ev0:
                raise RuntimeError("403: chat phase wrote to the notebook")
        state["history"] = (state["history"] + [{"role": "user", "content": text},
                                                {"role": "assistant", "content": reply}])[-C38.HISTORY338:]
        save()
        return out

    turn403.__name__ = "turn338"   # claude_fix02c.chat338_state (F1, delivered history) finds the history by this name
    loop.turn = turn403


def build_403(state_dir, args):
    """0.2c's X with install_chat403 in 338b's place; every other layer, switch and order is build_02c's."""
    import claude_e2e02c as E
    orig = C38B.install_chat338b
    C38B.install_chat338b = install_chat403
    try:
        loop = E.build_02c(state_dir, args)
    finally:
        C38B.install_chat338b = orig
    loop.layers330c = [("chat403" if x == "chat338b" else x) for x in loop.layers330c]
    return loop
