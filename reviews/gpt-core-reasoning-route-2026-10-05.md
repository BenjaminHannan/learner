# How should a small "thinker" do the reasoning when a frozen 1.2B language model sits on both sides of it? (no code or file access needed)

You are an expert in neural architectures, neuro-symbolic models, tool use and compositional generalisation. You have **no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer rather than guessing. Mark every claim as **shown by the data below**, **suggested**, or **untested**. Most results are 1 seed (a screen); the ones marked "3 seeds" or "6 seeds" are more solid.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

Everything here is about one system: the real pipeline below (a frozen LM plus a small trained thinker on a synthetic skills curriculum). I also have small card experiments and a separate "village" world model; neither is described here, so keep them out of your claims.

## 1. The model

- **Reader side:** a frozen LFM2.5-1.2B-Instruct language model reads the question. Its final-layer hidden states (2,048 wide, one per token) go through a small trainable **reader**: LayerNorm -> Linear(2048, 32) -> GELU -> Linear(32, 256), plus sinusoidal position codes.
- **Thinker ("core"):** about 9M parameters (only ~1.6M actually live: its mixture-of-experts layer never trained), width 256, 2 pre-LN transformer blocks applied in a loop for 4 rounds (h <- LN(h + input + blocks(...))). Measured: the loop is a contraction (relative change of h per round 1.6% at round 2, 0.6% after), so it behaves like one pass.
- **Exit:** the thinker's per-token states are projected (256 -> 32 -> 2048) and average-pooled into **8 vectors** that are placed in front of the question in the frozen LM's input: `[8 vectors][question tokens][BOS][answer]`. The same frozen LM writes the answer (the "talker"). Only the reader, thinker and exit train. Loss = cross-entropy on the answer tokens.
- Parent checkpoint: 50k updates (batch 1, AdamW 1e-3) on a 200k-row, 34-kind synthetic skills curriculum.

## 2. The task and the screen

Eight "worst" kinds of short word problems, e.g.:
- chain_ops: "Gus has 10 pebbles. Then Gus gives away 5. Then Gus multiplies the amount by 5. How many?" (steps `10 - 5 = 5 ; 5 * 5 = 25`)
- state_update: "A jar holds 32 marbles. 4 are removed. 7 are added." (steps `-4 -> 28 ; +7 -> 35`); a two-jar variant ends with `a + b`
- var_chain: "q = 8. p = q * 4. n = p + 9. What is n?" (steps `p = 8 * 4 = 32 ; n = 32 + 9 = 41`)
- chain_story2: "Zoe has 10 boxes with 3 pencils in each. Then Zoe gives away 24 of the pencils."
- plus cipher_map (letter codes), fewshot_number_rule (infer a rule from examples), group_induct (yes/no group rules), seq_cycle (repeating letter patterns).

Screen: 2,000 fixed training rows x 3 passes = 6,000 updates at batch 1. **Fit** = exact match on 320 of the practised rows; **held-out** = 320 new rows of the same kinds. Goal ("mark"): fit >= 85%.

## 3. What happened (all shown, by experiment)

| arm (3 seeds unless noted) | fit | held-out |
|---|---|---|
| baseline (answer only) | 66.6% | 48.1% |
| baseline, 2x practice | 72.4% | 49.4% |
| talker writes worked steps, then ` # answer` | 78.3% | 69.8% |
| worked steps, with hand-written steps for the 4 label-only kinds ("SR2") | **86.1%** | **80.6%** |
| SR2, 6 new seeds (confirmation) | CF_FIT | CF_HELD |

**Lesions (who does the work?).** After training, I replace each question's 8 thinker vectors with (i) the average for its kind, (ii) another same-kind question's vectors, (iii) one global average. Points lost on fit / held-out:

| | kind-average | same-kind swap | global average |
|---|---|---|---|
| baseline (3 seeds) | -1 to -6 / ~0 | -3 to -7 / ~0 | -18 to -24 / -11 to -14 |
| worked steps (9 runs) | 0 to -5 / 0 to -3.4 | -1 to -8 / 0 to -5.6 | -28 to -43 / -25 to -42 |

So the thinker's vectors carry which **kind** of puzzle it is (and the talker needs that more once it writes steps), but almost nothing about the particular question. The share of the steps lift that needs question-specific thinker content: +0.09, -0.29, -0.15 (3 paired seeds).

**Probe.** Can you read which number a number-token is (held tokens, values seen in training; best of 1-NN and ridge)? LM features 98.5%; after the 32-wide reader **17.6%**; thinker input 15.7%; after round 1 8.6%; after round 4 8.9%. A randomly initialised reader keeps 29.8%. Row probe R2 for the first step's value: LM features 0.22, thinker output 0.085.

**Learning ladder (no LM in the loss).** Predict the first intermediate value (step1, a single number token, via a head tied to the LM's token embeddings) or the answer, on the 4 chain kinds, 2,000 rows x 3 passes, batch 1, AdamW 1e-3, no weight decay:

| learner | step1 fit / held-out | answer fit / held-out |
|---|---|---|
| trained thinker | 7/320 / 3.1% | 6/320 / 0.7% |
| fresh thinker | 11/320 / 3.1% | - |
| linear readout of LM features (no thinker) | 147/320 / 0.6% | 146/320 / 2.6% |
| generic 4-layer d=256 transformer on LM features | 26/320 / 3.1% | 20/320 / 2.6% |
| generic transformer, 17,000 distinct rows, one pass | 10/320 / 3.1% | - |
| fresh thinker, 17,000 distinct rows, one pass | LDD_CORE | - |

**Plan + calculator test (no LM in the loss).** Instead of computing, the thinker outputs a plan: 6 pointer slots over the question's tokens (start number, then up to 5 operands) and 5 op slots ({+, -, *, /, STOP}, read from the 8 position-pooled chunks of the thinker output). An exact integer calculator executes the plan. Executing the gold plan reproduces the answer on all 17,981 training rows. Held-out = 160 new chain rows.

| | held plan-exact | held ops right | held pointers right |
|---|---|---|---|
| trained thinker, 2k rows x 3 | 26.9% | 32.5% | 58.1% |
| fresh thinker, 2k rows x 3 | 60.6% | 61.3% | 91.3% |
| fresh thinker, 17k distinct rows (end; best 75.6%) | 69.4% | 71.9% | 86.9% |
| fresh thinker, op head also reads the token its operand pointer picks, 2k x 3 | PLO_PLAN | PLO_OPS | PLO_PTR |
| same, 17k rows | PLOD_PLAN | PLOD_OPS | PLOD_PTR |

For comparison, the talker writing steps (SR2) gets 84-88% of these four kinds' held-out rows right. An audit of its wrong chain answers: 67% misreads (a dropped step, a wrong operand, the wrong value carried into the last line), 0-10% arithmetic slips, the rest format breaks.

## 4. My goal and the question

I want the **thinker** (not the borrowed LM) to do the reasoning: skills and critical thinking first, learn from few examples, and eventually beat 1-2B models at whole size (the LM counts towards size). A separate effort is looking at replacing the 1.2B reader/talker with something smaller.

Questions:
1. Given the data, what is the most likely reason no small learner computes even one arithmetic step here, while the thinker can learn *where* the numbers are? Is it data, the batch-1 recipe, the number representation (one token per number 0-999, embeddings from the LM), or something else?
2. Is "the thinker plans, an exact tool computes, the LM speaks" a sound direction for my goal, or does it just move the reasoning into a hand-built tool? What would make it count as the thinker reasoning?
3. What should the thinker's interface to the numbers be (pointers to tokens, digit-level codes, a learned number embedding, a scratchpad the thinker writes and reads), and should the 32-wide reader go?
4. How should the thinker share the work with the talker, so that the lesions above would show the thinker mattering for each question?

For each proposal: **one change at a time**, with the pass mark written in advance (on the fit / held-out numbers above, or the plan test), and the result that would prove it wrong. Order them by expected value per GPU-hour on one RTX 5090.

## 5. Summary for me

Finish with a plain-language summary (a high-school senior should follow it): what you think is going on, what you would try first, and what result would change your mind.
