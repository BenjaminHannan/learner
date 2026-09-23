# Paper claims check (2026-09-23)

Checks the paper claims in two notes against the full text of each cited paper:
- **A** = `reviews/research-next-ideas-2026-09-23.md` (v3)
- **B** = `reviews/opus-research-reader-gate-2026-09-23.md` (Opus note, including its addendum)

Paper texts: `/root/scr/papers/` (20 papers). Page numbers come from the `=== page N ===` markers in those text files. They are PDF page numbers, not the journal's page numbers. Only the chat pipeline is discussed; nothing here is about the small card experiments or the village model. No blind panel was opened.

## Result first

- **36 claims checked** against a paper text.
  - **30 CONFIRMED**
  - **5 OVERSTATED**
  - **1 WRONG** (an author name)
  - **0 NOT IN PAPER**
- **15 claims not checkable** (no text file on disk).
- All 20 arXiv IDs that have a text file are covered.

The main news:
- **Every "[abstract]" or "[title] / from memory" claim in note B that has a text file holds up in its core.** That includes 2306.00024 (the omission step is real), 2504.14716 (side-by-side judges really are more swayed), 2309.03882 (PriDe) and 2207.05221 (several samples help). Those can move from "thin evidence" to "read in full".
- **The 5 overstated claims are all about how a paper is used, not what it found:**
  - the 66% N-version figure is a drop in mean failing test cases, not in bugs;
  - the §5 PriDe recipe is described loosely;
  - Kadavath et al. also found that a "none of the above" option *hurts* accuracy and calibration, and §5's option list includes "None";
  - the contrast-set paper says rule-built perturbations rarely do what hand-made contrast sets do;
  - Stolcke et al. say statement-shaped questions are resolved by prosody *or by the next turn*, not by intonation alone.
- **Two findings are useful for the planned experiments:**
  - CoVe found that open verification questions beat yes/no questions, and that the model tends to agree with a yes/no fact whether it is right or wrong (p9). This directly backs the QA-checker experiment in A.
  - In Gero et al., the omission step raised recall but *lowered* precision on one task (0.929 → 0.881).

## Table

C = CONFIRMED, O = OVERSTATED, W = WRONG. "p" = PDF page.

| # | Note | Claim (short) | Paper | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 | A | A well-built QA metric beat the best entailment metric at checking summaries | 2112.08542 QAFactEval | C | p1: "QAFACTEVAL ... also outperforms the best-performing entailment-based metric." Table 3 (p7): 77.8 vs 75.7 (MNLI) balanced accuracy. The older QA metric QuestEval scored lower (68.2), so the building details matter. |
| 2 | A | QA and entailment combined did better still | 2112.08542 | C | p1: "QA-based and entailment-based metrics can offer complementary signals and be combined into a single metric for a further performance boost." The gain is small: 78.3 (synthetic) and 79.5 (supervised). Only the supervised version was statistically significant (p7). |
| 3 | A | CoVe: verification questions answered separately, without the original answer in view, worked better | 2309.11495 CoVe | C | p8: "consistent performance improvement across all tasks from applying the factored CoVe approach compared to joint CoVe." The 2-step variant was best on Wikidata (p8). p9 adds: "yes/no type questions perform worse for the factored version of CoVe." |
| 4 | A | Dialogue acts learned as their own task: 71% on transcripts vs 84% for people, phone calls | cs/0006023 Stolcke | C | p1: "71% based on word transcripts, compared to a chance baseline accuracy of 35% and human accuracy of 84%." The 84% is agreement between human labellers (p14). The data is Switchboard telephone speech. |
| 5 | A | Set prediction: facts as an unordered set, predicted in parallel with a matching loss | 2011.01675 SPN | C | p1: "non-autoregressive parallel decoding ... a set-based loss that forces unique predictions via bipartite matching." |
| 6 | A | SPN says nothing about putting a count before a list | 2011.01675 | C | p3: the paper sets aside predicting set size: "we simplify the pL(n\|X) into a constant ... generate a fixed-size set of m predictions." It never predicts a count. |
| 7 | A | Trust or Escalate: Simulated Annotators give a confidence signal | 2407.18370 | C | p1: "Simulated Annotators, a novel confidence estimation method that significantly improves judge calibration." |
| 8 | A | Its guarantee comes from choosing the threshold on human-labelled calibration data | 2407.18370 | C | p3: "given access to a small calibration set Dcal∼P(x,y human) of human preferences, we can measure an empirical risk." The threshold is chosen by fixed-sequence testing. |
| 9 | A | Active inference, Appendix C: finite-sample, time-uniform versions for bounded means | 2403.03208 | C | p24: "those for mean estimation—have direct non-asymptotic and time-uniform analogues." A condition applies: the labelling probability π must stay above a floor (the paper mixes it with a uniform rule). |
| 10 | A | It works by random sampling with known probabilities plus a correction | 2403.03208 | C | p4: "collect label Yi with probability π(Xi)." The estimator adds (Y − f)·ξ/π to the prediction. The abstract's own shorthand is "rely on the model's predictions where it is confident", but the correction term is what makes it valid. |
| 11 | A | CycleGT: cycles help learn text↔graph from unpaired data | 2006.04702 | C | p1: "unsupervised training method that can bootstrap from fully non-parallel graph and text data ... on par with several fully supervised models." Its text-to-graph side uses an off-the-shelf entity extractor and learns only the relations (p3). |
| 12 | A | UniversalNER: a smaller model trained on the big model's labels beat it by 7–9 F1 | 2308.03279 | C | p1: "outperforms its NER accuracy by 7-9 absolute F1 points in average." The students are 7B and 13B models, averaged over 43 datasets. |
| 13 | A | TinyStories: models under 10M parameters wrote fluent, grammatical stories | 2305.07759 | C | p1: "below 10 million total parameters ... fluent and consistent stories ... almost perfect grammar." This was on a synthetic dataset limited to words 3- to 4-year-olds know. |
| 14 | A | Calibrate Before Use: majority-label bias (listed under Sources only) | 2102.09690 | C | p4: "GPT-3 is biased towards answers that are frequent in the prompt." Note A cites the paper only in its Sources list and makes no claim about it in the body. |
| 15 | B | Over 350 LLMs; on one leaderboard, models agree 60% of the time when both are wrong | 2506.07962 Kim et al. | C | p1: "on one leaderboard dataset, models agree 60% of the time when both models err." Random choice among wrong answers would give 1/3 (p1). |
| 16 | B | Larger, more accurate models have more correlated errors, even across architectures and providers | 2506.07962 | C | p1: "larger and more accurate models have highly correlated errors, even with distinct architectures and providers." |
| 17 | B | The paper traces effects on LLM-as-judge | 2506.07962 | C | p4: "each judge systematically inflates the accuracy of models that are less accurate than itself, due to correlated errors." |
| 18 | B | Coding agents often fail together on tricky specs | 2606.20158 | C | p1: "substantial common-mode failure ... co-occuring failures can be traced to where is specification is particularly hard or ambiguous." (The typos are the paper's own.) There is one specification: Knight–Leveson's Launch Interceptor Program. |
| 19 | B | Three-agent voting cut bugs by 66% | 2606.20158 | O | The paper never says 66% or "bugs". It says the "mean failure count drops from 387.44 for single versions to 130.99 for triples" (p1). That is a 66% drop in failing test inputs out of 1,000,000, averaged over all 17,296 triples. |
| 20 | B | SAC3: self-consistency misses consistent errors; perturbed questions plus other models catch more | 2311.01740 | C | p1: two kinds of hallucination "cannot be effectively identified through self-consistency check alone." p7: self-check AUROC 65.9/56.1 vs >99% for SAC3-Q. The cross-model part is mixed: it helped on HotpotQA (+6.7), was "slightly worse" on NQ-open (p8), and failed on the senator task because the verifier models refused to answer (p7). |
| 21 | B | Large models are well calibrated on multiple-choice and true/false "in the right format" | 2207.05221 Kadavath | C | p1: "larger models are well-calibrated on diverse multiple choice and true/false questions when they are provided in the right format." The right format means visible lettered options (p4). |
| 22 | B | Judging one answer went better after the model saw several of its own attempts | 2207.05221 | C | p1: "Performance at self-evaluation further improves when we allow models to consider many of their own samples." The setup was 5 samples (p12). The paper says models "benefit less from this approach on tasks requiring long-form answers" (p13). |
| 23 | B | So comparing alternatives supports §5's rival-readings checker | 2207.05221 | O | Partly supported, but the same paper finds: "Replacing an option with 'none of the above' reduces accuracy and calibration significantly" (p4). §5 always adds a "None of these" option. |
| 24 | B | Models favour certain option letters regardless of content | 2309.03882 Zheng | C | p1: "they prefer to select specific option IDs as answers." Size of the bias: with answers balanced at 25% each, llama-30B picks A/B/C/D 34.6/27.3/22.3/15.8% (p1). Moving all gold answers to A raises its accuracy by 15.2 points (p2). |
| 25 | B | PriDe estimates the letter prior from permuted options on a small sample and removes it at test time without labels | 2309.03882 | C | p1: "PriDe first estimates the prior by permutating option contents on a small number of test samples." It is "label-free", and "(e.g., 5%)" of samples is used (p2). |
| 26 | B | §5 recipe: average the letter probabilities over cyclic permutations on 50 items, then divide | 2309.03882 | O | The paper averages *log* probabilities over the permutations for each item and applies a softmax (Eq. 7). It then averages those per-item priors and divides the observed probabilities by the result (Eq. 8, p6). The prior is defined for a fixed number of options n, but §5 lists have 2 to 6. |
| 27 | B | Side-by-side judges are more swayed by irrelevant surface features than one-at-a-time judges | 2504.14716 Tripathi | C | p1: "pairwise protocols are more vulnerable to distracted evaluation ... Pairwise preferences flip in about 35% of the cases, compared to only 9% for absolute scores." |
| 28 | B | Small edits to inputs expose decision boundaries that ordinary test sets miss | 2004.02709 Gardner | C | p1: "manually perturb the test instances in small but meaningful ways that (typically) change the gold label." Performance drops by up to 25%. |
| 29 | B | Our rival readings are contrast sets built at test time | 2004.02709 | O | Contrast sets are made by hand by experts, for evaluation. The paper warns that rule-based perturbations rarely cross the decision boundary: "it is very challenging to come up with rules or other automated methods for pushing pivots across a decision boundary" (p5). |
| 30 | B | Stolcke uses word, word-pattern and prosodic cues | cs/0006023 | C | p1: "detects and predicts dialogue acts based on lexical, collocational, and prosodic cues." |
| 31 | B | A statement-shaped question is often marked only by intonation, so in text some are truly ambiguous | cs/0006023 (the note cites the SwDA manual and Shriberg 1998, which are not on disk) | O | Stolcke agrees that declarative questions "are thus confusable with STATEMENTS" (p19). It then adds that "ambiguity can also be removed by examining the context of the utterance", such as a following yes/no answer. On balanced text, words alone separate questions from statements 85.9% of the time (p20). |
| 32 | B | Speaker commitment depends on context and pragmatics; fine-tuned models fail most on pragmatic cases | 2107.00807 | C | p1: BERT "fails on instances where pragmatic reasoning is necessary." Among the worst 10% of errors, context explains 61.8% in CB. In RP the largest share is "lexical inference" (35.2%), then prior probability (12.8%) (p13). |
| 33 | B | The LLM gives evidence spans for its extractions, checks its outputs, and accuracy improves across LLMs | 2306.00024 Gero | C | p1: "leverages the LLM to provide provenance for its own extraction and check its own outputs ... consistently improves accuracy for various LLMs." |
| 34 | B | A separate "find what was missed" step raises recall; a pruning step raises precision | 2306.00024 | C | p3: "The Omission step finds missing elements, which increases recall but at the cost of decreased precision." Table 3 (p4): omission recall 0.928→0.946 (medications) and 0.448→0.501 (ICD-10). Precision on medications fell 0.929→0.881. Prune raised precision 0.929→0.949 and 0.544→0.557. |
| 35 | B | Omission is a major error source, and detecting omissions is hard even with labelled data | 2211.07145 Zou | C | p5: "even using pre-trained models, we find it still reaches a high omission ratio of at least 70%." p7: "the best F1 score is around 50% in all five domains." QMSum reaches at most 41.35 F1 (p8). |
| 36 | B | Citation "Monperrus et al. 2026" for N-version programming | 2606.20158 | W | p1 authors: "Javier Ron, Benoit Baudry, and Martin Monperrus". The first author is Ron. |

### Not checkable (no text file on disk): 15

- **Note A (3):**
  - Gharsallah et al., arXiv 2609.15561 (judge perturbation study);
  - semantic entropy (Farquhar et al., Nature 2024);
  - conformal factuality, arXiv 2402.10978 (cited as background only).
- **Note B (12):**
  - Knight & Leveson 1986;
  - Eckhardt & Lee 1985;
  - Littlewood & Miller 1989;
  - Goel et al., arXiv 2502.04313 (CAPA);
  - Blum & Mitchell 1998;
  - the SwDA coding manual (qy^d tag);
  - Shriberg et al. 1998;
  - de Marneffe, Manning & Potts 2012;
  - Cao et al., arXiv 2311.18805;
  - Pruthi et al., arXiv 1905.11268;
  - Wei et al., arXiv 2403.18802 (SAFE);
  - Wang et al., arXiv 2304.10428 (GPT-NER).

  2606.20158 (p1) repeats the Knight–Leveson finding second-hand: independently written versions "still exhibited substantial common-mode failure".

## Suggested replacement wording (claims not CONFIRMED)

- **#19 (66%):** "Across all 17,296 three-version majority-vote units, mean failing test inputs (out of 1,000,000) fell from 387.44 for single versions to 130.99, about 66% fewer, despite correlated failures."
- **#23 (Kadavath supports §5):** "Kadavath et al. find lettered multiple-choice calibrated and self-evaluation helped by seeing several samples, but also that adding a 'none of the above' option significantly hurts accuracy and calibration, so §5's 'None' option is a risk to test."
- **#26 (PriDe recipe):** "PriDe: for each of K items, average the log letter-probabilities over cyclic permutations and softmax them to get that item's prior; average the priors; divide each new item's letter probabilities by that prior and renormalise. Estimate a separate prior for each option count (2 to 6)."
- **#29 (contrast sets):** "Rival readings borrow the contrast-set idea (small edits that change the answer), but contrast sets are hand-made for evaluation, and their authors warn that rule-built edits rarely cross the decision boundary."
- **#31 (declarative questions):** "Statement-shaped questions have no syntax marker and get confused with statements. Stolcke et al. resolve them with prosody or with the next turn (for example a yes/no answer). In plain text, without the next turn, some stay ambiguous, so asking is the safe action."
- **#36 (author):** "Ron, Baudry & Monperrus 2026, 'N-Version Programming with Coding Agents', arXiv 2606.20158."

## Plain-language summary for Ben

We checked 36 statements in the two notes about what research papers found, against the full papers. 30 were accurate. 5 stretched the paper a little, and 1 had the wrong first author.

The stretches are all about how a paper was applied to our checker, not about what it found:
- The 66% N-version figure counts failing tests, not bugs.
- The paper that likes multiple-choice formats also found that adding a "none of these" choice hurts, and our proposed checker adds one.
- Hand-made "contrast sets" aren't quite the same as rule-made rival readings.
- The 2000 dialogue paper says statement-shaped questions can also be told apart by what comes next, not only by tone of voice.

The papers note B could only skim before all hold up, so its "thin evidence" labels can be upgraded for those claims. 15 older or missing papers couldn't be checked because we don't have their text.
