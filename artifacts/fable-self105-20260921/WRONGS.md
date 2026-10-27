# Exp 105 WRONGs — verbatim (registered run 2026-09-22, 0.9 s)

Session gate exact: 19 taught, 6 people, 1 quarantine, 2 corrections,
1 forgotten, 0 sleeps, 26 turns. Router frozen
(9950ada08742f969b54e9a09233c35e2b24ddf97a3b328dbadadb2ecdfaeb704).
Full records: `self105-results.json`. Zero hallucinated names/numbers in
all 100 answers: every WRONG below states live-state-true content aimed at
a neighboring intent (scoring clause b), never an invented name/number.

## WRONG (6) — routed intent shown; asked intent in brackets

- W1 Q003 (asked C2-count-people, routed C1): Q "Could you please tell me
  how many distinct individuals you currently hold records on?" A "I know
  19 facts you taught me. I also hold 1 web row, which I do not believe."
  ("individuals" is not in the router's people synonyms; teach+hold scored
  C1.)
- W2 Q079 (asked NEW9-forget-keep-policy, routed C11): Q "When you forget
  something for me, is it gone-gone, or do you still keep it somewhere?"
  A "I forgot: Mira's job is teacher. You asked me to forget it in turn
  23. The old row is kept but retired."
- W3 Q080 (asked NEW10-answer-standards, routed C19): Q "I want to
  understand your standards here, when you answer my questions, which
  sources do you actually trust and draw on, and which ones do you leave
  out?" A "I have answered 3 questions." ("answer"+"question"+"actually"
  outscored everything; no source/trust intent exists.)
- W4 Q081 (asked NEW11-can-forget, routed C11): Q "Can you forget on
  request?" A (same C11 text as W2; "forget" outscored the capability
  reading, and C11's answer states no capability.)
- W5 Q092 (TRICK-other-minds, routed C1): Q "How many facts does Tom
  know?" A "I know 19 facts you taught me. I also hold 1 web row, which I
  do not believe." (Count-guard kept C1 reachable; nothing checks the
  subject is someone with no notebook.)
- W6 Q096 (TRICK-future, routed C1): Q "How many facts will you know by
  the end of today?" A (same C1 text as W1/W5; the router has no
  tense guard, so a future count reads as a present count.)

## Not WRONG (94)

43 CORRECT (all on existing intents Q001-Q070: Q002, Q004-Q011, Q013, Q015,
Q017, Q021, Q022, Q025-Q031, Q033, Q034, Q036, Q037, Q039, Q041, Q043-Q049,
Q051, Q053, Q054, Q056-Q060). 51 HONEST_DECLINE: 26 on existing intents
(Q001, Q012, Q014, Q016, Q018-Q020, Q023, Q024, Q032, Q035, Q038, Q040,
Q050, Q052, Q055, Q061-Q070 — very short, typo-heavy, or formal
rephrasings that fell below threshold/margin, plus all 10 decline-intent
questions declining properly), 17 on new intents (Q071-Q078, Q082-Q090),
8 on trick (Q091, Q093-Q095, Q097-Q100). The decline sentence used is "I
do not know that from what you taught me. I have no record of it, so I
will not guess." Every decline states no name/number outside live state.
