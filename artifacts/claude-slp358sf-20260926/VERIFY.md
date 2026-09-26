# slp-358sf blind recount (2026-09-26)

**Verdict: INCONCLUSIVE, as registered. I agree with RESULTS.md.** Seed 10 misses V by one puzzle (S − N on day_grids
= +19, bar +20), so seed 10 is INCONCLUSIVE. Seed 9 meets V (+97) and fails Q1, Q2 and Q3, so seed 9 is a FAIL. PASS
needs all four marks on both seeds, so it cannot PASS. The FAIL rule ("V met on both seeds and anything else") does not
apply because V is not met on both seeds. The proved-wrong counts hold on both seeds, but seed 10 is invalid, so only
seed 9 counts as evidence against the idea.

The seal holds. `sha256sum -c SEAL-code.sha256.txt` gives OK for all 6 files. The sealed files have the same hashes at
the seal commit 3e5c27016 (03:34:59 UTC), at the results commit 8e5d42054 (03:54:14 UTC) and at HEAD. 3e5c27016 is an
ancestor of 8e5d42054. The logs match the JSON exactly (base line and all 3 morning lines, scores and day records).

## Marks after night 3 (counted from the JSON only)

| mark | seed 9 | seed 10 |
|---|---|---|
| V: S − N, day_grids (400), ≥ +20 | 184 − 87 = **+97, met** | 38 − 19 = **+19, not met → INCONCLUSIVE** |
| Q1: P − S, day_grids, ≥ +20 | 170 − 184 = −14, fail | 34 − 38 = −4, fail |
| Q2: P − S, ≥ +10 on sums8 or grids6 (200) | sums8 114 − 128 = −14; grids6 39 − 47 = −8; fail | sums8 34 − 33 = +1; grids6 4 − 4 = 0; fail |
| Q3: P ≥ S − 10, harm_sums4 (300) | 281 vs 284 (−13), fail | 94 vs 82 (+2), ok |
| Q3: harm_grids4 (300) | 192 vs 174 (+8), ok | 97 vs 87 (0), ok |
| Q3: day_sums (400) | 359 vs 361 (−12), fail | 76 vs 79 (−13), fail |
| Q3 overall | fail (2 of 3) | fail (day_sums) |
| seed result | **FAIL** | **INCONCLUSIVE** |
| proved-wrong counts (P − S ≤ +5 on day_grids, sums8, grids6) | −14, −14, −8: met | −4, +1, 0: met (seed invalid) |

The report items, from the JSON:
- **P − N on harm** (sums4, grids4): seed 9 +33, +37 (S − N: +46, +29); seed 10 +35, +33 (S − N: +33, +33).
- **Nights 1-2, P − S:**
  - Seed 9, night 1: day_sums +2, day_grids +2, sums8 0, grids6 +6.
  - Seed 9, night 2: day_sums −32, day_grids −6, sums8 −26, grids6 −3.
  - Seed 10, night 1: day_sums −6, day_grids +4.
  - Seed 10, night 2: day_sums 0, day_grids +4.
- **Night pools (P):** seed 9: sums 84 / 33 / 58, grids 229 / 185 / 183. Seed 10: sums 266 / 225 / 241, grids 279 / 268 / 270.
  - Every pool equals 300 minus that arm's day-try right count, which confirms the pools are exactly the misses.
  - No pool fell below 16, so the fallback never ran.
  - excluded_day_items_in_tests = 0 on both seeds.
  - The N arm stays equal to base every morning, as it should.

## Disagreements with RESULTS.md

**Numbers: none.** Every cell in the RESULTS score table, every mark value and every pool size matches my count. The
problems are in the wording and in what the report leaves out:

1. **"seed 10's net never learned" (title) and "had barely learned anything" (plain words) go too far.**
   - Seed 10's base net scores 48/400 on day_sums, 59/300 on harm_sums4 and 64/300 on harm_grids4.
   - Its nights still add S − N +41 on day_sums and +33 on each harm test.
   - The net is weak but not blank. "Badly undertrained" is also a guess: pretraining used the same steps and learning
     rate as seed 9, so a bad seed or unstable training explains it just as well. The data do not say which.
2. **"especially on sums, where the misses were a small set practised over and over" is not shown.**
   - On seed 9, grids fell about as much as sums on the day-size tests (day_grids −14, day_sums −12).
   - Sums lost more than grids on transfer (−14 vs −8) and on harm (−13 vs +8).
   - The explanation that repetition hurt, and the report-only line "repeating a few missed sums looks like it hurt",
     are also untested. No arm uses a random pool of the same small size, so "mistakes" cannot be told apart from
     "fewer different puzzles" (see note 1).
3. **Messy cell.** The seed 10 Q3 cell reads "76 ≥ 79? no, 76 < 79 (FAIL)". The self-correction was left in. It should
   read "76 < 79 FAIL".
4. **Missing report items.** PASSMARKS lists "nights 1-2, day tries, night pool sizes, P vs N on harm" as report
   items. RESULTS gives the pool sizes and one night-2 remark. It leaves out the nights 1-2 scores, the day-try counts
   and P vs N on harm. They are listed above.
5. **The overall verdict wording is correct but rests on a reading of the rules.** PASSMARKS never says what happens
   when V holds on one seed and fails on the other. INCONCLUSIVE is the only reading that fits both written rules, and
   it is the one RESULTS uses. RESULTS keeps the proved-wrong clause to seed 9 only, which I agree with. It does not
   claim PROVED WRONG.
6. **(PASSMARKS, not RESULTS) The timestamp is wrong.** The header says the marks were "fixed ... 2026-09-26 04:10
   UTC". The seal commit is 03:34:59 UTC and the results commit is 03:54:14 UTC, both earlier. Git order still shows
   the marks came before the results, so the seal stands. The label is simply wrong.

## Code check (scripts/claude_slp358sf_nights.py)

- **P arm: correct.** `wrong_items` scores each arm's own net on that day's puzzles before its night, using the same
  scoring as `N.score` (8 rounds, code check). `mistakes_first` keeps a kind's misses if there are at least 16, and
  otherwise all of that kind. The code matches the docstring and PASSMARKS.
- **S arm: correct.** It calls `N2.night_batches("S", items, nrng, cfg)` with the same `nrng` seed formula as n2. This
  is the slp-358n2 sleep night.
- **Everything else is the same as n and n2.** CFG, pretraining, the fixed tests (seed 58600), the rng / rr / drng
  seed formulas, test exclusion, optimisers and learning rates all match.
  - Day tries are scored on the combined list rather than per kind. The shapes never overlap (sums are 3x6 and 3x7,
    grids are 5x5), so the batches and the counts are the same.
  - The only differences are the dropped R and Z arms (so S's rr stream on days 2-3 differs from what n2 would give
    for the same seed, which does not matter with fresh seeds) and that no base .pt is saved.

## Design notes (marks easier or harder than they look)

1. **No control for pool size.**
   - What varies: P changes which puzzles go into the night and also how many different ones. On seed 9 a sums night
     drew from 33-84 puzzles against 300.
   - Why it matters: a P loss (or gain) cannot be put down to "practising mistakes" rather than "less variety". The
     missing control is an arm with a random subset of the same size.
2. **Q1 is judged where P differs least from S, which makes it hard.**
   - The grids miss pools were 61-76% of all grids on seed 9 and 89-93% on seed 10, so the grids night was close to
     random.
   - On seed 10 the sums pools were also 75-89% of all, so P ≈ S there and seed 10 tested almost nothing.
   - The sums pools, where P really differs, count only toward Q3 (forgetting).
3. **The 16-miss floor is per kind, not per shape.**
   - How batches are drawn: `night_batches` picks the kind half and half, then a shape uniformly from the shapes in
     the pool (5 or 6 digit sums).
   - What that allows: if one sums shape had only a few misses, a quarter of all day batches were 64 draws from those
     few puzzles.
   - What we cannot check: the misses per shape are not logged.
4. **S and P are not matched step for step.**
   - Same seed, different plans: they share the `nrng` seed, but `rng.choice` over pools of different sizes uses up a
     different number of random bits, so the day/rehearsal plan drifts apart after the first draw.
   - Different rounds schedule: `rr` (the rounds per step) is drawn in sequence, S first and then P.
   - Unknown noise: there is no S-vs-S replicate, so we do not know how large an S − P gap arises by chance. Gaps of
     10-14 may sit within that noise.
5. **V on a weak net is close to the floor.** Seed 10 started at 19/400 on day_grids, and V missed by one puzzle. A
   fixed +20 bar is much harder to clear on a net this weak than on seed 9 (base 87).
