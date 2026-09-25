# CPU previews for road-map R2 and R4 (sleep research thread, 2026-09-25; dev only, not registered)

Small models (width 256), copy phase only (3,000 steps, batch 64, lr 3e-4), seed 2, 296's generator.
Practice never includes three-step. Dev = 200 generated items per kind (seed 777), not a panel.
Numbers are raw right / checked right (after the fact-check) of 200.

## R2: shared chain-step input (rsn-355's change), plain net, 03:35 UTC
| input | one-step | two-step | three-step (never practised) |
|---|---|---|---|
| old (one slot per step) | 200 / 200 | 141 / 91 | 0 / 0 |
| shared chain-step input | 199 / 199 | 137 / 83 | **64 / 13** |

- Suggested (1 seed, small, copy only): the shared input lets the net answer some three-step questions it
  never practised (64 of 200 raw), where the old input gets none. One- and two-step barely change.
- Most of those answers fail the fact-check (13 checked): the check needs every row of the chain cited, and
  the support head has never had to cite a third row. The registered rsn-355 scores checked answers, so
  its H1 (≥ 6/30 checked) may miss even if the net finds the right answer. Watch raw vs checked there.

## Loop previews (same setup, loop = 2 shared layers re-applied, no step embedding), 04:35 UTC
raw / checked of 200, at 6 | 12 | 20 thinking rounds

| loop | two-step | three-step (never practised) |
|---|---|---|
| old input | 162/97 · 165/105 · 165/104 | 0/0 · 0/0 · 0/0 |
| shared input | 98/17 · 92/18 · 93/18 | 74/1 · 76/1 · 75/1 |
| shared input + one step per round, then hold (R4) | 95/30 · 98/45 · 97/48 | 58/0 · 58/3 · 57/2 |

(one-step is 197-200 raw everywhere; R4 also scored at 2, 3, 4, 40 rounds: three-step raw 42, 53, 52, 58.)

- Suggested (1 seed, small, copy only): in the loop, the shared input again opens three-step a little (raw
  ~75/200), but two-step drops a lot (raw ~95 vs 165), unlike the plain net where two-step held.
- Almost none of the three-step answers pass the fact-check (1-3/200): the net never learned to cite a third row.
- More thinking rounds do not help in any arm (flat from 6 to 20; R4 flat from 3 to 40 once it starts).
- R4 as built (answer so far at every round, supervised from the solver's chain) does not beat the plain
  shared-input loop on three-step and does not make extra rounds useful. Not worth a rental as it stands.
- Taken with rsn-355 (full-size plain: three-step 0/30, even raw): answering one step past practice is not
  coming from input or loss tweaks at this scale. The pre-registered next step stands: practise three-step
  (round 1's C1) with the shared input, and test four-step as the new "past practice" question.
