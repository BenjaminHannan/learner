# StreamPonder: an attention-free word-stream LSTM reasoner (reads twice, ponders, halts) with a talker that sees only the final state

_Nothing pretrained and no attention anywhere. A per-word character-slot encoder feeds one weight-tied 3-layer LSTM. The LSTM reads the question twice, ponders for up to 8 silent ticks with a separate halting head, then hands one 320-number vector to a 1-layer GRU talker that never sees the question. I expect it to lose 3-8 points overall to a same-size plain transformer [suggested]. Its best chance of a measurable win is on the running-state families (state_update, var_chain, chain_ops, chain_story2, story_chain3), where the plain transformer is weakest._

## reader

Per-word character-slot encoder (custom_io/models/stream_ponder.py). It has no attention, no recurrence and nothing pretrained.

Input:
- The row's prompt is split with the harness's data.word_spans (words, numbers and punctuation; spaces dropped).
- Measured [shown]: 22-28 words per prompt at the median, 37-41 at p95 and at most 51, across all splits. Longest word is 11 characters in train and 12 in dev/family.
- Numbers have at most 4 digits.

Per word:
- Up to Lw=12 character ids are right-aligned into 12 slots, with PAD on the left. Longer words keep their last 12 characters.
- Embedding(108, 32, padding_idx=PAD) gives [12, 32]. Flattened that is 384, then Linear(384, 256) and LayerNorm(256).
- Added embeddings: word length (13 x 256), a space-before flag (2 x 256) and a tick type (marker / pass-1 word / later-pass word / ponder, 4 x 256).
- Output: [B, n_words, 256].
- At 10M: Embedding(108, 48) and Linear(576, 384).

Right-alignment puts units, tens and hundreds digits in fixed slots. This is Abacus-style place alignment (2405.17399). Unseen made-up words and the dev-only symbols (# @ & $ O) still get distinct character codes, because the harness gives every ASCII character its own id.

What it can compute: anything inside one word. That covers spelling, letter n, word length, digit identity and place, and the parity or size of a single number.

What it cannot compute: anything across words. It sees one word at a time, so it cannot bind a number to a noun, compare, count, look up or do arithmetic. Every cross-word step has to happen in the core.

## reasoner

One stacked LSTM run through cuDNN: 3 layers x 320 at 3M, 3 layers x 640 at 10M. The same weights apply at every tick, so the loop is the time axis. The effective depth is ticks x 3 layers.

Tick schedule per row:
- [pass marker][w1 .. wn] [pass marker][w1 .. wn] [ponder] x K
- R = 2 reading passes, then K = 8 ponder ticks.
- Ponder input is one learned constant vector plus the ponder tick-type embedding, so ponder ticks get no prompt input.
- Total ticks = R(n+1) + K: 58 at the in_dist median, 86 at p95, at most 112.
- All rows go through one cuDNN call with pack_padded_sequence over variable lengths.

Re-reading is the recurrent form of "re-feed the input every loop" (Recall 2202.05826, TRM). It turns facts-first lookups into question-first filtering. By pass 2 the state already holds the question ("word before quilt", "colour of the river", "decode 5 6 5"), so the core only has to pick out matching words as they stream by. Just Read Twice (2407.05483) measured +11 points for recurrent LMs this way.

State:
- (h, c) for each layer, 3 x 2 x 320 = 1,920 numbers.
- Only the top-layer h at the chosen tick (320 numbers) leaves the core.

Halting:
- Candidate states are k = 0..K. k = 0 is the last word tick of pass 2, before any pondering.
- A linear head (321 params) on each candidate predicts "the talker would answer exactly from this state".
- At inference the row halts at the first k with sigmoid >= 0.5, otherwise at K.
- The head is trained on detached states, so it can never change what the state contains. This guards against the repo's earlier failure where the stop head always quit after round 1.

Lesion knobs:
- `loops:K` forces exactly K ponder ticks with no halting. train.py sweeps 0, 1, 2 and 16.
- `reads:1` runs a single reading pass.
- `halt:off` always uses tick K.

Cells I rejected, and why:
- minGRU / Mamba: these linear recurrences fall in TC0 (2404.08819). In the xLSTM paper's table Mamba scores 0.05 on modular arithmetic against 1.0 for an LSTM. The running-state families need exactly that kind of state tracking.
- The old looped MLP core applied per chunk, and sLSTM: no fused kernel. A Python loop over about 100 ticks would break the 25-minute budget [suggested].

## talker

A 1-layer GRU (cuDNN), hidden 256 at 3M and 320 at 10M.

- Starting state: h0 = tanh(Linear(s)).
- Input at every step: [Embedding(108, 64)(previous char), Linear(s)]. The state is fed again at each step.
- Output: Linear(256, 108).
- Decoding is greedy for at most 9 steps (8 characters + EOS), starting from BOS.
- Answers come out in the dataset's own order, most-significant digit first. Carries run from the least-significant end, so the talker cannot easily finish an addition while it writes the digits.

Confirmed: talk(state, batch) reads only the state, plus the batch size and device. It gets no prompt_ids, no prompt lengths, no rows, no copy pointer and no attention. The only other influence is the halting head, which chooses which of the K+1 = 9 candidate states is handed over. That is at most about 3.2 bits of selection and carries no content.

It is the classic seq2seq decoder (Cho et al.) with no attention. Ben's design note fits: it translates a vector into characters.

Fallback if the probe lesion shows the GRU is doing arithmetic: replace it with per-slot heads (logits_i = MLP([s, E[Q_i]]) using the harness's Q0..Q7 ids, TRM-style). This is one change.

## why_reasoner_must_reason

The bottleneck argument: the only path from prompt to answer is reader (one word at a time, no context) -> LSTM core -> 320-number h -> talker (state only).

Any fact that spans more than one word has to be computed by the core and stored in that h at the halting tick. Examples are which number belongs to which noun, the running total, the item after "quilt", and the mapping 5 -> e. Unlike the sandwich, nothing downstream can re-read the words. The posterior-collapse result (1611.02731, the VAE line) says a latent carries only what the decoder cannot model locally. Here the decoder has nothing local to model the answer from.

What can still leak around the bottleneck:
1. The GRU talker can do some computation on what the state holds, for example finishing a sum or picking one of two stored words. The most-significant-first order makes carry arithmetic awkward. The frozen-state linear probe (lesion 6) measures how much this happens.
2. The reader computes features inside one word (a number's parity, digit places). These are local, not reasoning across words.
3. The halting head chooses which tick is decoded, about 3 bits of selection.
4. Dataset shortcuts are learned by the core itself, so they are not a leak, but they inflate in_dist. Examples: syllogism "starts with No -> no", object_track "last place named", and the 82% template overlap. Report syllogism and object_track separately.

Honesty point: the donor-swap collapse is guaranteed by the wiring and proves only the wiring. Evidence that the core reasons rather than memorises must come from four places: the chain families, the variant split, the probe, and the reads/loops lesions.

## params

Parameter counts come from building the modules on CPU [shown]. FLOP figures are hand arithmetic [untested].

**3M setting: total 3.135M** (plain_tf d256 L4 is 3,244,544, so 3% smaller)
- Reader 0.108M:
  - character Embedding 108x32 = 3.5k
  - slot Linear 384->256 = 98.6k
  - LayerNorm 0.5k
  - length, space, tick and ponder embeddings 5.4k
- Core 2.384M: LSTM 256->320 with 3 layers (739,840 + 821,760 + 821,760), plus the halt head (321).
- Talker 0.643M:
  - character Embedding 108x64 = 6.9k
  - init Linear 320->256 = 82.2k
  - state-input Linear 320->256 = 82.2k
  - GRU (64+256)->256 = 443.9k
  - output Linear 256->108 = 27.8k

**10M setting: total 10.556M** (plain_tf d384 L6 is 10,775,040, so 2% smaller)
- Reader 0.236M
- Core 9.19M: LSTM 384->640 x3
- Talker 1.13M: GRU hidden 320

**FLOPs per example**, forward, at the in_dist median of 58 ticks:
- 3M:
  - core 2 x 2.38M x 58 = 0.28 GFLOP
  - talker in training (9 states x 9 steps) 2 x 0.64M x 81 = 0.10 GFLOP
  - total 0.38 GFLOP, against plain_tf 2 x 3.24M x ~92 positions = 0.60 GFLOP (+~0.03 attention)
  - so about 0.6x in training and about 0.5x at inference
- 10M: 1.07 + 0.18 = 1.25 GFLOP against about 2.0 GFLOP, so about 0.6x.
- plain_tf's harness decode has no KV cache, so its real eval cost is several times higher still.

The parameter-matched plain_tf therefore already gets about 1.6x our compute. A plain_tf looped to matched compute would be smaller, not bigger.

Sequential depth runs the other way: 58-112 ticks x 3 layers against 4-6 parallel layers. Wall-clock per update is not lower and must be measured.

## pretrained_parts

None. Every weight is randomly initialised and trained only on the 200k skills rows, with the harness's 108-id character vocabulary. Nothing is borrowed, so the counted size is the whole model: 3.14M or 10.56M.

## training

**Main loss: deep supervision over the candidate halting states.**
- S = top-layer h at ticks k = 0..K, shape [B, K+1, d].
- Run the talker teacher-forced on all B(K+1) states in one cuDNN call. Inputs are [BOS, a0..a7]; targets are ans_ids with ans_mask.
- Take the per-row mean NLL over answer characters, giving [B, K+1].
- Weight the ticks with w_k = (k+1) / sum(j+1), so later ticks count more but every tick must hold a decodable answer. This is TRM/HRM-style deep supervision.

**Halting loss.**
- Weight 0.1 x BCE(halt(S.detach()), y_k).
- y_k = 1 when every teacher-forced argmax at tick k matches the target up to and including EOS. That is exactly equivalent to "greedy decoding from this state is exact".
- The aux values (nll_last, acc_tf_last, halt_bce) are logged through the harness's aux dict.
- The main arm uses no steps supervision.

**Optimiser:** the harness defaults throughout.
- AdamW (0.9, 0.95), weight decay 0.1 on matrices (including the LSTM/GRU weights), none on embeddings and biases.
- lr 1e-3, the same as the plain_tf calibration, with no extra tuning for either arm.
- Warmup 300 then cosine to 10%, clip 1.0.
- Batch 256, 24k updates (30.7 epochs), shuffled order, same --seed as the paired plain_tf.

**Precision:** autocast is disabled inside the model and cuDNN LSTM/GRU run in fp32/TF32. nn.LSTM is not on the autocast list, so bf16 inputs would mismatch the fp32 weights.

**Init:** orthogonal recurrent weights (weight_hh), LSTM forget-gate bias 1, PyTorch defaults elsewhere.

**Speed** [untested]:
- 3M: about 40-60 updates/s alone, about 15-20 when shared 3-way, so 20-27 min for 24k.
- 10M: may need 2-way sharing.
- Run a 300-update timing smoke test first.

**Needed beyond the harness:**
- A per-prompt word cache inside the model.
- Custom lesions declared in LESIONS (train.py's final_eval runs them automatically).
- A re-eval on sk200k_big with `python -m custom_io.evalx --run DIR --data .../sk200k_big`.
- A 70-line frozen-state probe script.

**Optional phase 2.** Only after the screen passes, and only as a separate arm: in-stream running-value supervision from row['steps'] for the 11 arithmetic families.
- Parse each step with a regex for 'a op b = c' and for state_update's '+b -> c'.
- Find the first prompt word equal to operand b after the previous match, within pass 1.
- At the following tick, add 0.3 x talker NLL of the string c.
- The same-information control is plain_tf with a small aux head that decodes c at the same character position.
- Note: 2603.21676 found per-step supervision hurt extrapolation, while the repo's worked steps helped (+11.8 fit). This is untested for a streaming core.

## predictions

**Baselines** [shown]:
- plain_tf 3.2M, 4 seeds, 24k updates:

| measure | score |
|---|---|
| in_dist | 75.7 (sd 1.7) |
| answer | 43.7 |
| frame | 71.2 |
| vocab | 60.5 |
| variant | 20.2 |
| family | 0.8 |
| multistep in_dist | 62.1 |
| pooled-5 | 54.2 |
| chain4 (chain_ops 8.1, chain_story2 47.5, state_update 40.0, var_chain 27.5) | 30.8 (sd 3.7) |
| chain5 (adds story_chain3 65.0) | 37.6 (sd 2.9) |

- plain_tf 10.8M, 1 seed: in_dist 76.0, chain4 36.9, chain5 43.0.
- Sandwich: in_dist 74.6, four chain families 22.5.

**StreamPonder 3M, R=2, K=8** [untested; my point estimate (range) and difference]:

| split | estimate | difference / note |
|---|---|---|
| in_dist | 70 (62-77) | about -6 |
| answer | 40 (33-46) | |
| frame | 63 (55-72) | likely a loss: unseen opener words disturb a running state |
| vocab | 58 (50-64) | |
| variant | 21 (15-27) | a tie |
| family | 1-5 | a tie at the floor |
| pooled-5 | 50 (44-56) | about -4 |
| multistep in_dist | 60 (50-70) | about a tie |
| chain4 in_dist | 42 (28-60) | about +11 |
| chain5 on the 1000-row big dev | 46 (34-62) | about +8 |

- Families where it may win:
  - state_update 70 (50-90) vs 40: a running total is a natural LSTM job.
  - object_track 80 vs 67.5: state tracking and swap parity.
  - table_calc 60 vs 49.
  - list_index 65 vs 54: re-reading turns the lookup into filtering.
- Families where it likely loses:
  - arith_bare 60 (45-75) vs 77.5: products must be formed inside a fixed state.
  - percent_rate and backward_solve.
  - fewshot_number_rule 50 vs 65.
  - cipher_map 45 vs 52.5.
  - kin_chain and order_chain: two-hop, facts-first.
- Worst families for StreamPonder: chain_ops 5-20, var_chain 20-45, cipher_map 35-65, fewshot_number_rule 40-65, seq_cycle 45-70.
- Held-out families: 0-5%, a tie (unit_convert maybe a few rows; clock_date 0).

**Other arms** [untested]:
- R=1, the pure angle with no re-read: in_dist 60 (50-70), and -15 to -40 on facts-first lookup families compared with R=2.
- 10M: in_dist 72 (64-78) vs 76.0; chain4 45 (30-62) vs 36.9. The gap to plain_tf probably widens with size (2207.10551) [suggested].

**Odds** [suggested]:
- Beats plain_tf on pooled-5 by 3 points or more: about 10-15%.
- Within 3 points (non-inferior): about 35%.
- Chain5 big-dev gain of +8 or more: about 40%.
- Most likely outcome (about 60%): loses 3-8 points pooled and wins 5-20 points on the running-state families.

Against the 1.2B sandwich [suggested]: about level on in_dist and ahead on the chain families. But plain_tf already beats the sandwich there (30.8 vs 22.5), so the sandwich is not the real bar.

## evidence

**Supports (all from papers.md unless marked):**
- 2405.04517, xLSTM table [shown]: LSTM scores 1.0 on parity and modular arithmetic. Mamba scores 0.13 and 0.05, Llama 0.03 on parity. 2404.08819 shows SSMs cannot compose permutations. Hence an LSTM cell rather than Mamba or minGRU.
- 2407.05483, Just Read Twice [shown]: repeating the prompt gave +11.0 points on average over 16 recurrent LMs. Hence R=2.
- 2202.05826 [shown]: re-injecting the input every iteration took prefix sums from 0% to over 97% at 512 bits. Re-reading is our version of this.
- 2510.04871 and 2506.21734, TRM/HRM [shown]: the gains come from deep supervision across passes and full backprop. TRM: full backprop 87.4 vs 56.5 with a 1-step gradient. HRM: +13pp from 1 to 2 loops.
- 2107.05407 [shown]: PonderNet's halting extrapolated where ACT failed.
- 2405.17399, Abacus [shown]: digit-position alignment was the real blocker. Hence right-aligned slots.
- 1909.07940 [shown]: a character CNN was the best number encoder, and even an untrained one beat BERT.
- 1803.03067 and FiLM [shown]: from-scratch LSTM/GRU question readers are enough on templated language (CLEVR 98.9 / 97.6).
- 1612.03969, EntNet [shown]: a non-transformer recurrent slot memory solves bAbI and tracks state to T=80. This is the fallback.
- Repo [shown]:
  - plain_tf fails mainly on running-state and lookup families: chain_ops 8.1, var_chain 27.5, table_lookup 28.1, state_update 40.0 (4 seeds). That is the niche.
  - Tiny looped reasoners with no language: 6-digit sums 298/300 vs 154 for the plain twin.
  - From-scratch tape/BiGRU readers (0.24M) vs SciBERT: about level on seen frames (1,867/1,847 vs 1,954 of 2,000), behind on new ones (2,149/2,290 vs 2,682 of 3,000). SciBERT executed 0 of 46 real sentences.

**Contradicts:**
- 2402.01032, Repeat After Me [shown]: fixed-state models need about 100x more samples to copy, and an LSTM could not learn copying of strings up to 300 tokens.
- 2312.04927, Zoology [shown]: a 70M attention model beats a 1.4B gated-convolution model on multi-query recall. Binding is the known weakness. Here copies are at most 8 characters and there are at most 7 key-value pairs, and re-reading helps but does not remove it.
- 1612.03969 [shown]: a plain LSTM had error 0.226 on the T=40 world-model task, where EntNet had 0.
- 2207.02098 [shown]: RNNs fail non-regular tasks; only structured memory generalises.
- 2212.04458 [shown]: LSTMs meta-learn far worse than transformers. Expect no gain on fewshot or held-out families.
- 2207.10551 [shown]: the vanilla transformer scales best overall.
- 2603.21676 [shown]: free text was the weak case for depth-recurrent models (60% OOD, about level with a 4M transformer), and learned ACT undershoots.
- Repo [shown]:
  - The stop head always quit after round 1.
  - tf2x4 (looped) scored 59.3 vs 65.7 for tf3m at 8k updates (1 seed).
  - A 3.2M plain_tf already matches the 1.2B sandwich on in_dist (75.7 vs 74.6).

**Outside papers.md, not checked here:**
- Learning to Execute 1410.4615: an LSTM reads programs much like var_chain (critic-listed).
- DreamerV3 2301.04104: a recurrent world model in Minecraft.

## lesions

All of these run in train.py's final_eval through LESIONS, n_loops and donor, except the probe.

1. **donor** (harness; same family, different answer).
   - Expected: in_dist exact falls from about 70 to 5 or less, a collapse of about 65 points. donor_match is about 55-70, roughly the model's own accuracy.
   - Mark (data.md): a drop of 20+ points and donor_match of 50% or more.
   - This is guaranteed by the wiring and proves only that no side path exists.
2. **shuffle_state** (rolls the state across the batch, mostly across families): exact falls to 2-8, the label coincidences. **zero_state:** 0-3, a format check only.
3. **reads:1** on the R=2 model.
   - Expected: in_dist -10 to -25 overall.
   - Facts-first lookup families (list_index, table_lookup, cipher_map, facts-first passage_qa, rule_apply, kin_chain): -20 to -60.
   - Question-first families (copy_word, letter_ops, arith_bare): 0 to -5.
   - This shows the lookup happens inside the core's second pass.
4. **loops:0** (no pondering; the state after the last word).
   - Expected: -1 to -6 overall, and -3 to -15 on arith_bare, percent_rate, story_chain3 and seq_cycle.
   - If the drop is under 1 point everywhere, pondering is decorative. Report that as a negative result.
   - **loops:16** (twice the trained count): within 2 points of K=8. Otherwise the loop is unstable past its training horizon.
5. **halt:off** (always tick K).
   - Expected: within 1 point of adaptive halting.
   - The mean halting tick on the chain families should be at least 2 ticks later than on copy_word, letter_ops and syllogism. If not, halting carries no information.
6. **Frozen-state linear probe** (new script, about 2 min of GPU).
   - Freeze the reader and core. Fit 9 per-slot linear softmax heads (320 -> 108) on the halted state of 50k train rows for 2k Adam steps. Decode slots up to EOS.
   - Mark: the probe recovers at least 80% of the talker's exact overall and at least 70% on chain5.
   - A probe far below the talker on numeric families means the GRU is doing arithmetic. Then switch to the per-slot talker.
7. **Mid-stream decode** (no training).
   - Apply the talker to pass-1 states at the tick after each state_update event, and report the % that equal the running total.
   - Above 30% would mean the core keeps a running value without being told [untested]. This is the clearest picture Ben can show of what the reasoner thinks.

## decisive_test

**One 3-run pack**, shared 3-way on the 5090. About 25 minutes and roughly $0.15-0.25 [untested cost].
- A: stream_ponder 3M (R=2, K=8), seed 0.
- B: stream_ponder 3M with R=1, seed 0. This is the pure-angle check.
- C: a fresh plain_tf 3M (d256 L4), seed 0.
- All three: 24k updates x batch 256, lr 1e-3, --final-eval.

C is needed because the calibration runs kept only RESULT.json and no checkpoint [shown]. C's checkpoint lets both A and C be re-evaluated with `python -m custom_io.evalx --run DIR --data .../sk200k_big` on the 5 chain families x 200 in_dist rows (1000 rows; SE about 1.6 points per arm).

**Pass marks**, fixed now. All four must hold:
1. chain5_big(A) - chain5_big(C) >= +8 points. This is where a streaming state should win.
2. in_dist(A) >= 68.0 on the standard dev. That is plain_tf's 4-seed mean of 75.7 minus about 4.5 sd, a screening non-inferiority floor.
3. donor in_dist exact <= 10 and donor_match >= 50.
4. A finishes 24k updates with status 'ok' inside 30 minutes when shared 3-way.

**Proves it wrong:**
- chain5_big(A) - chain5_big(C) < +3. Then the attention-free reasoner is just a weaker transformer on this benchmark, even on the families built for it. Stop the angle.
- Mixed result: a gain of +8 or more but in_dist below 68. That is a niche (state tracking), and the next step is a hybrid that adds an addressable memory, not more of this design.
- A - B in_dist tells whether re-reading is essential. Expected +8 or more.

**Confirmation**, only if the screen passes: 6 paired seeds at 3M (stream_ponder vs plain_tf, same seeds and order), 12 runs in 4 packs.
- Primary: mean paired chain5_big difference of +5 or more, positive in at least 5 of 6 seeds, with a McNemar test on paired rows.
- Secondary: pooled-5 paired difference of -3 or better.
- Disproof: mean chain5 difference below +2, or pooled-5 below -5.
- 10M: 3 paired seeds only if budget remains.
- Total is about 4-4.5 GPU-hours. Check that against the $3 cap at the box's hourly rate first.

## implementation

**Files:**
- New: custom_io/models/stream_ponder.py, class StreamPonder(Model), about 260 lines.
- Register it in custom_io/models/__init__.py: `MODELS['stream_ponder'] = StreamPonder`.
- New: custom_io/probe_state.py, about 70 lines.
- Phase-2 step-alignment aux inside StreamPonder.loss, about 60 lines, off by default (`steps_w=0`).
- About 30 lines of tests added to test_harness.
- Total about 420 lines. A few hours of work.

**Pseudo-code:**
```
LESIONS = ['shuffle_state','zero_state','reads:1','halt:off']; n_loops = K

__init__(vocab, d_c=32, d_in=256, d=320, layers=3, d_t=256, d_ce=64, reads=2, n_loops=8, halt_w=0.1, Lw=12)
  reader: ce=Emb(V,d_c,pad=PAD); wproj=Lin(Lw*d_c,d_in); wln=LN; len_emb=Emb(Lw+1,d_in);
          sp_emb=Emb(2,d_in); tick=Emb(4,d_in); ponder=Param(d_in)
  core:   LSTM(d_in,d,layers,batch_first); halt=Lin(d,1)
  talker: t_ce=Emb(V,d_ce); t_init=Lin(d,d_t); t_in=Lin(d,d_t); t_gru=GRU(d_ce+d_t,d_t); t_out=Lin(d_t,V)

_words(rows)   # CPU; cache keyed by prompt string; uses data.word_spans
  -> W[B,n_max,Lw]  right-aligned char ids
     sp[B,n_max]    1 if a space precedes the word
     n[B]

_states(batch, R, K)   # inside torch.autocast('cuda', enabled=False)
  x = wln(wproj(ce(W).flatten(2))) + len_emb((W!=PAD).sum(-1)) + sp_emb(sp)
  T = R*(n+1)+K; t = arange(T.max())
  pos = t % (n+1)
  idx = where(t < R*(n+1), pos-1, -1)        # -1 = marker or ponder
  typ = 0 if marker, 1 if pass-1 word, 2 if later-pass word, 3 if t >= R*(n+1)
  seq = gather(x, idx.clamp(0)) * (idx>=0) + ponder*(typ==3) + tick(typ)
  out = pad_packed(core(pack_padded(seq, T.cpu(), enforce_sorted=False)))
  return out.gather(1, (T-K-1)[:,None] + arange(K+1))   # [B,K+1,d]; k=0 = last word of final pass

loss(batch)
  S = _states(batch, reads, K)
  lg = talker_tf(S.flatten(0,1), [BOS, ans[:, :-1]].repeat_interleave(K+1))
  nll[B,K+1]   = masked CE mean
  main         = (nll * w).sum(1).mean()
  y            = (argmax == tgt | ~mask).all(-1)
  hb           = BCE_logits(halt(S.detach()), y)
  return main + halt_w*hb, aux

state(batch, loops=None)
  S = _states(batch, R_now, loops or K)
  if loops given or halt_off: return S[:, -1]
  stop = sigmoid(halt(S)) >= .5; stop[:, -1] = True
  return S[ar, stop.float().argmax(1)]

talk(s, batch)   # touches only s, len(s), s.device
  h = tanh(t_init(s)); c = t_in(s); prev = BOS
  9 greedy GRU steps; decode

generate(batch, lesion)
  'reads:R' / 'halt:off' -> set the override in try/finally, return talk(state(batch), batch)
  anything else          -> super().generate(batch, lesion)
```

**Gotchas:**
1. Prompt leak into the talker. talk() must never read batch['prompt_*'] or rows. Test: talk(s, batch) must equal talk(s, the same batch with prompt_ids zeroed and rows emptied).
2. cuDNN RNN under autocast: disable autocast in the model and call .float(). Otherwise bf16 inputs hit fp32 weights.
3. pack_padded_sequence needs lengths on CPU and enforce_sorted=False. The k=0 index is T - K - 1, not T - K.
4. loops:0 means K=0, so S has a single state. Forced loops must bypass halting.
5. Build the words from batch['rows'], not prompt_ids. donor_eval pads prompts to a common length, and rows are unaffected by that.
6. Words longer than 12 characters keep their last 12 (one row in dev/family). Characters seen only in dev already have their own ids.
7. Halting labels: teacher-forced all-correct is identical to greedy-exact. Keep the BCE on detached states.
8. Deep supervision runs B·(K+1) = 2304 rows x 9 x 108 logits. Fine.
9. The harness weight-decays the LSTM/GRU matrices. Keep that the same as plain_tf; do not tune it.
10. Keep the default cfg small enough for test_harness's CPU smoke run, or pass a tiny cfg there.
11. Pair the data order with plain_tf through the same --seed. Report status 'ok' (24k updates reached), never time_cap.

## risks

1. **The most likely failure** [suggested]: multi-digit products and quotients have to be formed inside a 320-number state in a few ticks. That would cost 10-25 points on arith_bare, percent_rate, chain_ops and var_chain, and could cancel the expected running-total gains. Then chain5 lands within noise of plain_tf.
2. **Binding and lookup.** Two-hop facts-first questions (kin_chain, order_chain) need more than two passes or entity slots. Multi-entry tables (cipher_map) strain a vector state (2402.01032, 2312.04927). R=3 or an EntNet / delta-rule memory would be the next step, and that memory is linear attention in disguise. The angle would then end with "pure recurrence is not enough here".
3. **Overall loss to plain_tf.** Likely 3-8 points pooled. The frame split may suffer because unseen opener words disturb the running state. At 10M the gap probably widens (2207.10551).
4. **No movement on held-out families.** They stay at 0-5%. LSTMs meta-learn worse than transformers (2212.04458). Nothing here addresses new task kinds, which need more task diversity or episodic training. Ben's few-examples north star is not advanced by this design.
5. **Decorative pondering or halting.** Deep supervision may fix the answer by k=0, and the halting head may always stop at k=0 (the repo precedent). That is harmless to accuracy but kills the "ponder" story. The loops:0 and halt:off lesions will show it.
6. **The talker computing.** If the GRU talker does arithmetic, credit leaks to it. The probe lesion detects this.
7. **Speed** [untested]: the sequential ticks plus fp32 cuDNN may push the 10M arm past 25 minutes when shared 3-way. Fall back to 2-way sharing, 2 layers x 768, or K=4.
8. **LSTM seed sensitivity** on algorithmic families. 6 seeds are required before any claim.
9. **Tuning asymmetry.** Both arms run at lr 1e-3 with no grid. LSTMs may want a different lr, but changing it for one arm only would be unfair.
10. **Shortcuts.** Syllogism and object_track shortcuts and the 82% template overlap inflate in_dist for both arms. Report those families separately.

## english_and_minecraft_path

**English.** The word-slot reader handles any spelling with no tokenizer vocabulary, so the same streaming core can move on to human-written English. The path is templated questions first, then simple QA. But from-scratch English needs vastly more data (Huginn used about 800B tokens). Long passages will expose the recall weakness, so that step likely needs an addressable recurrent memory (EntNet or delta rule) or a small borrowed embedding table [suggested].

**Minecraft.** An agent gets a continuous stream of observations and events, and a fixed-size recurrent state that ponders before each action is the shape that already reached diamonds from scratch (DreamerV3, 2301.04104, outside papers.md, not checked). The talker would become an action head that reads only the state. That keeps Ben's split: the reasoner decides, the talker translates.

