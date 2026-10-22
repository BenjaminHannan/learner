# Why does our looped "thinker" model gain so little from size, when a plain transformer gains a lot? Causes other than width, please.

You are an expert in training small neural networks: scaling behaviour, recurrent/looped transformers, optimisation,
data mixtures, output heads and evaluation design. Everything you need is below; answer from it directly, without
asking me to run anything first. If a fact you need is missing, name it and say how it would change your answer.
Mark every claim **shown** (follows from the numbers below), **suggested** (your inference) or **untested**.

I am a high-school senior building this with AI help. End with a plain-language summary I can follow (under 150 words).

Scope: only this one controlled comparison ("gate G1": two models, two sizes, same data). Other experiments in my project
are out of scope; don't mix them in.

## 1. The question

Going from 3M to 10M trained parameters (seed 400), **our model gained +1.64 points and the plain model gained +5.35**
on the same data, same updates, same learning rate. Two earlier outside reviews already blamed (a) growing by depth
instead of width and (b) our answer writer, which writes all letters at once. Both fixes are queued (section 7).
**I want every other plausible cause**, ranked, with a cheap test for each. My goal: our model's own score must clearly
rise with size (not just beat the plain model's gain), because the shipped model is about 100M trained parameters
(ladder 3M, 10M, 30M, 100M), trained on one 16 GB home GPU.

## 2. Headline results (shown; seed 400 unless stated)

Score = "pooled-5": exact match (strip, lowercase, collapse spaces; any accepted answer) over 6,040 dev rows in five
files, greedy decoding, final weights (no best-checkpoint pick).

| arm | 3M | 10M | gain |
|---|---|---|---|
| ours (G-B2) | 73.013 | 74.652 | +1.639 |
| plain (G-PT) | 67.119 | 72.467 | +5.348 |
| difference of gains | | | -3.709 |

- Seed 401 at 3M: ours 73.675, plain 68.013. No 10M seed 401. Plain-model seed sd about 1.0; one-seed paired
  difference sd about 1.4 (earlier ladder).
- A separate 160-row file of 4 never-seen skill families (not in the score): both arms 2-4% at every size.
- "Chain-5" (1,000 multi-step arithmetic chains): ours 99.9 -> 100.0, plain 91.0 -> 98.8.

Per dev file:

| file (rows) | ours 3M | ours 10M | ours gain | plain 3M | plain 10M | plain gain |
|---|---|---|---|---|---|---|
| in_dist (1,360) | 86.03 | 88.31 | +2.28 | 83.75 | 90.00 | +6.25 |
| answer: new answers (1,200) | 71.92 | 72.92 | +1.00 | 57.75 | 64.83 | +7.08 |
| frame: new frames (1,360) | 86.62 | 87.87 | +1.25 | 83.09 | 87.94 | +4.85 |
| vocab: new words (800) | 89.38 | 91.50 | +2.12 | 83.50 | 87.12 | +3.62 |
| variant: new templates (1,320) | 36.67 | 38.33 | +1.66 | 32.12 | 36.52 | +4.40 |

Per family (pooled over the five files), sorted by difference of gains. "Gold type" = share of that family's dev rows
whose gold answer is reachable by a calculator program / a number in the workspace / a copied prompt word / free letters
(GEN), from the data labeller, not from the model's routing (columns overlap).

| family | ours 3M | ours 10M | plain 3M | plain 10M | diff of gains | gold type prog/NUM/WORD/GEN % |
|---|---|---|---|---|---|---|
| arith_bare | 91.9 | 98.1 | 58.8 | 85.6 | -20.6 | 99/100/0/0 |
| backward_solve | 80.6 | 81.2 | 36.2 | 52.5 | -15.7 | 100/100/0/0 |
| cipher_map | 65.8 | 60.8 | 3.3 | 10.8 | -12.5 | 0/0/0/100 |
| table_lookup | 27.5 | 31.5 | 53.5 | 70.0 | -12.5 | 0/1.5/31/67.5 |
| chain_ops | 100.0 | 100.0 | 85.5 | 97.5 | -12.0 | 100/100/0/0 |
| story_addsub | 92.0 | 91.0 | 76.0 | 86.5 | -11.5 | 100/100/0/0 |
| story_chain3 | 100.0 | 99.5 | 85.5 | 96.0 | -11.0 | 100/50.5/49/0.5 |
| seq_next | 33.1 | 34.4 | 43.8 | 55.0 | -9.9 | 0/0/0/100 |
| chain_story2 | 89.5 | 87.5 | 83.0 | 90.0 | -9.0 | 100/100/0/0 |
| var_chain | 82.5 | 84.4 | 74.4 | 84.4 | -8.1 | 100/100/0/0 |
| copy_word | 85.0 | 81.0 | 75.5 | 79.5 | -8.0 | 0/0/100/0 |
| div_exact | 88.5 | 85.5 | 79.0 | 83.5 | -7.5 | 100/100/0/0 |
| object_track | 60.5 | 62.0 | 39.0 | 48.0 | -7.5 | 0/0/100/0 |
| odd_one_out | 83.8 | 80.0 | 69.4 | 71.2 | -5.6 | 0/100/0/0 |
| group_induct | 81.7 | 80.0 | 76.7 | 80.0 | -5.0 | 0/0/100/0 |
| order_chain | 71.0 | 68.5 | 67.0 | 69.5 | -5.0 | 0/0/70.5/29.5 |
| fewshot_number_rule | 10.6 | 10.6 | 40.0 | 44.4 | -4.4 | 0/4/0/96 |
| table_calc | 79.0 | 77.5 | 59.5 | 61.5 | -3.5 | 100/100/0/0 |
| distance_units | 85.0 | 85.0 | 80.5 | 83.5 | -3.0 | 100/100/0/0 |
| prop_eval | 87.5 | 88.3 | 78.3 | 81.7 | -2.6 | 0/0/100/0 |
| list_index | 62.5 | 63.0 | 45.5 | 48.5 | -2.5 | 0/8.5/68/23.5 |
| compare_numbers | 75.0 | 75.6 | 84.4 | 86.9 | -1.9 | 100/100/0/0 |
| state_update | 100.0 | 100.0 | 98.0 | 99.5 | -1.5 | 100/100/0/0 |
| word_filter | 65.5 | 64.5 | 65.5 | 66.0 | -1.5 | 0/5/0/95 |
| seq_cycle | 56.9 | 63.1 | 22.5 | 28.8 | -0.1 | 0/0/100/0 |
| percent_rate | 87.0 | 87.0 | 84.0 | 84.0 | 0.0 | 100/100/0/0 |
| syllogism | 86.9 | 86.9 | 86.9 | 86.9 | 0.0 | 0/0/30.5/69.5 |
| letter_ops | 76.0 | 76.5 | 77.0 | 76.5 | +1.0 | 0/0/0.5/99.5 |
| list_stats | 50.6 | 53.8 | 56.9 | 57.5 | +2.6 | 37/70.5/0/29.5 |
| verify_claim | 70.0 | 84.2 | 51.7 | 59.2 | +6.7 | 68.5/0/2/98 |
| passage_qa | 65.5 | 75.5 | 81.5 | 82.0 | +9.5 | 0/0/66/34 |
| rule_apply | 47.0 | 60.0 | 72.0 | 75.5 | +9.5 | 0/2/40.5/57.5 |
| kin_chain | 83.0 | 89.5 | 88.5 | 85.0 | +10.0 | 0/0/50.5/49.5 |
| digits_parity | 45.0 | 58.8 | 58.1 | 55.6 | +16.3 | 0/0/38.5/61.5 |

Notes (shown): ours gained more on 7 of 34 families; ours' own gain is zero or negative on 17 of 34. On the 12
families where plain was 10+ points behind at 3M, the gap closed by 7.98 points (unweighted mean); on the other 22 it
still closed by 1.41. About 2,560 of the 6,040 rows sit in families ours already scored 40/40 at 3M. Seed-to-seed
swings at 3M for ours reach 20 points in single small families (verify_claim 70.0 vs 90.8).

## 3. The two models (shown from code unless marked)

Shared: a **frozen** EmbeddingGemma text encoder (271M parameters, 768-d) reads the prompt; each arm learns a
zero-initialised linear map 768 -> 256 (198,400 parameters). Both arms also see the prompt as characters (108-char
vocabulary). Width 256, 4 attention heads (64 per head) in both arms at both sizes.

**Ours (G-B2, "ledger" model).**
- Character reader: embeddings + position + a "place in word" code, then 2 residual 1-D convolution blocks
  (kernel 5, so about +-4 characters of context), no attention; the frozen encoder's projected state is added here.
  The reader does not grow with size and is not looped.
- Workspace slots: up to 91 numbers found in the prompt (each slot = mean reader state over its digits), constants
  1, 2, 10, 100, and up to 11 result slots. Values are exact integers (|v| < 1e9) in a 93-d code.
- Thinker state: 8 control tokens + 36 register tokens (= 44 vectors of width 256; the registers start as copies of
  reader rows 0-35). Fixed 12 rounds, no learned halting. Each round adds a round embedding and applies the same
  stack of blocks (weights shared across rounds); each block = cross-attention to [workspace slots; reader output],
  then self-attention over the 44 tokens, then an MLP (hidden 4.8x width). Pointer heads use 64-d keys.
- Each round t = 1..11 writes one calculator call: an op head over 9 ops (NOOP, ADD, SUB, MUL, DIV, MOD, MIN,
  MAX, CMP) and two pointer heads that pick operand slots. An exact parameter-free calculator runs it, the result fills
  a result slot and is fed back as a register token.
- After the loop a 3-way mode head picks how to answer: NUM (pointer to a workspace slot, printed exactly), WORD
  (pointer to a prompt word), or GEN (free letters: all up to 35 characters written **at once**, register i ->
  character i, over the 108-char vocabulary, with a copy-from-prompt option). No autoregression in GEN.
- Size growth 3M -> 10M: blocks per round 2 -> 8; nothing else changes. Block applications per answer: 24 -> 96.
  Trained parameters 3,544,913 -> 10,496,537. About 1.2M of the 3M model sits outside the block stack (reader, heads,
  adapter), so the fixed part is ~35% of the 3M model and ~12% of the 10M model.
- Training loss = op CE + operand-pointer NLL + mode CE + NUM/WORD pointer NLL + GEN per-character NLL, all weight
  1.0; rows without a program get op weight 0.1. Teacher forcing: training feeds the gold op and operands each round;
  evaluation runs greedily on the model's own calls.

**Plain (G-PT).** A causal pre-LN character transformer on `[BOS] prompt [SEP] target [EOS]`, tied input/output
embeddings, learned positions, MLP 4.0x. The frozen encoder's projected state is added to the embedding of each prompt
character. Target = `step; step; ... # answer` for 11 multi-step families when it fits 109 characters, otherwise just
the answer. Token-mean cross-entropy over target characters. Greedy decoding. Size growth: 4 -> 13 layers
(3,495,936 -> 10,603,776 trained parameters).

## 4. Training (shown; identical for both arms and both sizes unless stated)

- AdamW, betas (0.9, 0.95), weight decay 0.1 on matrices only, **lr 1e-3 at both sizes** (no width/depth scaling of
  lr), 300-step linear warmup then cosine to 1e-4, grad-norm clip 1.0, bf16 autocast, no dropout.
- Init: all linear/embedding weights N(0, 0.02); residual output projections scaled 0.02/sqrt(3 x blocks x rounds)
  for ours (3M 0.0024, 10M 0.0012) and 0.02/sqrt(2 x layers) for plain.
- **24,000 updates x 256 rows at both sizes** (the step count is a floor that ruled at both sizes), same row order.
  Gradient accumulation (rows split into micro-batches; summing only): ours 4 at 3M, 16 at 10M; plain 4 and 8.
- Data pool: 1,418,702 rows, about 60M word pieces, about 4.3 passes per run (6.1M row draws, ~260M pieces). By pieces
  about 38% are our own synthetic skill rows (the 34 families' generators plus English/teaching rows) and 62% are web
  fill-in rows (a word blanked out of educational web text, to be predicted). The web rows are in both arms' loss but
  not in the score. Pieces per trained parameter: 17 at 3M, 6 at 10M.
- Wall clock on an RTX 5070 Ti 16 GB: ours 6.5 h (3M) and 42.7 h (10M, 0.156 updates/s, GPU often 14-41% busy);
  plain 2.4 h and 4.1 h.

## 5. Training curves and probes (shown)

- Final training loss: **ours 1.139 (3M) -> 1.128 (10M)**; plain 0.366 -> 0.328 (different objectives; not
  comparable across arms). Ours at 3M by term (mean of the last 1,500 updates): program op ~0, operand ~0, mode 0.196,
  NUM 0.009, WORD 0.134, **GEN 0.836** (about 75% of the total; flat after update 12,000). The 10M split by term is
  not logged in what I have.
- Ours at 3M: teacher-forced and free-run op/program accuracy 100% on a 400-row program check, both seeds.
- Ours, in_dist score with lesions at 3M (seed 400): full 86.0; rounds forced to 0/1/2/24 at test time: 1.0 / 24.1 /
  37.1 / 86.0; calculator off 47.8; operand-copy path off 79.4; word-copy path off 63.5; shuffled thinker state 7.7.
- Earlier ladder (same comparison, before the frozen encoder; ours then had a bug: 9 registers instead of 36 and GEN
  targets cut at 8 letters): ours +0.49 over six seeds (95% CI -0.74 to +1.72), plain +3.77 (5 seeds), a plain
  character language model +15.77 (starts 26 points lower). Shape probes (2 seeds): reader made 23 conv layers deep:
  +0.73 / -1.46 and one family broke (97.9 -> 72.5); width 384 x 3 blocks (lr x 256/384): +1.57 / +0.46. Extra rounds
  at test time added nothing at either size; the per-round score profile was nearly identical at 3M and 10M.
- Earlier "skills-only" first look (no web rows, bugged ours, seeds 200/201): ours +1.42 / -0.28 vs plain +2.73 /
  +2.19. **Ours' training loss fell 3x with size (0.0128 -> 0.0039) while in_dist barely moved (89.6 -> 91.0;
  90.9 -> 91.2).**

## 6. Rules any fix must respect

- Everything inside the model is learned; hand-written logic is allowed only as an outside tool the model chooses to
  call (the calculator counts as such a tool). No hand-picked data or settings at run time.
- No cutting training targets short.
- One change at a time, with pass marks written before the run. Compute: the 16 GB GPU above (a 10M run of ours costs
  ~43 h), free CPU for diagnostics on saved weights (final weights of every arm were saved), and about $30/month of
  cloud GPU.

## 7. Already proposed or queued (don't repeat these as your main answer; say how your ideas interact with them)

- WIDE: our 10M built by width instead of depth (width 448, 7 heads, 2 blocks, lr 1e-3 x 256/448). Pass >= 76.31,
  fail <= 75.01.
- G2f: an autoregressive answer writer replacing GEN (it reads the thinker's vectors; it may also be allowed to see
  the question).
- Dropped: more practice rows from the same generators.
- Suggested earlier, not tested: lr not retuned for a deep shared loop; frozen encoder hiding character detail;
  exact match hiding progress; "nothing left to learn" on program rows.

## 8. What I want from you

1. **List and rank the causes other than width and the GEN writer** that could make ours gain so little from size
   while the plain model gains a lot. Cover at least: the data mix and what dominates the gradient; optimiser, lr,
   warmup and init for a 96-application shared stack; the fixed 12 rounds, no halting and teacher forcing; the fixed
   44-token thinker state; the fixed 2-layer local reader and how the frozen encoder reaches each arm; the mode head
   and pointer heads; the update budget; and the score itself (saturated families, catch-up, exact match, noise).
   For each: the mechanism, why it hits ours but not plain, which numbers above support or weaken it, and its label.
   Explain the skills-only result (training loss fell 3x, dev barely moved) and the flat 1.13 loss under the same idea
   if you can.
2. **Diagnostics first:** which of these can be told apart with no training, on the saved 3M and 10M weights and logs
   (CPU only)? Give each as a concrete measurement and what result points which way.
3. **At most three training tests, one change each,** in the order you would run them, each with: the exact change,
   size/seeds, cost on the hardware above, pass mark, fail mark, and the result that would prove your cause wrong.
   Prefer tests at 3M or short runs that predict the 10M outcome, and say how a short run maps to the full one.
4. Which of your causes would still bite at 30M and 100M even if WIDE and G2f both work?
5. Is the yardstick fair (plain step model, pooled-5, one seed)? What single number would convince you that our design
   scales well?
6. A plain-language summary for me, under 150 words.
