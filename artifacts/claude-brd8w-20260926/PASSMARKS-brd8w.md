# brd-8w (registered as "brd-8"; renamed, name only): does a week of lucky-hit nights, instead of one night, clear the +24 bar on fresh puzzles? (registered 2026-09-26, before any run)

Source: Ben, 2026-09-26: "Solve this problem. Get it to the first pass", with $2 of vast.ai. Problem 7: can
sleep turn lucky guesses into real skill, meaning more NEW puzzles solved, not only the practised ones?
Ben's first pass, kept exactly: on 240 fresh puzzles with 30 tries each, the slept model solves at least 24 more
DIFFERENT puzzles than the same model without sleep in each of 3 separate training runs, and at least 24 more than
a fair control that trains the same amount on answers the model already knew.

## Why this change (evidence, before any run)
- One night (brd-5, brd-7, both on 400 practice puzzles) gained +21/+22/+13 and +23/+23/+11 over no sleep, short
  of +24. brd-6 showed that more practice puzzles in one night, at equal exposure, add nothing.
- Recount of brd-7 per puzzle: one night reaches 39-43 puzzles the untrained model missed but loses 20-28 it had
  reached (the untrained model reached 62 test puzzles with a single hit in 30), so the net is about +20.
- dl-2 (Fix sleep, registered PASS) ran the same copy practice for 7 nights. Puzzles reached on its fresh test
  went 34 → 46 after night 1 → 61 after night 7 (of 100; mean of 2 seeds). Night 1 closed 18% of the unreached
  gap, the same as brd-5/7; night 7 closed about 41%.

## The one change
brd-7's one night is replaced by a week of nights, using the Fix-sleep night rule unchanged (dl-2's S arm).
Code: scripts/claude_brd8w_week.py (docstring).
- **Day d = 1..7:** 150 new practice puzzles, puzzles(8100 + d, 150), the same for every seed (869 different puzzles
  over the week).
  - The model as it stands answers each puzzle once (greedy).
  - On a miss, it makes 30 rule-keeping guesses at T 1.5. The exact checker keeps the first right one.
  - The day's examples are the greedy-right answers plus the first hit on each won puzzle.
- **Night d:** claude_dl1_nights.train_copy on that day's examples: one LoRA r16 adapter that keeps growing, 3
  epochs, lr 2e-4, batch 8.
- **Arms:**
  - W is the week above.
  - C is the fair control. It gets the same days and the same night rule, but each night's examples are only C's
    own greedy-right answers from that day, repeated in turn to W's example count for that night.
  - base is the untrained model.
- **Temperature:** fixed at 1.5 for practice and test. brd-7's DEV rule chose 1.5 in all four earlier runs.
  Fixing it keeps the three parallel processes from choosing differently. This is stated as a deviation from
  brd-7's procedure.
- **Seeds:** 0, 1, 2, one process per seed (they may run on 3 GPUs at once). Each process measures its own base.

## Test panel, FIXED NOW
- File: artifacts/claude-brd8w-20260926/test_puzzles.jsonl, md5 e9de2a42441d59a4933fbce43ae668f0.
- Contents: 240 puzzles (160 with 3 numbers, 80 with 4 numbers and target 24; 187 hands), from
  puzzles(802, 1500).
- It excludes all 7 practice days, practice seed 9 (800), the DEV panel, and the brd-5, brd-6 and brd-7 panels.
- Nobody has scored it. 30 samples per puzzle at T 1.5.

## Measure and marks
cov@30 = test puzzles with at least one right answer in 30 samples, which counts DIFFERENT puzzles solved, not
total lucky hits. Intervals are 95%, bootstrapped over number hands (2,000 draws), averaged over the 3 seeds
(claude_blurt5s.boot_ci). Seed k's W and C are compared with the base measured in seed k's own process.
- **PASS:** all three must hold.
  - W's cov@30 after night 7 is at least base cov@30 + 24 in EVERY seed.
  - The 95% interval for W − base is above 0.
  - W's cov@30 is at least C's cov@30 + 24 in every seed.
- **Proved wrong:** the upper 95% bound of W − base is below +5 points (12 puzzles).
- **Otherwise:** NOT SHOWN.
- **Inconclusive:** a seed's process does not finish, or a seed wins fewer than 40 practice puzzles over the week,
  or C has no examples on more than 2 nights.
- **Reported, not marked:**
  - cov@1 and lucky samples;
  - cov@30 split into 3-number and 4-number puzzles;
  - W's cov@30 after nights 1 and 3;
  - the interval for W after 7 nights minus W after 1 night;
  - per-night own, wins and examples;
  - minutes and dollars.
- **Scoring:** `claude_brd8w_week.py --score` recounts from each seed's streams.json.

## Honesty notes
- This changes the recipe: a week of sleep, not one night. A pass would show that a week of lucky-hit nights
  passes Ben's first pass, and that one night does not. It does not show that one night is enough.
- The week sees 869 different practice puzzles against brd-7's 400. C gets the same days and the same number of
  training examples each night, so "more training" alone is controlled for by C, not by base.
- W after night 1 is scored in the same run, on the same panel, so the added nights' effect is visible within the
  run.
- Not measured here: forgetting of general answers. dl-2 found it grows over the week, 5-7 of 200 lost after
  night 1 and 26 after night 7. It remains open for the second pass.
- Prediction, before the run (from dl-2's curve and brd-7's per-seed spread):
  - W − base about +35 to +50 per seed;
  - PASS about 75%.

Addendum 2026-09-26 13:22 UTC (name only; runs in progress, no result opened except the live per-night log lines):
the creative thread registered a different test also called brd-8 (origin/main 4f226bbfe, 13:08 UTC, same folder
name). To keep both, this test is renamed brd-8w and its files moved to artifacts/claude-brd8w-20260926/ and
scripts/claude_brd8w_week.py. Code, panel (md5 e9de2a42441d59a4933fbce43ae668f0) and marks are unchanged from
commit 4fc86bc7e (12:55 UTC); the rentals run that commit's files under the old names.
