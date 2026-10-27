#!/usr/bin/env python3
"""Exp 255 unit tests for scripts/claude_fix255_text.py (no agent needed).

Checks, for one saved 138m-style sample of every template:
  1. the sample is rewritten, and by the expected template id;
  2. the new text has no USER, no dash joins, no mode names, no "?.",
     no Oxford comma, no bare 0/1-plural counts, no double spaces, and ends
     with . ? ! or a closing quote;
  3. the rewrite is idempotent (new text is not a template again);
  4. every frozen scorer anchor family gives the same yes/no on old and new
     (fable_decline224.is_decline, bench121 ABSTAIN_PHRASES with word
     boundaries, redteam143 ABSTAIN_MARKERS, session152 CLARIFY_BITS,
     S105 "i have no record");
  5. non-template lines pass through unchanged, and the dropped-question
     prefix is kept.
Run: python -B scripts/claude_fix255_test.py   (exit 0 = all pass)
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255_text as T
import fable_decline224 as D
import fable_bench121_run as B
import fable_redteam143_cases as R
import fable_session152_run as S

SAMPLES = json.loads('{"T04_GLUE": "I do not know that from what you taught me. I have no record of it, so I will not guess. I didn\'t understand that, I don\'t know — could you say it another way?", "T06_NEG148": "I didn\'t understand that. I only know current facts and I can\'t do \'not\' -- could you say it without that part?", "T02_Q2": "I didn\'t understand that question — could you say it another way?", "T05_F188": "I couldn\'t save that as a fact. I don\'t know that shape yet. Could you say it another way, like \\"Kim\'s boss is Lee.\\"", "T03_S1": "I didn\'t understand that well enough to save it — could you say it another way?", "T01_Q1": "I don\'t know that yet — you haven\'t told me.", "T14_GREETING": "Hi! Teach me like \\"Tom\'s boss is Ann.\\" Ask me like \\"Who is Tom\'s boss?\\"", "T15_187MAKER": "Nobody taught me who made me, so I do not know it. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules.", "T30_MODE": "Right now I am back in LISTENING mode, waiting for your next turn.", "T16_187WHAT": "I am plain software you are teaching: a notebook, a lookup loop, and fixed rules. I can only tell you what you taught me.", "T39_PEOPLE": "I know 5 people: Kestrel, Lorcan, Maudry, Nimue, Pentony.", "T38_FACTS": "I know 3 facts you taught me. I also hold 0 web row, which I do not believe.", "T31_SAYECHO": "my name. (I\'m treating that as pretend, so I won\'t save it.)", "T60_NEWUNSTORED": "You told me something new about I Believe I Can Fly\'s country of origin that I could not store. I can take one fact at a time — could you say it again as one fact?", "T07_TIME148": "I didn\'t understand that. I only know current facts, not years or \'as of\' -- could you say it without that part?", "T32_FIRST": "The first thing you taught me was: your name is Marek.", "T19_CAN": "I can: save what you teach me in my notebook; answer questions from my notes, following one or two steps; correct a fact or forget one when you ask; say I do not know instead of guessing; tell you where each fact came from; hold web text in quarantine without believing it.", "T17_187NAME": "You never gave me a name, so I do not have one. I am plain software you are teaching: a notebook, a lookup loop, and fixed rules.", "T08_SPLIT": "I can take one fact at a time — could you split that?", "T29_PEOPLE0": "I know 0 people: .", "T26_WEB0": "No. I hold 0 web rows.", "T27_SLEPT0": "No. I have slept 0 times.", "T42_SLEEPDERIVED": "None. 0 of my facts are sleep-derived.", "T50_BARECOUNT": "0.", "T28_CORRECTED0": "You corrected: .", "T44_ANSWERED": "I have answered 1 questions.", "T45_SAVEDN": "I saved 0 times through our turns.", "T47_REFUSEDN": "Yes, 20 times I asked for clarification instead of saving.", "T20_CANNOT": "I cannot: feel feelings or have favourites or opinions; guess, predict the future, or explain why things are so; believe the web on my own; remember anything nobody taught me; know anything from outside our turns, like yesterday; dream.", "T48_GUESSES": "0 guesses are waiting for your approval.", "T49_RULES": "0 of my facts came from rules.", "T18_FEELINGS": "I do not have feelings. I am plain software: a notebook, a lookup loop, and fixed rules.", "T21_AGETHEIR": "You never taught me their age, so I do not know it.", "T51_DREAM": "I do not dream. I have slept 0 times and hold 0 sleep-derived facts.", "T33_LAST": "The last thing you taught me was: Ilse\'s city is Brell, in turn 4.", "T34_FORGOT": "I forgot: Tomas\'s boss is Ilse. You asked me to forget it in turn ?. The old row is kept but retired.", "T35_CORRECTED": "You corrected: Tomas\'s boss from Wend to Oda.", "T22_SRCTHAT": "I\'m not sure what \\"that\\" means — I haven\'t just told you a fact.", "T09_UNREAD": "I couldn\'t read that message -- please send it as plain text.", "T10_SAYLIKE": "Please say it like \\"Mira\'s city is Lisbon.\\".", "T11_PICK": "Please answer with: pick <one of the IDs I listed>.", "T12_WEBACTOR": "That write is not allowed from web.", "T13_SELFFALLBACK": "I do not understand that question. Ask me about what I know, where it came from, or what I am doing.", "T23_SRCNOTRACK": "I can\'t say where that came from — I didn\'t keep track of which notes that reply used, so I won\'t guess.", "T24_SAYBARE": "(I\'m treating that as pretend, so I won\'t save it.)", "T25_IDLETHINKING": "Right now I am idle, in THINKING mode. I am waiting for your next turn.", "T36_SRCTOLD": "You told me: USER\'s city is Varn.", "T37_SRCPUT": "I put together things you told me: USER\'s boss is Tamsin; Tamsin\'s city is Brell.", "T40_WEBN": "Yes. I hold 1 quarantined web row. I filed it but I do not believe it.", "T41_SLEPTN": "Yes. I have slept 3 times.", "T43_TURNS": "We have had 1 turns.", "T46_REFUSED0": "No. I understood all 7 turns; I asked for clarification 0 times.", "T52_YESTERDAY": "I have no record of yesterday. My log starts with our first turn here and holds 4 turns.", "T53_NOBODYELSE": "Nobody besides you has spoken to me. All 9 turns are yours.", "T54_C5NOTURN": "You did, in turn ?.", "T55_UNSURE": "I am unsure about: Tomas\'s boss.", "T56_DONTKNOWEX": "I say I do not know instead of guessing. Like when you asked: Who is Nell\'s boss?", "T57_JUSTBEFORE": "Just before that, in turn 3, you asked: Who is Tomas\'s boss? I replied: Tomas\'s boss is Ilse.", "T58_UPDATEDUSER": "Updated: USER\'s city is Varn (it was Brell).", "T59_NOTSAVED": "I could NOT save that: the notebook reported a problem (E17)."}')

UNCHANGED = ["Saved: Mira's city is Lisbon.", "Haha, nice!", "I already have that.",
             "Forgotten: Mira's city.", "Tomas's boss is Ilse.",
             "Your name is Orla.", "My name is Premonition.", ""]

def fam(t):
    low = t.lower().replace("\u2019", "'")
    return (D.is_decline(t),
            any(r.search(low) for r in B._ABSTAIN_RES),
            any(m in low for m in R.ABSTAIN_MARKERS),
            any(b in low for b in S.CLARIFY_BITS),
            "i have no record" in low)

BAD = [r"\bUSER\b", "—", " -- ", r"\b(LISTENING|THINKING|SLEEP|WORK)\b",
       r"\?\.", r", [^,.?!]+, and ", r"\b0 [a-z]", r"\b1 [a-z]+s\b", "  ", r"\.\.",
       r'\."\.']

def main():
    fails = []
    for tid in T.TEMPLATE_IDS:
        if tid not in SAMPLES:
            fails.append((tid, "no sample")); continue
        old = SAMPLES[tid]
        new, got = T.rewrite255(old)
        if got != tid:
            fails.append((tid, "id", got)); continue
        for b in BAD:
            if re.search(b, new):
                fails.append((tid, "bad", b, new))
        if not re.search(r'[.?!]"?$', new):
            fails.append((tid, "end", new))
        if new[:1] != new[:1].upper():
            fails.append((tid, "cap", new))
        if T.rewrite255(new)[1] is not None:
            fails.append((tid, "not idempotent", new))
        if fam(old) != fam(new):
            fails.append((tid, "anchor", fam(old), fam(new), new))
        pre, gp = T.rewrite255(T.PREFIX_DROPPED + old)
        if gp != tid or pre != T.PREFIX_DROPPED + new:
            fails.append((tid, "prefix"))
    for u in UNCHANGED:
        if T.rewrite255(u) != (u, None):
            fails.append(("unchanged", u))
    for f in fails:
        print("FAIL", f)
    print(f"{len(T.TEMPLATE_IDS)} templates, {len(fails)} failures")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
