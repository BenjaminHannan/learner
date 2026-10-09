# Abacus Loop: a step-supervised register reasoner with a linear talker

_A from-scratch character reader feeds a small loop that reuses the same weights every round. The loop keeps the answer in a 9-slot "register" written units digit first, and after round r that register must hold the r-th worked-step result taken from the rows' `steps` field. The talker is one linear map per slot, so every answer character has to come out of the loop. In plain words: the model works the problem one step per round on an internal abacus, and the mouth can only read what is on the abacus._

## reader

From scratch, run once per question. Input: prompt_ids [B,T<=208] plus prompt_mask.

Embedding: X0 = E_char[ids] (108 x d) + E_pos[t] (208 x d) + E_place[ridx] (16 x d).
- ridx is the character's index counted from the RIGHT end of its token, using the regex tokens of data.word_spans.
- For a digit this is its place value (units = 0, tens = 1, ...). For a word it is the letter position from the end.
- Spaces and PAD get 15; values are clamped at 14.
- ridx is cached per prompt string and padded to prompt_ids.shape[1], because donor_eval pads to a common T. This is the Abacus/position-coupling idea from 2405.17399 and 2405.20671.

Reader body: 2 pre-LN BIDIRECTIONAL transformer blocks. These are plain_tf's Block with a key-padding mask instead of the causal mask: d=256, 4 heads, MLP 4x. A final LayerNorm gives X [B,T,256]. At ~10M: d=384, 6 heads, 3 blocks.

Can compute [suggested]:
- token and number identity and the digit place of every digit;
- 2 hops of context, for example which word a character belongs to, the "Then ..." sentences, and which number belongs to which name.

Cannot reliably do [suggested]: multi-operation arithmetic. A 2-layer reader has the depth for roughly one local operation, which is why the loop has to carry chains.

Never sees answer, accepted or steps. A unit test strips those fields from the rows and checks that state() is bit-identical. This passed on a scratchpad prototype [shown].

## reasoner

State S [B,16,d]:
- Slots 0-8 are the REGISTER. Slot j holds answer character j counted from the right, so the units digit is in slot 0.
- Slots 9-15 are 7 SCRATCH slots (for a pointer or progress marker; not supervised).

Slot codes P [16,d]: P[0..8] = E_place.weight[0..8], tied to the reader's place embedding so that register slot j is drawn to digit place j. P[9..15] is a learned nn.Embedding. Start state: S0 = P.

Each round r = 1..R, with R = 6 (the maximum number of steps in train is 5, so there is one spare round):
- H = S_{r-1} + P (re-inject slot identity).
- For each of 2 XBlocks, shared across all rounds:
  - H += SelfAttn(LN H) over the 16 slots;
  - H += CrossAttn(LN H -> X) with a key-padding mask. K and V of X are computed once per block per question and reused every round, so the prompt is re-read every round;
  - H += MLP_2x(LN H).
- S_r = LN_s(H). This bounds the state, following 2609.39967.

Other properties:
- Weights are shared across rounds (2 blocks in total; 3 at the 10M setting).
- No round-index embedding: the state itself has to carry progress. This also keeps loops:K > 6 meaningful and avoids an "r-th sentence" shortcut that would break on distractor variants.
- No halting. Rounds are fixed at 6, and the answer is trained to stay put once reached, so loops:12 should equal loops:6.
- Full backprop through all rounds. TRM found full backprop beat the 1-step gradient, 87.4 vs 56.5.
- n_loops = 6, so the harness sweeps loops:{0,1,2,12} automatically.

## talker

Per register slot j: logits_j = LN_t(S_R[:, j]) . E_char^T + b, with the output weights tied to the reader's character embedding.
- There is no attention, no mixing across slots, and no access to the prompt or the batch. talk(state, batch) ignores `batch` entirely.
- Decoding: argmax per slot, vocab.decode (which stops at the first EOS), then reverse the string, because the register is units-first. For example, register "0","3","-" decodes to "-30".

Confirmed: the talker sees ONLY the reasoner's final register.
- state() returns S_R[:, :9], which is 9 x 256 = 2,304 numbers.
- The scratch slots and the reader output never reach the talker.

The same linear talker also decodes the intermediate rounds during training. One fixed linear map must read v_1 off S_1, v_2 off S_2, and so on, which makes it a translator by construction.

Under the harness donor swap it can only print the donor's register [shown by construction, not evidence of reasoning].

## why_reasoner_must_reason

Bottleneck:
- The talker is a per-slot linear map with no access to the prompt, so every answer character must already sit in register slot j at the last round.
- Step targets forbid one-shot answers on multi-step rows. After round r the register must decode to v_r, the r-th worked-step result. For example, chain_ops "36, gives away 16, loses 6" must read 20 after round 1 and 14 from round 2 on. So a k-step row cannot show its answer before round k, and each round must turn v_{r-1} into v_r.
- The cheapest way to do that is to read v_{r-1} from the register and one operand from the prompt [suggested].

What can still leak:
1. Conveyor belt. The 2-layer bidirectional reader could precompute all intermediate values into X, and the loop would just copy v_r at round r. Unlikely at 2 layers [suggested], and the register-interchange lesion detects it.
2. Recompute-from-prompt. Each round could re-derive everything from X and ignore its own register: the sandwich-core failure, where 8 rounds equalled 4 [shown, code-map 6.2]. The interchange lesion detects this too.
3. 88.5% of train rows have no step targets. Their answer comes from the reader plus round 1 (about a 4-layer network, like plain_tf). Deep supervision pushes those answers early; the TRM ARC study 2512.11847 found most accuracy at the first recursion step. On those families "the reasoner" is reader plus round 1, and nothing forces multiple rounds.
4. Per-family shortcuts stay available to every model, for example syllogism "starts with No -> no".
5. The reader-to-loop link is deliberately open (the loop cross-attends to all of X). Only the loop-to-talker link is a hard bottleneck.

## params

3.2M setting (d=256, 4 heads), counted on a scratchpad prototype [shown]:
- Reader: 2 x 789,760 = 1,579,520.
- Reasoner: 2 XBlocks x 791,296 = 1,582,592. Each block has self-attn 4d^2, cross-attn 4d^2, MLP-2x 4d^2 and 4 LayerNorms.
- Embeddings: char 27,648 + pos 53,248 + place 4,096 + scratch codes 1,792.
- LN_x / LN_s / LN_t + talker bias: 1,644.
- Total 3,250,540 vs plain_tf d256 L4 3,244,544 (+0.2%).

10M setting (d=384, 6 heads, 3 reader layers, 3 XBlocks), counted [shown]: 10,786,284 vs plain_tf d384 L6 10,775,040 (+0.1%).

FLOPs per example, forward, mean prompt 81 chars, no padding [suggested, arithmetic]:
- 3.2M: reader ~0.27 GFLOP + 12 block-rounds x ~24 MFLOP (16 slots) ~0.29 + hoisted K/V ~0.04, about 0.60 GFLOP vs plain_tf ~0.58 (1.04x).
- With batch padding, about 0.8x, because the 16 slots are never padded.
- 10M: ~1.9 vs ~1.85 GFLOP (1.04x).
- So plain_tf at matched parameters is also the matched-compute arm.

Measured on CPU, random weights, batch 64, 4 threads: 1,117 vs 981 ms per training step (1.14x) [shown].

GPU wall-clock: 14 sequential small blocks vs 4 big ones, so I expect 1.3-1.6x plain_tf [untested]. That is about 25-31 min for 24k updates at 3-way sharing, given tf3m's 1,159 s at 3-way [shown].

GPU memory is about 3-5 GB per run [suggested].

## pretrained_parts

None. Everything is trained from scratch on the 200k rows.

A pretrained reader is deliberately left out:
- The design depends on character-level digit places tied to the register.
- The <100M models in baselines.md use BPE, and pythia merges digits [shown, baselines.md].
- Falcon-H1-Tiny-90M has single-digit tokens, but at 91M it would make the system 28x bigger than the baseline.

If Ben later wants his option (c), it is a one-change A/B on the reader slot only, with the loop, register and talker fixed [untested].

## training

Loss: L = (1/6) sum over r of CE_r. CE_r is the token-mean cross-entropy (in float32) of talker(S_r[:, :9]) against target_r, over the valid register slots: the reversed characters plus EOS, with -100 after.

Targets:
- vals = the numeric results of the steps (the regex `(?:=|->)\s*(-?\d+)\s*$` on each step), then the answer appended if it is not already last.
- This is used ONLY when len(steps) >= 2; otherwise vals = [answer].
- target_r = vals[min(r, k) - 1], so the register holds the answer from round k on.
- This covers 23,042 train rows (11.5%) [shown]: chain_ops 3,931, chain_story2 3,942, state_update 5,106, story_chain3 4,095, var_chain 4,226, percent_rate rate_total 1,742.
- Step counts k = 1/2/3/4/5 cover 176,958 / 13,490 / 6,891 / 2,213 / 448 rows [shown].
- The `len(steps) >= 2` rule correctly excludes single-step "checks", for example arith_bare "12 * ? = 96" with step "12 * 8 = 96".
- Examples (prototype): state_update targets read 33, 27, 25, 20, 20, 20; story_chain3 reads 79, 76, 152, 152, ... [shown].

Ablation arm `steps:false`: target_r = answer at every round, everything else identical.

Optimiser and schedule: exactly the harness defaults used for the baseline.
- AdamW betas (0.9, 0.95), weight decay 0.1 on matrices only. The slot codes and place embedding are nn.Embedding, so they are exempt like the other tables.
- lr 1e-3 at d256 and 7e-4 at d384, matching tf3m and tf10m.
- Warmup 300, cosine to 10%, gradient clip 1.0, bf16 autocast.
- Batch 256, 24,000 updates, shuffled order, same seeds as the paired baseline.
- `--minutes 45` as a safety cap only. A run that stops before 24k is not comparable.

Fairness rule: if the loop needs a different lr, the baseline gets the same 2-value grid.

Needed beyond the harness:
- the target builder inside loss() (it reads rows; no harness change);
- a diag script;
- a box-side build of the 200-per-cell dev set (same train hash), with the diag run on the box, because the box tars results without .pt checkpoints [shown, box.sh].

Pre-flight on CPU (free):
- test_harness passes;
- the leak test passes;
- overfit 512 mixed rows at d=128 for ~600 steps: last-round train exact >= 90% and intermediate-round exact >= 85%.

Budget:
- Each slot is 3 runs at ~30 min, about $0.25.
- Screen: 2 slots.
- Confirm: 4 slots (6 abacus + 6 plain_tf, fresh seeds 11-16).
- Optional 10M pair: 2 slots.
- Total about 8 slots, roughly $2-2.5 of the $3.

## predictions

All numbers are vs plain_tf at matched parameters (3.2M), 24k updates, and all are UNTESTED predictions.

Baseline facts [shown, results/*/RESULT.json]:
- tf3m over 4 seeds: in_dist 75.7 (sd 1.7), variant 20.2 (1.1), multi-step in_dist 62.1 (2.3), family 0.8.
- chain5 (chain_ops, chain_story2, state_update, var_chain, story_chain3) on the 40-per-family dev: in_dist 37.6 (seeds 36.5 / 42.0 / 36.0 / 36.0); variant 26.8 (29 / 23 / 30 / 25).
- tf10m: chain5 43.0 in_dist, 27.5 variant.
- Correction to the brief: "chain_ops 2-8%, state_update 8-10%" is the 8k-update table. At 24k, state_update is 32-52%, chain_ops 5-12%, var_chain 20-32%, table_lookup 20-30%, chain_story2 35-65%.

Abacus Loop with steps, 3.2M (central estimate, range in brackets):
- chain5 in_dist 60 [42-75], i.e. +22:
  - chain_ops 8 -> 35 [15-60]
  - chain_story2 48 -> 70
  - state_update 40 -> 70
  - var_chain 26 -> 50
  - story_chain3 65 -> 75
- multi-step in_dist (12 families) 69 [62-75]
- in_dist overall 77.5 [73-81]
- variant 22 [19-26], of which chain5 variant 38 [25-55]
- answer 44 [38-50], frame 72, vocab 61
- held-out families 1 [0-4]: no gain. This design does nothing for new kinds of question.
- Worst families afterwards: table_lookup ~28 (no steps), chain_ops ~35, and the copy-by-position families cipher_map / list_index / seq_cycle at ~45-55. These carry a 3-10 point risk from the parallel readout.

Answer-only Abacus arm: chain5 ~42 [35-50], in_dist ~75.

plain_tf trained to write the same intermediate values ("20 14 # 14"): chain5 ~58 [40-72]. I expect it to roughly tie the Abacus Loop (within +/-10) and possibly beat it.

10M setting: chain5 43 -> 65, in_dist 76 -> 79, variant 21.7 -> 24.

Honest odds:
- P(chain5 +10 confirmed) ~0.6
- P(variant +2) ~0.4
- P(no harm on pooled-5) ~0.65
- P(Abacus >= values-writing plain_tf - 2 on chain5) ~0.5.

Where it most likely loses: to a same-size plain transformer that writes the steps out.

Where it can still win:
- fixed compute with no written steps (6 rounds vs ~10-30 extra decoded characters);
- possibly variant rows that recombine operations;
- the property Ben wants: the reasoning provably lives in the loop.

## evidence

Supports:
- Step or hint supervision drives out-of-distribution success: CLRS 2205.15659 [shown in paper]. In this repo, worked-step targets gave +11.8 fit and +21.7 held-out [shown, UC SCREEN-v4]. On the chain families, the bare 1.2B scores 5% direct vs 71% when it writes steps [shown]. So steps are the lever. This design moves them from the talker's text into the loop.
- Each loop round can stand in for one chain-of-thought step: 2502.17416, where a 1x12 loop gets 99.9% on addition vs 0.1% for 1 layer.
- Deep supervision, re-feeding x every step, and a per-position linear head: TRM 2510.04871, where full backprop beats the 1-step gradient 87.4 vs 56.5.
- Re-reading the input every iteration: Recall 2202.05826 (0% -> 97%); MAC 1803.03067.
- Digit-place embeddings plus looping: Abacus 2405.17399, 92.9 -> 99.1 out of distribution. Position coupling: 2405.20671, where 1-layer models add 200 digits.
- Bounded state and a dense control that collapses out of distribution: 2609.39967, 7% vs 71%.
- Shared weights compose: 2604.07822.
- Reversed or scratchpad output helps small models: 2307.03381.
- Interchange and IIT as the lesion: 2112.00826, 2404.15255.
- Tiny looped reasoners beat their plain twins on code puzzles (6-digit sums 298 vs 154 of 300) [shown, digest row 22, a different task].

Contradicts or cautions:
- Per-step supervision HURT depth extrapolation in 2603.21676.
- Coconut's gains came from the curriculum, not the latent steps (2412.06769).
- TRM is mostly finished at the first recursion step (2512.11847).
- Sharing weights is not uniformly good (2108.12284: COGS 0.80 vs 0.77) and scales poorly on LM (2207.10551).
- In this repo, looping alone did not help: tf2x4 (looped 4x, 1.7M) 59.3 vs tf3m 65.7 in_dist at 8k, one seed [shown, CALIBRATION]. The sandwich core's 8 rounds equal its 4 rounds [shown].
- Implicit-CoT internalisation papers (2311.01460, 2405.14838, CODI 2502.21074) are listed in the digest but not verified in papers.md.

## lesions

The harness runs the loops:K sweep automatically. Everything else goes in diag_abacus.py, run on the 200-per-cell build; all collapse sizes below are predictions.

1. loops:1. chain5 in_dist falls from ~60 to <=8 (a collapse of ~50 points). On the same rows, the round-1 register still decodes v_1 correctly >= 70% of the time. Non-chain families stay within 3 points. In_dist overall drops ~8-10.
2. loops:2. Two-step rows (chain_story2, rate_total) stay intact; rows with k >= 3 collapse. chain5 ~25-30.
3. loops:12. Within 3 points of loops:6, because the answer is a trained fixed point. loops:0 gives 0.
4. Staircase. For each k, the intermediate exact at round r against v_r. Expected >= 50% at every r <= k on chain rows, with no cliff of more than 25 points between consecutive rounds.
5. KEY lesion: register interchange at round 1.
   - Pair row A with donor B of the same family and variant. Replace A's register after round 1 with B's, keep A's scratch and prompt, run rounds 2-6.
   - Score against the counterfactual cf = A's operations 2..k applied to v_1 of B.
   - Scorable: about 660 rows of the big in_dist build. chain_ops 173, chain_story2 197, state_update 189, var_chain 101; two_vars and non-exact divisions are skipped [shown, counted].
   - Pass: cf_match >= 40% (predicted 50-80%) and own-answer match <= 30%.
   - If the loop ignores its register: cf_match ~0 and own-answer match about the intact score.
6. Scratch interchange at round 1. Exploratory, no mark. Expected: A's value gets B's operation order.
7. Prompt-blind after round 1 (cross-attention output zeroed from round 2 on). chain5 falls to <=10%; k=1 families stay within 3 points. This shows each round reads a fresh operand.
8. Answer-only arm vs steps arm. chain5 gap >= +8. In the answer-only arm, loops:1 vs loops:6 differs by only ~5-10.
9. Harness donor / zero / shuffle. donor_match is about the donor's own accuracy (~75%) and exact is ~0; zero_state gives 0. These hold by construction (the talker reads only the register), so they are not reasoning evidence.

## decisive_test

Cheapest decisive test: one ~30-minute GPU slot (about $0.25) with 3 runs at 3.2M, 24k updates, batch 256, lr 1e-3, bf16:
- abacus_loop with steps, seeds 1 and 2;
- abacus_loop with steps:false, seed 1.

Comparison:
- Against the 4 existing tf3m seeds (same harness, hyperparameters and data-order seeds; exploratory) on the 40-per-family dev.
- The register-interchange diag runs on the box on the 200-per-cell build.

Go to the 6-seed confirmation only if ALL of these hold:
- (a) chain5 in_dist mean of the 2 steps seeds >= 47.6 (tf3m 37.6 + 10; tf3m seed range 36.0-42.0);
- (b) steps minus answer-only >= +8 on chain5 in_dist;
- (c) in_dist overall >= 74.0 (tf3m mean minus 1 sd);
- (d) interchange cf_match >= 40%.

Proves it wrong, any one of:
- both steps seeds <= 42.6 on chain5 in_dist (less than +5);
- steps minus answer-only < +3 (the loop is not carrying the steps);
- cf_match < 15% (the loop ignores its own register and the reader or prompt does the work again, the sandwich failure);
- in_dist < 72.

Confirmation marks, fixed now: 6 fresh paired seeds (11-16) against plain_tf 3.2M.
- chain5 in_dist on the big build (1,000 rows per seed): paired mean >= +10, with >= 5 of 6 seeds positive.
- variant overall >= +2.0 (the seed sd of 1.1 gives a paired standard error of ~0.64).
- pooled-5 >= -1.0.
- cf_match >= 40% in every seed.

Report the values-writing plain_tf (2 seeds) alongside. The claim "the loop adds something beyond the steps data" is made only if Abacus is >= values-writing plain_tf - 2 on chain5 and >= it on variant.

## implementation

Files: all new; plain_tf.py stays frozen.

1. custom_io/models/abacus_loop.py, ~200 lines.
   - EncBlock(plain_tf.Block): bidirectional, with SDPA attn_mask = prompt_mask[:, None, None, :].
   - XBlock(d, h, mlp=2):
     - kv_of(X) = kv(lnx(X)) reshaped to heads; called once per block per forward and reused every round;
     - forward(H, KV, mask) = self-attn over the slots, then cross-attn with the mask, then MLP.
   - AbacusLoop(Model):
     - __init__(vocab, d_model=256, n_heads=4, reader_layers=2, core_blocks=2, n_loops=6, n_scratch=7, n_reg=9, n_idx=16, steps=True); LESIONS = ['zero_state', 'shuffle_state'].
     - read(batch) -> (X, mask).
     - codes() = cat(idx.weight[:9], scr.weight).
     - rounds(batch, loops=None, S0=None, start=0) yields S_r: X, KV = read once; S = S0 or P; per round H = S + P, run the blocks, S = ln_s(H).
     - state(batch, loops) = last S[:, :9]; return P[:9] when loops = 0.
     - readout(R) = ln_t(R) @ tok.weight.T + bias.
     - talk(state, batch) = [vocab.decode(row)[::-1] for row in argmax].
     - targets(rows) gives [R, B, 9] of reversed characters + EOS, -100 padded.
     - loss = mean over rounds of CE, returning aux {loss_r1, loss_last}.
   - Init: normal(0.02), with residual output projections scaled by 0.02 / sqrt(2*reader_layers + 3*core_blocks*n_loops).
   - Register as 'abacus_loop' in models/__init__.py.
   - A working prototype of all of this is in the scratchpad: abacus_proto/abacus_loop.py. It reproduces the parameter counts, the targets, the leak test and the CPU timing.
2. custom_io/models/plain_tf_vals.py, ~70 lines: PlainTFVals(PlainTF), the same-information control.
   - Target = ' '.join(intermediate values) + ' # ' + answer, using the same len(steps) >= 2 rule; otherwise just the answer.
   - Cap 40 characters; builds its own answer ids from rows, not ans_ids.
   - Generates up to 41 steps (no KV cache, so eval takes ~4x longer) and scores the text after the last '#'.
3. custom_io/diag_abacus.py, ~160 lines.
   - Per-family exact on the big build for chain5 (in_dist and variant), for any model.
   - Round-wise intermediate exact.
   - Register interchange, with cf parsed from steps: chain formats 'a op b = c' and state_update '+n -> v'. Skip non-exact '/', var_chain two_vars, and cf equal to either answer.
   - Prompt-blind lesion.
   - Writes diag.json into the run directory so the box's tar picks it up.
4. Tests, ~50 lines:
   - leak test (strip answer, steps and accepted, then state must be equal);
   - targets round-trip;
   - donor_eval runs with padded T.
5. queue/04-abacus-screen.sh (# MEM 6000, # PAR 3):
   - the 3 `run` lines;
   - meanwhile build `--dev-per-cell 200` into $J/data_big and check the train hash;
   - then run the diag for each run.
   - Total ~500 lines.

Gotchas:
- Never use batch['ans_ids'] for targets: it is MSB-first and truncated.
- Pad ridx to prompt_ids.shape[1], because donor_eval pads.
- The slot and place codes must be nn.Embedding, otherwise train.py applies weight decay to them.
- Keep the register at 9 slots, the same as plain_tf's 8 characters + EOS. Raising it to 13 would be an unfair family-split advantage.
- A tensor-to-float on the loss before detach triggers a warning. Return detached values in aux.
- Do not add a round embedding in the main arm; it is the fallback knob only.
- Pack 2 abacus runs + 1 plain run per slot if the speed probe (first 300 updates) projects more than 30 minutes.

## risks

1. Parallel per-slot readout may hurt copy-by-position families: cipher_map encode ("7 6 6"), list_index, seq_cycle. A 3-10 point loss there could break no-harm. One-change fallback: a 1-layer causal talker that attends ONLY to the 9 register vectors.
2. Without a round index, the loop may not learn which operation comes next. The staircase would show round-1 values right and round-2+ values wrong. Fallback: a learned round embedding added to P (MAC-style), at the cost of loops:K > 6.
3. Two blocks per round may be too shallow for 3-4 digit multiplication or division, so chain_ops stays low. Fallback at equal parameters: 1 reader layer + 3 XBlocks.
4. Wall-clock. CPU measures 1.14x, but on GPU the 14 small sequential blocks may run 1.3-1.6x (launch-bound), giving 25-31 minutes when 3-way shared. Mitigation: 2-way packing, or R = 5.
5. The win may come from the steps DATA rather than the loop: the values-writing plain_tf may tie or win. Then the honest claim is only "beats answer-only plain transformers".
6. Step supervision can hurt extrapolation (2603.21676). Watch the variant split for the steps arm vs the answer-only arm.
7. Only 11.5% of rows have steps. Held-out families stay at 0-4%; this design does nothing for new kinds of question, which needs task diversity or episodic training (2306.15063, 1906.05381).
8. Worked steps will not exist for free in English or Minecraft.
9. The screen reuses calibration seeds, which is exploratory only. The verdict needs fresh paired seeds.
10. Changing lr only for the loop would bias the comparison; any lr grid must be shared with the baseline.
11. The box does not keep checkpoints, so every big-build eval and interchange must run inside the same job.

## english_and_minecraft_path

English: keep the loop, the register and the linear talker, and grow only the reader. That means a much larger from-scratch character reader trained on simple English, or Ben's option (c) as a one-change reader A/B. Per-round targets for human-written problems can come from worked solutions with calculator marks: GSM8K's <<48/2=24>> annotations give exact intermediate values, a direct match for this loss. Free-text answers would need a wider register or the 1-layer talker that reads only the register.

Minecraft: the register becomes a plan/inventory register and each round is one subgoal, for example logs, then planks, then sticks, then pickaxe. The per-round targets are the game state after each subgoal, which comes free in demonstrations. The talker becomes an action head reading only the register. Because each demonstration then supervises k states instead of one answer, this should be more sample-efficient for learning from few examples [suggested, untested].

