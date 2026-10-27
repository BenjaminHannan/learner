# E. Teaching a small model to abstain, ask, and hand over, without rewarding laziness

Research note, 2026-09-25. Every entry below was fetched with curl from arxiv.org/abs/<id>, and the key ones also from arxiv.org/html/<id>.
Quotes are copied verbatim. Where a quote contains maths, the symbols came from the HTML `alttext`. Licences come from the Hugging Face API tags (HF) or a raw LICENSE file (GH), as marked.
Labels: **SHOWN** means the paper's own experiments demonstrate it. **SUGGESTED** means it is an argument or theory, a single-group preprint, or a narrow setting. **DISPUTED** means other verified work points the other way.
None of this has been tested on Premonition. Every "plug-in" line is **untested** and is a proposal for the *card experiments* (24 puzzles and code tasks), not for the village model, unless it says otherwise.

## 0. The five findings that matter most for Ben's loop
1. **Ben's "sleep on your own hits" loop is a form of reinforcement fine-tuning, and that kind of training erodes "I don't know".** Refusal fell by more than 80% (Hallucination Tax), and reasoning fine-tuning cut abstention by 24% (AbstentionBench). Mixing in about 10% unsolvable problems restored refusal in 7-8B models.
2. **Small models are the hard case.** In the same paper, Qwen2.5-1.5B-Math barely learned to refuse: 0.00 → 0.04 on UMWP and 0.00 → 0.01 on the SUM test set. Two more papers say larger models cope better: Intellectual Humility and Abstention Inflation.
3. **A discrete "abstain" action trained with an error penalty can collapse into refusing everything.** This happened to a 1.5B model within 10 optimizer steps, and the reward curve looked like it was improving the whole time. The proposed fix is to always output a confidence score, train that score with a proper scoring rule, and apply the abstain threshold only at deployment. This is a single preprint, so SUGGESTED.
4. **Being able to solve a problem does not mean being able to ask about it.** Models "struggle to identify the right question even when they can solve the fully specified version" (QuestBench). ClarifyCodeBench and Ambig-SWE report the same.
5. **Over-asking mostly comes from training.** Untrained frontier models "rarely over-abstain" (AbstentionBench). But training on negative examples "can make the model over-conservative" (When2Call), and simply adding an "Unknown" option inflates abstention (Abstention Inflation).

## 1. Why models guess: the grading rewards it

**Why Language Models Hallucinate.** Kalai, Nachum, Vempala, Zhang (OpenAI/Georgia Tech), 2025, arXiv 2509.04664. https://arxiv.org/abs/2509.04664 and /html
- Quote: "Under binary grading, abstaining is strictly sub-optimal." Proposed prompt: "Answer only if you are $>t$ confident, since mistakes are penalized $t/(1-t)$ points, while correct answers receive 1 point, and an answer of 'I don't know' receives 0 points … $t=0.5$ (penalty 1), $t=0.75$ (penalty 2), and $t=0.9$ (penalty 9)."
- In plain terms: if right = 1 and wrong = 0, guessing always beats "I don't know". Penalizing wrong answers creates a confidence bar that the model must clear before answering. The paper calls this "behavioral calibration". **Label:** the maths is SHOWN (it is trivial). The claim that this is *why* models hallucinate is SUGGESTED (a position paper).
- Plug-in: the sleep reward must never be binary on items that can be abstained on. Use +1 / 0 / −t/(1−t) with t fixed in advance (for example t = 0.75, so a wrong answer costs −3), and report accuracy at several values of t.

**The Hallucination Tax of Reinforcement Finetuning.** Song, Shi, Zhao, 2025, arXiv 2505.13988. https://arxiv.org/abs/2505.13988 and /html
- Quote: "standard RFT training could reduce model refusal rates by more than 80% … incorporating just 10% SUM during RFT substantially restores appropriate refusal behavior, with minimal accuracy trade-offs on solvable tasks."
- Table 2, refusal rate on UMWP before → after training with 10% SUM mixed in:

| Model | UMWP refusal (before → after) |
|---|---|
| Qwen2.5-7B | 0.01 → 0.81 |
| Qwen2.5-7B-Instruct | 0.08 → 0.85 |
| **Qwen2.5-1.5B-Math** | **0.00 → 0.04** |
| Llama-3.1-8B-Instruct | 0.00 → 0.79 |

- Accuracy cost on AMC23 was −0.03 to −0.10. The paper tried mixing ratios of 0/1/10/30/50%: "higher ratios improve refusal rates … but lead to decreasing accuracy". **Label:** SHOWN for 7-8B models. For about 1.5B models, the same recipe was SHOWN to largely fail. **Dataset:** SUM, `lime-nlp/Synthetic_Unanswerable_Math`, MIT (HF).
- Plug-in: during practice, replace about 10% of items with provably unsolvable twins, where the target answer is "I can't solve this, because …". Measure refusal on unsolvable items and accuracy on solvable items after every sleep.

**AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions.** Kirichenko, Ibrahim, Chaudhuri, Bell (FAIR at Meta), 2025, arXiv 2506.09038. https://arxiv.org/abs/2506.09038 and /html
- Quote: "reasoning fine-tuning degrades abstention (by $24\%$ on average), even for math and science domains"; "scaling models is of little use"; appendix: "on most datasets the precision is close to [1] for most models—i.e., models rarely over-abstain."
- In plain terms: 20 datasets and 20 models show that training for reasoning makes models worse at saying "I can't". **Label:** SHOWN. **Dataset:** `facebook/AbstentionBench`, **CC-BY-NC-4.0** (HF; non-commercial). Its per-dataset licences are listed in Table 3, for example GSM8K-Abstain MIT, SQuAD 2.0 CC-BY-SA-4.0, UMWP "not specified".
- Plug-in: use it for held-out evaluation only, in the village model, and never train on it.

**Missing Premise exacerbates Overthinking.** Fan, Li, Sun, Zhou, 2025, arXiv 2504.06514. https://arxiv.org/abs/2504.06514 and /html
- Quote: "the response length of reasoning LLMs … drastically increases for ill-posed questions with missing premises"; "LLMs not specifically trained for reasoning exhibit much better performance on the MiP scenario"; "they typically fail to act on those suspicions". **Label:** SHOWN.
- Plug-in: a long search on an unsolvable item is a warning sign. Log how many guesses were made before giving up, separately for solvable and unsolvable items.

## 2. Training "I don't know"

**R-Tuning: Instructing LLMs to Say 'I Don't Know'.** Zhang, Diao, Lin, Fung, Lian, Wang et al., NAACL 2024, arXiv 2311.09677. https://arxiv.org/abs/2311.09677 and /html
- Quote: "We first apply the pre-trained model to answer all the questions … and split the questions into two sets based on the comparison between the prediction and label"; "the refusal ability was found to be a meta-skill that could be generalized to other tasks." **Label:** SHOWN on their tasks. That the skill generalizes as a meta-skill is SUGGESTED.
- Plug-in: this is the closest match to Ben's loop. The checker already splits items into hits and misses. Train "I am sure" on hits and "I am unsure" on items with zero hits. Caveat: for puzzles, "the model missed it" is not the same as "it is unsolvable", so keep the two labels separate (see section 7).

**Language Models (Mostly) Know What They Know.** Kadavath et al. (Anthropic), 2022, arXiv 2207.05221. https://arxiv.org/abs/2207.05221
- Quote: "larger models are well-calibrated on diverse multiple choice and true/false questions"; P(IK) "partially generalize[s] across tasks, though they struggle with calibration of P(IK) on new tasks." Self-evaluation "further improves when we allow models to consider many of their own samples". **Label:** SHOWN for large models. For a 1B model it is untested.
- Plug-in: blurting many guesses already provides the "many samples" signal. Train a P(IK) head or token to predict the hit-rate.

**TruthRL.** Wei, Yang, Sun, Wang, Shao, Chen et al., ICML 2026, arXiv 2509.25760. https://arxiv.org/abs/2509.25760 and /html
- Quote: a "ternary reward that distinguishes correct answers, hallucinations, and abstentions … treats abstentions as neutral"; "reduces hallucinations (e.g., 43.5% → 19.4%) and improves truthfulness (e.g., 5.3% → 37.2%)." **Label:** SHOWN for factual QA with retrieval.
- Plug-in: reward correct +1, "I don't know" 0, wrong −1 (this is Kalai's rule with t = 0.5).

**Rewarding Intellectual Humility: Learning When Not To Answer.** Jha et al., 2026, arXiv 2601.20126. https://arxiv.org/abs/2601.20126
- Quote: "moderate abstention rewards (r_abs ≈ −0.25 to 0.3) consistently reduce incorrect responses without severe accuracy degradation on multiple-choice tasks, with larger models exhibiting greater robustness … On open-ended question answering, we observe limitations due to insufficient exploration, which can be partially mitigated through supervised abstention training."
- Tested on 2B and 4B models. **Label:** SUGGESTED (a preprint).
- Plug-in: the abstain reward should sit between −0.25 and +0.3, never high. Teach the phrase with supervised fine-tuning before RL, because a 1B model will rarely produce it on its own.

**Beyond Binary Rewards (RLCR).** Damani, Puri, Slocum, Shenfeld, Choshen, Kim et al., 2025, arXiv 2507.16806. https://arxiv.org/abs/2507.16806
- Quote: binary rewards "do not penalize guessing … degrading calibration"; RLCR "augments a binary correctness score with a Brier score … While ordinary RL hurts calibration, RLCR improves it." **Label:** SHOWN.
- Plug-in: have the model state a confidence c, then score correct − (c − correct)².

**Abstention as an Action Can Kill Both the Reward Gradient and the KL Anchor.** Che, Yuan, Zhao, Yu, 2026, arXiv 2608.00301. https://arxiv.org/abs/2608.00301 and /html
- Quote: "the model drifts toward refusing everything, its mean training reward rising to zero … so the curve reads as improvement while coverage collapses"; "group normalization silently replaces every designed penalty with an effective penalty of one"; on Qwen2.5-1.5B, "the median answer probability falls from 1.000 to ≤0.008 within ten optimizer steps … while forced-answer correctness on those prompts holds at 0.94–0.97." Fix: "train a mandatory confidence report with a strictly proper score plus a correctness reward, and abstain only at deployment by thresholding the report." **Label:** SUGGESTED (a single-group preprint, unreplicated). It is also the most direct warning for a 1B model.
- Plug-in: do not make "abstain" a rewarded action at first. Always emit a confidence score, train it with a Brier score, and threshold it at test time. Also watch *coverage* on previously solved items, not only the reward.

**TIAR: Trajectory-Informed Advantage Reweighting.** Pan et al., 2026, arXiv 2605.25850. https://arxiv.org/abs/2605.25850
- Quote: it marks questions as out-of-knowledge using "GRPO's multiple trajectories as a natural abstention signal"; "outperforming the static ternary baseline on 17 of 31 benchmark datasets while fully preserving baseline accuracy." **Label:** SUGGESTED.
- Plug-in: the hit fraction among the blurts sets how much an abstention is worth on that item.

## 3. Clarifying questions

**AmbigQA.** Min, Michael, Hajishirzi, Zettlemoyer, EMNLP 2020, arXiv 2004.10645. https://arxiv.org/abs/2004.10645
- Quote: "over half of the questions in NQ-open are ambiguous"; the set has 14,042 questions. **Label:** SHOWN. **Dataset:** `sewon/ambig_qa`, CC-BY-SA-3.0 (HF).
- Plug-in: village-model evaluation only.

**CLAMBER.** Zhang, Qin, Deng, Huang, Lei, Liu et al., ACL 2024, arXiv 2405.12063. https://arxiv.org/abs/2405.12063
- Quote: "~12K high-quality data"; CoT and few-shot prompting "may result in overconfidence … and yield only marginal enhancements in identifying ambiguity." **Label:** SHOWN. **Licence:** **not verified** (no HF card found, GitHub API blocked).

**STaR-GATE.** Andukuri, Fränken, Gerstenberg, Goodman, 2024, arXiv 2403.19154. https://arxiv.org/abs/2403.19154
- Quote: "iteratively finetuned on questions that increase the probability of high-quality responses … preferred over responses from the initial model on 72% of tasks." **Label:** SHOWN.
- Plug-in: this is the self-improvement pattern Ben already uses, applied to questions. Keep a question as a "hit" only if, after the simulated human answers it, the checker passes.

**Modeling Future Conversation Turns to Teach LLMs to Ask Clarifying Questions.** M. J. Q. Zhang, Knox, Choi, ICLR 2025, arXiv 2410.13788. https://arxiv.org/abs/2410.13788 and /html
- Quote: "5% improvement in F1"; "3% improvement in accuracy" on deciding when to ask. Table 1 note: the best-F1 variant comes "at the cost of always asking clarifying questions". **Label:** SHOWN, with a small effect.
- Plug-in: score a question by the outcome after the answer, not by how it looks.

**Learning to Clarify (ACT).** Chen, Sun, Pfister, Arık, ICLR 2025, arXiv 2406.00222. https://arxiv.org/abs/2406.00222
- Quote: models "often overhedge or implicitly guess users' true intents rather than asking"; it introduces AmbigSQL. **Label:** SHOWN.

**CollabLLM.** Wu, Galley, Peng, Cheng, Li, Dou et al., ICML 2025 Outstanding Paper, arXiv 2502.00640. https://arxiv.org/abs/2502.00640
- Quote: "18.5% higher task performance and 46.3% improved interactivity … 201 judges … increases user satisfaction by 17.6% and reduces user spent time by 10.4%." **Label:** SHOWN.
- Plug-in: village model only. It rewards multi-turn outcomes, not the question itself.

**InfoQuest.** de Oliveira et al., 2025, arXiv 2502.12257. https://arxiv.org/abs/2502.12257
- Quote: models "frequently default to generic responses without proper clarification." **Label:** SHOWN. **Dataset:** `bryanlincoln/infoquest`, MIT (HF).

**QuestBench.** Li, Kim, Wang (Google DeepMind), 2025, arXiv 2503.22674. https://arxiv.org/abs/2503.22674 and /html
- Quote: it covers underspecified tasks "solvable by asking at most one question … only 40-50% accuracy on Logic-Q and Planning-Q … models struggle to identify the right question even when they can solve the fully specified version." **Label:** SHOWN. **Dataset:** `belindazli/QuestBench`, CC-BY-4.0 (HF).
- Plug-in: it is the best template for checkable asking. Take a well-posed problem, remove exactly one variable, and there is then exactly one correct question.

**ClarifyGPT.** Mu et al., 2023, arXiv 2310.10996. https://arxiv.org/abs/2310.10996
- Quote: it detects ambiguity "by performing a code consistency check"; "Pass@1 of GPT-4 from 70.96% to 80.80% on MBPP-sanitized." **Label:** SHOWN.
- Plug-in: this is how to *prove* a coding task is ambiguous. Sample several solutions. If they pass the visible tests but disagree on hidden inputs, the task is ambiguous.

**HumanEvalComm.** Wu, Fard, TOSEM, arXiv 2406.00215. https://arxiv.org/abs/2406.00215
- Quote: descriptions are modified for "inconsistency, ambiguity, incompleteness"; it defines metrics "Communication Rate and Good Question Rate". **Label:** SHOWN. **Dataset:** `jie-jw-wu/HumanEvalComm`, Apache-2.0 (HF).

**ClarifyCoder / Can Code LMs Learn Clarification-Seeking?** Wu et al., 2025, arXiv 2504.16331. https://arxiv.org/abs/2504.16331
- Quote: "63% communication rate (40% absolute increase) and a 52% good question rate (30% absolute increase) on ambiguous tasks … while maintaining code generation performance." **Label:** SHOWN. It does not report a false-ask rate on clear tasks, so that side is unmeasured.

**ClarifyCodeBench.** Fang et al., 2026, arXiv 2607.00711. https://arxiv.org/abs/2607.00711
- Quote: "Turn-discounted Key Question Rate, which penalizes inefficient questioning"; "Strong code generation performance does not inherently translate to effective requirement clarification." **Label:** SHOWN.

**Ambig-SWE.** Vijayvargiya, Zhou, Yerukola, Sap, Neubig, ICLR 2026, arXiv 2502.13069. https://arxiv.org/abs/2502.13069 and /html
- Quote: "models struggle to distinguish between well-specified and underspecified instructions … improvements in performance, up to 74% over the non-interactive settings"; "Claude Sonnet 4 and Claude Sonnet 3.5 are the only evaluated LLMs that achieve notable accuracy (89% and 84%)" at the distinction. **Label:** SHOWN.

**When2Call.** Ross, Mahabaleshwarkar, Suhara (NVIDIA), NAACL 2025, arXiv 2504.18851. https://arxiv.org/abs/2504.18851 and /html
- Quote: "simply adding negative examples … increases performance on When2Call but decreases performance on BFCL AST, as the model becomes too conservative"; models "still often hallucinate a tool call with the missing parameters". **Label:** SHOWN. **Dataset:** `nvidia/When2Call`, CC-BY-4.0 (HF).
- Plug-in: every training set of "ask" items needs a matched set of "just do it" twins.

**Ask, Condition or Abstain (ACA-RL).** Tong et al., EMNLP 2026, arXiv 2608.16554. https://arxiv.org/abs/2608.16554 and /html
- Quote: it uses a "structured reward over five behaviors: silent hallucination, explicit assumption, abstention, conditional formulation, and active elicitation … The highest reward is reserved for active elicitation … Abstention remains positive as a safe fallback, but its lower value discourages the model from stopping at gene[ric refusal]"; it builds 120K training items by removing premises, plus the 274-item MPB benchmark. **Label:** SHOWN on their benchmark. Licence not checked.
- Plug-in: this is the reward ordering to copy. Asking for the missing number > answering "if x = …, then …" > "can't" > stating an assumption > a silent guess.

**Clarify-or-Answer (CoA).** Cao, Wen, Wang, 2026, arXiv 2601.16400. https://arxiv.org/abs/2601.16400
- Quote: it "separately models the decision to ask or answer, and what to ask"; there is a non-ambiguous "contrast set"; "+15.3 points (83%)" over prompting. **Label:** SHOWN (for VQA).

**Uncertainty-Aware Clarification with Information Gain.** Deng et al., 2026, arXiv 2606.03135. https://arxiv.org/abs/2606.03135
- Quote: "improves the success rate by 3.7% over the no-clarification baseline, while adding only 0.3 total interaction steps on average" (τ-bench). **Label:** SUGGESTED (small gain).

**τ-bench.** Yao, Shinn, Razavi, Narasimhan, 2024, arXiv 2406.12045. https://arxiv.org/abs/2406.12045
- Quote: "succeed on <50% of the tasks … pass^8 <25% in retail." It introduces pass^k, which asks whether the agent succeeds on all k tries. **Label:** SHOWN.
- Plug-in: report pass^k for ask decisions too. A model that asks correctly only some of the time is unreliable.

## 4. Deciding when to stop and hand over

**Consistent Estimators for Learning to Defer to an Expert.** Mozannar, Sontag, ICML 2020, arXiv 2006.01862. https://arxiv.org/abs/2006.01862
- Quote: it learns "a classifier and a rejector … a novel reduction to cost sensitive learning." **Label:** SHOWN (for small classifiers).
- Plug-in: deferring is a decision with a cost. Hand over only when the expected loss from answering is greater than the cost of asking the human.

**Selective QA under Domain Shift.** Kamath, Jia, Liang, ACL 2020, arXiv 2006.09462. https://arxiv.org/abs/2006.09462
- Quote: "answers 56% of questions while maintaining 80% accuracy; in contrast, directly using the model's probabilities only answers 48%." **Label:** SHOWN.
- Plug-in: report coverage at a fixed accuracy. It is the standard measure for "how often did it hand over".

**Selectively Answering Ambiguous Questions.** Cole, Zhang, Gillick, Eisenschlos, Dhingra, Eisenstein, EMNLP 2023, arXiv 2305.14613. https://arxiv.org/abs/2305.14613
- Quote: "the most reliable approach to decide when to abstain involves quantifying repetition within sampled model outputs, rather than the model's likelihood or self-verification". **Label:** SHOWN.
- Plug-in: Ben's blurts give this for free. How often the same answer repeats is the confidence signal.

**Semantic Uncertainty.** Kuhn, Gal, Farquhar, ICLR 2023, arXiv 2302.09664. https://arxiv.org/abs/2302.09664
- Quote: "semantic entropy is more predictive of model accuracy … than comparable baselines." **Label:** SHOWN.

**Robots That Ask For Help (KnowNo).** Ren et al., CoRL 2023 (oral), arXiv 2307.01928. https://arxiv.org/abs/2307.01928
- Quote: it uses "conformal prediction to provide statistical guarantees on task completion while minimizing human help". **Label:** SHOWN.
- Plug-in: set the hand-over threshold on a calibration set so that the success rate after handing over is at least 1−ε.

**Deep Think with Confidence.** Fu, Wang, Tian, Zhao, 2025, arXiv 2508.15260. https://arxiv.org/abs/2508.15260
- Quote: "reduces generated tokens by up to 84.7% compared to full parallel thinking." **Label:** SHOWN (large models).
- Plug-in: stop blurting early once the trace confidence drops below a threshold.

**Rewarding Efficient Reasoning Improves Abstention (SURE).** Tsvilodub et al., 2026, arXiv 2609.20846. https://arxiv.org/abs/2609.20846 and /html
- Quote: "human reasoning effort on unanswerable tasks is upper-bounded by answerable tasks, whereas LRMs waste computational resources"; tested on 4B models, "+12.8% on average … 44% shorter CoTs." The efficiency term is the share of reasoning after "the first sentence where missing task-relevant information is identified". The weights are 0.5 and 0.5. **Label:** SUGGESTED (a recent preprint).
- Plug-in: the give-up budget on an unsolvable item should be no larger than the typical budget for a solvable item.

**SAAS (over-search).** Tang et al., 2026, arXiv 2605.29796. https://arxiv.org/abs/2605.29796
- Quote: agents are "blindly triggering searches when internal knowledge suffices and failing to terminate search". It contrasts runs with search on and search off. **Label:** SUGGESTED.
- Plug-in: the same idea works as an "ask-off" control. If the model solves the item with asking disabled, asking was unnecessary.

## 5. Failure modes: laziness, over-refusal, sycophancy

| Paper | Key fact (verbatim) | Label | Data / licence |
|---|---|---|---|
| XSTest, Röttger et al., NAACL 2024, 2308.01263 | "250 safe prompts … that well-calibrated models should not refuse … and 200 unsafe prompts as contrasts" | SHOWN | walledai/XSTest CC-BY-4.0 (HF) |
| OR-Bench, Cui, Chiang, Stoica, Hsieh, ICML 2025, 2405.20947 | "80,000 over-refusal prompts … ~1,000 hard prompts … 600 toxic prompts" | SHOWN | bench-llm/or-bench CC-BY-4.0 (HF) |
| CoCoNot (Art of Saying No), Brahman et al., NeurIPS 2024 D&B, 2407.12043 | "GPT-4 incorrectly complying with as many as 30% of requests"; "direct finetuning … can lead to both over-refusal and a decline in general capabilities" | SHOWN | allenai/coconot, ODC-BY per card (HF README) |
| Abstention Inflation, Ling et al., 2025, 2507.16199 | adding "Unknown" as an option causes "serious accuracy drops"; "Replacing 'Unknown' with an unrelated random word produces an identical effect"; "mitigated at larger model sizes" | SUGGESTED | — |
| Sycophancy, Sharma et al., 2023, 2310.13548 | "both humans and preference models (PMs) prefer convincingly-written sycophantic responses over correct ones a non-negligible fraction of the time" | SHOWN | — |
| SQuAD 2.0, Rajpurkar, Jia, Liang, ACL 2018, 1806.03822 | "over 50,000 unanswerable questions written adversarially … 86% F1 on SQuAD 1.1 achieves only 66% F1 on SQuAD 2.0" | SHOWN | rajpurkar/squad_v2 CC-BY-SA-4.0 (HF) |
| SelfAware, Yin et al., Findings ACL 2023, 2305.18153 | unanswerable questions "from five diverse categories and their answerable counterparts"; "a considerable gap between … models and human proficiency" | SHOWN | Apache-2.0 (GH LICENSE) |
| UMWP, Sun et al., LREC-COLING 2024, 2403.03558 | "5200 questions across five categories" | SHOWN | licence "not specified" per AbstentionBench |

- **Is over-asking a real risk? The evidence conflicts (DISPUTED).** Untrained frontier models "rarely over-abstain" (AbstentionBench, appendix D.1). But *training* toward abstaining or asking produced over-conservatism in When2Call, CoCoNot and the Abstention Collapse paper. For Ben the risk comes from the training step itself, so every change must be scored on solvable twins too.
- **Sycophancy relevance (for the village model only).** If a simulated or real human's reply is taken as ground truth, the model learns to agree. Only the exact checker should decide whether an item is a "hit".

## 6. Dropped or not verified
- "Know the Unknown" (the exact title) was not fetched and is not cited. SelfAware and KUQ (inside AbstentionBench) cover it.
- CLAMBER licence and ACA-RL/MPB licence: not verified.
- The "Missing I Don't Know" position paper (2609.17686) was read but is not relied on: a single author making an argument only.
- I-CALM (2604.03904) is prompt-only and does no training. It is kept only for its evaluation trick, used in section 7.

## 7. A checkable way to train asking (card experiments first; the village model stays separate)

**Three kinds of practice item, each with a provable label.** Every solvable item gets a twin, as in SUM, CoA's contrast set, When2Call and QuestBench.
1. **Unsolvable 24 hands, where the right move is "can't be done".** Brute force over +, −, ×, ÷ with exact fractions (run locally, `g24.py` in this folder) gives the counts below. Code proves unsolvability exhaustively, so the label is certain.

| Card range | Hands | Solvable | Unsolvable |
|---|---|---|---|
| 1-13 | 1820 | 1362 | 458 (25%) |
| 1-10 | 715 | 566 | 149 |
| 1-9 | 495 | 404 | 91 |

   - The target answer is "No solution. I checked every way to combine them." Evidence: SUM, AbstentionBench.
2. **Missing-number puzzles, where the right move is to ask.** Take a solvable item and hide one card or one quantity. Keep the item only if code confirms that at least two values of the hidden quantity lead to different answers, or that some values give a solution and others do not. The correct question names the hidden slot, and the checker verifies the name exactly. The simulated human then gives the value and the model must solve. Evidence: QuestBench's one-missing-variable construction, ACA-RL's premise removal.
3. **Ambiguous code tasks, where the right move is to ask.** Keep a task only if two readings of the spec each pass the visible tests but give different results on hidden tests. Code proves this, following ClarifyGPT's consistency check and HumanEvalComm's "ambiguity" edit. A question is correct if the simulated human's answer picks one reading and the final code then passes that reading's hidden tests. Evidence: ClarifyGPT, ClarifyCoder, Ambig-SWE.
- Also keep a fourth bucket: **hard but solvable items the model has not cracked yet.** Here "I couldn't find it within budget; handing over" is honest but should earn *less* than solving. Keep it distinct from "can't be done". This is R-Tuning's certain/uncertain split, but the labels come from the checker.

**Reward (one change at a time; defaults to test, not results).**
- Solve correctly: +1. Wrong answer or silent guess: −t/(1−t), with t = 0.75 giving −3 (Kalai). Use −1 if that proves too harsh (TruthRL).
- The right question on a truly missing-information item, followed by a correct solve after the reply: +1. A "can't" on a missing-information item: +0.25. On a truly unsolvable item, "can't, with a checkable reason": +1. This follows ACA-RL's ordering.
- Asking or abstaining on a solvable twin: −0.25. This keeps the abstain value inside the "moderate" band that Intellectual Humility found safe, and it is the anti-laziness term.
- Handing over after the budget on a hard solvable item: 0.
- **Do not make "abstain" a bare rewarded action in the first experiment.** Because of the 1.5B collapse result, first try the Abstention Collapse paper's fix: the model always writes a confidence, the confidence is scored with a Brier score (RLCR), and the decision to ask or abstain is made by a fixed threshold at test time. In Ben's hits-only sleep, "abstain" counts as a hit only on items with a proven unsolvable or ambiguous label. It never counts on a solvable twin.
- Mix ratio: start at 10% unsolvable plus 10% missing-information items (Hallucination Tax), and change it only as its own separate experiment.

**Pass marks (fixed before running; the numbers are Claude's proposals, and Ben should edit them before the first run).**
- **P1, recall.** On held-out unsolvable 24 hands, the model says "can't" in ≥ 70% of them.
  - *Proves it wrong:* ≤ 10% after training. The Hallucination Tax 1.5B result (0.00 → 0.04) predicts this failure for small models.
- **P2, false-ask rate (anti-laziness).** On held-out solvable twins *that the model solved before this sleep*, it asks or abstains on ≤ 5%.
  - *Proves it wrong:* > 10%, or a rise that tracks the rise in P1. That is the collapse and over-conservatism pattern (Abstention Collapse, When2Call).
- **P3, forced-guess laziness check (I-CALM two-stage).** Whenever the model abstains on any item, force a best guess afterwards. If the forced guess passes the checker on > 30% of abstentions on solvable items, the abstentions are lazy.
- **P4, right-question rate.** On missing-number items, the question names the hidden slot in ≥ 60% of cases, and the item is solved after the reply in ≥ 50%.
  - *Proves it wrong:* the model asks, but the question is generic, i.e. it does not name the slot. That matches the finding in InfoQuest and CLAMBER.
- **P5, no accuracy tax.** Accuracy on solvable items drops ≤ 2 points compared with the same run without the extra items.
- **P6, give-up effort.** The median number of guesses before a "can't" is ≤ the median number of guesses to a hit on solvable items (SURE, MiP).
- Report all six as pass^k over k = 4 samples (τ-bench), because a model that asks correctly only sometimes is unreliable.

**Plain-language summary for Ben.** Right now, a model that trains on its own wins learns that guessing is always worth it, because a wrong guess costs nothing. Research shows this training wipes out "I don't know" unless you mix in problems that truly can't be solved, and that it is especially hard for small models like yours. So we build practice problems where a computer can *prove* the answer is "impossible" or "you need to tell me X" (impossible 24 hands, puzzles with a hidden number, code with two readings). We give points for honest "can't" and good questions, and we take points away for asking when the model could have solved it. Then we check two numbers every night: does it say "can't" on the impossible ones, and does it keep solving the ones it already could.
