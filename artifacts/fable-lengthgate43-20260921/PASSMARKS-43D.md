# Experiment 43D — relative-position attention — pass marks (fixed before any full run)

Date: 2026-09-21. Script: scripts/fable_lengthgate43d.py. Seeds 4102, 4103, 4104. Same test inputs as 43A/43C.
Sealed rung after 43C failed: no position is added to token vectors; position enters only as a learned
attention bonus on clipped index differences (-4..+4). Arms: rel-start, rel-both (adds "my start index minus your END index").

Expectation written down before the run: skills whose source digit is a FIXED small step away (INC3, ROTL1)
should now work at any length; count-from-the-end skills (REV, REV+INC1) should work only in rel-both;
SWAP (needs odd/even place) and FOLD (needs place/2) may still fail because a clipped difference carries no parity or halving.

| Mark | Arm | Condition | Needed |
|---|---|---|---|
| D0 | each | validity: mean of six ops on lengths 4-8 >= 0.95 | per seed |
| D1 | rel-both | INC3 and ROTL1 each >= 0.90 at length 12 AND at length 16 | 3/3 valid seeds |
| D2 | rel-both | REV and REV+INC1 each >= 0.90 at length 12 AND at length 16 | 3/3 valid seeds |
| D3 | rel-start | INC3 and ROTL1 each >= 0.90 at length 12 AND at length 16 | 3/3 valid seeds |
| D4 | rel-both | all six ops mean >= 0.80 at length 12 (= 43A's G2) | 3/3 valid seeds |

SWAP and FOLD are reported per seed, no mark of their own.
Reading rules fixed now:
- D1+D2 pass -> relative attention with start+end indices is the position system going forward; skills needing parity/halving get one further change (an odd/even place feature, or recurrence).
- D1 pass, D2 fail -> end index signal is not being used; inspect bias tables before anything else.
- D1 fail -> position is not the (only) cause; stop position work and wait for the outside review.
- Architecture result about old skills; not a sleep result; toy only.
