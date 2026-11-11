# Papers for the "creative model" roadmap (2026-10-06)

Question: Ben defines creativity as "say random stuff, then filter": when the reasoner cannot solve something, a creative part blurts many varied tries, a checker or judge keeps the lucky ones, and "sleep" writes the lucky ones into the model so the reasoner can do it alone next time. What does the 2024-2026 evidence say beyond STaR, ReST-EM, expert iteration, HER, Tree of Thoughts, AlphaProof, FunSearch, AlphaEvolve, Go-Explore, Absolute Zero and Yue 2025 (RL narrows pass@k)?

How this list was made
- Every paper in sections A to H (40 entries) and in the "Also verified" list was opened on its arXiv abstract page (WebFetch) and its exact title, first author, date and arXiv id were checked. Papers I could not verify were dropped (see "Dropped or not used").
- Numbers come from the abstract unless the entry says "(full text)" or "(repo page)". I never took a number from a search-result snippet.
- Labels: **shown** = measured in the paper; **suggested** = argued, narrow, or my own inference; **disputed** = other measured work disagrees.
- Tag [NEW] = the arXiv id does not appear in any md/py/txt/json file under /home/user/learner. [in repo] = it already appears in some repo note (so it is not new to the project, only to this list).
- "For us" lines are split: **Thinker** = the small program-writing model plus exact executor (card-sized experiments); **Minecraft** = the village model and the north star. Keep these two apart when you quote them.
- Scale warning: most pass@k, diversity and creativity evidence below is from 3B to 32B+ LLMs, not 3 to 11M models trained from scratch. The genuinely small or from-scratch evidence is: Lee 2025 (A3), HRM/TRM (F32 to F35), CompressARC (F37), Craftax baselines (D22), DreamerV3 12M to 400M (D18), Craftax-Classic and Crafter world models (D23, D24). Everything else is "suggested" when applied to your thinker.

## Plain-language summary for Ben

- Your idea is a real, studied loop. In program space it is called wake-sleep (DreamCoder, 2020), CodeIt (2024) and SOAR (2025). SOAR got a 7B model from 14% to 36% on ARC puzzles by running this loop.
- The big new ingredient is "hindsight relabeling": a wrong try is still a perfect answer to a different question, so you can keep it and train on it (CodeIt, STEVE-1 in Minecraft, HSL in 2026).
- The big danger is that training only on winners makes the model repeat itself, so the variety you need for creativity dies. Fixes with evidence: also learn from the losers (negative reinforcement), reward groups of tries instead of single tries, invent sibling questions, and choose sleep examples for variety, not only for being right.
- "Creative" can be measured: quality times novelty. Bigger models are more correct but less varied, so being small is not automatically a creativity handicap.
- Tiny models like TRM (7M) do well on puzzles, but mostly because they get many augmented views and a vote, and because they are told which task it is. That is blurt-and-filter in disguise, not deep thinking.
- For Minecraft: from pixels, the best verified diamond result is Dreamer 4 at 0.7% of episodes with a 2-billion-parameter world model. Nobody has shown a tiny model beating Minecraft. Small Crafter-like games are already solved by small world models, so that is where to practise.

---

## A. Generate-and-filter, self-training, keeping variety

**A1. Large Language Monkeys: Scaling Inference Compute with Repeated Sampling** - Bradley Brown et al., 2024, arXiv 2407.21787 [in repo]
- Did: sampled many answers per problem and measured "coverage" (any sample is right).
- Result **shown**: coverage grows log-linearly over four orders of magnitude of samples; SWE-bench Lite with DeepSeek-Coder-V2-Instruct went from 15.9% (1 sample) to 56% (250 samples), above the 43% single-attempt record then; where no automatic verifier exists, majority vote and reward-model picking plateau after a few hundred samples.
- For us: **Thinker**: "blurt many, keep the lucky" works exactly as far as the checker can recognise a lucky try. An exact executor is the best checker possible, so program-writing is the right place to spend samples. **Minecraft**: the checker is "did the inventory or achievement change", exact for the early tech tree, missing for open-ended goals.

**A2. Mind the Gap: Examining the Self-Improvement Capabilities of Large Language Models** - Yuda Song et al., 2024, arXiv 2412.02674 [NEW]
- Did: formalised "model verifies its own outputs, filters, distils" and named the generation-verification gap.
- Result **shown**: improvement is governed by that gap; a variant of it scales monotonically with pre-training FLOPs across model families.
- For us: **Thinker**: **suggested** (my inference, not tested): a tiny model has a small gap, so it cannot grade its own tries well; filtering should come from the exact executor or from a bigger judge (the borrowed 1.2B), not from the thinker judging itself.

**A3. Self-Improving Transformers Overcome Easy-to-Hard and Length Generalization Challenges** - Nayoung Lee et al., 2025, arXiv 2502.01612 [in repo]
- Did: a transformer generates its own solutions to slightly harder problems, keeps only correct ones, retrains, repeats (arithmetic, string manipulation, mazes).
- Result **shown**: generalises from 10-digit to 100-digit addition "without apparent saturation"; filtering for correct self-generated examples gives "exponential improvements" in out-of-distribution accuracy across rounds; a pretrained start speeds it up; weak-to-strong curricula teach extrapolation with no architecture change.
- For us: **Thinker**: the closest published proof that the sleep loop works for plain small transformers; copy its "slightly harder each round" curriculum. Caveat **suggested**: its tasks have exact answers and a clean difficulty ladder, which creative tasks may not.

**A4. Pass@K Policy Optimization: Solving Harder Reinforcement Learning Problems** - Christian Walder et al., 2025, arXiv 2505.15201 [NEW]
- Did: a reward transformation over a batch that directly optimises pass@k (the joint value of k samples) with low-variance unbiased estimators.
- Result **shown**: on Gemma2 and Llama3.1 RL runs, pass@k optimisation keeps strong pass@1 while adding pass@k gains, and "unblocks learning" on task sets where pass@1 optimisation stalls.
- For us: **Thinker**: when the lucky try is rare, rewarding the group of tries instead of each try keeps variety while learning. **disputed** by A6 on whether pass@k should be a training objective.

**A5. The Surprising Effectiveness of Negative Reinforcement in LLM Reasoning** - Xinyu Zhu et al., 2025, arXiv 2506.01347 [in repo]
- Did: split RL into reinforcing correct samples and penalising wrong samples.
- Result **shown**: on Qwen2.5-Math-7B and Llama-3.1-8B-Instruct, negative-only training improves pass@k across the whole range (k up to 256), often matching PPO and GRPO; positive-only raises pass@1 but lowers pass@k through lost diversity; upweighting the negative part improves pass@k on MATH, AIME 2025, AMC23.
- For us: **Thinker**: sleep should also push probability away from wrong programs, not only copy lucky ones; copying only winners is what shrinks variety. Cheap to test as an unlikelihood term (**suggested**).

**A6. Pass@k Metric for RLVR: A Diagnostic Tool of Exploration, But Not an Objective** - Yang Yu et al., 2025, arXiv 2511.16231 [NEW]
- Did: analysed pass@k as a reweighting of pass@1.
- Result **shown** (analysis): the pass@k objective "provides a vanishing learning signal in regimes where exploration is most critical"; exploration collapse shrinks the pass@k to pass@1 gap; conclusion is to use pass@k as a scoreboard, not as the training target. **disputed**: conflicts with A4.
- For us: **Thinker**: report pass@1 and pass@k side by side as your creativity scoreboard, and test any pass@k-aware loss on your own cards before trusting either paper.

**A7. Beyond Pass@1: Self-play with Variational Problem Synthesis Sustains RLVR** - Xiao Liang et al., 2025, arXiv 2508.14029 [NEW]
- Did: during RL, the policy's correct solutions are used to write new variants of the training problems that keep the same answer; training continues on those.
- Result **shown**: keeps policy entropy up; absolute pass@32 gains of 18.3 and 22.8 points on AIME24 and AIME25; 12 benchmarks, 3B to 32B models.
- For us: **Thinker**: variety can come from changing the questions, not only the sampler: one lucky solution is turned into sibling tasks. This is your "creative part invents tasks" idea with measured support.

**A8. Forty Shades of Blue: Quality-Diversity Alignment via Mode-Conditioned Reinforcement Learning** - Jiayi Yuan et al., 2026 (14 Sep), arXiv 2609.14896 [NEW]
- Did: one LM conditioned on abstract "roles", each role exploring a different region of outputs, with adaptive quality gating.
- Result **shown**: SBERT diversity up 265% on held-out Infinity-Chat prompts while average general-capability pass@1 rose 10.3%; against the DivPO baseline, diversity 0.274 to 0.482 (+75.9%) and E-Vendi 2.86 to 4.4 (+53.8%). LLM scale; three weeks old; one paper.
- For us: **Thinker**: a small set of learned "mode codes" the blurter is conditioned on is a cheap way to force different tries (**suggested**).

## B. Measuring creativity and diversity

**B9. NoveltyBench: Evaluating Language Models for Humanlike Diversity** - Yiming Zhang et al., 2025, arXiv 2504.05228 [in repo]
- Did: a benchmark that counts how many distinct, high-quality outputs a model gives for prompts that allow many answers.
- Result **shown**: 20 leading models give far less diversity than humans; larger models in a family are often less diverse than smaller ones; in-context regeneration helps.
- For us: **Thinker**: copy the idea "count distinct classes among k samples", where for programs a class is "behaves differently on the test inputs".

**B10. CreativeBench: Benchmarking and Enhancing Machine Creativity via Self-Evolving Challenges** - Zi-Han Wang et al., 2026 (12 Mar), arXiv 2603.11863 [NEW]
- Did: a code benchmark with two creativity types; score = quality times novelty; proposes EvoRePE, an inference-time steering method.
- Result **shown**: scaling "significantly improves combinatorial creativity but yields diminishing returns for exploration"; larger models become "more correct but less divergent".
- For us: **Thinker**: score creativity as quality x novelty, so random junk (novel, wrong) and copies (correct, old) both score zero. Bigger is not more creative, so a small thinker is behind on coverage, not on divergence (**suggested**).

## C. Open-endedness, quality-diversity, novelty search

**C11. Position: Open-Endedness is Essential for Artificial Superhuman Intelligence** - Edward Hughes et al., 2024, arXiv 2406.04268 [NEW]
- Did: defines open-endedness as artifacts that stay both novel and learnable to an observer; argues foundation models make it reachable.
- Result **suggested** (position paper, no experiments).
- For us: **Thinker**: a testable meaning for "creative": the archive keeps producing members the model could not predict before but can learn after. Track both.

**C12. OMNI-EPIC: Open-endedness via Models of human Notions of Interestingness with Environments Programmed in Code** - Maxence Faldor et al., 2024, arXiv 2405.15568 [in repo]
- Did: a foundation model writes code for a new environment and its reward, a model of interestingness filters, and an archive of tasks grows.
- Result **shown** (qualitative, no headline number in the abstract): continually generates new, learnable tasks matched to the agent's skill.
- For us: **Minecraft**: the task generator is itself a program writer, so your thinker can write the next task. The judge of "interesting" was a large LLM; for a small model replace it with learned novelty or learning progress (**suggested**).

**C13. Enhanced POET: Open-Ended Reinforcement Learning through Unbounded Invention of Learning Challenges and their Solutions** - Rui Wang et al., 2020, arXiv 2003.08536 [NEW]
- Did: co-evolves environments and agents with a domain-general novelty measure for new challenges and a goal-switching heuristic that transfers solutions between challenges.
- Result **shown** (qualitative): produces diverse behaviours that solve environments "many of which cannot be solved through other means".
- For us: **Minecraft/Thinker**: keep old tasks and old solvers, and try each solver on each task; a lucky solution to one task is often the stepping stone for another. Needs no LLM.

**C14. Intelligent Go-Explore: Standing on the Shoulders of Giant Foundation Models** - Cong Lu, Shengran Hu, Jeff Clune, 2024, arXiv 2405.15143 [NEW]
- Did: replaces Go-Explore's handwritten "which state is interesting" rule with a foundation model's judgement.
- Result **shown** (no numbers in the abstract): "strongly exceeds classic reinforcement learning and graph search baselines" and "succeeds where prior state-of-the-art FM agents like Reflexion completely fail" on language and vision exploration tasks.
- For us: **Minecraft**: archive + return-to-promising-state + a judge is a minimal creative loop. The judge could be the borrowed 1.2B during training only (**suggested**).

**C15. ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution** - Robert Tjarko Lange et al., 2025, arXiv 2509.19349 [NEW]
- Did: LLM program evolution with explore/exploit parent sampling, code-novelty rejection sampling, and a bandit that picks which LLM to call.
- Result **shown**: new state-of-the-art circle packing with 150 samples ("orders of magnitude" fewer than prior systems); also AIME agent harnesses, ALE-Bench improvements, new MoE load-balancing loss.
- For us: **Thinker**: reject a try before running it if it is too similar to earlier tries (embedding or AST hash). Cheap, and it spends the executor on varied programs only.

**C16. Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents** - Jenny Zhang et al., 2025, arXiv 2505.22954 [NEW]
- Did: an agent rewrites its own code, keeps an archive of all variants, and checks each change on benchmarks.
- Result **shown**: SWE-bench 20.0% to 50.0%; Polyglot 14.2% to 30.7%.
- For us: **Thinker**: keep the archive, not just the best (stepping stones). Frontier-LLM based; no small-model evidence.

## D. Minecraft, Crafter, Craftax and game agents

**D17. Voyager: An Open-Ended Embodied Agent with Large Language Models** - Guanzhi Wang et al., 2023, arXiv 2305.16291 [in repo]
- Did: GPT-4 (black-box queries, no fine-tuning) with an automatic curriculum, a growing library of executable skills, and iterative code repair.
- Result **shown**: 3.3x more unique items, 2.3x longer distances, tech-tree milestones up to 15.3x faster than prior state of the art.
- For us: **Minecraft**: the "library of code skills" is what your thinker-writes-programs design already is; Voyager needed a frontier code writer, and whether a 3 to 11M writer can do it is untested.

**D18. Mastering Diverse Domains through World Models (DreamerV3)** - Danijar Hafner et al., 2023, arXiv 2301.04104 [in repo]
- Did: one set of hyperparameters across more than 150 tasks.
- Result **shown**: "the first algorithm to collect diamonds in Minecraft from scratch without human data or curricula". (full text) every Dreamer agent trained found diamonds within 100M environment steps (1 GPU for 9 days) in the MineRL block-breaking setting; on Crafter, six model sizes from 12M to 400M parameters: bigger gave both higher score and less data needed.
- For us: **Minecraft**: from-scratch diamonds is possible at 12M to 400M parameters, but at 100M steps and with the modified block-breaking setting. For 3 to 11M expect slower learning (**suggested**, from the Crafter size trend).

**D19. Training Agents Inside of Scalable World Models (Dreamer 4)** - Danijar Hafner et al., 2025, arXiv 2509.24527 [NEW]
- Did: reinforcement learning inside a learned fast world model ("imagination"), trained from offline video and a little action data.
- Result **shown**: first agent to obtain diamonds in Minecraft purely from offline data, choosing over 20,000 mouse and keyboard actions from raw pixels, real-time on one GPU. (full text) 2B parameters (400M tokenizer + 1.6B dynamics model); diamonds in 0.7% of episodes, iron pickaxe 29%; trained on VPT's 2541-hour contractor dataset; "100x less data" than VPT's offline agent.
- For us: **Minecraft**: imagination (blurt futures in a learned simulator, keep the rewarded ones) beats plain imitation. The honest bar for "diamonds from pixels" in 2025 is 0.7% at 2B parameters; there is no small-model result.

**D20. Video PreTraining (VPT): Learning to Act by Watching Unlabeled Online Videos** - Bowen Baker et al., 2022, arXiv 2206.11795 [NEW]
- Did: an inverse-dynamics model labels unlabeled Minecraft video with keypresses, then imitation, then RL fine-tuning.
- Result **shown**: agents that craft diamond tools, a task that takes proficient humans upwards of 20 minutes (24,000 actions at 20 Hz).
- For us: **Minecraft**: the pixels-to-keys prior that Dreamer 4 and STEVE-1 build on; needs a lot of video.

**D21. STEVE-1: A Generative Model for Text-to-Behavior in Minecraft** - Shalev Lifshitz et al., 2023, arXiv 2306.00937 [NEW]
- Did: adapts VPT to follow commands in MineCLIP's latent space using self-supervised behaviour cloning and hindsight relabeling, then trains a prior from text to those latent codes.
- Result **shown**: $60 of compute; robustly completes 12 of 13 early-game tasks from pixels with mouse and keyboard.
- For us: **Minecraft**: hindsight relabeling at the pixel level, the cheapest published way to get a language-steered agent. Relies on pretrained VPT and MineCLIP.

**D22. Craftax: A Lightning-Fast Benchmark for Open-Ended Reinforcement Learning** - Michael Matthews et al., 2024, arXiv 2402.16801 [in repo]
- Did: JAX re-implementation of Crafter (Craftax-Classic) and a much harder NetHack-flavoured extension (full Craftax).
- Result **shown**: Craftax-Classic runs up to 250x faster than Crafter; PPO with 1 billion steps finishes in under an hour on one GPU at 90% of optimal reward; for full Craftax, existing methods including exploration and environment-design ones "fail to make material progress". (full text) baselines used a 4-layer MLP of width 512 on 8,268-dimensional symbolic observations; no appreciable progress into the second floor (the gnomish mines). (repo page, not the paper) the best leaderboard entry at 1B steps is 18.3% of maximum reward (PPO-GTrXL). Note: my first read of the paper HTML suggested a much higher figure for PPO-RNN that I could not confirm, so I use the repo number.
- For us: **Minecraft**: a pixel-free gym where 1B steps cost an hour is the ideal lab for creative-loop experiments; the unsolved achievements need deep exploration and memory.

**D23. Improving Transformer World Models for Data-Efficient RL** - Antoine Dedieu et al., 2025, arXiv 2502.01591 [NEW]
- Did: model-based RL with a transformer world model: Dyna with warmup, nearest-neighbour patch tokenizer, block teacher forcing.
- Result **shown**: Craftax-Classic reward 67.4% after 1M environment steps in the v1 abstract (the latest version's abstract says 69.66%), vs DreamerV3 53.2% and human 65.0%.
- For us: **Minecraft**: first agent above the human level on Craftax-Classic at 1M steps; imagination is the sample-efficient route for a small agent.

**D24. Accurate and Efficient World Modeling with Masked Latent Transformers (EMERALD)** - Maxime Burchi, 2025, arXiv 2507.04075 [NEW]
- Did: world model with spatial latent states and MaskGIT-style prediction.
- Result **shown**: state of the art on Crafter, "the first method to surpass human experts performance within 10M environment steps", unlocking all 22 Crafter achievements (diamond included) during evaluation.
- For us: **Minecraft**: Crafter-from-pixels is solved by a modest world model, so use it as the small-agent practice field.

**D25. ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence** - ARC Prize Foundation, 2026 (24 Mar), arXiv 2603.24621 [NEW]
- Did: interactive turn-based games with no instructions, no stated goals and no language; agents must explore, infer goals, model the dynamics, plan.
- Result **shown**: humans 100%, frontier AI systems below 1% as of March 2026.
- For us: **Minecraft/Thinker**: the nearest public test of "work out an unknown game with no language prior", which is where an explore-then-write-a-world-model-program creative loop would show its worth.

## E. Library learning and program search

**E26. DreamCoder: Growing generalizable, interpretable knowledge with wake-sleep Bayesian program learning** - Kevin Ellis et al., 2020, arXiv 2006.08381 [in repo]
- Did: wake = solve tasks by neural-guided program search; sleep = add abstractions to a library and train the search network on "dreamed" programs.
- Result **shown**: rediscovers "the basics of modern functional programming, vector algebra and classical physics, including Newton's and Coulomb's laws".
- For us: **Thinker**: the original of your "sleep", with two sleeps (grow the library, retrain the guide).

**E27. LILO: Learning Interpretable Libraries by Compressing and Documenting Code** - Gabriel Grand et al., 2023, arXiv 2310.19791 [in repo]
- Did: LLM synthesis plus Stitch compression plus automatic naming and docstrings for the learned abstractions.
- Result **shown**: solves more complex tasks and learns richer libraries than DreamCoder on three benchmarks; the documentation step helps the synthesiser use the abstractions.
- For us: **Thinker**: give each learned skill a short name and description so the writer can find and reuse it.

**E28. Library Learning Doesn't: The Curious Case of the Single-Use "Library"** - Ian Berlot-Attwell et al., 2024, arXiv 2410.20274 [in repo]
- Did: re-examined LEGO-Prover and TroVE.
- Result **shown** (for those two systems): function reuse is "extremely infrequent"; the gains come from self-correction and self-consistency, not from the library.
- For us: **Thinker**: log the reuse rate of every learned skill; accuracy alone can hide a library nobody calls.

**E29. PoE-World: Compositional World Modeling with Products of Programmatic Experts** - Wasu Top Piriyakulkij et al., 2025, arXiv 2505.10819 [NEW]
- Did: a world model written as an exponentially weighted product of small LLM-written programs.
- Result **shown**: learns complex stochastic world models from a few observations and, inside a planning agent, generalises to unseen levels of Atari Pong and Montezuma's Revenge.
- For us: **Minecraft/Thinker**: a world model made of many tiny written rules, learned from few examples, is a plausible target for a small program writer (**suggested**).

**E30. Self-Improving Language Models for Evolutionary Program Synthesis: A Case Study on ARC-AGI (SOAR)** - Julien Pourcel et al., 2025, arXiv 2507.14172 [in repo]
- Did: alternate (a) evolutionary search where an LLM samples and refines programs and (b) hindsight learning where failed attempts become valid (problem, solution) pairs used to fine-tune the sampler and refiner.
- Result **shown**: 52% of the ARC-AGI public test set with an ensemble over model sizes. (full text, Table 1) Qwen2.5-Coder-7B: search alone 14.25%, after SOAR loops 36.25%; choosing sleep data "greedy-diverse" (half from solutions that solved the most examples, half from those that solved the fewest) beat purely greedy; solution diversity falls on solved tasks but stays on unsolved ones.
- For us: **Thinker**: the published recipe for your loop at 7B scale, with a variety rule for picking what to sleep on. Copy the rule; the scale gap (7B vs 3 to 11M) is untested.

**E31. CodeIt: Self-Improving Language Models with Prioritized Hindsight Replay** - Natasha Butt et al., 2024, arXiv 2402.04858 [NEW]
- Did: ARC as programming by examples; sample programs, relabel each program's actual output as the goal (hindsight), learn from prioritised replay.
- Result **shown**: solves 15% of ARC evaluation tasks, state of the art then, first neuro-symbolic method to scale to the full evaluation set.
- For us: **Thinker**: every executed try becomes a labelled example, even wrong ones; prioritised replay is the anti-forgetting part.

## F. Small recursive reasoners and test-time effort (ARC)

**F32. Hierarchical Reasoning Model** - Guan Wang et al., 2025, arXiv 2506.21734 [in repo]
- Did: two coupled recurrent modules, trained with no chain-of-thought and no pretraining.
- Result **shown**: 27M parameters, about 1000 training examples, strong on Sudoku-Extreme and Maze-Hard; ARC-AGI-1 40.3% and ARC-AGI-2 5.0% (numbers as reported in the TRM paper's table).
- For us: **Thinker**: tiny recurrent models can learn search-like tasks from few examples; read F34 and F35 before believing why.

**F33. Less is More: Recursive Reasoning with Tiny Networks (TRM)** - Alexia Jolicoeur-Martineau, 2025, arXiv 2510.04871 [in repo]
- Did: one tiny 2-layer network recursed, replacing HRM's two modules.
- Result **shown**: 7M parameters; ARC-AGI-1 45% (44.6), ARC-AGI-2 8% (7.8), Sudoku-Extreme 87.4 (HRM 55.0), Maze-Hard 85.3 (HRM 74.5); (full text) 1000 data augmentations per example and a majority vote over 1000 augmentations at test; adding layers overfit; swapping the MLP for a mixture of experts caused "a massive generalization drop".
- For us: **Thinker**: your 3 to 11M scale is the right neighbourhood. The recipe is augment, recurse, vote; do not add depth or experts.

**F34. Are Your Reasoning Models Reasoning or Guessing? A Mechanistic Analysis of Hierarchical Reasoning Models** - Zirui Ren et al., 2026 (v1 15 Jan, v2 22 Mar), arXiv 2601.10679 [in repo]
- Did: dissected HRM.
- Result **shown**: HRM can fail on puzzles with a single unknown cell and "guesses" the first fixed point; scaling the guesses (data augmentation, input perturbation, model bootstrapping) lifts Sudoku-Extreme from 54.5% to 96.9%.
- For us: **Thinker**: a tiny recurrent reasoner is already a blurt-and-filter machine. Make the variety explicit (perturb inputs, several seeds) and filter with the checker.

**F35. Tiny Recursive Models on ARC-AGI-1: Inductive Biases, Identity Conditioning, and Test-Time Compute** - Antonio Roye-Azar et al., 2025 (v1 4 Dec, v2 8 Jan 2026), arXiv 2512.11847 [in repo]
- Did: stress-tested TRM on ARC-AGI-1.
- Result **shown**: majority vote over 1000 test-time augmentations adds about 11 points of Pass@1 over a single pass; accuracy drops to zero when puzzle IDs are blank or random; most final accuracy appears at the first recursion step; the authors attribute TRM's score to efficiency, task-specific conditioning and test-time compute, "rather than deep internal reasoning".
- For us: **Thinker**: warning label on F33. Strong ARC numbers needed the task ID and heavy voting, so they are not evidence of reasoning about brand-new kinds of task.

**F36. The Surprising Effectiveness of Test-Time Training for Few-Shot Learning** - Ekin Akyurek et al., 2024, arXiv 2411.07279 [in repo]
- Did: temporarily update the model's weights at test time from the task's own examples.
- Result **shown**: up to 6x higher ARC accuracy than fine-tuned baselines; 53.0% on the public validation set with an 8B model, 61.9% ensembled with program synthesis; BIG-Bench Hard 10-shot 50.5% to 57.8%.
- For us: **Thinker**: "learn from few examples" in its plainest form: a throw-away adapter per task. Costs compute per task; untested at 3 to 11M.

**F37. ARC-AGI Without Pretraining (CompressARC)** - Isaac Liao et al., 2025, arXiv 2512.06104 [in repo]
- Did: a 76K-parameter network trained only on the one target puzzle at inference time, minimising its description length.
- Result **shown**: solves 20% of ARC-AGI-1 evaluation puzzles with no pretraining.
- For us: **Thinker**: extreme few-example learning exists with no teacher; "compress what you saw" is a candidate sleep objective (**suggested**).

## G. Curiosity and learning progress

**G38. MAGELLAN: Metacognitive predictions of learning progress guide autotelic LLM agents in large goal spaces** - Loris Gaven et al., 2025, arXiv 2502.07709 [in repo]
- Did: an LLM agent learns to predict its own competence and learning progress over a large language-defined goal space, generalising between related goals.
- Result **shown**: "the only method allowing the agent to fully master a large and evolving goal space" in their environment.
- For us: **Thinker/Minecraft**: a tiny learned "which kind of task am I improving at?" predictor can choose what to blurt at next (**suggested**).

## H. Hindsight relabeling and self-play task generation

**H39. Spinning Straw into Gold: Relabeling LLM Agent Trajectories in Hindsight for Successful Demonstrations (HSL)** - Zichao Li et al., 2026 (5 Jul; ICLR 2026), arXiv 2607.04235 [NEW]
- Did: after a rollout, an LLM relabels it with all the natural-language goals the agent actually achieved; adds irrelevant-action masking and reweighting; works for SFT and DPO.
- Result **shown**: on ALFWorld it beats baselines trained on the full dataset while using one quarter of the ground-truth demonstrations; bigger gains where goal spaces are more varied.
- For us: **Minecraft**: every wander becomes data: the borrowed 1.2B writes "got wood, crafted a table" and you train goal to behaviour. This is the cheapest use of a teacher that exists only during training.

**H40. R-Zero: Self-Evolving Reasoning LLM from Zero Data** - Chengsong Huang et al., 2025, arXiv 2508.05004 [in repo]
- Did: a Challenger is rewarded for tasks at the edge of a Solver's ability; the Solver trains on them; both start from one base model.
- Result **shown**: Qwen3-4B-Base improves by 6.49 on math reasoning and 7.54 on general-domain reasoning.
- For us: **Thinker**: "creative part" = a task writer rewarded for tasks the solver gets right only sometimes. 4B scale, no tiny-model evidence.

---

## Also verified (shorter notes; each opened on its arXiv abstract page)

Keeping variety and avoiding collapse
- **Is Model Collapse Inevitable?** Matthias Gerstgrasser et al., 2024, 2404.01413 [in repo]. **shown**: replacing real data with synthetic data collapses models; accumulating synthetic data alongside the original avoids it (test error bounded; language models, diffusion, VAEs; proof for linear models). Use: sleep should add to old data, not replace it.
- **RL's Razor: Why Online Reinforcement Learning Forgets Less** - Idan Shenfeld et al., 2025, 2509.04259 [in repo]. **shown** (LLMs and robotics models): on-policy RL forgets less than SFT; forgetting is predicted by the KL distance to the base policy. Use: sleep on the model's own samples with small drift (**suggested** for tiny models).
- **Self-Improvement in Language Models: The Sharpening Mechanism** - Audrey Huang et al., 2024, 2412.01951 [NEW]. **shown** (theory): self-improvement is "sharpening"; SFT-based sharpening is minimax optimal when the initial model has enough coverage, RL-based can beat it by exploring. Use: if the blurter has zero chance of the lucky try, sleep cannot help (same message as Yue 2025).
- **Rewarding the Unlikely: Lifting GRPO Beyond Distribution Sharpening** - Andre He et al., 2025, 2506.02355 [NEW]. **shown**: GRPO has a rank bias that reinforces already-probable solutions; an "unlikeliness reward" up-weights rare correct ones; competitive with DeepSeek-Prover-V1.5-RL on miniF2F-test. Use: upweight the rarest correct try when picking sleep data.
- **Outcome-based Exploration for LLM Reasoning** - Yuda Song et al., 2025, 2509.06941 [NEW]. **shown** (Llama and Qwen math): diversity lost on solved problems carries over to unsolved ones; a UCB-style bonus for rarely seen final answers plus a within-batch repeat penalty improve accuracy and mitigate collapse. Use: program outcomes are cheap to hash, so bonus rare outcomes and penalise duplicates.
- **The Entropy Mechanism of Reinforcement Learning for Reasoning Language Models** - Ganqu Cui et al., 2025, 2505.22617 [in repo]. **shown**: downstream performance R = -a*exp(H) + b in policy entropy H, so performance is "traded" for entropy and the ceiling sits at H = 0; Clip-Cov and KL-Cov slow the collapse. Use: log entropy as a gauge during sleep.
- **The Choice of Divergence (DPH-RL)** - Long Li et al., 2025, 2509.07430 [in repo]. **shown**: mass-covering f-divergences instead of reverse KL improve both Pass@1 and Pass@k, and need no online reference model.
- **SimKO / "Beyond the Sampled Token: Preserving Candidate Support in RLVR"** - Ruotian Peng et al., 2025, 2510.14807 [NEW]. Title note: the abstract page shows the newer title; v1 was "SimKO: Simple Pass@K Policy Optimization". **shown**: RLVR concentrates probability on the top-1 token; boosting top-K candidates for correct answers and penalising the top-1 for wrong ones raises pass@K (current version: models to 32B, K to 1024).
- **DSDR: Dual-Scale Diversity Regularization for Exploration in LLM Reasoning** - Zhongwei Wan et al., 2026, 2602.19895 [NEW]. **shown**: a global diversity term among correct trajectories plus token-level entropy regularisation gives consistent gains in accuracy and pass@k.
- **Jointly Reinforcing Diversity and Quality in Language Model Generations (DARLING)** - Tianjian Li et al., 2025, 2509.02534 [in repo]. **shown**: a learned partition function measures semantic diversity and is added to the quality reward; higher quality and novelty on non-verifiable tasks, higher pass@1 and pass@k on competition math.
- **Reasoning with Sampling: Your Base Model is Smarter Than You Think** - Aayush Karan, Yilun Du, 2025, 2510.14901 [NEW]. **shown**: MCMC sampling from a sharpened (power) distribution of a base model nearly matches and sometimes beats RL on MATH500, HumanEval and GPQA while keeping diversity; no training, but more inference compute.
- **Verbalized Sampling** - Jiayi Zhang et al., 2025, 2510.01171 [in repo]. **shown**: a training-free prompt that asks for a set of answers with probabilities raises creative-writing diversity 1.6 to 2.1x; blames typicality bias in preference data. Use: probably irrelevant to a from-scratch thinker whose collapse comes from training on winners, not from preference tuning (**suggested**).
- **Artificial Hivemind** - Liwei Jiang et al., 2025, 2510.22954 [in repo]. **shown**: 26K open-ended queries and 31,250 human annotations; repetition inside a model and strong similarity between different models. Use: one teacher gives one flavour of idea; add a second source.
- **Is Temperature the Creativity Parameter of LLMs?** - Max Peeperkorn et al., 2024, 2405.00492 [in repo]. **shown**: temperature is weakly correlated with novelty, moderately with incoherence, and not with cohesion or typicality.
- **Energy-Based Transformers are Scalable Learners and Thinkers** - Alexi Gladstone et al., 2025, 2507.02092 [in repo]. **shown** (authors' claims): up to 35% higher scaling rate than Transformer++, 29% more gain from "System 2 thinking" on language. Use: an energy model is a built-in checker; untested for small program writers.
- **Small Models Struggle to Learn from Strong Reasoners** - Yuetai Li et al., 2025, 2502.12143 [in repo]. **shown**: models of 3B or fewer do not reliably gain from long chain-of-thought or big-teacher distillation; mixing long and short chains, or big and small teachers, beats either alone. Use: keep borrowed-teacher traces short and mixed (**suggested** for 3 to 11M).
- **Can 1B LLM Surpass 405B LLM? Rethinking Compute-Optimal Test-Time Scaling** - Runze Liu et al., 2025, 2502.06703 [in repo]. **shown** (math, with a process reward model): 1B beats 405B on MATH-500, 0.5B beats GPT-4o, 3B beats 405B, 7B beats o1 and DeepSeek-R1. Use: "small beats big" is shown only with a verifier and extra tries, which is your executor plus blurting.

Open-endedness and quality-diversity
- **OMNI: Open-endedness via Models of human Notions of Interestingness** - Jenny Zhang et al., 2023, 2306.01711 [in repo]. **shown**: an LLM's sense of "interesting" focuses learning on tasks that are learnable and interesting, beating uniform sampling and learning-progress-only baselines in Crafter, BabyAI and AI2-THOR.
- **Quality-Diversity through AI Feedback (QDAIF)** - Herbie Bradley et al., 2023, 2310.13032 [in repo]. **shown**: LM-judged quality and diversity inside MAP-Elites cover more of the search space with high-quality samples than non-QD controls (creative writing).
- **Evolution through Large Models (ELM)** - Joel Lehman et al., 2022, 2206.08896 [NEW]. **shown**: an LLM as the mutation operator plus MAP-Elites produced hundreds of thousands of working Sodarace walker programs in a domain with no training data, then bootstrapped a new conditional model from them. Use: the closest published version of your whole loop (blurt programs, keep a diverse archive, train a model on it).
- **Human-Timescale Adaptation in an Open-Ended Task Space (AdA)** - Adaptive Agent Team (Jakob Bauer first listed), 2023, 2301.07608 [NEW]. **shown**: meta-RL over a vast task distribution + attention memory + an automatic curriculum at the frontier of ability gives adaptation on a human-comparable timescale; scales with network size, memory length and task richness. Large model.

Minecraft and open-world games
- **MineDojo** - Linxi Fan et al., 2022, 2206.08853 [NEW]. **shown**: thousands of open-ended tasks, an internet-scale knowledge base, and a video-language learned reward (MineCLIP); NeurIPS 2022 outstanding paper.
- **JARVIS-1** - Zihao Wang et al., 2023, 2311.05997 [NEW]. **shown**: over 200 tasks; a memory-augmented multimodal LM; 5x the reliability of prior state of the art on ObtainDiamondPickaxe. Use: its memory of past successes is an in-context version of your sleep; LLM scale.
- **Optimus-1** - Zaijing Li et al., 2024, 2408.03615 [NEW]. **shown** (no numbers in the abstract): hybrid multimodal memory (knowledge graph + experience pool) with planner and reflector, near human-level on many long-horizon tasks.
- **Discovering Hierarchical Achievements in RL via Contrastive Learning (Achievement Distillation)** - Seungyong Moon et al., 2023, 2307.03486 [NEW]. **shown** (no numbers in the abstract): contrastive prediction of next achievements gave state-of-the-art Crafter with fewer parameters.
- **CrafterDojo** - Junyeong Park et al., 2025, 2508.13530 [NEW]. **shown**: a light Minecraft stand-in with CrafterVPT, CrafterCLIP, CrafterSteve-1 and data tools. Use: rebuild the VPT to STEVE-1 pipeline at small scale.
- **Multi-Agent Craftax** - Bassel Al Omari et al., 2025, 2511.04904 [NEW]. **shown**: 250M interactions in under an hour; existing algorithms struggle with long-horizon credit assignment, exploration and cooperation.

Programs, search and test-time effort
- **Top-Down Synthesis for Library Learning (Stitch)** - Matthew Bowers et al., 2022, 2211.16605 [in repo]. **shown**: 3 to 4 orders of magnitude faster and 2 orders less memory than DreamCoder's library learner, with comparable or better compression. Use: cheap compression of a skill library.
- **Learning to Discover at Test Time (TTT-Discover)** - Mert Yuksekgonul et al., 2026, 2601.16175 [NEW]. **shown**: test-time RL with gpt-oss-120b sets state of the art on Erdos minimum overlap, GPUMode kernels (up to 2x), AtCoder and single-cell denoising, a few hundred dollars per problem. Use: aim for one great solution; very large model.
- **Evolving Deeper LLM Thinking (Mind Evolution)** - Kuang-Huei Lee et al., 2025, 2501.09891 [NEW]. **shown**: evolutionary generate-recombine-refine search solves over 98% of TravelPlanner and Natural Plan with Gemini 1.5 Pro and beats Best-of-N and sequential revision; needs an evaluator.
- **Product of Experts with LLMs: Boosting Performance on ARC Is a Matter of Perspective** - Daniel Franzen et al., 2025, 2505.07859 [in repo]. **shown**: 71.6% (286.5/400) of the public ARC-AGI evaluation set at about 2 cents per task on a 4090; task-specific augmentations in training, generation and scoring; depth-first search for diverse high-probability candidates; the model also scores candidates. Use: this is "reframing" in practice, viewing the same task from several transformed angles and combining the scores.
- **Combining Induction and Transduction for Abstract Reasoning** - Wen-Ding Li et al., 2024, 2411.02272 [in repo]. **shown**: writing a program is better for precise computation and composing concepts, predicting the output directly is better for fuzzy perceptual concepts; ensembling approaches human-level on ARC. Use: give the thinker both a program path and a direct path and let the checker choose.

Curiosity, autotelic agents, hindsight, self-play
- **Exploration by Random Network Distillation** - Yuri Burda et al., 2018, 1810.12894 [in repo]. **shown**: prediction error against a fixed random network as a bonus gives the first better-than-average-human result on Montezuma's Revenge without demonstrations.
- **Planning to Explore via Self-Supervised World Models (Plan2Explore)** - Ramanan Sekar et al., 2020, 2005.05960 [NEW]. **shown**: plans ahead inside a self-supervised world model to find novel states, instead of computing novelty only after reaching them; beats earlier self-supervised exploration and approaches agents that had reward access.
- **Intrinsically Motivated Goal Exploration Processes with Automatic Curriculum Learning (IMGEP)** - Sebastien Forestier et al., 2017, 1708.02190 [NEW]. **shown**: self-generated goals plus intrinsic reward select an automatic curriculum; a real humanoid robot discovered skills that act as stepping stones.
- **Autotelic Agents with Intrinsically Motivated Goal-Conditioned RL: a Short Survey** - Cedric Colas et al., 2020, 2012.09830 [in repo]. **suggested** (survey): an autotelic agent represents, generates, selects and solves its own problems; needs compact goal encodings and goal-achievement functions.
- **Augmenting Autotelic Agents with Large Language Models (LMA3)** - Cedric Colas et al., 2023, 2305.12487 [NEW]. **shown**: an LM relabels achieved goals (hindsight), proposes new goals with sub-goals and writes reward functions; masters a large variety of skills in a text world with no hand-coded goals. Precursor of HSL.
- **SAC-GLAM** - Loris Gaven et al., 2024, 2410.12481 [NEW]. **shown**: soft actor-critic plus hindsight relabeling for LLM agents beats on-policy methods in multi-goal settings.
- **Guiding Pretraining in RL with Large Language Models (ELLM)** - Yuqing Du et al., 2023, 2302.06692 [NEW]. **shown** (no numbers in the abstract): rewarding goals suggested by an LM gives better coverage of common-sense behaviours in Crafter and usually matches or improves downstream tasks.
- **The Wisdom of Hindsight Makes Language Models Better Instruction Followers (HIR)** - Tianjun Zhang et al., 2023, 2302.05206 [in repo]. **shown**: relabel instructions with what the model actually did, then train supervised; comparable to or better than SFT on 12 BigBench tasks.
- **Self-Questioning Language Models** - Lili Chen et al., 2025, 2508.03682 [in repo]. **shown**: a proposer is rewarded when its question is neither too easy nor too hard, the solver by majority vote; improves on three-digit multiplication, OMEGA algebra and Codeforces without curated data. Use: three-digit multiplication is card-sized.
- **Language Self-Play For Data-Free Training** - Jakub Grudzien Kuba et al., 2025, 2509.07414 [NEW]. **shown**: Challenger and Solver from one model in a minimax game improve Llama-3.2-3B-Instruct with self-play alone.
- **Towards Understanding Self-play for LLM Reasoning** - Justin Yang Chae et al., 2025, 2510.27072 [NEW]. **shown** (analysis): compares self-play with RLVR and SFT using pass@k, update sparsity and entropy dynamics, and "highlights its inherent limitations".

Measuring creativity, analogy and reframing (nothing here was tested on small models)
- **MacGyver: Are LLMs Creative Problem Solvers?** - Yufei Tian et al., 2023, 2311.09682 [NEW]. **shown**: 1,600+ unconventional problems; humans and LLMs fail in complementary ways (LLMs propose physically impossible actions); reflection and divergent-then-convergent prompting help.
- **Assessing the Creativity of LLMs in Proposing Novel Solutions to Mathematical Problems (CreativeMath)** - Junyi Ye et al., 2024, 2410.18336 [NEW]. **shown**: creative problem solving varies a lot across LLMs; Gemini-1.5-Pro was best.
- **Divergent Creativity in Humans and Large Language Models** - Antoine Bellemare-Pepin et al., 2024, 2405.13012 [in repo]. **shown**: against 100,000 humans, LLMs beat the average on the Divergent Association Task but fall short of highly creative people.
- **Benchmarking Language Model Creativity: A Case Study on Code Generation (NeoGauge)** - Yining Lu et al., 2024, 2407.09007 [NEW]. **shown**: "denial prompting" (add a constraint to the previous solution) plus a convergent and divergent metric on Codeforces; GPT-4 still below human creativity; MCTS and self-correction gave "no significant improvement in creativity". Use: "solve it again without using X" is a cheap variety generator for programs.
- **Creativity or Brute Force? Brainteasers as a Window into LLM Problem-Solving** - Simeng Han et al., 2025, 2505.10844 [NEW]. **shown**: models often find insightful solutions but sometimes brute-force when a creative one exists.
- **What Shapes a Creative Machine Mind? (C^2-Eval)** - Zicong He et al., 2025, 2510.04009 [NEW]. **shown**: separates convergent from divergent creativity and scores usefulness, originality and surprise; the abstract gives no size numbers.
- **Creative Preference Optimization** - Mete Ismayilzada et al., 2025, 2505.14442 [in repo]. **shown**: the MuCE dataset (200K+ human responses, 30+ psychological assessments); preference-tuned models beat GPT-4o on novelty, diversity and surprise at matched quality.
- **Large Language Models as Analogical Reasoners** - Michihiro Yasunaga et al., 2023, 2310.01714 [NEW]. **shown**: the model writes its own relevant examples before solving; beats 0-shot and manual few-shot chain-of-thought on GSM8K, MATH, Codeforces and BIG-Bench. LLM only.
- **Take a Step Back: Evoking Reasoning via Abstraction in LLMs** - Huaixiu Steven Zheng et al., 2023, 2310.06117 [NEW]. **shown** (PaLM-2L, GPT-4, Llama2-70B): +7% and +11% on MMLU Physics and Chemistry, +27% on TimeQA, +7% on MuSiQue.
- **Self-Discover** - Pei Zhou et al., 2024, 2402.03620 [NEW]. **shown**: the LM composes reasoning modules into a structure; up to 32% over chain-of-thought and over 20% above CoT self-consistency at 10 to 40x less compute.

## Not a paper: newest Minecraft news (treat as unverified)
- Reports dated 20 to 21 Sep 2026 (makeuseof.com, windowsforum.com) say a planner LLM called "Astra" paired with TypeSafe AI's "Jev" (a fast "System One" model that picks among predefined options) beat the Ender Dragon in 8 min 43 s for under $1; the earlier Astra-only run reportedly ran 141 hours without finishing. It is a demo posted by an engineer (Ronak Malde), not a paper; the article does not say whether the inputs were pixels or game-state text; I found no independent replication. If it holds, the lesson is the split: a slow planner plus a fast chooser from a menu of moves, which matches your thinker plus executor design. A separate Jev Minecraft demo (24 ms per decision) was explicitly described as not independently verified.

## Top 10 for our roadmap (ranked)

1. **SOAR (2507.14172)**: your sample, hindsight-relabel, fine-tune loop already built and measured on programs (7B: 14.25% to 36.25%); take its "greedy-diverse" rule for choosing sleep data.
2. **Self-Improving Transformers (2502.01612)**: shows the filter-and-retrain loop with a harder-each-round curriculum on plain small transformers with exact checkers; the nearest scale match.
3. **CodeIt (2402.04858)** with **STEVE-1 (2306.00937)** and **HSL (2607.04235)**: hindsight relabeling turns every try, even wrong, into a labelled example (programs, pixels, language goals); prioritised replay fights forgetting.
4. **TRM (2510.04871)** read with **Roye-Azar (2512.11847)** and **Ren (2601.10679)**: a 7M recurrent reasoner works through augmentation plus voting plus task identity; build the thinker to blurt several views and filter.
5. **Negative Reinforcement (2506.01347)** with **PKPO (2505.15201)** and **SvS (2508.14029)**: how to keep variety during sleep (learn from losers, reward groups of tries, invent sibling tasks); track pass@1 and pass@k.
6. **Large Language Monkeys (2407.21787)**: coverage rises log-linearly with tries and the checker is the bottleneck, which is why the exact executor is your advantage.
7. **Dreamer 4 (2509.24527)** with **EMERALD (2507.04075)** and **Dedieu (2502.01591)**: world-model imagination is the working route for Minecraft-like games; honest bars are Crafter fully solved by a modest model and 0.7% diamonds from pixels at 2B.
8. **OMNI-EPIC (2405.15568)** with **ShinkaEvolve (2509.19349)**: the same program writer also writes the next task, and rejects tries too similar to earlier ones before spending executor time.
9. **DreamCoder (2006.08381)** with **Library Learning Doesn't (2410.20274)**: a library of reusable skills as the second sleep, with reuse rate logged so it cannot fake progress.
10. **CreativeBench (2603.11863)** with **NoveltyBench (2504.05228)**: score creativity as quality x novelty and count distinct behaviours among k tries; bigger models are less divergent, so measure it directly.

## Things the evidence says will NOT work for a small model

1. **Sleeping only on your own successes.** Positive-only training raises pass@1 and lowers pass@k (A5, Yue 2025 in your notes, A7, entropy law in "Also verified"). Shown at 3B to 32B; untested at 3 to 11M, but there is no reason to expect better.
2. **Expecting sleep to create abilities the blurter never produces.** Reinforcement narrows to what the base model can already sample (Yue 2025); sharpening theory says the same (2412.01951). If a lucky try has zero chance, only new tasks or hindsight relabeling can widen it.
3. **Letting a tiny model grade its own tries.** The self-verification gap scales with pre-training compute (A2). **suggested** for small models; use the exact executor or the borrowed teacher as judge.
4. **Raising temperature as the creativity knob.** Weak link to novelty, moderate link to incoherence (Peeperkorn 2405.00492).
5. **Majority voting where there is no verifier.** It plateaus after a few hundred samples (A1). Voting helps TRM only because the task has one right grid and a task ID (F35).
6. **Distilling long, expert reasoning traces straight into a very small student.** Models of 3B or fewer already learn worse from long or big-teacher chains (2502.12143). **suggested** that 3 to 11M is worse; use short, mixed traces.
7. **Adding depth or experts to a tiny recursive model.** TRM: more layers overfit, mixture-of-experts caused a massive generalisation drop (F33).
8. **Reading a high ARC score as proof of reasoning.** TRM goes to 0% when puzzle IDs are blanked and gets most of its accuracy at the first recursion step (F35); HRM "guesses" (F34).
9. **Judging a skill library by accuracy.** Reuse can be near zero while accuracy rises from self-correction (E28).
10. **Using a GPT-4-class judge of "interesting" at deployment.** OMNI, OMNI-EPIC, Intelligent Go-Explore and MAGELLAN all lean on an LLM judge; a 3 to 11M model cannot be that judge. It is fine as a training-time helper, but the deployed model needs a cheap substitute (novelty or learning-progress score). **suggested**.
11. **Hoping a small model beats full Craftax or Minecraft soon.** Full Craftax is unsolved (best repo-leaderboard entry 18.3% of max at 1B steps; the paper's own baselines were 4-layer MLPs), and the best pixel Minecraft diamond result is 0.7% at 2B parameters. Small models should practise on Crafter and Craftax-Classic, where world-model agents already pass human level.
12. **Creativity from scale.** Larger models are often less diverse and "more correct but less divergent" (B9, B10).

## Gaps and caveats

- No paper found with a small (under about 100M) from-scratch model doing generate-and-filter-and-sleep on program writing beyond Lee 2025's arithmetic, strings and mazes, and TRM/HRM's puzzle models. That is open ground for the cards.
- Topic 9 (analogy, reframing, concept blending): only LLM-prompting papers (Analogical prompting, Step-Back, Self-Discover) were verified, none on small models. The closest working "reframing" is ARC augmentation views (Franzen 2505.07859, TRM). A search for concept blending returned only vision-language papers; I did not verify any.
- Topic 10 (latent noise, diffusion, energy-based sampling for small program writers): nothing measured on small program writers. Nearest: EBT (2507.02092), Reasoning with Sampling (2510.14901), mode-conditioned diversity (A8).
- Numbers that differ by version or source: Dedieu 2502.01591 says 67.4% in v1 and 69.66% in the latest abstract; SimKO 2510.14807 was retitled; the Craftax 18.3% figure is from the repo leaderboard, not the paper.
- Dropped or not used: a search snippet claimed a 10-agent text-based Minecraft system reached 91.7% against the Ender Dragon (arXiv 2503.03505); the abstract page has no such numbers, so I did not list it. Optimus-3 (2506.10357) was dropped because its abstract numbers are ambiguous. "Whether LLM judges of interestingness can be shrunk" and any claim that a tiny model beats Minecraft are untested here.
- The [NEW] and [in repo] tags came from a plain text search for the arXiv id; a paper cited by title only would show as [NEW].
