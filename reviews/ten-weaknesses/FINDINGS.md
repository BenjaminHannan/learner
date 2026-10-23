# Ten weaknesses in premonition v1 (audit 2026-10-23)

Multi-agent audit: 6 lens finders (32 candidates) -> merge (14) -> one adversarial skeptic each (11 survived, 3 refuted) -> ranked. Status labels: shown / suggested / untested. Excludes weaknesses owned by other threads (bridge, loops, multi-step kinds, held-out gap, show-your-work). Sealed test never opened.

## 1. Comparison questions (Q13 compare_count) can be answered by always picking the first place named  [shown, impact 4/10, cost cheap]

In village compare_count questions (Q13, 'more X at A or at B?'), the generator draws the first-named place from places believed to hold that kind and the second from all places, and every template prints the first slot first. So among answerable Q13 questions the right answer is the first-named place about 96-98% of the time (dev 118/121, validation 227/236, train sample 71/77). Q13 is 4.7% of dev questions and 9.1% of validation questions, and D trains on it and is scored on it. Only the leak report drops it. Compared with a fair 50/50 two-way question, the most this shortcut can add is about 2.3 points of D dev accuracy and 4.4 of validation accuracy. How much D actually uses it is not known, because no per-qtype results exist and the FULL weights were not kept. It also means the W1 'best no-learning baseline' (global majority, 8.9%) leaves out a free heuristic worth about 4.6 points on dev and 8.7 on validation.

**Evidence**
- learnlab/village/scheduler.py:599 `at = sorted({b for o in mine if (b := believed(o))}) or pids`; :605 place=rng.choice(at), place2=rng.choice(pids), never swapped
- learnlab/village/render.py:145-146 and learnlab/patterns.py:410: every compare_count template has {place} before {place2}
- learnlab/village/stream.py:28,148 and learnlab/step1.py:1979-1987: Q13 is dropped only from to_qa_examples and the leak report; premonition/data.py reads every question via step1.read_questions (step1.py:260) with no qtype filter
- design/v1/results2/full/final_dev.json: d_dev.questions=42653 (= all questions in 5,000 dev visits); baseline_dev.best=0.0895 (global majority only); no per-qtype breakdown
- Regenerated with learnlab.village.shards.render_range, seed 0: dev 95000-95299 has 121/2571 Q13 (4.7%), 118 first-named and 3 second-named; validation 0-299 has 236/2597 Q13 (9.1%), 227 first-named and 9 second-named; train 0-149 has 77 Q13, 71 first-named
- Q13 depth, dev {2:27, 3:94}; validation {2:29, 3:115, 4:69, 5:20, 6:3}
- design/v1/KNOWN_ISSUES.md does not mention this

**Fix:** Village model only. In scheduler.py:605, choose a = rng.choice(at) and b = rng.choice(pids) as now. Then swap them using a separate derived RNG, e.g. random.Random(f"{visit_seed}:cmp:{kind}").random() < 0.5, so the main rng stream is not touched and every other question in every visit stays byte-identical. Emit place=a, place2=b after the swap. In the same change, add a 'first-named place on Q13, global majority otherwise' heuristic to v1/baselines.py. Also report D accuracy with and without Q13, and Q13 accuracy split by whether the answer was named first or second, in final_dev.json.

**Pass mark (fixed in advance):** Fixed in advance. On regenerated dev visits 95000-95299 and validation 0-299, the first-named share of answerable Q13 questions is between 40% and 60% in each split (n is about 120 and 236; a binomial at 50% stays inside this band with more than 95% probability). All non-Q13 question records (text, answer, depth) are byte-identical to the pre-fix generator for those visits. The new heuristic baseline on pre-fix data scores at least 4 points above the global-majority baseline on dev; this checks the reasoning behind the fix. After the fix, that heuristic's Q13 gain over global majority on dev is under 1.5 points.

**Would prove it wrong:** The fix is wrong if the first-named share after the fix falls outside 40-60%, or if non-Q13 records change. Either result means the swap leaked into the main rng or the answer is set somewhere other than slot order. The claim that the shortcut inflates D is wrong if a D retrained on the rebuilt data keeps the same Q13 accuracy on both first-named and second-named answers (within 3 points of the old overall Q13 accuracy). That would mean D was counting, not using position.

**Overlap:** none (it touches (d) only in that it changes what the validation number means)

## 2. Plan questions (Q12 plan_get) are scored by exact string match only, against the oracle's and project's own rule  [shown, impact 3/10, cost cheap]

v1's D scorer (premonition/train.py judge, lines 605-607, reached by v1/run.py final_eval through validation_hook, and also by v1/sealed_read.py) marks Q12 plan answers right only on an exact string match. The project's rule, learnlab/step1.py:22-23 and oracle.py:38-39, says any plan check_plan accepts is correct, and the project's other evaluator (train.py:859) follows that rule. So a working plan that is not the canonical string, for example one with a redundant 'go to <current place>', counts as wrong in v1. Q12 is about 13% of validation questions (68/527 in a 60-visit regeneration; second to Q4, not the largest type) and about 7% of dev. The error only lowers v1's numbers, and they are not directly comparable to Trainer.evaluate results. How much accuracy it costs is unmeasured, because no per-question predictions or weights were kept.

**Evidence**
- premonition/train.py:605-607 judge: correct.append(step1.exact_match(said, expected)); no plan path
- premonition/train.py:640 validate -> judge; train.py:693 validation_hook wraps validate
- v1/run.py:31 imports validation_hook; run.py:170,174 compute d_{dev,validation} accuracy and bridge_off_accuracy with it
- v1/sealed_read.py:33,52 uses the same validation_hook
- premonition/train.py:849,859: other evaluator: correct = exact or (plan is not None and bool(prediction) and step1.plan_works(plan, prediction))
- learnlab/step1.py:22-23 and learnlab/village/oracle.py:38-39: any plan check_plan accepts is correct; oracle truth for q.plan_get returns None ('any working plan is right')
- oracle.py:842-844 go() skips 'go to' when person_at(person)==place; oracle.py check_plan: a go to the current place is ok (no-op)
- tests/test_learnlab_step1.py:493 asserts 'go to {here}, ' + answer works
- Regenerated 60 validation visits (seed 0, scratchpad): Q12 68/527 = 12.9%; Q4 89 is larger, so Q12 is not the largest type
- design/v1/results2/full/final_dev.json: only aggregate accuracy (dev 42653 q, validation 8675 q); no per-qtype or per-question predictions, so the size of the effect cannot be computed

**Fix:** Make validation_hook/validate/judge take an optional plans mapping (question index in the cache -> (world, person, item)), built with step1.load_oracle on the split dir (the same source Trainer.evaluate uses). In judge, for Q12 rows, set correct = exact or (plan is not None and bool(said) and step1.plan_works(plan, said)). Return both 'accuracy_exact' and 'accuracy' (plan-checked), plus Q12-only counts for each, and have v1/run.py final_eval and v1/sealed_read.py pass the plans and write both numbers into final_dev.json.

**Pass mark (fixed in advance):** Fixed in advance. (1) Unit test: judge with plans counts a Q12 prediction 'go to {here}, {canonical}' as correct and 'not told' as wrong. With plans=None, the scores match today's judge on every question. (2) On the next FULL checkpoint, plan-checked accuracy >= exact-only on dev and on validation. On the same predictions, per-question correctness agrees 100% with Trainer.evaluate's 'correct' field.

**Would prove it wrong:** On the next checkpoint, if plan-checked minus exact-only Q12 accuracy on validation is under 1 point (under about 0.13 points overall), the bug is real but does not matter and explains none of the dev/validation gap. If plan-checked is ever below exact-only, or the plan path accepts a plan that check_plan rejects, the fix is wrong.

**Overlap:** Touches (d) as a measurement artefact inside the dev/validation gap, but it is a separate scorer bug with its own fix.

## 3. The W1 baseline is too weak: answers chosen from the question wording alone (per-type majority) already clear the W1 mark  [shown, impact 4/10, cost cheap]

The W1 baseline in v1/baselines.py answers every question with the same answer (' no', 8.95% on dev), so the W1 dev mark is 18.95%. A rule that never reads the story and gives each question bank its most common train answer scores about 20-21% on dev. I reproduced 20.1% on 300 regenerated dev visits, fitting on just 400 train visits. That already beats the mark. Every gold-phase checkpoint from step 1200 to 3600 (21-25%) and the bridge-off lesion (26.1%) also pass W1, though none of them does much better than knowing the question type. FULL and FLOOR still pass under any sensible baseline, so the decision is unchanged. But the reported 'W1 PASS' tells us almost nothing, and the sealed threshold (sealed_read.py:54) inherits the same weak mark. The '+4 to 5 points' figure for adding first-named place on Q13 came from a finder. I did not check it.

**Evidence**
- v1/baselines.py:15-23 - only majority_train/majority_dev over whole answer tuples; best = max of the two (one constant answer)
- design/v1/results2/full/final_dev.json - baseline_dev.best 0.08949, answer ids [828,2], n_questions 42653; W1_dev_threshold 0.18949; d_dev.bridge_off_accuracy 0.2608
- V1_SPEC.md:17 - 'W1: sealed main-task accuracy at least 10 points above the best no-learning baseline'
- v1/sealed_read.py:54 - dev_base = final_dev.json baseline_dev.best feeds W1_threshold for the sealed read
- My own CPU check: fitted on train visits 0-399 (3,478 q), scored on dev visits 95000-95299 (2,571 q): global majority 7.9%, per-bank majority 20.1%
- Per-bank dev hit rates from my check: count_held 0.56, yn_in 0.52, yn_has 0.50, what_if 0.47, yn_at 0.45, count_at 0.29, direction 0.25, in_container 0.24
- results2/full/dev_evals.jsonl - steps 1200-3600 accuracy 0.252/0.218/0.221/0.250/0.207 (all above 18.95%); D only moves above the prior at step 4200 (0.591)
- premonition/slices.py:80-81,246 - question tags already carry qtype and bank by question id, so a per-bank baseline can be joined to the cache without regenerating anything

**Fix:** Add a `majority_per_bank` rule to v1/baselines.py. Group the train cache by bank (bank looked up by question id from premonition/slices.py tags or the shard jsonl), take each bank's most common answer tuple, and score it on the scored cache. Fall back to the global majority for banks never seen in train. Set baselines()['best'] to the max of majority_train, majority_dev and majority_per_bank. Also emit a per-bank table of D accuracy minus this baseline. Recompute on the existing dev cache, then report the result in REPORT-V1/KNOWN_ISSUES as a disclosed limitation of the frozen v1 mark. Do not change the v1 verdict after the fact. Use the new baseline for the next run's W1.

**Pass mark (fixed in advance):** Fixed in advance. On the real v1 dev cache (42,653 questions), per-bank train majority scores at least 18.95%. That confirms the step-1200 checkpoints and the bridge-off lesion beat the current mark only through the question-type prior. The new W1 dev mark (per-bank best + 10) is then at least 28.95%. Under it, bridge-off (26.1%) and step 1200 (25.2%) fail, and FULL (80.1%) and FLOOR still pass.

**Would prove it wrong:** Per-bank majority on the real dev cache comes out below 15%. That would mean the pointer-id answer encoding or the cache's question set differs from the regenerated strings enough that the question-type prior is actually weak. The current mark would then be roughly adequate.

**Overlap:** touches (a): the bridge-off 26% matches the question-only prior. The mechanism (a weak baseline) is separate and separately fixable

## 4. W2 (creative) has no no-learning baseline; a two-rule lookup (39.8%) and a blind program search (73.8%) both beat the model (34.8%)  [shown, impact 4/10, cost cheap]

W2 is a flat 20% first-try mark with no baseline term, unlike W1. On creative dev, the single input-blind program "answer q*q" already scores 19.92% (51/256), essentially at the mark. A no-check rule (outputs < 10 -> x%10, else x*x) scores 39.8%. The model's 34.8% comes almost entirely from the two one-step, parameter-free kinds. It is not below a fair matched baseline: blind BFS with one candidate scores 0%, and needs about 20 checked candidates to reach 39.1%. The 73.8% figure needs 6,000 checked candidates, so it is not a fair comparison. The model does tell square from last_digit, which no fixed program can. So "W2 PASS" shows only that the model chooses well among one-step programs, which is far weaker than "few-shot rule inference on held-out kinds". The underlying multi-step failure is owned item (c). The distinct weakness is that the W2 mark cannot tell real inference from a trivial solver.

**Evidence**
- design/v1/V1_SPEC.md:18 W2 = 'creative at least 20% first-try on held-out puzzle kinds'; no baseline term (W1 at line 17 is baseline + 10)
- v1/run.py:181 W1_dev_threshold = base['best'] + 0.10; v1/run.py:191 W2_dev_pass = c['first_try'] >= 0.20
- Re-run on creative/data/c2/dev.jsonl (n=256: affine 52, other kinds 51 each): constant program q*q = 51/256 = 0.1992; constant q%10 = 0.1992
- Same dev: two-rule lookup checked against examples = 0.3984; no-check rule 'max(ys)<10 -> x%10 else x*x' = 0.3984
- creative/blind_baseline.search_fits on dev, first fit right by budget: 1 -> 0.0, 5 -> 0.199, 20 -> 0.391, 100 -> 0.410, 1000 -> 0.582, 6000 -> 0.738 (double_add 1.0, sq_plus 0.627, affine 0.115)
- creative/c2_pilot.py:27-42 the model's first_try is one greedy program; right = it reproduces the examples and matches the key (a single candidate, not a search)
- design/v1/results2/full/final_dev.json creative_dev first_try 0.34765625, by_kind last_digit 0.980, square 0.725, others <= 0.02; floor 0.33984375
- creative/c2b.py:339-348 the blind baseline was run only on C2b's sealed test as report-only; design/v1 never computes it on dev
- design/v1/V1_PARAMS.md:41 W2 was calibrated as 'about half of C2b's 39.29%' and '36x the no-sleep 0.55%', i.e. against the project's own earlier results, not against a trivial solver

**Fix:** In v1/run.py final_eval, add creative_baselines(dev_rows), a CPU-only function that needs no weights, and write its output into final_dev.json. It computes three baselines on creative dev:
(a) best_fixed_program: the best single input-blind program among all 1-step blind-BFS candidates. Each is applied to the query alone, and the max is taken over candidates (currently 19.92%).
(b) blind first-fit right at budgets 1, 4 and 32, from creative/blind_baseline.search_fits.
(c) the same three numbers on the parameterised kinds only (affine, sq_plus, double_add; n=154).
Then redefine W2-dev, frozen in a spec amendment before the next run, as
first_try >= max(best_fixed_program, blind_first_fit@1) + 0.10, which is 29.9% today.
Also report the model's reach@4 and reach@32 next to blind @4 and @32, and the gap per kind. That last report is only a comparison and does not decide anything. Change nothing else.

**Pass mark (fixed in advance):** Fixed now:
- On a fresh checkout, creative_baselines(dev) reproduces best_fixed_program = 0.1992 and blind first-fit@1 = 0.0, @4 = 0.0, @32 = 0.391 (±0 points: it is deterministic).
- The amended W2-dev threshold is written in final_dev.json as 0.2992 before any creative stage starts.
- The next FULL run counts as W2 PASS only if its creative dev first_try is >= 0.2992.
- On top of that, a 'rule-inference' claim may be made only if first_try on the parameterised kinds is at least 10 points above blind first-fit@1 on those kinds (currently 0%).

**Would prove it wrong:** Any of these shows the fix or the claim is wrong:
- creative_baselines gives different numbers on two runs, which would mean it is not deterministic.
- The best single input-blind program scores far below 20% on dev, which would mean the existing 20% mark already had a 10-point margin.
- The re-run model's correct answers on the one-step kinds are not concentrated on square and last_digit, for example if parameterised-kind first_try is >= 10%. Then the current W2 would already reflect multi-step inference, and the baseline would change no decision.

**Overlap:** partly (c): multi-step kinds score near 0. Distinct: the mark has no baseline, so it is unsound even if (c) were fixed. Related to KNOWN_ISSUES 7 but distinct.

## 5. D's LR stays at 1e-3 to the last step (no decay, no weight averaging, no checkpoint choice), so the reported number is a draw from a ~7-point band  [shown, impact 5/10, cost medium]

D (village model) trains at a constant lr of 1e-3 after a 100-step warmup, for both the Muon and AdamW groups, to the last step. There is no decay, no weight averaging and no checkpoint choice, and the reported FULL number is the raw step-12000 snapshot. On the fixed 4,336-question dev subset, FULL dev accuracy over steps 6000-12000 jitters with SD 2.2-2.4 points even after the trend is removed (jumps of +-4 points between neighbouring evals; binomial SD about 0.6), while dev loss falls steadily. So the reported 80.1% is one draw from roughly a 76-84 band: the last-5-eval mean is 81.4 +- 1.9. FLOOR is still trending upward (last-5 SD 0.9) rather than swinging, so the instability is mainly a FULL (Muon) problem. D5's direction (FULL > FLOOR by >= 10 points at every eval after 4200) holds. The 11.7-point size, and any re-run's pass or fail against fixed dev marks, depend on which snapshot is taken.

**Evidence**
- learnlab/train.py:99-101 lr_at = lr * min(1,(step+1)/warmup): no decay
- premonition/train.py:291-292 sets every param group's lr from lr_at each step; v1/dtrain.py:60-74 (MuonAdamW) does not override lr_at
- v1/run.py:39-40 LR=1e-3, WARMUP=100; v1/run.py:271 mini_train_config(lr=LR, warmup_steps=WARMUP); v1/run.py:377-378 save_final at trainer.step == a.steps
- design/v1/V1_PARAMS.md:31 'lr 1e-3 with 100 warmup steps then constant'
- v1/run.py:140-142 eval subset = first n dev visits (fixed); dev_evals.jsonl questions=4336
- results2/full/dev_evals.jsonl steps 6000-12000 acc: 76.4,78.1,82.5,80.8,76.8,79.8,83.2,83.6,79.4,81.0,79.9; sample SD 2.43, detrended SD 2.22, slope +0.49/1k; last-5 mean 81.4 +- 1.9
- results2/full/dev_evals.jsonl dev_loss 1.032 (6000) -> 0.964 (12000), nearly monotone
- results2/floor/dev_evals.jsonl same window: slope +1.65/1k, detrended SD 1.88, last-5 mean 68.0 +- 0.88 (the claimed 3.6 SD is mostly trend)
- v1/decide.py:24-25 D5 reads only final_dev.json of each arm
- custom_io/train.py:14-21 existing warmup+cosine-to-10% lr_at

**Fix:** Override lr_at in v1/dtrain.py StepTrainer with warmup-stable-decay, using total_steps (already stored at dtrain.py:72): lr = base*(step+1)/warmup during warmup; base until 80% of total_steps; then linear down to 0.02*base at total_steps. Apply it to all param groups (Muon and AdamW alike) through the existing premonition/train.py:291 loop, and record the schedule in V1_PARAMS.md. Change nothing else: no EMA, same seed, same data and curriculum. Also, starting now and at no cost, report the last-5-eval mean +- SD next to every final D dev number (FULL 81.4 +- 1.9, FLOOR 68.0 +- 0.9 from existing files).

**Pass mark (fixed in advance):** Fixed in advance, for the FULL arm re-run with WSD (village D only, dev only, sealed test untouched): (1) SD of the 4,336-question subset accuracy over the last 4 evals (steps 10200-12000, all inside the decay phase) < 1.0 point; (2) final full-dev accuracy (final_dev.json, 42,653 questions) >= 81.4%, the current run's last-5 subset mean; (3) validation accuracy not below 44.7% - 1.0.

**Would prove it wrong:** Final full-dev accuracy <= 80.1%, or the SD over the last 4 evals stays > 2.0 points during the decay. Either would show that the jitter does not come from the constant lr (more likely from halting, item b, or the bridge EMA state, item a), and that the schedule does not help.

**Overlap:** Touches (b) only indirectly (swings move with loops_mean, so halting is probably the part that wobbles); the fix is a separate recipe change.

## 6. Final and periodic evals throw away diagnostics validate() already computes (by-depth, gold-card accuracy, halt/ask, slices), no per-question or per-type record is kept, and creative per-item results are dropped  [shown, impact 5/10, cost cheap]

The village D evals (final and periodic) compute but discard validate()'s by_depth, accuracy_gold_cards/own_minus_gold_cards, halt_rate, asked_rate, gold_any_at_4, random_recall_at_4 and card stats. final_eval pays for the gold-card pass and then drops it. No slice tags are ever passed, so slices is always empty. No per-question record (question_id, visit_id, correct, loops) is saved, so per-depth, per-qtype and paired or visit-clustered statistics cannot be rebuilt for this run, now that the weights are gone. The creative card experiment's dev_report drops per_q_right, so FULL-vs-FLOOR and bridge-on/off creative differences (n=256) have no paired test or interval. The 'within noise' claim in REPORT-V1 is unquantified. The periodic dev_loss is teacher-mode and did not track own-mode accuracy (plateau 0.21-0.25 at steps 1200-3600 while dev_loss fell; late swings of ±4 pt while dev_loss moved 0.04). losses.jsonl was produced and probably shipped in out.tar.gz but was not committed to results2. Weight loss is a separate, known issue.

**Evidence**
- v1/run.py:170-176: final_eval keeps {accuracy, questions, gold_recall_at_4, loops_mean} + bridge_off_accuracy from validate()
- premonition/train.py:620-683: validate(gold_cards=True default) computes by_depth (668), halt_rate, slices, accuracy_gold_cards/own_minus_gold_cards/loops_mean_gold_cards (673-676), gold_any_at_4, random_recall_at_4, asked_rate, cards (678-682)
- v1/run.py:286-293: periodic evaluate keeps accuracy, questions, loops_mean, gold_recall_at_4, dev_loss only
- v1/run.py:140-143: make_eval_batches calls pdata.collate without slices; VisitCache.tags (premonition/data.py:212) unused in v1
- design/v1/results2/full/final_dev.json: d_dev/d_validation have only 5 keys; grep of results2 finds no by_depth/accuracy_gold_cards/slices
- design/v1/results2/full/dev_evals.jsonl: steps 1200-3600 acc 0.252,0.218,0.221,0.250,0.207 while dev_loss 1.354->1.112; step 4200 acc 0.591; late acc 0.768/0.832/0.836/0.794 with dev_loss 1.002-0.978
- v1/run.py:127-137: dev_loss uses mode='teacher', p_own=0.0
- v1/creative_sleep.py:161-164: dev_report uses g['per_q_right'] for by_kind but returns only first_try/fits/n/by_kind; creative/c2_pilot.py:45 boot() not called from v1
- v1/sealed_read.py:57: out holds only village_test_accuracy and question count plus W flags
- design/v1/REPORT-V1.md:25: '+0.8 points creative (within noise, n=256)' with no interval
- Correction: v1/rent.py:73 out.tar.gz excludes only wake-ckpt and *.pt, so losses.jsonl was shipped but not committed to results2; D-final.pt is in ckpt.tar.gz (rent.py:75), loss covered by the known weights issue
- Correction: the cache keeps question_ids and visit_ids (premonition/data.py header), so qtype is recoverable by a join; per-question predictions are what is missing

**Fix:** One reporting change across both experiments, no training change.

Village D:
- In v1/run.py final_eval and evaluate, store the whole validate() dict, minus the bulky 'cards' summary or with it kept, under d_{split} and d_{split}_bridge_off.
- Add a per_question=True option to validate that returns per-question rows (question_id, visit_id, depth, correct, loops, halted, asked, correct_gold_cards). Write them to out/per_question_{split}_{bridge}.jsonl.
- Pass VisitCache.tags slices built from shard qtype/bank in make_eval_batches.

Creative cards:
- Make creative_sleep.dev_report return per_q_right with row ids and kinds.
- Add to v1/decide.py a Wilson interval for each accuracy, a McNemar test for each paired bridge-on/off and FULL/FLOOR difference, and a visit-clustered bootstrap for village D.

Also:
- Commit losses.jsonl into results2 when a run is curated.
- Log an own-mode dev loss beside the teacher-mode one.

**Pass mark (fixed in advance):** These conditions are fixed before the next run.
- Its final_dev.json has by_depth, accuracy_gold_cards, halt_rate and asked_rate for d_dev and d_validation in both bridge states.
- Every dev_evals.jsonl line has by_depth and accuracy_gold_cards.
- Each per_question_*.jsonl has exactly `questions` rows, and its mean(correct) equals the reported accuracy to the last bit, in all four split×bridge files.
- creative_dev.per_q_right has length 256 and its mean equals first_try exactly.
- decide.py prints a 95% interval for every reported difference.
- Fit check on the current code: validate() on a dev subset run twice gives identical per-question rows.

**Would prove it wrong:** The fix fails if any of these happen.
- A per-question file's mean differs from the reported accuracy, or its row count differs from `questions`. That would mean the saved records are not what was scored.
- by_depth counts do not sum to `questions`.
- Keeping the extra fields changes the reported accuracy at all. The gold-card pass and the recorder must not touch own-mode answers.

The claim that the weakness matters would be undercut if the visit-clustered bootstrap interval for dev accuracy turns out no wider than the binomial one. Clustering would then not matter.

**Overlap:** Supplies evidence for (a), (b) and (d) (the lost validation by_depth is (d)'s direct evidence), but the defect and fix are separate reporting changes.

## 7. Training-time evals never score the held-out validation split, and the dev eval subset is the first 512 visits rather than a random sample  [shown, impact 4/10, cost cheap]

For the village model D, the periodic evals in v1/run.py:282-293 score only 512 in-distribution DEV visits. The held-out validation split (1,000 visits, held out by names, templates, styles and families) is loaded at startup but scored only once, at the end (run.py:167-175). Over about 6.1 epochs, the logs therefore cannot show whether validation accuracy (44.7% at the end) rose, plateaued or fell while dev went flat at about 80% after step 6600 and dev loss kept falling. The step budget and schedule were set without any held-out signal. The secondary claim, that taking the first 512 dev visits instead of a random sample biases the dev curve, is negligible: the subset gave 79.9% against 80.1% on the full dev set at step 12000.

**Evidence**
- v1/run.py:45 DEV_EVAL_VISITS = 512; run.py:282-283 eval_batches/hook are built from data.dev only
- v1/run.py:285-293 evaluate() returns dev accuracy/questions/loops/gold_recall/dev_loss; no validation
- v1/run.py:167-175 data.validation is used only in final_eval
- v1/dtrain.py open_data loads the train, dev and validation caches at startup (validation is already in memory during training)
- v1/run.py:140-143 make_eval_batches: chosen = range(min(n_visits, len(cache)))
- results2/full/dev_evals.jsonl: 21 dev-only points; acc 0.764@6000, 0.825@7200, 0.768@8400, 0.836@10200, 0.794@10800, 0.799@12000; dev_loss 1.032 -> 0.964
- results2/full/final_dev.json: d_dev 0.8006 (42,653 q) vs the 512-visit subset 0.7994 at step 12000, so the subset is representative; d_validation 0.4473 (8,675 q) is a single point
- KNOWN_ISSUES.md:19 (item 17): the 48-visit cap gives about 6.1 epochs

**Fix:** In v1/run.py, build a second fixed set of eval batches from all 1,000 data.validation visits next to the dev ones (make_eval_batches(data.validation, len(data.validation), ...)). In evaluate(), run the same validation_hook on it under bridge.frozen_ctx=True and add val_accuracy, val_questions, val_loops_mean and val accuracy by question depth to each dev_evals.jsonl line. Training behaviour does not change: nothing reads these fields and no checkpoint selection uses them. Leave dev at the first 512 visits, since that subset is representative. Record in the run notes that any later budget or checkpoint choice based on this curve makes the validation number a tuned number.

**Pass mark (fixed in advance):** Fixed in advance. The next FULL-config run logs 21 validation points (step 0 plus every 5%), and the last one matches final_dev d_validation to within 0.5 points (same visits, same weights). Rule for reading the curve: smooth with a 3-point moving average. If the smoothed validation peak is at least 3 points above the smoothed final value (mean of the last 3 points) and the peak falls before 75% of steps, later training hurts held-out accuracy, and a shorter or decayed schedule is the next single change to test.

**Would prove it wrong:** The 'later training hurts held-out accuracy' idea is wrong if the smoothed validation curve over the second half (steps 6000-12000) never drops more than 1 point below its running maximum and the last-3 mean is within 1 point of the smoothed peak. Then validation is plateaued or still rising, the budget is not overfitting held-out data, and the gap belongs entirely to (d)'s causes (depth and wording coverage). The monitoring fix itself fails if the last logged validation point differs from final_dev d_validation by more than 0.5 points, which would mean the hook or the bridge freezing is inconsistent.

**Overlap:** (d) owns the gap size and causes; this is a distinct monitoring fix (the held-out curve over training).

## 8. G1's benefit is never measured (no skills retention after sleep, no G1-off control), its KL anchor is the raw parent for all four stages, and A3's dev clause can never fail  [shown, impact 5/10, cost medium]

v1 runs G1 in all four creative sleep stages, at real cost: 17-27% of the loss after the first quarter of each stage, embeddings and LayerNorm frozen (41 tensors), and about 11.6% of Linear directions locked. But v1 never measures whether G1 keeps the skills it exists to keep. The skills baseline (base5) is computed once, on N', and never compared with W1 or W2. C2b's per-night parts/harm check (harm <= 2 points, otherwise stop) was not carried over. final_eval scores no skills. No G1-off control exists. So it is unknown whether G1 buys any retention, and also unknown whether sleep with G1 still damages skills. Separately, A3's dev clause is weak (dev first-try is 0-1.2% at warm-up and N', on n=256) but it can fail: it was false at FULL N' (+1.17 points). The kl_first values do not show a steadily growing distance from the raw anchor.

**Evidence**
- v1/creative_sleep.py:106-107 base5 = fastsleep.skills5(N, skills_data, device) computed once, on N' only
- v1/creative_sleep.py:117-145 night loop: search, records, sleep, save; no evaluate or skills check after W1/W2; :146 complete.json only copies the N' base5
- v1/run.py:159-195 final_eval: D dev/validation, creative dev first-try, bridge-off; no skills5 or harm on any checkpoint
- creative/c2_stuck.py:175 parts = practised reach32 >= parts_min and skills_harm_points <= c2_keep.HARM_MAX (creative/c2_keep.py:24 HARM_MAX = 2.0), stops on failure; creative/c2b.py:376,391 C2b mark 'skills harm <= 2 on every parent'
- grep base5|skills5|harm over design/v1/results2/ and REPORT-V1.md: no matches
- results2/full/creative_train.json phases: frozen_tensors 41, mean_free_share 0.8842-0.8848, kl_share_mean_after_25pct 0.195/0.172/0.269/0.235, kl_max_term W1 35.19; FLOOR W1 kl_max_term 63.07
- V1_PARAMS.md:24,27 G1 on in all four stages in both FLOOR and FULL; no guard-off arm
- Refuting a side claim: results2/full/creative_train.json a3.Nprime dev 0.0 -> 0.01171875 (+1.17 points, so the '< 1 point' clause was FALSE); FLOOR a3 warmup 0 -> 0.0078, Nprime 0.0078 -> 0.0039
- Refuting a side claim: kl_first.kl_term FULL Nprime 2.58, W1 1.89, W2 4.83; FLOOR 0.35, 0.09, 0.73: no steady rise; one 32-row sample per value (v1/g1.py extra_loss)
- design/v1/KNOWN_ISSUES.md:2 and V1_SPEC.md:14: sleep + G1 never run together before v1

**Fix:** Creative module only; D is untouched. First, port C2b's harm measure. Score fastsleep.skills5 (pooled-5 chain families of skills dev/in_dist) on raw B2_s200, N', W1 and W2. Write skills_harm_points = 100*(skills5(raw) - skills5(X)) for each X into final_dev.json and complete.json. Then run the one comparison: a paired G1-off sleep. Start from the same kept N' (re-run sleep only), with the same seed, records search, LR and update counts, and guard=None for night 1 and night 2. Score W2_on and W2_off on the same skills dev rows and the same 256 creative dev rows.

**Pass mark (fixed in advance):** Fixed in advance, with a paired bootstrap over questions. G1 is justified (keep it) if skills_harm(W2_off) - skills_harm(W2_on) >= 2 points, with the 95% interval above 0, AND creative dev first-try(W2_on) >= first-try(W2_off) - 2 points (interval not entirely below -2).

**Would prove it wrong:** This would show that G1 buys nothing, and that its 17-27% loss share and frozen embeddings/LayerNorm are pure cost: skills_harm(W2_off) <= 2 points (C2b's HARM_MAX), i.e. sleep without the guard does not measurably damage skills. Separately, if W2_on harm is above 2 points, G1 is not doing its job even with its cost.

**Overlap:** none of (a)-(e); may contribute to (c). Related to KNOWN_ISSUES 2 and 15.

## 9. G1 as coded is not the L14 'NK30' recipe it cites (G normalisation, diary size, KL weighting, lr)  [shown, impact 3.5/10, cost medium]

G1's K-FAC hard mask is built without per-example normalisation of G (v1/g1.py:140, norm=None). Every recipe it cites uses norm='example': mainbrain NK30 (protect_g 'example') and Far transfer L14 (learn_probe Guarded.measure). In mainbrain, per-example G was the single change that turned a failing lock into a passing one: empirical G at energy 0.99 (arm E) lost 12 of 160 and failed DM3, while per-example G (arm N) lost 4 of 160. So the v1 lock is really "arm E + 30x KL", an untested variant. It is not "as in L14 NK30", and the cited NK30/L14 evidence (old-skill retention, plus KNOWN_ISSUES 2's transfer-blocking HO 9.8) does not carry over to it. The other three points do not stand. The 1,024-row diary is already disclosed (KNOWN_ISSUES 4). The KL composition (plain loss at weight 1 + 30 x KL on 32 rows) matches L14's kl_replay_loss, the recipe g1 cites. The nights' lr 1e-3 is C2b's documented sleep recipe, and L14 used 1e-4, not 3e-4. Whether the mismatch moves v1's creative numbers is unknown, because v1 never measures the creative module's old-skill retention.

**Evidence**
- v1/g1.py:4-5 'hard mask as in L14 "NK30"'; v1/g1.py:140 kf.kfac_stats(cpu, self.diary[:1024], bs=64), no norm argument
- mainbrain/kf.py:150 def kfac_stats(m, rows, bs=64, norm=None, pad_mask=False, ...): the default is empirical G
- mainbrain/constants-kf99n-kl30-lr3e4.json: protect_g 'example'; mainbrain/fullrun.py:106 norm='example' if pg == 'example'
- origin/claude/forgetting-replay-arm:domain/far/learn_probe.py Guarded.measure: self.kf.kfac_stats(self.m, self.diary, norm='example') (L14's lock); training-config line 1873 guard_norm='example'
- learn_probe.py:1632-1660 kl_replay_loss: 'plain loss on the new rows at weight 1 + weight x ... KL, NOT wrap's (n_new/B, n_rep/B) split', which matches g1 + creative/sleep.py:117-122, so sub-claim 3 is refuted against L14
- mainbrain/MARKS-2026-10-10.backup-through-result-30.md:237-245 arm N (per-example G) lost 4/160 and passed; :225-229 arm E (empirical G at 0.99) lost 12/160 and failed DM3; :212-213 free share 0.967 (empirical) vs 0.921 (per-example) at 0.97
- design/v1/results2/full/creative_train.json phases/{warmup,Nprime,W1_sleep,W2_sleep}/guard mean_free_share 0.884-0.885 (empirical G)
- design/v1/results2/full/final_dev.json: no skills/old-skill retention metric for the creative module (only creative_dev and kl_share)
- grep over design/v1, v1, reviews for norm='example'/protect_g/per-example: no hits, so the choice is undocumented
- mainbrain/MARKS-PENDING-2026-10-13.md:85 L14 ran at lr 1e-4 (sub-claim 4's 3e-4 is NK30's fullrun lr, not L14's)

**Fix:** Make one change, in the creative module only: pass norm='example' at v1/g1.py:140 (kf.kfac_stats(cpu, self.diary[:1024], bs=64, norm='example')). Keep everything else as it is (1,024 rows, 30x KL composition, C2b lrs) so that the normalisation is the only thing that differs. Record the change in V1_PARAMS and KNOWN_ISSUES. To judge it, add the measurement v1 is missing: custom_io skills-dev exact-match accuracy of the creative module before (parent B2_s200) and after the full sleep chain (W2.pt). Then run the warm-up -> N' -> W1 -> W2 creative chain twice, norm=None and norm='example', same seed 0, same diary, bridge vector frozen at the FULL run's saved value. The village model D is not touched, retrained or re-scored.

**Pass mark (fixed in advance):** Fixed in advance, on creative dev (n=256) and skills dev:
(a) The skills-dev accuracy drop from parent B2_s200 to W2.pt with norm='example' is at most half of the norm=None drop, or is below 1.0 point when the norm=None drop is itself below 2 points (then report "lock strength does not matter here").
(b) Creative dev first-try with norm='example' is at least 31.8% (no more than 3 points below norm=None's same-seed value, with 34.8% as the reference).

**Would prove it wrong:** The fix is shown wrong if norm='example' gives a skills-dev drop at least as large as norm=None's. It is also shown wrong if norm='example' cuts creative dev first-try by more than 5 points (below about 29.8%) with no retention gain. In that case the stronger lock blocks the creative gain, which is the KNOWN_ISSUES 2 / A3 concern, and the relabel-only route (document G1 as a new empirical-G variant) is the right one.

**Overlap:** none. KNOWN_ISSUES 1 and 4 note the model-family premise and the 1,024 CPU rows, not the norm or KL weighting.

## 10. HALT is trained on 'my answer is right now', with no 'is evidence still missing' term, and it cancels ASK at inference  [suggested, impact 4/10, cost medium]

D's HALT head is trained to predict "every answer token is argmax-correct at this loop" (model.py:812-824). It has no term for whether gold evidence is still unfetched, although have_all is computed right there (model.py:819). Spec revision 9.9 (design/06 line 242) called for rollout-based targets ("halt at the first loop after which more loops no longer turn the answer correct"), and the handoff (line 85) lists them as not done. At inference, D stops at sigmoid(halt) > 0.5. So a confident guess made on partial evidence ends the episode. Masking the final ASK when done is the same in training (model.py:851) and is not a separate bug. Validation uses fewer loops than dev (2.08 vs 2.27) although it needs deeper evidence. That fits the mechanism, but how much accuracy it costs has not been measured.

**Evidence**
- premonition/model.py:812-816: correct = (wrong == 0).float() from teacher-forced argmax
- premonition/model.py:818-820: have_all computed, used only in scale = where(have_all, 1.0, early_ans)
- premonition/model.py:824: halt_terms.append(BCE_with_logits(halt, correct))
- premonition/model.py:957,962: done = (prob > 0.5) | last; fetch masked by (ask <= 0) | done
- premonition/model.py:849-851: in training the last loop also inserts no cards (~going), so the ASK masking is consistent, not a bug
- design/06-premonition-mini-spec.md:242 (revision 9.9): HALT targets were meant to come from own-retrieval rollouts
- design/research/2026-09-18-trainer-handoff.md:85: 'rollout HALT targets (9.9) belong in forward' (never implemented)
- design/06-premonition-mini-spec.md:225: phase 6 pass mark 'loops rise with depth'
- design/v1/results2/full/final_dev.json: loops_mean dev 2.268 vs validation 2.082; gold_recall_at_4 0.762 vs 0.603
- design/v1/results2/full/dev_evals.jsonl: only aggregate loops_mean logged; no halt-rate, step-0 accuracy or by-depth loop counts

**Fix:** Village model (D) only. Step 1, a gate before any retrain: on a retained D checkpoint (floor, or a fresh FULL retrain with the same seed), evaluate dev and validation twice: once with the learned HALT, and once with HALT ignored (run to max_loops, own ASK unchanged). Report accuracy and loop histograms by evidence size and depth. Step 2, the change: at model.py:824, use the target `correct * have_all.float()` when gold is not None, so a told question is labelled "halt" only once all its gold cards (NULL for 'not told') are fetched. Leave everything else the same: inference, weights, seed, steps.

**Pass mark (fixed in advance):** Fixed in advance. Gate: on the baseline model, forced-continue minus learned-HALT accuracy on dev questions with 2 or more gold cards is at least +1.0 point, with the visit-clustered bootstrap lower bound above 0. If not, halting is not costing accuracy and step 2 is skipped. Fix, same seed and steps as FULL: (1) dev accuracy on questions with 2 or more gold cards rises at least 1.5 points (clustered lower bound above 0); (2) validation accuracy rises at least 1.0 point; (3) overall dev accuracy does not fall more than 0.5 points; (4) mean loops rise with gold-card count on dev, monotone over the buckets 1, 2-4 and 5 or more.

**Would prove it wrong:** Any one of these proves the fix wrong. The baseline's forced-continue gain is under 0.5 points, so early halting was not the bottleneck. Or the retrained model's loops rise by 0.3 or more on multi-card questions while their accuracy moves less than 0.5 points; then the missing evidence is not being retrieved, so retrieval (recall 0.60 on validation) or the (b)/(d) threads, not HALT, is the cause. Or overall dev falls more than 0.5 points.

**Overlap:** Sub-cause of (b). Kept because it is a specific, one-line fixable flaw in the HALT target and the HALT/ASK interaction, not loop capacity.

## Dropped
- The teacher phase (5-30% of steps, 3,000 steps) produces no gain on the scored accuracy; all gain arrives after the switch to own mode (suggested only; needs a GPU retrain; likely saves ~20% compute rather than adding accuracy)

## Refuted by the skeptics
- Every held-out creative dev rule is literally in the sleep pool; square and last_digit are one rule each: I re-ran the overlap check myself on creative/data/c2/pool.jsonl (1,024 rows) and dev.jsonl (256 rows), keyed on (kind, params). The numbers are right: 255 of 256 dev rows have their exact rule in the pool. The one miss is a single affine row. Dev's 33 affine rules include 32 that are in the pool; double_add 7/7, sq_plus 7/7, square 1/1, last_digit 1/1. square and last_digit have 205 pool rows eac
- Creative dev both tunes the sleep temperature and judges W2, and the cold-start gate failed for FULL at every temperature and was ignored: The facts in the claim check out, but none of them is a weakness that costs accuracy or makes the reported numbers less trustworthy in a way that matters.

What I confirmed:
(1) v1/creative_sleep.py:103-114 picks T on creative dev. It takes the highest reach32 over T_GRID (creative/c2_pilot.py TEMPS, 8 values) among temperatures that pass sameness. It never reads 'verdict' (grep: the only hit in v
- NULL card is always re-eligible and fills top-k slots at inference, but teacher training never shows NULL to answerable questions: The code facts quoted are right. The conclusion drawn from them is not.

The facts:
- premonition/store.py:96-98 does turn NULL back on after it has been fetched.
- premonition/model.py:956-963 inserts store.top(scores, top_k) at every ASK with no score threshold.
- model.py:883 leaves NULL out of the teacher distractors.
- store.py:157-161 makes NULL gold only for never-told questions.

Why the c

## Implemented on this branch (all default OFF or reporting-only; v1 numbers unchanged)
- #1 Q13 swap: `LEARNLAB_COMPARE_SWAP=1` (learnlab/village/scheduler.py). First-named share dev 97.5% -> 50.4%, validation 96.2% -> 53.0%; all non-Q13 questions byte-identical; flag-off output hash-identical to before.
- #3 per-bank W1 baseline: `baselines(..., banks=, first_named=)` adds `majority_per_bank`, `first_named_q13`, `best_v2` (v1 `best` unchanged). On regenerated strings: per-bank 20.1% dev / 15.3% validation; + Q13 first-named rule 24.7% / 24.0%. Not yet run on the real v1 cache.
- #4 W2 baselines: `v1/creative_baselines.py`, reported in final_dev.json. Dev: best fixed program x*x 19.92%; blind first-fit @1/@4/@32 = 0 / 19.92 / 39.06%; parameterised kinds 0%; proposed W2 mark 29.92%.
- #2 plan-aware Q12 scoring: `premonition/scoring.py`, `--plan-scoring` (off by default; `accuracy` stays exact match).
- #6/#7 eval diagnostics: final eval keeps by_depth, gold-card, halt/ask rates for both bridge states; `--per-question` jsonl; periodic evals also score validation (`--val-every-eval`, on, RNG and bridge state restored) and bridge-off; Wilson/McNemar helpers in v1/decide.py.
- #5 WSD learning-rate schedule: `--lr-schedule wsd` (default `constant`). `scripts/last5_noise.py`: FULL last-5 dev 81.44 +- 1.92, FLOOR 68.04 +- 0.88.
Tests: `pytest v1/tests tests/test_premonition_train.py` 33 passed, 3 skipped (need B2_CKPT/SKILLS_TRAIN); `test_cpu_smoke_on_a_tiny_village` excluded: it fails on budget_ok under machine load on the unmodified base too.
