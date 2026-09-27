# Creative stopping toy — freeze note (Fable, 22 Sep 2026; written BEFORE the test suite is run)

Dev-phase calibration changes (all made on the dev suite only; first dev run kept in dev-v0-uncalibrated/):
1. World: relations come in sibling families (keep 0.85, add 0.02) so neighbouring rules overlap -> near-misses exist.
2. Filter: 12 balanced examples (6 yes / 6 no) instead of 6; keep threshold 0.85.
3. Dreamer and filter are one model (Ben, 21 Sep): fresh dreams drawn ∝ exp(10 * filter score / temperature).
4. Unchecked good ideas carry over in a backlog.
5. Stop rule: count-based expected-value stop and stall stop switched OFF (Ben: do not penalise thinking).
   New evidence-based stop "out of ideas I believe in": backlog empty AND Good-Turing unseen share among
   kept-idea dreams < 0.10 with >= 14 kept dreams. Caps doubled: 12 rounds / 96 dreams / 24 checks.
6. Meter caps now read at run time (bug: they were baked in as class defaults).

Pass marks: the six coded marks are UNCHANGED from design doc 33. Verdict = coded verdict.
Secondary, descriptive only (Ben's priorities, declared here before the test): marks 1, 2, 6 and
A correct give-ups >= 60% of unsolvable items. Threshold chosen after seeing dev (70-80%); not a claim.

Prediction (coordinator): coded verdict KEEP_FIXED_N, p=0.90 (dev fails marks 3, 4, 5 in every seed).
Mark 2 passes in 3/3 seeds, p=0.65. Zero false FOUND in A/B/C, p=0.97. Secondary passes 3/3, p=0.55.
