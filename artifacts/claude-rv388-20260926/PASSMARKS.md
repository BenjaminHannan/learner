# rv-388 pass marks (thought-memory thread; written 2026-09-26 15:04 UTC by `date -u`, before any test hand is played)

Question: does Creative's learned "is this still solvable?" judge make going back pay off in step-by-step search, and is
that because of what it knows (not just because it prunes)?
Agreed with Creative (12:55 UTC): its feas-24b recipe unchanged, test hands from its held-out hands, an exact-code
ORACLE arm as a report-only ceiling. Code: scripts/claude_rv388.py (sealed below).

## Setup (fixed)
- Proposer: plain MiniCPM5-1B, bf16, CPU, enable_thinking=False. Every step from a state is scored by the log-probability
  of its text ("8 - 3") after the reply prefix; steps giving the same next state are pooled; one is sampled at T = 1.5.
  Depth-first search with code bookkeeping: a wrong final number is banned; a state with every next state banned is a
  dead end and the search goes back one more step.
- Judge: feas-24b's recipe unchanged (seed-792 split, layer 16, l2 100, seed-0 rows); features on 2 CPU threads. The
  refit reproduces feas-24b's seed-0 counts exactly: real 158 of 200 pairs, shuffled 111
  (dev/judge-check.json; on 4 threads the features differ and it gives 155 and 90, dev/judge-check-4threads.json).
- Arms (same hands, same step budget, same random numbers per hand):
  END: go back only at a wrong final number. JUDGE: also set aside a new 3- or 2-number state the judge scores below
  logit 0 (soft: it comes back once every unflagged step at that state is banned). PLACEBO: the same with the
  shuffled-label judge, cut at logit -0.0833, which flags the same share (44.5%) of practice states as JUDGE's cut.
  ORACLE (report only): the flag is exact reachability (feas24.reach).
- Budget 160 model steps per hand, from practice (40 practice hands, seed 1, never test hands): END solved 8 by 60
  steps, 11 by 100, 14 by 160, 14 by 200; 160 is the first budget where END solves at least a third
  (dev/b200/calibrate-seed1.json). Cuts file: cuts.json.
- On the same practice states, the real judge flagged 356 dead and 0 live states; the placebo flagged 346 dead and
  10 live. 772 of 800 entered states were dead.

## Test
Seeds 388101 and 388202: 80 hands each, disjoint, from one fixed shuffle of the 348 solvable held-out hands (the last
25% of feas-24's seed-792 shuffle; no judge test pair came from other hands). Judge training states can still appear
along the way (the split is by state); the share of entered states in the judge's training rows is reported.

## Marks (unit = hand)
- PASS: JUDGE solves at least 6 more hands than END AND at least 6 more than PLACEBO, in both seeds.
- PROVED WRONG: JUDGE solves no more hands than END in both seeds, OR no more than PLACEBO in both seeds (what the judge
  knows adds nothing over pruning the same share at random).
- Anything else: no clear result.
- Report only: ORACLE; steps used; flags on live vs dead states (exact reachability) per arm; judge forward passes per
  arm (the judge is not free compute); share of entered states that were in the judge's training rows.

## Predictions
- P388.1 JUDGE beats END by 6 or more in both seeds (on practice it flagged 356 dead states and no live one).
- P388.2 JUDGE does NOT beat PLACEBO by 6 in at least one seed: nearly every state the 1B enters is dead, so pruning at
  random also helps; the placebo loses only where it sets aside live states. (So I predict no PASS.)
- P388.3 ORACLE solves at least 75 of 80 in both seeds.
