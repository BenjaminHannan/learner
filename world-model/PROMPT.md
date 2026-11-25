# PROBLEM-7 prompt (same file to Fable 5.2 max and gpt-6.2-astra max)

Settings: Fable `claude-fable-5-2`, effort max, no system prompt, web search off. Astra max via Responses API.

```text
<background>
We are building a small from-scratch "thinking" model (a recurrent whiteboard of vector rows, updated by a stack of attention + sparse mixture-of-experts blocks, several ticks per answer). Its end demo is live play in a Minecraft-like survival game: continuous "what happens next?" predictions shown beside reality, and visibly better play after "sleep" (offline training). Most results below come from small toy builds; main-build facts are labelled separately.

Readers: an engineer who will turn your answer into ONE test on a laptop CPU/GPU, and an owner (a high-school senior) who reads only the last section.

Why this matters: the design calls for a DreamerV3-style split (the world model learns only from real observed transitions; the policy may practise inside short imagined rollouts that start from real states, with the world model frozen). Today the world model has never seen a real outside transition, so we cannot tell whether it can learn one.
</background>

<system_under_test>
Main build (shown, code read):
- The world model is NOT a separate network. It is the same thinking trunk run in an "imagine next state" mode. Input: the current board (64 rows of width 256, of which the first 24 are "slow" readout rows), plus one extra row holding an embedded action, plus a mode embedding and a clock embedding (time since last tick). The trunk runs all its blocks. Output: predicted next board summary z_pred = (mean of the 24 slow rows of the current board) + a linear head on the action row's output, and a predicted next board (current rows + a residual).
- Loss: mean squared error between z_pred and the REAL next board summary (mean of the slow rows of the board after the next real tick), with the target detached (stop-gradient). Nothing else trains it.
- Planning calls the same mode with every weight, the context and the start board detached, so a planner's value can only train the actor/move embedding, never the world model or the trunk.
- The only training signal the world model gets anywhere today: "previous internal thinking tick + action WAIT -> board summary after the last thinking tick", weighted 0.1 in a text-question school. No outside observation, no outside action, no multi-step rollout, no "nothing changes" baseline. In one 50M-parameter dry run, that term (times 0.1) fell from 0.022 to 0.001.
- Senses (frozen borrowed encoders: a 24 fps image encoder, a video-window encoder, sound, speech) enter as read-only context rows the blocks attend to every tick; they do not write the board directly.
- Production trunk: 16 blocks x width 896, 16 experts top-2 per block, ~466M total / ~106M active parameters. A "4 wide blocks" shape (4 blocks x width 1792, ~467M / ~107M) is being timed separately; assume either shape.
</system_under_test>

<owner_rules>
- The world model trains only on real observed transitions, never on its own imagined rollouts.
- The policy may train inside short imagined rollouts (5-15 steps) that start from real observed states, world model frozen. Do not invent fake world/UI variations from one demo.
- No hand-written rules, lookup tables or game-specific shortcuts inside the model; say what is learned. No access to the game's internal state as an input (pixels/sounds and the model's own actions only). Internal state may be used ONLY by the scorer.
- One change at a time; pass marks fixed before any run; 3 misses close an idea.
- First test must run on a laptop (Apple M1 Pro, 32 GB, shared) in under 30 minutes wall clock. A 16 GB consumer GPU is available later in 12-minute slots.
- Keep the shared-trunk design unless you show it cannot work; if you recommend a separate world-model network, say exactly what evidence forces it.
</owner_rules>

<facts>
- The candidate laptop environment is an open 2D Minecraft-like survival benchmark: 64x64 RGB top-down view, 17 discrete actions (move 4 ways, do/interact, sleep, place stone/table/furnace/plant, make wood/stone/iron pickaxe and sword, noop), 22 achievements (collect wood, place table, make pickaxe, collect iron, diamond, ...), procedurally generated worlds, fast on CPU (these counts from memory, unchecked). It is the benchmark DreamerV3 reported on (from memory, unchecked). It is not yet installed; if you prefer a different laptop environment, say why.
- Data available: we can record our own random/scripted-exploration trajectories in that environment (no human data). Held-out worlds = different generator seeds.
- The model is recurrent over ticks; one environment step can be 1 or more board ticks.
</facts>

<results>
Toy builds only (separate small networks, NOT the main build):
1. Text "word room" planning (shown): a world model with a copy head + try-every-command 1-step search: 100 / 94.5 / 100 % over 3 seeds. A learned critic ranking a beam search (8 wide, 6 deep) beat the plain beam at tight search budgets: +51 / +64.5 / +37.5 points on 4-6-move goals, mean +38.3 on 7-9-move goals. An actor trained on the critic-ranked beam's picks matched it within 3 points. (A bug invalidated all deeper-than-1 search numbers in the first two tests.)
2. Bait grid with a trap (shown, PILOT, inconclusive): the "model learned" gate failed: honest imagination's 4-step value error 0.314 vs mark 0.243 (= 0.7 x best constant guess 0.347). Arms where the planning value could reach live inputs or a free "intention" vector became over-hopeful (4-step bias +0.35 to +7.97; all 12 candidate moves tied in 66-100% of decisions). Fully walled-off arms were nearly unbiased (+0.04 / -0.06). The main build then detached all planner inputs.
Main build: no world-model result on real transitions exists (shown: no such code path).
</results>

<candidates>
All untested. Each is described by its mechanism only.
1. Latent target as today, real data. Feed real frames as context, real actions as the action row; target = detached board summary after the board reads the real next frame. Same loss, multi-step by feeding imagined boards back.
2. Observation-grounded target. Keep the shared trunk; add a small decoder from the imagined next board to the next frame's frozen-encoder features (or low-res pixels), loss in observation space, optionally plus the latent loss of candidate 1.
3. DreamerV3-style separate world model. A separate small recurrent state-space model (own encoder, stochastic latent, decoder, reward/continue heads, KL balancing) trained only on real transitions; the thinking board reads its state as context and the policy trains in its rollouts.
4. Frozen-target prediction. Predict the next frame's embedding from a frozen pretrained image encoder (target cannot drift), contrastive or cosine loss, through the shared trunk; no decoder.
</candidates>

<question>
One decision: how should this model's world model be grounded on real observed transitions, and what is the single first laptop test?

Please give:
1. A diagnosis in 8 lines or fewer: does the current latent-only, shared-trunk, stop-gradient-target design risk a trivial or collapsing target once real frames drive the board, or is it sound? Name the measurement that would tell.
2. For each candidate: the strongest reason it works, the strongest reason it fails, whether it breaks an owner rule, keep or drop. Add a better candidate if you have one.
3. Your pick, with exactly ONE first test: the single change; data (how many transitions, which worlds held out); pass marks fixed in advance, including (a) k-step prediction error at k = 1, 3, 5 on held-out worlds vs a "nothing changes" baseline, (b) an action-shuffled control that proves the model uses the action, (c) any anti-collapse check; your guess as PASS / PARTIAL / WRONG percentages; the result that would prove you wrong; what to do next if it passes (including the first dream-trained policy test) and if it fails.
4. One free check to run before that test (no training, minutes on a CPU).
5. If no design meets every rule and mark, say so and name the cheapest rule to loosen.
6. Assumptions that would change your pick if false, and up to 3 facts you wanted but did not have.
7. A plain-language summary of 4-6 sentences for the owner.

Label every claim shown, suggested or untested. "Shown" is only for results in this message. Mark any paper you cite as "from memory, unchecked". Keep the toy-build and main-build results apart. Do not propose giving the model the game's internal state, hand rules, or training the world model on its own imagined rollouts.

Length: about 1,100 words before the summary. Everything you produce in this reply, including reasoning before the answer, counts toward one output limit. Use the reasoning space to settle the hard decisions, and write the answer once.
</question>
```
