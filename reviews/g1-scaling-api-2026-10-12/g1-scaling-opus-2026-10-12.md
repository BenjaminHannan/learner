# g1-scaling-opus-2026-10-12 (claude-opus-5-5, effort xhigh, normal API)

Returned 2026-10-12 10:27 AM ET; stop_reason: end_turn; input 6,745 tokens, output 78,298 tokens; cost $1.59 at list prices; 799 s. Served by claude-opus-5-5. Prompt: g1-scaling-other-causes-2026-10-12.md

# Gate G1: why ours gains so little from size (causes other than width and the GEN writer)

Labels: **[shown]** follows from your numbers. **[suggested]** is my inference. **[untested]** is a plausible mechanism with no evidence yet.

---

## 0. The most useful fact is already in your table

The family sizes can be recovered exactly. Every family score is a multiple of 1/120, 1/160 or 1/200, and those sizes sum to 6,040 **[shown]**. I split the 34 families into the 13 whose gold answers are at least 99% calculator-reachable (the "calculator families") and the other 21:

| block | rows | ours: errors at 3M | ours: net fixed by 10M | plain: errors at 3M | plain: net fixed by 10M |
|---|---|---|---|---|---|
| 13 calculator families | 2,440 | 270 | **−1 (0%)** | 572 | **+191 (33%)** |
| other 21 families | 3,600 | 1,360 | +100 (7.4%) | 1,414 | +132 (9.3%) |
| all | 6,040 | 1,630 | +99 (6.1%) | 1,986 | +323 (16.3%) |

What this table shows:

- **Where the gap is.** 86% of the −3.71 gap (−192 of −224 rows) sits in the calculator families **[shown]**.
- **Outside them, the arms scale alike.** Both fix a similar share of their own errors (7.4% vs 9.3%) **[shown]**.
- **What ours' 270 calculator-family errors are.** They cannot be arithmetic errors: the calculator is exact and program accuracy is 100% on the 400-row check. So they are reading or routing errors on unfamiliar rows, and 4x more depth fixed none of them **[suggested; D1 confirms]**.
- **What plain's +191 there is.** Much of it is plain learning to compute (arith_bare +43 rows, chain_ops +24), which ours never needs to learn **[suggested]**.
- **Where ours' errors are by file (10M).** The variant file holds 814 of 1,531 errors (53%) and the answer file holds 325 (21%). Ours fixes 2.6% of its variant errors per rung; plain fixes 6.5% **[shown]**.
- **Saturation does not explain it.** The change in log-odds is 0.085 for ours vs 0.254 for plain **[shown]**.
- **Noise.** A single-seed gain has a standard deviation of about 1.2, judging from your six-seed confidence interval. So ours' +1.64 is about 1.4 standard deviations: it does not yet prove any rise **[shown arithmetic]**. The gap is about 2 standard deviations and has the same sign as the earlier ladder, so it is probably real **[suggested]**.

So the sharp question is: **why does 4x more thinker depth fix zero of ours' errors on the families the design is built for?** I rank causes mainly by how well they answer that.

---

## 1. Ranked causes

### 1. Fixed, local reader feeds every pointer (grounding bottleneck) — [suggested], highest

**Mechanism.**
- Each number slot is the mean reader state over that number's digits; words likely work the same way. The reader is 2 conv blocks (about ±4 characters of context), plus the encoder vector, plus position.
- Every operand pointer, NUM/WORD pointer and thinker cross-attention reads these vectors.
- Adding blocks per round improves the query side. The keys and values stay just as shallow.
- On a new template, the cue that separates "price" from "count" may be 10+ characters away. The keys don't carry it, so the thinker must rebuild it through 44 queries × 4 heads, which it learned only for training templates.

**Why ours, not plain.** Plain re-reads every prompt character with full attention in every layer, so 4 → 13 layers deepens each number token's own representation. In ours the growing part (blocks per round) sits entirely behind a reader that never grows.

**For:**
- 0 of 270 calculator-family errors fixed.
- Program terms ≈ 0, yet families stay stuck: backward_solve 81 → 81, compare_numbers 75 → 76, table_calc 79 → 78.
- The per-round profile is identical at both sizes, and extra rounds add nothing.
- The variant file improved least.
- Lesions show heavy reliance on the copy paths: in_dist drops 6.6 with operand-copy off and 22.5 with word-copy off.

**Against.** The 23-layer conv reader probe did not help (+0.73 / −1.46). But that reader was still local, ran in the bugged era, and had no attention. Nobody has tried an attention reader.

**Interaction.**
- WIDE widens the reader (if width is global) but keeps it local and 2 blocks deep, so it helps at most partly.
- G2f, if it sees the question, gives GEN rows their own read path. Pointer and calculator rows still read through the old keys.

### 2. The objective is already satisfied where ours' errors live — [suggested] (expands "nothing left to learn")

**Mechanism.**
- The exact calculator plus teacher forcing make in-distribution program rows easy: op and operand loss are about 0 at 3M.
- Rows at near-zero loss send near-zero gradient. So the extra 7M parameters get almost no signal from exactly the families where ours' dev errors are.
- Those errors are generalisation errors (new templates, new answers) that the training loss never sees.
- The spare capacity goes to fitting repeated rows (4.3 passes) and to the web/GEN terms.

**Why ours, not plain.** Plain must spell out steps and digits, so it keeps making errors on training rows (loss 0.33–0.37). Those rows keep pushing gradient through all of its prompt representations, and better reading comes along as a by-product.

**Skills-only result explained.**
- A mean training loss of 0.0128, summed over terms, means nearly every training row was right. A wrong mode or pointer costs at least ln 2 ≈ 0.69 on that row. So at most about 2% of rows can be wrong if errors are mode/pointer errors, and up to about 14% if they were single wrong characters in 8-letter GEN targets.
- Meanwhile in_dist dev was about 90%. So there was a train/dev gap at both sizes.
- The 3x lower loss at 10M is a more confident or memorised fit to rows already seen, not better generalisation **[suggested; depends on loss normalisation]**.

**Flat 1.13 explained by the same idea.**
- At 3M, the skill-type terms (op, operand, NUM) sum to about 0.01. GEN, mode and WORD make up the rest **[shown]**.
- A 3x drop in the skill terms, as in skills-only, would lower the total by about 0.007–0.01. That is about the −0.011 you observed.
- So the flat total is consistent with the 10M fitting skill rows 3x better while dev barely moves **[suggested; D3 checks]**.

**For.** Ours' real gains are where loss is not zero: rule_apply +26 rows, digits_parity +22, passage_qa +20, verify_claim +17, kin_chain +13. All are non-calculator families **[shown]**.

**Interaction.** Neither WIDE nor G2f addresses this.

### 3. The yardstick: catch-up, ceilings, file mix, noise — [shown], explains most of the gap but not ours' flat curve

- **Catch-up.** 191 of plain's 323 gained rows are in calculator families.
- **Ceilings.** chain_ops, story_chain3 and state_update (600 rows) were at about 100% for ours at 3M, so no gain was possible.
- **File mix.** The variant file is 22% of rows, holds half of ours' errors, and both arms score under 40% on it.
- **Exact match** may hide partial GEN progress **[untested; D7]**.
- **Noise** is as described in section 0.

### 4. Optimising the deep shared stack — [untested], cheap to check

- **Residual additions per answer** **[shown from code]**:

  | model | residual additions |
  |---|---|
  | ours 3M | 72 |
  | ours 10M | 288 (3 sublayers × 8 blocks × 12 rounds) |
  | plain 10M | 26 |

- **The depth-scaled init is erased early.** Adam moves each weight by roughly the learning rate per step, regardless of init. The 0.0012 init on output projections is overtaken during warmup, so depth-scaling stops controlling branch size after a few hundred updates **[suggested]**.
- **Same learning rate at 4x the residual depth.** Every weight is reused 12 times and warmup is only 300 steps. This may leave late blocks near-identity.
- **Gradient clipping with accumulation.** If micro-batch losses are summed, not averaged, the 10M's raw gradient norm is about 4x the 3M's (16 vs 4 micro-batches) against the same clip of 1.0. Clipping would then fire almost every step **[untested; check code]**.
- **For.** Flat loss; identical round profiles.
- **Against.** In skills-only, the 10M cut training loss 3x, so depth can be used.
- **WIDE confounds this cause.** WIDE also lowers the learning rate (×0.57) and returns to 72 residual additions. A WIDE pass will not tell you whether width or optimisation was the fix.

### 5. Web blanks own ours' gradient — [suggested] mechanism, [untested] size

**Mechanism.**
- 62% of pieces are web fill-in rows. For ours, a web row is a mode decision plus usually a 35-character GEN output. GEN is 75% of the loss and flat after update 12,000.
- Ours weights each row equally. Plain uses a token mean over target characters, so its long step targets (up to 109 characters) outweigh a one-word blank many times over.
- With ours' program terms about 0, late gradient is mostly web GEN + mode + WORD. Clipping a web-dominated gradient norm also shrinks whatever skill signal remains.

**Against.** In the skills-only look (no web rows), ours still gained little (+1.42 / −0.28). So this is not the only cause.

**Interaction.** G2f changes this. An autoregressive writer with token-mean loss would match plain's weighting and turn web rows into useful language signal.

### 6. Output routing: mode head and single-word pointer — [suggested]

- **Mode loss is high.** Mode cross-entropy of 0.196 is too high for a solved 3-way choice. It implies a few percent of rows are mis-routed, or the mode labels are ambiguous.
- **A wrong mode is a sure miss.** Plain has no routing step that can fail this way.
- **The WORD pointer copies only one word.**
  - In table_lookup, ours scores 27.5 and 31.5 while 31% of gold answers are WORD-reachable. That is consistent with ours getting almost only the WORD-reachable rows **[numbers shown, inference suggested]**.
  - Plain reaches 70% there, so the other rows are learnable.
  - If those answers are multi-word copies, a span pointer (start and end positions) would reach them. That is a pointer-design problem, not a GEN-writer problem.
- **Interaction.** G2f shrinks the cost of mis-routing to GEN, but the mode head still decides.

### 7. The calculator is used only by imitation — [suggested]

- Programs are learned only from gold programs. Rows without a program get op weight 0.1, probably trained toward NOOP (missing fact).
- So numeric families with no labelled programs can never use the calculator:
  - fewshot_number_rule (96% GEN): ours 10.6 → 10.6, plain 40 → 44.
  - Possibly seq_next: ours 33 → 34, plain 44 → 55.
- Neither WIDE nor G2f fixes this.

### 8. Fixed 44-token thinker state — [suggested], low-to-mid

- Depth adds compute, not memory. Plain's memory is every position × every layer.
- The registers double as GEN output slots and start as copies of the first 36 prompt characters.
- **For.** The shuffled-state lesion drops in_dist to 7.7.
- **Interaction.** WIDE widens each token, and G2f could free the registers from output duty.

### 9. Update budget — [untested]

- The deeper tied loop may need more than 24k updates.
- **Check:** whether the 10M loss was still falling at the end.
- **Against:** 3M GEN was flat after update 12k, and plain gains at the same budget.

### 10. Fixed 12 rounds, no halting, teacher forcing — weakened [shown]

- Extra rounds at test time add nothing. Free-run accuracy equals teacher-forced (100%). Chain-5 is 100%.
- Teacher forcing could matter only on new templates (no training to recover after a wrong first call). D1 shows whether errors start in round 1.

### 11. Frozen-encoder route — weakened [shown]

- Both arms receive the same projected encoder state.
- The scaling deficit predates the encoder (+0.49 vs +3.77 in the earlier ladder).

### Facts I'm missing, and what they'd change

| missing fact | what it changes |
|---|---|
| 10M loss split by term (recoverable via D3) | orders causes 2, 4 and 5 |
| Web share by **rows**; GEN loss normalisation (per row or per character, padding) | strength of cause 5 |
| Mode-label rule when several modes reach gold | cause 6 |
| Op target on rows without a program | cause 7 |
| Encoder output pooled or per token | per-token states aligned to characters would weaken cause 1 |
| Sum vs mean in accumulation; gradient-norm logs; pre-LN in ours | cause 4 |
| Whether WIDE widens the reader | WIDE's overlap with cause 1 |
| What table_lookup, seq_next and fewshot GEN answers look like (numbers? multi-word?) | causes 6 and 7 |

---

## 2. Diagnostics on saved weights (CPU only, no training)

Run them in this order.

| # | Measurement | Reading |
|---|---|---|
| D8 | **Code and logs (minutes):** accumulation normalisation, clip rate, whether the 10M loss was still falling at 24k, GEN normalisation, mode-label rule, op target on rows without a program, web share by rows. | Clipping on more than 90% of 10M steps → cause 4. Loss still falling → cause 9. |
| D1 | **Error ledger, 3M and 10M, all 6,040 rows.** For each miss: predicted mode vs modes that could reach the gold. For program rows, the first round whose call leaves every valid program, and whether op or operand was wrong. For NUM/WORD, the rank of the gold slot. Cross-tabulate by file. | Operand/pointer errors on variant/answer, same rows at both sizes → cause 1. Mode errors → cause 6. Op errors would be surprising (depth should help those). |
| D3 | **Per-term teacher-forced loss on about 4k training rows, both sizes, split web vs skill and by family; plus greedy exact match on training rows.** | Skill terms fall at 10M while dev is flat → cause 2. Web GEN equal and dominant → cause 5. All terms equal → depth unused → cause 4. |
| D6 | **10M block audit.** Per-block, per-round ratio of update size to state size. Skip each block at test time; skip blocks 3–8 in every round. Check how far weights moved from init. | Most blocks removable for under 1 point → idle depth (cause 4, or 2). |
| D2 | **Row flips.** Count fixed and broken rows for 3M → 10M vs seed 400 → 401 at 3M. | If size churn looks like seed churn, the size change did nothing systematic. It also gives you a real noise estimate. |
| D4 | **Oracle rescoring.** Force the best reachable mode; separately force the gold first-round operands. Recompute the 10M gain under each. | If the gain under oracle mode is far above +1.64, routing is masking the thinker's progress (cause 6). |
| D7 | **Gold log-likelihood and per-character accuracy by family, both arms, both sizes.** | Ours' gold likelihood improves at 10M while exact match is flat → exact match hides progress, and G2f is likely to cash it in. |
| D5 | **Grounding probe.** Fit a logistic probe for "this number is a gold operand" on ours' slot vectors vs plain's hidden states at the same digits. Train on in_dist, test on variant. | Plain's probe improves 3M → 10M while ours stays flat and lower → cause 1. |

---

## 3. Training tests (one change each, in this order)

### Before any 10M run: fix throughput

At 10M, 16-way accumulation means 16-row micro-batches, which is why the GPU sits 14–41% busy. Activation checkpointing per round should allow larger micro-batches and perhaps cut wall-clock 2–3x **[suggested]**.

Settle sum vs mean accumulation first. Otherwise changing the micro-batch count also changes how often clipping fires (cause 4). Check on a short run that the loss curve matches.

### T1 — R10: spend the 10M budget on the reader (tests cause 1)

- **Change:** keep the 3M thinker (2 blocks per round). Add 9 pre-LN bidirectional self-attention blocks after the conv reader (width 256, 4 heads, MLP 4x), giving about 10.6M parameters. Slots and words are pooled from the new reader output. Learning rate stays 1e-3, seed 400.
- **Cost:** about 8–10 hours. Estimate: the 3M run (6.5 h) plus attention over the prompt, which cost plain about 1.7 h for 9 extra layers.
- **Pass:** pooled score ≥ 76.31 (WIDE's bar) **and** at least 41 rows net fixed in the calculator families (15% of 270).
- **Fail:** pooled score ≤ 75.01 **and** at most 14 rows fixed there (5%).
- **In between:** run seed 401, compared against the 3M seed-401 score of 73.675.
- **What proves cause 1 wrong:** at most 5% of calculator-family errors fixed. Then cause 2 leads.
- **Short-run mapping:** none needed; this is a full-length run.

### T2 — continuation-mix test (separates causes 5 and 2)

- **Change:** continue the saved final 3M and 10M weights for 2,000 updates at constant learning rate 1e-4. Use a 100-step warmup to rebuild the Adam state. Two arms per size: (a) the same data mix, (b) skill rows only. This is a diagnostic, not a recipe.
- **Effect:** E = score(b) − score(a), computed for each size.
- **Cost:** about 8 hours (10M runs about 3.6 h each, 3M runs about 0.55 h each).
- **Pass (cause 5 is real):** E at 10M ≥ +1.5 **and** E at 10M − E at 3M ≥ +1.0.
- **Fail:** E at 10M ≤ +0.5, or the 10M's E is no larger than the 3M's.
- **Bonus reading:** if only non-calculator families move, cause 2 is supported (no gradient reaches the calculator rows).
- **Short-run mapping:** this shows capacity already present in the weights, not how a from-scratch run would allocate it. A pass justifies a later full run with web-row weighting, nothing more.

### T3 — choose one by the rule below, written down before running

Apply the first rule that matches:

- **T3a — learning-rate test (cause 4).** Run this if D6 shows half or more of the 10M's blocks removable, or D8 shows clipping on more than 90% of steps.
  - **Change:** the 10M depth arm at learning rate 5e-4 vs 1e-3, both on a compressed 6,000-update schedule, plus a 3M reference on the same schedule.
  - **Cost:** about 23 hours before the throughput fix.
  - **Pass:** 5e-4 beats 1e-3 by at least 1.5 points. **Fail:** the two are within ±0.7.
  - **Mapping:** short-run learning-rate rankings usually hold, and the best learning rate tends to drift lower for longer runs. So a win for 5e-4 should persist at 24k updates. A tie does not fully clear cause 4.
- **T3b — marginal-mode loss (cause 6).** Run this if D4's oracle-mode lift is at least 2 points and D1 shows at least 25% routing errors.
  - **Change:** at 3M, replace the mode cross-entropy with −log Σ over valid modes of p(mode) · p(gold | mode).
  - **Cost:** 6.5 hours.
  - **Pass:** at least +1.5 pooled, with the mixed-mode families up 5 or more points. **Fail:** at most +0.5.
- **T3c — second seed.** If neither rule above fires, run seed 401 of whichever 10M variant passed (WIDE or R10).

---

## 4. What still bites at 30M and 100M even if WIDE and G2f both work

- **Cause 1 (fixed reader).** The fixed part shrinks to about 4% of the model at 30M and about 1% at 100M, unless the reader grows with size.
- **Cause 2 plus data.** The pool is 60M pieces. At 100M parameters that is 0.6 unique and 2.6 drawn pieces per parameter: a memorisation regime. The calculator keeps training rows easy, so spare capacity memorises **[suggested]**.
- **Cause 3 (yardstick).** More families hit 100%, and the variant file remains a floor.
- **Causes 6 and 7.** G2f softens routing errors, but the mode head and the imitation-only calculator remain.
- **Cause 4.** It returns with any depth growth. Under width scaling, not every parameter should get the 256/448 learning-rate scaling: embeddings and heads differ.
- **Compute.** At current throughput, a 100M ours on one GPU leaves no room for seeds or learning-rate sweeps. That alone can hide real scaling.

---

## 5. Is the yardstick fair, and what number would convince me?

**Fairness.**
- The plain step model is a fair control: same data and updates, comparable supervision (steps vs programs).
- But "difference of gains" rewards plain for learning arithmetic, which ours has by construction. 86% of the gap comes from that block.
- Your own goal, ours rising with size, is the right test.
- Pooled-5 is fine, but always report the calculator and other blocks plus the per-file split.
- One seed cannot resolve claims of ±1.5 points.

**The single number:** ours' error ratio, err(10M) / err(3M) on pooled-5, averaged over 2 seeds per size, should be **≤ 0.85**, repeated at 30M.

| | current error ratio |
|---|---|
| ours | 0.939 |
| plain | 0.837 |
| WIDE's pass bar, expressed as a ratio | 0.878 |

Guard: the calculator-family block alone should be ≤ 0.90 (currently 1.004). Ratios of 0.93 or worse at both rungs would mean the design scales poorly.

---

## 6. Plain-language summary (about 145 words)

Most of the gap comes from 13 arithmetic families. Your model already does arithmetic with its calculator, so it can't improve there by "learning math." The plain model can, and that is most of its gain. On the other families, both models improve at similar speeds.

The real problem: your model's remaining arithmetic-family mistakes are reading mistakes on new wordings, and making the thinker four times deeper fixed none of them. The likely reason is the small reader that never grows. Every bigger model still reads the question through it. Training also sends almost no signal there, because those training rows are already "solved," so extra size mostly memorises.

Next steps:
1. Run the free CPU checks, starting with sorting your model's mistakes by type.
2. Try putting the extra size into the reader (about 9 hours).
3. Judge success by the share of its own mistakes your model fixes, using two seeds.
