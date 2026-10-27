#!/usr/bin/env python3
"""Exp 280 -- THE ONE CHANGE: "What can you do?" says only what is true.

Base: 260 (scripts/claude_loop260_agent.py, read-only). New file only.

DIAGNOSIS (reproduced live on 260, rows in
artifacts/claude-capab280-20260923/pilot/repro260.json; the probe's own
rows are artifacts/claude-chatweak-20260923/dialogs.json t08/t02/t05):
  - "What can you do?" gets the fixed self99 C24 sheet
    (scripts/fable_self99.py CAPABILITY_CAN): "answer questions from my
    notes, following one or two steps; correct a fact or forget one when
    you ask". Both boasts are disproven on the same store: a stored
    two-link chain ("Bram's boss is Ossa." + "Ossa's city is Lima.") gets
    "I didn't understand that question" on "Where does Bram's boss
    live?", and "Forget where Liora lives." / "Forget everything about
    Liora." get "I don't know anyone called where Liora." /
    "everything about." with nothing removed.
  - Variants ("what are you good at", "Tell me what you're able to do.")
    get the clarify line (unhelpful but claim nothing).
  - "Can you <ability>?" turns are NOT routed to the self sheet on 260:
    most clarify; "Can you answer a two-step question?" gets the C19
    count reply ("I have answered 0 questions."); "Can you tell me where
    a fact came from?" gets the C1 count reply; "Can you feel happy?"
    gets the feelings decline. None claims an ability. Per the spec's
    "if the base already routes them to the self sheet" condition, they
    are out of scope and pass through byte-identical.
  - "What can you not do?" gets the CANNOT sheet, which claims no
    ability; per the spec it stays as is.

THE RULE (outermost instance turn wrapper turn280 over turn260):
  1. A general ability question (closed GENERAL280 set below, matched
     after lowercasing, apostrophe/space collapsing, edge-punctuation
     stripping, and dropping at most 2 leading greeting/opener words) is
     answered with the sealed CAN280 reply. 0 writes.
  2. Belt and braces: any head reply carrying an old-sheet signature
     (OLD_SIG280) is replaced with CAN280. This catches every wording
     that would otherwise emit the false sheet, including opener-
     prefixed ones 260 strips ("heyy, what can you do?"). Reply-only,
     0 writes (the underlying turn already ran; self turns write 0).
  3. Everything else passes through byte-identical. "What can you not
     do?", "Can you ...?", teaches, asks, and the notebook are untouched.

THE SEALED ABILITY TABLE (evidence = builder's own dev chats,
artifacts/claude-capab280-20260923/devcases280.json, 82 dialogs with
fictional names; scores are right/total on the 260 arm):
  kept plainly (dev >= 80%):
    save-teach      8/8    "save what you teach me in my notebook"
    answer-one-step 8/8    "answer one-step questions from my notes"
    honest-abstain  8/8    "say I do not know instead of guessing"
  kept with the working example phrasing (>= 90% on that phrasing):
    correct         8/8 on "No, ..."/"Actually, ..." (0/4 on the
                    "X is Y, not Z." contrast shape; 8/12 overall)
    forget          8/8 on "Forget X's R." (0/4 on "where"/"everything
                    about"/"I want you to" wordings; 8/12 overall)
    two-step chain 10/10 on "Who is X's boss's boss?" (1/6 on mixed
                    hops like "Where does X's boss live?"; 11/16 overall)
  dropped (never claimed anywhere in CAN280):
    mixed two-fact hops, contrast corrections, other forget wordings,
    provenance ("tell you where each fact came from", 0/8 natural
    phrasings all clarify), quarantine (no turn-level evidence).
"""

from __future__ import annotations

# ------------------------------------------------------- sealed ability table
ABILITY280 = (
    {"id": "save", "claim": "save what you teach me in my notebook",
     "example": "Rina's boss is Skye.", "evidence": "dev save 8/8",
     "dev": "8/8", "list": "plain"},
    {"id": "ask1", "claim": "answer one-step questions from my notes",
     "example": "Where does Tavish live?", "evidence": "dev ask1 8/8",
     "dev": "8/8", "list": "plain"},
    {"id": "abstain", "claim": "say I do not know instead of guessing",
     "example": "Who is Zara's boss? (never taught)",
     "evidence": "dev abstain 8/8", "dev": "8/8", "list": "plain"},
    {"id": "correct", "claim": "correct a fact",
     "example": "No, Mira's city is York.",
     "evidence": "dev correct 8/8 on No/Actually phrasing "
                 "(0/4 contrast shape; 8/12 overall)",
     "dev": "8/8 on phrasing", "list": "with example"},
    {"id": "forget", "claim": "forget a fact",
     "example": "Forget Quinn's cat.",
     "evidence": "dev forget 8/8 on direct phrasing "
                 "(0/4 other wordings; 8/12 overall)",
     "dev": "8/8 on phrasing", "list": "with example"},
    {"id": "twochain", "claim": "follow two steps",
     "example": "Who is Nils's boss's boss?",
     "evidence": "dev twohop 10/10 on boss-chain phrasing "
                 "(1/6 mixed hops; 11/16 overall)",
     "dev": "10/10 on phrasing", "list": "with example"},
)

# Rendered once from the table above; every general ability question gets
# exactly this reply. Lists 6 table-backed abilities (>= 3) and one short
# limits sentence naming the dropped shapes. Claims nothing dropped.
CAN280 = (
    "I can: save what you teach me in my notebook; "
    "answer one-step questions from my notes, like 'Where does Tavish live?'; "
    "correct a fact if you say it like 'No, Mira's city is York'; "
    "forget a fact if you say it like 'Forget Quinn's cat'; "
    "follow two steps if you ask like 'Who is Nils's boss's boss?'; "
    "and say I do not know instead of guessing. "
    "I can't yet answer mixed two-fact questions like "
    "'Where does Quill's boss live?', forget things you phrase any other "
    "way, or tell you where a fact came from."
)

# Signatures of the OLD false sheet. A head reply containing any of these
# is replaced with CAN280. CAN280 itself contains none of them.
OLD_SIG280 = (
    "one or two steps",
    "following one or two",
    "correct a fact or forget",
    "forget one when you ask",
    "answer questions from my notes, following",
)

# Closed set of general ability questions (normalized form; see _norm280).
GENERAL280 = frozenset([
    "what can you do",
    "what are you good at",
    "what are you able to do",
    "tell me what you are able to do",
    "tell me what you're able to do",
    "tell me what you can do",
    "say what you can do",
    "list what you can do",
    "what are your abilities",
    "what are your skills",
    "list your abilities",
    "tell me your abilities",
    "what things can you do",
    "what stuff can you do",
    "describe what you can do",
    "tell me about what you can do",
])

# Leading words dropped (at most 2) before the GENERAL280 match. A fact
# turn can never match GENERAL280 afterwards, so this cannot misroute one.
OPENER280 = frozenset([
    "hey", "heyy", "hiya", "howdy", "hi", "hello",
    "please", "so", "well", "um", "uh", "okay", "ok",
])


def _norm280(text: str) -> str:
    t = str(text).lower().replace("\u2019", "'").replace("\u2018", "'")
    t = " ".join(t.split()).strip(" ?!.\"'-,;:")
    words = t.split(" ")
    n = 0
    while n < 2 and words and words[0].rstrip(",") in OPENER280:
        words = words[1:]
        n += 1
    t = " ".join(words).strip(" ?!.\"'-,;:")
    if t.endswith(" please"):
        t = t[:-len(" please")].strip(" ?!.\"'-,;:")
    return t


def is_general280(text: str) -> bool:
    """True only for closed-set general ability questions."""
    return _norm280(text) in GENERAL280


def has_old_sheet_sig(reply_lines) -> bool:
    blob = " ".join(reply_lines).lower()
    return any(s in blob for s in OLD_SIG280)


def install_capab280(loop):
    """Install the 280 layer on a built 260 loop (outermost, instance)."""
    inner_turn = loop.turn            # turn260(turn224c(...))
    loop.turn280_inner = inner_turn
    loop.capab280_log = []

    def turn280(text: str) -> list[str]:
        t = str(text)
        if is_general280(t):
            loop.capab280_log.append({"pre": t})
            return [CAN280]
        r = list(inner_turn(t))
        if has_old_sheet_sig(r):
            loop.capab280_log.append({"post": t})
            return [CAN280]
        return r

    turn280.__name__ = "turn280"
    loop.turn = turn280
    return loop
