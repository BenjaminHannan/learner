# g1-scaling-fable-2026-10-12 (claude-fable-5-1, effort xhigh, normal API)

Returned 2026-10-12 10:22 AM ET; stop_reason: end_turn; input 6,745 tokens, output 33,944 tokens; cost $1.76 at list prices; 520 s. Served by claude-fable-5-1. Prompt: g1-scaling-other-causes-2026-10-12.md

# Reading the numbers first (before causes)

Three things in your tables already constrain the answer:

1. **About three-quarters of the headline "-3.7" is plain catching up where you were already near the ceiling** (shown, assuming roughly equal family sizes — the check: 7.98 × 12/34 + 1.41 × 22/34 = 3.73 ≈ 3.71, so the assumption holds). 42% of dev rows sit in cells where ours was already 40/40. On the other ~3,480 rows ours went from ≈53% to ≈56% (+2.8), still small but not +1.6.
2. **Ours' loss has almost nothing score-relevant left in it** (shown): op ≈ 0, operand ≈ 0, NUM 0.009, GEN 0.836 (75%, flat after update 12k), leaving mode 0.196 and WORD 0.134. Total loss 1.139 → 1.128: 3× the parameters bought a 1% loss change. Plain's single CE (0.366 → 0.328) is still falling and every token of it is the same mechanism that produces answers.
3. **The 10M loop does the same thing the 3M loop did** (shown): per-round score profile nearly identical, 24 rounds = 12 rounds, extra blocks changed the loss by 0.01.

So the question is really: *why does extra depth in ours have nothing useful to do?* The causes below are the pieces of that answer.

---

## 1. Ranked causes (other than width and the parallel GEN writer)

| # | Cause | Label | Strength |
|---|---|---|---|
| C1 | Gradient starvation: the only loss terms still large (GEN on web rows) can't fall, the terms that could use depth (program) are already zero | shown + suggested | strongest |
| C2 | Yardstick: catch-up on your ceiling families and 42% rows at 100% | shown | explains the headline, not your own gain |
| C3 | Mode head / ambiguous mode targets (CE 0.196 is big) | suggested, untested | high, cheap to check |
| C4 | Paths that decide most non-program rows don't grow: local 2-conv reader → 64-d pointer keys → WORD/NUM pointers | suggested | medium-high |
| C5 | Template memorisation instead of rule learning (finite synthetic generators, no dropout, 4.3 passes) | shown for the old skills-only run, suggested now | medium |
| C6 | Optimiser/budget not retuned for a 96-application shared stack (lr 1e-3, warmup 300, 24k updates, 6 pieces/param) | suggested, untested | medium |
| C7 | Fixed 44-token state, fixed 12 rounds, teacher forcing: depth adds compute on a memory that doesn't grow, on rows where the program is already free | suggested | medium |
| C8 | Noise and exact match: one seed, per-family SE ≈ 3.3 points, your +1.64 is ≈1.2 sd from zero | shown | real; it blurs every per-family claim |
| C9 | Minor: accumulation 4→16 with summed micro-batches + clip 1.0; init scale | untested, probably small | low |

### C1. Gradient starvation — "nothing size-sensitive in the loss is score-relevant"
- **Mechanism.** By pieces, 62% of training is web fill-in; for ours those rows touch only the mode head (trivially GEN) and the GEN head. GEN is flat at 0.836 from update 12k on, at both sizes (shown for 3M; inferred for 10M from 1.128 total — **suggested**). The other 38% are skill rows, and the 14 program families have op/operand CE ≈ 0 and free-run accuracy 100% under teacher forcing (shown): once that's learned, those rows send ~zero gradient into the stack. What remains to drive the 7.3M new parameters is mode + WORD loss on a minority of rows.
- **Why plain, not ours.** Plain's web rows are ordinary LM pretraining; every layer learns spelling, English, copying — the same machinery it uses to write `step; step # answer`. Its arithmetic rows still carry loss (0.33 at the end) because the step traces are long and hard, so depth keeps getting signal from them. Ours gets its arithmetic from the tool at 3M and then has no loss left there.
- **Support (shown):** loss-term split; flat 1.139 → 1.128; program families flat for ours (mean own gain on the 13 prog=100 families ≈ +0.1 points); ours gained on some mixed WORD/GEN "reasoning" families (passage_qa, rule_apply, verify_claim, digits_parity) — exactly where loss is still nonzero.
- **This also explains the skills-only result and the flat 1.13 under one idea:** in the skills-only run the loss was already near zero (0.0128) at 3M; the 3× drop to 0.0039 is the model fitting the last residual training rows of finite generators — memorisation, which doesn't transfer to new answers/frames/words/templates. In the current run, the big term is web GEN, which can't fall for ours (writer floor, and a 2-conv reader + one frozen sentence vector carry limited information about the blanked word), so the loss is flat. Both cases: the loss either sits at zero or at a floor; neither state gives depth a job that shows up on dev. **Suggested.**
- **Interaction with G2f:** an autoregressive writer makes the web loss reducible, so web rows will *then* absorb the new capacity (the thinker becomes a web-word model). You will need to down-weight web rows or they will swamp the skill signal at 30M/100M.

### C2. The yardstick: catch-up plus ceiling
- Shown: 12 families where ours led by ≥10 at 3M account for ≈2.8 of the 3.7 difference of gains; arith_bare alone moved plain +26.8. 2,560 rows can't contribute to ours' gain at all.
- This does not rescue your real goal (own gain on non-ceiling rows ≈ +2.8 is still weak), but "difference of gains" is the wrong number to stare at. See §5.

### C3. Mode head and mode-label ambiguity
- **Mechanism.** Mode CE averages 0.196 over all rows. If web rows are all GEN (near-zero CE there), the skill-row mode CE is roughly 0.196 ÷ skill-row share — plausibly ~0.4–0.5 nats, i.e. real confusion. A wrong mode is a guaranteed exact-match miss no matter how good the thinker is. Your labeller marks overlapping gold types (story_chain3: NUM 50.5 / WORD 49; table_lookup: WORD 31 / GEN 67.5; syllogism, order_chain, list_index, passage_qa, rule_apply all mixed). **Missing fact:** which single mode is the training target when several are valid. If it is arbitrary/priority-based per row, the 0.196 is partly a floor that no amount of depth lowers; the fix is a marginal loss (log-sum over valid modes).
- **Why plain, not ours:** plain has no mode decision.
- **Support (suggested):** ours is weakest or flattest on mixed-mode families (table_lookup 27.5→31.5, list_index 62.5→63, order_chain 71→68.5, syllogism 86.9 flat); compare_numbers at 75% with a CMP op available and NUM gold smells like a wrong-mode/wrong-slot error, not a reasoning error. **Untested.**

### C4. The non-growing paths that decide most non-program rows
- **Mechanism.** From 3M to 10M only thinker blocks grow. The reader (2 conv blocks, ±4 chars, no attention), the number-slot extraction (mean reader state over digits), the 64-d pointer keys, and the mode/pointer heads are identical at both sizes (35% → 12% of parameters, shown). WORD and NUM pointers choose among keys computed by the fixed local reader; the thinker can only improve the *query*. Parsing an unfamiliar template is a reading problem: ours' variant file (1,320 rows, 22% of the score, at 37%) gained +1.66 vs plain +4.40 (shown). Plain re-reads raw characters with full attention at every one of its 13 layers; its reading grows with size.
- **Support:** WORD-gold families flat for ours (copy_word 85→81, group_induct 81.7→80, object_track 60.5→62, prop_eval 87.5→88.3); lesion "word-copy path off" costs 22.5 points, so this path carries a lot of score (shown). **Weakens:** the old 23-conv reader probe (+0.73 / −1.46) didn't help — but that was the bugged 9-register model, so weak evidence either way. **Suggested.**
- **Missing fact:** a per-file × per-family table. If ours' residual errors on calculator families (div_exact 85, table_calc 78, story_addsub 91) are concentrated in the variant/frame files, that pins the bottleneck on reading rather than thinking.

### C5. Memorising templates rather than learning rules
- **Mechanism.** Synthetic generators have finite templates; 4.3 passes, no dropout, loss near zero on skill rows. Bigger ours fits the training rows more exactly (shown in the old run: 0.0128 → 0.0039) without moving dev (89.6 → 91.0). Under teacher forcing the template → program mapping is learnable as a lookup; more capacity means a better lookup, not better parsing.
- **Why plain, not ours:** plain's targets are long traces with token-mean CE that never gets near zero in 24k updates, so it stays in the "still learning general regularities" regime. **Suggested.**

### C6. Optimiser and budget for a 96-application shared stack
- **Mechanism.** Same lr 1e-3, same 300-step warmup, same 24k updates for 24 and 96 sequential block applications. With weight sharing, one weight is used 12× per forward, so each Adam step moves the *function* far more than the same step in plain; and 6 pieces/param at 10M is thin for both arms, but ours' usable signal is thinner (C1). Init scale (0.0012) is probably *not* the issue: Adam moves each weight by ~lr per step, so an init of 0.0012 vs 0.0039 is erased within tens of updates (**suggested**).
- **Support:** 10M loss ≈ 3M loss despite 3× parameters; identical per-round profile. **Weakens:** 3M with the same lr trained fine; the old width-384 probe with lr scaling also gained little. **Untested.** **Missing:** pre-clip grad-norm logs and any loss spikes at 10M.

### C7. Fixed 44-token state, fixed rounds, teacher forcing
- **Mechanism.** Plain's depth adds both compute and *memory* (13 layers of activations over every position). Ours' depth adds compute over a fixed 44 × 256 state; the loop converges to a fixed point (24 rounds = 12 rounds, shown), and a deeper per-round stack reaches the same attractor faster rather than a better one (**suggested**). Teacher forcing means on 14 families the loop is never asked to do anything the gold program didn't spell out; on the other 20 families (op weight 0.1, no program) the rounds are just refinement steps with no structured target. No-halting is harmless given convergence.
- **Interaction with WIDE:** width grows the state (44 × 448) and the pointer queries — so WIDE partly tests C7, not just "width vs depth".

### C8. Noise and exact match
- Shown: per-arm pooled-5 seed sd ≈ 1.0, row-level SE ≈ 0.57; gain sd ≈ 1.4. Plain's +5.35 is ≈3.8 sd; ours' +1.64 is ≈1.2 sd (and only +1.3 against the two-seed 3M mean of 73.34). Per-family n ≈ 160–200 → SE ≈ 3.3 points; verify_claim swings 20 points between seeds. "Zero or negative on 17/34" is consistent with a true small positive gain plus noise. Exact match hides partial GEN progress (one letter wrong = zero).

### C9. Minor
- Summed micro-batches (4 → 16 for ours, 4 → 8 for plain) with clip at 1.0: a 4× larger summed gradient at 10M is clipped far more often; Adam mostly cancels a uniform scale, but the interaction with epsilon/clipping differs between sizes and arms. **Untested, probably small.** Check from logs (pre-clip norm, clip frequency).

---

## 2. Diagnostics first (CPU, saved final weights + logs, no training)

| # | Measurement | Points to |
|---|---|---|
| D1 | Recompute per-term loss (op, operand, mode, NUM, WORD, GEN-web, GEN-skill) at 3M and 10M on a fixed sample (2k skill rows + 2k web rows). | If GEN-web flat and mode/WORD barely moved → C1 (nothing reducible). If mode/WORD dropped but score didn't → look at C3/C8 (errors at decision time, not capacity). |
| D2 | Mode oracle on all 6,040 dev rows: run all three answer modes per row; score = 1 if *any* matches gold. Also the confusion matrix of chosen mode vs. modes that would have been right. | Oracle − actual ≥ 3 points, or oracle *gain* 3M→10M ≫ +1.6 → C3 is masking real scaling. Oracle gain also small → bottleneck is upstream (C1/C4/C5). |
| D3 | Block knockout at 10M: skip block k (k = 1..8) at test time, in_dist score; plus per-block residual-contribution norm ‖block out‖/‖stream‖ per round. | Skipping blocks 3–8 costs < 1–2 points each and their contributions are ≪ blocks 1–2 → the depth is inert → C1/C6/C7. Large costs → depth is used but mis-aimed → C3/C4/C5. |
| D4 | Full per-round profile 0..12 at both sizes, and ‖s_t − s_{t−1}‖ per round. | Fixed point reached by the same round at both sizes → C7. 10M converges earlier but to the same score → extra depth = faster, not better. |
| D5 | Partial credit: character accuracy / edit distance on GEN-gold rows; top-3 pointer rank on WORD/NUM rows, 3M vs 10M. | Near-miss improvement without exact-match improvement → C8's exact-match part (and tells you how much G2f can harvest). |
| D6 | Score accounting: gain on the 3,480 non-ceiling rows; gain excluding the 12 catch-up families; row-level bootstrap CIs for both arms. | Quantifies C2 and C8; this is the number you should track from now on. |
| D7 | Gradient-share: one backward pass on a representative batch at each size; norm of the stack gradient coming from web-GEN vs skill terms. | > 50% from a flat term → C1 confirmed as "most of the gradient is wasted". |
| D8 | Count training rows with ≥ 2 valid gold modes and which one the loss targets. | Any arbitrary/priority assignment → C3 has a floor; use a marginal loss. |
| D9 | Logs: pre-clip grad norm, clip frequency, loss spikes, final block weight norms (blocks 3–8 vs 1–2) at 10M. | Norms near init / constant clipping → C6/C9. |
| D10 | Per-file × per-family table for ours. | Residual calculator-family errors concentrated in variant/frame → C4 (reading), not thinking. |

D1, D2, D3 and D6 together separate the top four causes in an afternoon.

---

## 3. Three training tests (one change each, in this order)

**T1 — Web-row loss weight 0.1 (tests C1).** Ours 3M, seeds 400 + 401, everything else identical. Cost: 2 × 6.5 h. Pass: two-seed mean pooled-5 ≥ 74.8 (≥ +1.5 over the 3M two-seed mean 73.34, and the per-term loss shows mode/WORD falling). Fail: ≤ 73.5. Disproof: a fail means web rows were not stealing anything usable at 3M — C1 then reduces to "program rows are already zero", which T1 can't fix (then C4/C5/C7 lead). Mapping to 10M: at 3M there is little idle capacity, so even +1.5 here predicts a larger effect at 10M; if T1 passes, T3 runs with it.

**T2 — Marginal mode loss (tests C3), only if D2 shows oracle − actual ≥ 3 points.** Replace mode CE + the chosen mode's NLL with −log Σ over valid modes of p(mode)·p(answer | mode). Ours 3M, seed 400, 6.5 h. Pass: pooled-5 ≥ 74.8 and dev mode-error rate halves. Fail: ≤ 73.5. Disproof: if D2 shows the oracle gap < 1.5, skip T2 entirely (C3 is wrong). Fallback T2′ if D2 is negative: 3M with 48k updates (13 h) to test the budget part of C6 — pass ≥ +1.5; a pass means equal-updates ladders are unfair to the bigger model and your 100M will be starved.

**T3 — 10M with whichever of T1/T2 passed (the scaling test itself).** Seed 400, ~43 h; save checkpoints every 4k updates from now on. Pass: own gain over the matching new 3M ≥ +3.5 on pooled-5 and ≥ +4 on the non-ceiling subset. Fail: own gain ≤ +2.0. Disproof: 3M improved but 10M gain still ≤ 2 → the surviving culprit is the deep shared stack's optimisation (C6/C7); then try lr 5e-4 + 1,200-step warmup at 10M, or prefer WIDE. Short-run mapping: compare the 10M checkpoint at 12k updates with the 3M at 12k on in_dist; if 10M@12k ≤ 3M@12k + 1, kill the run and call it a fail (the 3M in_dist curve flattens by ~12k, so a 10M that isn't ahead there won't catch up).

A cheaper extra ladder point (4 blocks ≈ 5.8M, ~20 h) would give you a three-point curve and a halfway stop rule.

---

## 4. What still bites at 30M and 100M even if WIDE and G2f both pass

- **C1 (flips sign):** with a working AR writer, the 62% web rows become learnable and will dominate the gradient at larger sizes; skill rows still send ~zero signal from program families. Needs explicit loss weighting or a curriculum.
- **C5/C7:** teacher-forced programs on finite templates are solved at 3M; nothing in the loop gets harder with size. Variant-file score (~37%) will not move unless reading generalises.
- **C4:** the reader, slot extraction and pointer keys stay fixed functions; at 100M they're ~1% of parameters but still the gate for every WORD/NUM row.
- **C6 + wall clock:** 10M already takes 43 h at 14–41% GPU busy (launch-bound: 96 tiny sequential kernels). 100M at equal updates means ~0.6 pieces/param and weeks of wall clock; plain at 100M would be undertrained too, but ours more so. Equal-updates is not a viable ladder rule past 30M.
- **C2/C8:** with 42% of rows already at ceiling, the score has less than 30 points of headroom and ~1.4-point noise per gain; the dev set itself needs harder families or more rows.

---

## 5. Is the yardstick fair? What single number would convince me?

Fair in the narrow sense (same rows, updates, lr, data), not in the useful sense:
- "Difference of gains" rewards plain for buying with parameters what your tool bought for free (C2, shown).
- Equal updates ≠ equal compute (ours 10M: 43 h; plain: 4 h) and ≠ equal usable gradient (C1).
- One seed with sd ≈ 1.4 on a gain cannot distinguish +1.6 from +4 (C8, shown).
- Exact match on GEN rows hides progress (C8/D5).

**The one number:** ours' own 3M→10M pooled-5 gain on the 3,480 non-ceiling rows, mean of seeds 400 and 401, with a row-bootstrap 95% CI whose lower bound is above +1.5 — I'd want ≥ +4.0. Not "beat plain's gain"; "your own curve rises outside the noise". Then repeat the same number for 10M→30M.

**Missing facts that would change the ranking:** the 10M per-term loss (D1 — if mode/WORD fell a lot, C3/C8 rise above C1); the mode-target policy for overlapping gold types (D8); the per-file × family table (D10 — decides C4 vs C7); pre-clip grad norms (C6/C9).

---

## 6. Plain-language summary

Your bigger model didn't learn much more because there was almost nothing left for it to learn from. The calculator rows are already perfect at 3M (zero loss), and three-quarters of the remaining loss is the web word-guessing task, which sits at a floor your design can't lower — so the extra blocks get no useful teaching signal, and the loop just reaches the same answer as before. On top of that, most of the plain model's "big gain" is it catching up on arithmetic you already had, and your +1.6 is within the noise of one seed. Before training anything: recompute the per-term losses at 10M, run the "mode oracle" (would any answer mode have been right?), and knock out blocks 3–8 at 10M to see if they do anything. Then try down-weighting web rows at 3M (cheap), fix the mode loss if the oracle says so, and only then spend 43 hours on a 10M rerun. Track your own gain on the non-ceiling rows, two seeds.
