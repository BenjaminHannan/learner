# Angle 2: augmentation, dreaming and constants (literature pass for C2)

Date 2026-10-07. Papers only: nothing was run, no GPU, no repo file edited. Scope is the small card experiments (B2 model, C2 task). The village model is not discussed.

## How to read this file
- Labels. **shown** = demonstrated in program synthesis with an exact executor. **suggested** = demonstrated in a neighbouring setting (symbolic regression, semantic parsing, language models, RL) with a plausible bridge. **untested** = the paper does not test it, or it is our extrapolation.
- Read depth. **FT** = I opened the full PDF and read the passage around every number quoted. **abs** = abstract only; no numbers quoted from it. Chen 2019 (ICLR, not on arXiv; listing https://iclr.cc/virtual/2019/poster/760) was read through a raw text mirror of the paper, and its Table 3 numbers were checked there. Ellis and Gulwani 2017 (IJCAI, not on arXiv, https://www.ijcai.org/proceedings/2017/227) is abs only.
- Verification. All 41 arXiv ids below were checked against the arXiv API on 2026-10-07 (title, authors, date). None failed.

## Bottom line
1. Re-running a verified program on fresh inputs is the best-supported move (Shin 2019: same programs, new I/O, 0.04-24.30% became 62.78-80.19% on twelve narrow test sets). It adds variety of examples, not new rules. It cannot teach a rule for which no program was ever found.
2. In these papers new (rule, program) pairs come from three generic sources: hindsight relabelling of the model's own samples (CodeIt 49/400 vs 24/400 without), mutation of found programs (CodeIt 17/400 without mutation), or a prior over programs (DreamCoder, DeepCoder, TF-Coder). Each has a documented diversity or mismatch failure (Topic 5).
3. Constants are hard when each value is its own multi-step construction. DeepCoder's net confuses (+1) with (-1) and (/2) with (/3) and (/4). SketchAdapt: a pure neural writer scored 1.1% on a held-out sub-expression, 29.8% when search filled it. In the papers read, constants work through an atomic token, a post-hoc optimiser or test-time search; the one exception (d'Ascoli's float model building out-of-vocabulary constants from a small vocabulary) is only approximate. We allow none of the three today.
4. No paper here goes from near 0 to 70% on a held-out parameterised kind with one greedy try and no search. The nearest, Nye 2020 (no-search synthesis 0.0-13.3% on SCAN splits, 100% with search), points the other way. Treat 70% as a stretch target that probably needs several of the cards below stacked.
5. Two cheap ideas look under-used for us: canonical constant-builders (program aliasing) and feeding executor values back to the controller.

---
## Topic 1. Execution-based augmentation and hindsight relabelling

| Citation | Finding | Mechanism to implement | Relevance here | Label |
|---|---|---|---|---|
| Devlin et al. 2017, RobustFill, arXiv 1703.07469 (FT) | Fresh programs and I/O every minibatch: 256M programs, 1,024M I/O examples seen, 24 h on 2 Titan X; best synthesis model 92% on a real test set vs 34% for the previous best neural one. | Sample program from the DSL (up to 10 expressions); sample inputs meeting executor preconditions; run for outputs; never reuse a batch. | Upper end of the dose scale. We cannot afford 10^8, but the principle is fresh data from few programs. | shown |
| Shin et al. 2019 (ICLR), Synthetic Datasets for Neural Program Synthesis, arXiv 1912.12345 (FT) | Same training programs, new I/O drawn uniformly over salient input variables: on 12 narrow input test sets 62.78-80.19% vs 0.04-24.30% for the baseline; baseline 73.52% falls to 27.9% on a uniform-input test. Models trained on one narrow input distribution score high on it and "usually very low" on others. | Keep programs; resample inputs by rejection so each salient variable is uniform; discard input sets on which the program crashes or misses a branch; sample 1-5 shown examples per minibatch. | Direct template for replay. Warns that replay on a narrow x-range overfits to that range, and that the number of shown examples is a variable to randomise. | shown |
| Butt et al. 2024, CodeIt, arXiv 2402.04858 (FT) | Hindsight relabelling (run a sampled program on the demo inputs, store its realised outputs): ARC eval policy-only 49/400 vs 24/400 without. No mutation 17/400; no priority replay 38/400 (forgetting); one demo only 34/400. | 24 samples per task per iteration at T=0.95; drop syntax errors and slow runs; priority = fraction of demo outputs matched; 19,200 mutated tasks made once from the 400 seeds; each iteration trains 1 epoch on 10,000 items from seeds plus mutants and 90,000 from the buffer; mutation picks a random line and swaps its function or an argument (hyperparameters 0.25/0.5/0.25). | Closest recipe: small data, executor, many cheap rounds. Their ConceptARC appendix: worst on numerical or logic tasks. | shown |
| Pourcel et al. 2025, SOAR, arXiv 2507.14172 (FT) | Relabel every sampled program, keep at most 50 per task: sampling accuracy on ARC-train (Qwen-2.5-Coder-14B, 3k samples) 29.29 (base), 34.67 (correct-only), 36.46 (25 best plus 25 worst programs for diversity). | Rank by accuracy on shown pairs; take 25 top and 25 bottom; fine-tune on (new outputs -> program). | Gives a dose (<=50 per task) and shows wrong programs still teach. | shown |
| Akyurek et al. 2024, test-time training, arXiv 2411.07279 (FT) | Leave-one-out tasks (each shown pair becomes the query, demos permuted) plus invertible augmentations: fine-tuned model 5% -> 29% (about 6x) on 80 ARC tasks. In-context format beats direct I/O training; per-task adapter beats a shared one by 7 of 80 tasks; about 12 h per 100 tasks on one A100. | Build n tasks from n pairs; train with loss on demo outputs too (26% -> 29%). | Leave-one-out on the 3 shown pairs gives 3 labelled queries per verified program for free. Per-task training breaks "one program, no test-time search" and our budget. | suggested (LM, no executor) |
| Hodel 2024, re-ARC, arXiv 2404.07353 (FT) | A hand-written generator plus verifier per ARC task; each makes at least 10,000 unique examples with ranges widened beyond the original. No experiments in the paper. | Sample every free parameter; verify each example with a solver. | The hand-written-generator route is exactly what we may NOT do for held-out kinds. Our generator is the found program plus a generic x-range. | untested (data release; used by 2411.07279 and 2411.02272) |
| Li et al. 2024, BARC, arXiv 2411.02272 (FT) | 100 human seed programs (160 later) remixed by an LLM into 100k-400k executable problems; accuracy grows with synthetic data size but saturates in number of seeds. Authors call the remixes "dream data". | Seed -> LLM description -> retrieval-augmented code -> run, drop non-deterministic or trivial problems. | Confirms many instances per seed help. Needs an LLM to remix; ours must mutate the model's own programs. | shown |
| Gauthier and Urban 2022, integer sequences from scratch, arXiv 2202.11908 (FT) | DSL has only the constants 0, 1, 2, basic operators and loops. Generation 0 solves 993 sequences; generation 1 adds 8,438. Hindsight relabelling "crucial": 187 new solutions at generation 25 vs 160 targeted. Training on the smallest solution rather than a random one gives about 10% more solutions. | Keep the shortest program per target (fixed tie order); relabel failed attempts as solutions for the sequences they produce. | Same constants-from-few-literals problem, with an executor. Source for canonical (shortest) builders. | shown |
| Odena et al. 2020, BUSTLE, arXiv 2007.14381 (FT); Shi et al. 2020, TF-Coder, arXiv 2003.09040 (FT) | Training data from the synthesiser's own enumeration: BUSTLE 1,000 searches x 100 values -> 200k examples, trained on CPU in hours; TF-Coder 20,000 runs -> 39,930,863 examples. | Run bottom-up search on random inputs; pretend any enumerated value is the output; pick a sub-expression as positive, a non-sub-expression as negative (BUSTLE). | Cheap CPU dataset of (outputs -> program) from our executor. TF-Coder notes operations needing complex arguments are rare in such data (reshape 6 thousand vs expand_dims 9 million of 40 million): same fate as multi-step constants. | shown |
| Andrychowicz 2017, HER, arXiv 1707.01495 (abs); Abolafia 2018, priority queue training, arXiv 1801.03526 (abs); Chollet et al. 2024, ARC Prize report, arXiv 2412.04604 (abs) | Origin of relabelling; training on the best programs in a priority queue; survey: top ARC systems used program synthesis plus test-time training. | - | Background only. | suggested |

---
## Topic 2. Synthetic task generation ("dreaming") and the sampling distribution

| Citation | Finding | Mechanism to implement | Relevance here | Label |
|---|---|---|---|---|
| Ellis et al. 2020, DreamCoder, arXiv 2006.08381 (FT) | Recogniser trained 50/50 on replays (found programs) and fantasies (programs sampled from a library prior fitted to found programs); fantasy inputs are drawn from the training tasks. Early dreams are "simple and largely unstructured... limited value"; later ones recombine learned blocks; at fixed library, dreaming raised held-out accuracy (Fig 6 caption). Trains on 100-200 tasks. | Fit a probabilistic grammar to found programs; sample; run on real task inputs; train on the canonical (MAP) solution. | "Dreams from the model's own found programs" is this. Expect little gain while the found set is about 200 programs. | shown |
| Balog et al. 2017, DeepCoder, arXiv 1611.01989 (FT) | Enumerate programs, prune any with a shorter equivalent (same outputs on random inputs); choose inputs by propagating output ranges backwards. | As stated; five I/O pairs per program. | Template for a dedupe-by-behaviour step. | shown |
| Shin et al. 2019, program side (as above) | Training data had been pruned to programs with at least 2 actions; action-only programs scored 16.00-73.06% by length. Adding 20,000 programs per length 1-20 raised them to 20.00-78.12% and cost 1.7 points on the original test (73.52 -> 71.8). | Rejection sampling with acceptance g(s) = (P[X=nu(s)]+eps)^-1 (min_x P[X=x]+eps), on hand-chosen salient variables. | If dreams come from a generic prior, flatten length and number of x-dependent steps instead of keeping the grammar's natural skew. | shown |
| Nye et al. 2020, rule induction, arXiv 2003.05562 (FT) | Meta-trained on rule systems sampled from a meta-grammar: 100% on four SCAN splits with search; without search 0.0, 13.3, 3.5, 0.0. The SCAN grammar lies inside the meta-grammar's support ("SCAN-like"). | Train recogniser on sampled grammars; test-time search checks consistency. | Warning on both counts: the prior quietly contained the test, and search did the heavy lifting. | shown (with search) |
| Lake 2019, meta seq2seq, arXiv 1906.05381 (FT) | Each episode randomly permutes the meanings of 4 primitives (original permutation withheld): 99.95% on SCAN "add jump" vs 0.03% for standard seq2seq. | Episode = support set plus queries under a fresh random mapping. | Forces reading meaning from the prompt, not memory. Built around the test split, so copying it would be hand-building. | suggested (not program synthesis) |
| Andreas 2020, GECA, arXiv 1904.09545 (FT); Jia and Liang 2016, arXiv 1606.03622 (FT) | Recombine fragments seen in similar contexts. GECA cuts SCAN errors by up to 87% (abstract figure); Jia and Liang: GeoQuery 85.0 -> 89.3%, ATIS 76.3 -> 83.3%. | Swap a fragment between two examples that share a context; induce a grammar and sample. | Analogue of swapping x-independent sub-programs between found programs. | suggested (semantic parsing) |
| Garg et al. 2022, arXiv 2208.01066 (FT) | 9.5M-parameter GPT-2-style model (12 layers, 256-d), fresh prompts each of 500k steps, in-context learns 20-d linear functions near least squares; nontrivial with 1k distinct functions, near full with 10k; curriculum (5-d subspace, 11 points, +1 dim and +2 points every 2,000 steps) needed at d=50. | Sample a function from a prior, k points, mask last label. | Number of distinct rules matters for continuous parameters. We have 65 discrete rules, so memorising rules is fine; the open problem is reading which rule. | suggested |
| Muller et al. 2022, PFNs, arXiv 2112.10510 (abs); Le et al. 2017, inference compilation, arXiv 1610.09900 (abs) | Amortised inference learned only from samples of a prior; the prior is the whole design. | - | Names our idea: the controller as an amortised parameter-inference network. | suggested |

---
## Topic 3. Constants, literals and execution states

| Citation | Finding | Mechanism to implement | Relevance here | Label |
|---|---|---|---|---|
| DeepCoder (1611.01989, FT) | Constants are a closed set of atomic lambdas: (+1), (-1), (*2), (/2), (**2), (*3), (/3), (*4), (/4). Confusion analysis: (+1) vs (-1), (/2) vs (/3) vs (/4), and (**2) read as (*). | Predict which lambdas occur; search does the rest. | Even atomic constants are confusable. Ours are not atomic. | shown |
| RobustFill (1703.07469, FT) | 430 program tokens, parameter values among them; string constants are spelled by attending over the I/O characters. | Each parameter value is one output token. | Atomic parameters work; copying from the prompt is closed to us because programs may not read example values. | shown |
| Nye et al. 2019, SketchAdapt, arXiv 1902.06349 (FT) | Trained on 8,000 programs with the 'odd' sub-expression removed: generator only 1.1% on 'odd' (4.5% on 'even'), synthesizer only 0.0%, SketchAdapt 29.8% (34.4% on 'even'). | Sketch with HOLE tokens; fill holes by timed enumeration; learns when to defer. | Closest evidence that a neural writer fails on an unseen part and a hole-filler fixes it. Test-time enumeration is barred here, so the fill must move offline. | shown |
| Shi et al. 2023, ExeDec, arXiv 2307.13883 (FT) | Predict the next execution subgoal (target value per example), then a sub-program reaching it: +7% (RobustFill, 34% fewer failures) and +5% (DeepCoder, 1.28x) over the no-subgoal ablation on five compositional-generalisation tasks. No-subgoal was slightly better on DeepCoder's own distribution and on length generalisation. | SubgoalModel: (I_i, O_i) -> values S_i; SynthesizerModel: (I_i, S_i) -> sub-program; teacher forcing on line-by-line decompositions. | Our slots are execution states. A subgoal head asks "what number should this slot hold for each example". | shown |
| Chen, Liu, Song 2019 (ICLR), Execution-Guided Neural Program Synthesis (text mirror, FT) | Condition on the state after running the partial program: Karel generalisation 71.91% (Bunel MLE) -> 85.08% (execution-guided) -> 92.00% (plus RL and an ensemble of 15 with majority vote). | Training pairs from executing ground-truth program prefixes: (state_k, outputs) -> next segment. | Feeding executor values back to the controller. | shown |
| Zohar and Wolf 2018, PCCoder, arXiv 1809.04682 (FT) | State = values of all variables for every example plus the outputs; predict next statement, operands and which variables to drop; programs more than twice as long as prior work (abstract). | Embed each example's state vector, pool across examples; auxiliary losses. | Our 27 slots are this state. | shown |
| Bunel et al. 2018, arXiv 1805.04276 (FT) | Program aliasing: likelihood on one reference penalises other correct programs. RL on semantic correctness lifts Karel top-1 generalisation 71.91 -> 77.12% (full data) and 12.58 -> 25.28% (small data), while exact match falls (39.94 -> 8.21% for RL_beam). | REINFORCE with +1 if outputs match on held-out examples; beam-level objective. | 7 = 10-2-1 = 2+2+2+1: many builders, one score. Low-data regime is ours. | shown |
| Kamienny et al. 2022, arXiv 2204.10532 (FT); Biggio et al. 2021, arXiv 2106.06427 (FT, method) | Skeleton plus BFGS vs predicting constants as tokens: small constant errors hurt at high precision; refinement from the predicted constants gives a 3x gain in Acc0.001, random initialisation makes it worse. | Constants as numeric tokens; optimiser polishes from the model's guess. | Exactness is the issue (integer constants get no partial credit). Our "optimiser" is offline search. | suggested (symbolic regression) |
| d'Ascoli et al. 2022, arXiv 2201.04600 (FT) | Decoder has integers -10..10 plus a few constants and must write 0.33 as [div,add,mul,3,10,3,mul,10,10]; integer symbolic model 92.7% (<=5 operators) -> 78.4% (<=10); float model 100% (1 operator) -> 10% (10). Operator-count curriculum "did not bring any improvement". | Generator: random trees, constant leaf probability 1/3, fresh data. | The same build-a-constant-from-a-small-vocabulary problem; difficulty grows steeply with operators (our budget is 7 steps). | suggested |
| TF-Coder (2003.09040, FT) | Constants are chosen heuristically (0, 1, -1 plus sizes read from the examples) and given weights. | - | Reading constants off examples is the thing our rules forbid inside the program. | shown |
| Ellis and Gulwani 2017, IJCAI (abs) | A learned bias over program behaviours, trained on abundant unlabelled data, ranks the programs that fit the few examples. | - | Our pool is unlabelled. Fitting 3 pairs does not mean the program is right. | suggested |

---
## Topic 4. Few-shot numeric rule induction in small nets

| Citation | Finding | Mechanism to implement | Relevance here | Label |
|---|---|---|---|---|
| Garg et al. (2208.01066, FT) | See Topic 2: a 9.5M net reads a linear rule from examples with fresh data and a curriculum. | Curriculum on dimension and number of points. | Reading (A,B) from three pairs is the base skill. | suggested |
| d'Ascoli et al. (2201.04600, FT) | OEIS next-term accuracy at 15 terms: numeric 53.1%, symbolic 33.4%. Integers are written in base 10,000, one token per digit. | Fresh random-tree generator. | Small nets infer integer rules from a few values when trained on a broad generator. | suggested |
| Lee et al. 2023, arXiv 2307.03381 (FT) | 10.6M NanoGPT: plain 3-digit addition stalls near 85% at 10,000 samples; reversed output shows a sharp transition between 1,000 and 4,000 samples; intermediate-result scratchpads cut sample needs; models learn length-specific procedures. | Reverse the answer digits; add intermediate steps. | Shows format and visible intermediate results decide whether a small net learns digit arithmetic. | suggested |
| Wallace 2019, arXiv 1909.07940 (abs); Golkar 2023, xVal, arXiv 2310.02989 (abs); Schwartz 2024, NumeroLogic, arXiv 2404.00459 (abs) | Character-level number embeddings are more exact; a continuous number channel helps out-of-distribution; a digit-count prefix tells a causal model the place value early. | Re-tokenise numbers. | Cheap format tests for the prompt reader. | suggested |
| Power 2022, arXiv 2201.02177 (abs); Nanda 2023, arXiv 2301.05217 (abs) | Small transformers on modular arithmetic memorise first and generalise much later; smaller data needs more optimisation steps. | - | Residue-type structure may need long training; budget risk. | suggested |
| Trask 2018, NALU, arXiv 1808.00508 (abs); Madsen 2020, arXiv 2001.05016 (abs) | Units for exact arithmetic extrapolation. | - | Low relevance: our executor already does exact arithmetic. | suggested |

---
## Topic 5. Negative results and distribution mismatch

| Citation | Finding | Relevance here | Label |
|---|---|---|---|
| Shin 2019 (1912.12345, FT) | Narrow-input training collapses off-distribution; baseline 73.52% -> 27.9% on a uniform-input test. | Replay on the pool's x-range alone may overfit to it. | shown |
| BUSTLE (2007.14381, FT) | Random-program training "does come with a risk of poor performance on human-written tasks"; property signatures reduced it in their domain. | Generic-prior dreams need a mismatch check on the real DEV split. | shown |
| Jia and Liang (1606.03622, FT) | CONCAT-2 alone scored 84.6 vs 85.0 with no recombination on GeoQuery; recombination hurt slightly on Overnight without copying. | A single recombination rule can be net-negative. | suggested |
| GECA (1904.09545, FT) | No improvement on SCHOLAR (token overlap with test rose under 1%); works when augmentation raises train-test overlap. | Swapping constants helps only if it creates the unseen pairs. | suggested |
| Lee et al. 2025, arXiv 2502.01612 (FT intro and filtering) | Self-improvement without filtering fails from error accumulation on harder tasks; length filtering and majority voting rescue it. | Fitting 3 shown pairs is a weak filter; use cross-question support (Card 1). | suggested |
| Haluptzok 2023, arXiv 2207.14502 (FT) | Interpreter-verified self-made data gave a large boost over unverified; second iteration helped little; trivial solutions "such as small constants" were filtered out. | Expect round 2 to pay less than round 1. | shown |
| Shumailov 2023, arXiv 2305.17493 (abs) | Training on a model's own samples loses distribution tails. | Dreams only from our own programs shrink the program distribution; executor checks and replay should limit it, untested. | suggested |
| CodeIt (2402.04858, FT) | Without priority replay 38/400 vs 49/400. | Forgetting: keep replay of old skills. | shown |
| ExeDec (2307.13883, FT), d'Ascoli (2201.04600, FT) | Subgoal prediction not uniformly better; operator curriculum no help. | Do not assume auxiliary targets or curricula are free wins. | shown / suggested |
| Berlot-Attwell 2024, arXiv 2410.20274 (abs) | Library reuse was extremely rare in two LLM maths systems. | Reusing found sub-programs may look good without being used. | suggested |

---
## Cross-cutting numbers (dose and overfitting)
- Instances per rule that papers actually used: SOAR at most 50 per task; CodeIt 24 samples per task per round plus about 48 mutants per seed at the start; BARC thousands per seed; re-ARC at least 10,000 available; Garg 1k-10k distinct functions; Lee 1k-4k samples for a phase transition. For 65 rules, 10^2-10^3 prompts per rule (10^4-10^5 total, about 6M tokens per epoch at 60 tokens each, my estimate) sits inside this range.
- Overfitting signs recorded: narrow input ranges (Shin), no replay (CodeIt A3), no filtering (Lee 2025), second rounds (Haluptzok), more seeds without more data per seed (BARC).
- Equivalent programs split probability mass; the score is greedy first try. Canonical shortest programs helped (Gauthier: about 10%; DreamCoder MAP), RL on semantic reward helped in low data (Bunel).

---
## Hypothesis cards for C2 (generic prior or the model's own programs only)
Hand-building rule: any generator, filter, weight or feature that names or favours the five held-out shapes is NOT allowed. Allowed filters: runs without error, output depends on x, not constant, behaviour-distinct, length. Coverage of the 65 rules may be MEASURED afterwards but must not select anything.

**Step 0 (no training, any card): rule support.** For each found program, count how many pool questions its outputs fit (all 3 shown pairs). If the pool is spread evenly over the 65 rules, a real rule should fit about 16 questions (1,024 / 65); a spurious fit should fit few. Keep programs with cross-question support, and use the same test to label more pool questions with the same program. Source: DreamCoder replay plus compression, Ellis and Gulwani 2017, Lee 2025 filtering. Untested.

**Card 1. Execution replay with fresh inputs.**
- Change: per verified program, N new prompts (2-4 fresh shown pairs plus a fresh query, x from the pool's range widened about 1.5x) plus 3 leave-one-out prompts from each original question.
- Mechanism: the model must infer the program from outputs rather than memorise 3 x-values per question; replay labels are correct by construction even if the program is not the 'true' rule (only the original pool prompts carry that risk).
- Source: Shin 2019, RobustFill, Akyurek 2024, SOAR (dose). Label: shown for replay, untested for leave-one-out here.
- Expected: up on rules that already have programs (sq_plus 20-27% to roughly 30-45%, my guess); small on affine unless Step 0 widens coverage. Test N = 10, 50, 200.
- Cost: CPU minutes to generate; about 0.3-0.5 GPU-h per arm (estimate from model size).
- Wrong if: at N = 50 with matched gradient steps vs a control repeating the original prompts, covered rules gain under 5 points, or the curve is flat from N = 10 to 200 (variety was not the limit), or any practised kind drops over 1 point.

**Card 2. Hindsight relabelling of the model's own samples.**
- Change: sample 32 programs per pool prompt at T = 1; keep executable, x-dependent, behaviour-distinct (probe grid); relabel with their own outputs; at most 50 per behaviour; 50% practice replay; 3 rounds.
- Mechanism: every try becomes a correct example; the constants it can already build reappear in new combinations.
- Source: CodeIt, SOAR, Gauthier and Urban, BUSTLE. Label: shown.
- Expected: small positive (SOAR-size, a few points) if the sampler ever writes two x-dependent steps.
- Cost: sampling 1,024 x 32 is minutes; 0.3 GPU-h per round.
- Wrong if: under 1% of relabelled programs contain two or more x-dependent operations (generic count), or affine is still at or below 4% after 3 rounds.

**Card 3. Constant-mutation dreams from found programs.**
- Change: CodeIt-style mutation of found programs (swap an op, or swap an operand pointer), restricted to x-independent steps (generic data-flow property) or to any step as a second arm; keep behaviour-distinct mutants; 50/50 with replay.
- Mechanism: widens which constants appear in context without new search.
- Source: CodeIt mutation (17/400 without vs 49/400), DreamCoder fantasies, BARC remix (LLM analogue). Label: shown for mutation, untested for the x-independent restriction.
- Expected: affine from at most 4% to 8-15% if mutants reach new (A,B) pairs; much less if they do not.
- Cost: CPU; at most 1 GPU-h.
- Wrong if: 20,000 behaviour-distinct mutants add under 2 points on affine and sq_plus (coverage is not the bottleneck; reading is). Flag: do not choose mutants by whether they look like the kinds.

**Card 4. Canonical constant-builders (remove aliasing).**
- Change: rewrite the x-independent steps of every training program (practised kinds included) to the shortest builder from 1/2/10/100 with a fixed tie order. Control: random equivalent builders.
- Mechanism: one target per number, so greedy decoding stops splitting mass between 7 = 10-2-1 and 2+2+2+1.
- Source: Gauthier and Urban (smallest vs random, about 10%), DreamCoder MAP, Bunel aliasing. Label: shown in neighbouring settings.
- Expected: +1 to +4 points overall; cheap.
- Cost: a table from the executor; no extra training beyond one run.
- Wrong if: within 1.5 points of the control over 3 seeds. Flag: borderline but generic, because it touches every program, not the held-out kinds.

**Card 5. Execution-state and residual feedback to the controller.**
- Change: after each step run the executor on the 3 shown inputs; the controller sees per-slot values and (target output minus current value) per example; optional auxiliary loss predicting the next slot's values.
- Mechanism: after "multiply x by something", a parameter that was an inverse-arithmetic problem becomes a visible number.
- Source: Chen 2019 (71.91 -> 85.08), ExeDec (+5 to +7), PCCoder. Label: shown.
- Expected: held-out overall +3 to +8 if reading is the bottleneck; none if the controller already sees these values (check first).
- Cost: architecture change; 1-2 GPU-h.
- Wrong if: no held-out kind moves by 3 points. Flag: programs still may not read prompt values; only the controller sees executor values. Ask Ben to confirm this is allowed.

**Card 6. Generic-prior dreams with flattened salient variables.**
- Change: random programs over all 7 ops with random x/constant/earlier-result pointers; keep runnable, x-dependent, behaviour-distinct; flatten length, number of x-dependent steps and output magnitude (Shin acceptance rule); at least 50% practice replay.
- Mechanism: amortised inference from a broad prior, as in DeepCoder and PFNs.
- Source: DeepCoder, RobustFill, TF-Coder, Shin 2019, PFNs (abs). Label: shown for synthesis, untested for constants.
- Expected: widest range, from a loss to about +8; mismatch risk is real (BUSTLE, Shin).
- Cost: generation is CPU; training 1-2 GPU-h.
- Wrong if: any practised kind drops over 1 point, or held-out gain is under 2 at equal compute. Flag: any weight toward linear or squared shapes is forbidden; do not copy Nye 2020's "SCAN-like" prior.

**Card 7. Literal token compiled to a canonical builder.**
- Change: the controller may write LIT(v), a macro that a compiler expands into the Card 4 builder (the whole program must still fit 7 steps after expansion). Found programs are decompiled by partially evaluating their x-independent steps.
- Mechanism: a parameter becomes one shared token (B = 7 is the same token in every kind), as in DeepCoder and RobustFill; emission becomes classification.
- Source: DeepCoder, RobustFill; Kamienny (constants as tokens). Label: untested here.
- Expected: possibly the largest single gain on affine (4% to 15-30%) if emission, not reading, is the bottleneck; a null result shows the bottleneck is reading.
- Cost: compiler and decompiler on CPU; 1 GPU-h.
- Wrong if: affine stays under 8% with LIT tokens. Flag: interface change; ask Ben whether it respects "built from 1/2/10/100 inside the program".

**Card 8. Number format for the prompt reader.**
- Change: re-tokenise numbers with a digit-count prefix or place-value tags; no derived statistics (a "difference of examples" feature would be affine-specific and is forbidden).
- Source: NumeroLogic (abs), Lee 2023, Wallace (abs). Label: suggested.
- Expected: 0 to +4; cheap.
- Cost: tokenizer change; 0.5 GPU-h.
- Wrong if: no change on DEV and a probe still cannot decode the behaviour class from the controller state.

**Suggested order (my judgement).** Step 0, then Cards 1 and 4 (cheapest, best supported), then 3 and 2, then 5 and 7 as the diagnostic pair (reading vs emission), then 6 and 8. Change one thing per run; fix pass marks before looking at DEV; touch the holdout only for the final run.

---
## Plain-language summary (for a high-school senior)
Our small model has to write a tiny program for a number pattern it was never taught, like "multiply by 4 and add 7", and it has to build the numbers 4 and 7 out of 1, 2, 10 and 100. It gets one try.

The papers say three things. First, if you already have one correct program, you can run it on new numbers to make as many practice questions as you like, and this works well, but only for patterns where you found a program. Second, to get programs for new patterns you can let the model try things and keep every attempt as a lesson about the answers it actually produced, or you can make small random changes to programs you already trust. Both have worked in puzzle-solving programs. Third, numbers are the hard part: models confuse "add 1" with "subtract 1", and the methods that handle numbers well use either a final search or a fine-tuning step that we are not allowed to use.

So I would try the cheap ideas first: more practice from the programs we have, one standard way to build each number, and letting the model see what each step produced. None of the papers shows 70% in one try with no search, so reaching it may need several of these together.
