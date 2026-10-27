# slp-358n3 pass marks, DRAFT for the Thread manager's check (sleep research thread, written 2026-09-27T14:21Z; not sealed, nothing run)

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
- Night size: 300 steps (n2's). The batch is 256, the reasoner's own training batch (n2 also used its own day batch).
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
S sleep (the day's puzzles with right answers), R rehearsal-only night (same steps), Z placebo night, N no night.
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
| M1 learns from the day | S − R on day_grids and on day_sums (400 each) | mean ≥ +20 and ≥ +20 on 3 of 4 seeds, each kind. Ceiling rule: a kind where S and R are both ≥ 360 on a seed counts as uninformative on that seed. The kind passes if its informative seeds pass. If it is uninformative on 3 or more seeds, it is reported as such and M1 rests on the other kind. |
| M2 not a placebo | S − Z on each day kind | ≥ +20 on 3 of 4 seeds, each kind (same ceiling rule) |
| M3 no harm | S on harm_sums4 and harm_grids5 (300 each) | ≥ N − 6, every seed, each test |
| M3b retention | "lost" = harm items the arm's pre-night net got right and its morning gets wrong, after each of the 3 nights | S lost ≤ 15 of 300, every seed, every night, each test |
| RESUME | the night loop is stopped at step 150 of night 2 (S arm, seed 13). It saves net, optimizer, step and all random-number states, and a fresh process resumes. On CPU in float32, the weights after night 2 must be bit-identical to an uninterrupted run (torch.equal on every tensor). The CPU copy uses 20-step nights and 64-item batches, so it tests the code path, not GPU numerics. | identical |

**PASS (H-B) = M1, M2, M3, M3b and RESUME.** Otherwise FAIL (stays FAIL).

**Proved wrong** ("a night on the day's checked answers teaches the full-size reasoner more than extra old
practice"): S − R ≤ +5 on both day kinds, on 3 of 4 seeds, with neither kind at the ceiling on those seeds.

**Report:**
- mornings after nights 1 and 2
- each arm's day tries
- R vs N and Z vs N on harm
- mean stop round per test
- fixed-8 and fixed-48 scores
- excluded-item counts
- torch.__version__, GPU name and minutes, in every summary

## What this does and does not license
- A PASS licenses running this night code on whatever net becomes REASONER02D (358b3's checkpoint) to make SLEEP02D.
  The build's row B then compares SLEEP02D against SLEEP02D="" on the build's own tests. That comparison is Month-end's
  gate, not graded here.
- These are code-made number sums and Latin grids with code-checked answers. They are not chat puzzles, and the
  reasoner's own tries are graded but not reused.
- Nights that learn from the reasoner's own right and wrong tries are a later test (step (c), with Creative's H arm).

## Where it runs (needs the Thread manager's check; money under Ben's 14:05 standing order)
- One vast card, the best TFLOPS per $/h with at least 24 GB, the same kit pattern as 358t/358s (vstart, vguard,
  vcollect; destroy only after a verified copy-back).
- The 4 358u loop final.pt files go up from the Mac by scp. Each is sha-checked against 358u's SEAL-run before use.
  Weights never go to git.
- Estimate (inferred from 358i training speed, not measured): under 1 h and under $1 on a 5090-class card. The guard
  stops at $1.50, and the time limit is 2 h scaled to card speed.
- It starts only after 358u's collect verifies all 4 loop checkpoints. If fewer than 3 exist, n3 waits.
- The RESUME check runs on the Mac's CPU at $0, or on this container on a tiny stand-in net: it tests code, not weights.

## Predictions (before any run)
- M1: 55%. The full nets are strong, so the day kinds are harder sizes where one short night may do less.
- M3/M3b: 75%.
- RESUME: 90%.
- PASS: 40%.
- Proved wrong: 20%.

## Asks
- Fix sleep: their ip-1b interrupt-and-resume check, to reuse its method for RESUME.
- Month-end: which puzzle panels the build grades, so that day items can be checked against them too.
