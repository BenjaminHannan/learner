# dir-h6 design: how sleep length changes each kind, and one test of why grids fell

Helper H6 (Claude), 2026-09-28 19:2x UTC. Analysis and design only. No training was run (this box has no torch).
Goal served: finish-line item 5 (overnight the model gets better at everything, mostly the previous day's work, keeps old
skills within sealed limits, sleeps only while idle and stops cleanly; sleep trains only the reasoner).
Labels: **shown** = read off the raw files by code; **suggested** = a reading of the numbers; **untested** = nothing here
tests it. Small card experiments and the village model are not used.

## 1. What slp-358n3 shows about sleep length (raw seed JSONs, recounted by H6)

Source: `artifacts/claude-slp358n3-20260927/runs/s{13,14,15,16}/slp358n3-seed*.json` (`morning[night][arm][test].right`).
S = 300-step night, L = 6,000-step night (20 times longer, same lr 3e-5, same mix); N = no night. Both nights use only the
day's own 300 sums and 300 grids plus rehearsal. L exists on seeds 13 and 14 only (report only by design). Counts are
right answers out of N. Day sizes: sums 12, grids 7.

### Day kinds (400 each), after each night
| test | seed | night | N | S | L | L - S | L - N |
|---|---|---|---|---|---|---|---|
| day_sums | 13 | 1 / 2 / 3 | 263 | 367 / 369 / 381 | 377 / 379 / 388 | +10 / +10 / +7 | +114 / +116 / +125 |
| day_sums | 14 | 1 / 2 / 3 | 228 | 353 / 379 / 388 | 382 / 388 / 391 | +29 / +9 / +3 | +154 / +160 / +163 |
| day_grids | 13 | 1 / 2 / 3 | 293 | 342 / 353 / 366 | 293 / 281 / 290 | -49 / -72 / -76 | 0 / -12 / -3 |
| day_grids | 14 | 1 / 2 / 3 | 279 | 365 / 348 / 361 | 292 / 315 / 267 | -73 / -33 / -94 | +13 / +36 / -12 |

### Old-skill tests, after night 3 (N / S / L), seeds 13 and 14
| test (N of items) | seed 13 | seed 14 |
|---|---|---|
| harm_sums4 (300) | 300 / 300 / 300 | 300 / 300 / 300 |
| harm_grids5 (300) | 300 / 300 / 300 | 300 / 300 / 300 |
| rep_sums6 (200) | 198 / 199 / 200 | 200 / 200 / 200 |
| rep_sums8 (200) | 190 / 198 / 197 | 184 / 200 / 200 |
| rep_sums10 (200) | 167 / 194 / 196 | 151 / 197 / 198 |
| rep_grids6 (200) | 194 / 196 / 194 | 192 / 198 / 192 |
Lost counts: L lost 1 of 300 once (seed 13, night 1, harm_grids5), otherwise 0; S lost 0 in all 24 cells.

### Four-seed S against N, after night 3 (for the spread)
day_sums N 263, 228, 240, 298 (mean 257.3); S 381, 388, 379, 376 (mean 381.0, spread across seeds SD 5). day_grids N 293, 279,
284, 184 (mean 260.0, SD 51); S 366, 361, 353, 353 (mean 358.3, SD 6). S - N: sums +118, +160, +139, +78; grids +73, +82, +69, +169.

### How much do these counts wobble? (the repo's own spread)
- Arms that should barely differ: R (rehearsal-only night) minus N, on 4 seeds x 3 nights = 12 cells. day_sums: SD 10, range
  -20 to +17. day_grids: SD 19.7, range -12 to +49, mean +22 (so a short rehearsal night itself moves grids by ±20 or so).
- Night to night for the same arm (S, nights 1 and 2 against night 3): SD about 11 on both kinds.
- Retraining the base net: `artifacts/claude-rsn358u2-20260928/RESULTS.md` re-ran the same recipe; bigger-size tests moved
  by up to 14 to 23 (sums) and +24.5 on the 4-seed mean (grids7; one seed 187 to 257). That is a between-net spread, not a
  same-net one; it is why every follow-up compares arms on the same checkpoint in the same run.
- Reading (suggested): about 20 on grids and 10 on sums is the size of a difference that could be chance in one seed.

### What sleep length did, kind by kind
- **Sums (shown):** the longer night is about the same as the short one. L - S after night 3: +7 and +3 (seeds 13, 14),
  with S's own seed-to-seed SD at 5. Against no night both gain about +115 to +160. At the harder report size sums10: S 194/197,
  L 196/198. So "longer helped sums" is only true against no night; against the short night it is a tie or +3 to +7 (2 seeds) that
  the sums test, already at 376 to 391 of 400, has little room to show (suggested).
- **Grids (shown):** the short night gains +49 to +86 over no night on seeds 13 and 14 (+73 and +82 after night 3;
  +49 and +86 after night 1). The long night has no gain over no night: L - N = 0, -12, -3 (seed 13) and +13, +36, -12 (seed 14).
  Those L - N values are inside the ±20 wobble; L - S is -76 and -94 after night 3, about four times the wobble.
  So the grid result is "L kept nothing of S's gain", not "L pushed grids far below where they started".
- **Grids get slower, not only worse (shown):** at a forced 8 rounds, L scores 225 and 234 on day_grids, N 274 and 280,
  S 329 and 331; at forced 48 rounds, L 290 and 274, N 295 and 279. So L is about N at 48 rounds and about 50 below N at 8 rounds.
  Mean stop round after night 3: seed 13 N 21.95, S 17.30, L 21.45; seed 14 N 22.52, S 15.04, L 16.04.
- **Old skills (shown):** none damaged. The harm tests are at 300 of 300 for N, S and L, so they only catch big damage;
  the non-ceiling report sizes show no loss for L (rep_grids6 L 194 and 192 against N 194 and 192).
- **Only 2 seeds have L (shown).** Both agree in sign on every comparison above; two seeds is enough to say "the loss
  happened twice", not to give a rate.

## 2. Why did grids fall? Candidates, sorted

What the code says the long night changes relative to the short one (shown, from `scripts/claude_slp358n3_nights.py`
`Arm`, `draw`, `night`): only the number of steps (300 vs 6,000), per night. The learning rate (3e-5 constant), the batch
(256), the optimizer, the half-day-half-rehearsal rule, and the pool of day puzzles (the same 300 sums and 300 grids,
redrawn with replacement) are the same. Each night uses only that day's 300 puzzles per kind (no earlier days are replayed,
except through the rehearsal stream).

By arithmetic on that code (shown, my count): in S each day puzzle is drawn about 64 times in a night (about 75 day steps per
kind x 256 draws / 300 puzzles); in L about 1,280 times. The learning-rate-times-steps that the net moves under is 20 times larger.

| candidate | what the numbers say | status |
|---|---|---|
| **Replay mix** (day share vs rehearsal share) | The share is 50% day / 50% rehearsal in both S and L (code). So the mix ratio is not what differs between S and L. What does differ is how many times each day puzzle is repeated. | The ratio as an explanation of L vs S is **ruled out by the code**; a different reading (a repeat-count effect that a lower day share would reduce) is **untested**. |
| **Overfit to yesterday's 300 puzzles** | About 1,280 passes per puzzle is a lot for 300 puzzles. Consistent with sums (rule-like, they generalise) staying good and grids (Latin squares, may be memorable) not. Also consistent: grids gain at night 1 already gone (L - N = 0 and +13). No train-vs-fresh gap was logged. | **Suggested**, untested. |
| **Learning rate too high for that many steps** (drift; the net moves 20 times as far) | Consistent: the fresh-grid gain disappears even after night 1 (6,000 steps in one night). Also consistent with the slow-down at 8 rounds. Nothing separates it from the row above; both grow with steps. | **Suggested**, untested. This is the design's test. |
| Sums crowd grids out of the net | Half the day batches are sums, half grids in both arms. Sums do not gain more in L than in S (+3, +7). No evidence of a trade-off in the numbers. | **Untested**, weak. |
| The test is noisy | L - S is -76 and -94 against a wobble of about 20. Not a noise result on 2 seeds. Seed count is small. | Noise **unlikely** as the whole story (suggested). |
| Rehearsal stream undoes the day's grids | R alone (300 steps of rehearsal) gains about +22 on grids, so rehearsal does not undo them at 300 steps. At 6,000 steps L is below R's gain. | **Untested**. |

## 3. How the brain does it (simplified textbook science; not checked here)

- **Two learners with different speeds.** A fast store (the hippocampus) holds the day's events; a slow one (the cortex)
  changes gradually. During sleep the fast store replays the day's memories to the slow one.
- **Interleaving.** The replay is mixed with older material. Teaching the slow learner only the new thing quickly
  overwrites the old (the classic reason for "complementary learning systems", McClelland, McNaughton and O'Reilly).
- **Slow cortical learning.** The slow store takes small steps, over many nights, not one long hard push.
- **Sleep is cyclic and bounded.** A night has a few replay cycles. A rough thing to notice is that the brain does not
  seem to hammer one memory a thousand times in a night, and it also seems to turn overall synaptic strength back down
  (homeostasis). I do not claim anything about counts in humans.
Mapping onto our nights: our night is a fast replay of yesterday's 300 puzzles into a fast-learning net. The brain
picture suggests three knobs: (a) a slow learning rate (small steps), (b) interleave with old material (already done: 50%
rehearsal), (c) do not repeat one day's items without limit, and let the night's size follow how much there is to learn.
Only (a) is a single-number change on the existing code. Whether it is the right knob is the question here.

## 4. The ONE follow-up experiment (sealed in PASSMARKS.md)

**Question.** Is the long-night grid loss caused by too much total learning (learning rate x steps)? Test: keep L's 6,000
steps, mix, data and batch plan exactly, and lower only the learning rate to 1.5e-6, which gives the same learning rate x
steps as the short night S (3e-5 x 300 = 9e-3; 1.5e-6 x 6,000 = 9e-3).

Why this change and not "length-scaled replay ratio":
- It is the smaller single change to the existing code (one number), and it is the knob the brain picture calls "slow cortical learning".
- It splits the two leading suspects: a gentle night still repeats each puzzle about 1,280 times. If grids come back, the cause is how far the net moves, not the number of repeats. If they do not, repeats/mix are next.
- The mix ratio cannot explain L vs S (it is 50% in both), so a replay-ratio test would be a change with no observed difference to explain.
- The rule "lr x steps is a fixed budget" also fits the product, where idle time (so night length) is not known in advance: spending more idle time makes each step gentler and cannot make the night move further.

**Arms** (each of seeds 13, 14, 15, 16; same checkpoint per seed; 3 days of 300 sums and 300 grids): N no night; S 300 steps,
lr 3e-5; L 6,000 steps, lr 3e-5; **B 6,000 steps, lr 1.5e-6 (the change)**. B and L share every random draw (checked by the
recorded batch-plan hashes), so B vs L differs only in the learning rate. Four seeds, so seeds 15 and 16 also give L its first test there.

**Why these marks** (numbers as in PASSMARKS.md):
- M0: L - S <= -40 on 3 of 4 seeds. Seeds 13, 14 gave -76 and -94; 40 is two of the grid wobbles (SD about 20) and about half the old gap. If the loss does not reproduce there is nothing to rescue.
- M1: B - L >= +40 (two wobbles) and B >= S - 30 (one and a half wobbles; the gap to close was about 85), 3 of 4 seeds and on the mean, so one odd seed (seed 16's N grids are 184 vs 279 to 293 on the others) does not decide alone.
- M2: sums within 20 of S (two of the sums wobbles, SD about 10; S is at 376 to 388 of 400).
- M3/M3b: slp-358n3's own harm limits (S >= N - 6, lost <= 15 of 300). They are at the ceiling, so I add M3c: the four report sizes that are not at the ceiling (N is 151 to 200 of 200 there), B >= N - 15 of 200 (about four binomial errors on 200 items) on every seed.
- Proved wrong: B - L <= +15 on 3 of 4 seeds, which is inside one wobble. This is the result that says "smaller learning rate does not rescue grids".
- I do not use a mark for "longer beats shorter". That would be a second question; B - S is report only.

**Predictions:** M0 valid 75%; M1 met 40% given M0; PASS 25%; proved wrong 35%.

**Cost and place.** GPU. Estimate (inferred from slp-358n3, not measured): 4 seeds x (L + B = 2 long arms) is about 4 times the long-arm work
slp-358n3 did (2 seeds x 1 L arm, 53 minutes for the busiest seed on an RTX 3090 with four runs sharing the card, spend 0.48 dollars in all).
About 2.5 to 5 hours on a 3090-class card, so roughly 1 to 3 dollars at up to 0.60 dollars/h. Cap $4 for the job
(guard stops at $3.00). BensPC could do it for $0 in 5 to 8 hours (inferred) if free.

## 5. Reuse plan (existing scripts the job calls) and the one new script

| step | script | what it does | new? |
|---|---|---|---|
| seal check | `sha256sum -c artifacts/claude-slp358n3-20260927/SEAL-code.sha256.txt` | 18 of 18 lines must match | existing |
| day sizes | `artifacts/claude-slp358n3-20260927/run-vast/sizes.json` (copied, not re-picked) | sums 12, grids 7, the same for every arm | existing file |
| checks | `scripts/claude_rsn358u_run.py selftest` | 358u reasoner selftest | existing |
| the nights | `scripts/claude_slp358n3_nights.py` (imported: `CFG`, `TINY`, `make_tests`, `day_items`, `dev_items`, `panel_keys`, `key`, `judge`, `Arm`, `night`, `draw`, `train_step`, `load`) | tests, days, exclusions, mix, step, scorer, unchanged | existing, sealed |
| the new arm and runner | `scripts/claude_dir_h6_sleeplen.py` (`run`, `smoke`) | subclasses `Arm` for B (lr only), runs N/S/L/B, writes slp-358n3's JSON layout | **new; py_compile only; never run** |
| scorer for RESULTS | pattern of `scripts/claude_slp358n3_report_score.py` | the recount step writes it from PASSMARKS.md only | not written (blind step) |
| checkpoints | the 4 358u loop `final.pt` (Mac `~/premonition-models/rsn358u/loop-s{13..16}/`, sha256 in `artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt`) | inputs, read only, uploaded, sha-checked | existing |
| vast kit | copy of `handoff/kit/sleep358nv` with the edits listed in the queue file | rents, guards, collects | edits needed (Director) |

Honest limits of the new script: it was only compiled. It has not been run, not even on the tiny settings, because there is no torch on this box.
Its `smoke` command runs slp-358n3's tiny settings on an untrained net and asserts the arms, the two learning rates,
the step counts and that L and B drew identical batches. The queue job runs smoke first and stops if it fails. Its
first real failure must be reported, not patched.

## 6. If the result is proved wrong, the next single change
If B does not rescue grids, the next test keeps L's lr and steps and lowers only how often the day's puzzles are repeated (the day share of each batch, for example 50%
to 10% of batches) or gives the night fresh puzzles of the day's kind; that is a different question and is not run now.
If B passes, the follow-up is a schedule that works whenever the night is cut (lr fixed by budget, checked at stops after 300, 1,500 and 6,000 steps), then the idle-sleep wiring.

## 7. Risks and things I could not check
- The script has never run; a bug would waste a rental (smoke first mitigates this; the tiny smoke does not exercise GPU bf16).
- The 358u checkpoints live only on the Mac; the job cannot start without them and the Director's kit copy.
- Re-running S and L on a different card is not bit-identical to the earlier run (358u2 saw this); the marks use only same-run comparisons.
- Ceiling: sums are near 400; harm tests are at 300 of 300. That is why M2 and M3c are as they are and why sums cannot show length helping.
- A learning rate 20 times lower may simply learn less (B near N). The proved-wrong clause says so, and B - N is reported.
- The test set and the day puzzles are slp-358n3's, which H6 has read the numbers of; nothing was tuned on them and no marks depend on B, but the thresholds were chosen after seeing L and S on seeds 13 and 14. Seeds 15 and 16 are the fresh evidence.
- No blind panels were opened; `panel_keys` reads 358i's sealed panels for hashes only (as slp-358n3 did) and is unchanged.
