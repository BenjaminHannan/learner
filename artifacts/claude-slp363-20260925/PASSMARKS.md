# slp-363 pass marks (registered 2026-09-25, before any registered run)

Question: does one night of "practice school" (practice puzzles built from the user's own taught notebook) make the
loop reasoner better at questions about facts it has never seen, more than the same amount of plain practice, and
more than practice on the same puzzles with scrambled grades?
Change (one): the practice file used during the night. Everything else is identical across arms: the same starting
checkpoint (BASE), seed, recipe (claude_rsn_recipe.py, --base 296 --arm plain), steps (1,000 copy + 2,000 practice),
and mix share (0.5; 0 for PLAIN, which is the recipe's definition of plain practice).
Code: scripts/claude_slp363_run.py (driver), claude_slp363_night.py (world, night file, scrambled-grade placebo),
claude_slp363_school.py (the school builder), claude_rsn_recipe.py (sleep research thread's recipe). GPU: BensPC.

Arms, per seed S in {1, 2}: NOSLEEP (BASE = 296 recipe, default steps), PLAIN (BASE + night, generator only),
PLACEBO (BASE + night, 50% from the scrambled-grade file), SCHOOL (BASE + night, 50% from the school file).
Night file: world seed 363000+S, 2,000 items. School panel (judged): 1,000 items from a world never used in training
(world seed 364417), built and scored only inside the registered run, never printed, category counts only.
No-harm panel: reasonpanel296 items-v2 (TEST-ONLY, scored once per checkpoint by the builder).
Score = checked-right count (answers that survive the fact-check on the way out).

| Mark | Bar (each seed) |
|---|---|
| S1 school panel: SCHOOL minus each of PLAIN, PLACEBO, NOSLEEP | ≥ +20 (of 1,000) |
| S2 reasonpanel296: SCHOOL minus PLAIN | ≥ −5 |
| S3 school panel, answers given when the fact is absent: SCHOOL minus the lower of PLAIN and NOSLEEP | ≤ +2 |

PASS = S1, S2 and S3 on both seeds.
Proved wrong if: SCHOOL minus PLACEBO ≤ 5 on the school panel on both seeds (then the school's grades add nothing
beyond practising that puzzle shape).
Report only: every arm's per-category counts on both panels, raw and checked counts, PLAIN minus NOSLEEP (does any
extra practice help), dev scores, minutes per phase.
What a PASS would not show: the panel is built by the same builder as the nights (same kinds of question), so a PASS
means the night helps on new facts of the user's kind, not on new kinds of question; three-step questions are not
judged (the reasoner's third-step input is untrained, sleep research round 2).

## Disclosures written at seal time
- Names and relations are replaced by anonymous symbols for every puzzle (claude_rsn294_core.encode), so the
  reasoner cannot memorize the user's facts from the night; any gain must be a skill.
- The school's first placebo (grades shuffled across the batch) fails the recipe's start-up check (most shuffled
  answers are not in the puzzle). placebo_legal draws each grade uniformly from the answers the reasoner could
  give; in the dev night 225 of 2,000 scrambled grades equal the truth by chance.
- Dev (not registered): night file world 11 → 2,000 items, 0 wrong golds, 0 without a gold action (real and
  placebo). A local tiny-model plumbing run (--dry, 20+20 steps, CPU) ran the whole flow. In that run the panel
  step first used world seed 363999, the seed I had planned to register. That file was never opened and was moved
  to a quarantine folder. The registered panel seed was then changed to 364417, which has never been generated.
  --dry now uses world 9001, and it never touches reasonpanel296.
