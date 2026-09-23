# Exp 100 blind questions — FROZEN before importing the answerer (2026-09-21)

Rule: written from ONLY artifacts/fable-self99-20260921/transcript.md and the
intent list (ids + one-line intent) in its PASSMARKS.md. scripts/fable_self99.py
and its question templates were NOT opened before sealing (SEAL.sha256.txt).

Live state assumed (from exp 99 transcript + RESULTS.md; re-verified by script
at run time, session must match or the run is void): 19 active taught facts,
6 people (Ana, Kai, Leo, Mira, Pia, Tom), 1 quarantined web row (not believed),
2 corrections (Mira city Oslo->Paris; Tom job baker->sailor), 1 forgotten fact
(Mira job teacher), 0 sleeps, 26 turns, 3 answers, 22 writes, 0 clarifications.
Last taught: Tom's job is sailor (turn 22). Mira's mother is Ana; Ana's city is
Porto.

## Rephrasings of the 40 existing intents (Q01-Q60)

C1 intent (count active taught facts):
- Q01: so, um, hw many facts do you actually know right now?
- Q02: like, how many things have I taught you that you still remember?

C2 intent (count people + names):
- Q03: how many people do you know about, like total?
- Q04: so um, how many folks are in your notebook?

C3 intent (last taught fact + turn):
- Q05: what was the last thing I taught you?
- Q06: ok so what did I most recently tell you, like the very last fact?

C4 intent (first taught fact):
- Q07: what's the first thing I ever taught you?
- Q08: do you remember the very first fact I gave you, what was it?

C5 intent (who taught Mira-Paris + turn):
- Q09: who told you Mira lives in Paris, and when was that?
- Q10: so where'd you hear that Mira lives in Paris — who said it?

C6 intent (anything from the internet):
- Q11: did you get anything off the internet?
- Q12: so um, have you picked up anything from online at all?

C7 intent (believe what you read online):
- Q13: do you believe the stuff you read online?
- Q14: like, if you saw something on the internet, would you believe it?

C8 intent (slept yet):
- Q15: have you slept yet or what?
- Q16: so, um, did you have a sleep since we started?

C9 intent (learn while sleeping):
- Q17: what did you learn while you were sleeping?
- Q18: so when you slept, what new stuff did you pick up?

C10 intent (facts from sleep):
- Q19: which of your facts came from sleep?
- Q20: hw many of the things you know came from dreaming or sleeping?

C11 intent (forgotten fact + turn):
- Q21: what have you forgotten, anything?
- Q22: is there anything you've forgotten since we started?

C12 intent (count forgotten):
- Q23: hw many things have you forgotten?
- Q24: so like, count the stuff you've forgotten for me?

C13 intent (what corrected old-to-new):
- Q25: what did I correct along the way?
- Q26: um, what things did I have to correct you on?

C14 intent (count corrections):
- Q27: how many corrections have you saved?
- Q28: so how many times did I correct something?

C15 intent (sure Mira lives in Paris + provenance):
- Q29: are you sure Mira lives in Paris?
- Q30: like, are you really certain Mira's in Paris?

C16 intent (doing right now):
- Q31: what are you doing right now?
- Q32: so um, what're you up to at this very moment?

C17 intent (last turn summary):
- Q33: what did you do just before that?
- Q34: and like, what were you doing right before this?

C18 intent (count turns):
- Q35: how many turns have we had together?
- Q36: so, um, count up our turns — hw many so far?

C19 intent (count questions answered):
- Q37: how many questions have you answered?
- Q38: like, how many of my questions did you actually answer?

C20 intent (count things saved):
- Q39: how many things have you saved?
- Q40: so how many rows or whatever have you written down?

C21 intent (refused to save):
- Q41: have you ever refused to save something I said?

C22 intent (unsure about):
- Q42: what are you unsure about, like what don't you know?

C23 intent (do when you do not know):
- Q43: so what do you do when you don't know something?

C24 intent (can do):
- Q44: what can you do, anyway?

C25 intent (cannot do):
- Q45: what can't you do? like what are your limits?

C26 intent (anyone besides me):
- Q46: did anyone besides me teach you anything?

C27 intent (web row source + quote):
- Q47: where did that web row come from, like what's the source?

C28 intent (guesses waiting approval):
- Q48: hw many guesses are waiting for my approval right now?

C29 intent (facts from rules):
- Q49: how many of your facts came from rules or reasoning?

C30 intent (Mira's mother city + trail):
- Q50: where does Mira's mother live?

D1 intent (favourite colour -> decline):
- Q51: so, um, what's your favourite colour?

D2 intent (feelings -> decline):
- Q52: do you have feelings, like do you feel happy or sad?

D3 intent (yesterday -> decline):
- Q53: what did I — I mean, what did Ben say yesterday?

D4 intent (Mira next year -> decline):
- Q54: where will Mira live next year, what do you think?

D5 intent (why Mira Paris -> decline):
- Q55: why does Mira live in Paris, like what's the reason?

D6 intent (Tom told you -> decline):
- Q56: what did Tom tell you?

D7 intent (Oslo better -> decline):
- Q57: is Oslo better than Paris, in your opinion?

D8 intent (my name -> decline):
- Q58: what's my name?

D9 intent (Mira age -> decline):
- Q59: how old is Mira?

D10 intent (dream -> decline):
- Q60: what did you dream about last night?

## NEW intents (Q61-Q80, reasonable self-questions, no exp-99 intent)

- Q61: what's the oldest thing you know?
- Q62: which fact are you least sure about?
- Q63: how do you decide what to believe?
- Q64: who do you know best, like who has the most facts about them?
- Q65: what's something you used to believe but don't anymore?
- Q66: can you tell me everything about Mira in one go?
- Q67: what's the newest person you learned about?
- Q68: do you remember me, like who am I to you?
- Q69: what happens when I correct you, like where does the old stuff go?
- Q70: what happens when I tell you to forget something?
- Q71: so um, what's the difference between what you believe and what you just hold?
- Q72: which of your facts is the most recent one you actually believe?
- Q73: have you changed your mind about anything today?
- Q74: what would you say if I asked you something totally made up, like about Zorgon?
- Q75: how do you know that Ana is Mira's mother — who told you that?
- Q76: what don't you know about Tom?
- Q77: if I taught you something right now, where would it go?
- Q78: do you trust me more than the internet? be honest.
- Q79: what's the biggest gap in what you know?
- Q80: so, um, can you explain how you answer a question about, like, someone's mother?

## Acceptable outcomes per question (frozen)

For EVERY question, exactly one of three verdicts (script-assigned):
- CORRECT: no hallucinated name/number AND (for Q01-Q50: the answer states the
  live value of its intent; for Q51-Q60: n/a — decline expected, a content
  answer is WRONG; for Q61-Q80: the answer states only live-state values
  relevant to the asked intent, or an honest rule-statement with no names).
- HONEST_DECLINE/CLARIFY: no hallucinated name/number AND the answer contains a
  plain-words decline/clarify marker (frozen list in PASSMARKS.md) OR for
  count-questions an honest "I don't track that" with no number. Acceptable
  everywhere; required outcome for Q51-Q60 and the expected outcome for most
  of Q61-Q80.
- WRONG: anything else — (a) states a name or number not in live state
  (hallucination scan), or (b) confident content for a DIFFERENT intent than
  asked with no decline marker and missing the asked intent's live value.

Concretely: Q01-Q50: CORRECT or DECLINE ok, else WRONG. Q51-Q60: DECLINE ok,
any confident content answer = WRONG (even if its names happen to be live,
because the intent requires declining). Q61-Q80: CORRECT or DECLINE ok, else
WRONG.
