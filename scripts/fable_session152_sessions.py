#!/usr/bin/env python3
"""Experiment 152 -- realistic-user session red team (sessions only, no logic).

Six sessions of 30 turns each in the voice of a high-school student typing
on a phone. Written BEFORE the registered run; sealed with PASSMARKS.md.
Each turn: text + expected acceptable behaviour written before running.

Expect kinds:
  teach    -- a fact write must happen (fact_writes >= 1) and the reply
              confirms it; `want` = value substring that must be stored.
  correct  -- like teach but supersedes an earlier fact; `want` = new value.
  ask      -- exact answer; `want` = answer substring, no write (writes == 0).
  reask    -- like ask but ~10 turns after first ask (delayed recall).
  abstain  -- honest abstain (never taught / unknown entity / missing link),
              writes == 0.
  clarify  -- input is genuinely garbled/ambiguous (clear=False): a clarify
              reply with no write is acceptable.
  smalltalk-- greetings/thanks/lol: must not write; a small-talk reply with
              no write is OK, "I didn't understand ..." leaves a normal
              person stuck (UNHELPFUL).
  self     -- "who are you" / "what can you do": must not write; an honest
              identity/capability answer (or helpful pointer) is OK,
              "I didn't understand ..." leaves a normal person stuck.
  known    -- one turn per already-known issue (fixes 144/146/147/148/150/
              151 in flight); judged but EXCLUDED from the novelty count.

`clear` = True means a normal person would call the message clear, so a
bare "I didn't understand" verdicts as UNHELPFUL rather than OK.
"""

from __future__ import annotations


def T(text, expect, want=None, clear=True, known=None):
    return {"text": text, "expect": expect, "want": want, "clear": clear,
            "known": known}


SESSIONS = [
    {
        "id": "S1-family10",
        "note": "Only 1- and 2-hop questions about a 10-fact family.",
        "turns": [
            T("hi", "smalltalk"),
            T("Ana's mother is Lisa.", "teach", "Lisa"),
            T("Ana's father is Mark.", "teach", "Mark"),
            T("Who is Ana's mother?", "ask", "Lisa"),
            T("Lisa's city is Denver.", "teach", "Denver"),
            T("where does she live?", "ask", "Denver"),
            T("Who is Ana's mother's city?", "ask", "Denver"),
            T("Mark's city is Denver.", "teach", "Denver"),
            T("what about his mom?", "ask", "Lisa"),
            T("Ana's sister is Zoe.", "teach", "Zoe"),
            T("Who is Ana's sister?", "ask", "Zoe"),
            T("Zoe's city is Austin.", "teach", "Austin"),
            T("Where is Ana's sister's city?", "ask", "Austin"),
            T("Ana's brother is Leo.", "teach", "Leo"),
            T("Who is Ana's brother?", "ask", "Leo"),
            T("Leo's teacher is Patel.", "teach", "Patel"),
            T("Who is Leo's teacher?", "ask", "Patel"),
            T("Who is Ana's brother's teacher?", "ask", "Patel"),
            T("Kip's wife is Jo.", "teach", "Jo"),
            T("Who is Kip married to?", "known", "Jo", known="K147"),
            T("Jo's city is Austin.", "teach", "Austin"),
            T("Who is Kip's wife's city?", "ask", "Austin"),
            T("Who is Ana's mother?", "reask", "Lisa"),
            T("Who is Ana's mother's city?", "reask", "Denver"),
            T("thanks!", "smalltalk"),
            T("Who is Zoe's city?", "ask", "Austin"),
            T("Who is Mark's city?", "ask", "Denver"),
            T("lol", "smalltalk"),
            T("Who is Ana's father's city?", "ask", "Denver"),
            T("ok cool", "smalltalk"),
        ],
    },
    {
        "id": "S2-casual-friends",
        "note": "Lowercase, emoji, btw/also fillers, hedge (known K150).",
        "turns": [
            T("heyyy", "smalltalk"),
            T("what can you do", "self"),
            T("Marta's friend is June.", "teach", "June"),
            T("june's city is reno", "teach", "reno"),
            T("btw marta's brother is kai", "teach", "kai"),
            T("Who is Marta's friend?", "ask", "June"),
            T("oh and june's teacher is patel", "teach", "patel"),
            T("who is june's teacher?", "ask", "patel"),
            T("I think Kip Dune's city is Reno.", "known", None, known="K150"),
            T("Who is Marta's friend's city?", "ask", "reno"),
            T("who are you", "self"),
            T("Marta's sister is Wren.", "teach", "Wren"),
            T("also wren's city is miami", "teach", "miami"),
            T("what is wren's city?", "ask", "miami"),
            T("lol", "smalltalk"),
            T("Who is Wren's city?", "reask", "miami"),
            T("Marta's father is Dez.", "teach", "Dez"),
            T("dez's city is dallas", "teach", "dallas"),
            T("where is marta's father's city?", "ask", "dallas"),
            T("Who is June's city?", "reask", "reno"),
            T("ty, very helpful!", "smalltalk"),
            T("Marta's mother is Liv.", "teach", "Liv"),
            T("liv's city is boston", "teach", "boston"),
            T("who is marta's mother's city?", "ask", "boston"),
            T("Who is Zane's city?", "abstain"),
            T("k bye", "smalltalk"),
            T("Who is Marta's mother's city?", "reask", "boston"),
            T("Who is Liv's city?", "ask", "boston"),
            T("Who is Marta's brother?", "reask", "kai"),
            T("Who is Marta's sister's city?", "ask", "miami"),
        ],
    },
    {
        "id": "S3-teachers-correction",
        "note": "Bare correction, pronoun + synonym, year (K148), two-of (K144).",
        "turns": [
            T("heyy, what can you do?", "self"),
            T("Nadia's teacher is Rao.", "teach", "Rao"),
            T("Who is Nadia's teacher?", "ask", "Rao"),
            T("rao's city is seattle", "teach", "seattle"),
            T("where does she live?", "ask", "seattle"),
            T("Where is Nadia's teacher's city?", "ask", "seattle"),
            T("no wait, it's denver", "correct", "denver"),
            T("Actually, Rao's city is Denver.", "correct", "Denver"),
            T("Where is Nadia's teacher's city?", "reask", "Denver"),
            T("Nadia's brother is Finn.", "teach", "Finn"),
            T("what about his mom?", "ask", "Orla"),
            T("Finn's mother is Orla.", "teach", "Orla"),
            T("Who is Finn's mother?", "ask", "Orla"),
            T("Who is Nadia's brother's mother?", "ask", "Orla"),
            T("Who was Nadia's teacher in 2023?", "known", "Rao", known="K148"),
            T("Nadia's school is Lyceum.", "teach", "Lyceum"),
            T("Aldo's title is Dean of the School of Music.", "teach", "Dean"),
            T("who is the dean of the school of music?", "known", None, known="K144"),
            T("What is Aldo's title?", "ask", "Dean"),
            T("where does she live?", "clarify", None, clear=False),
            T("thanks!", "smalltalk"),
            T("Who is Nadia's teacher?", "reask", "Rao"),
            T("Where is Nadia's teacher's city?", "reask", "Denver"),
            T("Who is Petra's teacher?", "abstain"),
            T("Who is Nadi's teacher?", "abstain", None, clear=False),
            T("Who is Finn's mother?", "reask", "Orla"),
            T("What is Nadia's school?", "ask", "Lyceum"),
            T("ok cool", "smalltalk"),
            T("Who is Nadia's brother's mother?", "reask", "Orla"),
            T("Who is Orla's city?", "abstain"),
        ],
    },
    {
        "id": "S4-pets-identity",
        "note": "Pets without possessives, identity/capability, untaught, emoji value, typo.",
        "turns": [
            T("hi!!", "smalltalk"),
            T("my dog is biscuit", "teach", "biscuit"),
            T("Biscuit's color is brown.", "teach", "brown"),
            T("Biscuit's owner is Ana.", "teach", "Ana"),
            T("What is Biscuit's color?", "ask", "brown"),
            T("Who is Biscuit's owner?", "ask", "Ana"),
            T("Ana's pet is Biscuit.", "teach", "Biscuit"),
            T("Who is Ana's pet's color?", "ask", "brown"),
            T("who are you", "self"),
            T("what can you do?", "self"),
            T("Milo's color is gray.", "teach", "gray"),
            T("Milo's owner is Ana.", "teach", "Ana"),
            T("What is Milo's color?", "ask", "gray"),
            T("What is Milo's city?", "abstain"),
            T("What is Zane's color?", "abstain"),
            T("thanks so much!", "smalltalk"),
            T("Milo's toy is ball", "teach", "ball"),
            T("What is Milo's toy?", "ask", "ball"),
            T("lol", "smalltalk"),
            T("What is Biscuit's color?", "reask", "brown"),
            T("Who is Ana's pet's owner?", "ask", "Ana"),
            T("What is Biscut's color?", "abstain", None, clear=False),
            T("Who is Milo's owner?", "ask", "Ana"),
            T("Who is Ana's pet?", "reask", "Biscuit"),
            T("ok cool", "smalltalk"),
            T("What is Milo's color?", "reask", "gray"),
            T("Who is Biscuit's owner's pet?", "ask", "Biscuit"),
            T("Who is Ana's pet's color?", "reask", "brown"),
            T("bye!!", "smalltalk"),
            T("What is Milo's toy?", "reask", "ball"),
        ],
    },
    {
        "id": "S5-robustness",
        "note": "Missing periods, no question mark (K151), contractions, imperatives, typos.",
        "turns": [
            T("hey", "smalltalk"),
            T("Rosa's friend is Tess.", "teach", "Tess"),
            T("Tess's city is Omaha", "teach", "Omaha"),
            T("What is Tess's city", "known", "Omaha", known="K151"),
            T("who is rosa's friend", "ask", "Tess"),
            T("what's tess's city?", "ask", "Omaha"),
            T("tell me tess's city", "ask", "Omaha"),
            T("Rosa's mother is Vera.", "teach", "Vera"),
            T("vera's city is lima", "teach", "lima"),
            T("Who is Rosa's mother's city???", "ask", "lima"),
            T("  who is vera's city  ", "ask", "lima"),
            T("Rosa's brother is Ned.", "teach", "Ned"),
            T("ned's teacher is quinn", "teach", "quinn"),
            T("who is ned's teacher", "ask", "quinn"),
            T("Who is Rosa's brother's teacher?", "ask", "quinn"),
            T("ok", "smalltalk"),
            T("Tess's city is Omaha.", "teach", "Omaha"),
            T("What is Tess's city?", "reask", "Omaha"),
            T("Rosa's sister is Pia 🙂", "teach", "Pia"),
            T("Who is Rosa's sister?", "ask", "Pia"),
            T("cool thanks", "smalltalk"),
            T("Who is Rosa's friend?", "reask", "Tess"),
            T("Where is Rosa's friend's city?", "ask", "Omaha"),
            T("Who is Rosa's mother's city?", "reask", "lima"),
            T("Who is Tess's city?", "reask", "Omaha"),
            T("Who is Ned's teacher?", "reask", "quinn"),
            T("Who is Rosa's brother?", "ask", "Ned"),
            T("Who is Pia's city?", "abstain"),
            T("Who is Rosa's sister's city?", "abstain"),
            T("bye", "smalltalk"),
        ],
    },
    {
        "id": "S6-pronouns-corrections",
        "note": "Pronoun follow-ups, Actually- vs refused-correction staleness (K146).",
        "turns": [
            T("hii", "smalltalk"),
            T("Eve's mother is Fay.", "teach", "Fay"),
            T("Fay's city is Reno.", "teach", "Reno"),
            T("where does she live?", "ask", "Reno"),
            T("Who is Eve's mother's city?", "ask", "Reno"),
            T("Eve's father is Gus.", "teach", "Gus"),
            T("what about his mom?", "clarify", None, clear=False),
            T("Gus's mother is Hattie.", "teach", "Hattie"),
            T("Who is Gus's mother?", "ask", "Hattie"),
            T("and his dad?", "clarify", None, clear=False),
            T("Gus's father is Ivan.", "teach", "Ivan"),
            T("Who is Gus's father?", "ask", "Ivan"),
            T("Who is Eve's father's mother?", "ask", "Hattie"),
            T("Vera's city is Lima.", "teach", "Lima"),
            T("no Vera's city is Quito", "known", None, known="K146"),
            T("What is Vera's city?", "known", "Lima", known="K146"),
            T("Actually, Vera's city is Quito.", "correct", "Quito"),
            T("What is Vera's city?", "reask", "Quito"),
            T("Eve's sister is June.", "teach", "June"),
            T("June's city is Miami.", "teach", "Miami"),
            T("where does she live?", "clarify", None, clear=False),
            T("Who is June's city?", "ask", "Miami"),
            T("thanks!", "smalltalk"),
            T("Who is Eve's mother?", "reask", "Fay"),
            T("Who is Eve's mother's city?", "reask", "Reno"),
            T("Who is Eve's father's father?", "ask", "Ivan"),
            T("lol", "smalltalk"),
            T("Who is Gus's mother's city?", "abstain"),
            T("What is Vera's city?", "reask", "Quito"),
            T("ok cool", "smalltalk"),
        ],
    },
]


def check():
    """Pre-run sanity: 6 sessions x 30 turns, one known turn max per class."""
    assert len(SESSIONS) == 6, len(SESSIONS)
    seen = {}
    for s in SESSIONS:
        assert len(s["turns"]) == 30, (s["id"], len(s["turns"]))
        for t in s["turns"]:
            assert t["expect"] in ("teach", "correct", "ask", "reask",
                                   "abstain", "clarify", "smalltalk",
                                   "self", "known"), t
            if t["known"]:
                seen[t["known"]] = seen.get(t["known"], 0) + 1
    # K146 is a two-turn correction+stale pair for one issue; rest max one.
    for k, n in seen.items():
        assert n <= (2 if k == "K146" else 1), (k, n)
    kinds = {}
    for s in SESSIONS:
        for t in s["turns"]:
            kinds[t["expect"]] = kinds.get(t["expect"], 0) + 1
    return {"sessions": len(SESSIONS),
            "turns": sum(len(s["turns"]) for s in SESSIONS),
            "expect_mix": kinds, "known": seen}


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=1, sort_keys=True))
