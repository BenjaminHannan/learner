# T3 design: newer-weighted replay across three nights (H6's night design)

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Design only; nothing run here (no torch). Labels: shown / suggested / untested.
Serves finish-line item 5. Not the keep-old-skills levers (weight blending, weakest-first replay), not "Deep or just big", not dir-h6 (which changes the learning rate of a long night); T3 changes only how the replayed puzzles are weighted across nights.

## 1. What H6's nights contain (shown, from `scripts/claude_slp358n3_nights.py`)
`draw`: half the batches from the rehearsal stream (`R.Source`, fresh code-made old material), half from the current night's day puzzles (300 sums + 300 grids, kind chosen first). `night` uses only that day's items; earlier nights' puzzles are not replayed except through the generic stream.
The three days use the same kinds (`day_items`: sums size 12, grids size 7, new puzzles each day). Consequence (shown by the code): "weight rehearsal toward newer nights" has nothing to weight, and no night has its own skill. See PASSMARKS "Disclosure".

## 2. What is built (`scripts/claude_dir_t3_recency.py`, imports the sealed nights code unchanged)
`night_mem`: the day half of night n draws, per item, a night index by weights over nights 1..n (S: 0..0:1, U: uniform, W: 2^(night-1)) and an item of that night's pool.
Every random number is shared: the kind, and per item one u in [0,1) and one integer j; the weights only change which night u lands in, so U and W are paired item by item and S, U, W are identical on night 1 (a batch-hash check, `night1_batches_identical_SUW`). The rehearsal half is the same stream in every arm (deep copies of one `R.Source`).
Draw d re-draws rounds, batch plan and rehearsal stream. Everything else is `N3.train_step` at S's settings. Smoke (untrained net, tiny settings, 2 nights) asserts the arms, weights, the identity checks and that S differs from U on night 2.
S here is S's recipe through this new code path, not bit-identical to slp-358n3's S (different random consumption); slp-358n3 / H6 numbers are context only.

## 3. Where each number comes from (raw files, recounted by me 22:13 UTC from `artifacts/claude-slp358n3-20260927/runs/s13..s16`)
| number | value | source |
|---|---|---|
| M1 bar | 24 of 400 (day_grids) | 2 x 11.7, the same arm's night-to-night SD on day_grids (11.2 on day_sums); above R - N SD 19.7 and above S's cross-seed SD 6.4 |
| sums gate | -12 | sums R - N SD 10.3, night-to-night 11.2; room above S is only 12 to 24 of 400, so sums cannot carry a +20 bar |
| G2 | N + 40 | S - N after night 3: +73, +82, +69, +169 (grids) |
| G3, G4 | N - 6 ; lost <= 15 of 300 | slp-358n3's own limits (`artifacts/claude-slp358n3-20260927/PASSMARKS.md` via dir-h6 M3, M3b) |
| G5 | N - 15 of 200 | dir-h6 M3c |
| margin | max(6, 2 x SE) | Ben's rule, 3 draws |
| proved wrong | d <= +6 on every seed | the margin floor: "no seed gains beyond the floor" |
Draft TESTS.md said "at least 20 of 400 on day tests"; that cannot hold on sums (room 12 to 24) and is below the measured grid wobble's twice; replaced.

## 4. Jobs (HELD; BensPC RTX 5070 Ti, $0, one job at a time, no rental)
One job per seed so each is small: `dst-t3-1-s13-benspc`, `-2-s14`, `-3-s15`, `-4-s16`. Job 1 also sets up the folder on BensPC, copies the 4 checkpoints from the Mac (sha256 against `artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt`), checks the seals and runs `smoke`; jobs 2 to 4 reuse the folder.
Cost (inferred, not measured): per seed 9 night arms (3 arms x 3 draws) x 900 steps = 8,100 steps plus 27 morning evaluations of 8 tests. slp-358n3's busiest seed took 53 minutes on an RTX 3090 shared by four runs for about 21,600 steps and 15 evaluations. Guess: 40 to 90 minutes per seed on the 5070 Ti alone; cap each job 150 minutes. If BensPC has no CUDA torch, the job stops with NO-CUDA (nothing is installed).
Checkpoints are on the Mac only (`~/premonition-models/rsn358u/loop-s{13..16}/final.pt`, `000-bash-h7-dirh6-inputs` prints whether they match their seals). Same inputs as dir-h6.

## 5. Risks
- Script never ran (py_compile only); smoke is the first step and any traceback is reported, not patched. bf16 on GPU is not exercised by the CPU smoke.
- GPU arithmetic is not bit-identical between cards: the identity flags compare batch hashes (data), not weights; night-1 S = U = W scores can differ by a few counts on GPU (report only).
- Four seeds x 3 draws is enough for a 24-of-400 bar only if seed effects are small; seed 16's base net is odd (N day_grids 184 against 279 to 293). The gate G2 uses each seed's own N.
- Weights 1:2:4 only, one setting; a different ratio is untested.

## 6. If it fails / if it passes
Fails (proved wrong): recency weighting does not matter when the kinds repeat; the honest next single change is a **different kind per night** (e.g. night 1 sums, night 2 grids, night 3 a third kind) so "newest-night skill" exists; that needs new day generators and a decision from the Director (not built here).
Passes: repeat with a different weight ratio (1:1:8) and with a fourth night before any product claim.
