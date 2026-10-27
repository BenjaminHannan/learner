# slp-358n2 blind recount (verifier, 2026-09-26)

**Recount verdict: PASS, as registered.** M1, M2 and M3 hold on both seeds. On seed 3, M1 sums passes only by the
ceiling rule (S 382, R 366, both ≥ 360; S − R = +16, which is below +20). So on seed 3 the sums tell us nothing, and
seed 3's M1 rests on grids. The proved-wrong clause is not met on either seed. My numbers agree with RESULTS.md. That
file leaves out a few things the marks said to report (listed below). Its timestamps and ordering claims can be
checked only partly.

Method: I read PASSMARKS.md and both docstrings first. I wrote my own recount over `runs/slp358n-seed{3,4}.json`
(key `morning` -> `"3"`) and checked the logs. Only then did I read RESULTS.md. I ran no training and no `run`/`smoke`
command. The code checks below ran the real `night_batches` and `shuffled_answers` from the sealed files, with torch
stubbed out and no model. torch is not installed in this container.

## Marks (after night 3; integer counts)

Raw counts:

| test (items) | seed | S | R | Z | N |
|---|---|---|---|---|---|
| day_sums (400) | 3 | 382 | 366 | 1 | 312 |
| | 4 | 332 | 264 | 4 | 187 |
| day_grids (400) | 3 | 228 | 149 | 20 | 116 |
| | 4 | 195 | 112 | 4 | 38 |
| harm_sums4 (300) | 3 | 300 | 300 | 119 | 297 |
| | 4 | 274 | 279 | 50 | 225 |
| harm_grids4 (300) | 3 | 213 | 213 | 189 | 208 |
| | 4 | 195 | 208 | 132 | 109 |
| transfer_sums8 (200) | 3 | 149 | 89 | 0 | 56 |
| | 4 | 76 | 44 | 0 | 21 |
| transfer_grids6 (200) | 3 | 65 | 23 | 0 | 15 |
| | 4 | 27 | 0 | 0 | 0 |

| mark | pass rule | seed 3 | seed 4 |
|---|---|---|---|
| M1 grids S − R | ≥ +20 | 228 − 149 = **+79** PASS | 195 − 112 = **+83** PASS |
| M1 sums S − R | ≥ +20, or S and R both ≥ 360 | 382 − 366 = **+16**; both ≥ 360, so PASS by ceiling (uninformative) | 332 − 264 = **+68** PASS |
| M2 grids S − Z | ≥ +20 | 228 − 20 = **+208** PASS | 195 − 4 = **+191** PASS |
| M2 sums S − Z | ≥ +20 (ceiling not reached: Z = 1 / 4) | 382 − 1 = **+381** PASS | 332 − 4 = **+328** PASS |
| M3 harm_sums4 S ≥ N − 6 | | 300 vs 291 (S − N = **+3**) PASS | 274 vs 219 (**+49**) PASS |
| M3 harm_grids4 S ≥ N − 6 | | 213 vs 202 (**+5**) PASS | 195 vs 103 (**+86**) PASS |
| proved wrong (S − R ≤ +5 on grids AND sums, no ceiling) | | no (+79 / +16, and sums at ceiling) | no (+83 / +68) |

Report-only items, recounted:
- S − R after nights 1 / 2 / 3. Grids: seed 3 +47 / +51 / +79, seed 4 +60 / +73 / +83. Sums: seed 3 +43 / +28 / +16,
  seed 4 +43 / +34 / +68.
- Harm vs N at night 3 (sums4, grids4). R: seed 3 +3 / +5, seed 4 +54 / +99. Z: seed 3 −178 / −19,
  seed 4 −175 / **+23**. On seed 4 the placebo still beats no night on 4x4 grids.
- The day's own tries (sums right, grids right, out of 600 items). Day 1 is the same for every arm: seed 3 233 / 82,
  seed 4 126 / 24. Day 3: seed 3 S 282 / 165, R 265 / 121, Z 15 / 70, N 228 / 98. Seed 4 S 231 / 142, R 196 / 78,
  Z 6 / 1, N 124 / 27.
- `excluded_day_items_in_tests` = 0 on both seeds (JSON). I recomputed it from the code's own seeds (58600 tests;
  58700 + 10·seed + day for the day items) and also got 0. I also found 0 *structural* near-duplicates: the same grid
  pattern with different symbol names, or a sum with its two numbers swapped.
- Logs agree with the JSON. The `base` line and the `morning 1/2/3` lines in `seed3.log` and `seed4.log` exactly
  match `morning` in the JSON. N at night 3 equals base, as expected, since N is never trained. The logs do not print
  `excluded_day_items_in_tests`. Only the JSON has it.

## Seal and ordering

- `sha256sum -c SEAL-code.sha256.txt`: all 6 files **OK**. These are the wrapper, the sealed slp-358n runner,
  rsn358a_run, rsn358a_envs, blurt1 and PASSMARKS.md.
- git: PASSMARKS.md, SEAL and `claude_slp358n2_nights.py` were all first (and only) committed in **280d665a8, 2026-09-26
  00:29:05 +0000**, on main. The sealed runner has been unchanged since b071ed0f0 (00:00:31). envs and run.py are older.
- Result files: `runs/` and RESULTS.md are git-ignored (`artifacts/`) and not committed. All four run files have mtime
  **00:51:50.44** (they were written within 0.1 ms of each other), and so does RESULTS.md. So they were copied or
  written in one batch. Their mtime is an upper bound on when the runs finished, not a record of when they ran.
- Ordering is **consistent but not proven, and the window is tight**. The runs took 20.1 min (seed 3) and 21.8 min
  (seed 4) by the JSON's own clock. To have started after the seal commit, seed 4 must have started between 00:29:05
  and about 00:30:02, and its result must have landed here almost as soon as it finished. The seeds must also have
  run in parallel, because run back to back they need about 42 min, more than the 22.75 min available. Nothing
  records a start time or a code hash in the outputs. torch is absent here, so the runs happened in some other
  environment. That the run used the sealed code is **untested**.
- Minor file-time notes. `scripts/__pycache__/claude_slp358n2_nights.cpython-311.pyc` dates from 00:28:40, before the
  seal. I checked its bytecode against the sealed source and it is identical, so it looks like a compile check and
  does not show that anything ran.
- **Text timestamps disagree with the files.** PASSMARKS says "fixed before any run; 2026-09-26 ~00:50 UTC", but it
  was committed at 00:29:05. Read literally, "~00:50" is the minute the runs finished. RESULTS says "~01:15 UTC", but
  the file mtime is 00:51:50. The git commit is the authoritative time. These labels look hand-written and wrong.

## Disagreements with RESULTS.md

No number disagrees. I checked every count in its table, every mark cell, the nights 1/2/3 grids gaps, and the seed-4
harm comparison with R. The things below are omissions or claims that go past the evidence:

1. **The day's own tries are not reported.** PASSMARKS lists them under "report" (shown). The numbers are above.
2. **`excluded_day_items_in_tests` is not reported** in RESULTS.md. It is 0 on both seeds (shown).
3. **Harm of Z and R vs N is only partly reported.** R − N is never stated (seed 4: +54 / +99). For Z, only
   "hurt practised sums" is given. On seed 4, Z beats N on harm_grids4 (132 vs 109), which is not mentioned (shown).
4. Mornings after nights 1 and 2 are reported for grids only. The sums gaps (+43/+28 and +43/+34) are left out. On
   seed 3 the sums gap shrinks every night as R climbs to the ceiling (shown). This is minor.
5. The "~01:15 UTC" header and "run unchanged" cannot be checked. There is no code hash in the outputs and the run was
   done off this machine (untested).
6. Plain words: "no worse than no sleep on what it already knew" is true by M3. But on seed 4 the N baseline is weak
   (base harm_grids4 109/300), so that bar is easy. On seed 4, sleep is *below* the rehearsal night on the practised
   sizes (−5 sums4, −13 grids4). RESULTS says this under report-only but not in the plain summary (shown for the
   numbers; whether it is real interference is suggested).

**Is the plain-words summary fair?** Mostly yes. The headline gaps (+79 / +83 grids, +68 sums on seed 4) are correct.
It says seed 3 sums sat at the ceiling, it labels transfer as report-only, and it states that the night material is
tested-size practice with code-checked answers. Two gaps: it leaves out the small seed-4 shortfall against rehearsal
on the practised sizes. And "sleeping on the day's checked answers" is a metaphor. What was shown is that half of 300
small steps spent on correctly answered new-size puzzles beats spending all 300 on old sizes. That is expected of
supervised practice on the tested distribution, and nothing about it is specific to sleep.

## Code concerns (the one change)

- **night_batches gives day practice evenly to sums and grids: shown.** A day batch first picks the kind
  (`rng.choice(["grids","sums"])`) and then a shape within that kind. I executed the real function on the real day
  items with the run's seeds. Per night, S had 70–93 sums batches and 71–88 grids batches, with 131–143 rehearsal
  batches. Over 6 nights the totals were 492 sums, 469 grids and 839 rehearsal. The old slp-358n function gave 613
  sums, 298 grids and 889 rehearsal on the same items. So the split is even in expectation, and each night has only
  binomial noise. That this reproduces the actual run's plan is suggested: it assumes the same Python `random`
  behaviour, and the logs do not record the mix.
- **The wrapper does replace what the sealed runner calls: shown.** `N.run.__globals__ is N.__dict__`, and after the
  wrapper is imported, `N.__dict__["night_batches"]` and `N.__dict__["shuffled_answers"]` are the wrapper's
  functions. `run()` looks both names up in module globals at call time. The wrapper's `N.main()` runs N as the
  imported module (not `__main__`), so N's code is not defined twice.
- **S and Z get the same batch plan: shown.** Both use the same `nrng` seed, and with the same item order the day
  batches draw the same puzzles. Only the answers differ.
- **The grid placebo is what the docstring says: shown.** Every blank cell gets a random symbol from that puzzle's own
  symbols, and given cells get 0. Consequences: about 20% of blank cells are right by chance (0.194–0.205 per night),
  and 0/300 grids per night are fully right. The sums placebo is the unchanged shuffle, and 1–4 of 300 sums per night
  keep their true answer by chance. The placebo is *actively wrong* rather than neutral: Z drives day_sums to 1–4 and
  harm_sums4 to 50–119. So M2 (S − Z) is an easy bar and mostly measures damage from wrong answers (suggested).
- **S vs R practice amounts: shown.** Both arms get 300 steps at the same learning rate. R gets 300 rehearsal steps.
  S gets about 140 rehearsal steps and about 160 day steps, so S sees about half as much old practice. That works
  against S on M3, so M3 is conservative. R never sees 5–6-digit sums or 5x5 grids at all. S − R therefore mixes up
  "checked answers" with "any exposure to the new sizes". Z separates the two only partly, because Z's answers are
  harmful rather than empty (suggested).
- **Shared `rr` stream: suggested, small.** The loop-length draws (`rr`) are consumed by S, then R, then Z each night,
  so arms get different round counts. This adds noise, not bias in a known direction. It is inherited from the sealed
  slp-358n. I found no dropout by grep, and I did not check whether the net uses any other torch randomness
  (untested).
- **Leaks: day vs tests is clean (shown, above). Practice vs harm tests is untested.** Pretraining and rehearsal draw
  4-digit sums and 4x4 grids without filtering them against harm_sums4 or harm_grids4. This affects every arm. R gets
  the most rehearsal, so any leak would favour R and N over S on harm. It could not inflate S's pass.
- **Seed spread: shown / suggested.** The two seeds' bases differ a lot (day_grids 116 vs 38, harm_grids4 208 vs
  109). There is one run per seed and no interval. S − R on grids is large and the same sign on both seeds, but two
  seeds cannot tell us how large the spread between seeds is.

## Plain English (for Ben)

When the small puzzle-solver spent its "night" practising the day's new, bigger puzzles with the correct answers, it
got clearly better at fresh puzzles of that kind (about 80 more right out of 400 grids on each seed) than when it
spent the night on old practice only, and it did no worse than doing nothing at the puzzles it already knew. The
write-up's numbers are correct and the test passes its pre-set bar, but one seed's sums were already near perfect,
the report leaves out a few items the marks asked for, and we can't prove from here exactly when the runs started.
