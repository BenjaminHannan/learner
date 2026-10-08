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
- Marks, arms and readout unchanged.
