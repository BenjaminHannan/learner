# Custom reader/talker panel: synthesis and test plan (2026-10-05)

Labels: [shown] = measured, [suggested] = reasoned, [untested] = guessed. Facts I checked in the repo:
- With 3 runs sharing the GPU, plain_tf-S trains at 20.7 updates/s [shown].
- 23,042 train rows have 2 or more step values [shown].
- RRL's "100% parse" claim is wrong. Only 1,944 of 4,095 story_chain3 rows and 2,792 of 5,106 state_update rows parse fully.
- The brief's chain_ops 2-8% and state_update 8-10% are the 8k-update figures. At 24k updates they are 5-12% and 32-52%.
- box.sh leaves *.pt out of the results it ships back, and the evalx CLI defaults to CPU and prints totals only. So every big-dev and lesion eval has to run inside the job.

## 1. Ranking

| # | Design | One line | Evidence / Ben-fit / Testability = Total | Size S / M (all from scratch) | Verdict |
|---|---|---|---|---|---|
| 1 | Abacus Loop | Slot loop whose units-first register must hold the r-th worked-step value after round r; linear talker | 6 / 7 / 7.5 = 20.5 | 3.25M / 10.79M | **Test now**, merged into A. It has the best causal lesion (register interchange). |
| 2 | TRM-Text | Conv reader feeding a recursive slot net with deep supervision; linear talker | 4 / 8 / 8 = 20 | 3.11M / 10.77M | **Test now**, merged into A. Its reader becomes A's reader, and its answer-only recursion becomes arm A0. |
| 3 | Ledger | The loop writes (op, slot, slot) steps for an exact executor; the talker prints or copies | 8 / 6 / 5 = 19 | 3.33M / 10.79M | **Test now** as B (Ledger-lite). It is the most direct fix for plain_tf's measured failures, by a different mechanism. |
| 4 | Typed Word-Slot Workspace | Context-free word reader, slots that hold running values in place, typed linear talker | 5.5 / 8 / 5 = 18.5 | 3.26M / 10.69M | **Later.** It needs 1.62x the FLOPs and about 400 lines, and A and B already cover its parts. |
| 5 | Re-Reading Latent Loop | Perceiver latents re-read a ±4-character encoding; content-free pointer | 4 / 7 / 7 = 18 | 3.10M / 10.76M | **Drop.** Its answer-only loop forecasts in_dist −3.5. Its pointer moves into B. |
| 6 | StreamPonder | An LSTM reads twice, ponders and halts; GRU talker | 3 / 5 / 6.5 = 14.5 | 3.14M / 10.56M | **Drop.** It forecasts a loss on pooled-5, and its halting idea already failed in this repo. |

## 2. Designs to test now

A and B use the same reader, so comparing them compares only the reasoners.

**Shared reader** (nothing pretrained, no attention):
- Input: x = E_char[108,d] + E_pos[208,d] + E_place[16,d].
- Place is the character's index from the right end of its `word_spans` token:
  - units digit 0, tens 1, and so on;
  - letters by position from the end of the word;
  - space and pad 15; values clamped at 14.
  It is cached per prompt and padded to prompt_ids.shape[1], because donor_eval pads.
- Two residual blocks of x + Conv1d_k5(GELU(LN x)), masked, then a LayerNorm, give X.
- The receptive field is ±4 characters, so all cross-word work has to happen later in the model.

### A. Register Loop (Abacus Loop + TRM-Text)

- **Reasoner:**
  - The state S [B,16,d] has 9 register slots (slot j holds answer character j from the right) and 7 scratch slots.
  - Slot codes P: the register codes are tied to E_place[0..8], and the scratch codes are an nn.Embedding. S0 = P.
  - Each of R = 6 rounds computes H = S + P, then applies 3 XBlocks shared across rounds, then sets S = LN(H). Each XBlock has self-attention over the slots, cross-attention to X (K/V cached once) and an MLP at 2.25x.
  - No round embedding, no halting, full backprop through all rounds. n_loops = 6.
- **Talker:** for each register slot, logits_j = LN(S_R[:,j])·E_charᵀ + b. Take the argmax, cut at EOS and reverse. talk() ignores the batch.
- **Sizes** [suggested; confirm with n_params() to within ±3%]:
  - S: d=256, about 3.22M, about 0.95x plain_tf-S FLOPs.
  - M: d=384 with 5 XBlocks, about 10.86M, about 1.0x FLOPs.
- **Loss:** the mean over rounds of the float32 cross-entropy on S_r.
  - Step values come from the regex `(?:=|->)\s*(-?\d+)\s*$`, with the answer appended if it is not already last.
  - When a row has 2 or more values, target_r = vals[min(r,k)−1]. Otherwise the answer is the target every round.
  - **Arm A0** (one change): the answer is the target every round. This tests TRM's claim that recursion alone helps.
- **Lesions:**
  - Harness: loops {0,1,2,12}, shuffle, zero, donor.
  - In-job, on the big build:
    - Round-1 register interchange with a same-family donor. It is scored against the counterfactual: the row's own operations 2..k applied to the donor's v1. About 660 rows can be scored.
    - A staircase: exact match against v_r at each round.
    - Prompt-blind after round 1.

### B. Ledger-lite (Ledger with the judges' fixes)

- **Workspace** [B,27,d], with values stored as int64:
  - 16 prompt-number slots. Each is the span-mean of X, plus an ordinal code, plus an exact value code (9 least-significant-first digit one-hots, sign, log magnitude).
  - Constants 1, 2, 10 and 100.
  - 7 result slots.
- **Controller** Z [B,17,d]: 8 control tokens and 9 register tokens tied to E_place.
  - 8 iterations of 2 blocks shared across iterations. Each block has cross-attention to [workspace; X], self-attention and an MLP at about 4.5x.
  - At t = 1..7, an op head chooses from {NOOP, ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP} and two pointers choose the operands.
  - A parameter-free int64 executor writes the result slot. DIV is allowed only when exact.
- **Talker** (linear or parameter-free; a mode head picks the path):
  - NUM prints the value the reasoner pointed to.
  - WORD copies word k of the current row. Its keys are content-free: Lin(sin(word index)) + E[length].
  - GEN is a per-slot linear readout of the register tokens, tied to E_char. It replaces the 1-layer decoder.
- **Sizes** [suggested]:
  - S: about 3.2M, at about 1.1x FLOPs.
  - M: d=384 with 3 blocks, MLP width tuned to within ±3% of 10.78M.
- **Loss:** programs are parsed from `steps` with no search and teacher-forced. The prototype re-executes 2,033 of 2,033 gold programs [shown]. Loss terms:
  - op cross-entropy, with NOOP at weight 0.1 on rows without a program;
  - operand NLL that ignores operand order;
  - mode cross-entropy;
  - answer-pointer and word-pointer NLLs;
  - register cross-entropy on GEN rows.
  Log free-run accuracy next to teacher-forced accuracy.
- **Lesions:**
  - Harness: loops {0,1,2,16}, shuffle, zero, donor.
  - Custom `noexec` makes every result invalid. Custom `opswap` swaps ADD and SUB at inference.
  - Neither name has a colon, so parse_lesion will not break on them.

**Both designs:**
- **Optimiser:** the harness AdamW (0.9, 0.95) with weight decay 0.1 on matrices. Store all codes as nn.Embedding so they are not decayed. lr 1e-3 (S) or 7e-4 (M), warmup 300, cosine to 10%, gradient clip 1, bf16 with pointers in fp32.
- **Schedule:** batch 256, 24k updates, shuffled, `--final-eval --minutes 40`. A run must end with status ok. One lr retry (5e-4) is allowed, but only if every arm gets it.
- **Unit tests:**
  - The state is bit-identical when answer and steps are removed from the rows.
  - B's pointer gives the same result when the characters are relabelled by a bijection.
  - The executor reproduces the gold programs.
- **Build:** about 250 lines for A and 450 for B, starting from the scratchpad prototypes.

### Baseline arms (each is one change from plain_tf-S)

- **plain_tf-S:** d256, 4 layers, 3.24M. It matches both parameters and compute.
- **plain_tf-L2×2:** 2 layers looped twice, 1.67M, same FLOPs. This is the looped arm at matched compute.
- **plain_tf_steps-S:**
  - Target: '; '.join(steps) + ' # ' + answer on the 11 arithmetic families, and the answer alone otherwise. Targets are capped at 64 characters; rows over the cap use the answer only.
  - It is a subclass with its own ids and a 288-position table, so data.MAX_ANS stays unchanged. It is scored on the text after the last '#'.
  - It is also scored as **C1′**: a calculator fills in each 'a op b =' while decoding, with no retraining.
  - It gets at least as much information as A or B, so it is the cautious same-rows bar.

## 3. Test plan

**Stage 0:**
- Build `--dev-per-cell 200` on the box and assert only the train.jsonl hash.
- Run a 400-update speed probe with 3 runs sharing the GPU. Any arm projected to take over 25 minutes runs 2-way instead.
- Measure FLOPs.

**Screen:**
- Seeds 100 and 101, shared by all six arms, so initialisation and data order are paired.
- 12 runs in 4 windows. Each seed gets one window of {A, plain_tf, plain_tf_steps} and one of {B, A0, L2×2}.
- Inside the job: final eval, lesions, donor, the diagnostics, and `chain_panel.py`, which scores the 5 chain families × 200 big-build in_dist rows (1,000 rows).

**Confirm:**
- Fresh seeds 200-205: the screen winner against plain_tf-S and plain_tf_steps-S. 18 runs in 6 windows.
- Open LMs through hf_baseline, with --revision pinned:
  - **EleutherAI/pythia-31m** (30.5M total, 4.7M non-embedding), fine-tuned on seeds 200-202 with the same rows, order, batch and 24k updates. lr is picked from {1e-4, 3e-4, 1e-3} by 6k-update runs. Picking on dev can only flatter the baseline.
  - **EleutherAI/pythia-14m** as a floor, seed 200.
  - 8-shot with no fine-tuning: **HuggingFaceTB/SmolLM2-135M** and **EleutherAI/pythia-31m**.
- L2×2 joins the confirm stage only if it came within 2 pooled-5 points of the winner.

**Metrics:**
- **Primary: pooled-5**, the micro exact match over in_dist, answer, frame, vocab and variant (6,040 rows).
- **Also reported separately:** chain-5 (big build, 1,000 rows), multi-step in_dist (12 families, 480 rows) and variant.
- **Statistic:** the per-seed paired difference d_s = design − baseline at the same seed. Report:
  - the mean d̄;
  - the 95% CI, d̄ ± 2.571·sd/√6;
  - how many seeds are positive;
  - a paired McNemar test on chain-5.

**Placeholders for the noise job:** σ_P, σ_C and σ_V are the standard deviations of a one-seed paired difference on pooled-5, chain-5 and variant. The lead fills them in from the noise job. Until then the defaults are 1.4, 3.0 and 1.6, which are √2 × the 4-seed standard deviations.

**Screen GO** (2-seed means; all are required):
- **G1:** pooled-5 d̄ vs plain_tf ≥ max(+1.0, 0.7σ_P). A true +3 effect passes this about 98% of the time.
- **G2:** chain-5 d̄ vs plain_tf ≥ max(+8, 2σ_C), with both seeds positive.
- **G3:** in_dist d̄ ≥ −2.0.
- **G4:** pooled-5 d̄ vs plain_tf_steps ≥ −1.0. For B, also vs C1′.
- **G5:** the lesion marks below hold.

**Confirm PASS:**
- **PASS-1 (beats a same-size transformer):**
  - pooled-5 d̄ vs plain_tf ≥ +2.0, CI above 0, and at least 5 of 6 seeds positive;
  - chain-5 d̄ ≥ +8, CI above 0, McNemar p < 0.01;
  - in_dist d̄ ≥ −1.0.
- **PASS-2 (Ben's criterion):** PASS-1, plus:
  - pooled-5 d̄ vs plain_tf_steps ≥ +1.0, CI above 0;
  - pooled-5 at least 2 points above the fine-tuned pythia-31m, paired on seeds 200-202.
- **Secondary:** variant d̄ vs plain_tf ≥ +2.0, CI above 0.
- **FAIL:** pooled-5 d̄ < +1.0, or in_dist d̄ < −2.0.
- Anything between FAIL and PASS is inconclusive. Make no claim and spend nothing more on it.

**Lesion marks (must hold in every seed):**
- **Wiring checks only** (these hold by construction):
  - shuffle_state in_dist ≤ 10;
  - zero_state ≤ 5;
  - donor swap drops in_dist by at least 20, with donor_match ≥ 50% on number and string families;
  - loops:0 ≤ 5;
  - loops:2n within 3 of intact.
- **Real evidence for A:**
  - interchange cf_match ≥ 40% and own-answer match ≤ 30%;
  - prompt-blind after round 1 puts chain-5 ≤ 10;
  - loops:1 puts chain-5 ≤ 15 while one-step families stay within 5. This only counts in A0, because A's step targets force it;
  - A − A0 ≥ +8 on chain-5.
- **Real evidence for B:**
  - loops:1 puts chain-5 ≤ 5;
  - loops:2 cuts chain-5 by at least 40 while one-op families stay within 5;
  - noexec puts program families ≤ 10;
  - opswap: at least 90% of outputs equal the value of the swapped program;
  - also report loops:2 vs loops:8 on the 19 families without programs.

**Results that would prove each design wrong:**
- **A**, any one of:
  - chain-5 d̄ < +3;
  - A − A0 < +3. Then if A0 − plain_tf is also < +3, answer-only recursion is ruled out too;
  - cf_match < 15%. The loop is then recomputing from the prompt, which is the sandwich's failure;
  - in_dist d̄ < −4.
- **B**, any one of:
  - chain-5 d̄ < +10;
  - pooled-5 d̄ ≤ 0;
  - C1′ within 3 points of B on both chain-5 and pooled-5. The credit then belongs to the calculator plus the steps, not to B's structure.
- If B passes overall and only its non-program families lose more than 5 points, fix the GEN path before confirming.

## 4. Cost

The box costs $0.45/h. A window is 3 runs sharing the GPU, about 30 minutes including the in-job eval.

| Stage | Box-minutes | $ |
|---|---|---|
| Stage 0: setup, big dev build, probes | 25 | 0.19 |
| Screen: 12 runs | 120-150 | 0.90-1.13 |
| Confirm one design: 18 runs | 180-210 | 1.35-1.58 |
| Open LMs: lr pick, 4 fine-tunes, 2 few-shot runs | 55-75 | 0.41-0.56 |
| **Total** | **380-460** | **2.85-3.45** |

- If the total goes over $3, drop the pythia-14m run first, then shrink the lr grid to 1e-4 and 3e-4.
- If both designs pass, the second one adds about $0.45 using the same baselines, and needs Ben's OK.
- The 10.8M check (2 seeds, about $0.35) runs only if money remains.

## 5. If nothing beats plain_tf

1. State it plainly: a 3.2M character transformer trained for 20 minutes is the bar, and it ties the 1.2B sandwich [shown].
2. Add one ingredient at a time to plain_tf, 2 seeds each, with the same marks:
   - place codes;
   - a content-free copy pointer;
   - plain_tf_steps;
   - C1′.

   Whichever one raises pooled-5 is the ingredient the next custom design should be built around. If the pointer wins, the Typed Word-Slot Workspace goes next.
3. If plain_tf_steps wins and A and B do not, explicit intermediate values are what helps. The next design should write them into an exact scratch area, as B does, rather than into a latent state.
4. Option (c), a small pretrained reader, is tested only after the from-scratch screen, as one change on whichever design came closest:
   - Keep the loop, register and talker. Feed the reader frozen pythia-14m states, copied from each token to its characters.
   - Its 14.1M parameters count toward the size, so the bars become plain_tf-M, pythia-31m and pythia-70m.
   - Use 2 seeds and the same marks.
5. None of the six designs improves the held-out families; all forecast 0-5%. Learning new kinds of task from a few examples needs task diversity or episodic training, which is a separate track.

## 6. For Ben

Right now the big borrowed language model does the thinking. We'll test two small models built from scratch, about 3 million numbers each, where the thinking part has to do the work. The reader sees only a few letters at a time, and the answerer can only read the thinker's notes.
- **Model A** works one step per round on an internal "abacus".
- **Model B** writes a tiny program ("add these, then multiply"), and an exact calculator runs it.

Each must beat an ordinary transformer of the same size, including one trained to write out its steps. The winning margins were fixed in advance and must hold across six repeat runs. We'll also scramble each model's notes mid-problem to prove the thinker really carries the answer. The total cost is about $3. Neither design helps with brand-new kinds of question yet.

The working draft is at /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/synthesis-draft.md.