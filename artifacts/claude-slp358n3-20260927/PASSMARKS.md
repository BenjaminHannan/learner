# slp-358n3 pass marks (sleep research thread; draft 2026-09-27T14:21Z, the Thread manager's four fixes 14:25Z applied; fixed before any run)

This is the build's sleep gate H-B. Since 0.2d ADDENDUM-46 (Ben 13:28 UTC, "yes"), H-B means the reasoner's nights, and
SLEEP02D is the reasoner's slept checkpoint. The talker gets no nights.

## Question
Does a night of sleep make the full-size loop reasoner better at fresh puzzles of the day's kind? A night means
practising the day's puzzles with code-checked answers, mixed half-and-half with its old practice, in small steps.
It is compared with a night of the same length spent only on old practice. It must not harm what the reasoner already
knew, and the night loop must survive being stopped and resumed (Ben 14:49 UTC 09-26: sleep only while dormant, and
it can be stopped at any moment).

## What it is (one change from slp-358n2, registered PASS)
slp-358n2's night recipe, with ONE change: the small in-run nets (2 x d256, 3,000 CPU steps) become the 4 full-size
358u loop checkpoints (2 x d512, seeds 13-16, 60,000 steps, never told the puzzle kind). Everything the change forces
is carried by a fixed rule, not tuned:
- Night loss: 358a's own loop loss (1-16 rounds, gradient through at most 6, answer loss + 0.5 x stop-head loss).
  Autocast is bf16 with the weight cache off (358i2's fix).
- Night size: 300 steps (n2's absolute steps; graded). n2's night was 10% of its training steps; 300 is 0.5% of the
  reasoner's 60,000, so a report-only L arm runs S's night at 6,000 steps (10%, n2's ratio) on seeds 13 and 14. The batch is 256, the reasoner's own training batch (n2 also used its own day batch).
  The learning rate is 3e-5, constant: a tenth of the reasoner's peak 3e-4, the same ratio as n2 (1e-4 against 1e-3).
  AdamW (wd 0.1, betas 0.9/0.95), one optimizer per arm, kept across the 3 nights.
- **No pilot.** The Thread manager asked that a pilot's steps and learning rate go into the plan before sealing. Here
  they are fixed by the rule above instead, so no dev run can steer them.
- Night mix: half day batches and half rehearsal. A day batch picks the kind first (half sums, half grids; n2's fix),
  then draws only that kind. Rehearsal draws from the reasoner's own practice stream (358a's Source, fresh seed 100+s),
  with the kind hidden from the net as in 358u.
- Placebo answers: n2's clean placebo (sums get answers shuffled between same-width sums; each blank grid cell gets a
  random symbol from that puzzle's own symbols).
- Scoring is how the build runs the reasoner: 48 rounds and the sealed v2 stop rule (claude_rsn358b2_bridge.py:138-141).
  Fixed round 8 and round 48 are report only.
- Numbers (make-24) are left out of days and tests. No 358 net learned them (358i3: numbers5 +0.00). Rehearsal still
  contains them, because the practice stream always did.

## Day kinds (a code rule on the untouched nets, before any night)
The 358i3 loop nets already score about 292-299 of 300 on sums6 and grids6 (VERIFY-recount.md:19-20), so days at
those sizes would sit at the ceiling. That is how slp-358n2's seed-3 sums became uninformative. So before any night,
code scores all 4 base nets on 300 fresh dev items (seed 58640) per candidate size:
- sums: 6, 8, 10, 12
- grids: 6, 7

For each kind, the day size is the smallest candidate whose 4-seed mean is at most 240 of 300. If none qualifies, the
day size is the largest candidate and that kind uses the ceiling rule below. The choice is logged and is the same for
every seed and arm. Dev items are never test or day items.

## Arms (each seed; all arms start from the same 358u checkpoint)
S sleep (the day's puzzles with right answers), R rehearsal-only night (same steps), Z placebo night, N no night;
report only: L, S's night at 6,000 steps (seeds 13 and 14; same data, same draws as S for its first 300 steps).
There are 3 days. Each day: 300 fresh puzzles of each day kind (seed 59000+10s+d, the same for every arm). Every
arm's try on them is graded before its night, then the night. Any day item that equals a test item, a dev item or an
item of 358i's sealed test panels is dropped and counted. The comparison is by code, on hashes; counts only, and no
panel is read item by item. The TEST-ONLY numbers4 panel is not touched.

## Tests (fixed, made by code, seed 58630; the same for every seed and arm)
- day_sums and day_grids: 400 each, at the chosen day sizes.
- harm_sums4 and harm_grids5: 300 each, the practised sizes.
- report: sums and grids at every other candidate size, 200 each; sums4/grids5 "lost" counts.

## Marks (after night 3; per seed s13-s16)
| mark | what | pass |
|---|---|---|
| M1 learns from the day | S − R on day_grids and on day_sums (400 each) | mean ≥ +20 and ≥ +20 on 3 of 4 seeds, each kind. Ceiling rule: a kind where S and R are both ≥ 360 on a seed counts as uninformative on that seed. Floor rule: a kind where S and R are both ≤ 40 on a seed is also uninformative on that seed. The kind passes if its informative seeds pass. If it is uninformative on 3 or more seeds, it is reported as such and M1 rests on the other kind (and if both are, M1 fails). |
| M2 not a placebo | S − Z on each day kind | ≥ +20 on 3 of 4 seeds, each kind (same ceiling and floor rules) |
| M3 no harm | S on harm_sums4 and harm_grids5 (300 each) | ≥ N − 6, every seed, each test |
| M3b retention | "lost" = harm items the arm's pre-night net got right and its morning gets wrong, after each of the 3 nights | S lost ≤ 15 of 300, every seed, every night, each test |
| RESUME | the graded run's own night code and settings (300 steps, batch 256, lr 3e-5), device CPU in float32 with torch.use_deterministic_algorithms(True), 4 threads: arm S, seed 13, nights 1-2. Run 1 goes straight through. Run 2 stops at step 150 of night 2 and saves net, optimizer, step and every random-number state atomically (tmp file, fsync, os.replace; Fix sleep's pattern). Run 3, a fresh process, resumes from that file. | the weights and the optimizer state after night 2 are identical (torch.equal on every tensor), and the hashes of the 150 batches drawn after the resume equal the straight run's batches 150-299 |

**PASS (H-B) = M1, M2, M3, M3b and RESUME.** Otherwise FAIL (stays FAIL).

**Proved wrong** ("a 300-step night on the day's checked answers teaches the full-size reasoner more than 300 steps of
old practice"): S − R ≤ +5 on both day kinds, on 3 of 4 seeds, with neither kind at the ceiling or floor on those seeds.
It says nothing about longer nights; L is reported beside it.

**Report:**
- mornings after nights 1 and 2
- each arm's day tries
- R vs N and Z vs N on harm
- L vs S and L vs N on every test (seeds 13-14), and L's lost counts
- mean stop round per test
- fixed-8 and fixed-48 scores
- excluded-item counts
- torch.__version__, GPU name and minutes, in every summary

## What this does and does not license
- The night teaches from answers made by code (sums computed, grids filled by a solver). Under the goals page
  (ben-goals-2026-09-26.md:40) a hand-written stand-in is allowed only as disclosed test scaffolding. So a PASS licenses
  this night in 0.2d with code answers as disclosed scaffolding: run on whatever net becomes REASONER02D to make
  SLEEP02D, and row B (Month-end's gate, not graded here) compares it with SLEEP02D="". The product night needs answers
  from the reasoner's own checked tries (step (c), brd-13's O/H arms), which is a later test.
- These are code-made number sums and Latin grids, not chat puzzles; the reasoner's own tries are graded, not reused.

## Where it runs (needs the Thread manager's check; money under Ben's 14:05 standing order)
- One vast card, the best TFLOPS per $/h with at least 24 GB, the same kit pattern as 358t/358s (vstart, vguard,
  vcollect; destroy only after a verified copy-back).
- The 4 358u loop final.pt files go up from the Mac by scp. Each is sha-checked against 358u's SEAL-run before use.
  Weights never go to git.
- Estimate (inferred from 358i's speed, 8 runs at once in 75 min on a 5090; not measured): 4 seeds at once, each with
  2,700 graded night steps, 18,000 L steps on 2 seeds, and 16-19 scorings of about 2,600 items at 48 rounds, about 1.5-2 h
  on a 5090; RESUME's 1,200 CPU steps run beside it on the rental's CPU. About $1 at $0.50/h. The guard stops at $2.00
  (cap $2.40), with the fit check and waves of the 358s kit.
- It starts only after 358u's collect verifies all 4 loop checkpoints. If fewer than 3 exist, n3 waits.
- RESUME runs on the same rental's CPU with the seed-13 checkpoint (same code, device CPU).

## Predictions (before any run)
- M1: 55%. The full nets are strong, so the day kinds are harder sizes where one short night may do less.
- M3/M3b: 75%.
- RESUME: 90%.
- PASS: 40%.
- Proved wrong: 20%.

## Asks
- Fix sleep answered (14:24Z): ip-1b never resumed a night mid-training, so RESUME is new method; the atomic save and
  the list of states to restore follow their advice.
- Month-end: which puzzle panels the build grades, so that day items can be checked against them too.
