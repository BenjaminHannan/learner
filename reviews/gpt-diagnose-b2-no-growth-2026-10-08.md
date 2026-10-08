# Why doesn't a bigger version of my small reasoning model get better? (no code or file access needed)

You are an expert in neural architectures, scaling behaviour and small-model training. You have **no access** to my code,
files or machine, so everything you need is pasted below. Do not ask me to run anything before you answer. Reason from what
is here, and if a fact you need is missing, say exactly what it is and how it would change your answer. Mark every claim as
**shown by the data below**, **suggested**, or **untested**. Two to six seeds is a screen, not a reliability estimate.

This question is only about the "B2" skills model described here. Please don't mix in ideas from other projects of mine
(card-retrieval experiments, a village simulation); they are separate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

## 1. What I'm trying to show

That my own architecture ("B2") gets clearly better as it gets bigger (3M -> 10M -> 30M trained parameters), and stays
ahead of plain transformers of the same size trained on the same data. The marks were fixed before any run: B2 must gain
at least +3.0 points per size step, and its lead over the plain step model must not shrink by more than 1.0.

**Updated goal (after these results):** my model must gain **more** from each size step than a plain transformer of the same
size gains on the same data. The finished model will read its input through a frozen pretrained text embedder
(EmbeddingGemma 2, 271M parameters, about 768 numbers per word piece); help from that reader is fine, but the part I train
(the looped "thinker" below) should learn more and drive the answers. The 30M step of today's B2 is on hold.

**My next planned test (fixed before it is built):** the same 3M -> 10M step, with both my model and the plain step model
reading through the same frozen EmbeddingGemma 2 front (each prompt character's input gets a learned projection of the
Gemma state of its word piece, zero-initialised). Pass: mean over 6 seeds of (my 10M-minus-3M gain) minus (the plain
model's gain) above 0 with its 95% CI above 0, and at least half of my model's gain must remain when measured as
(full model) minus (thinker switched off). Two seeds first: go on if the gain difference is at least +1.0 on both, stop
if it is 0 or less on both. A version of B2 with this front ("EGE") scored +2.67 over B2 at 3M on an older data set
(6 seeds), so it is our best model today.

## 2. The data and the test

- **Training pool** (same rows, same order, for every model and both sizes): about 60M "word pieces", 38% my own question
  rows and 62% fill-in-the-blank rows cut from web text (FineWeb-Edu). 24,000 updates of 256 rows each (about 4.3 passes).
- **Own question rows:** short synthetic word problems from 38 skill families (arithmetic, multi-step stories, tables,
  unit distances, variables, comparisons, few-shot rules, etc.). Every row has the answer and its worked steps
  (e.g. `12 + 7 = 19; 19 * 3 = 57`). Answers are short (numbers or words).
- **Web fill-in rows:** a web passage with one word blanked out; the target is the missing word.
- **Score = "pooled-5":** exact-match accuracy over five held-out dev files (6,040 rows) built like training rows but with
  exactly one shift each: `in_dist` (no shift), `answer` (numeric answers never seen in training), `frame` (unseen sentence
  pieces, openers and closers), `vocab` (unseen names, nouns, places, made-up words), `variant` (unseen structural variants
  of each skill and one unseen layout). The web text is not scored.

## 3. The models (all read the prompt one character at a time; no borrowed tokenizer or pretrained weights)

**B2** (my architecture):
- **Reader:** character embedding + position + a "place" code (digit position inside a number), then **2 residual
  convolution layers, kernel 5** (pre-LayerNorm, GELU). So each character's reader output sees only about 9 characters
  around it.
- **Workspace:** the numbers found in the prompt are copied into exact integer slots (up to 91), plus constants and result slots.
- **Controller:** a set of tokens (8 control tokens + 36 register tokens) updated by `blocks` transformer blocks (each:
  cross-attention to [workspace; reader output], self-attention among the controller tokens, MLP). The same blocks are
  **looped 12 times**. On most loops a control token picks an operation and two operand slots, and an **exact,
  parameter-free integer calculator** writes the result into the next result slot (a program, trained by teacher forcing
  from the worked steps).
- **Talker:** after the last loop, a head picks the answer **mode**: NUM (print the value of the slot an answer pointer
  picks), WORD (copy word k of the prompt), or GEN (generate characters: each of the 36 register tokens emits one character
  in parallel through a linear readout tied to the character table, mixed with a pointer-copy distribution over prompt
  characters; **not autoregressive**). Web fill-in rows are answered by WORD or GEN.
- Training loss = program steps + mode + answer pointer + word pointer + GEN characters.

**PT** (plain step model): a decoder-only causal character transformer, d = 256, reads `[BOS] prompt [SEP]` and writes the
worked steps, then ` # `, then the answer, autoregressively. No calculator. Fill-in rows are prompt -> missing word.

**LLM** (plain language-model recipe): same network as PT, but web rows are read as raw text with a next-character loss
on every character (the blank filled back in); question rows as PT. No calculator.

**How each grew from 3M to 10M** (width fixed at 256 for all):
- B2: controller blocks 2 -> 8 (reader stays 2 conv layers, 12 loops, 36 registers). 3,346,513 -> 10,298,137 params.
- PT and LLM: 4 -> 13 transformer layers. About 3.30M -> 10.41M params.
- Same learning rate (1e-3, AdamW, bf16, batch 256), same data, same 24,000 updates.

## 4. Results (pooled-5 %, one rented RTX 5090 per seed; 3M and 10M of a seed ran on different boxes of the same GPU type)

| seed | B2 3M | B2 10M | gain | PT 3M | PT 10M | gain | LLM 3M | LLM 10M | gain |
|---|---|---|---|---|---|---|---|---|---|
| 400 | 71.59 | 71.62 | +0.03 | 66.66 | 69.74 | +3.08 | 46.42 | 61.46 | +15.03 |
| 401 | 73.21 | 73.49 | +0.28 | 66.23 | 70.48 | +4.25 | 47.91 | 63.11 | +15.20 |
| 402 | 74.14 | 73.03 | -1.11 | 66.42 | 69.88 | +3.46 | 48.69 | 63.05 | +14.35 |
| 403 | 71.51 | 72.02 | +0.51 | 65.51 | 69.88 | +4.37 | 48.00 | 61.77 | +13.77 |
| 404 | 72.17 | 72.90 | +0.73 | 66.46 | (cut by a cost cap) | - | 46.72 | (cut by a cost cap) | - |
| 405 | 71.42 | 73.91 | +2.48 | 66.14 | 69.85 | +3.71 | 41.97 | 62.45 | +20.48 |

Mean gain: B2 +0.49 over 6 seeds (95% CI -0.74 to +1.72); PT +3.77 and LLM +15.77 over 5 seeds (seed 404's box hit its
time cap before its PT and LLM 10M arms ran). B2's lead over PT: 6.1 -> 2.9. Per-dev-file and per-family tables below
use the 5 seeds with all arms.

**Per dev file, mean 10M minus 3M over the 5 seeds:**

| model | in_dist | answer | frame | vocab | variant |
|---|---|---|---|---|---|
| B2 (3M level: 87.4 / 72.4 / 86.2 / 85.1 / 34.9) | +0.25 | +0.07 | +0.57 | +0.93 | +0.55 |
| PT (3M level: 82.1 / 61.1 / 78.9 / 82.7 / 31.3) | +4.01 | +5.47 | +5.66 | +2.38 | +0.89 |
| LLM (3M level: 58.6 / 35.3 / 54.5 / 65.0 / 25.2) | +17.01 | +18.65 | +20.22 | +16.30 | +6.95 |

**Per skill family** (exact %, all five dev files pooled, mean over the 5 seeds; about 120-200 rows per family per seed;
selected families, the full list is 34):

| family | B2 3M | B2 10M | PT 3M | PT 10M | what it asks |
|---|---|---|---|---|---|
| chain_ops | 100.0 | 99.9 | 94.2 | 97.9 | 2-3 step arithmetic story |
| story_chain3 | 99.9 | 99.9 | 90.8 | 95.6 | 3-step story arithmetic |
| state_update | 98.9 | 99.0 | 98.5 | 99.9 | track a value through updates |
| percent_rate | 96.5 | 97.6 | 82.9 | 84.3 | "Rosa has 4 times as many pebbles as Kai (5)." -> 20 |
| cipher_map | 97.5 | 99.2 | 51.3 | 41.3 | "Code: e=4, h=2, a=5, b=1. Write beb as numbers." -> 1 4 1 |
| arith_bare | 85.2 | 89.4 | 66.4 | 74.8 | "Subtract 20 from 22." (some held-out formats) |
| backward_solve | 81.2 | 81.4 | 37.2 | 63.6 | "Two numbers add up to 89 and differ by 5. The smaller?" -> 42 |
| fewshot_number_rule | 19.1 | 18.9 | 31.8 | 44.2 | "(47, 16) -> 63; (26, 12) -> 38. Now (47, 16) -> ?" (infer the rule) |
| seq_next | 36.2 | 37.8 | 41.5 | 51.1 | "Continue the pattern: 5, 6, 9, 14, ?" -> 21 |
| order_chain | 43.7 | 42.6 | 51.1 | 57.3 | "Cy is older than Wren... Who is the oldest?" -> a name |
| rule_apply | 60.9 | 62.8 | 71.2 | 74.8 | "if a number is at least 12, add 4; otherwise subtract 4. Apply it to 73." |
| passage_qa | 78.1 | 77.5 | 84.8 | 85.8 | short facts, then a question (often a sum) |
| table_lookup | 27.3 | 27.4 | 22.2 | 26.3 | "harbor: 58; engine: 4; ... Which word has the largest number?" |
| list_index | 42.0 | 43.7 | 38.9 | 41.3 | "Items: bridge, falcon, kettle... Which word comes right before kettle?" |
| digits_parity | 50.0 | 50.1 | 50.0 | 51.4 | "What is the tens digit of 764?" and similar (flat for all four) |

So B2 is at or near 100% on the families its calculator program covers, and flat on the pattern / rule families, where
the plain model does gain with size (shown). B2's calculator ops are add, subtract, multiply, divide, mod, min, max and compare over number slots, and its programs are learned only from rows whose worked steps parse into those ops;
anything else has to be produced by WORD copy or the parallel GEN head.

**Shape probe (2 seeds, B2 only, 10M size; readout fixed before it ran).** Each arm is one change against the 10M B2
above. **R:** blocks stay 2, reader grows from 2 to 23 conv layers (sees about 93 characters instead of 9; 10.24M
params). **W:** width 256 -> 384, blocks 3, reader 2 conv layers, learning rate scaled by 256/384 (9.89M params).
"Grows" = at least +3.0 over the same seed's 3M B2 on both seeds and at least +2.0 over the deep 10M B2; "flat" = under
+1.0 on both seeds; otherwise "unclear". "Leak" = score with the loop switched off (0 rounds).

| arm | seed | pooled-5 | vs 3M B2 | vs deep 10M B2 | train loss (GEN part) | leak |
|---|---|---|---|---|---|---|
| 3M B2 | 400 / 401 | 71.59 / 73.21 | - | - | 1.228 / 1.229 (0.88 / 0.80) | 5.3 / 9.8 |
| deep 10M B2 | 400 / 401 | 71.62 / 73.49 | +0.03 / +0.28 | - | 1.216 / 1.206 (0.87 / 0.78) | 0.6 / 0.1 |
| R | 400 / 401 | 72.32 / 71.75 | +0.73 / -1.46 | +0.70 / -1.74 | 1.154 / 1.156 (0.88 / 0.78) | 0.0 / 0.0 |
| W | 400 / 401 | 73.16 / 73.68 | +1.57 / +0.46 | +1.54 / +0.18 | 1.205 / 1.194 (0.87 / 0.76) | 10.9 / 12.4 |

So R is flat and W is "unclear" (slightly better than deep, far from +3). R broke the letter-code family (cipher_map
97.9 -> 72.5, 2-seed mean), which needs the reader's narrow local window. W's 2-seed family means vs 3M B2 rose a little
on the rule families (fewshot_number_rule 16.2 -> 20.6, seq_next 36.2 -> 40.0, order_chain 43.0 -> 47.5, rule_apply
61.2 -> 66.5; 160-200 rows per family per seed, so within noise), and its leak rose too.

## 5. What I'd like from you

1. List the plausible explanations for "B2 doesn't improve with size while the plain models do", and rank them. For each,
   say what in the data above supports or weakens it, labelled shown / suggested / untested. Candidates I've thought of
   (add your own, and tell me if any of these is wrong): the extra size went into a part that isn't B2's bottleneck (the
   2-layer, 9-character reader); B2 is near a ceiling for this test that size can't fix; the non-autoregressive GEN head
   can't use more capacity on web text; the 12-loop recurrence with 8 blocks needs a lower learning rate or more updates;
   the plain models only gain because they start lower; B2 is already saturated on the families its calculator covers,
   and its remaining errors are in pattern / rule families that its fixed program ops and parallel GEN head can't express,
   so no amount of controller size helps there (the per-family table points this way). Also tell me what it means that
   B2 is near 100% on a third of the families: can pooled-5 still show scaling for it? (I don't want to switch to a
   test just because B2 looks better on it.)
2. Say what the R and W probe results above do to each explanation (R flat, W slightly better than deep, neither close
   to +3), and whether a wider-and-deeper B2 at 30M is worth trying.
3. Is the planned Gemma-front test above the right next test for the updated goal? If not, propose the **one** next
   change you'd test instead (one change at a time), with pass marks fixed in advance and the result that would prove
   your explanation wrong. What would make a design gain **more** from size than a plain transformer, and which part of
   B2 would have to change for that? Keep it cheap: a 10M run costs me about $2-3 a seed (about double with the Gemma
   front, our estimate).
4. Tell me whether running the 30M size of the current B2 shape (about $42 for six seeds) could still tell me anything
   useful, given the +3.0-per-step mark already fails at the first step.
5. Plain-language summary for me (a high-school senior): what's going on, what to try next, and why, in a few short
   paragraphs with no jargon.
