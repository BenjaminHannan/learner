# Hypothesis queue

Ordered by rank: the top untried card is what a `literature` trial implements next.
Re-rank at every research refresh. Keep retired cards (with their trial ids): failures are results.
Rules for every card: no test-time search; synthetic prompts only from programs the night found (W, chain search over its own notes) or a generic prior;
filters may only be generic (runs, depends on x, prompt-format rules, behaviour-distinct, length). Never favour the five held-out shapes.

## H1 - Execution replay of found programs   [status: near-miss, trial 1]
- Idea: for every found program (W + chain records), make k fresh prompts of the same rule: new shown inputs and a new query from the C2 input domain, outputs from the program; prompt-format filters only.
- Mechanism: the model learns to read the rule from many example sets instead of 1 per pool question; DEV uses the same 65 rules with new examples.
- Source: Shin 2019 (1912.12345), RobustFill, SOAR dose <= 50/task.
- Expected effect: large on rules with found programs; +5 to +20 points overall (guess), mostly sq_plus/double_add/affine.
- Cost: CPU seconds to make prompts; training cost grows with k (keep updates bounded first, then raise).
- Risk: wrong-but-fitting programs replayed many times; overfit to x-range; harm from fewer replay rows.
- Trials: segment 2 #7 (compliant top-up at 80 visits) DISCARD -0.5: affine 21->21/25 but last_digit 100->84/80; the top-up trades rules, it does not add capacity. #5 (combine #1 + H14) near-miss +0.2: top-up to 32 records per distinct program lifts affine 6->31 / 25 but costs last_digit (92->82 on s201), square and double_add a little; a capacity/updates trade-off, so pair it with more updates. #4 (simplify, ablation) removing the per-record replay at the same batch-1024 updates loses badly (seed 0: sq_plus 69->31, double_add 67->16): replay is what makes the big sleep work, not size alone. #1 near-miss +2.6 (k=24 per distinct program, 16 visits, batch 512). Constant rules up (affine 8->14, sq_plus 20->37, double_add 7->22) but square 94->83 and last_digit 96->69: per-program balance makes the two one-program rules rare. Next: replay per record (keeps the pool's mix).

## H2 - Canonical constant builders   [status: untried]
- Idea: rewrite every training program's x-independent sub-computations to the shortest builder from 1/2/10/100 with a fixed tie order.
- Mechanism: removes aliasing (7 = 10-2-1 = 2+2+2+1), so greedy decoding does not split probability across equivalent targets.
- Source: Gauthier and Urban 2022 (2202.11908), Bunel 2018 (1805.04276), DreamCoder MAP.
- Expected effect: +1 to +4 points.
- Cost: an executor table; no extra training.
- Risk: the canonical builder may be longer than what the model writes, or clash with the practised add/mult programs' style.
- Trials:

## H3 - Train longer on W + C   [status: KEPT, trial 2]
- Idea: more updates (2x-4x job 6's) on W + chain records.
- Mechanism: BC used job 6's updates for 3x the records (about 5 visits per record).
- Source: local (BC pilot); Power 2022 / Nanda 2023 (more steps for small data, abs).
- Expected effect: +2 to +6.
- Cost: 2-4x fine-tune time.
- Risk: harm on skills; overfit.
- Trials: #2 KEPT: 48 visits (3x updates) at batch 64: screen +10.3 (52.3, 52.7), fresh +1.5; sq_plus 43, double_add 27 on s200. Harm 0.6. More training is the lever; next scale it at big batch (H14).

## H4 - Leave-one-out prompts   [status: untried]
- Idea: from each found (question, program), make prompts where each shown pair in turn becomes the query and the program's answer for the original query becomes a shown pair.
- Mechanism: 4 prompts per question from its own numbers; cheaper and closer to the pool's input distribution than H1.
- Source: Akyurek 2024 (2411.07279).
- Expected effect: +2 to +8.
- Cost: negligible to build.
- Risk: subsumed by H1.
- Trials:

## H5 - Stack memory sleep on the fine-tuned model   [status: untried]
- Idea: after the fine-tune, add arm M's notebook (W + C notes) on top.
- Mechanism: the notebook recalls exact programs for repeated shapes (square, last_digit) and costs ~1-2 TF.
- Source: local (memory sleep +31 alone).
- Expected effect: -2 to +4 (crowding risk seen in MC).
- Cost: ~2 TF, a minute.
- Risk: notes override correct weights.
- Trials:

## H6 - Second night (expert iteration round 2)   [status: untried]
- Idea: sample 32 tries per still-unsolved pool question from the fine-tuned model, keep the fitting ones, fine-tune again.
- Mechanism: STaR / ReST-EM / CodeIt rounds.
- Source: STaR (2203.14465), ReST-EM (2312.06585), CodeIt; Haluptzok: round 2 pays less.
- Expected effect: +2 to +6.
- Cost: ~25 TF sampling + a fine-tune.
- Risk: little new beyond chain search, which already covers every pool question.
- Trials:

## H7 - Replay ratio and learning-rate schedule   [status: untried]
- Idea: cosine decay to 0; record share 0.5 -> 0.75 of each batch.
- Mechanism: decay sharpened the planner 83 -> 98% on the bench; more record rows per update.
- Source: project bench recipe (CRDC, cosine).
- Expected effect: +1 to +5.
- Cost: none.
- Risk: harm guard.
- Trials:

## H8 - Mutation dreams from found programs   [status: untried]
- Idea: mutate found programs (swap an op or an operand pointer, esp. in x-independent steps), keep behaviour-distinct runnable ones, replay them as extra prompts.
- Mechanism: widens which constants/compositions the model has practised.
- Source: CodeIt mutation; DreamCoder fantasies.
- Expected effect: 0 to +6.
- Cost: CPU; extra training rows.
- Risk: mismatch, dilution.
- Trials:

## H9 - Support filter for chain records   [status: untried]
- Idea: keep a chain program only if it fits at least 2 pool questions (cross-question support), or weight records by support.
- Mechanism: spurious fits to 3 points are unlikely to fit other questions.
- Source: angle-2 Step 0 (untested); Lee 2025 filtering.
- Expected effect: 0 to +3.
- Cost: CPU.
- Risk: drops rare rules (each affine rule is in the pool ~4 times).
- Trials:

## H10 - Generic-prior dreams   [status: untried]
- Idea: random programs over all ops with flattened length / x-dependence, run on C2-format inputs, mixed into training.
- Mechanism: amortised rule inference from a broad prior.
- Source: DeepCoder, RobustFill, Shin 2019.
- Expected effect: -3 to +8.
- Cost: CPU + training.
- Risk: distribution mismatch (BUSTLE); must not weight toward held-out shapes.
- Trials:

## H11 - Hindsight relabelling of failed tries   [status: untried]
- Idea: resample tries; every runnable x-dependent try becomes a record for a prompt rewritten with its own outputs.
- Mechanism: CodeIt / SOAR relabelling.
- Source: CodeIt, SOAR.
- Expected effect: 0 to +4.
- Cost: 25 TF sampling.
- Risk: C2b's H arm was weak.
- Trials:

## H12 - Bold: replay-only schedule from scratch of the sleep   [status: untried]
- Idea: two-stage sleep: stage 1 trains only on replayed prompts of found programs (H1) at high lr, stage 2 short consolidation with skills replay.
- Mechanism: separates learning the rules from protecting old skills.
- Source: CLS interleaving (McClelland 1995), latent replay.
- Expected effect: unknown, maybe large.
- Cost: as H1.
- Risk: harm in stage 1 not fully repaired.
- Trials:

## H13 - Blind-search records for the pool   [status: untried]
- Idea: for each pool question, a breadth-first search over x and the constants (no notes, no model) finds the shortest program that fits its 3 examples; train on those instead of (or besides) chain records.
- Mechanism: covers questions the chain library cannot express, and BFS order gives one consistent (shortest) construction per rule.
- Source: local (fast-sleep research: blind search fits 60% of missed pool questions at 5k states; 94.9% of DEV at 50k); DreamCoder wake search.
- Expected effect: +2 to +8 on top of replay, mostly via consistency.
- Cost: CPU search seconds to minutes (integer ops, about zero FLOPs).
- Risk: wrong-but-fitting short programs (mod/min/max tricks).
- Trials:

## H14 - Much more training at big batch   [status: KEPT, trial 3]
- Idea: with the reader place ids pre-filled (m/fast.py), a batch-1024 update costs about 0.7 s under the counter; spend 1,000-3,000 TF of updates instead of about 40-350.
- Mechanism: the gold-key ceiling at 16 visits is only about 45%, so job 6's budget is far too small to learn the constant-building rules.
- Source: local (ceiling reference), scaling of supervised program induction (RobustFill).
- Expected effect: large if the rules are learnable at all by this model.
- Cost: minutes per seed.
- Risk: skills harm (keep half-batch replay); overfit to found programs.
- Trials: #6 KEPT (tune): 80 visits/record (2x updates, ~2,400 TF): screen 72.3 / 69.1, fresh 70.7 and one more (+7.0); incumbent 72.7. double_add 76-80, sq_plus 73-78, affine 12-13. #3 KEPT (bold): per-record replay k=3 + batch 1024, 40 visits/record, ~1,200 TF. Screen 66.4 / 62.9, fresh seeds 64.5 and one more (+21.9). sq_plus 69, double_add 55-67, affine still 6, harm <= 0.3. Pool check (design-time, pool key): chain records are 100% right on every kind; affine has 48 distinct programs over 202 records, so each affine rule is seen far less than sq_plus/double_add's 7.
