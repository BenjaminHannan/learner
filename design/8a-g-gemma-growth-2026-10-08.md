# Test 8a-G: does a Gemma-fronted model gain more from size than a plain model? (spec, 2026-10-08, 10:30 AM ET, before any run)

Owner: whole-model roadmap thread. Marks fixed here before anything is built or run. Any change after the first run needs
a dated addendum.

## 0. Why, and Ben's words

- Ben, 10:16 AM ET 10-08 (relayed by the coordinator, his own words): "It should scale more than a plain model. so from
  increased parameters, the benefit should be more than the plain model. Also, the model should have the gemma embedder
  as it's main inputting/ecoder or whatever. basicallly it should just be in our plans for the finished model. [...] if
  the reader being good is part of the model, that's fine. It's just that the thinker should learn more and be the
  driving intelligence. You don't have to ban any help from the gemma reader. Also, I don't care if you use the
  fineweb-edu text. [...] For the three cals waiting on me, just do what you want".
- 8a's result (`8A-10M-RESULT-2026-10-08.md`): today's B2 with the letter reader gained +0.49 from 3M to 10M; the plain
  step model gained +3.77 on the same pool (shown). So the letter-reader B2 fails Ben's bar. The 30M rung of that B2 is
  held (our call, as Ben allowed).
- EGE (B2 with the frozen EmbeddingGemma 2 in front of its letter window, `ledger.py` `eg_embed=True`) is our best
  Gemma-fronted model: 6-seed confirm on the q33 data +2.67 pooled-5 over B2, ahead on 6 of 6, failing only the
  zero-round leak mark (shown, q39). Ben's message allows reader help, so that mark no longer blocks it.

## 1. The one change

Against the 8a ladder, one thing changes: **both the model and the plain yardstick read the prompt through the same frozen
EmbeddingGemma 2 front.** Pool, rows, order, caps (addendum G), seeds, 24,000 updates of 256 rows, learning rate and
rung shapes (3M; 10M grown deep, blocks 2 -> 8) stay as in 8a, so 8a's letter-reader results stand beside these as a
reference (disclosed: the probe hinted that a wider shape did slightly better, +1.0 vs +0.2 on two seeds; it is not used
here, to keep one change).

## 2. Arms (per seed, per rung; both arms of a seed and rung on one rented RTX 5090)

- **Ours (G-B2):** EGE: B2 with `eg_embed=True` (linear adapter, letters kept). 3M = B2_S + adapter; 10M = 8a's deep 10M
  B2 + adapter. The adapter counts as trained parameters.
- **Plain yardstick (G-PT):** 8a's plain step model (`plain_tf_steps_g`, writes steps # answer) with the same front: each
  prompt character's input embedding gets `eg_proj(ln(H))`, H = the EmbeddingGemma state of the token holding that
  character, zero-initialised, nothing added past the prompt. Sized to within 2% of G-B2 at each rung, as in 8a. **Not
  built yet** (the 8a job refuses `eg_embed`; `custom_io/g8a/README.md`).
- Gemma's 271,002,624 frozen parameters are the same in every arm; whole sizes are reported with them counted (Ben's rule).
- Reported, not run again: 8a's letter-reader B2, PT and LLM at 3M and 10M on the same seeds.

**Why the step model is the yardstick** (default picked, Ben can override): it learns the same rows and writes the same
answers, so the difference is the design. The plain LLM recipe gained +15.8 from size in 8a, but it starts 26 points
lower; it stays reported.

## 3. Marks (6 seeds, 400-405; per seed d = 10M score minus 3M score, pooled-5 on the 6,040 dev rows)

1. **Ben's bar: ours gains more from size than the plain model.** Mean over seeds of d(G-B2) - d(G-PT) > 0, with its
   95% CI (t, n = 6) above 0.
2. **Ours grows at all.** Mean d(G-B2) has its 95% CI above 0.
3. **The thinker drives the gain** (Ben: "the thinker should learn more and be the driving intelligence"). With the
   thinker switched off (`loops:0`, zero rounds), the rest of the model (reader and talker) is allowed to help, but:
   (a) at both rungs, G-B2's full score minus its thinker-off score is at least half its full score; and (b) at least
   half of G-B2's mean size gain comes from the thinker: mean [d(full) - d(thinker-off)] >= 0.5 x mean d(full).
4. **Good enough.** G-B2 at 3M has a 6-seed mean of at least 72.0 (8a's mark 4).
5. **Guard.** Chain-5 >= 99 at both rungs (the calculator path is intact).

**Proved wrong** (for "a Gemma front lets our design out-scale the plain model"): mean d(G-B2) - d(G-PT) below -1.0
with its CI below 0.

**Reported:** per-dev-file and per-family gains (the rule and pattern families above all: fewshot_number_rule,
seq_next, order_chain, rule_apply); training-loss parts; thinker-off score per rung; G-B2 minus 8a's letter B2 per rung
(what the Gemma front is worth); G-PT minus 8a's letter PT; hours and dollars per arm.

## 4. Two-seed screen first (seeds 400 and 401; readout fixed now)

- **Go on to the other 4 seeds:** d(G-B2) - d(G-PT) >= +1.0 on both seeds AND d(G-B2) > 0 on both.
- **Stop:** d(G-B2) - d(G-PT) <= 0 on both seeds. The design change has to come from the thinker, not the reader.
- Otherwise **unclear:** run the other 4 seeds (the full marks then decide).
- Guard on the screen: chain-5 >= 99 on both seeds.

**Prediction (suggested, written now):** the screen stops. 8a's per-family table points at the thinker and its answer
writer (near 100% on calculator questions, flat on rule questions), and a better reader does not change what the thinker
can express. What would prove that prediction wrong: G-B2 passes the screen with gains on the rule families.

## 5. Build, money, order

- **Build** (8a build code, PR #51, branch `claude/project-thread-f1to6a`; routed to its owner through the
  coordinator): (1) the G-PT front in `plain_lm.py`, zero-initialised, with a unit test that at step 0 it computes exactly
  what PT computes; (2) the 8a job accepts `eg_embed` when every arm has a front; (3) the bands count the adapter; (4)
  the box installs a transformers version with EmbeddingGemma 2 (>= 5.19; 8a's box pins 5.17.0) and checks the 3 probe
  vectors (`python -m custom_io.models.eg check`).
- **Speed first:** one 5090 times 200 updates of each arm at 3M and 10M (about 20 minutes). The caps per box are set
  from it. Our estimate before timing: about 12 GPU hours a seed (Gemma's forward pass about doubles the 3M cost), about
  $6 a seed, about $12 for the screen and about $36 for all six seeds (could be off 2x).
- Rented 5090s (Ben's standing Vast OK; the account refills). Per-box caps from the speed check; boxes destroyed when
  done; checkpoints exported (one collector at a time).
- **Not in this test:** 30M; the learned stop (H1); the calculator as a tool (T1/2c2). Those belong to B3, which must
  pass this same bar at 3M -> 10M before the 8c ship build.

## 6. Addendum A (2026-10-08, 10:33 AM ET, before any run): build check and speed

- **Build:** commit 2a46cb17d0 (PR #51). Checked by the roadmap thread on CPU. The plain step model's front is zero-initialised and added only at the
  real prompt positions, in both training and answer writing. The 3M sizes under the addendum G caps are G-B2 3,544,913 and G-PT 3,495,936 (1.4%
  apart). Letter-reader counts are unchanged from 8a.
- **Bug found, fix requested:** at 10M the job crashes before training, because `configs.b2_cfg` gets `n_loops` twice. The one-line fix gives
  G-B2 10M = blocks 8, 10,496,537 (+4.97%, in band) and G-PT 13 layers, 10,603,776. The fix landed as 612f5c5b01 (10:34 AM ET), and the 10M boxes run on it. The 3M boxes run on
  2a46cb17d0, because the 3M path does not touch that code (disclosed).
- **Speed check folded into the screen:** the speed probe has no Gemma option. Each screen box's own timing therefore sets the caps for seeds 402-405,
  and the screen boxes self-stop at 8 hours (MAXH 8, about $4.50 a box at most). Marks, arms and readout are unchanged.
- **Pool check:** every 8a-G box must build the same pool as 8a for its seed. Its pool MANIFEST sha must equal the 8a box's for that seed and rung,
  or the box's results do not count.

## 7. Addendum B (2026-10-08, 2:50 PM ET, after the first Vast run): the screen moves to BensPC

- **Why:** Ben, 2:39 PM ET 10-08 (relayed by the coordinator): "just use benspc for now". Vast credit is at $0, so there are no new rentals.
- **What the Vast boxes left:** the four screen boxes (2 seeds x 2 rungs, both arms on each) stopped when the credit ran out. One arm-run finished:
  G-B2 3M seed 400 = **72.42** pooled-5 (4,374 of 6,040). Thinker-off (`loops:0`) 10.48; chain-5 100; 3.16 updates/s on a 5090, 2.11 h, peak 8.9 GB.
  Its pool MANIFEST (1d32e12a) equals 8a's seed-400 pool, so it passes the pool check. Letter-reader B2 on the same seed and pool scored 71.59, so
  the Gemma front is worth +0.83 here (one seed, reported). The other seven arm-runs were cut partway and nothing from them is kept. Box 54861956
  holds the finished G-B2 checkpoint and stays (stopped) until credit returns. The three boxes with nothing finished were destroyed.
- **New plan:** the whole screen runs on BensPC's RTX 5070 Ti (16 GB) from queue `8aG-pc-screen.txt` at code 612f5c5b01 (the 10M fix; the 3M path is
  unchanged). One job at a time, sharing the GPU with the reader/talker thread through `GPU-BUSY.txt`: data build (pool-set MANIFEST e8f32daf...),
  then 3M s400, 10M s400, 3M s401, 10M s401, each with both arms. Inputs: data pool at da1a59cf (`claude/data-pool-8b`), own text from
  `claude/8a-own-data`. Addendum A's pool check still applies to every PC job.
- **Same machine:** G-B2 3M s400 runs again on the PC, so both arms of every seed and rung come from one machine. The PC run counts; the Vast 72.42 is
  reported as a cross-machine check (suggested: they agree within about 1 point).
- **10M memory:** both 10M arms use gradient accumulation 2 (two halves of 128 rows, still 256 rows per update, same rows and order), because the
  letter-reader 10M B2 peaked at 21.5 GB on the 5090 and the PC has 16 GB. Disclosed: bf16 sums can differ slightly from one 256-row pass.
- **Hours:** set from the first PC run's speed. Our guess before timing (suggested): about two days of PC time for the screen, more while the
  reader/talker jobs hold the GPU. Seeds 402-405, if the screen says go on or unclear, also run on the PC unless credit returns.
- Marks, arms and the screen readout are unchanged.

## 8. Addendum C (2026-10-08, 3:28 PM ET): on hold

- Ben, 3:27 PM ET 10-08: "I only want large amounts of money being spent on a training run that demonstrably works. Can you do that instead of
  doing a bunch of little tests?" The coordinator's reading: only runs already in progress on free machines finish; no new tests start.
- The PC screen had not started (the PC was offline), so it is held, not run. The queue and code stay staged on the PC. The thread "One big proven
  training run" decides whether this check gates its run. Box 54861956 stays stopped (no credit is spent on it). Marks unchanged.

## 9. Addendum D (2026-10-08, 3:40 PM ET, before any valid run): the 9-slot bug, and the fixed re-run (gate G1)

- **Bug (shown).** Found by Ben's 8b session (`design/8b-gemma-growth-2026-10-08.md` addendum B on `claude/nice-lamport-al1gwo`), confirmed in the code by
  the "One big proven training run" thread, and reproduced here on CPU at 612f5c5b01. `caps.apply()` (`custom_io/g8a/caps.py:139-147`) patches the
  Ledger's `N_REG` / `GEN_MAX` only if `custom_io.models.ledger` is already imported. `train.py` applies the caps at line 147 and builds the model at
  line 155, and `models.build` imports the Ledger lazily (`models/__init__.py:22`). So the Ledger kept its defaults `N_REG = 9`, `GEN_MAX = 8`
  (`ledger.py:62-63`): 9 register tokens instead of 36, and GEN training targets cut to 8 letters (`ledger.py:441`). That breaks addendum G's caps
  and the no-cut rule. CPU check: after `apply(caps_g.json)` the caps say n_reg 36, but the imported Ledger has N_REG 9, GEN_MAX 8.
- **Affected:** every 8a B2 run (ladder and shape probes), and this test's one finished arm (Vast G-B2 3M s400, 72.42). The plain arms are
  unaffected. The 8b session reports (not rechecked here): none of the 6,040 scored dev rows has a GEN answer over 8 letters; 191,172 of
  1,655,902 pool rows have answers over 8 letters; trained parameter counts do not change.
- **Fix:** only `caps.py` from `g8b/overlay/custom_io/g8a/caps.py` (branch `claude/nice-lamport-al1gwo` at e9125e9013; sha256 3da2dfbb...). It
  differs from 612f5c5b01's `caps.py` only in importing those modules before patching (checked with diff). The overlay's `configs.py`, `job.py`
  and `ledger.py` are **not** used: they sit on an older base without the plain arm's Gemma front and the pinned caps, and `gen_ar` is 8b's own
  change. CPU check with the fix: Ledger N_REG 36, GEN_MAX 35; trained counts from `sizes()` unchanged by the fix (3M G-B2 3,543,889 /
  G-PT 3,495,936; 10M 10,495,513 / 10,603,776; counted with sizes()' default vocab, 1,024 below the runs' 108-letter vocab).
- **G1 = this test, re-run with the fix.** Marks (section 3), arms (G-B2 vs G-PT, same Gemma front), seeds 400 and 401, rungs 3M and 10M, the
  pool, 24,000 updates of 256 rows and the screen readout (section 4) are all unchanged. BensPC only (addendum B), run as gate G1 of the big-run
  plan (`/mnt/project-files/big-run/PLAN.md` section 5). New queue name, so no code frozen from the old staging is reused.
- **Memory:** the thinker now holds 8 + 36 = 44 tokens instead of 17, so addendum B's memory figures no longer hold. Start at gradient
  accumulation 2 at 3M and 4 at 10M for both arms (still 256 rows per update, same rows and order). If a job stops on CUDA out-of-memory,
  rerun it with accumulation doubled for both arms (at most 8). Accumulation changes only bf16 summing order (disclosed).
- **Voided or relabelled:** the Vast G-B2 3M s400 72.42 is the bugged model and counts toward nothing. In section 3's reports, "G-B2 minus
  8a's letter B2" now mixes two changes (the Gemma front and the fix); it stays reported with that label.
- **Prediction (suggested, written now):** the same as section 4: likely stop or unclear (the 8b session and the big-run plan expect G-B2 to gain
  +0 to +2 against G-PT's +3 to +4). What would prove it wrong: go on both seeds, with gains on the rule families.
- **Hours:** set by the first PC job's speed. The big-run plan's estimate (suggested) is about 2 days of PC per seed, so about 4 days for the
  screen. The 36 slots make G-B2 slower than that estimate assumed (untested).

## 10. Addendum E (2026-10-08, 5:50 PM ET, before any G1 training): Windows line endings and the PC pool check

- G1's first PC launch (about 3:50 PM ET) stopped at the data step, before any training: `own72_MANIFEST.json` hashed to 5d9e79d7 instead of
  e8f32daf. Shown: the file at da1a59cf hashes to e8f32daf as committed and to exactly 5d9e79d7 with every `\n` turned into `\r\n`, so Windows
  git converted line endings on checkout. Fix: the data-pool and own-data checkouts are renormalized with `core.autocrlf false` (expected hash
  unchanged). The 36-slot check and the Gemma check passed on the PC.
- **Pool check on the PC (replaces addendum A's byte check for PC jobs):** Python on Windows writes the pool's `train.jsonl` with `\r\n`, so its
  byte sha (and the MANIFEST sha) differ from the Vast boxes even when every row is the same. The check is on content: sha256 of `train.jsonl`
  with `\r\n` read as `\n` must equal 8a's pool `train_sha256` for that seed (s400 b90ff7d7..., s401 910485f1...) with 1,418,702 rows. A
  mismatch stops the queue.
- 6:30 PM ET: the relaunch stopped again in the data step, still before any training. The web slices that `data_pool/web_slice.py` builds
  on Windows also come out with `\r\n`. Shown on the PC: with `\r\n` read as `\n`, the rung3 and rung10 slices match the manifest's sha256
  exactly (12,345 and 36,132 lines). The slices are converted to `\n`, checked against the manifest, and placed where the data step looks first.
  Nothing in the content changes.
- Marks, arms and readout unchanged.

## 11. Addendum F (2026-10-08, 8:18 PM ET, G1 running): GPU memory on the 16 GB PC

- G1's first training run (6:32 PM ET, 3M s400, accumulation 2 = 128 rows per pass) spilled into Windows shared memory (4.2 GB shared on top of
  15.5 GB dedicated, 98% use at 106 W, speed falling from 0.97 to 0.57 updates/s by step 1,000). Per addendum D's rule it was stopped and
  restarted at 7:08 PM ET with accumulation 4 for both 3M arms. The 1,000 updates already done were discarded, so nothing mixed.
- **10M settings (suggested estimate, set before those jobs start):** the 36-slot 3M B2 needs about 150 MB per row, and in 8a the 2 -> 8 block step
  raised per-row memory about 2.4x. So the 10M B2 runs at accumulation 8 and the 10M plain arm at 4. The arms may differ, since accumulation changes
  only the bf16 summing order (256 rows per update either way).
- **Spill rule (replaces "at most 8"):** a job whose shared GPU memory passes 1 GB is stopped and rerun with that arm's accumulation doubled, up to 16.
- Marks, arms and readout unchanged.

## 12. Addendum G (2026-10-09, 8:40 AM ET, G1 running): first G1 result in, and a spill on seed 401

- **3M s400 is done** (shown, `claude/8a-g-pc-results` commit 532ebdc, `results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/`). G-B2: pooled-5
  73.01 (4,410/6,040), chain-5 99.9, thinker-off (loops:0) 0.66, 1.02 updates/s, 6.5 h. G-PT: 67.12 (4,054/6,040), chain-5 91.0, 2.80 updates/s,
  2.4 h. One rung of one seed: no readout yet. The Vast 72.42 and letter-B2 71.59 remain context only.
- **Is the fix inside the run?** Shown before launch: the PC's code printed `36 35` and its `caps.py` hash matched. Not logged inside the run (the
  `caps` event prints 36 with or without the bug). Suggested: G1's B2 needs about 1.6x the memory per row and about 1.7x the compute per row of
  the bugged Vast run, which fits the larger thinker.
- **Seed 401 spilled** (the restart below was replaced by addendum H). 3M s401 B2 (accumulation 4) reached 1.15 GB of shared GPU memory, and 500 updates took 1,169 s against 490 s for s400.
  The GPU showed 15.9 of 16.3 GB in use with Ben's desktop apps also on the card (inferred cause). Per addendum F it is stopped at update 9,000 and
  rerun from the start as queue 8aG1f. The partial run's files stay on the PC and count for nothing.
- **Settings for the rest of G1 (set before these runs start):** 3M s401 at accumulation 8 for both arms; 10M at B2 16 and plain 8. This goes one
  step past addendum F's "double the spilling arm" so that the 10M runs, which need more memory, don't lose hours to the same spill. It changes
  only the bf16 summing order (256 rows per update either way). If a 10M B2 at 16 still spills, it stops and waits for a decision.
- **Job cards:** the PC babysitter's cards are in `results/8a-g/pc-job-cards/`. The stall check reads the step count, because Windows does not refresh
  LastWriteTime on a file that is still open.
- Marks, arms and readout unchanged.

## 13. Addendum H (2026-10-09, 9:05 AM ET): 3M s401 is not restarted after all

- **Change to addendum G:** 3M s401 is **not** stopped. It keeps running at accumulation 4, as 3M s400 did. Reasons: at 8:46 AM ET it was at
  update 9,500 of 24,000 (shown, 1,170 s per 500 updates). Finishing it slowly needs about 9.4 h more for B2. A restart needs 24,000 updates
  at accumulation 8, and the half-size micro-batches of this small model are likely slower per update too (suggested; not measured). So a
  restart saves little or nothing, and it would need Ben's own go on the Mac. Keeping accumulation 4 also makes the two 3M seeds identical in
  settings.
- **10M jobs run in a new queue, 8aG1f** (`results/8a-g/pc-job-cards/8aG1f-pc.txt`). They use B2 at accumulation 16 and plain at 8, as set in
  addendum G, with the start-memory gate lowered from 13,000 to 9,000 MiB so a busy desktop doesn't hold them back. WORK\STOP keeps them out of
  the old queue. `q8aG1f_wait.ps1` runs detached on the PC: it waits for the 8aG1e runner to exit, moves STOP, starts 8aG1f, and swaps the job
  cards (g1e to done, g1f installed). Nothing is stopped.
- Estimates (suggested): 3M s401 done about 8:30 PM ET 10-09; the two 10M jobs follow at an untested speed, so the gate lands late Saturday ET.
- Marks, arms and readout unchanged.

## 14. Addendum I (2026-10-09, 10:50 AM ET, before any 10M result): stop early if seed 400 already rules out a pass

- **Rule (fixed now, before any 10M run has started):** after 10M s400, compute seed 400's gain difference, d(G-B2) - d(G-PT), with
  pooled-5. If it is at or below -1.0, 10M s401 is not run. The gate then reads **Stop (one seed)**. In every other case 10M s401 runs as planned
  and the readout is unchanged.
- **Why:** Go needs +1.0 or more on both seeds, so a seed 400 result at or below -1.0 rules Go out. Skipping seed 401 then saves about half a
  day of the PC. The big-run replan (Ben 10:43 AM ET 10-09: no Vast, soonest finish) waits on this gate. A result between -1.0 and +1.0 also rules
  Go out, but seed 401 still runs then, because it tells Stop from Unclear and that changes what the replan does next. The -1.0 line came from
  the coordinator's replan note.
- **How (on the PC, no one needs to be awake):** queue 8aG1f now holds 10M s400 only, and queue 8aG1s401 holds 10M s401. `q8aG1s401_wait.ps1`
  waits for 10M s400 to finish, then runs `g1_futility.py` (exit 3 = skip). Any error in the check starts seed 401, so a fault never holds the
  GPU back. Files are in `results/8a-g/pc-job-cards/`. Settings are unchanged from addendum H.
- Marks, arms and readout otherwise unchanged.

## 15. Addendum J (2026-10-09, 11:05 AM ET): jobs staged for the first PC gap after G1 (not part of G1's readout)

Asked by the big-run scorecard (coordinator relay, 11 AM ET). Both are **staged, not running**. Each starts only when Ben types go in the
Mac chat and no queue runs. Cards and queue files are in `results/8a-g/pc-job-cards/after-g1/`.

- **fc100, the 100M fit check, part A (about 1 h).** G1's code and pool. The dense ledger thinker at the planned 100M shape: 21 blocks x 512,
  12 rounds, Gemma input. Three runs of 60 updates at gradient accumulation 64, 128 and 256 (4, 2 and 1 rows per pass). It reports
  updates per second, peak and reserved memory, and any shared-memory spill. **It does not cover** H1's learned stop with round
  checkpointing, 2,000-letter rows, or the larger caps, because B3's code and the long-chunk pool don't exist yet. Those parts still need
  their own check on B3. The big-run thread decides whether part A is worth its hour or should wait for B3.
- **c30, the G-PT 30M control (about 1-2 PC days, not measured).** G1's plain arm at the 30M rung, seed 400 only (kill-first), with the same
  code and pinned caps. The job builds the 30M pool (own rung 30 + web rung30 slice) first, because 3M and 10M share a smaller pool.
  Steps follow the pool schedule: max(24,000, 600M seen pieces / (256 x mean row pieces)), about 55,000 if rows average 42 pieces as at
  3M (suggested). Gradient accumulation for the plain arm is staged at 16. It is set from G1's 10M-s400 plain-arm peak memory before launch,
  and the spill rule doubles it up to 32. Mark (big-run scorecard row 3, theirs): B3's 10M-to-30M gain minus this control's gain over
  G-PT 10M s400 must be >= +1.0 on one seed, kill-first; <= 0 proves it wrong. B3 group 1 goes first if it is ready.
- **Cap-hit counters for G1 (scorecard row 6).** Shown for the 3M/10M s400 pool: its `caps_report.json` gives `rows_over_caps` 0 for every cap,
  on the 1,655,902 train rows and on the dev splits with programs. `g8a.job` exits instead of cutting a row that touches a cap. The s401 pool
  writes the same report; it gets read when its results are collected.
- **Decision (big-run thread, relayed 11:08 AM ET):** fc100 part A runs in the first PC gap after G1, because a measured 21x512 speed is
  worth the hour and a no-fit kills the PC plan early. A part A pass does not clear the 100M launch: part B (H1 round checkpointing,
  2,000-letter rows, new caps) runs on B3 group 1 before launch. c30 runs right after fc100 unless B3 group 1 is ready first. Row 6: G1 passes
  the truncation audit on both seeds (the non-ASCII drops are disclosed, not truncation). Starting still needs Ben's go in the Mac chat.

## 16. Addendum K (2026-10-09, 11:20 AM ET): one post-G1 chain on the PC, experts test first

Asked by the coordinator (relay, 11:10 AM ET) after Ben asked for the experts test first after G1 (10:18 AM ET). Two separate waiters
("start GX when no queue runs" and fc100/c30) could race for the same gap, so one waiter runs them in order, one queue at a time:

1. **Gate G1 ends:** an ok `RESULT.json` for `8aG1s401*-10M-s401` (any spill letter), or the futility waiter logged the s401 skip, or
   `WORK\G1-DONE.txt` (manual release); and no G1 waiter, no queue runner and no `WORK\STOP` for 5 minutes in a row.
2. **Test GX stage 1** (thread "Many experts, many layers test", queue `8aGX` from `src-8gx`, its card's step 3 exactly), unless
   `WORK\GX-ON-MAC.txt` exists (stage 1 moved to the Mac). It needs `src-8gx\GX-SETUP-OK.txt`, written by the installer after that card's
   setup steps 1-2 (experts branch `custom_io` at c1464d19b7, caps hash, `test_moe` ALL OK on CPU). If any job in its queue file ends without
   an ok `RESULT.json` (a spill relaunch as `8aGXb` still counts), the chain **holds** until `WORK\GX-DONE.txt` exists, so a fixed GX goes
   straight back on instead of waiting behind c30.
3. **fc100** (addendum J). An out-of-memory run is a result, so the chain goes on either way.
4. **c30** (addendum J), skipped if `WORK\B3-READY.txt` exists. Its accumulation is now **PT=32**, not 16: G1's 3M s401 spilled at
   accum 4 and lost about half its speed, which costs far more than smaller passes do. The spill rule doubles 32 -> 64 -> 128.

`WORK\STOP` holds the chain at every step; the waiter never removes it. Files: `after-g1/q8aPost_wait.ps1` (the waiter) and
`after-g1/install_post_g1.ps1` (sets up `src-8gx`, copies the queue files and card templates, starts the waiter detached; it starts no GPU
work). Both parse clean, and the waiter ran end to end in a mock PC (fake processes and clock) for five cases: normal, s401 skipped, GX on
the Mac, GX failed then released, B3 ready (shown, mock only). Rough PC time after G1 (suggested, not measured): GX about 20-24 h (its card),
fc100 about 1 h, c30 about 1-2 days. Starting needs Ben's go.

## 17. Addendum L (2026-10-09, 11:50 AM ET): fc100 part A moves to B3 inputs

Asked by the big-run thread (coordinator relay, 11:41 AM ET): run part A with the B3 caps on the B3 3M long-chunk pool, so the same hour
measures the memory that matters. It stays in the post-G1 chain behind GX. G1 itself is unchanged (still `src-8ag`, 612f5c5b01 + caps fix).

- **Code:** new folder `src-b3` = `custom_io` at **c24bce9489**, not 61fb6fdac2: `--cloze-long` and `caps_b3.json` exist only in c24bce9489,
  the child of 61fb6fdac2. Its diff against 61fb6fdac2 touches only `g8a/caps.py` (`compute_global`), `g8a/job.py`, `g8a/pool.py` and adds
  `caps_b3.json`; `train.py` and the models are byte-identical (shown: same file hashes). Hashes: caps.py D276FAC0..., caps_b3.json
  BD81C67F..., `data_pool/cloze_long.py` FF6A2E12... (branch claude/data-pool-8b at 3d0afbeadd, copied to `WORK\b3-inputs`).
- **Pool:** the PC builds it itself (the audited B3 3M pool was built on cloud CPU). Queue line `8aFC-pool-3M-s400-L` runs `g8a.job --rung 3M
  --seed 400 --cloze-long ... --caps-file caps_b3.json`: it builds `p10-rung30-s400-a64-L` and its `caps.json` and `caps_report.json`, then
  **stops at the 3M size check**, because under the B3 caps the 3M B2 arm is 4,023,377 parameters, more than 3% from 3,500,881 (shown on
  CPU at c24bce9489). That stop is expected here, and it means **B3 group 1 at 3M will hit the same check** until its owner widens the 3M
  band for B3 caps or sizes the 3M arms down.
- **Runs:** unchanged shape (ledger, 21 blocks x 512, 12 rounds, Gemma input, 60 updates at accumulation 64, 128, 256), now `--data` and
  `--caps` from the `-L` pool. Rough PC time about 1-2 h with the pool build (suggested). Part B (H1 round checkpointing) still waits for B3
  group 1.
- **Chain and installer:** the waiter launches `8aFC` from `src-b3` (its own caps hash) and needs `src-b3\B3-SETUP-OK.txt`; without it, it
  logs NEEDS ATTENTION and goes on to c30. The installer unpacks `b3.zip`, checks the three hashes, runs `test_g8a` on CPU (passes, 12 s here)
  and writes the marker. Both scripts parse clean; the mock-PC run starts 8aGX from src-8gx, 8aFC from src-b3, 8aC30 from src-8ag (shown,
  mock only). c30 keeps G1's code because it is G1's control.

## 18. Addendum M (2026-10-09, 11:55 AM ET): c30 moves to the B3 caps and pool

Asked by the big-run thread (coordinator relay, 11:52 AM ET; PLAN.md substitution 4): a rung is a matched pair, so the plain partner of
B3 30M runs at caps_b3 on the B3 long-chunk pool. c30 therefore runs from `src-b3` (c24bce9489) with `--cloze-long` and
`--caps-file caps_b3.json`, PT only, seed 400, accum PT=32, and builds `p30-rung30-s400-a64-L` first. It is still last in the post-G1
chain and still skipped if `WORK\B3-READY.txt` exists. G1 is unchanged.

- **Size check (shown on CPU at c24bce9489, caps_b3, Gemma front):** 10M B2 9,816,397 / PT 9,814,442 and 30M B2 29,718,329 / PT 29,556,480
  pass the job's bands. Only 3M refuses (addendum L) until the matched-pair band code lands.
- **Its 10M partner** is G2's own G-PT 10M at caps_b3, not G1's (different pool and caps). G2's G-PT 3M and 10M are not staged here.
- **Time (suggested, not measured):** about 52,000 steps if rows average 44.7 pieces as in the B3 3M pool (60.0M pieces / 1,343,273 rows),
  slower per step than at G1's caps because of the long rows: about 2-3 PC days.
- Installer and waiter: both queue files go to `src-b3`, the waiter starts c30 from `src-b3` with its caps hash and needs
  `B3-SETUP-OK.txt`. Parse clean; the mock-PC run starts 8aGX (src-8gx), 8aFC and 8aC30 (src-b3) in order (shown, mock only).

## 19. Addendum N (2026-10-09, 11:59 AM ET): G2's plain controls join the chain; src-b3 moves to 71299b1a47

Asked by the big-run thread (coordinator relays, 11:55-11:56 AM ET). New post-G1 order on the PC: **G1, GX stage 1, fc100, g2c3, g2c10, c30**.

- **src-b3 = custom_io at 71299b1a47** (was c24bce9489): it adds the matched-pair 3M band (3M under sized caps is the architecture at those
  caps, only a +50% runaway refused; test `test_3m_band_follows_the_caps`) and tool.py fixes (CELLS 21, tape entry counter). `train.py`,
  `ledger.py`, `plain_lm.py`, `g8a/job.py`, `g8a/pool.py`, `caps.py` and `caps_b3.json` are byte-identical to c24bce9489, so fc100 and the
  controls train the same code. Shown on CPU at 71299b1a47: `test_g8a` 16 ok; under caps_b3 with the Gemma front the size check passes at
  3M (B2 4,023,377 / PT 4,022,440), 10M and 30M.
- **fc100's pool line** no longer stops at the size check: `--maxh 1e-9` skips its arm, so its RESULT reads arm_failed with PT skipped_maxh,
  and nothing trains (a tiny value, so a rerun on an existing pool still skips).
- **g2c3** = G-PT 3M at caps_b3 on `p10-rung30-s400-a64-L` (the pool fc100 builds), seed 400, accum PT=16. **g2c10** = G-PT 10M on the same
  pool (3M and 10M share it, as in G1), seed 400, accum PT=32. Both from src-b3 with `--cloze-long` and `--caps-file caps_b3.json`. Seed 401
  only if B3's seed 400 is not at its proved-wrong line (big-run thread's call; not staged). Spill rule doubles twice.
- **c30** accum PT=64 now (was 32), so 4 rows per pass: micro-batches pad to the longest row, and about 1 row in 100 is a 2,000-letter
  chunk (suggested from the 80/7/7/6% piece mix), so about 4% of 4-row passes hold one, against about 47% of 64-row passes. A wider model
  needs more room per row than 10M. Spill rule 64->128->256.
- **Accumulation reasoning (suggested, not measured):** G1's G-PT 3M peaked at 2,681 MiB allocated (10,334 reserved) at accum 4 with rows
  of at most 280 letters; padding to 2,000 letters is up to about 7x the activations, hence 4x fewer rows per pass than G1's 3M (accum 4) and 10M (accum 8) plain runs.
- **Rough PC time after G1 (suggested):** GX about 20-24 h, fc100 about 1-2 h, g2c3 + g2c10 about 0.5-1 day (big-run thread's estimate),
  c30 about 2-3 days. The chain still skips only c30 if `WORK\B3-READY.txt` exists.
- Waiter and installer updated (four src-b3 queues and cards); both parse clean; mock-PC runs give the order above for normal, B3-ready
  and GX-failed-then-released cases, and the installer mock sets up both folders and copies the four queues (shown, mock only).

## 20. Addendum O (2026-10-09, 12:45 PM ET): chain version 2, B3 group 1 at 3M joins, GX split by seed

Asked by the big-run thread (coordinator relay, 12:11 PM ET). Ben's go at 12:27 PM ET covered version 1 (addenda K-N), which is what the
PC gets now. Version 2 installs only on his go on a new card, and only while version 1's waiter is still waiting for G1.

- **Order (v2):** G1, then GX seed 400, fc100, g2c3, **B3 3M seed 400** (then its readout), GX seed 401 if GX seed 400 is alive, g2c3 seed
  401 and **B3 3M seed 401** if B3 seed 400 is alive, g2c10, then c30. c30 runs earlier, in the gap, if B3's fixed code is not installed
  when B3 is due; the chain then holds for it, or for `WORK\B3-SKIP.txt`.
- **Alive rules (adopted by the big-run thread, 12:40 PM ET):** GX seed 400 is alive when GX minus G-B2 on pooled-5 is at least +0.5
  (X1's +1.0 less the 0.5 hair) and X4 is not "fail" (`analyze_gx --seeds 400`). B3 seed 400 is alive when B3-1 is at least +1.0
  (PLAN.md sec. 5: below +1.0, no seed 401). `WORK\GX-S401-GO.txt` / `GX-S401-SKIP.txt` and `B3-S401-GO.txt` / `B3-S401-SKIP.txt`
  override the rules. A score that cannot be read starts no seed-401 run and says NEEDS ATTENTION.
- **g2c3 seed 401 is added (default picked here):** B3 seed 401 needs its own plain partner on the same pool and caps (PLAN.md
  substitution 4). It builds the seed-401 long-chunk pool, which B3 seed 401 then reuses.
- **GX queues `8aGXs400` / `8aGXs401`:** the experts thread's two g8a lines, one per queue, unchanged. The jobs keep the names
  `8aGX-3M-s400` / `-s401` that `analyze_gx` reads; a spill relaunch renames only the queue.
- **B3 queue `8aB3G1s400` / `s401`:** arm B3, `--b2-extra '{"eg_embed": true}'` (B3_G1 already holds every switch), `--cloze-long`, `--caps-file
  caps_b3.json`, accum B3=32 (a guess, unmeasured; spill rule 32, 64, 128). Code `src-b3r` is PR #56 with the round-cap fix below. Its
  pair g2c3 runs from src-b3 (71299b1a47). Shown: the diff from 71299b1a47 to e070556ce5 only adds B3 (the arm, its job branch, the
  LOOP_SWEEP hook, and tool_h1/b3 in the caps patch list), so the plain arm and the pool builder are the same code.
- **Bug found before any B3 run (shown):** at e070556ce5, `caps.apply` sets every listed module's `CAP` to `plain_target`. Commit
  ca4460b13d added tool_h1 and b3 to that list, so H1's round cap of 32 becomes 109 under caps_b3.json (and under caps_g.json).
  `b3_capcheck.py` builds a tiny B3 after `caps.apply`, in train.py's order, and prints 109. It went to the PR #56 owner. The upgrade
  refuses any B3 code whose cap is not 32, then runs test_g8a and test_b3_run on CPU.
- **Readout `b3_readout.py`** (run by the waiter after each B3 run; its lines go into that queue's log). B3-1: pooled-5 minus g2c3's
  (checks same pool hash, caps and seed). B3-2: loops:0 over full, chain-5, donor. B3-3: noexec program rows against intact. B3-4: H-a with
  the loops:32 lesion, H-c, H-d, H-e flat 5, H-f, mean rounds by program length (1 against 11 steps: n_res is 11 under caps_b3, so there
  are no 12-step rows; big-run thread, 12:40 PM ET), and 8-11 step chains at the own stop against loops:32 (from the checkpoint; no
  training). B3-5: the held-out long rows (`long_dev.jsonl`, 1,360 rows, 340 per bucket; SHA-256 8cf15f7b... at f1to6a 649c1e3fcb, rebuilt 1:03 PM ET because the first build, 7ab9b5b9..., had 9 of its 340 base prompts in the skills training set; swapped on the PC before any B3 run). The dev splits stop at
  280 letters (shown: caps_g.json, sized on own72 + slice + dev, has max_prompt 280), so they cannot fill the long buckets. B3-6: every
  cap counter at the end of training and after the evals, plus the pool's rows_over_caps. Exit 0 alive, 3 dead, 2 cannot tell.
  Shown: it runs end to end on a tiny real B3 (no Gemma) trained at e070556ce5, including the checkpoint part and the real long-dev file.
- **PC fix to version 1 (shown):** on BensPC, test_moe's first test (`test_off_is_base`, weight bytes against gold made on another
  machine's torch build) fails at the first weight. The installer now runs the other 8 tests after `caps.apply(caps_g)`; they pass here in
  9 s. A setup folder left by a failed run is renamed aside, never deleted.
- **Tests (mock PC only):** the waiter gives the expected order in 9 cases (normal, both seeds dead, X4 failed, late B3 code with c30 in
  the gap, B3 skipped, GX on the Mac, unreadable scores, override flags, GX failed then released). The upgrade gives the expected result
  in 5 cases (replaces a waiting v1, refuses a started v1, refreshes a running v2, sets up the fixed code, refuses a 109 cap).
- **Rough PC time after G1 (suggested, unmeasured for B3):** GX seed 400 about 11 h, fc100 1-2 h, g2c3 about 2.4 h, B3 3M seed 400
  12-26 h. If both are alive: GX seed 401 about 11 h, g2c3 seed 401 about 3 h, B3 seed 401 12-26 h. Then g2c10 about half a day and c30
  2-3 days.

## 21. Addendum P (2026-10-09, 1:15 PM ET): answers to the architecture audit (B01-11, B01-12, B01-13, B01-15)

From `architecture/AUDIT-2026-10-09.md` (12:20 PM ET). Nothing here changes a mark or a run.

- **B01-12, answers over 35 letters (shown):** G1's own cap report on the PC (`8aG1d-3M-s400/caps_report.json`, pushed to
  `claude/8a-g-pc-results`) counts 1,655,902 rows; the longest answer is 35 letters, and rows over the caps are 0 for every cap, in
  training and in the dev files. So no G1 training answer is cut at 35. B3 counts `gen_answer_over` and `answer_over_max` at run time as
  well (readout B3-6).
- **B01-13, what "thinker off" means once the stop is learned (shown):** `loops:K` forces exactly K rounds with the stop head ignored
  (`tool_h1.py` docstring line 21 and `run()` lines 97-101 at e070556ce5). So `loops:0` is zero rounds for B3 too, the same test as G1's;
  the stop's "at least 1 round" applies only to the model's own runs. B3-2 reads it this way.
- **B01-15, the Gemma adapter's size (shown, my count):** the adapter is a layer norm and a 768-to-d linear map (`ledger.py` lines 30-45 at
  e070556ce5): 1,536 + 768 x d + d = 198,400 at width 256, 395,264 at 512 (under 0.1% of the whole). It is counted in every trained size this spec reports (sec. 2), and the source of truth now
  counts it too (FINISHED sec. 1: "102.1M trained, which includes the Gemma adapter and the letter window").
- **B01-11, which plain model is the yardstick (open, for Ben):** Ben's bar (10:16 AM ET 10-08) says "more than the plain model" and
  does not name one. This spec picked the plain step model (same rows, same answers) by default; the plain LLM recipe gained more in 8a
  (+15.8 against +3.8 from 3M to 10M on the letter reader) but starts 26 points lower. The marks stay sealed as written. The 8a LLM
  numbers stay reported beside them, and the roadmap lists the choice for Ben (whole-model roadmap, "Latest, Fri Oct 9").

## 22. Addendum Q (2026-10-10, 8:30 AM ET): 3M seed 401 result, 10M speed, and seed 401 starts beside seed 400

- **3M s401 is done** (shown, `claude/8a-g-pc-results` commit d17716d8ea, `results/8a-g/pc/8aG1e-pc/8aG1e-3M-s401/`). G-B2: pooled-5 73.68
  (4,450/6,040), chain-5 100.0, thinker-off (loops:0) in_dist 0.0, 0.41 updates/s, 16.3 h. G-PT: 68.01 (4,108/6,040), chain-5 97.2,
  2.96 updates/s, 2.3 h. The 3M gap B2 - PT is +5.67 here and +5.89 on s400. Still no readout: G1 is about the 3M -> 10M gains.
  The slow s401 B2 matches its peak reserved memory of 16,220 MiB (the whole card) against 11,750 on s400, with the same peak allocated
  (2,847 vs 2,851 MiB): its memory cache grew into Windows shared memory (shown from RESULT.json; the cause of the growth is suggested).
- **10M is slower than planned, and not from a spill** (shown, PC read 8:22 AM ET). 10M s400 started 10:55 PM ET 10-09. Its B2 arm
  (accumulation 16, so 16 rows per pass) was at update 4,500 after 28,048 s: 6.24 s per update. It is the only compute process on the card:
  5,398 MiB dedicated, 82 MiB shared; whole card 6,178 MiB dedicated and 179 MiB shared of 16,303. Over 15 one-second samples the GPU was
  14-41% busy at 75-83 W of 250 W. Suggested cause: passes of 16 rows leave the GPU idle most of the time. Alone, s400 B2 ends about
  4:30 PM ET Sun 10-11 and the gate about Wed 10-14 (suggested). The old "late Sat 10-10" ETA is withdrawn.
- **Change (one; Ben chose "Share the GPU" on a card, 8:25 AM ET 10-10):** 10M s401 starts now on the same GPU, beside s400, with the same
  queue file and settings (`8aG1s401-pc.txt`, B2=16, PT=8). Each seed still trains on one machine. `results/8a-g/pc-job-cards/g1_share_watch.ps1`
  starts it and watches. It stops the s401 training processes (not s400, not the runner) if (1) the G1 training processes' shared GPU memory
  passes 1 GB on 3 checks in a row, or (2) any 500-update stretch of s400 B2 that starts after s401 began takes more than 5,000 s (1.6x its
  3,121 s alone; below that, the two runs together do at least 1.25x the work of one). Then `q8aG1s401_wait.ps1`, still waiting, reruns s401
  after s400 as before. Expected gain if it holds: about a day off the gate (suggested). Costs: addendum I's futility skip no longer saves GPU
  time, and s400 ends up to 1.6x later. Running side by side changes no numbers in either run; only updates/s and wall time differ, and those
  are not marks. The waiter will still run the futility check and relaunch the s401 queue after both end; with s401's RESULT.json present the
  runner skips it, so a "skipped" or "started" line there after this point means nothing.
- **Measured (shown, PC read 10:34 AM ET 10-10):** s401 started 8:29 AM ET. s400 B2 took 3,049 s for updates 5,000-5,500 alone and 3,210 s
  for 6,000-6,500 shared (+3%); s401 B2 took 3,230 and 3,220 s for its first two stretches. So the two runs together do about 1.9x the work
  of one. GPU 81% busy, 11.9 GB used, shared memory 164 MiB; no stop rule tripped. New gate ETA about Mon 10-12 midday ET (suggested; the
  10M plain arm's speed is not measured yet).
- Marks, arms and readout unchanged.

## 23. Addendum R (2026-10-10, 9:15 PM ET): post-G1 chain v3 (group 2 slot, all-steps controls)

- **Why:** Ben's standing rule (8:50 PM ET 10-10): never ask him for an OK; choose the sensible default and do it. Ben's "Option a" (8:23 AM ET 10-10)
  picked big-run PLAN.md's option A for group 2 (g2c3s, then B3 group 2 at 3M seed 400, after B3 group 1 s400 and before the 10M and 30M
  controls). The big-run thread's addendum 10-10 9:00 PM ET replaces g2c10 and c30 with all-steps controls g2c10s and c30s (arm PTS under
  `caps_b3s.json`). Both need a waiter change, and this thread owns the waiter, so one change (v3) carries both.
- **Order in v3 (`results/8a-g/pc-job-cards/after-g1/q8aPost3_wait.ps1`):** GX s400 (skipped if it already has an ok RESULT.json: the
  experts thread started it beside G1 at 8:50 PM ET 10-10 with its own watcher; if that watcher stops it, its folder is renamed aside and v3
  runs it here) -> fc100 -> g2c3 -> B3 group 1 3M s400 + b3_readout -> **g2c3s -> B3 group 2 3M s400** -> [GX s401 if alive] ->
  [g2c3 s401 + B3 group 1 s401 if alive] -> **g2c10s -> c30s** (c30s may still run earlier in the gap while B3 waits for its code).
- **Code:** the group 2 jobs run from a new folder `src-b3g2` = `custom_io` of `claude/learner-new-g2` at 1acfde9a73 (its `custom_io` is
  identical to 9dbcbb579c, the commit the local session tested). caps.py 32862ae2...ea03e, caps_b3s.json 8cbea48d...cbf31, caps_b3g2.json
  ee551d3a...7ed4 (shown, computed from the commit). Queue files: `8aG2C3S-pc.txt` and `8aB3G2s400-pc.txt` from that branch; new
  `8aG2C10S-pc.txt` (10M, accum PTS=32 as g2c10's PT=32) and `8aC30S-pc.txt` (30M, accum PTS=64 as c30's PT=64), same pool and steps as
  the controls they replace. CPU check at 1acfde9a73 (shown, cloud CPU): all four queues parse; PTS passes the size bands at 3M
  (3,459,328 vs B2 3,500,881), 10M (10,567,168 vs 10,452,505) and 30M (28,841,088 vs 28,934,585), before the caps' position-table growth.
- **Install (`upgrade_post_g1_v3.ps1`):** only while v2 still waits for G1; unpacks src-b3g2 and checks the three hashes, puts the two caps
  files in `WORK\b3-inputs`, reruns the CPU check on the PC, writes `src-b3g2\G2-SETUP-OK.txt`, then stops v2 by PID and starts v3. Any
  failure stops before the waiter is touched. A missing G2-SETUP-OK.txt later makes v3 skip each group 2 job with a NEEDS ATTENTION line.
- **Untested:** the speed of every group 2 job on the PC; the 10M and 30M accumulations are the old cautious guesses, and G1 showed that
  16-row passes leave the GPU mostly idle at 10M (addendum Q), so fc100's memory readings should reset them before g2c10s runs (suggested).
- **Installed 8:59 PM ET 10-10** (v2 pid 2760 stopped, v3 pid 8764; CPU check ok on the PC). **Revision v3b (9:10 PM ET), swapped in by
  `swap_v3b.ps1` while v3 still waits:** (1) before any launch, a job folder whose job-level RESULT.json is not ok is renamed aside
  (`<job>.failed-<stamp>`, never deleted), because local_runner skips any job with a RESULT.json; the experts thread's GX run beside G1
  ended arm_failed at 8:53 PM ET. (2) The architecture thread's sealed rule: if group 1 s400 is proved wrong on B3-1 (below +1.0), B3-2 or
  B3-3 (read from `WORK\b3g1-s400-readout.json`), group 2 and g2c3s wait for the bisect; they move to the end of the chain and run there only
  on `WORK\G2-GO.txt` (`G2-SKIP.txt` drops them). The rest of the chain does not wait.
- Marks unchanged (they are the big-run thread's, in PLAN.md).

## 24. Addendum S (2026-10-11, 8:50 AM ET): post-G1 chain v3c (no GX, four 100M shapes, inserted jobs)

- **GX is skipped on the PC.** GX stage 1 ran on two rented 5090s (Ben's yes, 10:24 PM ET 10-10) and lost on both seeds (GX-3M minus
  the same-box G-B2 3M: -1.62 and -1.19; experts thread, commit 1457feaf57). Ben dropped the deep experts run at 8:11 AM ET 10-11 ("you
  don't have to do that. But I do want deep layers in the model at some point"; to the experts thread: "add as many layers as possible.
  don't worry about the experts"). `WORK\GX-ON-MAC.txt` is on the PC (checked 4:50 AM ET 10-11), so the waiter skips GX s400 and s401.
- **fc100 measures four dense ~100M shapes** (FINISHED-MODEL-2026-10-09.md item 10, rule taken 8:20 AM ET 10-11 by the architecture
  thread). Part 1 (queue `8aFC`, src-b3) now only builds the B3 3M long-chunk pool, as before, so every later B3 job reuses the same pool;
  its three ledger 21 x 512 runs are dropped. Part 2 (new queue `8aFC2`, src-b3g2) writes the B3G2 caps beside the pool (a `--maxh 1e-9`
  B3G2 job, nothing trains), then runs 20 updates (256 rows, no eval) of model `b3g2` at four shapes, 8 heads each: 21 x 512, 30 x 432,
  37 x 384 and 54 x 320, each at accumulation 64 (4 rows per pass) and 256 (1 row per pass). Config = `configs.b3_cfg('100M', group 2)`
  under caps_b3g2 (n_loops 12) with blocks and width changed; training draws 4, 8, 16 or 32 rounds per batch, so 20 updates reach the
  32-round cap with probability about 99.7%. Trained counts (shown, cloud CPU at 1acfde9a73): 102,641,692; 102,972,181; 99,765,806;
  100,267,567. The eight train lines parse with train.py's own argument parser (shown). Peak memory and speed on the PC: untested.
- **Inserted jobs.** The 10M depth pair (8 x 256 against about 14 x 192, group 2, seed 400; config from the architecture thread after
  group 2's 3M readout, marks sealed by the big-run thread) cannot be written yet. Instead of another waiter swap mid-chain, v3c runs any
  `WORK\insert\<order>-<name>.txt` ("queue: <Q>", "src: src-b3g2" or "src-b3", optional "card:") alone, at check points after group 2 at
  3M, before g2c10s, before c30s and at the end, then renames the file `.done-<stamp>`. The queue file must already be in that src.
- **Order now:** fc100 part 1 -> fc100 part 2 -> g2c3 -> B3 group 1 3M s400 -> [group 2 hold rule] g2c3s -> B3 group 2 3M s400 ->
  [inserted jobs] -> [g2c3 s401 + B3 s401 if alive] -> [inserted] -> g2c10s -> [inserted] -> c30s -> [inserted].
- **Install (`swap_v3c.ps1`):** only while v3b still waits for G1; parse check of the new waiter, `fc2check.py` on the PC's CPU (queue
  parses, eight configs at 95-106M trained), then copies the queues (the old src-b3 `8aFC-pc.txt` kept as `.v3b-<stamp>`) and the card
  templates, makes `WORK\insert`, stops v3b by PID and starts v3c.

## 25. Addendum T (2026-10-11, 10:00 AM ET): fc100 part 3, answer speed (waiter v3d)

- **Why.** Ben, 9:17 AM ET 10-11: "How fast does the model do inference though?" Nothing on the PC has timed answering yet; fc100 part 2
  times training updates only. The coordinator's default (no OK needed): time answering for the four ~100M shapes when fc100 runs.
- **What.** `infer_speed.py` runs right after fc100 part 2, alone on the GPU, from src-b3g2. For each of the four shapes (21 x 512,
  30 x 432, 37 x 384, 54 x 320) a freshly started model (seed 400, bf16 autocast as in training's eval, the frozen EmbeddingGemma 2 reader
  included) answers dev in_dist questions with exactly 12 or 32 thinking rounds (`loops:K`) at batch 1 (16 questions), 16 (64) and 128
  (256), one warmup batch on other rows per cell, at most 30 s per cell and 60 minutes in all. Output `WORK\fc100-infer.json`: questions
  per second, seconds per question, peak memory, writer steps.
- **Untrained weights, two writer modes.** The writer of an untrained model rarely writes its end mark, so each cell is timed twice:
  *quiet* (one writer step per round, as a trained model on a round without a calculator call, and an answer of at most max_ans + 1 steps)
  and *busy* (the writer runs to its cap WCAP every round and for the answer: the slow side). The real model sits between them, near
  quiet when it makes few calls; `ms_per_writer_step` turns a call count into time. Thinking time itself does not depend on the weights.
- **Not measured:** the learned stop (meaningless untrained), a bf16 weight copy, batching tricks such as a key-value cache in the writer.
  So the numbers are a floor for what the finished model can do, not a ceiling.
- **Checked (shown, cloud CPU at 1acfde9a73, tiny width):** the script runs end to end, quiet writes 1 step per round and 13 answer steps
  under caps max_ans 12, busy writes 96 (WCAP), the time caps and the per-step cost work. GPU numbers: untested until it runs.
- **Install (`swap_v3d.ps1`):** only while v3c still waits for G1; parse check, `infer_speed.py --selftest` on the PC's CPU, copies the
  script and the fc100v2 / fc100v3 card templates, stops v3c by PID and starts v3d. The waiter stops the timing after 120 minutes if it
  hangs; a failure is logged and the chain goes on to g2c3.

## 26. Addendum U (2026-10-11, 10:35 AM ET): inserted jobs from new code (waiter v3e, staged, not installed)

- **Status (10:40 AM ET):** not installed. The Mac session would not run `swap_v3e.ps1` without Ben's word in its own chat, and the
  request was withdrawn rather than asking Ben. The PC keeps waiter v3d (c06efc3f55). Until v3e is installed, inserted jobs take only
  src-b3g2 / src-b3, and `WORK\insert\README.txt` will be refused and renamed at the first check point (a harmless NEEDS ATTENTION line).
  A creative/sleep job on new code can instead run in a slot held with `WORK\STOP` (the chain waits before its next launch), or v3e can
  be swapped in by hand between two jobs.

- **Why.** The architecture thread (10:32 AM ET 10-11): Ben made creative mode and sleep core parts of run-1. The PC will later need
  CB-2 (a creative/sleep test on the 10M group 2 seed-400 checkpoint), maybe CB-1 (on the 3M group 2 checkpoint), and the 100M
  day-and-night phase. Their code does not exist yet and will not live in src-b3g2 (pinned) or src-b3. v3d's inserted jobs only took
  those two folders, and a waiter swap is easy only while it still waits for G1 (about Mon midday ET).
- **What v3e changes (inserted jobs only).** A `WORK\insert\<order>-<name>.txt` may name any `src-<name>` folder in custom-io with
  `caps: <SHA-256 of its caps.py>` (Launch checks it, as for the chain's own queues), or `cmd: <file>.cmd` for a plain script in
  custom-io that keeps its job in the foreground; the chain waits for it to exit and logs NEEDS ATTENTION every `hours:` (default 48)
  while it runs, never stopping it. `README.txt` in that folder is no longer taken for a job (v3c/v3d would have refused it and
  renamed it at the first check point). Cards of inserted jobs now move to `pc-jobs\done` when the next card is installed.
- **Checked (shown):** both waiters parse under PowerShell 7.4 (cloud); a mocked run of `RunInserts` over nine insert files (good queue,
  new src with and without caps, cmd, bad cmd path, cmd mixed with queue, bad src, missing keys, README) did what is written above;
  a mocked `InferStep` wrote the expected cmd file and log lines. Windows PowerShell 5.1 on the PC: parse-checked by `swap_v3e.ps1`.
- **Checkpoints kept.** local_runner never deletes `checkpoint.pt`; the group 2 checkpoints CB-1/CB-2 need will be at
  `WORK\results\8aB3G2s400-pc\8aB3G2s400-3M-s400\B3G2\checkpoint.pt` and `WORK\results\8aB3G2-10M-pc\8aB3G2-10M-s400\B3G2\checkpoint.pt`.

## 27. Addendum V (2026-10-11, 3:50 PM ET): long_dev overlap in the old web slices; the post-G1 chain keeps them

- **Finding (data pool thread, 3:34 PM ET 10-11, commit 4976ed3788):** the new 600M pool's 13-gram gate against the held-out long-row
  test (`big-run/long-dev/long_dev.jsonl`, used only by B3-5) removed 6 / 20 / 63 documents from rung3 / rung10 / rung30, so the old
  8a slices (web_slices_8a, which G1 and the whole post-G1 chain use) contain them.
- **Which long_dev rows (shown, here):** the same overlap rule (data_pool/overlap13.py) over the old slices finds the same 6 / 20 / 63
  documents. They touch 12 / 21 / 50 of the 1,360 long_dev rows, all of them padded rows (280-2,000 letters); no unpadded row is touched,
  so the shared text is distractor padding, never a question or an answer. List and script: `results/8a-g/long-dev-overlap/`.
- **Decision (default, no OK needed):** the post-G1 chain stays on the old slices. Every comparison in it pairs runs on the same pool,
  its controls must match G1 and each other, and the PC's data step (`get_data.py` at the pinned code) only accepts the web_slices_8a
  manifest. G1's numbers are unaffected (G1 never scores long_dev). B3-5 is reported twice: on all 1,360 rows and on the 1,310 rows the
  rung30 list leaves (the conservative list for every rung). New ladders and run-1 use the new 600M files.

## 28. Addendum W (2026-10-11, 4:45 PM ET): new fc100 shape list and new code for the post-G1 chain (staged)

- **Why.** Ben's rules of 4:06-4:17 PM ET 10-11 (project chat; recorded by the architecture thread as FINISHED items 16-18): calculator
  replies are read by the reader (Gemma + letter window), the talker gets no pointer or copy, no converter plug, agent turns. The
  architecture thread (4:25-4:38 PM ET) asked: (1) B3 group 1 3M s400 and B3G2 3M s400 run on new commits (group 1 = ca7e1d1b88 under
  review, parent 8fce7247a8; group 2 later tonight), caps, data and queue lines unchanged; (2) the 10M S runs and the depth twin D are
  held (they move to the agent model AT; AT-1 at 3M joins after B3G2 when its queue arrives); (3) fc100 part 2 measures five 512-wide
  shapes instead of the old four.
- **fc100 part 2 queue (staged in the repo, not yet on the PC):** 21, 26, 30, 34 and 37 layers, d 512, 8 heads, mlp 4.8 (the settled
  21 x 512) / 3.10449 / 2.15723 / 1.43066 / 0.98926, the architecture thread's exact list (4:41 PM ET,
  `/mnt/project-files/architecture/fc100-512/fc100-512-shapes.json`); trained counts with today's Gemma plug on (shown, `fc2check.py`
  at 1acfde9a73, equal to that file): 102,641,692; 102,630,897; 102,655,471; 102,641,095; 102,638,513. (A first staged version
  matched 102.63M without the plug, about 0.4% bigger with it; replaced.) Accumulation 64 then 256, 20
  updates each, as before. Same rule: the deepest shape that fits 16 GB at <= 1.25 x the step time of 21 x 512.
- **Install plan (no waiter swap):** one Mac install before G1 ends: keep src-b3r and src-b3g2 renamed, unpack the new commits into the
  same paths, re-check caps.py and the caps json hashes, run the CPU tests the architecture thread names (group 1: test_reader_rule,
  test_b3, test_b3_run, test_g8a), copy the new 8aFC2 queue and run `fc2check.py`, rewrite the SETUP-OK files.
- **Blocker:** since 10:36 AM ET 10-11 the Mac session will not run BensPC scripts sent by other threads without Ben's word in its own
  chat. Without the install, the old list and the old code run after G1.

## 29. Addendum X (2026-10-11, 5:20 PM ET): one install script for the reader-rule code (`install_rr.ps1`, staged)

- **What it installs** (whatever its folder holds, so it can run once with everything or once per piece): `b3r.zip` (custom_io of
  the group 1 reader-rule commit) into src-b3r; `g2.zip` (the group 2 commit) into src-b3g2; the five-shape `8aFC2-pc.txt` of
  addendum W with `infer_speed.py` (any number of shapes) and the fc100v2 card; and, last, waiter v3e (addendum U) through
  `swap_v3e.ps1`. The two commit SHAs and the hashes of the files they change are written into the script when the architecture
  thread sends them; with `TBD` it refuses a zip.
- **Order and safety.** Only while the waiter still waits for G1 (checked at the start and again just before the swap). Each zip is
  unpacked beside the live folder as `<name>.new-<stamp>` and checked there: caps.py as pinned (src-b3r: the hash on line 1 of the
  live B3R-SETUP-OK.txt; src-b3g2: the waiter's 32862AE2...), the caps json files, the commit's changed files; the chain's queue
  files (the new commit's own copy wins, a missing one comes from the live folder); CPU checks with the GPU hidden: group 1 =
  `b3_capcheck` (cap 32), `test_g8a`, `test_b3_run` (the checks that already passed on the PC) plus the reader-rule test the
  architecture thread names; group 2 = `g2check`, `fc2check` on the 8aFC2 list it will run, `infer_speed --selftest`, plus that
  test. Then the live folder is renamed `<name>.before-rr-<stamp>` (kept) and the new one takes its name, with its SETUP-OK file
  (line 1 still "caps.py <hash>", plus "commit <sha>", so a rerun skips it). A failed check renames the new folder `.failed-<stamp>`
  and changes nothing live. The long CPU suites (`test_b3`, `test_b3g2`: over 10 minutes each) run here in the cloud on the exact
  commits before the package is sent, not beside G1.
- **Tested (shown, cloud, pwsh 7.4.6 on a simulated PC tree; the current two commits stand in for the new ones; real python checks,
  only the process list mocked):** parse check 0 errors. Full install: every check passed (b3_capcheck 32, test_g8a, test_b3_run ALL
  OK, g2check, fc2check 10 runs, infer_speed selftest), both folders swapped, old ones kept as `.before-rr-<stamp>`, about 5 minutes.
  Rerun: both commits "already installed", only the list refreshed. After "gate G1 has ended": refused, nothing changed. A wrong
  pinned file hash in g2.zip: refused after group 1's checks; both new folders renamed `.failed-<stamp>`, live folders untouched.
  List only (no zips): checked on the live code, 8aFC2 and infer_speed.py replaced with the old copies kept. Not simulated: the
  v3e step (it runs `swap_v3e.ps1`, tested on its own for addendum U).
- **Group 1 filled in (7:30 PM ET).** The architecture thread's final group 1 commit is ca7e1d1b88 (parent 8fce7247a8, the PC's
  code; two Opus reviews, no blocking findings; on claude/project-thread-qtxfp4 through the tree-unchanged merge 77c0a6a9c1). It changes
  models/{eg,ledger,tool,b3}.py and adds tests/test_reader_rule.py; no new parameters (3M stays 4,041,685). install_rr.ps1 now pins the
  SHA-256 of those five files and runs `test_reader_rule` first among group 1's CPU tests. Shown in the cloud on the exact commit:
  test_reader_rule ALL OK (12 s), test_g8a ok, test_b3_run ALL OK. Simulated install of group 1 alone: every check passed, src-b3r
  swapped, the old code kept; with the parent commit in b3r.zip instead it refused on models\ledger.py and changed nothing live.
  Group 2 (`$SHAG2`) still waits for the talker thread's G2f head.

## 30. Addendum Y (2026-10-11, 6:05 PM ET): the talker's first run (G2f) moves before B3 group 1 (waiter v3e, staged)

- **Why.** Ben, 5:51 PM ET 10-11 (project chat): "can you build the talker". The architecture thread (5:58 PM ET) said G2f (B3 group 2
  with its fixes 1, 2 and 2b: the talker writes answers and calls from the thinker's state only) is the talker's first PC run, the
  agent model's AT-1 gate waits on G2f and not on group 1, and group 1 keeps the old copying talker. It suggested g2c3s then G2f
  before B3 group 1, leaving the order to this thread. Taken (default, no OK needed).
- **Rule in v3e.** After fc100 parts 1-3: if src-b3g2's G2-SETUP-OK.txt says "reader rules" (only `install_rr.ps1` writes that), run
  g2c3s, then B3 group 2 3M s400 (= G2f), the inserted-jobs check point, then g2c3 and B3 group 1 3M s400 with its readout; the
  option A hold (group 2 waits when group 1 s400 is proved wrong on B3-1, B3-2 or B3-3) no longer applies, because group 2 has
  already run. Without the reader-rule code, v3d's option A order and its hold stay exactly as they were. The rest (seed-401 runs,
  g2c10s, c30s, inserts) is unchanged. `swap_v3e.ps1` now also checks for this rule before swapping.
- **Tested (shown, cloud, simulated PC, pwsh 7.4.6, real caps hashes, mocked processes):** with the reader-rule marker: 8aFC, 8aFC2,
  timer, 8aG2C3S, 8aB3G2s400, 8aG2C3, 8aB3G1s400 + readout, seed-401 pair, 8aG2C10S, 8aC30S. Without it: v3d's order. Without it and
  group 1 proved wrong on B3-2: group 2 held to the end and run on WORK\G2-GO.txt.
- **Timing (suggested, not measured):** G1 ends about Monday midday ET; fc100 parts 1-3 and g2c3s come first, so G2f starts Monday
  evening at the earliest and its 3M result lands about Tuesday, as the architecture thread told Ben.

## 31. Addendum Z (2026-10-11, 8:00 PM ET): no plug at 30M and 100M in the post-G1 chain (staged)

- **Why.** Ben, 4:12 PM ET 10-11: "can you remove the converter plug and just have our model match gemma's". The architecture thread
  built it (7:20 PM ET, claude/project-thread-qtxfp4 at 77c0a6a9c1, merged into B3 group 2 with Ben's rules 1 and 2): at 30M and
  100M the model is 512 wide and reads Gemma's own 512 numbers (the state after Gemma's final norm, before its 512 -> 768
  projection) through a zero-start LayerNorm(512); 3M and 10M keep the plug. It asked for c30s to be re-staged with it.
- **Defaults taken (no OK needed).** (1) c30s (`8aC30S-noplug-pc.txt`): the same job with `--noplug`; at that commit under
  caps_b3s.json its PTS arm is 9 layers, hidden 2099, 512 wide, 30,003,659 trained (B2 30,000,092), lr 5e-4 (the width rule,
  every arm at this rung). (2) fc100 part 2 (`8aFC2-noplug-pc.txt`, card `fc100v2-noplug.md`): the five depths measured on the
  real no-plug 100M front, configs from `configs.b3_cfg('100M', {"eg_embed": true, "noplug": true, "blocks": N}, group 2)`, the
  architecture thread's counts exactly: 21 (mlp 4.83496) 102,634,902; 26 (3.13379) 102,636,407; 30 (2.18066) 102,630,231;
  34 (1.45215) 102,630,205; 37 (1.00879) 102,623,523. Every other key of each config is unchanged. (3) The proof the
  architecture thread asked for before the first no-plug run (`eg check ... pre`) runs inside install_rr.ps1 on the CPU in fp32
  (the gated number; G1 keeps the GPU); the bf16 GPU number comes from the first no-plug run itself.
- **When.** Only with a group 2 commit that has the no-plug code (it contains a10b6eacf1). Then the package carries
  8aFC2-noplug-pc.txt as 8aFC2-pc.txt, fc100v2-noplug.md as fc100v2.md, and 8aC30S-noplug-pc.txt as 8aC30S-pc.txt. Without it,
  both stay plugged and nothing here is sent.
- **Install changes.** install_rr.ps1 installs an `8aC30S-pc.txt` from its folder into the new src-b3g2 (only with g2.zip; on a
  rerun it must equal the live one). A list or c30s queue that will be live and reads Gemma's own numbers ('"eg_pre": true' or
  `--noplug`) is gated on `python -m custom_io.models.eg check cpu pre` with CUSTOM_IO_EG2 = C:\Users\benja\eg2 ("pre_ok": true:
  512 wide and Gemma's own projection of it equals its 768 output within 1e-4). g2check.py reads c30s's queue: with `--noplug` it
  needs job.py's `--noplug` and checks the 30M PTS config under caps_b3s.json (eg_pre, width 512).
  It now also builds B3 group 2 at 3M (the G2f run) under caps_b3g2.json and prints its count, so a group 2 commit whose 3M model
  fails its own size check is refused at install. `infer_speed.py --selftest` (no Gemma, tiny width) drops the no-plug keys from
  the shape it borrows; the real timing run keeps them.
- **Architecture's answer (7:45 PM ET):** all three defaults right. Its group 2 work is final at 73bc563ec0 (rule 1, answers from
  thoughts, the answer asked after the last reply is read, the per-row settle fix, and the no-plug merge); the talker thread merges
  that into G2f, so the install SHA still comes from them (their 3M count about 4,023,302, g2c3 4,022,440).
- **Tested (shown, cloud, pwsh 7.4.6 on a simulated PC tree; group 1 = ca7e1d1b88, group 2 stand-in = 73bc563ec0; only the process
  list and the Gemma check are mocked, no Gemma here):** both lists regenerate identically at 77c0a6a9c1 and 73bc563ec0; fc2check
  prints the five counts above; g2check prints "c30s no plug: PTS 9 layers, hidden 2099 ... lr 0.0005" and "B3G2 3M: 4,081,871" at
  73bc563ec0, and still passes on the old code with the plugged queue. Full install: every check passed, both folders swapped, the
  no-plug 8aFC2 and c30s queues live, marker "eg check cpu pre ok (no plug)". The first try failed on the answer-timer selftest
  (fixed as above) and changed nothing live. Old group 2 code with the no-plug files: refused at g2check ("this job.py has no
  --noplug"). Gemma proof failing: refused after every other check; both new folders renamed `.failed-<stamp>`, live untouched.

## 32. Addendum AA (2026-10-11, 9:35 PM ET, before any run): does size help more when practice rows grow with it? (test DS)

- **Why.** Ben, 9:16 PM ET 10-11, on G1's first 10M number (G-B2 seed 400: 73.01 at 3M -> 74.65 at 10M, +1.64): "that's not
  scaling to the degree that I wante dit to". Beating the plain model's gain is not enough; size has to clearly lift our score.
- **What the 3M seed 400 results show (shown, `claude/8a-g-pc-results` 532ebdc, G-B2 RESULT.json):** 2,560 of the 6,040 pooled-5
  rows are in families the 3M model already gets 40/40; of the 1,630 rows it misses, 836 are in the `variant` file (known skills,
  new wordings; 484/1,320 = 36.7%). 3M and 10M train on the same pool (`p10-rung30-s400-a64`: 1,418,702 rows, 60.0M pieces, of
  which 501,456 skills rows), 24,000 updates of 256 rows, so 4.33 passes; 259.9M pieces seen at both sizes.
- **Explanations (suggested, untested):** (1) the score left to gain sits mostly in new wordings, which the same rows cannot
  teach at any size; (2) the 10M has 3x the parameters and no more rows (6 pool pieces per parameter against 17 at 3M);
  (3) the 10M was grown in depth only (2 -> 8 blocks, width 256, the 3M's lr), and 8a's probe hinted width grows better
  (+1.0 vs +0.2, two seeds). This test changes (2) only.
- **The one change.** G-B2, seed 400, at 3M and at 10M, trained on the 30M rung's pool (`p30-rung30-s400-a64`: own_rung 30, all
  72M own pieces, 190M pieces, nested: every row of the 10M pool is in it) instead of the 10M pool. Everything else as G1: code
  612f5c5b01 + the caps fix, caps_g.json, shapes, lr, accumulation (B2 3M 4, 10M 16), and **24,000 updates of 256 rows** (the
  same compute; each row is drawn about 1.4 times instead of 4.3). The job needs a pool-rung switch (G1's job.py builds the pool
  of the model's own rung); that patch goes in a new source folder, G1's src-8ag is not touched.
- **Marks (fixed now, seed 400; d_big = 10M - 3M pooled-5, both on the 30M pool; G1's d = +1.64):**
  - **Pass:** d_big >= +3.3 (double G1's gain), with chain-5 >= 99 at both sizes.
  - **Proved wrong** (for "more practice rows let size help"): d_big < +2.0. Then the next fix is new kinds of practice
    (wordings, skills), not more rows of the same kinds.
  - **Between:** run the seed 401 pair before deciding.
  - **Reported:** 3M on the 30M pool minus G1's 3M (what more rows give at 3M); per-file gains, the `variant` file above all;
    thinker-off scores; hours.
- **Order on the PC (default taken, no OK needed):** the 3M run first in the post-G1 chain (about 6.5 h), the 10M run (about
  40 h at G1's 6.24 s per update) after fc100 and the talker's first run (G2f). Not part of G1's readout.

## 33. Addendum AB (2026-10-11, 10:05 PM ET, before any run): test DS dropped; test WIDE instead (outside opinions)

- **Asked** (Ben, 9:17 PM ET: "if you come back inconclusive, ask fable 5.1 what to do in the api call"; 9:19 PM ET: "use this", the
  Managed Agents Deep researcher). Brief `reviews/fable-scaling-2026-10-11.md` (Fable 5.1, xhigh, API: 4.5 min, about $1.02);
  `reviews/deep-research-scaling-2026-10-11.md` (Managed Agents deep researcher, Opus 5.5, web: 8 min, $4.41 list). Answers:
  `reviews/fable-scaling-answer-2026-10-11.md`, `reviews/deep-research-scaling-answer-2026-10-11.md` (mirrored under
  /mnt/project-files/whole-model-roadmap/reviews/).
- **Both:** more rows of the same kinds will not make size help at 10M; grow width, not depth, first; the autoregressive writer
  (B3 group 2, G2f) is the main fix. Fable ranks first: "the thinker has nothing left to learn from its signal, and the answer
  path can't express the remaining answers". It also points out that `frame` and `vocab` (86.6, 89.4) equal `in_dist` (86.0), so
  B2 generalises across wordings; my "same wordings" guess in addendum AA is contradicted.
- **Free diagnostic Fable asked for, done from the 3M s400 RESULT.json (shown):** on the 400-row program check, teacher-forced
  and free-run op and program accuracy are 100%; the program loss is 0 at the end of training. Of the nine families where the
  plain model beats B2, eight have **0% program coverage** (no calculator program at all; compare_numbers is the exception), and
  their answers go through the WORD pointer or the parallel GEN head: table_lookup GEN 67.5% / WORD 31.0%, rule_apply 57.5 / 40.5,
  fewshot_number_rule GEN 96.0, passage_qa WORD 66.0, digits_parity GEN 61.5, seq_next GEN 100, kin_chain 50 / 50, list_stats NUM
  70.5 (prog 37). So the misses sit on B2's answer heads, not on its programs (Fable's "right program, wrong pointer" branch: G2f's
  writer is the right fix).
- **Test DS (addendum AA) is dropped** before any run: its hypothesis is weakened (plain model +3.77 on identical rows; B2 already
  fits its programs), it cannot add unseen structures by construction, and its pass and fail lines are about one paired sd apart.
- **Test WIDE (one change: the shape).** B2 seed 400 at about 10M **by width**: d 448, 7 heads (64 per head, as at 3M), 2 blocks,
  mlp 4.8, reader 2 layers, 12 rounds, eg_embed: the 3M shape with only the width changed; 10,173,509 trained under G1's caps
  (the deep 10M: 10,496,537). lr 1e-3 x 256/448 = 5.71e-4 (the width rule of the 30M rung and of 8a's W probe). G1's code
  (612f5c5b01 + the caps fix) plus one added rung row (`10MW`) in configs.py, in a new folder src-wide; G1's 10M pool
  p10-rung30-s400-a64 (reused, same rows and order), 24,000 updates of 256 rows, accumulation 8. B2 only.
  - **Pass:** pooled-5 >= 76.31 (>= +3.3 over 3M's 73.01) with chain-5 >= 99: depth was the wrong axis; grow width at every rung
    and revisit the 100M shape list (21-37 blocks at 512).
  - **Fail (proves "adding B2 parameters any way helps" wrong):** <= 75.01 (+2.0). Then the answer heads are the only path to
    scaling, and B3 group 2 carries it.
  - **Between:** seed 401 wide.
  - **Reported:** minus the deep 10M (74.65), training loss and its GEN part, per file, the nine B2-losing families, hours.
  - **Cost (untested):** 12-20 h on the PC (Fable's estimate).
- **Order after G1 (default taken):** fc100, g2c3s, **G2f** (B3 group 2 3M s400; Fable's floor: >= 67 = the plain model's level,
  >= 71 = it kept B2's strengths), then **WIDE** (an inserted job, waiter v3e, check point "after group 2 at 3M"), then the rest of
  the chain. A B3 group 2 10M step follows only if G2f clears 67; its shape (wide or deep) is set by WIDE. Its marks get their own
  addendum before it runs.
- **Flagged for Ben, not changed:** both answers warn that the G2f writer reads only the thinker's vectors (no view of the question
  or the tape), which Ben's rule 2 requires. G2f's score is the first evidence.
- **Install (staged 10:30 PM ET):** `results/8a-g/pc-job-cards/wide/` holds `configs.py` (G1's file plus the `10MW` row only,
  sha 4d273a64...), queue `8aWIDE-pc.txt`, `widecheck.py` (CPU, meta device: 10,173,509 trained, 448 wide, 2 blocks, 12 rounds; peak
  0.3 GB), card `wide.template.md` (spill rule accum 8 -> 16 -> 32), and `install_wide.ps1`: copies src-8ag's custom_io to src-wide
  (G1's caps.py, caps_g.json and configs.py hashes checked first; src-8ag is never changed), runs widecheck, then writes
  `WORK\insert\20-wide.txt` (needs waiter v3e). install_rr.ps1 calls it last. **Accumulation 8, not 16 (suggested):** per micro-batch,
  WIDE's activations are about 0.9-1.05x those of the deep 10M at 16 (32 rows x 2 blocks x 448 against 16 x 8 x 256), which ran
  without a spill.

## 34. Addendum AC (2026-10-11, 10:30 PM ET): Ben's PC restart, G1 reruns, and the install with free memory

- **What happened (shown/inferred):** Ben restarted BensPC at about 9:45 PM ET ("I need to restart my pc", then "It's breaking a
  ton"); I missed his question. train.py saves only at the end of a run, so the runs in progress are lost: 10M s400's plain arm (PT;
  its B2 arm finished, 74.65, and is kept) and 10M s401's B2 arm. The waiters and queue runners stopped too. The PC's memory was
  short before the restart (install_rr ran out at 9:20 PM ET); that is a likely cause of the trouble (inferred, not checked).
- **Recovery** (`results/8a-g/pc-job-cards/restart/`, rehearsed in a fake PC tree): `g1recover.ps1` reports what survived and,
  only if nothing of G1 or the chain runs, (1) writes rerun queues for the arms without an ok RESULT.json: **8aG1fR** (s400, PT
  only, accum 8) and **8aG1s401r** (s401, B2 + PT, accum 16 / 8), same settings and seeds as G1, new folders, so the finished B2
  folder is never written to; (2) renames the stale GPU-BUSY.txt and pool locks aside, moves the dead cards to done; (3) restarts the
  post-G1 waiter (still v3d; it reads s401's end through the glob `8aG1s401*`, which 8aG1s401r matches); (4) starts
  `pc_after_restart.ps1` detached: **the install first** (install_rr.ps1: group 1 ca7e1d1b88, group 2 = G2f 74d6e92c75, the no-plug
  lists, waiter v3e, test WIDE), while the memory is free, then G1: s400 at once, s401 beside it only when s400 trains and free
  commit >= s400's python memory + 4 GB and GPU memory used <= 9,000 MiB, else after s400.
- **Addendum I's futility rule** (skip s401 if s400's gain difference <= -1.0) is now read by hand when s400 PT lands: g1_futility.py
  expects both arms in one job folder.
- **install_rr.ps1 changes:** group 2 filled (74d6e92c75: b3g2, writer, b3, eg, ledger, tool, configs, job pinned); CPU tests
  test_reader_rule, test_b3g2_run, test_talk_rounds, test_b3g2 (each under 0.5 GB; test_no_plug, 4.8 GB, left out); a memory guard
  before each CPU step (estimate + 2 GB free to commit, Gemma fp32 4 GB); v3e skipped if it already runs; test WIDE last.
- **Cost:** G1's end moves by about a day (estimate). The order after G1 is unchanged (addendum AB).

## 35. Addendum AD (2026-10-12, 12:15 AM ET, before any G2f or agent-model number): AT-1 goes in right after G2f, gated (staged)

- **Ask:** the Build the talker thread sent the AT-1 queue (`custom_io/queue_local/8aAT-3M-s400-pc.txt` at **6e72a5fae5**, PR #69,
  arm AT = B3AT, the agent-turn model, 4,023,302 trained at 3M; AT-0 passed on 31a078a2ac) to run after G2f seed 400, per the big-run
  PLAN's sealed gate (sixth Addendum 10-11 (3)): **AT-1 runs only if G2f seed 400 is not proved wrong on B3G2-1 to B3G2-3.** It also
  said a G2Q queue (the talker that also reads the question) will follow. The order is this thread's call (PLAN eleventh Addendum (6)).
- **Order (my default, no OK needed):** at the waiter's first insert check point, right after g2c3s and G2f: the gate, then
  **AT-1**, then test WIDE (20-wide.txt), then **G2Q as a side run (30-g2q.txt, when its files arrive)**; then g2c3 and B3 group 1 as
  before. AT-1 goes first because the agent model is the finished design and its 10M date (Oct 31 to mid-November) waits on it.
  G2Q after WIDE either way: if G2f is proved wrong, AT-1 does not run and G2Q starts about half a day later than it could have.
- **Which lines the gate can read there (shown from the waiter's order):** group 1 has not run at that point (G2f moved before it,
  addendum Y), so only the proved-wrong lines that do not need group 1 are read: B3G2-1's "below g2c3s"; B3G2-2's "thinker-off
  (loops:0) above 60% of the full score"; B3G2-3's "calculator off within 10 points of intact". **B3G2-1's "more than 6.0 below
  group 1" and B3G2-2's "chain-5 more than 5 below group 1" are read by hand when group 1 lands**; if either proves G2f wrong then,
  AT-1's result is reported with that flag and the big-run thread decides (its gate wording assumed group 1 first). "Cannot tell"
  (a missing or failed result) counts as not passing: AT-1 does not start and the log says NEEDS ATTENTION.
- **How (files in `results/8a-g/pc-job-cards/agent/`, rehearsed in a fake PC tree, pwsh 7.4.6):** `install_agent.ps1` unpacks
  6e72a5fae5's custom_io as `src-at` (caps.py 4334…62D3, caps_b3g2.json = G2f's, 8 pinned files; b3g2.py, writer.py and b3.py are
  byte for byte G2f's), copies the queue as `8aAT-pc.txt` (job 8aAT-3M-s400, spill names 8aATb, 8aATc), runs `atcheck.py` (queue
  parses; arm AT builds b3at at 4,023,302) and test_b3at_core + test_b3at_run on the CPU with the memory guard, then writes
  `WORK\insert\10-g2fgate.txt` (cmd: g2f_gate.cmd) and `11-at.txt` (queue 8aAT, src-at, card at.template.md). It refuses unless the
  waiter is v3e and has not ended G2f. `g2f_gate.ps1` runs `g2f_gate.py` (standard library) on the newest ok RESULT.json of G2f
  (8aB3G2s400*) and g2c3s (8aG2C3S*); on anything but "not proved wrong" it turns 11-at.txt into `cmd: at_skipped.cmd` (a no-op),
  keeping the original as 11-at.txt.gated-<stamp>. Rehearsed: install, rerun (DONE), waiter past G2f, waiter v3d, a changed file in
  the zip, low memory (each refused with nothing changed but a kept .failed folder), and the gate on pass / proved wrong / missing pair.
- **Needs:** one Mac job (Ben's yes in the Mac chat), sent together with G2Q's install so he types one yes. Not before the recovery
  job (addendum AC) has run, because install_agent needs waiter v3e.

## 36. Addendum AE (2026-10-12, 1:55 AM ET): no G1 reruns; G1 read from what exists; the PC install fixed; Modal

- **Ben, 1:17 AM ET:** "I don't think you should rerun g1, it's not worth it". The two 10M reruns of addendum AC (8aG1fR: s400 PT;
  8aG1s401r: s401 B2 + PT) are dropped. Ben, 1:15 AM ET: "you can use $30/month as of now on the gpus there" (Modal).
- **G1 read from what exists (shown, from the RESULT.json files):** 3M: G-B2 73.01 vs G-PT 67.12 (s400), 73.68 vs 68.01 (s401).
  10M: G-B2 s400 74.65, so d(G-B2) = +1.64 on one seed. The plain 10M arm (s400 stopped at update 16,500 of 24,000 in the restart)
  and both s401 10M arms were never finished. **So mark 1 (Ben's bar: ours gains more from size than the plain model) cannot be
  scored, and G1 ends unscored.** Mark 2 has one seed and no interval; mark 4 holds on the two-seed screen (3M mean 73.35 >= 72.0).
  Ben's own reading of the one number stands (9:16 PM ET 10-11: "not scaling to the degree that I wanted"). The size question moves
  to test WIDE (addendum AB) and to the writer (G2f): those are the next scaling evidence, not a G1 rerun.
- **What happened on the PC (shown, the Mac's 12:58 AM ET and 1:22 AM ET reports):** the 10:25 PM ET recovery job (addendum AC) ran
  at 12:38 AM ET, before Ben's message. It restarted the waiter (v3d) and started 8aG1fR at 12:41 AM ET. Its install stopped at one
  test in G2f's code: `test_reader_rule.test_r2_call_and_stop_inputs_unchanged_by_the_answer_rule` pins five numbers to the last bit
  (float.hex). On BensPC the three call numbers matched the pin to the bit; the stop head's input sums did not (stop_abs
  0x1.2905bcc9c0e26p+13 vs 0x1.2905bcd29db68p+13, a gap of 1.8e-9 of itself; stop_in a gap of 4.6e-12 of stop_abs). The same commit
  passes the bit pin on the cloud CPU (torch 2.14.1+cpu, 1 and 4 threads; shown here). So it is this CPU's rounding, not a code
  change (inferred from those two facts). Nothing was swapped: the install's checks run before any change, as designed.
- **Fix (rehearsed):** `after-g1/run_tests.py` runs a test module as its own main() does, with that one comparison allowing 1e-7
  relative (call, stop_abs; call_acc and eos_acc exact) and 1e-9 x stop_abs (stop_in), about 50 to 200 times the PC's gaps; the
  rest of that test (finite loss, no copying) and every other test run as written, and the exact numbers are printed (MACHINE
  ROUNDING line). install_rr.ps1 uses it for test_reader_rule only. Checked on the CPU at 74d6e92c75: the exact pin passes, the PC's
  numbers as the pin pass, the pre-G2f pin (a real change: call 129.9 vs 151.4) FAILS. The talker thread owns the test; a tolerance
  in their next commit would make this wrapper unneeded (suggested).
- **Stopping the reruns (rehearsed on a fake PC, pwsh 7.4.6):** `restart/nog1_go.ps1` refuses if the chain is past G1, G1-DONE.txt or
  STOP exists, the waiter is not running once, or a non-G1 queue runner runs. Otherwise it stops the old pc_after_restart.ps1 first
  (else it starts s401 when s400's runner ends), then the 8aG1fR / 8aG1s401r cmd trees and python processes, keeps their logs and
  partial folders, renames the plan aside (so nothing restarts G1), moves the cards to done, renames the killed run's GPU-BUSY.txt and
  pool locks aside, and starts pc_after_restart.ps1: install_rr, then install_agent (AT-1 + G2Q, addendum AD), then
  `WORK\G1-DONE.txt` only after a clean install_rr. The waiter cannot start the old chain in between: without G1-DONE.txt or s401's ok
  RESULT.json it keeps waiting. Scenarios: go, install fails (no G1-DONE), past G1, G1-DONE present, another runner, a process that
  will not stop, no waiter, no NO-G1-RERUN.txt. Sent to the Mac at about 1:50 AM ET under Ben's 1:18 AM ET line in the Mac chat ("yes,
  run the roadmap thread's PC installs and next jobs, and don't ask me again for its jobs"). **The Mac held it (1:39 AM ET), rightly:**
  stopping a running job and the test tolerance are not clearly covered by that line, and Ben's 1:17 AM ET words were not said in the
  Mac chat. It asks Ben there: "stop G1" and whether he accepts the 1e-7 tolerance. Until then 8aG1fR (the plain 10M s400 arm) keeps
  training; if it finishes first, its RESULT.json is kept and G1 seed 400 becomes readable (ours +1.64 against the plain arm's gain).
- **Modal (the $30/month):** G2f stays on the PC: the AT-1 gate reads its RESULT.json there, and a second copy would duplicate it.
  **Test WIDE is offered to Modal** (standalone; nothing waits on it; 12-40 h of PC time otherwise), with a rule fixed before any
  number: probe about 300 updates per GPU type (bf16 needed, so no T4); projected cost = 24,000 x s/update x price + 15%; run only if
  that is <= $20 and the wall time <= 20 h (one Modal call; train.py saves only at the end), with a hard stop at $24; else WIDE stays
  on the PC. A Modal WIDE differs from the PC runs only in the GPU (bf16 summing order; disclosed, as for accumulation). If it runs
  there, `WORK\insert\20-wide.txt` is taken off the PC's list.
- **Order and dates:** unchanged order (addenda AB, AD): fc100 parts 1-3, g2c3s, G2f, the AT-1 gate, AT-1, WIDE (unless on Modal),
  G2Q, g2c3, B3 group 1, the s401 pairs, g2c10s, c30s. It starts about 5 minutes after the install ends, which is about 40 minutes
  after Ben's line in the Mac chat (the morning of 12 Oct, estimate): about a day earlier than addendum AC's estimate, because nothing
  waits for G1's s401 arms.

## 37. Addendum AF (2026-10-12, 8:25 AM ET): G1 seed 400 read; G1 reads Stop (one seed) by addendum I

- **What changed since AE:** the plain 10M s400 rerun (8aG1fR) finished at 4:50 AM ET, before Ben's line in the Mac chat, so it was
  kept (AE). The Mac read the six G1 RESULT.json files read-only at 8:00 AM ET with `results/8a-g/g1-readout/g1s400_read.py`.
  Table, per-family gains and the verbatim PC output: `results/8a-g/g1-readout/G1-S400-READOUT-2026-10-12.md` (mirrored).
- **Shown (pooled-5, 6,040 dev rows):** G-B2 73.01 -> 74.65, **d +1.64**. G-PT 67.12 -> 72.47, **d +5.35**. **Gain difference -3.71.**
  Ours minus plain: +5.89 at 3M, +2.19 at 10M. Chain-5: G-B2 100.0 at 10M (guard holds); G-PT 98.8. At 10M ours trained 42.7 h
  at 0.156 updates/s and the plain model 4.1 h at 1.62 updates/s (about 10x; 2.7x at 3M).
- **Reading by the rules fixed before any 10M result:** addendum I: seed 400's gain difference is at or below -1.0, so 10M s401
  is not run and **the gate reads Stop (one seed)**. This replaces AE's "G1 ends unscored". Section 4's Go (+1.0 on both seeds)
  is ruled out. Section 4's prediction (suggested, written 8 Oct: "the screen stops") held on this seed. Mark 1's interval and the
  "proved wrong" line need more seeds: not claimed. Mark 2: one seed, +1.64. Mark 4 holds (3M mean 73.35). Mark 5 holds. Mark 3
  (thinker-off) not read here.
- **Per family (shown):** ours gained more on 7 of 34 families: digits_parity +16.3, kin_chain +10.0, rule_apply +9.5, passage_qa
  +9.5, verify_claim +6.7, list_stats +2.6, letter_ops +1.0. The plain model's largest leads: arith_bare (+6.2 vs +26.8),
  backward_solve, table_lookup, cipher_map, chain_ops. Rule families: fewshot_number_rule 10.6 -> 10.6 (plain +4.4), seq_next +1.3
  (plain +11.2), order_chain -2.5 (plain +2.5).
- **Catch-up explains part, not all (shown, unweighted family means):** on the 12 families where the plain model sat 10+ points
  behind ours at 3M, the difference is -7.98; on the other 22 it is still -1.41; on the 29 families where ours was below 90 at 3M,
  -2.42. Suggested: the flat rule families fit addendum AB's diagnosis (the misses sit on B2's fixed answer heads), which G2f's
  writer targets. Untested.
- **What changes:** the s401 rerun 8aG1s401r (B2 + PT 10M, training since 4:52 AM ET; about 43 h + 4 h at seed 400's speeds, so
  about 4 AM ET Wednesday) is futile by addendum I as well as dropped by Ben (AE). `nog1_go.ps1` stops it once Ben types his line in
  the Mac chat; nothing else changes. Order unchanged (AB, AD, AE). The size question stays with test WIDE (pass >= 76.31, fail
  <= 75.01; the plain 10M's 72.47 is reported next to it, not a new mark) and with G2f. The big-run thread is told.
