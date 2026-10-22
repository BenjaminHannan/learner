# Shape ideas: world models, planning and agents (design only)

2026-10-03, research subagent. Nothing was trained or run, and no repo file was changed.

- **Labels:** **shown** = a number in the cited paper, in its own setting. **Suggested** = reasoning. **Untested** = not run here.
- **"HTML summary"** = read through a fetch tool's summary, not the PDF.
- **Rulers stay separate:** the puzzle ruler, the assistant panel, and C3/C5. The village model and card experiments are not used.
- A village-stage note (`final-sweep-2026-09-19/05-alternatives.md`) rejected latent world-model *pretraining* for a different model. Nothing below is pretraining.

## 1. Imagine the result before calling the tool (latent dynamics)
1. **What:** the core predicts, in its own latent, the register state it will reach after a tool's result returns, given only the chosen operation. The core itself acts as MuZero's dynamics function.
2. **Sources:**
   - EfficientZero, arXiv 2111.00210 (PDF tables opened).
   - TD-MPC2, arXiv 2310.16828 (HTML summary).
   - V-JEPA 2, arXiv 2506.09985 (HTML summary).
3. **Evidence:**
   - **Shown:** on Atari 100k, removing EfficientZero's latent consistency loss drops the mean human-normalised score from 1.943 to 0.881. That is its largest ablation.
   - **Shown:** TD-MPC2 has no decoder and scores 16.0 / 49.5 / 57.1 / 68.0 / 70.6 at 1M / 5M / 19M / 48M / 317M weights (80 tasks).
   - **Shown:** V-JEPA 2-AC (300M, under 62 h of robot video) plans toward a goal embedding: cup pick-and-place 80%, vs Octo 15%. Its stated limit is a one-step horizon.
   - **Contrary (already in the repo):** a LeWM reproduction found that one-step prediction error does not rank planners.
4. **Maps to our core:**
   - At a tool step, a twin pass replaces the result segment with one "imagined result" token (an op embedding plus a new role id).
   - Loss: 1 − cosine to the real pass's registers, with stop-gradient on the real side and a fixed weight of 0.5.
   - Cost: about 4k weights, plus one training pass per tool step.
   - Later this becomes the Minecraft world model.
5. **Test (after F0, C3):** one change, adding the twin loss to C3, with the stream capped at 2k and at 20k unique problems.
   - **Pass:** held-out accuracy (structural split) at least +5 at 2k, both seeds.
   - **Wrong:** under +2, or collapse (register spread below 20% of baseline).
6. **Risk:**
   - E1-R3-A's forward-prediction loss was flagged under the predictive-coding ban. This one is action-conditioned and does no settling at inference, but it still needs a ruling.
   - Use it on computation tools only. Predicting lookup results bakes facts into the weights.

## 2. Score every move, then branch (value head plus real-tool search)
1. **What:** train the operation chooser to predict, for every candidate operation, whether it leads to the right answer, instead of copying the one right operation. At test, run the top 2 through the real tool and keep the higher-value branch.
2. **Sources:**
   - *Grandmaster-level chess without search*, arXiv 2402.04494 (HTML summary).
   - ARC Prize 2025 analysis (arcprize.org blog) and arXiv 2601.10904 (abstract).
3. **Evidence:**
   - **Shown:** at 9M weights, puzzle accuracy is 83.3% with action-value targets, 77.5% with state-value and 65.7% with move-copying. The first gap vanishes once data is corrected for; copying stays last.
   - ARC 2025's main theme was the "refinement loop": try, check against feedback, repeat.
4. **Maps to our core:**
   - This is the deferred plan head, with a new target. The head is about 4k weights.
   - Labels come from running every candidate through the tool at data generation, which is free.
   - Branching costs 2 passes, at test only.
5. **Test (after S):** one change, the plan-head target switched from copying to a yes/no score per operation, using argmax with no branching.
   - **Pass:** at least 8 fewer wrong operations on a fresh sealed 128 panel, both seeds.
   - **Wrong:** within 3.
   - **Then branching:** pass at least +6/128 right answers; wrong at +2 or less.
6. **Risk:** needs a tool whose options can be listed (the calculator can, web search cannot). Nothing on the forbidden list.

## 3. Find the task code by search (latent program search)
1. **What:** after reading k examples, the registers hold a task code. At test, a few gradient steps refine that code to fit the examples better, with the weights frozen.
2. **Sources:**
   - Macfarlane & Bonnet, *Searching Latent Program Spaces*, NeurIPS 2025, arXiv 2411.08706 (HTML summary).
   - Contrary: *Test-time Adaptation of Tiny Recursive Models*, arXiv 2511.02886 (HTML summary).
3. **Evidence:**
   - **Shown:** on a 1M-weight pattern task, training with one inner step and then searching gives 99.5%, vs 67.5% for averaged codes.
   - **Shown:** on ARC-AGI evaluation (178M weights), search doubles out-of-distribution accuracy, from 7.75% to 15.5%, and beats test-time training at equal compute (15.25% vs 13.5%).
   - **Contrary, shown:** tuning only TRM's task embeddings scored near zero. **Suggested:** LPN differs because it trains *with* the inner step.
4. **Maps to our core:**
   - Builds on C5. The registers after reading the examples are the starting code. A leave-one-out loss sends gradients to that 8×256 start only.
   - Training uses 0-1 inner steps.
   - Cost: no stored weights, and about 10 backward passes at test. Nothing is forgotten, and the input type does not matter.
5. **Test (after C5):** one change, 1 inner step in training and 10 at test.
   - **Pass:** at least +8 over C5 at k=8 and at least +10 at k=16, on held-out rule families, both seeds. The shuffled-answer control stays within 5 of k=0.
   - **Wrong:** under +3 at both k.
6. **Risk:** test-time gradient steps might count as "energy settling", which needs a ruling. The objective is the user's examples, and the reasoning state is never optimised.

## 4. A "what changed?" head (inverse dynamics)
1. **What:** a small head reads before and after states and names the operation that connects them, and later the key or mouse action.
2. **Sources:**
   - VPT, arXiv 2206.11795 (HTML summary).
   - LAPA, arXiv 2410.11758 (abstract).
   - Dreamer 4, arXiv 2509.24527 (HTML summary).
3. **Evidence:**
   - **Shown (VPT):** trained on 1,962 h of labelled play, the model reached 90.6% keypress accuracy and labelled 70k h of web video. Seeing future frames made it about 100× more data-efficient than copying; 100 h was already usable.
   - **Shown (Dreamer 4):** learned what actions do from a small labelled share of 2,541 h, and reached the first offline diamonds (0.7% of episodes).
   - **Abstract only (LAPA):** unlabelled latent actions beat real labels.
4. **Maps to our core:**
   - Rule-finding from example pairs is an inverse problem, so the head adds a "which operation turned A into B" loss, about 8k weights.
   - Later, it labels Minecraft videos with actions.
5. **Test (C5 setup):** one change, adding the inverse loss to meta-training.
   - **Pass:** at least +8 at k=4, both seeds.
   - **Wrong:** the head is at least 90% accurate but the gain is under 3.
6. **Risk:** operation ids must be actions, never task-kind labels.

## 5. Slow core, fast reflex, THINK action (System 2 / System 1)
1. **What:** the core updates its intent registers every few frames, and a tiny reflex head acts every frame. The agent may choose THINK to run more rounds instead of acting.
2. **Sources:**
   - Figure Helix blog, 2025.
   - Taufeeque et al., arXiv 2407.15421 (HTML summary).
   - Bush et al., arXiv 2504.01871 (HTML summary).
3. **Evidence:**
   - **Shown (Helix):** a 7B slow model at 7-9 Hz and an 80M fast model at 200 Hz, joined by one latent vector.
   - **Shown (Sokoban):** a 1.29M-weight looped ConvLSTM plans about 50 steps ahead. Six extra thinking steps solve 4.7% more levels. It learned to pace to buy thinking time, and it searches forward from the boxes and backward from the targets.
4. **Maps to our core:** a reflex MLP (about 0.3M weights, no attention), plus one THINK score. Stage one only needs registers readable after any round, which random-depth training already gives.
5. **Test (later toy):** walk the 9×9 mazes one move per frame with a moving goal. One change: allow THINK at a small time cost.
   - **Pass:** at least +10 solved at equal frames.
   - **Wrong:** THINK used on under 5% of frames, or a gain under 3.
6. **Risk:** the reflex head must stay thin. With the registers zeroed, it should be near chance.

**Seen, not proposed:**
- **DreamerV3:** diamonds from scratch, one A100, 9 days, settings fixed across 12M-400M.
- **ARC-AGI-3 milestone winners:** 27-31B LLMs writing code.
- **JARVIS-VLA, STEVE-1, Coconut:** larger models, or already covered.

## Top 2 (plain language)
1. **#2 Score every move, then branch.** It hits the 38/128 wrong-operation answers directly, for about 4k weights, with a 9M-scale result behind it. Every planner needs this value head later, including one for Minecraft.
2. **#3 Search for the task code.** It is the only idea that learns a new task from a few examples without changing weights, so it forgets nothing. It adds no stored weights and works for any input type. The TRM failure shows what to do differently.

Ideas #1-#4 each add under 0.1% of the core's weights, so they ride the D = 256/384/512 ladder unchanged. When closed-loop acting starts, build #1 first: it is the world model, but it needs the ruling.
