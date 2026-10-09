# Papers on the warm-up blocker (creative test, B2)

Written 2026-10-06 by the Sonnet papers thread. Papers only, no ideas (the Opus roadmap thread turns these into decisions).
Sources: web search result summaries and abstracts. Claims below are what the papers' abstracts say; none were re-run here. Not read in full: marked "abstract only".

The blocker: B2 (3.3M from scratch, thinker writes programs, exact executor) samples many program tries per puzzle, keeps only tries that reproduce every shown example, trains on those. Only 0.2-0.4% of tries follow the rules and 1-3 of 256 puzzles get an accepted try, even after a two-number warm-up, because real puzzles need three numbers and chaining. Tries are peaked (few distinct programs).

## A. Bootstrapping / cold start for expert iteration

1. **STaR: Bootstrapping Reasoning with Reasoning** (Zelikman et al., NeurIPS 2022) https://arxiv.org/pdf/2203.14465
   - Claim: sample rationales, keep the ones reaching the right answer, fine-tune, repeat; "rationalization" (give the answer as a hint, regenerate the reasoning) rescues problems the model never solves.
   - Why it matters: the paper itself says the first round only works if few-shot accuracy is above chance. That is exactly our cold-start gap (0.2-0.4%). Rationalization is the paper's own fix for zero-success puzzles, the analogue of showing the model the answer/examples.

2. **Beyond Human Data: Scaling Self-Training (ReST-EM)** (Singh et al. 2023) https://arxiv.org/abs/2312.06585
   - Claim: generate, filter with a binary check, fine-tune, repeat a few times; beats fine-tuning on 3x more human data on MATH and APPS.
   - Why: it is the same loop as our test with a verifier as the filter. Needs a base model that already succeeds sometimes (pretrained PaLM-2). Also reports that pass@1 rises while the pass@k gap stays.

3. **Reinforced Self-Training (ReST)** (Gulcehre et al. 2023) https://arxiv.org/abs/2308.08998 (abstract only)
   - Claim: split into Grow (sample a dataset offline) and Improve (train on filtered data with raised thresholds, repeated), reusing the data across passes.
   - Why: gives a standard recipe for raising the keep threshold over rounds, and for reusing the few accepted tries instead of discarding them.

4. **Self-Improving Transformers Overcome Easy-to-Hard and Length Generalization** (Lee et al., ICML 2025) https://arxiv.org/abs/2502.01612
   - Claim: small transformers trained from a seed set of short problems self-label slightly longer problems each round, filter for correctness, and generalize from 10-digit to 100-digit addition; starting from a pretrained model speeds it up.
   - Why: closest published match to "short warm-up, then longer compositions", with transformers trained from scratch and an exact filter. They add each round only a slightly harder length, so the success rate stays above zero. Also shows filtering (not just generating) drives the gain.

## B. Program synthesis with hindsight / self-training (ARC-style)

5. **CodeIt: Self-Improving Language Models with Prioritized Hindsight Replay** (Butt et al. 2024) https://arxiv.org/abs/2402.04858
   - Claim: when a sampled program does not solve the task, relabel the task as "whatever this program actually outputs" and train on that pair; replay prioritized. Reaches 15% of ARC eval, above prior neural and symbolic baselines.
   - Why: the strongest direct answer to "almost no tries pass". Every try becomes a valid (program, input, output) example for a different puzzle, so 100% of tries give training signal instead of 0.2-0.4%. Works in our exact-executor setting because the executor can run any program.

6. **SOAR: Self-Improving Language Models for Evolutionary Program Synthesis** (Pourcel, Colas, Oudeyer, ICML 2025) https://huggingface.co/julien31/Soar-qwen-32b (model card; paper title: "Self-Improving Language Models for Evolutionary Program Synthesis: A Case Study on ARC-AGI")
   - Claim: alternate search (sample programs, refine the best ones) with learning; failed programs are relabeled as correct solutions to the synthetic tasks they accidentally solve, and used as training data.
   - Why: same hindsight idea as CodeIt plus a refine step: edit a near-miss program instead of resampling from scratch (useful when two-number programs almost solve three-number puzzles).

7. **Combining Induction and Transduction for Abstract Reasoning** (Li et al., ICLR 2025) https://arxiv.org/abs/2411.02272
   - Claim: models trained on large synthetic sets of (program, input generator) pairs; induction (write the program) is better at precise computation and composing several concepts.
   - Why: shows synthetic program/puzzle data is the main training source, and that program-writing models do well on composition. Supports generating synthetic puzzles with known programs instead of waiting for self-found ones. (Abstract only; their synthetic data came from LLM-written code, which we cannot use.)

## C. Wake-sleep / learned search policy

8. **DreamCoder: Growing generalizable, interpretable knowledge with wake-sleep Bayesian program learning** (Ellis et al.; PLDI 2021) https://arxiv.org/abs/2006.08381
   - Claim: wake = solve problems by search; sleep = (a) store common sub-programs as new library primitives, (b) train the neural search policy on "dreams" (programs sampled from the library, run to get tasks), not just on solved tasks.
   - Why: the dream phase is the synthetic warm-up: random programs with known answers train the policy, so it does not depend on its own rare wins. Library learning turns frequent two-step chains into one primitive, which shortens the chaining problem.

9. **DeepCoder (Balog et al. 2017) and RobustFill (Devlin et al. 2017)** https://arxiv.org/abs/1703.07469 (RobustFill) (abstract only)
   - Claim: neural program synthesis trained on millions of randomly generated program + input/output pairs, tested on real tasks; RobustFill reaches 92% on a real-world test set.
   - Why: the classic version of "synthetic warm-up data": sample random programs, run them, train the model to invert. Our small card-style puzzles are the same kind of domain.

## D. Short-to-long composition and curricula

10. **Extrapolation by Association: Length Generalization Transfer in Transformers** (2025) https://arxiv.org/abs/2506.09251
    - Claim: training jointly with a longer related auxiliary task transfers length generalization to the target task; evidence points to heads being reused between tasks.
    - Why: bears on whether two-number warm-up transfers to three numbers. It says transfer happens when tasks are related and the longer task is in the mix, which is a reason to mix 2- and 3-number items instead of 2 then 3.

11. **ExeDec: Execution Decomposition for Compositional Generalization in Neural Program Synthesis** (2023) https://arxiv.org/abs/2307.13883
    - Claim: have the model predict the next sub-goal (the intermediate output after the next step) and run the program step by step with the executor, which improves generalization to longer compositions.
    - Why: our chaining failure is "one result into a second step". Predicting and executing one step at a time, with the executor feeding back the real intermediate value, gives credit for a correct first step even when the whole program fails.

12. **Curriculum learning with Hindsight Experience Replay (CHER)** (Fang et al. 2019, NeurIPS) https://papers.nips.cc/paper_files/paper/2019/file/83715fd4755b33f9c3958e1a9ee221e1-Paper.pdf (abstract only; also arXiv 2008.09377)
    - Claim: in sparse-reward goal tasks, mix hindsight relabeling with a curriculum that picks goals by closeness to the agent's current reach and by diversity.
    - Why: the RL ancestor of CodeIt, plus a goal-selection rule that balances "easy enough to succeed" with "diverse".

13. **Absolute Zero: Reinforced Self-play Reasoning with Zero Data** (Zhao et al., NeurIPS 2025) https://neurips.cc/virtual/2025/poster/116121
    - Claim: one model proposes tasks and solves them, with a code executor as the check and a learnability reward that favors tasks of mid difficulty; no external data.
    - Why: a mechanism for choosing which puzzles to attempt (not too hard, not too easy) when the success rate is near zero. Uses a pretrained coder; no from-scratch tiny model.

## E. Keeping diversity / avoiding collapse

14. **Assessing Diversity Collapse in Reasoning** (Dang et al., ICLR 2025 workshop) https://iclr.cc/virtual/2025/10000515
    - Claim: as pass@1 improves during supervised fine-tuning, pass@k falls and does not recover with later RL or self-improvement; probability mass collapses onto one reasoning path.
    - Why: matches our peaked tries. Training on only the few accepted tries risks locking in the first lucky program.

15. **Self-Improvement Can Self-Regress: The Rise-and-Collapse Failure Mode of LLM Self-Training** https://arxiv.org/pdf/2606.21090 (abstract/summary only; could not confirm authors)
    - Claim (as summarized in search): iterative SFT/DPO raises pass@1 but cuts output diversity and OOD generalization, and biases toward easier problems.
    - Why: a warning that self-training on easy accepted tries drifts toward easy puzzles, which could mean the 3-number puzzles never get tried.

16. **Outcome-based Exploration for LLM Reasoning** https://arxiv.org/pdf/2510.15502v1 (summary only)
    - Claim (as summarized): rewarding rare outcomes or using pass@k-style objectives counters the diversity loss from pass@1 rewards.
    - Why: gives named ways to keep the sample spread wide while filtering.

## Gaps / honest limits
- Almost every self-training paper above starts from a pretrained model that already succeeds sometimes. Only Lee et al. (item 4) trains small transformers from near scratch, and with a growing-length curriculum. None addresses a 3.3M model with a 0.2-0.4% base success rate directly.
- I did not find a paper that measures a 2-number to 3-number warm-up transfer for a program-writing model specifically. Items 4, 10 and 11 are the closest.
- I did not re-run or check any numbers; they are what the abstracts and search summaries state.
