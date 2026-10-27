# lis-320 ADDENDUM-7 note: why pilot 5 is the test, and the reader gap the group-speaker drop creates
# (additive note; ADDENDUM-7 stays as sealed. Written before any pilot 5 result is read.)

Written 2026-09-26 22:58 UTC by the reading thread, at the Thread manager's review (22:57 UTC).

## Fairness
The group_speaker drop is a code filter I wrote after seeing pilot 4's three wrong rows. Its re-run on pilot 4's raw rows
(344 of 419 kept, all three wrong rows dropped) is a check that the code does what I meant, not evidence that it works:
it was built to catch exactly those rows. The fair test is pilot 5 on fresh seed 325, whose rows nobody has seen, with a
fresh hand-read agent and the marks fixed in ADDENDUM-7.

## Known reader gap (named now, for step 2; the marks do not cover it)
Real users say "we live in X" and "our cat is Y". With every group-speaker turn dropped, the lis-320 reader is never
trained on such turns, so it is never shown how to save a fact shared by the user and someone else. The compiled facts
table will miss shared facts by design. This is a known gap of the lis-320 reader, not something R1-R7 or C1 test, and it
goes on the step 2 list (with the history-owner compiler) as its own item: label shared facts for both owners.
Size, counted on DEV text only (never on a sealed panel), with the name-free part of the rule (so "Mira and i" is not
counted; a lower bound): 16 of 336 everyday-chat DEV turns (5%) and 26 of 194 e2e331 DEV bank turns (13%) have
group-speaker wording. That is turns with such wording, not shared facts; many are small talk ("we should get her
something"). In the seeder's output (pilot 4 raw) 19 of 419 turns were dropped for it.
