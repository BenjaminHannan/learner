# Typed Word-Slot Workspace (TWS): context-free char-CNN/number-code reader, looped slot reasoner with in-place step values, linear typed talker

_Cut the question into words and numbers by a fixed rule. Embed each one on its own (spelling for words, digit places for numbers). A small looped attention block does all the cross-word work and even writes the running totals onto the numbers it uses. The answer is then read off with purely linear heads that point at a word, spell a number, pick yes/no, or read letters. Every bit of reasoning has to sit in the middle, and the design makes no claim beyond that until one 30-minute screen against a same-size plain transformer passes._

## reader

FIXED SEGMENTATION (not learned). The regex is `\d+:\d+ | (?<![\w)])-?\d+ | [A-Za-z]+('[A-Za-z]+)* | -> | \.\.\. | [^\w\s]`. It differs from data.word_spans in one way: a minus sign glued to digits stays with the number ("-47"), while "t - 3" stays three tokens.
- Each token gets a kind: word, number, punctuation or time.
- Slot cap W_MAX = 56. [shown, measured on the files] Slot counts are p50 22 / p99 42 / max 50 in train, and max 51 across all dev files. The longest token is 11 chars (12 in dev/family).
- Shapes: ch [B,W,12] char ids (harness vocab, 108 ids), kind [B,W], mask [B,W].

PER-TOKEN ENCODER (learned, no mixing between tokens).
- Per char: E_char[108,48] + pos-from-start[12,16] + pos-from-end[12,16], giving 80-d.
- Three Conv1d (k=1,2,3; 96 filters each), GELU, masked max over chars: 288-d.
- Spelled features: E_spell[108,16] at char positions 0-7 (128-d), plus the last 4 chars right-aligned (64-d).
- Length one-hot (13), and a fixed letter-count bag (26, clipped at 3, divided by 3).
- Concatenated that is 519-d, then word_mlp Linear(519,d), GELU, Linear(d,d).

VALUE-AWARE NUMBER CODE (fixed features, learned projection). 80 features per number:
- sign (1);
- 6 places, least significant digit first, each one-hot over {0-9, BLANK} (66);
- FoNE cos/sin(2*pi*x/10^i) for i=1..6 (12), so x mod 10^i is linearly recoverable;
- log10(|x|+1)/5 (1).
- num_proj Linear(80,d, no bias). Its 66 digit columns E_num[6,11,d] are TIED to the talker's digit readout, so a number enters and leaves in the same code.

SLOT VECTOR. e = LN(word_mlp + num_proj + kind_emb + idx_from_start_emb + idx_from_end_emb), shape [B,W,d].

CAN compute (all per token): spelling, length, first and last letters, letter counts, digits, parity, magnitude, and recognising an unseen made-up word by its spelling. The reader is about 12% of parameters.

CANNOT compute anything that involves two tokens. There is no binding, comparison, arithmetic or question understanding, by construction. Dev-only symbols (#@&$, capital O) get untrained char embeddings, the same as for plain_tf.

## reasoner

STATE. N = W word slots + 9 registers, d wide.
- r0 is the answer register. r1..r8 are char registers, one per answer character position (raise to 9 so 8 chars plus EOS fit; the prototype has 8).
- Registers start from learned vectors reg_init[9,d], which also carry each register's identity.

LOOP. inj = [e ; reg_init], h0 = 0. For t = 1..T: h = h + inj (the input is re-fed every loop, as in Recall/TRM), then h = Block2(Block1(h)).
- Two DISTINCT pre-LN blocks, SHARED across all T loops.
- Each block: 8-head bidirectional attention plus a 4x GELU MLP.
- Attention bias comes from a learned table of 19 buckets per head: 17 relative slot-to-slot offsets (clipped to +-8), one for slot attending to a register, one for register attending to anything. Pads are key-masked.
- Output: ln_out(h) split into S = slots [B,W,d] and Rg = registers [B,9,d]. This pair is what state() returns.
- Fixed T = 6. No halting and no loop-index embedding, so loops:K can run past T.

IN-PLACE SCRATCH (the "structured workspace" part). Training asks the slot of the operand that step k consumes to hold the running value after step k. Example: "Ed has 36. gives away 16. loses 6." The "16" slot holds 20 and the "6" slot holds 14 (see training). So binding, tracking and comparing happen in the slots, and the answer register only has to collect the result.

SIZE AND COST.
- 3M setting: d=336, 2 shared layers x 6 loops = 12 layer applications over about 33 tokens (22 words + registers) per row. Plain_tf runs 4 layers over about 92 chars.
- 10M setting: d=624, same layout.
- Compute is matched to plain_tf only approximately (about 1.6x; see params).

CAN do: exact-spelling match (attention between identical char-CNN vectors works for unseen words, which is the ESBN-style indirection argument; suggested), marking the answer slot, step-by-step running totals over at most about 6 operations, and writing letters into char registers.

CANNOT do: procedures longer than about 12 attention hops, numbers above 6 digits, or knowledge absent from the prompt (weekday order for clock_date).

## talker

The talker sees ONLY the reasoner final state (S, Rg), and EVERY head is linear in that state plus a softmax. It cannot do arithmetic, comparisons or lookups itself.
- GATE: Linear(d,4) on r0 gives log p(type), type in {COPY, NUMBER, LABEL, STRING}.
- COPY: pointer logit_k = w_ptr . S_k over the current row's non-punctuation slots. There is no query vector from r0 (the prototype first had one and it was removed), so the reasoner has to make the answer slot stand out. The emitted literal is the current row's token k, looked up by index. That copy source plus token kinds and lengths is all talk() reads from the batch, as base.py allows.
- NUMBER: v = W_val r0 (Linear d,d, no bias). For each of 6 places, digit logits = v . E_num[p, 0..9|BLANK], using the tied input code. Sign comes from Linear(d,2). Output is digits up to the first BLANK, reversed. All answers fit: the train maximum is 38,897 (5 digits), and 1,687 answers are negative.
- LABEL: Linear(d,8) over {yes, no, true, false, odd, even, a, b}.
- STRING: char j = argmax (W_s r_{1+j}) . E_char^T, tied to the reader's char table, stopping at EOS.

Decoding picks the type with the highest gate + best content log-prob (sum only up to EOS for STRING).

Coverage [shown]: COPY, NUMBER or LABEL covers 93.8% of train answers and 95.4% of in_dist. The rest are cipher strings and single letters, which go to STRING.

Under donor_eval the talker gets the donor's (S, Rg). The only thing taken from the current row is the literal word at the donor's chosen index.

## why_reasoner_must_reason

BOTTLENECK BY CONSTRUCTION.
1. The reader embeds each token alone. Nothing in it lets one token see another, so any answer that depends on more than one word must be computed in the reasoner.
2. The talker is linear: per-slot linear scores, then softmax over slots, plus linear readouts of registers. It has no access to the prompt except fetching the literal of the slot index it picked. It cannot add, compare, look up or count.

So the sandwich's failure (the 1.2B re-reads the question; the core carries a family mode; same-family swap 74.6 -> 74.4) has no path here. The donor-swap lesion should therefore collapse.

WHAT CAN STILL LEAK AROUND IT, OR LOOK LIKE REASONING WITHOUT BEING IT:
(a) Residual pass-through. S contains the reader features through the residual stream. Argmax over a per-slot linear score can by itself find e.g. the largest-magnitude number (log-magnitude feature) or the last-named word (index-from-end feature). The reasoner then only has to supply a mode (largest vs smallest, or a sign flip), which is a shallow, family-mode-like contribution. Measure it with loops:1 and per-family donor results.
(b) Copy-pointer donor confound. The donor's index applied to the current row can hit the right word when templates align (object_track "last place named"), so copy families will drop less under donor swap. Report the donor result by answer type.
(c) Supervision is not reasoning. The step loss hands the model the decomposition. A chain-family gain may come from the supervision and not the architecture. The plain_tf_steps arm and the step_w=0 ablation separate the two.
(d) Template shortcuts. 82% of in_dist prompts have an exact train template, and syllogism and object_track have known heuristics. The reasoner can still learn shallow rules; the variant and vocab splits are where that shows.

## params

[shown] Counted with the scratchpad prototype; plain_tf counts come from the repo class.

3M setting (d=336, 8 heads, 2 shared layers, T=6, 9 registers): 3,264,359 total, vs plain_tf d256 L4 at 3,244,544.
- Reader 408,144 (12.5%): char-CNN 46k, word MLP about 287k, num_proj 27k, kind and position embeddings 39k, char tables.
- Reasoner 2,722,088 (83.4%): 2 blocks of about 1.36M each, registers, relative-bias table.
- Talker 134,127 (4.1%): value readout 112,896, string projection 16,176, label 2,696, gate 1,348, sign 674, pointer 337.

10M setting (d=624): 10,688,711 total, vs plain_tf d384 L6 at 10,775,040.
- Reader 891,696; reasoner 9,368,264; talker 428,751.

FLOPs [shown, torch FlopCounterMode on the same 256 train rows, CPU]:
- Training forward+backward per example: plain_tf 3.2M 2.82 GFLOP; TWS-3M 4.58 (1.62x); plain_tf 3.2M with n_loops=2 5.61 (1.99x); plain_tf 10.8M 9.46; TWS-10M 15.27 (1.61x plain_tf 10.8M).
- Generation: TWS is one non-autoregressive pass, 1.50 GFLOP/example vs 8.49 for plain_tf's cache-free 9-step decode, so eval is far cheaper.

The fair compute-matched arm is therefore plain_tf n_loops=2, which has MORE compute than TWS.

Speed:
- [shown] CPU, batch 64, warm cache: TWS-3M 865 ms/step vs plain_tf 570 (1.5x).
- [untested] GPU. Plain_tf 3.2M did 20.7 updates/s with 3 runs sharing the card (19.3 min for 24k). TWS has about 3x more small kernels, so I expect 10-16 updates/s 3-way shared (25-40 min). The plan is under training.

## pretrained_parts

None. Every weight starts random, and the segmentation, number features and letter bag are fixed rules, not learned or borrowed. Nothing outside the 200k train rows is used, and the whole model is about 3.3M (or 10.7M) parameters. If English later needs word meanings, the first borrowed piece I would allow is a small static word-vector table added to the per-token reader (no LM, no context). The reader would stay context-free, so it still could not reason.

## training

LOSS.
- Answer term: marginal likelihood over valid typed derivations, ans_nll = -log sum over valid types t of p(t | r0) * p(content | t).
  - COPY is valid when the normalised answer equals at least one non-punctuation token; logsumexp over all matching slots.
  - NUMBER is valid when the answer is an integer of up to 6 digits; per-place cross-entropy plus sign.
  - LABEL is valid when the answer is one of the 8 labels.
  - STRING is valid only when no other type is (so the "spell anything" route cannot replace copying); char cross-entropy up to EOS.
  - Copied numbers, true/false, odd/even and A/B are valid under two types and train both.
- Step term (in-place supervision): STEP_NLL, weight step_w = 0.5. For rows whose worked `steps` end in "= v" or "-> v", step k is aligned to the first prompt number slot after the previous one that holds its operand. That slot's value readout (the same W_val, tied E_num and sign head, applied to S_j) must decode v_k at the FINAL loop.
  - No per-loop timing is imposed. 2603.21676 found per-step timing hurt extrapolation, so the readout only has to be right at the end.
  - [shown, parsed with the prototype] Coverage: chain_ops 3,931/3,931, chain_story2 3,942/3,942, var_chain 5,002/5,002, state_update 2,792/5,106 (the longest prefix with results is used), story_chain3 1,944, and one-step arith_bare/story_addsub/div_exact/distance_units 21,193. About 38.8k rows (19%) in total.
- Total loss = ans_nll + 0.5 * step_nll. Both are computed inside model.loss from batch['rows'] (answer, steps), which the harness allows. No deep supervision and no halting in v1.

OPTIMISER (harness defaults, as used for calibration). AdamW (0.9, 0.95), weight decay 0.1 on 2-D non-embedding weights. Make reg_init and the bias table nn.Embedding so they are not decayed.
- lr 1e-3 for 3M, 7e-4 for 10M. Warmup 300, cosine to 10%, gradient clip 1.0, bf16 autocast.
- Batch 256, 24,000 updates, shuffled order, seeds paired with the comparison arm.
- Init: normal std 0.02, residual output projections at 0.02/sqrt(2*L*T) = 0.02/sqrt(24).
- Command: `python3 -m custom_io.train --model workspace --cfg '{"d":336,"n_heads":8,"n_layers":2,"n_loops":6,"step_w":0.5}' --steps 24000 --batch 256 --lr 1e-3 --bf16 --final-eval --minutes 28 --seed S`.

BEYOND THE HARNESS, one extra comparison arm: plain_tf_steps. It is plain_tf whose target is "v1;v2;...#answer" (the same parsed step values written out as text), with an internal answer cap of 24 chars, scored on the text after the last '#'. It gives plain_tf the same supervision so a win can be credited to the architecture.

SPEED PLAN [untested].
- Pad W to a multiple of 8 and torch.compile the loop.
- Run a 500-step smoke test first. If it is under 16 updates/s 3-way shared, run TWS 2-way shared, or keep the --minutes cap and report the update count reached.

## predictions

All numbers are vs plain_tf 3.2M at 24k updates (4-seed mean from CALIBRATION/03-noise: in_dist 75.7, answer 43.7, frame 71.2, vocab 60.5, variant 20.2, family 0.8, multi-step in_dist 62.1, pooled-5 54.2). All TWS numbers are SUGGESTED, untested and have wide ranges.

- in_dist 78 (72-83), diff +2 (-4..+7).
- answer 52 (45-60), +8 (+1..+16). The gain comes from copy families where plain_tf fails: object_track 2.75 -> 60-90, list_index 24.5 -> 50-80, order_chain 14 -> 40-60.
- vocab 72 (63-80), +11 (+3..+19). Main drivers: copy_word 30.5 -> about 95, list_index, object_track, table_lookup, rule_apply.
- frame 74 (67-80), +3.
- variant 24 (19-32), +4. Possible gain on the layout-only "Question:... Facts:" rows from bidirectional slots; new computations stay near 0.
- held-out family 0-5, no win.
- pooled-5 60 (55-66), +6 (+1..+12).
- multi-step in_dist 68 (58-78), +6.

FOUR CHAIN FAMILIES (in_dist; plain_tf chain_ops 8.3, state_update 40.0, var_chain 27.5, chain_story2 47.8, mean 30.9):
- TWS chain_ops 35 (15-60), state_update 70 (45-90), var_chain 55 (30-80), chain_story2 65 (45-85). Mean about 56 (35-78), i.e. +25.
- With step_w=0, expect these back within +-10 of plain_tf.
- Against plain_tf_steps on the chain families TWS may well LOSE: I give it about 35% to win.

WORST FAMILIES predicted for TWS: chain_ops, arith_bare 50-80 (plain 78), fewshot_number_rule 45-70 (plain 66), seq_cycle 35-70 (plain 54), cipher_map 40-80 (plain 54), percent_rate 65-90 (plain 89). The cause is arithmetic done inside one vector with no digit-by-digit generation.

10M setting: +1 to +3 over TWS-3M, with a similar gap to plain_tf 10.8M (untested; screen at 3M only).

Honest odds (suggested):
- about 55% that TWS beats plain_tf by at least 3 pooled-5 points;
- about 70% that in_dist is no worse than -2;
- about 95% that the donor swap collapses by 20 points or more (it is built in);
- if it loses, most likely through single-step multiply/divide/percent families.

## evidence

Papers (papers.md):

SUPPORT.
- 2108.04378: copy decoder +0.057, and structured/tagging output took COGS from 0.28 to 0.64-0.78 in small from-scratch models.
- 1506.03134: pointers generalise to unseen items.
- 1909.07940: a from-scratch char-CNN was the best number encoder (list-max 0.93; even untrained it beat BERT).
- 2502.09741: FoNE exact digit features, 38M from scratch beats fine-tuned Llama-1B at 6 digits.
- 2405.17399: Abacus found digit-position marking to be the blocker; input injection plus looping took OOD from 92.9 to 99.1.
- 2202.05826: re-injecting the input every loop took 0% to over 97%.
- 2510.04871: TRM, a tiny recursed net with per-position heads.
- 2604.07822: weight sharing gives systematic composition.
- 2205.15659: CLRS hints, i.e. supervising intermediate states, help OOD.
- 2012.14601 (ESBN) and 1612.03969 (EntNet): binding and slot tracking with unseen entities.
- 2603.21676: perception interface + invariant looped core + readout is the closest template.
- 2402.01032: exact content must stay addressable, not compressed.
- 2307.03381: least-significant-digit-first output.
- 2008.06662: NeSS warns that an op able to write the whole answer recreates the talker. That is why STRING is valid only when nothing else is, and why the talker heads are linear.

CONTRADICT OR CAUTION.
- 2603.21676: per-step supervision hurt extrapolation. Mitigation: final-loop value targets only, no timing.
- 2511.14761: a non-looped model with good input beat loopers, so include the plain arms.
- 2512.11847: most accuracy came at the first recursion, so the loop may be shallow.
- 2207.10551 and 2108.12284: weight sharing is not uniformly good.
- 2306.15063 and 2212.04458: 34 families is far below the task-diversity threshold, so no new-family generalisation is expected.

REPO.
- CALIBRATION [shown]: plain char TF from scratch reaches 75.7 in_dist and 54.2 pooled-5, which is the bar. Per family [shown, 4 seeds]: it fails exactly where pointers and binding help (copy_word on vocab 20-42, object_track on answer 0-5, list_index in_dist 48-58, table_lookup 20-30) and on chains (chain_ops 5-12).
- Digest A17 [shown]: reader + core + direct 475-class head reached 13-15%. It had a frozen-LM reader, batch 1, 6k updates and a closed answer vocabulary. TWS differs in four ways: digit-code numbers, pointer copy, a from-scratch char reader, and 24k x 256 updates.
- Digest A7 [shown]: copy-and-gate on the core collapsed on unseen English kinds (13.6%). Expect the same on held-out families; nothing here claims otherwise.
- Digest A22 [shown]: tiny looped reasoners beat plain twins on 6-digit sums (298 vs 154 of 300).
- Digest A23 [shown]: from-scratch BiGRU/tape ears were close to SciBERT on templated frames.
- Digest A19 / data.md [shown]: worked steps help (bare 1.2B 5% -> 71% on chains).

## lesions

All lesions are harness-native unless marked.

1. DONOR SWAP (evalx.donor_eval, same family, different answer). in_dist exact goes from about 78 to 20 or less, a drop of 55 points or more (pre-set mark: 20 or more; the sandwich drops 0.2).
   - Number/label/string-typed rows: donor_match (output equals the donor's answer) of 50% or more; expected 60-80%.
   - Copy rows: about 10-35% stay right because of template position coincidences. Report by answer type.
2. shuffle_state (across families): 10% or less. zero_state: a constant answer, 0-10%, a format check only.
3. LOOPS CURVE (n_loops sweep):
   - loops:1 gives in_dist 35-55, with chain families at 20 or less while copy families keep most of their score;
   - loops:2 gives 50-70;
   - loops:12 within 10 of intact. Untested: there is no random-depth training, so over-running may degrade.
4. WAVEFRONT PROBE (about 20 lines, eval only; not in the harness). Apply the value readout to the operand slots after each loop. If the loop really tracks state, step k becomes correct from loop k (or k+1) onward. Prediction: 70% or more of step-k values correct by loop k+1 on state_update. Values correct only at loop 6 and never earlier would mean the work is not stepwise.
5. TRAINING ABLATIONS (one extra run each):
   - step_w=0: chain-4 mean drops back to about 31 +- 10;
   - same parameters with T=1: chain families collapse while copy families hold.
6. CONTROL ARMS: plain_tf (same params), plain_tf n_loops=2 (more compute), plain_tf_steps (same supervision).

## decisive_test

SCREEN S1: one box slot, 3 runs sharing the GPU 3 ways, about 30 min, about $0.3, seed 0, 24k updates x batch 256, full final eval + donor.
Arms:
- TWS-3M (d336, T6, step_w 0.5);
- a fresh plain_tf 3.2M twin (same seed and order);
- plain_tf_steps 3.2M.

PASS MARKS (fixed now), all required:
(a) TWS pooled-5 at least plain_tf twin + 3.0. One-seed sd of plain_tf pooled-5 is 1.0 [shown, 4 seeds].
(b) TWS in_dist at least twin - 2.0.
(c) TWS chain-4 in_dist mean (chain_ops, state_update, var_chain, chain_story2) at least twin + 10.
(d) donor-swap in_dist exact drop of 20 points or more.

THIS PROVES IT WRONG: pooled-5 diff below +1.0, OR in_dist diff below -2. Then stop the angle.
- If only the chain mark fails (chain-4 diff below +5), the "reasoner reasons" claim is dead even if the copy gains are real. That is what the screen is for.
- If TWS passes but plain_tf_steps is within 1 pooled-5 point of TWS and beats it on the chain families, the win belongs to the supervision, not the workspace. Then the claim is only "latent steps match written steps at less decode cost".

CONFIRMATION C1 (only if S1 passes): 6 paired seeds of TWS vs plain_tf, plus plain_tf_steps and plain_tf n_loops=2 if they were within 2 points in S1. About 2-3 GPU-hours, about $1.2-1.8.
Pass:
- paired mean pooled-5 diff of +3.0 or more with 95% CI above 0;
- in_dist diff of -1 or better;
- on the 200-rows-per-cell dev build (5 chain families x 200 rows), TWS at least plain_tf + 10 with paired McNemar p < 0.01;
- donor drop of 20 or more in every seed.

## implementation

FILE custom_io/models/workspace.py (about 300 lines). Register `'workspace': Workspace` in models/__init__.py.
A working prototype (shapes, gradient flow, generate, lesions and donor talk checked on CPU; NOT trained) is at /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/ws/workspace.py. The checks are in check.py and flops.py in the same folder.

PARTS.
- segment(prompt) -> [(text, kind)] (regex in reader).
- num_feats(x) -> 80 floats.
- step_targets(row, seg) -> [(slot, value)].
- RowPrep: a cache keyed by prompt string, holding char ids as uint8 [W,12], kinds, integer values, copy mask, typed targets and step targets.
- WordReader (char-CNN + spelled features + num_proj + embeddings).
- SlotReasoner (2 Blocks + registers + 19-bucket relative bias).
- TypedTalker (gate, ptr, W_val with tied E_num, sign, label, string projection with tied E_char).
- Workspace(Model) with state(), talk(), loss(), and LESIONS = ['shuffle_state', 'zero_state', 'loops'].

PSEUDO-CODE.
- state(batch, loops): P = prep(rows); e = reader(P); inj = cat(e, reg); h = 0; repeat loops: h = h + inj; h = B2(B1(h, bias)); h = LN(h); return h[:, :W], h[:, W:].
- talk((S, Rg), batch): heads on (S, Rg) only; type = argmax(gate + best content); copy literal = current row token[argmax ptr].
- loss: -logsumexp(gate + [lp_copy, lp_num, lp_lab, lp_str]) + 0.5 * step_nll(S[b, slot]).

PLUS custom_io/models/plain_tf_steps.py (about 50 lines, the supervision-matched control) and a wavefront probe script (about 20 lines). Estimate about 400 lines total, 3-5 hours.

GOTCHAS.
1. Prompt leak into the talker: talk() must never call the reader. Use only the current row's token strings (copy literal), kinds (mask) and lengths. Unit test: permute the prompts of batch B in talk(state(A), B). Non-copy outputs must not change.
2. Donor W mismatch: pad S to the current W with zeros and mask from the CURRENT row only. Never infer lengths from the state (base.py contract).
3. Cache key: use the prompt string. Ids are unique across the 7 files [shown: 0 collisions in 206,200 rows], but the 200-per-cell rebuild may reuse them. Store uint8 and ints and compute the number/bag features on GPU; the prototype's float cache would need about 2 GB for 200k rows.
4. STRING registers must be 9, not 8 (8 chars + EOS). Sum the string score only up to the first EOS (the prototype sums all registers).
5. The minus sign glued to digits in the segmenter (word_spans splits "-47"); keep "->" and "h:mm" whole.
6. The harness decays every 2-D non-Embedding parameter, so make reg and the bias table nn.Embedding.
7. Cast the float attention bias to the bf16 dtype for SDPA. Pad W to a multiple of 8 before torch.compile.
8. Labels a/b and true/false/odd/even are also copyable; the marginal loss handles that, and the gate confusion matrix should be logged.
9. The harness truncates ans_ids to 8, but loss() reads row['answer'], so the number head covers 5-6 digit answers (var_chain has 8 answers above 9,999).

## risks

1. ARITHMETIC INSIDE ONE VECTOR. Without digit-by-digit generation, multiply/divide/percent and few-shot multiplication rules may drop 10-25 points vs plain_tf. That is the most likely way TWS loses overall [suggested]. Pre-registered next change if the screen fails mainly there: 6 least-significant-first digit registers for NUMBER, each read linearly.
2. CREDIT. Chain gains may come from the step supervision. plain_tf_steps can match or beat TWS on chains; that is about a 65% chance by my estimate.
3. SPEED. 1.6x the FLOPs and about 3x more small kernels may overrun the ~25 min 3-way budget. The fixes are 2-way sharing or the --minutes cap, but a capped run reports fewer updates.
4. TYPE-GATE ERRORS. The right content under the wrong type gives a wrong answer.
5. LESION CONFOUND. The copy-pointer donor result is inflated by template position coincidences.
6. TALKER SHORTCUTS. The pointer can find extremes (largest number, last word) from residual reader features, so the reasoner may only supply a mode on argmax families.
7. SUB-WORD LIMITS. Only the first 8 and last 4 letters are explicit; letter counts come from the bag.
8. NO NEW KINDS. Held-out families stay near 0. This angle does not address new task kinds (below the task-diversity threshold).
9. LOOP STABILITY. There is no random-depth training, so loops:12 may degrade. Weight sharing may need far more than 24k updates to grok (2604.07822 used over 1.3M).
10. BRITTLE SEGMENTATION FOR REAL ENGLISH. Decimals, "1,000", hyphenated words and numbers above 999,999 are not handled.

## english_and_minecraft_path

English: the fixed segmentation and the spelling-based char-CNN work on any text and keep unseen names and words copyable. Human paraphrase needs word meanings that 200k synthetic rows cannot teach. The first add-on would be a small static word-vector table inside the per-token reader (no LM, still context-free, so it still cannot reason). Free-form English answers would grow the STRING registers into a short decoder that still reads only reasoner registers.

Minecraft: the slot set becomes typed objects (entities, blocks, inventory items, chat words), with value codes for counts and coordinates and registers for goals. The typed talker turns into typed action heads: point at an entity or slot, write a number argument with the digit code, pick a discrete action with the label head. Pointing works on items never seen in training, which suits learning from a few examples.

