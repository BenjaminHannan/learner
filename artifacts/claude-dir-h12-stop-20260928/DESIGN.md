# H12: train the loop's learned stop on the new kind (mazes) while it adapts

Written 2026-09-28 21:10 UTC (`date -u`) by Director helper H12, on top of main commit `bc6cb4368`. Nothing in this folder has been run.
When this page was written no plug-in code, selftest or marks script for H12 existed. The pass marks are in PASSMARKS.md and
were written next, before any code. Labels: **shown** = counted from a raw file or the code, you can check it;
**suggested** = my reading, rests on stated assumptions; **untested** = nobody has run it. Counts are "x of N".

## 1. The question, in plain words (for Ben)
The reasoner thinks in rounds and has a small "stop" part that is supposed to say "my answer is right, I can stop now".
That stop was only ever trained on sums and grids. When the reasoner meets a new kind of puzzle (mazes), the stop is
untrained for it, and in the fair few-example ruler it mostly never fires: the reasoner just thinks all 48 rounds.
Ben wants the reasoner to decide its own thinking time. The textbook fix is to keep training the stop while the reasoner
adapts to the new kind, the same way it was trained in practice. This test asks one thing: **after that single change,
does the stop fire on its own on mazes, without costing accuracy?**

## 2. Why this is worth a test (shown)
- The ruler's learned stop rule: from round 3 on, stop at the first round where the stop probability is above 0.5 **and** the
  last three predictions agree (`scripts/claude_fewex_bench.py:76-78`). Otherwise it runs to the 48-round cap.
- The harness Learner trains the loop on mazes with cross-entropy only. Its line `self.update(torch.stack(ces).mean())  # no maze stop-head loss`
  is `scripts/claude_fewex_bench.py:205`; `artifacts/claude-fewex-20260927/PROTOCOL.md:17` says "There is no stop-head loss during maze adaptation".
- Practice (sums and grids) does train the stop: `scripts/claude_fewex_net.py:171-172`, loss = mean cross-entropy over the gradient rounds
  + 0.5 x mean binary cross-entropy between the halt logit and "this round's answer is exactly right" (target is a constant, built from the
  round's own arg-max).
- Practised loop, holdout 9x9, cap hits (`RESULTS-EQ.md:76-84`, seed 0): 300 of 300 at k = 1, 4, 16, 64, 256, 1,024 and 4,096, and 163 of 300 at k = 16,384.
  **Seed 1 is different** (`RESULTS-EQ.md:120-128`): 300, 300, 23, 262, 300, 71, 196, 177 of 300 at k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384.
  So "cap on every rung" is true for seed 0 only. On the holdout the learned-stop read is 0 to 14 of 300 above the fixed 16-round read at every one of the eight positive rungs in both seeds
  (recounted from the `fixed_right` and `right` fields of `eq-runs/loop-s{0,1}-pre/holdout.json`; k >= 16 also in H9 REPORT.md:97-104), so at the ruler the untrained stop costs time, not accuracy.
- Baseline dev panel (the panel this test is judged on), same numbers I recomputed from `eq-runs/loop-s{0,1}-pre/adapt.json`: cap hits at k = 64, 256, 1,024, 4,096, 16,384
  are 300, 300, 300, 300, 143 (seed 0) and 265, 300, 61, 196, 194 (seed 1), of 300 each.

## 3. The one change
`scripts/claude_dir_h12_stop.py` (new file) is a plug-in for the equal-practice harness `scripts/claude_fewex_eq_bench.py` (used unedited, `--plugin claude_dir_h12_stop`).
Its `Net` **is** the baseline loop's `claude_fewex_net.Net`, class unchanged: same 1,645,726 weights, same state-dict, no new number.
Its `Learner` subclasses the harness's baseline `Learner` and overrides only `maze_batch`. In the baseline each of the four optimizer updates on a batch runs
3 no-gradient rounds and 2 gradient rounds (state carried, detached between updates) and minimises the mean of the two cross-entropies. The plug-in minimises

    mean over the 2 gradient rounds of CE   +   0.5 x mean over the 2 gradient rounds of BCEwithLogits(halt logit, exact-now)

where `exact-now` is 1.0 for a maze whose every fill-slot token is right at that round and 0.0 otherwise, per maze in the batch. Weight 0.5, the mean over gradient rounds and the target are copied
from `claude_fewex_net.train_loss` (`claude_fewex_net.py:171-172`). Nothing else differs from the baseline loop:

| Same as the baseline (shown from the code) | Value |
|---|---|
| Start net | the ruler's own qualified 12,000-step sums+grids source nets (`runs/qual-loop-s{0,1}`, on Ben's Mac; never retrained) |
| Net, weights, stop rule, fixed-depth read | unchanged; fixed depth is the run's own source-selected depth (16 in both baseline seeds) |
| Mazes and order | the same per-seed 16,384-layout pool, same nested prefixes, same batches (`claude_fewex_eq_bench.py:33-58`) |
| Updates | 512 batches of 32, 4 optimizer updates per batch = 2,048 per rung, checked by the harness (`claude_fewex_eq_bench.py:115-116`) |
| Optimizer | AdamW lr 1e-3, weight decay 0.1, betas (0.9, 0.95), 50-step warm-up, gradient clip 1.0 (inherited `Learner`) |
| Sleep, scoring, panels, replay | inherited unchanged (`Learner.sleep` is not overridden, so sleep has no stop loss, exactly as in the baseline) |

Two things follow from that and are **not** part of the change (suggested, untested): (a) because the baseline round structure is kept, the maze stop loss sees only rounds 4, 5, 9, 10, 14, 15, 19 and 20
(rounds 1-3, 6-8, 11-13, 16-18 and everything after 20 have no stop loss on mazes; practice covered rounds 1 to 16); (b) the stop loss gradient flows into the shared blocks, as in practice, so it can also change the
body. Point (b) is why the marks also report the fixed-16 read, which does not use the stop at all.

Nothing here is maze-specific (Ben rejects tricks built for mazes, `handoff/director-briefs/h9-novelty-research.md:2`): the loss uses only "is my answer exactly right now", the feedback signal
the loop already gets on every kind; there is no kind label and no hand-written rule. The maze is only the test kind; the same lines would apply to any new kind's adaptation.

## 4. Arms, seeds, what is judged
- **Variant (H12):** practised loop + this Learner, `--init pre`, seeds 0 and 1 (the harness only allows these two). Two jobs.
- **Control:** the baseline practised loop, already run and on main: `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/adapt.json`. Not retrained. It is the higher of the available controls for
  every reading: I use it for both the learned-stop read and (for the fixed-16 read) its own fixed-16 numbers; the plain net has no stop head, so it is not a control for a stop test.
- **Not run:** a fresh loop, a plain net, a holdout. Fresh and plain would answer race questions this test does not ask. **The holdout stays unopened**, so this variant can still enter a race with a clean holdout.
- **Panel:** the dev 9x9 panel (300 mazes, `PANEL_SIZES` in `claude_fewex_data.py`); 7x7 (24) and 11x11 (300) dev panels are reported. All marks are read from the dev records `adapt.json`.

**Race entry or diagnostic fix? Recommendation: diagnostic (report-only on F_eq).** Reasons: (1) the design's own question is about the stop, and the harness already reads accuracy at the round the stop picks; in the
baseline the learned read is 0 to 14 of 300 above the fixed 16-round read at every positive holdout rung (shown, section 2), so a better stop has little accuracy to win by itself (suggested); (2) the race bar
(F_eq +10 over the loop in both seeds, `RACE-PASSMARKS.md`/`RACE-ADDENDUM-1.md`) needs the curve to move about one rung left (H9 REPORT section 2), which a stop-time change does not do by mechanism (suggested);
(3) a race entry would also need a fresh copy (+5) and old-kind sleep gates, which this test does not run. F_eq and F_few are reported with a noise-based bar for "helps" (PASSMARKS.md), not as a promotion test.

## 5. What each result would mean (fixed in PASSMARKS.md)
- **STOP LEARNED:** cap hits fall to about the number of mazes it gets wrong (plus a fixed 30), mean rounds fall below the "16 rounds for solved, 48 for unsolved" line, and accuracy stays within the ruler's own stop-failure limit of the fixed-16 read, on at least 4 of 5 rungs in **both** seeds.
- **WRONG:** the stop still does not fire on at least 2 of 5 rungs in **both** seeds even with the stop loss on. Then the stop loss alone does not give a maze stop; the next single changes to try are listed in section 7.
- **FIRES BUT HURTS**, **NOT SHOWN:** see PASSMARKS.md.
Rungs k = 1, 4, 16 are reported, not judged: the net solves at most 28 of 300 there (baseline holdout), so there is almost nothing correct for a stop to fire on; a stop that stays at the cap when it is nearly always wrong is doing the right thing.

## 6. Compute and cost
CPU on Ben's Mac, strict fp32, `--threads 1`, $0, no rental, no BensPC. Why the Mac: (1) the four qualified source checkpoints are not in git and sit on the Mac (`handoff/queue/dir-h1-heldout.md` line 3);
(2) the ruler is fp32 CPU with autocast disabled (`PROTOCOL.md:17`) and a GPU run needs a separate addendum with strict fp32, TF32 off and CPU-equivalent smoke results before its first score (`ADDENDUM-4.md:15`); (3) two jobs are small: the baseline's loop dev jobs took 10,149 s and 10,123 s
(169 minutes) with eight running at once on a 10-core host (`rung_seconds`, `training_seconds` in the two baseline `adapt.json`). The extra term is one small BCE per round, so I expect about the same (untested). Time cap 300 minutes. Vast would cost
more than $0 and add a GPU-equivalence problem for no gain; not recommended.

## 7. If it is WRONG or FIRES BUT HURTS: next single changes (each its own test, not run now)
1. Make the stop loss see every round (rounds 1 to 16, like practice) by giving the plug-in its own round schedule: one change, needs a new Learner path.
2. Train only the halt layer on detached features (isolates "the stop head learned" from "the auxiliary loss reshaped the body").
3. Change the inference rule's three-round-agreement condition. That edits the ruler's scorer, so it needs Ben and an addendum.
Each one starts from these results, with marks fixed before its first run.

## 8. What could not be tested, risks
- No maze score of this design exists. Marks and code were written before any run. The code is checked by `scripts/claude_dir_h12_selftest.py` (records in `SELFTEST-plugin.log`, see PASSMARKS.md "Order"); a full 2,048-update rung was **not** run here.
- Two seeds only, dev panel only, one architecture. The noise estimate behind the "helps" bars comes from the baseline's two seeds (suggested; see PASSMARKS.md). A same-recipe replicate would measure run-to-run noise properly; I did not add one to keep compute at two jobs.
- The stop loss might change the body (point (b) in section 3); the fixed-16 rows show that. Old-kind and sleep rows are report-only (single sleep draws are inside noise, H8 X1).
- Rounds without stop loss (section 3 (a)) mean the result may say "the baseline round structure gives the stop too little coverage", which would be a finding about the Learner, not about the idea.
- **Not** proven by anything here: that a maze-trained stop transfers to another new kind, or that "decides its own time" means it thinks longer on harder mazes; only aggregate rounds per maze size are read (7x7, 9x9, 11x11).
