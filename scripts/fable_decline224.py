#!/usr/bin/env python3
"""Exp 224a — ONE shared decline detector: is_decline(reply) -> bool.

Problem: every frozen scorer carries its own abstain/clarify phrase list
(bench121 ABSTAIN_PHRASES, redteam143 abstain_markers, session152
CLARIFY_BITS, redteam110 ABSTAIN_BITS, sleep104 classify, the self
scorers' "I have no record"). The loop138 agent therefore glued two
declines together (S105.HONEST_DECLINE + L138.DECLINE_SUFFIX) so that every
list matched. This module is the one shared definition the scorers can
use instead, so the agent can serve ONE clear sentence per turn type.

is_decline accepts:
  (i)  every decline / abstain / clarify text the frozen agents serve
       today (census in CENSUS224 below; each entry names its source), and
  (ii) the three exp-224b sentences (NEW_SENTENCES224, fixed here BEFORE
       the 224a seal; the 224b agent imports them from this file).

Rule (deterministic, no model): normalise (lower case, curly quotes ->
straight, whitespace collapsed); a reply that starts with "Saved:" or
"Forgotten:" is never a decline (write confirmations); otherwise it is a
decline iff it contains one of DECLINE_MARKERS224 as a substring. The
marker list is the union of the frozen scorers' own marker lists plus the
census families that no frozen list covered. Known, documented false
positive (inherited from the frozen scorers, kept so no frozen verdict
moves): the self capability sheet "I can: ... say I do not know instead of
guessing ..." contains "do not know" and counts as a decline, exactly as
the frozen session152 scorer counts it. Self-router CANNOT answers ("I
have no opinions.", "I cannot predict.") are NOT declines: see
SELF_CANNOT_ANSWERS224.

Additive only: no frozen file is edited; this module imports nothing.

  python3 scripts/fable_decline224.py --selftest
"""

from __future__ import annotations

import sys

# ----------------------------------------------------------- 224b sentences
# One sentence each, no names, no numbers. Fixed before the 224a seal.
Q1_SENTENCE = "I don't know that yet — you haven't told me."
Q2_SENTENCE = ("I didn't understand that question — could you say it "
               "another way?")
S1_SENTENCE = ("I didn't understand that well enough to save it — could "
               "you say it another way?")
NEW_SENTENCES224 = {"Q1": Q1_SENTENCE, "Q2": Q2_SENTENCE, "S1": S1_SENTENCE}

# ------------------------------------------------------------- the census
# Texts the frozen agents serve today (exact strings or fixed templates
# filled with fictional names). Source = file that defines the text.
GLUE138 = ("I do not know that from what you taught me. I have no record of "
           "it, so I will not guess. I didn't understand that, I don't know "
           "— could you say it another way?")
CENSUS224: list[tuple[str, str]] = [
    # the glue (loop138 / 138g turn(), loop188 QUESTION_FALLBACK188)
    (GLUE138, "fable_loop138_agent.py DECLINE_SUFFIX + fable_self105.py "
              "HONEST_DECLINE; fable_loop188_agent.py QUESTION_FALLBACK188"),
    ("I do not know that from what you taught me. I have no record of it, "
     "so I will not guess.", "fable_self105.py HONEST_DECLINE"),
    # not-understood clarifies
    ("I didn't understand that. Could you say it another way?",
     "fable_agent_loop.py / fable_loop113_agent.py CHAIN_MISS_TEXT / "
     "fable_fix150c_closedclass.py GENERIC_MSG / fable_fix167b_valuescreen.py "
     "NO_WRITE_CLARIFY / fable_loop102_agent.py FORGET_AMBIG_MSG"),
    ("I didn't understand that.", "fable_agent_loop.py _act fallback"),
    ("I didn't catch anything.", "fable_agent_loop.py empty turn"),
    ("Was that a question?", "fable_earsguard91 / loop96 '?' clarify"),
    ("I can only handle one-word names so far.", "fable_agent_loop.py"),
    ('Please say it like "Mira\'s city is Lisbon.".', "fable_agent_loop.py"),
    ("Please answer with: pick <one of the IDs I listed>.",
     "fable_agent_loop.py pick clarify"),
    ("Please answer yes or no.", "fable_fix154d/167e confirm clarify"),
    ("I wasn't waiting for an answer.", "confirm path, nothing pending"),
    ("Okay, I left it as it was.", "confirm path, 'no' answer"),
    ("I couldn't read that message -- please send it as plain text.",
     "fable_loop102_agent.py"),
    # exp-148 screen messages (fable_screen148_mixin.py)
    ("I didn't understand that. I only know current facts and I can't do "
     "'not' -- could you say it without that part?",
     "fable_screen148_mixin.py negation screen"),
    ("I didn't understand that. I only know current facts, not years or "
     "'as of' -- could you say it without that part?",
     "fable_screen148_mixin.py time screen"),
    # split / hearsay / pretend / description screens
    ("I can take one fact at a time — could you split that?",
     "SPLIT clarify (earsguard91 / fix150)"),
    ("You told me something new about Mira's city that I could not store. "
     "I can take one fact at a time — could you say it again as one "
     "fact?", "fable_doubt146_store.py"),
    ("Do you know that yourself, or did you hear it somewhere? I only save "
     "facts you tell me directly.", "fable_loop102_agent.py HEARSAY_MSG"),
    ("That sounds like hearsay, so I won't save it as a fact. If it's true, "
     "just tell me plainly.", "fable_fix137d_frame.py"),
    ("OK, I'll treat that as pretend, so I won't save it.",
     "fable_fix137c_hypo.py"),
    ("That sounds like a description, not a name, so I didn't save it. What "
     "is Mira's mother's name?", "fable_fix171_nameval.py"),
    ('Did you mean "Rome"? Please say it again without the extra words.',
     "fable_fix139d value screen"),
    ("I couldn't save that as a fact. I don't know that shape yet. Could "
     "you say it another way, like \"Kim's boss is Lee.\"",
     "fable_loop188_agent.py statement fallback"),
    # notebook abstains / ambiguity / change prompts
    ("I don't know Mira's city.", "fable_notebook_contract.py MISSING_FACT"),
    ("I don't know anyone called Zed.",
     "fable_notebook_contract.py UNKNOWN_ENTITY"),
    ("I don't know your mother yet.", "fable_loop166_agent.py"),
    ("I don't know anyone whose city is Oslo.", "fable_fix153_reverse.py"),
    ("I know more than one Mira: Mira (E0001), Mira (E0003). Which one do "
     "you mean?", "fable_notebook_contract.py AMBIGUOUS"),
    ("Mira's work is Alpha Book and Beta Book. Which one do you mean?",
     "fable_loop154b_agent.py multi-value ask"),
    ("Mira's boss is Lisbon, which is not someone I can look up.",
     "fable_notebook_contract.py BROKEN_CHAIN"),
    ("I have Mira's city as Lisbon. Do you want me to change it to Oslo?",
     "change prompt (conflict clarify)"),
    ("I could not use that: bad value.", "fable_notebook_contract.py"),
    ("I could NOT save that: the notebook reported a problem (x).",
     "fable_agent_loop.py"),
    ("That write is not allowed from web.", "fable_notebook_contract.py"),
    ("I do not know that. I don't know Ana's city.", "fable_self99.py"),
    # self-router no-record / do-not-know answers (self99 / 161 / fix168)
    ("You never told me your name, so I do not know it.",
     "fable_fix138g_suites / self99"),
    ("You never told me your age, so I do not know it.",
     "fable_selfcard161.py"),
    ("You never taught me Mira's age, so I do not know it.",
     "fable_fix168_ground.py"),
    ("I have no record of that.", "fable_selfcard161.py"),
    ("I have no record of that, so I do not know it.",
     "fable_fix168_ground.py"),
    ("I have no record of that city, so I cannot be sure.",
     "fable_fix168_ground.py"),
    ("I do not understand that question. Ask me about what I know, where it "
     "came from, or what I am doing.", "fable_loop138c_agent.py"),
    ("Nobody taught me who made me, so I do not know it.",
     "fable_loop187_agent.py"),
    ("I'm not sure what you meant.", "fable_listening_english.py"),
    ("I can't answer that.", "fable_talker120d_mouth.py"),
]

# ------------------------------------------------------------ the markers
# Union of the frozen scorers' marker lists (normalised) + census families
# that no frozen list covered + the 224b sentences' own markers.
DECLINE_MARKERS224: tuple[str, ...] = (
    # fable_bench121_run.ABSTAIN_PHRASES (== fable_bench113_run)
    "i don't know", "i dont know", "was that a question",
    "i didn't understand that", "i did not understand",
    "i didn't catch anything", "i can take one fact at a time",
    "could you split that", "do you know that yourself",
    "i only save facts you tell me directly", "i can only follow",
    "please say it like", "i can only handle one-word names",
    "i didn't get the value", "which is not someone i can look up",
    "i know more than one", "which one do you mean", "please answer with",
    "please answer yes or no", "i wasn't waiting for an answer",
    "i couldn't read that message", "do you want me to change it to",
    # redteam143 abstain_markers
    "don't know", "not someone", "didn't understand", "could you say",
    "split that", "only follow", "didn't catch", "couldn't read",
    "only handle one-word", "could not use that", "didn't get the value",
    "not allowed", "do you want me to change", "i only save facts",
    "i wasn't waiting for an answer",
    # session152 CLARIFY_BITS
    "another way", "which one", "do not know", "unknown", "unsure",
    "missing", "1 to 3",
    # redteam110 ABSTAIN_BITS
    "wasn't waiting", "left it as it was", "not someone i can look up",
    "could not save",
    # self scorers (S105 decline marker)
    "i have no record",
    # census families no frozen list covered
    "i could not store", "couldn't save", "i could not save",
    "i won't save it", "so i won't save", "i didn't save it",
    "i can't answer that", "cannot answer that",
    "i do not understand that question", "not sure what you",
    "please say it again without", "which is right?",
    "which one is wrong", "which one should",
)

_NEVER_PREFIXES = ("saved:", "forgotten:")

# Self-router CANNOT answers are ANSWERS about the agent, not declines
# (pilot evidence, 224a: counting them would move frozen verdicts, e.g.
# redteam143 K9/O5 "What is the capital of Ostmark?" -> "I have no
# opinions." is a self-router MISROUTE the frozen scorer rightly calls
# WRONG-ANSWER). is_decline must REJECT these; self replies that say
# "do not know" / "no record" still count, as in every frozen scorer.
SELF_CANNOT_ANSWERS224: list[tuple[str, str]] = [
    ("I cannot predict.", "fable_fix168_ground.py"),
    ("I cannot predict. I only know what you taught me.",
     "fable_selfcard161.py"),
    ("I cannot predict. Nothing you taught me says where Mira will live.",
     "fable_fix168_ground.py"),
    ("I have no opinions.", "fable_self99 capability CANNOT"),
    ("I have no opinions. I only store what you state.",
     "fable_selfcard161.py"),
    ("I do not have favourites. I only store what you state, not likes.",
     "fable_selfcard161.py"),
    ("You never told me why. I only store what you state, not reasons.",
     "fable_fix219_selfname.py"),
]


def _norm(reply: object) -> str:
    s = str(reply or "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    return " ".join(s.lower().split())


def is_decline(reply: object) -> bool:
    """True iff the reply is a decline / abstain / clarify (see module doc)."""
    low = _norm(reply)
    if not low:
        return False
    if low.startswith(_NEVER_PREFIXES):
        return False
    return any(m in low for m in DECLINE_MARKERS224)


def selftest() -> int:
    bad = [t for t, _src in CENSUS224 if not is_decline(t)]
    bad += [t for t in NEW_SENTENCES224.values() if not is_decline(t)]
    for t in NEW_SENTENCES224.values():
        assert not any(ch.isdigit() for ch in t), t
    bad += [t for t, _src in SELF_CANNOT_ANSWERS224 if is_decline(t)]
    rej = ["Saved: Mira's city is Lisbon.", "Mira's city is Lisbon.",
           "I already have that.", "Haha, nice!", "Forgotten: Mira's city."]
    bad += [t for t in rej if is_decline(t)]
    print("selftest", "OK" if not bad else f"FAIL {bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 0)
