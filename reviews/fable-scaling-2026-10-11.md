# Why does my looped reasoning model gain so little from size, and what one change should I test next?

You are an expert in neural architectures, scaling behaviour and small-model training. You have **no access** to my code,
files or machine, so everything you need is below. Do not ask me to run anything before you answer. Reason from what is
here; if a fact you need is missing, say exactly which one and how it would change your answer. Mark every claim as
**shown** (by the data below), **suggested**, or **untested**. One or two seeds is a screen, not a reliability estimate.

This question is only about the "B2" skills model and its size ladder described here. Please don't mix in ideas from
other projects of mine (small card-retrieval experiments, a village simulation); they are separate.

I am a high-school senior building this with AI help. Please keep the whole answer under about 1,800 words and end with a
plain-language summary I can follow.

## 1. The goal, and today's problem

The finished model will read its input through a frozen pretrained text embedder (EmbeddingGemma 2, 271M parameters) and
think with a trained, looped "thinker" that should be the driving intelligence; the shipped thinker is planned at about
100M trained parameters. I want size to clearly make it better. Two bars:

1. (fixed before the runs) From 3M to 10M trained parameters, my model must gain **more** than a plain transformer of the
   same size gains on the same data (6 seeds; a 2-seed screen first).
2. (new, from me today) The gain itself must be **big**. My model's first 10M result gained +1.64 points over 3M on the
   same seed. That is not the scaling I want.

Constraints: one home GPU (RTX 5070 Ti, 16 GB), busy with this test until about Monday midday. Measured run times on it:
my model at 3M about 6.5 h, at 10M about 40 h (6.24 s per update; the GPU is only about 23% busy because the 10M runs as 16
small micro-batches of a 12-round loop); the plain model is several times faster. Big money goes only into one large run
that has already been shown to work, so every test before it must fit on this GPU.

## 2. The data and the test (identical for every model and both sizes)

- **Training pool:** 1,418,702 rows, about 60M word pieces. 38% my own question rows (501,456 synthetic skill rows from 34
  skill families, 255,495 English passage questions, 54,712 tutor-written question rows), 62% fill-in-the-blank rows cut
  from web text (FineWeb-Edu: a passage with one word blanked, the target is the word). 24,000 updates of 256 rows
  (about 4.3 passes; 260M pieces seen at both sizes). Same rows, same order at 3M and 10M.
- **Skill rows** are short synthetic word problems (arithmetic, multi-step stories, tables, unit distances, variables,
  comparisons, few-shot rules, sequences, ordering, ...). Every row has the answer and its worked steps
  (e.g. `12 + 7 = 19; 19 * 3 = 57`). Answers are short (numbers or words).
- **Score = "pooled-5":** exact match over five held-out dev files (6,040 rows), built like training rows with exactly one
  shift each: `in_dist` (1,360 rows, no shift), `answer` (1,200, numeric answers never seen in training), `frame` (1,360,
  unseen sentence pieces, openers and closers), `vocab` (800, unseen names, nouns, places, made-up words), `variant` (1,320,
  unseen structural variants of each skill and one unseen layout). A sixth file, `family` (160 rows, unseen skill
  families), is reported only; every model scores 2-5% there. Web text is not scored.
- **Noise (measured, 4 seeds of a plain model):** pooled-5 seed-to-seed sd about 1.0; sd of a one-seed paired
  difference about 1.4.

## 3. The models

**B2 (mine; model name "ledger"):**
- **Reader:** each prompt character gets an embedding + position + a "place" code (digit position inside a number), then
  2 residual convolution layers (kernel 5). With the Gemma front ("EGE"), each character's input also gets a trained
  linear projection of the frozen EmbeddingGemma 2 state of the word piece that holds it (zero-initialised).
- **Workspace:** the numbers in the prompt are copied into exact integer slots (up to 91), plus constants and result slots.
- **Controller (the "thinker"):** 8 control tokens + 36 register tokens, updated by `blocks` transformer blocks (each:
  cross-attention to [workspace; reader output], self-attention among the controller tokens, MLP). The same blocks are
  **looped 12 times** (shared weights). On most rounds a control token picks an operation and two operand slots, and an
  **exact, parameter-free integer calculator** writes the result into the next result slot. Ops: add, subtract,
  multiply, divide, mod, min, max, compare. The program is trained by teacher forcing from the worked steps; rows whose
  steps don't parse into these ops have no program target.
- **Talker:** after the last round, a head picks the answer **mode**: NUM (print the value of the slot an answer pointer
  picks), WORD (copy word k of the prompt) or GEN (each register token emits one character in parallel through a linear
  readout tied to the character table, mixed with a pointer-copy distribution over prompt characters; **not
  autoregressive**). Web fill-in rows are answered by WORD or GEN.
- Loss = program steps + mode + answer pointer + word pointer + GEN characters.

**PT (plain step model):** a decoder-only causal character transformer, width 256, with the same Gemma front added to
each prompt character's input. It reads `[BOS] prompt [SEP]` and writes the worked steps, then ` # `, then the answer,
autoregressively. No calculator.

**How each grows from 3M to 10M (width 256 fixed for both):** B2 controller blocks 2 -> 8 (reader stays 2 conv layers,
12 rounds); 3,544,913 -> about 10.0M trained. PT 4 -> about 13 layers; 3,495,936 -> about 10M. Same learning rate (1e-3,
AdamW with weight decay 0.1, 300 linear warmup steps, then cosine to 10% of base, bf16), same data, same 24,000 updates. Gemma's 271M frozen parameters are the same in
every arm.

## 4. Results

### 4a. Older ladder (no Gemma front; B2 had a settings bug: 9 register tokens instead of 36 and GEN targets cut to 8 characters)

Mean 10M minus 3M, pooled-5: **B2 +0.49** (6 seeds, 95% CI -0.74 to +1.72), **PT +3.77** (5 seeds), a plain
next-character language-model recipe **+15.77** (5 seeds, but it starts 26 points lower). B2's training loss barely moved
(1.231 -> 1.209; GEN part 0.828 -> 0.815); PT's did (0.365 -> 0.331). Per family (5-seed means, %), B2 was flat while PT
grew on: fewshot_number_rule (B2 19.1 -> 18.9, PT 31.8 -> 44.2), seq_next (36.2 -> 37.8; 41.5 -> 51.1), order_chain
(43.7 -> 42.6; 51.1 -> 57.3), rule_apply (60.9 -> 62.8; 71.2 -> 74.8), backward_solve (81.2 -> 81.4; 37.2 -> 63.6).
A 2-seed shape probe at 10M: a deeper reader (23 conv layers) was flat; wider (384, 3 blocks, lr x 256/384) gained +1.57 and
+0.46.

### 4b. This test (bug fixed, Gemma front on both models)

| seed | B2 3M | B2 10M | PT 3M | PT 10M |
|---|---|---|---|---|
| 400 | 73.01 | **74.65** (+1.64) | 67.12 | pending (done about 11:30 PM tonight) |
| 401 | 73.68 | training (79%) | 68.01 | not yet run |

- Per dev file at 3M (%), in_dist / answer / frame / vocab / variant / family:
  B2 s400 86.0 / 71.9 / 86.6 / 89.4 / 36.7 / 2.5; s401 86.5 / 71.2 / 86.4 / 91.2 / 38.9 / 1.9.
  PT s400 83.8 / 57.8 / 83.1 / 83.5 / 32.1 / 3.1; s401 84.6 / 59.2 / 83.2 / 85.6 / 32.7 / 4.4.
- At 3M, 2,560 (s400) and 2,480 (s401) of the 6,040 pooled-5 rows are in families B2 already answers 40/40 in that file.
  Of B2's 1,630 (s400) and 1,590 (s401) misses, 836 and 807 are in the `variant` file.
- Training loss, B2: 1.139 at 3M -> 1.128 at 10M (s400). At 3M the GEN-character part is about 0.86 of it; the program
  part is about 0. PT at 3M: 0.366.
- 10M per file and per family: not read yet (pending).

**Per family at 3M, seed 400, all five dev files pooled (rows correct out of n), sorted by B2 minus PT:**

| family | n | B2 | PT | B2-PT | | family | n | B2 | PT | B2-PT |
|---|---|---|---|---|---|---|---|---|---|---|
| table_lookup | 200 | 55 | 107 | -52 | | percent_rate | 200 | 174 | 168 | +6 |
| rule_apply | 200 | 94 | 144 | -50 | | order_chain | 200 | 142 | 134 | +8 |
| fewshot_number_rule | 160 | 17 | 64 | -47 | | distance_units | 200 | 170 | 161 | +9 |
| passage_qa | 200 | 131 | 163 | -32 | | prop_eval | 120 | 105 | 94 | +11 |
| digits_parity | 160 | 72 | 93 | -21 | | chain_story2 | 200 | 179 | 166 | +13 |
| seq_next | 160 | 53 | 70 | -17 | | var_chain | 160 | 132 | 119 | +13 |
| compare_numbers | 160 | 120 | 135 | -15 | | copy_word | 200 | 170 | 151 | +19 |
| kin_chain | 200 | 166 | 177 | -11 | | div_exact | 200 | 177 | 158 | +19 |
| list_stats | 160 | 81 | 91 | -10 | | verify_claim | 120 | 84 | 62 | +22 |
| letter_ops | 200 | 152 | 154 | -2 | | odd_one_out | 160 | 134 | 111 | +23 |
| syllogism | 160 | 139 | 139 | 0 | | chain_ops | 200 | 200 | 171 | +29 |
| word_filter | 200 | 131 | 131 | 0 | | story_chain3 | 200 | 200 | 171 | +29 |
| state_update | 200 | 200 | 196 | +4 | | story_addsub | 200 | 184 | 152 | +32 |
| group_induct | 120 | 98 | 92 | +6 | | list_index | 200 | 125 | 91 | +34 |
| | | | | | | table_calc | 200 | 158 | 119 | +39 |
| | | | | | | object_track | 200 | 121 | 78 | +43 |
| | | | | | | arith_bare | 160 | 147 | 94 | +53 |
| | | | | | | seq_cycle | 160 | 91 | 36 | +55 |
| | | | | | | backward_solve | 160 | 129 | 58 | +71 |
| | | | | | | cipher_map | 120 | 79 | 4 | +75 |

859 of B2's 1,630 misses are in the nine families where the same-size plain model does better.

Examples: table_lookup "harbor: 58; engine: 4; ... Which word has the largest number?"; rule_apply "if a number is at
least 12, add 4; otherwise subtract 4. Apply it to 73."; fewshot_number_rule "(47, 16) -> 63; (26, 12) -> 38. Now
(47, 16) -> ?"; seq_next "Continue the pattern: 5, 6, 9, 14, ?"; passage_qa: short facts, then a question.

## 5. My current reading, and the test I planned tonight

- (shown) A large part of pooled-5 is already solved at 3M; about half of the misses are new structural variants.
- (suggested) My first guess to my user was "both sizes see the same practice rows, so the bigger thinker memorizes the
  same wordings better and can't learn new ones". The plain model gaining +3.77 on the same rows in the older ladder
  weakens that guess; the pending PT 10M number above tests it again.
- (suggested) The other reading: B2's answer path (fixed calculator ops plus a parallel one-shot GEN writer) cannot
  express the lookup / rule / pattern answers, so a bigger controller has nowhere to put its extra capacity. The loss
  barely moving with size fits this.
- **Planned test "DS"** (marks written, not run): B2 seed 400 at 3M and 10M trained on a 3.2x bigger pool (the 30M rung's
  pool: same generators and mix, more rows, nested), still 24,000 updates (each row seen about 1.4 times instead of 4.3).
  Pass: 10M minus 3M at least +3.3. Proved wrong: under +2.0. Cost about 46 GPU hours.

## 6. Already queued on the GPU after this test

In this order, each run about 3-7 h at 3M unless noted:
- **fc100**: fit and speed check of the planned ~100M thinker shapes (no score).
- **B3 group 2 at 3M ("G2f", seed 400).** This is the next design, and it changes exactly the answer path: every
  hand-made answer head of B2 (the NUM slot pointer, the WORD pointer and the parallel GEN head) is **deleted** and
  replaced by ONE small learned **autoregressive byte writer** (one decoder block, attention over the thinker's vectors
  only, no copy path). After each round the writer is asked "call?" and may write a tool call as text (e.g. `sub 12 5`);
  the calculator is an external tool whose text reply goes onto a tape that the reader (Gemma + the character window)
  reads on the next round. The answer is written by the same writer from the thinker's vectors alone, after the thinker
  has read the last reply. A learned stop head ends the loop. Numbers are bytes,
  no integer slots. Trained 4,023,302 at 3M; 9,824,546 at 10M; a 10M card exists (about 1-2 days, unmeasured).
- **B3 group 1 at 3M** (an intermediate step that keeps B2's answer heads but adds the tool tape, any-round calls and
  span copying); plain controls for B3's longer rows.
- Later: 10M and 30M rungs of B3; the shipped thinker is planned at ~100M (512 wide, 21-37 blocks, reading Gemma's own
  512 numbers directly).

## 7. What I'd like from you

1. Rank the explanations for "my model gains only about +1.6 from 3M to 10M" (add your own; tell me if any of mine is
   wrong): the answer path can't express the missing answers; pooled-5 is near a ceiling for B2 so size can't show; the
   practice rows are the limit; growing depth only (same width, same learning rate, 12 shared-weight rounds) is the wrong
   way to add size or trains badly; the frozen Gemma front already does most of the reading, so the thinker's size matters
   less; the parallel GEN writer can't use more capacity. For each, what above supports or weakens it.
2. The plain model's 10M score for seed 400 is pending. Give me a decision rule fixed now: what each outcome (PT gains
   +3 or more; PT gains about as little as B2; in between) means for the ranking and for what I test next.
3. Is test DS worth about 46 hours of my only GPU? If not, give the **one** test you would run first instead: one change,
   pass marks fixed in advance, the result that would prove your explanation wrong, and the GPU hours on a 16 GB RTX 5070
   Ti (ideally under a day; single-seed screens are fine if you use the noise numbers above).
4. Does B3 group 2 (section 6) address the cause you rank first? Would a 3M -> 10M step of B3 group 2 be a better first
   test than DS? What design change would most likely make size help a lot in the finished ~100M model, and which part
   of B2 or B3 group 2 stands in the way? Be concrete.
5. A plain-language summary for me (a high-school senior): what's going on, what to try next and why, in a few short
   paragraphs with no jargon.
