# 8b: why B2 does not grow, and three EmbeddingGemma-input fixes (written 2026-10-08, 10:45 AM ET, before any 8b run)

Scope: the B2 skills model and the 8a size ladder only (spec `design/8a-bigger-is-better-2026-10-07.md` on
`claude/project-thread-yha868`, PR #50). Nothing here is about the card experiments or the village model.
Labels: **shown** = read off a result file or the code; **suggested** = an inference; **untested** = no run yet.
Code read: build branch `claude/project-thread-f1to6a` at 50ee171632 (the commit every 8a run used).

## 0. One correction to the brief

PT is `plain_tf_steps`, the plain causal letter transformer that writes the worked steps (spec section 3). It is not a
pretrained-reader arm (shown, spec lines 49-51). "The plain model" below means the plain LLM arm (`plain_lm`) when it
stands alone, as in Ben's mark.

## 1. Diagnosis: the extra size never reaches the loss

Evidence comes from the 8a results already on `claude/project-thread-yha868` (no new runs). Scripts:
`g8b/analysis/free_ablations.py`, output `g8b/analysis/free_ablations.txt`.

**D1. B2-10M fits its training data no better than B2-3M, from step 1,000 on (shown).** Mean training loss over the
6 seeds, by step (total / GEN part / mode+word part):

| step | B2 3M | B2 10M | PT 3M | PT 10M | LLM 3M | LLM 10M |
|---|---|---|---|---|---|---|
| 1,000 | 2.618 / 1.10 / 0.69 | 2.597 / 1.10 / 0.69 | 1.737 | 1.719 | 1.982 | 1.924 |
| 4,000 | 1.591 / 0.94 / 0.57 | 1.588 / 0.94 / 0.57 | 0.749 | 0.698 | 1.244 | 1.156 |
| 12,000 | 1.380 / 0.89 / 0.48 | 1.369 / 0.88 / 0.47 | 0.475 | 0.442 | 1.133 | 1.030 |
| 24,000 | 1.232 / 0.83 / 0.39 | 1.210 / 0.81 / 0.38 | 0.365 | 0.332 | 1.078 | 0.955 |

PT and LLM at 10M pull below their 3M curves early and the gap widens. B2's two curves lie on top of each other, and so
do the R (reader grown) and W (wider) probes (1.156 and 1.199 at 24k). The program loss is already 0.004 at 3M with 100%
op accuracy. So the 3M thinker already fits the rows its calculator covers. The rest of the loss (GEN 0.82, mode 0.22,
word 0.19) does not move with thinker size, reader depth or width. This rules out "overfits with size", and it makes
"a plain lr or optimizer mismatch" unlikely as the main cause, because 10M is no faster even early on (suggested; a
lower-lr arm would test it, untested).

**D2. The calculator families are saturated; the families with headroom never touch the calculator (shown).** The parser
writes a program for 14 families (41% of dev rows). B2 is at 86.2% there at 3M and gains +0.26. On the other 20 families
(62.2% at 3M, so 38 points of headroom) B2 gains only +0.57 (sd 2.0), while PT gains +3.14 and LLM +11.71 on the same
families (5 paired seeds). So "B2 is near a ceiling" explains only the calculator families.

**D3. On the non-program families the talker, not the thinker, does the work, and the talker does not grow (shown, from
the saved lesion evals).** Pooled-5 per family, mean of 6 seeds, 3M (10M in brackets):

| family | intact | 1 round | 2 rounds | 24 rounds | no word content keys |
|---|---|---|---|---|---|
| copy_word | 80.2 (79.1) | 74.6 (74.5) | 79.7 (78.0) | 79.7 | 5.8 (15.4) |
| group_induct | 76.1 (75.7) | 58.2 (65.6) | 67.2 (73.6) | 75.7 | 7.4 (7.5) |
| prop_eval | 82.4 (81.8) | 67.6 (70.0) | 77.1 (81.4) | 82.4 | 8.5 (17.8) |
| object_track | 67.0 (67.9) | 40.8 (54.3) | 58.8 (64.2) | 67.3 | 2.5 (2.4) |
| rule_apply | 61.2 (63.4) | 15.2 (20.5) | 24.7 (28.7) | 53.9 | 33.3 (35.8) |
| seq_next | 36.8 (38.5) | 0.4 (0.1) | 3.6 (3.4) | 33.4 | 36.8 (38.5) |

The WORD answer is a dot product between one 64-number query from the thinker and per-word keys built from the 2-layer
letter reader. Removing the reader's content from those keys collapses the WORD families. Two rounds already give most of
the score, and 24 rounds give nothing more. The thinker's output reaches an answer only through three narrow, fixed-size
channels: the mode head, a 64-d pointer query, and 36 GEN registers read out in parallel. None of them grows when blocks
are added (code: `ledger.py` `run()` end and `talk()`).

**D4. The rule families have no program to learn (shown).** Their worked steps are labels, not arithmetic:
`seq_next` -> `['rule growing_step', 'next = 47']`, `fewshot_number_rule` -> `['infer pair rule']` or `['rule x*1+14']`,
threshold `rule_apply` -> `['threshold']`. The parser writes no program (coverage 0%), so B2 must compute the number
inside its state and spell it through 36 parallel GEN registers (seq_next is 100% GEN, fewshot 96%). Neural arithmetic
through a parallel, non-autoregressive readout is where B2 is worst (seq_next 37, fewshot 19 vs PT 51, 44 at 10M).

**D5. 62% of every batch is web fill-in, and its loss sits on the GEN/mode floor (shown for the floor, suggested for the
cause).** The GEN part plateaus at about 0.81-0.83 per letter from step 16k on, the same for 3M, 10M, R and W. One
suggested cause is that a parallel per-letter readout can only learn per-letter marginals, so a bigger thinker cannot lower
it much. That is where the plain LLM's growth comes from (it is not scored, but it shapes the representation).

**Ranking of Ben's candidates (suggested unless marked):**
1. **Size goes where the answer path is not** (D1-D3; shown that it does not reach the loss, suggested as the main cause).
2. **No program targets for the rule families** (D4; shown that there are none, suggested as the reason those families are flat).
3. **Thinker starved of usable input** (letter window, 9 characters). R grew the reader to 93 characters and was flat
   (shown). EGE (EmbeddingGemma before the window) raised the 3M level +1.6 / +2.1 on 2 seeds of the older skills-only data
   (shown, `custom_io/results/RESULTS-EG2.md`). Whether richer input changes the *slope* is untested. This is the hinge,
   and the screen below tests it.
4. **Rounds / registers:** more test-time rounds give nothing (shown). Training with more registers is untested, but the
   register count only matters to GEN (D4-D5).
5. **Depth vs width:** W was +1.5 over deep on one seed and +0.2 on the other (shown, 2 seeds, unclear). Same loss curve.
6. **Optimizer / lr (muP):** unlikely as the main cause (D1: identical curves from step 1k), untested directly.
7. **Data mix:** the 62% fill-in share feeds the D5 floor (suggested). Changing the mix is outside Ben's data rule only if
   rows are added; reweighting is allowed but untested.

**What would prove this diagnosis wrong:** an arm that changes only the input (EGE below) gaining at least +3.0 more than
B2 from 3M to 10M on the same seed. That would mean the thinker was starved after all, not stuck behind its narrow
answer channels.

## 2. Three fixes, each built on an EmbeddingGemma input (one change at a time)

The base is **EGE** (built: `ledger.py` `eg_embed=True`): each letter's input embedding also gets
`eg_proj(LayerNorm(H))`, where H is the 768-d EmbeddingGemma 2 state of the token that holds the letter. `eg_proj`
starts at zero, the letter window stays (cipher_map needs it, shown in RESULTS-EG2), and the frozen 271,002,624-param text
part is counted in every size comparison. Fixes 2 and 3 are each one change from Fix 1.

- **Fix 1, EGE-grow (input only).** EGE with the thinker grown 3M -> 10M exactly as the 8a ladder grows B2 (blocks 2 -> 8,
  12 rounds, 36 registers). Trained params 3,544,913 -> 10,496,537; whole model with EmbeddingGemma 274.5M -> 281.5M.
  Prediction (suggested): the level rises 1-3 points at both sizes, but the slope barely moves, because EmbeddingGemma's
  context lands in the talker's word and copy keys (D3), which do not grow.
- **Fix 2, Gemma feeds only the thinker (route).** EmbeddingGemma's states go only into the thinker's cross-attention
  memory. The number slots, word keys and copy keys use the plain letter reader (the EGK switch, `eg_thinker=True`). So
  whatever EmbeddingGemma knows can reach an answer only through the thinker, and the thinker's size should limit how
  much of it gets through. EGK went non-finite twice on seed 201 at 3M (shown). It needs a stability fix (cause
  untested), with its own 2-seed stability check before any growth run.
- **Fix 3, the thinker writes its answers (talker).** Fix 1 plus a small autoregressive letter decoder (1 layer, d 256,
  the same size at every rung, counted) that replaces the parallel GEN readout and cross-attends only to the thinker's
  final tokens. NUM and WORD pointers are unchanged. This targets D4-D5: GEN answers stop being per-letter marginals, and
  every GEN letter is conditioned on the thinker's state, so its size matters. Not built.

Backlog, not one of the three: self-found programs for the rows whose steps are labels (D4). B2 would sample its own
programs, and any program whose result equals the answer becomes a training target, with no new teacher and the full
targets kept. This would make the calculator the thinker's tool on the rule families. It is not an input change.

## 3. Marks (fixed now, before any 8b run)

Per fix X and seed s: `G_X(s) = pooled-5(X, 10M, s) - pooled-5(X, 3M, s)`, using the 8a recipe unchanged (same pool, caps,
24,000 updates x 256, lr 1e-3, bf16, rented RTX 5090s, the build at 50ee171632 plus `g8b/overlay`).

- **M1, Ben's mark (primary, gates any growth claim):** over the 6 paired seeds 400-405, the mean of
  `G_X(s) - G_LLM(s)` > 0, with the 95% paired-t interval (t = 2.571, 5 df) entirely above 0. `G_LLM` comes from
  `results/8a-ladder`; LLM-10M seed 404 was cut by the 8a cost cap and must be run first (about $1).
- **M2 (reported):** the same against PT. **M3 (reported, needed before saying "the thinker drives it"):** the same against
  PT given the same EmbeddingGemma front (not built; spec section 3 asks for it whenever B2 takes EGE).
- **Guards (each rung, each seed):** chain-5 >= 99; cipher_map pooled-5 >= 90; loops:0 in_dist <= 5 (the EGE leak, which was
  18.1 on seed 200 in RESULTS-EG2). A failed guard voids that seed's gain.
- **Sizes:** trained params (adapter included) and whole size (EmbeddingGemma included) are printed beside every number.

**The screen now (Fix 1, seed 400 only, because only $5.03 of Vast credit is left):** EGE-3M and EGE-10M, seed 400, one
5090 each, against B2 seed 400 (3M 71.59, 10M 71.62, gain +0.03) and LLM seed 400 (gain +15.03).
- **Kill line:** `G_EGE(400) < +5.0` means Fix 1 fails the screen and gets no more seeds for M1 (the LLM's smallest seed
  gain is +13.77 and B2's seed-to-seed gain sd is about 1.2).
- **Starved-input readout:** `G_EGE(400) - 0.03 >= +3.0` means supported and the diagnosis above is proved wrong;
  `< +1.0` means not supported; anything between is unclear. One seed is a screen, not a claim.
- **Prediction (written now):** `G_EGE(400)` between -1 and +2; EGE above B2 by 1-3 points at each size.
- If it passes the kill line: seeds 401-405 at both sizes plus LLM-10M s404, about $20 more, needing a top-up and Ben's yes.

**30M rung (~$42):** decided now, before the screen. Run it only if some fix passes M2 at 3M -> 10M on 6 seeds. The
current B2 shape at 30M is not worth it: its 3M and 10M training curves are the same curve, so 30M would add cost and
nothing new (suggested).

## 4. Cost

5090 at about $0.46/h (best TFLOPS per dollar on Vast today, tied with the 4090; the 4090's 24 GB is too tight for B2-10M
at 21.5 GB plus EmbeddingGemma). Screen: about 2.6 h + 5 h of box time, about $3.50.

## 5. Addendum A (2026-10-08, 10:50 AM ET, before any 8b run): Fix 1 is already running elsewhere; this thread screens Fix 3

- **Fix 1 is the roadmap thread's test 8a-G** (`design/8a-g-gemma-growth-2026-10-08.md` on `claude/project-thread-yha868`, written
  10:30 AM ET). It runs EGE at 3M and 10M on seeds 400 and 401 on the same pool and recipe, against the plain step model given the
  same EmbeddingGemma front (my M3 yardstick, built there). Its boxes were already up at 10:45 AM ET. Running my seed-400 EGE screen
  would buy the same numbers twice, so it is cancelled. Section 3's Fix 1 screen readout is applied to 8a-G's EGE numbers when they land.
  8a-G's own marks (yardstick: PT with the same front) decide its test; mine (M1: the plain LLM, as Ben's brief to this thread
  says) are reported beside them.
- **This thread screens Fix 3 instead**, built as `gen_ar` in `g8b/overlay/custom_io/models/ledger.py`: EGE plus the thinker writing
  GEN answers letter by letter. After the last round, each letter slot (units first, as the GEN targets) goes once through the
  thinker's own blocks, with the cross-attention sublayer skipped. It self-attends to the final thinker tokens and the earlier
  letters, then runs the MLP. Its states replace the 36 parallel registers in the unchanged pointer-generator (vocabulary + copy
  from the prompt). One new weight (a 256-number type embedding). The prompt reaches a letter only through the thinker's state and
  the copy pointer, as before. So the change is "parallel letters -> letters written in order by the thinker's own blocks", and
  the writer is as deep as the thinker at each rung. It is one change from 8a-G's EGE arm (call this arm **EGA**). Sizes: 3M
  3,545,169 trained (274.5M whole); 10M 10,496,793 (281.5M whole).
- **Screen:** EGA at 3M and 10M, seeds 400 and 401, the 8a recipe unchanged (pool, caps, 24,000 x 256, lr 1e-3, bf16), one RTX
  5090 per rung and seed, B2-only jobs. `d(s) = pooled-5 at 10M - pooled-5 at 3M`. Reference gains on the same seeds (shown, 8a):
  B2 +0.03 / +0.28, PT +3.08 / +4.25, LLM +15.03 / +15.20. 8a-G's G-B2 and G-PT gains are used when they land.
  - **Go to 6 seeds** if `d_EGA - d_PT >= +1.0` on both seeds and `d_EGA - d_B2 >= +3.0` on both. When 8a-G reports, it also
    needs `d_EGA - d_G-PT >= +1.0` on both.
  - **Stop** if `d_EGA - d_B2 < +1.0` on both seeds. That proves wrong the claim that the parallel answer writer is what holds
    growth back (D3-D5).
  - Otherwise **unclear**: seeds 402-403 next (still under the $40 line in total).
  - **M1 (vs the plain LLM):** reported on 2 seeds, judged only on 6.
  - **Answer-path readout (reported):** the 3M-minus-10M training-loss gap over steps 20k-24k is >= 0.05 total and >= 0.03 on
    the GEN part (B2: 0.022 and 0.014; PT: 0.033). If it isn't, the extra size still does not reach the loss.
  - **Guards (both rungs, both seeds):** chain-5 >= 99; cipher_map >= 90; thinker off (`loops:0`) pooled-5 <= half the full score
    (8a-G mark 3a). A failed guard voids that seed.
  - **Prediction (written now, suggested):** `d_EGA` between +1 and +4, with the gain on seq_next, fewshot_number_rule,
    rule_apply and digits_parity. EGA above EGE at each rung. Ben's bar against the plain LLM (+15.8) will not be met by any
    B2-like design on pooled-5 this way: B2 starts 26 points higher, with about a third of the families near 100. That is a
    prediction, and it is not a reason to change the test.
- **Cost:** 4 boxes at about $0.46-0.62/h. Estimated 3M about 2.5 h and 10M about 5.5 h with setup, about $9 in all. Caps:
  MAXH 6 (3M) and 10 (10M), at most about $19 (B2's speed varies 2x with the box CPU: 3.2-7.1 updates/s at 3M in 8a). The account refills; Ben's line for asking is $40.

## 6. Addendum B (2026-10-08, 11:05 AM ET, before any 8b run): B2 never got its 36 letter slots; the screen gains a control

- **Bug (shown, reproduced on CPU with the 8a code at 50ee171632 and the current build head 612f5c5b0):** `caps.apply()` patches
  the Ledger's `N_REG` / `GEN_MAX` only if `custom_io.models.ledger` is already imported. `train.py` applies the caps first and
  builds the model after (`models.build` imports the ledger lazily), so the Ledger kept `N_REG = 9`, `GEN_MAX = 8`. So every 8a B2
  run (ladder and probes), and 8a-G's EGE arm, ran with **9 register tokens, not 36**. The thinker held 8 + 9 = 17 tokens, not
  the 44 written in section 1. Its **GEN training targets were cut to the first 8 letters**, against addendum G's no-cut rule.
  `N_RES`, `N_NUM`, `W_MAX` came through right (the ledger copies them from `progparse`, which is patched first), and the plain arms
  are unaffected (`plain_lm` reads the step cap at call time: 109). The scored dev rows are unaffected (0 of 6,040 have a GEN answer
  over 8 letters). The caps report counts 191,172 of 1,655,902 pool rows with answers over 8 letters; those answered in GEN mode,
  mostly long web fill-in words, were trained on cut targets. Fix (`g8b/overlay/custom_io/g8a/caps.py`): import those modules
  before patching. With it the Ledger gets 36 / 35, and trained parameter counts do not change (the register slots have no weights
  of their own).
- **What it changes:** Ben's candidate "too few registers" was never tested at the intended size. The section 1 diagnosis (D1-D5)
  stands as a description of the 8a runs, with the thinker's state being 17 tokens.
- **Screen arms, now two (both with the fix, B2-only jobs, seeds 400 and 401, 3M and 10M, 8 boxes):**
  - **EGE36** = EGE with the fix (Fix 1 without the cut). Against 8a-G's EGE, the one change is the fix (registers 9 -> 36, uncut
    GEN targets). It is also the control for:
  - **EGA36** = EGE36 + `gen_ar` (Fix 3). Against EGE36, the one change is the letter writer.
- **Readout (replaces section 5's go / stop for this screen; guards, loss-gap readout and M1 reporting unchanged):**
  - EGA36 **go** to 6 seeds: `d_EGA36 - d_PT >= +1.0` and `d_EGA36 - d_EGE36 >= +2.0` on both seeds. EGA36 **stop**:
    `d_EGA36 - d_EGE36 < +1.0` on both. That proves wrong the claim that the parallel letter writer holds growth back.
  - EGE36 **go**: `d_EGE36 - d_PT >= +1.0` on both seeds. EGE36 **stop**: `d_EGE36 - d_B2 < +1.0` on both. That proves wrong
    "the input plus the missing registers is what held growth back".
  - Otherwise unclear. If 8a-G's G-PT lands, it replaces PT in both go rules (the fair yardstick).
  - Reported: EGE36 minus 8a-G's EGE per rung and seed (what the 36 slots and uncut targets are worth).
- **Prediction (written now):** EGE36 gains +0 to +2, EGA36 +1 to +4. Neither reaches the plain LLM's +15.
- **Cost:** 8 boxes at about $0.56-0.68/h; expected about $22. Caps: MAXH 6 (3M) and 9 (10M), at most about $39.

## 7. Addendum C (2026-10-08, 12:35 PM ET, after launch, before any 8b result): two launch failures, marks unchanged

- The first 3M boxes refused to start: `configs.train_args` checks the size band too, on the full config, so EGE's 198,400-param
  adapter put 3M 7.3% over. Fixed like `job.py` (band on the thinker's shape, adapter counted and reported): `ed8a8a6`.
- The first 10M boxes ran out of GPU memory 18 s into training. With the caps fix the thinker carries 8 + 36 = 44 tokens instead of
  17, and the 8a 10M B2 already peaked at 21.5 GB with 17. The 10M arms now train each 256-row update as 2 micro-batches of
  128 (`--accum B2=2`, `8084eba`). B2's losses are per-row means over the batch, so the update is the same up to rounding. The 3M
  arms fit in one batch.
- Wasted box time is about 45 min on 4 boxes plus about 40 min on 4 boxes, about $4. Caps are now MAXH 9.5 at 10M. Expected
  total about $26; if every box hit its cap, about $40.
- Nothing in sections 3, 5 or 6's marks or readout changes.

## 8. Addendum D (2026-10-08, 2:45 PM ET, no 8b result exists): the screen was killed when Vast credit ran out; marks unchanged

- **What happened (shown, Vast account at 2:27 PM ET):** all eight screen boxes (and the roadmap thread's five) were `exited`, credit 0, balance
  -$0.71. Credit was $3.68 at 12:55 PM with about 13 boxes up (about $8/h). I launched 8 boxes without checking that the balance covered
  them, and I did not watch it afterwards. No run finished and none saved anything: `train.py` writes its checkpoint and the
  result only at the end, and the loss lines lived only on the boxes' disks. **No 8b result exists.** My estimate of the wasted spend
  is about $8-9 across the 8b boxes since 11:03 AM (launch times x $0.5-0.8/h, including the two failed launch waves; Vast shows no
  per-box cost, so its billing page has the exact figure).
- **Why it wasn't "it refills":** the account's auto-billing threshold is $5.00, yet credit went from $3.68 to 0 with no charge, and
  the balance went negative. Cause unknown (a failed or capped charge is a guess). Ben has to check Vast billing.
- **The redo, if Ben funds it, is the same screen:** same two arms, same four jobs each, same marks (sections 3, 5, 6, 7), all eight
  boxes from **one** commit (the first screen's 3M and 10M boxes were on two commits; the 3M ones differ only in `configs.py`, which
  `job.py` also bypasses). About $26.
- **New safeguards:** `box-g8b.sh` prints a `PROG` line per run every 5 minutes (latest train line plus the last line of the
  run's `stdout.txt`), so speed shows by step ~500 and a kill keeps the partial loss curve. `vast8b.py create` refuses to launch unless
  credit is at least `--need` dollars (default 10); set it to cover every live box on the account, other sessions' included.
- **Untested speed risk:** EGA36's final eval decodes letters one at a time with no cache (`ar_decode`), and the final eval repeats that
  under about a dozen lesions, plus the donor eval, each batch also running EmbeddingGemma. Neither EGE nor EGA has been timed at 10M with
  `--accum 2`. At the first `PROG` lines, project training time plus the eval against MAXH 9.5 (a MAXH kill during the final
  eval loses the whole run). If it doesn't fit, raise MAXH for that box and tell Ben the new worst-case cost.
