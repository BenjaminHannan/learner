# Exp 100 WRONGS + MISSES — verbatim (registered run 2026-09-22, 0.9 s)

Session gate exact: 19 taught, 6 people, 1 quarantine, 2 corrections,
1 forgotten, 0 sleeps, 26 turns. Full records: `self100-results.json`.

## WRONG (5) — confident content for a different intent, all names/numbers live

- W1 Q14 (asked C7-belief): Q "like, if you saw something on the internet,
  would you believe it?" A "Yes. I hold 1 quarantined web row. I filed it
  but I do not believe it." (C6 content; leading "Yes" mis-affirms belief.)
- W2 Q23 (asked C12-count): Q "hw many things have you forgotten?" A "I
  forgot: Mira's job is teacher. You asked me to forget it in turn 23. The
  old row is kept but retired." ("hw many" missed the count branch.)
- W3 Q24 (asked C12-count): Q "so like, count the stuff you've forgotten for
  me?" A (same C11 text as W2; "count" missed the count branch.)
- W4 Q28 (asked C14-count): Q "so how many times did I correct something?"
  A "You corrected: Mira's city from Oslo to Paris; Tom's job from baker to
  sailor." (C13 list instead of the count 2.)
- W5 Q69 (asked NEW-process): Q "what happens when I correct you, like where
  does the old stuff go?" A (same C13 text as W4; pairs, not the
  kept-both-rows process.)

## MISSES (19) — rephrasings declined by the exact fallback (verbatim answer)

Fallback text (all 19): "I do not understand that question. Ask me about
what I know, where it came from, or what I am doing."
- Q01 "so, um, hw many facts do you actually know right now?" ("hw many")
- Q02 "like, how many things have I taught you that you still remember?"
  ("things", not "facts")
- Q04 "so um, how many folks are in your notebook?" ("folks", not "people")
- Q05 "what was the last thing I taught you?" ("taught" lacks "teach")
- Q06 "ok so what did I most recently tell you, like the very last fact?"
  ("tell", not "teach")
- Q08 "do you remember the very first fact I gave you, what was it?"
  ("first fact", not "first thing")
- Q09 "who told you Mira lives in Paris, and when was that?" ("told", not
  "taught")
- Q10 "so where'd you hear that Mira lives in Paris — who said it?"
- Q16 "so, um, did you have a sleep since we started?" (needs "have you
  slept")
- Q18 "so when you slept, what new stuff did you pick up?" (needs
  "while sleeping"/"learn")
- Q30 "like, are you really certain Mira's in Paris?" (needs "are you sure")
- Q32 "so um, what're you up to at this very moment?"
- Q34 "and like, what were you doing right before this?" (needs "just
  before")
- Q36 "so, um, count up our turns — hw many so far?" ("hw many")
- Q38 "like, how many of my questions did you actually answer?" (needs exact
  "how many questions have you answered")
- Q40 "so how many rows or whatever have you written down?"
- Q43 "so what do you do when you don't know something?" (contraction
  "don't" vs "do not")
- Q44 "what can you do, anyway?" (exact-equality "what can you do?" fails on
  ", anyway?")
- Q20 (C10, answered by the dream-decline branch, marker-hit, value-absent):
  Q "hw many of the things you know came from dreaming or sleeping?" A "I do
  not dream. I have slept 0 times and hold 0 sleep-derived facts."

## Clean (56)

27 CORRECT (Q03, Q07, Q11, Q12, Q13, Q15, Q17, Q19, Q21, Q22, Q25, Q26, Q27,
Q29, Q31, Q33, Q35, Q37, Q39, Q41, Q42, Q45, Q46, Q47, Q48, Q49, Q50);
10/10 decline rephrasings Q51-Q60 decline properly; 18/20 new intents decline
honestly (Q61-Q68, Q70-Q80 except Q69; Q78's C6 content carries the honest
"do not believe it" marker so it scores DECLINE). Zero hallucinated
names/numbers in all 80 answers.
