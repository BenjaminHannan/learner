# slp-358lp blind recount

**Verdict: FAIL confirmed.** V is met on both seeds. P1, P2 and P3 fail on both seeds. P4 passes on both. The
proved-wrong clause is **not triggered**: seed 7 meets it (+5, -2) but seed 8 does not (sums8 +13). Every count in
RESULTS.md matches the raw JSON and the logs. RESULTS.md makes two claims the numbers do not support (see
Disagreements).

Seal: `sha256sum -c SEAL-code.sha256.txt` gives all 6 OK (the lp, n2, n, rsn358a_envs and rsn358a_run scripts and
PASSMARKS.md). The seal commit f20fd114f (2026-09-26 02:21:04 UTC) is an ancestor of the results commit 4a256f41d
(03:33:48 UTC). None of the sealed files changed between the two commits.

## Marks after night 3 (counted from runs/slp358lp-seed{7,8}.json, `morning["3"]`)

| mark | pass | seed 7 | seed 8 |
|---|---|---|---|
| V day_grids S - N (400) | >= +20 | 82 - 61 = **+21** met | 194 - 101 = **+93** met |
| P1 transfer_sums8 L - S (200) | >= +20 | 102 - 97 = **+5** FAIL | 145 - 132 = **+13** FAIL |
| P2 transfer_grids6 L - S (200) | >= +20 | 16 - 18 = **-2** FAIL | 69 - 65 = **+4** FAIL |
| P3 L - F, sums8 / grids6 | >= +10 on both | 102-100 = **+2** / 16-19 = **-3** FAIL | 145-146 = **-1** / 69-64 = **+5** FAIL |
| P4 L vs N - 6, harm_sums4 / harm_grids4 | both | 290 >= 225 / 154 >= 134 PASS | 300 >= 272 / 198 >= 167 PASS |
| proved wrong: L - S <= +5 on both transfer tests | both seeds | yes (+5, -2) | no (+13) |

Report-only after night 3: day_sums L-S / L-F = +4 / -2 (seed 7) and +7 / +12 (seed 8); day_grids L-S / L-F =
+5 / +6 (seed 7) and +4 / -1 (seed 8). Minutes 40.0 and 39.0. excluded_day_items_in_tests = 0 on both seeds.
The N arm's scores equal the base scores every morning, as they should.

Logs: all four lines of each log (the base line and mornings 1-3) match the JSON exactly, and so do the final
minutes. The L and F arms took the same number of day steps each night (seed 7: 155/150/147; seed 8: 141/155/163).
That confirms they drew the same candidates and the same rehearsal batches.

## Disagreements with RESULTS.md

All tables and marks in RESULTS.md agree with my counts. Problems are in the prose.

1. **Line 37, "Nights 1-2 show the same picture: L, F and S within a few counts of each other on every test": wrong.**
   - Seed 7, night 1: L trailed on day_sums (L 272, S 308, F 302: -36 against S) and on transfer_sums8 (L 61, S 79,
     F 79: -18).
   - Seed 7, night 2: L still trailed on transfer_sums8 (L 79, S 90: -11).
   - Seed 8, night 1: harm_grids4 spread 174 to 191 (L 174, F 191).
   - The day-try scores the next day agree (seed 7 day 2 sums: L 224, S 234, F 236).
   - The honest summary is that the gaps close by night 3. Early on, L was sometimes clearly behind.
2. **Line 42-43, "the night's gain comes from practising the day's checked puzzles at all": goes beyond this run.**
   slp-358lp has no rehearsal-only (R) arm or placebo arm. It cannot separate "the day's checked puzzles" from
   "300 more training steps". Only slp-358n/n2 could speak to that.
3. Line 36, "picks spread almost evenly": true, but it is not evidence of anything. The 4 candidates are drawn
   independently from the same distribution, so the chosen index is spread evenly whatever the score measures. The
   forced pick 0 on a night's first step adds at most one pick per night. The run did not log the scores or the kind
   of each pick, so it cannot show that the score carried any signal.
4. Line 6, "all OK at launch": I cannot check this. Nothing in the run records it. The seal checks OK now, and the
   seal commit came before the results commit.
5. Minor: the PASSMARKS header says "fixed ... 2026-09-26 03:00 UTC", but the file was committed at 02:21 UTC. It
   is probably a typo. It does not affect the order: the results commit came at 03:33, after about 40 minutes of
   running time.

## Code check (scripts/claude_slp358lp_nights.py)

- **L picks the best of K=4 and F picks the worst: confirmed.** The score is the cosine between -grad(loss) and
  `move`. `move` is an EMA with decay 0.9 of the per-step weight change `after - before`. L takes the max score and
  F takes the min.
- **S is exactly the slp-358n2 night: confirmed.**
  - It calls `N2.night_batches("S", ...)` with the same nrng seed formula (58900 + 10*seed + day) and runs
    `N.train_steps`.
  - Its AdamW (lr 1e-4, wd 0.1) is created once and kept across nights, as in n2.
  - Pretraining, tests (seed 58600), cfg and scoring are the same code. cfg in the JSON equals `N.CFG`.
  - One caveat: the depth draws (the `rr` stream) are shared by the arms in turn, so S's depths differ from an n2
    run. This matches n2 in distribution.
- **Rehearsal, steps, lr and tests are identical in kind but not batch-for-batch.**
  - Rehearsal: the same `N.practice_batch`, with p = 0.5 per step.
  - Steps and lr: 300 steps at 1e-4.
  - L/F consume the nrng stream faster than S (4 candidates per day step, "streams part", as the code says). After
    the first day step, S sees different rehearsal batches and different day batches from L/F.
  - L and F see identical batches, so L vs F is the cleanly matched comparison (it is P3).
- Docstring detail: "The first day step of each night has no movement yet: take candidate 1." In the code, `move`
  is None only before the night's very first step. Step 1 is rehearsal about half the time, and then the first day
  step is scored against one rehearsal step's movement.
- The scoring passes do not change the weights. `train_steps` clears the grads with `set_to_none=True`, and the net
  has no dropout or other torch randomness. So the "4 extra gradient passes" affect compute only.

## Design notes: marks easier or harder than they look

- **Each candidate is scored at a different unroll depth, and not the depth it is trained at (makes P1-P3 harder).**
  One `srr` serves all 4 candidates, and each `loss_of` call draws its own (total, k). So the scores of the 4
  candidates mix batch content with depth (k from 1 to 4 gradient rounds, total from 1 to 12). The step then trains
  the chosen batch at a fresh depth from `rr`. This noise dilutes any real content signal and pushes L and F toward
  a random pick (suggested, untested).
- **Gradient vs movement mismatch.** The score uses the raw, unclipped gradient (clipping does not change a cosine).
  The movement is the AdamW step: per-coordinate preconditioned, plus decoupled weight decay (lr*wd*p = 1e-5*p per
  step). The movement also includes the rehearsal steps (about half of all steps), not just day steps. Weight decay
  always points toward zero, so it adds up coherently in the EMA while gradient parts partly cancel. Its share of
  `move` may be larger than one step's share suggests. That share was not measured (untested).
- **A possible hidden second change: the kind mix.** The per-kind embedding and heads mean the cosine may largely
  reflect kind (sums vs grids), matching whatever the last few steps trained. That would tilt L toward the recent
  kind and F away from it, which changes the even kind mix that n2's one fix set up. The run logged only the pick
  index, so this cannot be checked (untested).
- **L vs S is less clean than L vs F.** Different batch streams (above) and different `rr` depth draws add
  arm-to-arm noise to P1/P2. Seed 8 shows that noise: L-S = +13 on sums8 while F-S = +14.
- **P4 is almost automatic.** It compares L with N (no night), not with S, and every night arm beats N on both
  harm tests every morning. With harm_sums4 at 300/300 for S, L and F on seed 8, it could not detect harm there.
- **P2 and P3 on grids6 are near the floor on seed 7.** S scores 18/200, so P2 needs L >= 38 (double S). Seed 7's
  V is only just met (+21 vs +20).
- **Mark stringency.** A +20/200 transfer gain is large next to the arm-to-arm spread seen here (up to about 14 on
  sums8). The FAIL is clear because the flipped arm matches L on both seeds, not only because L missed +20.
