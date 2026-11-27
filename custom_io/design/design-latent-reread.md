# Re-Reading Latent Loop (RRL): a Perceiver-style looped latent reasoner with a shallow char reader and a slot talker that copies by position only

_32 latent slots re-read a local-only character encoding of the question every round for 8 weight-shared rounds. A talker that sees only the final latents writes the answer in parallel, right-aligned slots, and copies characters by position without seeing their content. Every cross-word computation therefore has to happen in the loop. It is about 3.1M or 10.8M parameters, has about 1.0-1.07x the FLOPs of plain_tf at the same size, and is probably about even with plain_tf on in_dist, with an outside chance of a multi-step win._

## reader

ShallowReader. Nothing pretrained, no attention, no global mixing.

Input: prompt_ids [B,T<=208] and prompt_mask. Four integer features per character come from the prompt string using data.word_spans, cached per prompt: word index w (0..62; 63 = space or none), offset from word start (0..14), offset from word end (0..14), and digit place counted from the right end of its digit run (0..7; 8 = not a digit; Abacus-style, 2405.17399).

x_t = E_char[id_t] + Lin(sin(pos_t)) + Lin(sin(w_t)) + E_os + E_oe + E_place, giving [B,T,d], masked.
- Positions and word indices use fixed sinusoids, so "the word before word w" is a linear map (a rotation) that the loop can learn. [suggested]
- Then 2 LocalBlocks: x += W2·GELU(W1·DWConv_k5(LN(x)))·mask, with a 2x MLP, then a final LN. Output X [B,T,d].
- K/V for the loop are computed from X once and reused every round.

Can compute: [shown by construction] every feature at character t depends only on characters t-4..t+4 plus t's own position codes. It can therefore identify characters, short words and numbers (digits with their place values), and attach local cues such as "away 22" or "x =".

Cannot compute: anything across more than about 4 characters. It cannot combine "30" with "22" in "has 30 coats. Then Gus gives away 22", match a question word to a list item, or count, compare or look up. The receptive field is fixed, so there is no pathway for it.

Untrained symbols (capital O in dev/vocab; # $ & @ in dev/family) get their own untrained embedding but keep exact position codes.

## reasoner

LatentLoop. Latent state Z [B, L=32, d]. Z0 is a learned [32,d] init (std 1), the same for every row.

For r = 1..R (R=8), with one set of weights shared across all rounds:
  (1) READ: Z += W_o·MHA(q=W_q·LN(Z), K_x, V_x, key mask). 8 heads, so each latent makes 8 soft reads of the character array every round.
  (2) THINK: n_sa=2 distinct pre-LN self-attention blocks over the 32 latents (bidirectional, 4x MLP). These are shared across rounds but differ from each other within a round.
Then a final LN gives Z_R.

Design choices:
- No round embedding, so 'loops:K' at test time stays meaningful and longer runs are possible.
- No halting: R is fixed at 8 and the harness sweeps loops:{0,1,2,16}.
- Full backprop through all 8 rounds; at L=32 the memory cost is small.
- Residual output projections start at std 0.02/sqrt(2·R·(n_sa+1)).

Why re-reading every round: Recall (2202.05826), TRM (2510.04871), MAC (1803.03067) and MemN2N (1503.08895) all re-feed the input every step. The old sandwich core received its input once as a 32-dim per-token feature that swamped the state (|e|/|h|=44, code-map section 6). [shown in papers; untested here]

The state Z_R [B,32,d] is exactly what `state()` returns under the harness state/talk contract. It has no time dimension and depends only on the prompt.

Variants are cfg flags used only as ablation arms:
- read_once: cross-attend in round 1 only, i.e. plain Perceiver IO.
- no_core: the talker cross-attends to X directly.
- Eval lesion 'noread:K': reads stop after round K.

## talker

SlotTalker. Parallel, not autoregressive, one pass.

8 learned slot queries, right-aligned: slot j is the j-th character from the end, so for numbers it holds place value j. Slot len is the stop symbol (EOS) and later slots are ignored. Reversed, least-significant-first output follows 2307.03381.

Per slot:
- S = slots + CA(LN(S), LN(Z_R)), then S += MLP_2x(LN(S)), then LN.
- No slot-to-slot attention.
- Three heads:
  (a) gen logits = S·E_char^T, tied to the reader's character table, [B,8,108];
  (b) pointer logits = (W_pq·S)·P_t^T/8 over the prompt positions [B,8,T], where P_t = Lin(sin(w_t)) + E'_oe[offset-from-word-end_t] (d_p=64). The keys are CONTENT-FREE: word index and offset only. Spaces and pad are masked out.
  (c) gate g = sigmoid(w·S).
- p(c) = g·softmax(gen)(c) + (1-g)·Σ_t ptr_t·[id_t = c]. The mixture is computed in fp32 as a logaddexp of the two log terms.
- Decode: argmax per slot; stop at the first EOS from slot 0 upward; reverse.

What the talker sees: [shown in the scratch prototype's code]
- Z_R (the reasoner's final state).
- The CURRENT row's content-free word positions.
- Its character ids, used only as the copy target. Once a position has been chosen, the character id there is what gets written.

It never sees character content when it decides anything. In particular it cannot match, compare or compute over prompt content.

Why the pointer exists: exact copying of unseen strings (new names, made-up words, an untrained 'O') through a 256-number latent is lossy (2402.01032). With the pointer the latent only has to say WHERE ("word 7"), and ESBN-style indirection (2012.14601) lets that transfer to unseen tokens.

This matches the harness talk(state, batch) rule: copy source and lengths come from the current batch. It also matches Ben's note that the talker translates and does not reason, with one exception: the 2x MLP is a small capacity the lesions must bound.

## why_reasoner_must_reason

Bottleneck argument. [shown by construction]
- The reader mixes only within a ±4-character window.
- The talker sees only Z_R plus content-free position keys.
- So the 8-round latent loop is the only component that can relate two tokens more than 4 characters apart.
- Every skill that needs such a relation (binding a question word to a list item, combining operands from different sentences, tracking a running value, comparing numbers across a list) must be computed in Z_R or the answer cannot exist.
- Unlike the sandwich, there is no second path for the answer to bypass the core: no raw prompt words reach the talker. A donor or shuffled Z_R must therefore change the output wherever the answer's content or position varies between rows.

What could still leak around it:
(1) The talker's one cross-attention plus 2x MLP could do the LAST arithmetic step if Z_R holds operands rather than results. Bound: an ablation with a linear talker (no MLP), or check that loops:K accuracy rises with K while the talker is identical.
(2) The pointer is a softmax over positional keys. It can pick an extreme position ("last word", "first word") without the latent knowing the index. That is a positional shortcut; data.md already lists "last recipient named" as one for object_track.
(3) The ±4 window can do tiny local work, e.g. read the sign of "away 22" or a number's magnitude. That is reading, not reasoning.
(4) The loop can still learn per-family templates rather than general procedures. The bottleneck forces the loop to hold the answer; it does not make the loop generalise. That is the open question, measured by variant and held-out families.
(5) The digit-place and word-index codes are hand-built structure. If RRL wins, a plain_tf given the same codes is the control for crediting the loop.

Plain-language summary for Ben: the reading part can only see a few letters at a time and the answering part can only look at the thinker's notes (plus 'copy the word at slot 7'). So if the model gets a two-step question right, the thinking loop had to do the two steps. Whether that makes it smarter than a normal small transformer is what the test decides.

## params

Measured on the scratch prototype (CPU build, random weights). [shown]

~3M setting RRL-S: d=256, 8 heads, L=32, n_sa=2, R=8.
- Reader 0.700M: character table 27.6k (tied to the talker's gen head), sinusoid projections 131k, small tables 10k, 2 local blocks 528k.
- Reasoner 1.852M: Z0 8.2k, cross-attention 263k, 2 latent blocks 1.58M.
- Talker 0.552M: slots 2k, cross-attention 263k, MLP 263k, pointer and gate 21k.
- TOTAL 3.104M vs plain_tf-S (d256 L4) 3.245M.

~10M setting RRL-M: d=480, 8 heads (dim 60), L=32, n_sa=2, R=8.
- Reader 2.387M, reasoner 6.483M, talker 1.891M.
- TOTAL 10.761M vs plain_tf-M (d384 L6) 10.775M.

FLOPs per training example: torch FlopCounterMode on loss(), forward only, 256 shuffled train rows padded to T=170. Backward is about 2x for both.
- RRL-S 1.135 vs plain_tf-S 1.111 GFLOP, ratio 1.02x.
- RRL-M 3.985 vs plain_tf-M 3.730, ratio 1.07x.
- plain_tf-S with n_loops=2 is 2.212 GFLOP. So plain_tf at matched parameters is ALSO the compute-matched arm (±7%), and plain_tf n_loops=2 is a 2x-compute arm to add only if RRL wins.

Generation: RRL is one parallel pass; plain_tf re-runs the whole sequence up to 9 times with no KV cache. Eval is therefore about 5-9x cheaper. [suggested from code]

Kernel count: 4,061 vs 441 aten ops per forward+backward (batch 64). Measured as a CPU dispatch count, which includes the per-row feature building. CPU step time at batch 64: RRL-S 1.12 s vs plain_tf-S 1.95 s. [shown, CPU]

GPU speed is untested. Estimate: 15-25 updates/s in a 3-way share (plain_tf-S was 20.7, shown), so 24k updates take 16-27 min.

## pretrained_parts

None. Every weight is trained from scratch on the 200k skills rows. The only built-in structure is fixed sinusoidal position codes and integer features computed from the prompt string: word index, offsets within a word, and digit place. Those are code, not borrowed weights.

## training

Loss: negative log-likelihood of the gen+copy mixture over the right-aligned slots 0..len (len answer characters plus one EOS stop slot), averaged over valid slots. This mirrors the harness ans_mask, which covers the characters plus EOS. Answer-only, applied to the final round only. No deep supervision and no step supervision in the decisive arm: one change at a time.

Optimiser: the harness as-is. AdamW (0.9, 0.95), weight decay 0.1 on matrices, none on embeddings or norms. Batch 256, 24k updates, cosine to 10% of the peak lr, grad-clip 1, bf16 autocast, shuffled order, --minutes 28 cap.
- RRL-S: lr 1e-3. RRL-M: lr 7e-4. Same as the calibration runs.
- --warmup 1000 instead of 300, because the 8-round loop is deep.
- Fairness: if RRL gets one lr retry (5e-4 after a loss spike), plain_tf gets the same retry. Report both.

Commands:
- S: python3 -m custom_io.train --model perceiver_loop --cfg '{"d_model":256,"n_heads":8,"n_latents":32,"n_sa":2,"n_loops":8}' --steps 24000 --batch 256 --lr 1e-3 --warmup 1000 --bf16 --eval-every 4000 --final-eval --minutes 28 --seed S
- M: same with d_model 480 and --lr 7e-4.

Beyond the harness:
(1) For confirmation, build the 200-per-cell dev (same train hash) on the box and train with --data pointed at it, so RESULT.json has 200 rows per family. box.sh's hash assertion must then compare train.jsonl only.
(2) Pre-registered follow-up arm, run only after the decisive test passes: steps-notebook auxiliary.
- Parse each step's result with r'(?:=|->)\s*(-?\d+)\s*$'. This covers 100% of rows in the five chain families [shown on train].
- Up to 5 'pages'. Page p reuses the SAME talker, with a learned page vector added to the slot queries, and decodes step p's value from Z_R.
- Loss weight 0.3.
- It supervises the core, not the talker. The repo's +11.8 fit from worked steps came from the LM writing them, and 2603.21676 found per-step supervision hurt extrapolation, so this is a separate arm. [untested]

## predictions

All predictions are untested, at matched parameters and 24k updates. Plain_tf-S reference: 4 seeds, shown in CALIBRATION.md and the RESULT files.
- in_dist 75.7 (sd 1.7); multi-step in_dist (12 families) 62.1 (2.3); variant 20.2; vocab 60.5; answer 43.7; family 0.8.
- chain-5 (chain_ops, chain_story2, story_chain3, var_chain, state_update; 40 rows each) = 36.5 / 42.0 / 36.0 / 36.0, mean 37.6 (computed from the RESULT files).

RRL-S, point estimate (rough 80% range):
- in_dist 72 (64-78), Δ -3.5. P(RRL ≥ plain) ≈ 35%. Likely losses: exact lookups through a 32-slot bottleneck and parallel digit decoding (arith_bare, list_stats).
- variant 22 (15-30), Δ +2. The order-agnostic read might help the 313 held-out-layout rows. [weak suggestion]
- multi-step in_dist 60 (50-70), Δ -2.
- chain-5 42 (30-55), Δ +4. P(Δ ≥ +6) ≈ 25-30%.
- vocab 66 (56-76), Δ +5.5. P(Δ>0) ≈ 70%. This would come from the content-free pointer on copy_word, list_index, order_chain and object_track, which is credit to the talker, not the loop.
- answer 48 (40-56), Δ +4.
- Worst families: chain_ops 3-20 (both architectures stay low: multiplication up to 4800 without steps), table_lookup 25-60 (plain 25-30), var_chain 20-50 (plain 22-32), state_update 25-55 (plain 32-52), chain_story2 35-65 (plain 35-60), list_index 50-85 (plain 48-58), cipher_map 40-75 (plain 52).
- Held-out families 0-6%. No mechanism here for new kinds; unit_convert may get a few of 40.

RRL-M vs plain_tf-M (76.0 in_dist, 43.0 chain-5, 1 seed): in_dist 73 (65-79), chain-5 47 (35-60).

Overall honest call: more likely than not to tie or lose slightly on in_dist. The realistic places to win are multi-step chains (the loop), the vocab/answer splits (the pointer), eval cost, and clean attribution.

## evidence

Papers supporting the design (from papers.md):
- 2103.03206 Perceiver: latents re-reading the input with weights shared across repeats trained from scratch; more cross-attends helped. [shown, vision only] Caveat: sharing the FIRST cross-attend was unstable there.
- 2202.05826 Recall: re-injecting the input every iteration gives 0% → 97% extrapolation. [shown, prefix sums]
- 2510.04871 TRM: x visible every step, a tiny net, parallel per-position output head. [shown, grids]
- 1803.03067 MAC: from-scratch embeddings with control re-attending the words each step, CLEVR 98.9. [shown, templated language; note MAC's reader is a biLSTM, more powerful than ours]
- 1503.08895 MemN2N: more hops help. [shown, bAbI]
- 2012.14601 ESBN: a controller that never sees content transfers to unseen entities. This supports content-free pointer keys. [shown, visual symbols]
- 1506.03134 and 2108.04378: copy/pointer heads help small from-scratch models out of distribution (copy decoder +0.057 average; layer sharing +0.065).
- 2405.17399 Abacus: digit-place marking was the real blocker. 2307.03381: reversed output helps.
- 2512.14693 URM and 2609.39967: recurrence beats unshared depth at equal FLOPs; the dense same-size control is 7% vs 71% out of distribution.

Papers against the design:
- 2107.14795 Perceiver IO matched BERT on text only with web-scale pretraining; small-data text is untested.
- 2502.17416: loops buy depth, not memorisation, which predicts losses on lookup and memory-heavy families.
- 2604.07822: systematic composition appeared only after more than 1.3M steps; 24k may be far too few.
- 2512.11847: TRM's loop is shallow in practice (most accuracy at the first step).
- 2603.21676: the text case was the weak one (60% out of distribution).
- 2207.10551: weight-sharing models scale poorly, and rankings flip with size, so test at both sizes.
- 2511.14761: a non-looped model with a better input representation beat looped ones, so the plain_tf + codes control is needed.

Repo results:
- [shown] Plain char transformers from scratch reach 75.7 in_dist (3.2M, 4 seeds) and 76.0 (10.8M). That is the bar, and it already ties the 1.2B sandwich at 74.6.
- [shown] tf2x4 (plain transformer, 2 layers looped 4 times, 1.7M) got 59.3 vs 65.7 for tf3m at 8k updates. Looping at half the parameters lost.
- [shown] The sandwich core carried only a family mode (74.4 vs 74.6 under swap). This design removes that bypass by construction.
- [shown] A core-only copy-and-gate talker collapsed to 13.6% on unseen English kinds. Here there is no LM fallback, so a weak loop means total failure. That is visible, not hidden.
- [shown] A reader+core class head with no LM got 13-15%. Different regime: batch 1, 6k updates, 32-dim LM features. Here: 6.1M rows seen, about 30 epochs.
- [shown] Tiny looped reasoners on code puzzles: 6-digit sums 298/300 vs 154 for the plain twin.
- [shown] From-scratch 0.24M "ears" (the small tape/BiGRU readers in results-digest row 23) matched or beat SciBERT on frames.

## lesions

All lesions run automatically in train.py final_eval, using the harness state/talk contract plus LESIONS = ['shuffle_state', 'zero_state', 'noread:1', 'noread:2']. Expected sizes are untested.

1. shuffle_state (Z_R rolled by one row, usually a different family): in_dist ~72 → 3-12. This is guaranteed by construction, so it is a plumbing check, not evidence of reasoning.

2. Donor swap (evalx.donor_eval: same family, different answer; talker on the current row with the donor's Z_R):
- in_dist exact falls 40-50 points, to about 20-35.
- donor_match 60-85% on numeric and label families (arith_bare, story_addsub, the chain families, verify_claim, prop_eval).
- Near 0 on copy families. There the pointer copies the CURRENT row's word at the donor's position.
- Fixed-position copy families (copy_word, last-letter letter_ops) should NOT drop, because the state correctly says 'copy word k' for every row. That is not a failure.
- Pass mark (data.md): drop ≥ 20 and donor_match ≥ 50% on generated-answer families.

3. zero_state: in_dist → 0-2%. A format check only.

4. loops:K sweep. The talker is identical across K, so changes are the loop's.
- loops:0 → 0-3% (a constant output).
- loops:1 → 10-30.
- loops:2 → 25-50 on in_dist but chain-5 ≤ 15, while single-lookup families keep more. A gap of ≥ 20 points between them credits the extra rounds with the multi-step work.
- loops:16 → intact to -30 (unknown). Holding steady would mean a stable iterative operator.

5. noread:1 and noread:2 (reads stop after round K; evaluation only, off-distribution, so confounded like the old zero_pool): chain-5 ≤ 10 and ≤ 20.

6. TRAINED ablation arms, the clean versions:
- read_once (cross-attend only in round 1, same parameters): chain-5 -5 to -15 vs RRL, in_dist -3 to -10. Credits re-reading if ≥ 5 below.
- no_core (talker cross-attends to the reader output X; no latents): in_dist 20-35%, mostly local families such as copy_word, letter_ops, digits_parity. RRL must beat it by ≥ 25.
- linear talker (no talker MLP): ≤ 3 points lost if the talker only translates.

## decisive_test

CHEAPEST TEST that decides it (kill or go): one RRL-S run.
- Setup: seed 0, 24k updates, batch 256, sharing the GPU with its two trained ablations (read_once, no_core). One ~25-min 3-way window, roughly $0.15-0.30 of the $3. [cost suggested]
- Comparison: the 4 existing plain_tf-S seeds on the regular dev. This is exploratory; per CALIBRATION.md the old seeds are not used for a verdict.

Pass marks, fixed in advance. GO to confirmation only if ALL hold:
(a) RRL chain-5 in_dist (200 rows) ≥ 45.0 (the best plain seed was 42.0);
(b) in_dist ≥ 70.0;
(c) donor-swap in_dist drop ≥ 30 points;
(d) loops:2 chain-5 ≤ intact - 15.

PROVES IT WRONG (stop the angle):
- chain-5 ≤ 40 AND multi-step in_dist ≤ 62, so the loop adds nothing on multi-step within plain's seed range; OR
- in_dist < 66 (more than 5 sd below plain).
Side readings: read_once ≥ RRL - 2 on chain-5 means re-reading is not what helps; no_core ≥ RRL - 15 means the latent loop is not doing the work.

CONFIRMATION, if GO: 6 paired seeds (0-5) of RRL-S vs fresh plain_tf-S, both trained with --data on the 200-per-cell build. That is 12 runs, about 4 windows.
- Primary: chain-5 on the big in_dist (1000 rows), paired mean difference ≥ +6.0 AND ≥ 5 of 6 seeds positive.
- Also required: in_dist (6800 rows) difference ≥ -2.0; donor drop ≥ 30.
- Wrong: mean chain-5 difference < +2.0, or in_dist < -4.0.
- Add a plain_tf-S + RRL position-codes control (3 seeds). If it closes ≥ half the chain-5 gap, the codes get the credit, not the loop.
- Then run RRL-M vs plain_tf-M with 2 seeds as a size check (2207.10551).

Total ≈ 7 windows ≈ 2.5-3 GPU-hours. At an assumed $0.4-0.7/h that is about $1-2, within $3. [rate untested]

## implementation

Files:
- custom_io/models/perceiver_loop.py: helpers _feats(prompt) (lru-cached, built on data.word_spans), prompt_features, sincode; classes MHA, SABlock, LocalBlock, ShallowReader, LatentLoop, SlotTalker, PerceiverLoop(Model).
- Register 'perceiver_loop' in models/__init__.py MODELS.
- Queue job custom_io/queue/04-rrl-screen.sh with the three arms.
- Optional later: a pos_feats flag on plain_tf (~25 lines) for the codes control; a steps_aux arm (~45 lines).

Estimated size: about 260 lines for the model; about 330 with the extras.

A working scratch prototype exists OUTSIDE the repo at /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/plr/perceiver_loop.py (244 lines). It implements state/talk, the right-aligned targets, the mixture loss and the noread lesion, and passed a CPU check: forward/backward, evaluate under every lesion, and evalx.donor_eval. It was never trained.

Key pseudo-code:
  state(b, loops):
    X = reader(ids, mask, feats)
    K, V = ca.kv(X)
    Z = Z0
    repeat loops or R times:
      Z += ca(LN(Z), K, V)
      for blk in sa: Z = blk(Z)
    return LN(Z)
  talk(Z, b):
    S = slots + CA(S, LN(Z))
    S += MLP(S)
    logp = logaddexp(log σ(g) + log_softmax(S E^T), log σ(-g) + log scatter_add(softmax(Wq S · P(w, oe)^T), ids))
    argmax per slot → stop at EOS → reverse
  loss = nll(logp, right_aligned(ans))

Gotchas:
(1) Prompt leak into the talker. Pointer keys must be built ONLY from (word index, offset from word end); ids enter only as the scatter target. Add a unit test: with Z fixed, relabelling prompt characters by a bijection must leave the gate, gen logits and per-position pointer mass unchanged.
(2) talk() takes positions and copy source from the CURRENT batch (harness contract). Under the donor swap, a copy family therefore copies the current row's word at the donor's position. Report that separately.
(3) The harness weight-decays every ndim≥2 parameter that is not in an nn.Embedding. Store Z0 and the slots as nn.Embedding, or they shrink about 4x over 24k updates.
(4) Compute the mixture in fp32 under bf16; mask pointer logits with -1e4, not -inf.
(5) Spaces are not copyable; the 1.5% of answers with spaces come from the gen head.
(6) Build features as numpy arrays once per prompt. Per-row torch.tensor calls cost about 3 ms per step.
(7) No round embedding, so loops:K stays valid.
(8) Residual init std 0.02/sqrt(2·R·(n_sa+1)); Z0 std 1; slots std 0.5.
(9) If below about 16 updates/s shared, run 2-way or wrap LatentLoop in torch.compile (untested on the box's torch version).
(10) The dev family split has answers up to 12 characters. Raising n_slots is free here, but raise MAX_ANS for both arms together.
(11) box.sh's hash check must cover train.jsonl only when --data points at the 200-per-cell build.

## risks

1. The most likely failure is a bottleneck tax: 32 latents with 8 soft reads per round underfit the exact lookups (list_index, cipher_map, table_lookup, passage_qa) and the parallel multi-digit outputs, so in_dist lands 3-10 points under plain_tf. Perceiver IO needed pretraining on text (2107.14795). [suggested]
2. 24k updates may be far too few for a weight-shared loop to find a general procedure (2604.07822 needed more than 1.3M steps), so it may memorise templates like everything else. [suggested]
3. Idle rounds: the loop may do everything in 1-2 rounds (2512.11847). loops:K will show this; nothing breaks, but the "loop reasons" claim fails.
4. Stability: 24 residual sub-layers per pass at lr 1e-3. Mitigated by pre-LN, small residual init, 1000 warmup steps and grad-clip; one symmetric lr retry is allowed.
5. Throughput: 9x more kernels than plain_tf. If it is launch-bound, the --minutes cap cuts updates and biases against RRL.
6. Attribution confounds: any vocab/answer win is the pointer (a plain_tf with a copy head could match it), and any multi-step win could be the digit-place codes. Hence the codes control.
7. The talker MLP may do the last arithmetic step (a partial leak); the linear-talker ablation bounds it.
8. The pointer's positional-extreme shortcut ("last word").
9. Held-out families stay near 0. Nothing here helps with new kinds of task, and new kinds are what "critical thinking" ultimately needs.
10. If the angle loses, the honest fallback is that a plain small transformer is already the bar. The value left would then be the clean core/talker split and cheap one-pass decoding, not accuracy.

## english_and_minecraft_path

English: keep the loop and the talker and change only the reader's lexicon. Use a shallow word-piece or char-CNN table, still with no cross-token mixing, trained on skills rows plus generated paraphrases. Optionally initialise it from a small pretrained embedding table (under 5M parameters, counted in the size). New wording then changes only reader features, and the donor swap keeps showing whether the loop carries the answer. [untested]

Minecraft: a Perceiver loop reads any array. The same latents can cross-attend at once to voxel and entity arrays, inventory slots and chat tokens, each with its own shallow reader and type code. The latents persist across game ticks as working memory, running a few rounds per tick. The slot queries become action heads (move, look, attack, craft) plus content-free pointers to an entity or inventory slot, so the agent can act on items it has never seen. Few-example learning would put demonstrations into the input array and let the loop infer the rule (2311.12424). [untested]

