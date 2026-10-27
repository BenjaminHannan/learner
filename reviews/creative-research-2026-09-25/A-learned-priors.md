# A. Can a learned model know "where to look" on hard, real problems?

Question (Ben): in the real world, do a problem's inputs predict where its solution is, so that a model can learn an intuition that guides search?
Our design, for reference: a learned prior proposes many guesses, an exact checker keeps the right ones, and in "sleep" the model trains on its own verified hits.

**How it was checked (2026-09-25).** Every quote below was copied from text fetched with curl:
arXiv abstracts from `https://arxiv.org/abs/<id>` (meta `citation_abstract`), Nature papers from `https://www.nature.com/articles/<doi-suffix>`, and PDFs/HTML where noted.
The arXiv export API returned HTTP 406 and OpenAlex/Semantic Scholar were rate-limited, so abs pages were used instead.
Labels: **SHOWN** = measured in the paper. **SUGGESTED** = argued or indirect. **DISPUTED** = contested by other measured work.

---

## 1. Direct evidence that a learned prior guides search on hard problems

**1.1 AlphaGo Zero.** Silver et al., "Mastering the game of Go without human knowledge", *Nature* 2017, doi:10.1038/nature24270.
Verified via nature.com (abstract) and the UCL preprint PDF `discovery.ucl.ac.uk/id/eprint/10045895/1/agz_unformatted_nature.pdf`.
- Quote (abstract): "a neural network is trained to predict AlphaGo's own move selections and also the winner of AlphaGo's games. This neural network improves the strength of the tree search".
- Quote (preprint): "The raw neural network, without using any lookahead, achieved an Elo rating of 3,055. AlphaGo Zero achieved a rating of 5,185".
- Plain: the network alone plays at professional level, and the network plus search is far stronger than either part. The prior and the search complement each other. **SHOWN.**
- Design link: this is our loop exactly (search, then train on search results, then search better). Here the "checker" is winning the game.

**1.2 AlphaZero.** Silver et al., arXiv:1712.01815 (2017; later *Science* 2018).
- Quote: "Starting from random play, and given no domain knowledge except the game rules, AlphaZero achieved within 24 hours a superhuman level of play in the games of chess and shogi (Japanese chess) as well as Go". **SHOWN.**
- Design link: the prior was learned entirely from its own play. Nothing was copied from humans.

**1.3 Expert Iteration.** Anthony, Tian, Barber, "Thinking Fast and Slow with Deep Learning and Tree Search", NeurIPS 2017, arXiv:1705.08439.
- Quote: "tree search is improved by using the neural network policy to guide search, increasing the strength of new plans ... ExIt outperforms REINFORCE for training a neural network to play the board game Hex". **SHOWN.**
- Design link: this paper names our "sleep" loop: search (slow) produces the targets, and the network (fast) imitates them.

**1.4 AlphaGeometry.** Trinh, Wu, Le, He, Luong, "Solving olympiad geometry without human demonstrations", *Nature* 2024, doi:10.1038/s41586-023-06747-5. Verified via nature.com full text.
- Quote (abstract): "a neural language model ... to guide a symbolic deduction engine through infinite branching points ... On a test set of 30 latest olympiad-level problems, AlphaGeometry solves 25, outperforming the previous best method that only solves ten".
- Quote (ablation): "incorporating algebraic deduction added seven solved problems to a total of 14 (DD + AR), whereas the language model's auxiliary construction remarkably added another 11 solved problems, resulting in a total of 25."
- Quote: "with a beam size of 8, that is, a 64 times reduction from the original beam size of 512, AlphaGeometry still solves 21 problems."
- Plain: the exact engine alone solved 14/30. The learned "where to add a point" guess raised this to 25/30, and even a much smaller search solved 21/30. **SHOWN.**
- Design link: this is the cleanest case of a learned proposer plus an exact checker. The prior was trained only on synthetic, machine-checked data.

**1.5 AlphaProof.** Hubert, Mehta, Sartran, et al. (39 authors), "Olympiad-level formal mathematical reasoning with reinforcement learning", *Nature*, doi:10.1038/s41586-025-09833-y.
Search results say it was published online November 2025; the page metadata gives 2026/03 (issue date). Verified via nature.com full text.
- Quote (abstract): "For the most difficult problems, it uses test-time RL, a method of generating and learning from millions of related problem variants at inference time ... solved three out of the five non-geometry problems, including the competition's most difficult problem."
- Quote (results): TTRL increased "solve rates by an additional 15 absolute percentage points on both formal-imo and PutnamBench-test compared with a 12 TPU hours search". The IMO solutions "each ... required 2–3 days of TTRL".
- Quote (limits): the problems "operate within a known fixed library of mathematical concepts with a certain degree of thematic consistency ... extending these capabilities to the frontiers of research mathematics ... is particularly challenging".
- Plain: training on your own verified hits from nearby variants of a hard problem solved problems that more search alone did not. **SHOWN.**
- Design link: TTRL is the closest published match to our "sleep". The difference is that it trains on self-made *variants* of the target problem, not only on the target itself.

**1.6 Neural MIP solving.** Nair et al., "Solving Mixed Integer Programs Using Neural Networks", arXiv:2012.13349 (2020).
- Quote: "the learning-augmented SCIP is 2x to 10x better on all datasets except one on which it is $10^5$x better, at large time limits", measured on "six diverse real-world datasets, including two Google production datasets and MIPLIB".
- Plain: on real industrial optimization problems, a network learned from similar instances where good answers tend to lie. **SHOWN.**
- Design link: this is real-world evidence that instance features predict good assignments ("Neural Diving"), with the exact solver finishing the job.

**1.7 Davies et al.** "Advancing mathematics by guiding human intuition with AI", *Nature* 2021, doi:10.1038/s41586-021-04086-x. Verified via nature.com full text.
- Quote: "we trained a feed-forward neural network to predict the signature from measurements of the geometry on a dataset of randomly sampled knots. The model was able to achieve an accuracy of 78% on a held-out test set ... substantially higher than chance (a baseline accuracy of 25%)".
- Plain: in research mathematics, easy-to-compute features of an object predicted a hard invariant well above chance. Attribution then pointed humans to a new theorem. **SHOWN** for the prediction; **SUGGESTED** for "intuition" in general.
- Caution: their first conjecture had counterexamples ("we were able to construct counterexamples"), so the learned pattern needed an exact check.

**1.8 NeuroSAT.** Selsam et al., "Learning a SAT Solver from Single-Bit Supervision", arXiv:1802.03685 (2018; ICLR 2019).
- Quote: "Although it is not competitive with state-of-the-art SAT solvers, NeuroSAT can solve problems that are substantially larger and more difficult than it ever saw during training".
- Plain: a network learns real structure in NP-complete problems, but on its own it is weaker than hand-built search. **SHOWN** (including the limit).

## 2. Formal theorem proving: learned prior + exact checker (Lean/Metamath) + training on own proofs

**2.1 GPT-f.** Polu & Sutskever, arXiv:2009.03393 (2020).
- Quote: "GPT-f found new short proofs that were accepted into the main Metamath library ... the first time a deep-learning based system has contributed proofs that were adopted by a formal mathematics community." **SHOWN.**

**2.2 Expert iteration for maths.** Polu, Han, Zheng, Baksys, Babuschkin, Sutskever, "Formal Mathematics Statement Curriculum Learning", arXiv:2202.01344 (2022; ICLR 2023).
- Quote: "at same compute budget, expert iteration, by which we mean proof search interleaved with learning, dramatically outperforms proof search only ... capable of finding and solving a curriculum of increasingly difficult problems, without the need for associated ground-truth proofs."
- Table (PDF): on mathlib-valid, pass@1 went from 46.7% (θ0) to 56.3% (θ1) after one round of training on its own found proofs. **SHOWN.**
- Design link: this is the strongest direct test of "train on own hits beats more guessing at equal compute".

**2.3 HyperTree Proof Search.** Lample et al., arXiv:2205.11491 (NeurIPS 2022).
- Quote: "a model trained on annotated proofs manages to prove 65.4% of a held-out set of Metamath theorems ... Online training on these unproved theorems increases accuracy to 82.6%." **SHOWN.**

**2.4 LeanDojo / ReProver.** Yang et al., arXiv:2306.15626 (NeurIPS 2023 D&B).
- Quote: premise selection is "a key bottleneck in theorem proving"; the benchmark has a split "requiring the prover to generalize to theorems relying on novel premises that are never used in training"; the paper reports "the effectiveness of ReProver over non-retrieval baselines and GPT-4".
- Plain: the theorem statement predicts which library lemmas will be needed. This is "where to look" in the literal sense. **SHOWN** (the abstract gives no number).

**2.5 DeepSeek-Prover V1 / V1.5 / V2.** arXiv:2405.14333, 2408.08152, 2504.21801.
- V1 quote: "46.3% with 64 samples and 52% cumulatively on the Lean 4 miniF2F test, surpassing the baseline GPT-4 at 23.0%".
- V2 quote: "88.9% pass ratio on the MiniF2F-test and solving 49 out of 658 problems from PutnamBench". **SHOWN.**
- Note: miniF2F is high-school competition level. PutnamBench (49/658, about 7%) is the harder signal.

**2.6 Goedel-Prover V1/V2.** Lin et al., arXiv:2502.07640 and 2508.03613 (2025).
- V1 quote: "Each new prover can prove many statements that previous ones could not, and these new proofs are added to the training set for the next prover." (This is expert iteration.)
- V2 quote: "Model averaging: We merge model checkpoints to mitigate the decrease in model output diversity in later stages of training." The model "solves 86 problems on PutnamBench at pass@184". **SHOWN.**
- Design link: they report the warning we should expect. Training on own hits *narrows* the guesses, and they needed a fix to keep diversity.

**2.7 Kimina-Prover.** arXiv:2504.11354: "80.7% with pass@8192" on miniF2F. **Seed-Prover** (ByteDance), arXiv:2507.23726: "proves 78.1% of formalized past IMO problems ... fully prove 5 out of 6 problems" at IMO 2025. **SHOWN.**

**2.8 STaR.** Zelikman et al., arXiv:2203.14465 (NeurIPS 2022).
- Quote: "fine-tune on all the rationales that ultimately yielded correct answers; repeat ... performs comparably to fine-tuning a 30× larger state-of-the-art language model on CommensenseQA." **SHOWN.**
- Note: these are easier tasks, included only as the plain-language version of "train on own hits".

## 3. Discovery on open problems (the checker scores, the LLM proposes)

**3.1 FunSearch.** Romera-Paredes et al., "Mathematical discoveries from program search with large language models", *Nature* 2024, doi:10.1038/s41586-023-06924-6. Verified via nature.com full text.
- Quote: "we discover new constructions of large cap sets going beyond the best-known ones ... This shows that it is possible to make discoveries for established open problems using LLMs." In n = 8 it found "a cap set of size 512".
- Quote on diversity: "Preserving and encouraging diversity of programs in the database is crucial to enable exploration and avoid being stuck in local optima." **SHOWN.**
- Design link: the prior here is a fixed LLM (no retraining). Improvement comes from putting the best past hits into the prompt ("best-shot prompting"), plus islands for diversity.

**3.2 AlphaEvolve.** Novikov et al., arXiv:2506.13131 (2025 white paper).
- Quote: "found a procedure to multiply two $4 \times 4$ complex-valued matrices using $48$ scalar multiplications; offering the first improvement, after 56 years, over Strassen's algorithm in this setting." **SHOWN.**
- Follow-up: Georgiev, Gómez-Serrano, Tao, Wagner, "Mathematical exploration and discovery at scale", arXiv:2511.02864. Quote: "a list of 67 problems ... The system rediscovered the best known solutions in most of the cases and discovered improved solutions in several." **SHOWN.** Honest reading: it mostly *matches* the best known results and improves on only a few.
- Earlier relative: AlphaTensor (Fawzi et al., *Nature* 2022, doi:10.1038/s41586-022-05172-4): "improves on Strassen's two-level algorithm for the first time ... since its discovery 50 years ago" (4×4, finite field). **SHOWN.**

**3.3 Open Erdős problems with formal (exact) checking.** Tsoukalas et al. (Google DeepMind), "Advancing Mathematics Research with AI-Driven Formal Proof Search", arXiv:2605.22763 (May 2026). Verified via arXiv abs and HTML.
- Quote: "Our most capable agent autonomously resolved 9 of 353 open Erdős problems at the per-problem cost of a few hundred dollars, proved 44/492 OEIS conjectures ... A basic agent alternating LLM-based generation with Lean-based verification replicated the Erdős successes but proved costlier on the hardest problems."
- Quote: "The effectiveness of our basic agent in our post-hoc analysis was surprising."
- Plain: a simple loop that guesses and then checks exactly solved about 2.5% of real open problems. Cleverer search mainly saved cost. **SHOWN.**
- Design link: this is our architecture at research scale. The success rate is low but not zero, and the prior matters more than elaborate search.

**3.4 Semi-autonomous Erdős study.** Feng, Trinh, et al., arXiv:2601.22401 (Jan 2026).
- Quote: "700 conjectures labeled 'Open' ... We address 13 problems ...: 5 through seemingly novel autonomous solutions, and 8 through identification of previous solutions in the existing literature. Our findings suggest that the 'Open' status of the problems was through obscurity rather than difficulty ... the risk of ''subconscious plagiarism'' by AI." **SHOWN** (counts); **SUGGESTED** (the "obscurity" reading).
- Note: a search summary gave "4 novel / 9 literature" (the v1 figures, repeated in arXiv:2602.10177). The current abstract says 5/8.

## 4. Scaling the number of guesses (coverage) and spending compute wisely

**4.1 Large Language Monkeys.** Brown et al., arXiv:2407.21787 (2024).
- Quote: "coverage -- the fraction of problems that are solved by any generated sample -- scales with the number of samples over four orders of magnitude ... often log-linear ... SWE-bench Lite ... increases from 15.9% with one sample to 56% with 250 samples".
- Second quote: "In domains without automatic verifiers ... majority voting and reward models plateau beyond several hundred samples". **SHOWN.**
- Design link: many guesses plus an exact checker is the regime where repeated sampling pays off. Without an exact checker it stalls.

**4.2 Snell et al.** "Scaling LLM Test-Time Compute Optimally ...", arXiv:2408.03314 (2024; ICLR 2025).
- Quote: "the effectiveness of different approaches to scaling test-time compute critically varies depending on the difficulty of the prompt ... improve the efficiency ... by more than 4x compared to a best-of-N baseline ... on problems where a smaller base model attains somewhat non-trivial success rates, test-time compute can be used to outperform a 14x larger model." **SHOWN.**
- Design link: search helps only where the prior already puts *some* probability on the answer.

## 5. Limits and counter-evidence

**5.1 No Free Lunch.** Wolpert & Macready, *IEEE Trans. Evol. Comp.* 1(1):67–82, 1997, doi:10.1109/4235.585893. Verified via PDF at cs.ubc.ca/~hutter/earg/papers07/00585893.pdf.
- Quote: "for any algorithm, any elevated performance over one class of problems is offset by performance over another class."
- Plain: a learned prior can beat random guessing only if the problems you meet share structure with the ones you trained on. **SHOWN** (theorem, averaged over *all* problems). It does not say real problems lack structure. Sections 1–3 are evidence that they have some.

**5.2 RL on own hits may only sharpen, not expand.** Yue et al., "Does Reinforcement Learning Really Incentivize Reasoning Capacity in LLMs Beyond the Base Model?", arXiv:2504.13837 (2025).
- Quote: "While RLVR-trained models outperform their base models at small k (e.g., k = 1), the base models achieve a higher pass@k score when k is large ... the observed reasoning abilities originate from and are bounded by the base model."
- Rebuttals: ProRL (Liu et al., arXiv:2505.24864): "RL-trained models consistently outperform base models across a wide range of pass@k evaluations, including scenarios where base models fail entirely regardless of the number of attempts" (with KL control and reference resets). Wen et al. (arXiv:2506.14245): "RLVR can extend the reasoning boundary", using a CoT-Pass@K metric.
- Label: **DISPUTED.** This is the most important open question for our "sleep" step.
- Design link: our pass mark should be *coverage at large k*, not only hit rate at k = 1. Training on own hits can make guesses more accurate while losing rare correct guesses.

**5.3 Model collapse.** Shumailov et al., "AI models collapse when trained on recursively generated data", *Nature* 2024, doi:10.1038/s41586-024-07566-y.
- Quote: "indiscriminate use of model-generated content in training causes irreversible defects in the resulting models, in which tails of the original content distribution disappear." **SHOWN** (for *unfiltered* self-training).
- Design link: our exact checker filters out wrong outputs, but kept hits can still over-represent easy cases. Goedel-V2 (2.6) and FunSearch (3.1) both needed explicit fixes to keep diversity.

**5.4 Hard open problems mostly remain unsolved, even with exact verifiers.**
- *FrontierMath Erdős* (Adamczewski & Bloom, arXiv:2609.25050, Sept 2026). Quote: "68 Erdős problems that are open as of August 2026 ... resolve ... in the proof assistant Lean ... We evaluated five AIs with a budget of \$300 per problem. One (GPT-6 Astra) scored 3%, and all others scored 0%." **SHOWN.** (Here "GPT-6 Astra" is an OpenAI model, not our lead agent.)
- *FrontierMath: Open Problems* (Epoch AI, page epoch.ai/frontiermath/open-problems, fetched 2026-09-25). Unsolved problems, each with a computer verifier. Page shows "Solved (AI) (4) Solved (human + AI) (4) ... Unsolved (41)". By notability: "Moderately interesting 5 / 22 ... Solid result 2 / 18 ... Major advance 1 / 6 ... Breakthrough 0 / 3". **SHOWN** (live tally).
- *FrontierMath* original paper (Glazer et al., arXiv:2411.04872, Nov 2024): "Current state-of-the-art AI models solve under 2% of problems". **SHOWN** for then. It is now outdated: current Tier 4 leaderboard values appeared only on third-party aggregators, which were not verified and are not used here.
- *Humanity's Last Exam* (Phan et al., arXiv:2501.14249): "State-of-the-art LLMs demonstrate low accuracy and calibration on HLE". **SHOWN** for Jan 2025. Current scores were not verified.
- Plain: the success rate falls steeply with real difficulty. Wins cluster on "long-tail" and obscure problems (5.4 and 3.4), not on breakthroughs.

**5.5 ARC: brute search versus generalization.** Chollet et al., "ARC-AGI-2", arXiv:2505.11831 (2025). Verified via arXiv HTML.
- Quote: "49% of the Private Evaluation set was successfully solved by at least one team. Crucially, the dominant techniques employed by these successful submissions were reported to be variations of brute-force program search."
- Plain: on novel puzzles, blind search covers about half and the rest needs abstraction a prior did not provide. ARC-AGI-2 was built to resist this. **SHOWN** (the ARC-AGI-1 meta-analysis). Current ARC-AGI-2/3 leaderboard numbers load by JavaScript and were not verified.

**5.6 Where learned priors misled.**
- Davies 2021 (1.7): the first ML-suggested conjecture was false ("we were able to construct counterexamples").
- Feng et al. 2026 (3.4): many "solutions" were rediscoveries of existing literature ("subconscious plagiarism").
- The Quanta article (Aug 3 2026, quantamagazine.org/why-the-legendary-erdos-problems-are-falling-to-ai-20260803/) reports a user whose AI "solution" to Erdős #333 was already in "a paper published in 1977", quoting him: "As someone who has fallen for this twice now, it's quite gut-wrenching." **SHOWN** (anecdotes).
- The widely reported October 2025 "GPT-5 solved 10 Erdős problems" episode surfaced only in search snippets and was **not verified** here, so it is not relied on.

---

## Dropped / not verified
- Current leaderboard numbers for FrontierMath Tier 4, ARC-AGI-2/3 and HLE. Epoch and ARC pages render scores with JavaScript, and only aggregators showed numbers.
- "Tao wiki: AI contributions to Erdős problems": GitHub fetch was blocked by the session's repository binding.
- Bryan, Elek, Manners, Salafatinos, Vakil, arXiv:2601.07222 (Jan 2026) is real ("The proof of this result was obtained in conjunction with Google Gemini"). It is a single anecdote, so it is only mentioned here.

## Bottom line for our design
1. **Yes, features predict where solutions are, but only within a family of related problems.** Evidence: Go (3,055 → 5,185 Elo with search), geometry (14 → 25/30), real MIPs (2–10×), knots (78% vs 25% chance). All SHOWN.
2. **Training on own verified hits works on hard formal problems.** Evidence: expert iteration (46.7 → 56.3%), HTPS (65.4 → 82.6%), AlphaProof TTRL (+15 points). SHOWN.
3. **It can shrink diversity.** Yue et al. (DISPUTED), Goedel-V2 and FunSearch all had to protect diversity. Measure pass@large-k before and after each sleep.
4. **At the research frontier, the hit rate is small.** Evidence: 9/353 Erdős; 3% on FME; 0/3 breakthroughs on FrontierMath Open Problems. An exact checker makes the rare hit trustworthy, but it does not make hits common.
