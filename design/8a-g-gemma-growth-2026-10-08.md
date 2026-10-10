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
