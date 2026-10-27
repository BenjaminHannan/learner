# Experiment 43C — segment-relative positions — pass marks (fixed before any full run)

Date: 2026-09-21. Script: scripts/fable_lengthgate43c.py. Seeds 4102, 4103, 4104.
Written after 43A was read (all of G1-G4 failed) and after a probe showed the length-12
errors are wrong digits in the first 1-3 answer places, not early stops.
One change from the registered base: the answer's positions restart, so input digit i and
answer digit i share a position number. Same test inputs as 43A.

Copy-like ops = ROTL1, INC3, SWAP (source digit is a fixed shift away).
End-relative ops = REV, FOLD, REV+INC1 (source digit is counted from the end).

| Mark | Condition | Needed |
|---|---|---|
| C0 | validity: mean accuracy on lengths 4-8 >= 0.95 | per seed |
| C1 | copy-like ops, length 12, mean >= 0.90 | 3/3 valid seeds |
| C2 | copy-like ops, length 16, mean >= 0.80 | 3/3 valid seeds |
| C3 | all six ops, length 12, mean >= 0.80 (= 43A's G2) | 3/3 valid seeds |
| C4 | end-relative ops, length 12, mean >= 0.50 | 3/3 valid seeds |

Reading rules fixed now:
- C1 pass, C4 fail -> shared position numbers solve "same place" skills; "count from the end" skills need a second position signal (distance to the end of the input). That is the next single change.
- C3 pass -> this becomes the base for the next sleep experiment and for a train-1-3 / test-4-8 run.
- C1 fail -> the wall is not position numbering alone; next rung = relative-position attention.
- Architecture result about old skills only; not a sleep result; toy only.
