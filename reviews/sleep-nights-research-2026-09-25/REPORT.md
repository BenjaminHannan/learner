# Can a night of sleep almost never make the model worse? (research, 2026-09-25)

Written by a research subagent of the Fix-sleep thread (WebSearch snippets only; no pages fetched, no code run). Saved
verbatim by the thread. Labels: **SHOWN** = a paper measured it in a comparable setting; **SUGGESTED** = different
setting or indirect; **UNTESTED** = our reasoning. "(snippet)" = words seen in a search-result summary. Citations
are as the agent reported them and have not all been re-checked; treat arXiv ids as leads.

## Summary for Ben (result first)
1. You are half right. Learning from the model's OWN tries (like RL) forgets much less than copying outside answers.
   The main reason found is "stay close to what you already are", not "RL is magic".
2. Our lucky-hit nights already learn from the model's own tries, so they are closer to RL than they look. What they
   lack: learning from the wrong tries, re-sampling, and any measure of "did it get worse elsewhere".
3. RL still forgets when it trains on one narrow thing after another ("RL Forgets!", 2026). The fix that holds up is
   replay: mix in a little old practice every night, which is also what the brain seems to do.
4. As far as found, labs do NOT veto each training step. They make each step small and safe (small updates, a leash to
   the starting model, mixed data), check whole runs broadly, and roll back only when something broke.
5. So the per-night pass/fail self-check should become a broad tripwire that almost never fires. It still has a job:
   catching a broken checker or a bug.
6. RL tends to shrink variety. Our own control arm showed it (27 puzzles reached -> 3-4).
7. Merging bored mode and sleep fits both the brain story and RL practice: gather while idle, learn in rounds.
8. First test: change only the learning rule (copy hits -> reward-weighted update from right AND wrong tries), with a
   broad harm panel in every arm.

## Q1. Does on-policy RL forget less than SFT on filtered self-generated samples?
- Shenfeld, Pari, Agrawal (2025), "RL's Razor: Why Online Reinforcement Learning Forgets Less", arXiv 2509.04259.
  Forgetting tracks KL(fine-tuned || base) on the new task; on-policy RL is biased toward KL-close solutions; SFT on a
  KL-minimal target forgot even less (paraphrase). SHOWN.
- Chen et al. (2025), "Retaining by Doing: The Role of On-Policy Data in Mitigating Forgetting", arXiv 2510.18874.
  RL forgets less than SFT; protection comes mainly from on-policy data "rather than other algorithmic choices such
  as the advantage estimate or KL regularization" (snippet); data regenerated each epoch can suffice. SHOWN.
- Chu et al. (2025), "SFT Memorizes, RL Generalizes", arXiv 2501.17161 (GeneralPoints card arithmetic, close to our
  puzzles): RL generalized to unseen rule variants; SFT useful before RL to fix format. SHOWN (generalization).
- Lai et al. (2025), arXiv 2507.05386: RFT forgot much less than SFT over 7 sequential multimodal tasks. SUGGESTED.
- Limits: Luo et al. (2026), "RL Forgets! Towards Continual Policy Optimization", arXiv 2607.04364: RL still forgets
  in continual post-training; the KL is measured on current-task data, forgetting is drift on prior tasks. SHOWN (VLM).
  Wang et al. (2026), arXiv 2607.01763: GRPO adapted more conservatively than dense on-policy self-distillation.
  Harmon et al. (2025), arXiv 2510.17776: counting per-item 1->0 flips, post-training forgetting often low-to-moderate;
  averages hide flips.
- Where our nights sit (UNTESTED, checked against scripts/claude_blurt2.py): 30 samples at T 1.5 from the current
  model, first exact hit per missed puzzle + own right answers, 3 epochs cross-entropy, lr 2e-4, LoRA r16 on q,k,v,o
  = rejection-sampling fine-tuning (RAFT / STaR / ReST-EM family), roughly on-policy; no negatives, no re-sampling,
  no KL. Nobody has measured the 1B's forgetting.

## Q2. How real RL runs keep from getting worse
- InstructGPT (Ouyang et al. 2022, arXiv 2203.02155): KL penalty still left regressions; mixing pretraining gradients
  (PPO-ptx) beat raising the KL coefficient (snippet). SHOWN.
- Tulu 3 RLVR (Lambert et al. 2024, arXiv 2411.15124): exact-checker PPO; more KL drift typically lowered average
  scores; small targeted gains. SHOWN.
- Clipping / trust regions: PPO, GRPO (DeepSeekMath 2024); DAPO (arXiv 2503.14476) clip-higher and dropping all-right /
  all-wrong groups. ProRL (arXiv 2505.24864): KL control, reference resets, diverse task mix. SHOWN.
- Degradation modes: entropy collapse (Cui et al. 2025, arXiv 2505.22617); reward hacking (Gao et al. arXiv
  2210.10760; Baker et al. arXiv 2503.11926 on unit-test rewards); train/inference numeric mismatch collapses
  (SUGGESTED). No source found for a per-update keep/undo veto; labs use conservative updates + run-level evals
  (SUGGESTED, absence of evidence).

## Q3. Continual fine-tuning: forgetting, replay, LoRA, averaging
- Kalajdzievski (2024), arXiv 2401.05605: forgetting grows as a power law in steps and parameters. SHOWN (SFT, 7B).
- Biderman et al. (2024), "LoRA Learns Less and Forgets Less", arXiv 2405.09673. SHOWN.
- "LoRA Without Regret" (Thinking Machines blog 2025): LoRA matches full FT for RL even at rank 1; use all layers
  (ours: attention only). Tina (arXiv 2504.15777): LoRA + GRPO on 1.5B, ~$9. SUGGESTED.
- Replay: Scialom et al. (2022, EMNLP) 0.25-1% rehearsal kept old tasks; CLEAR (Rolnick et al. 2019). SHOWN.
- WiSE-FT / soups: helped for CLIP; Harmon et al. found merging does not reliably help LLM forgetting. Mixed.
- STaR / ReST-EM re-train from base each iteration on accumulated data (paraphrase); ReST-EM saw diminishing returns
  after a couple of iterations. An option: re-train the adapter nightly from base on the growing hit bank.

## Q4. GRPO-style RL at ~1B
- One-example RLVR (arXiv 2504.20571): Qwen2.5-Math-1.5B large gains; entropy loss critical. SHOWN (Qwen, math).
- Gandhi et al. (2025), arXiv 2503.01307: on Countdown (our family) base-model habits decide RL gains. SHOWN.
- Spurious Rewards (arXiv 2506.10947): random rewards raised Qwen-Math by 21.4 points, not Llama/OLMo. Any RL test
  needs a shuffled-reward placebo. SHOWN.
- Yue et al. (arXiv 2504.13837): RLVR raises pass@1, base wins at large k (contested by ProRL).
- Signal: blurt-3 practice had >=151 of 400 groups with both right and wrong guesses (our data). Usable. Drop all-0 /
  all-1 groups. Compute for us UNTESTED (short answers; likely 1-3 GPU-hours per multi-night run).
- Rare success helpers: oversampling, curriculum, SFT warm-up, off-policy guidance (LUFFY arXiv 2504.14945),
  hindsight relabelling (our blurt-4).

## Q5. Diversity
- RAFT (positive-only, = our method) collapses entropy fastest (Xiong et al. 2025, arXiv 2504.11343). SHOWN.
- Training on negatives keeps pass@k (Zhu et al. 2025, arXiv 2506.01347). SHOWN.
- Other levers: entropy bonus, clip-higher, KL-Cov, B-STaR diversity monitoring (arXiv 2412.17256).
- Our W arm (distinct hits) widened reach 27 -> 38. Keep "puzzles reached" as a mark in every sleep test.

## Q6. Brain analogy
Complementary learning systems (McClelland et al. 1995; Kumaran, Hassabis, McClelland 2016), hippocampal replay in
sleep (Wilson & McNaughton 1994), sleep-like replay recovering forgotten tasks in networks (Tadros et al. 2022, Nat.
Commun.). Supports gather-awake / consolidate-offline / interleave old with new. SUGGESTED. Merging modes UNTESTED.

## Q8. Fast improvement on the day's own kind of work, without other skills dropping (added on request)
- Test-time training: Akyurek et al., arXiv 2411.07279 (ICML 2025): a small LoRA per task on augmented versions of
  its few examples gave "up to 6x higher accuracy" on ARC (8B) and +7.3 pp on BIG-Bench Hard 10-shot (snippets); a
  separate adapter per task beat one shared adapter (paraphrase of a secondary summary). SHOWN (8B).
- Tiny data can go far: TTT on 20 nearest neighbours, one step each (Hardt & Sun, ICLR 2024, arXiv 2305.18466);
  1-shot RLVR (Q4); LIMA 1,000 examples (arXiv 2305.11206). Ours: blurt-3 doubled lucky guesses from one night of
  151 hits + 23 own answers.
- On-the-job RL: TTRL (arXiv 2504.16084) majority-vote reward on unlabeled test questions; TTC-RL (arXiv 2510.04786)
  picks task-relevant practice then RL. SHOWN (7-8B; majority vote is a weaker check than our exact checker).
- Keeping other skills: SEAL (arXiv 2506.10943): earlier tasks "gradually decline as the number of edits increases"
  (snippet). Sparse memory fine-tuning (arXiv 2510.15103): NaturalQuestions F1 drop 89% full FT, 71% LoRA, 11% sparse
  memory slots (snippet; needs memory layers MiniCPM lacks).
- For us (UNTESTED): one adapter per kind of work (number puzzles, code with tests, tool calls), trained nightly on
  its own family and loaded only for that work, so a night cannot lower other skills; general gains from a slower
  shared adapter consolidated from all banks with replay. Data per night: a few hundred checked examples looks
  enough to move one family; measure 50 / 150 / 450 later.

## Q7. Recommendation (the agent's)
- Night = rounds of: sample groups from the CURRENT adapter, one reward-weighted update from right AND wrong tries
  (group-relative advantage, drop all-right/all-wrong groups), replay from a hit bank across families plus a general
  anchor slice.
- Tripwire, not gate: fixed broad panel counted in 1->0 / 0->1 flips, KL of adapter vs base on general prompts,
  puzzles reached, independent re-check of a sample of rewarded hits. Undo only if it fires; if it fires twice in 20
  nights, change the recipe.
- First test, one change (the learning rule): S = current SFT on hits; R = group-relative policy gradient on the same
  gathered groups; Z = R with shuffled rewards (placebo); harm panel + KL in all arms; 3 nights; 2 seeds.
- Honest limits: all forgetting evidence is 1.5B-8B+, mostly Qwen/Llama, mostly math; none on MiniCPM or a daily loop.

## Sources
arXiv: 2509.04259, 2510.18874, 2501.17161, 2507.05386, 2607.04364, 2607.01763, 2510.17776, 2203.02155, 2411.15124,
2503.14476, 2505.24864, 2505.22617, 2210.10760, 2503.11926, 2401.05605, 2405.09673, 2504.15777, 2205.12393,
2109.01903, 2603.12163, 2203.14465, 2312.06585, 2504.20571, 2503.01307, 2506.10947, 2504.13837, 2503.16219,
2504.14945, 2510.02230, 2504.11343, 2506.01347, 2509.07430, 2412.17256. Other: LoRA Without Regret (Thinking Machines);
TinyZero; arXiv 2411.07279, 2305.18466, 2305.11206, 2504.16084, 2510.04786, 2506.10943,
2510.15103; Rolnick et al. NeurIPS 2019; Kumaran et al. TiCS 2016; Tadros et al. Nat. Commun. 2022.
