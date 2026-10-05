# Ledger: a looped slot-program reasoner with an exact executor

_A small char reader puts the prompt's numbers into a 27-slot workspace. One shared block, looped 8 times, writes up to 7 (op, slot, slot) steps; an exact integer executor runs each step and writes the result back into the workspace. The answer comes out one of three ways: a slot the reasoner points to, printed exactly; a prompt word the reasoner points to, copied; or text from a 1-layer talker that sees only the reasoner's 8 state vectors and the executor's results._

## reader

Shapes are written for the ~3M setting (S); the ~10M setting (L) is in brackets.

Input: prompt_ids [B,T<=208] and prompt_mask, from the harness as-is. No BOS, so char i sits at position i.

Embedding: x = tok[108,d] + pos[224,d] + place[11,d].
- place = the digit's distance from the right end of its digit run (0 = ones digit, up to 9; 10 = not a digit). This is an Abacus-style magnitude cue.
- It is computed with tensor ops: next_nondigit = flip(cummin(flip(where(is_digit, T, idx)))), and place = next_nondigit - idx - 1.

Encoder: n_read = 2 [3] pre-LN bidirectional transformer layers, d = 256 [400], 4 [5] heads, MLP 4x, key-padding mask, final LN. Output H [B,T,d].

Number tokenizer (hand-written, no parameters): digit runs give up to 16 prompt integers.
- Exact values come from scatter_add of digit*10^place, as int64 [B,16].
- Each number gets the mean of H over its span [B,16,d] and its order of appearance.

Workspace S [B,27,d], with vals [B,27] int64 and valid [B,27] bool:
- Slots 0-15 are prompt numbers: span-mean H + ordinal_emb + type_emb + Linear(93->d)(code(value)).
- code(v) = 9 least-significant-digit-first digit one-hots, sign, valid flag and log10 magnitude. It is exact up to 1e9.
- Slots 16-19 hold the constants 1, 2, 10 and 100.
- Slots 20-26 are empty result slots that the executor fills.

Word keys: data.word_spans gives up to 64 words. Kw [B,64,64] = Linear(span-mean H).

What the reader can do: tag each number and word with its context (for example "16 follows 'gives away'"), and locate words.

What it cannot do:
- It has no output path. Everything it computes reaches the answer only through the reasoner's attention, or as the keys of the reasoner's word pointer.
- It cannot compute multi-digit results exactly.

A deeper bidirectional reader could still solve the non-program families by itself. The loops lesions measure that, and keeping the reader shallow (2 layers) is deliberate.

## reasoner

State: Z [B,8,d], starting from a learned z0. There is one weight-shared block, run for n_loops = 8 iterations t = 0..7.

Each iteration:
1. Z = Z + step_emb[min(t,7)].
2. Z cross-attends to memory [S + src_slot ; H + src_char], with masks. The char K/V are computed once per forward because H never changes; only the slot K/V are recomputed.
3. Self-attention among the 8 Z tokens.
4. MLP (2x in S, 4x in L). All sublayers are pre-LN.

At t = 0 the reasoner only reads. At t = 1..7 it may write:
- z = LN(Z[:,0]).
- Op logits = Linear(d,9)(z) over {NOOP, ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP}.
- Two operand pointers: softmax over valid slots of (W_a z)·(W_k S)/8 and (W_b z)·(W_k S)/8, with d_k = 64. Pointers can target prompt numbers, constants or earlier results, which is how chained steps bind.
- The executor (no parameters, int64, about 15 lines) computes v = op(vals[a], vals[b]):
  - DIV is valid only when the division is exact; MOD and DIV by 0 are invalid.
  - CMP returns the sign of a-b (-1/0/1).
  - Any |v| >= 1e9 is invalid.
- Result slot 20+t-1 = Linear(93->d)(code(v)) + type_emb[result] + op_emb[op] + step_emb[t] + W_z z. Its vals and valid entries are set. NOOP writes an invalid, empty slot.

In training, the gold op and a gold operand are teacher-forced. All gold candidates for an operand have the same value, so which one is picked does not matter.

After t = 7, with z = LN(Z[:,0]):
- mode = Linear(d,3)(z), one of NUM / WORD / GEN.
- Answer-slot pointer over S: (W_ans z)·(W_k S).
- Word pointer over Kw: (W_w z)·Kw.

Halting: none. The loop always runs 8 iterations, and NOOP is the learned "do nothing" step. The longest supervised program is 6 ops (state_update/var_chain 5, compare_numbers 6); longer programs are dropped to answer-only.

Lesion behaviour: loops:K runs K iterations. The step embedding is clamped at 7 and writes happen only at t <= 7.

State handed to the talker: (Z [B,8,d], S [B,27,d], vals [B,27], valid [B,27], mode logits [B,3], answer-slot logits [B,27], word logits [B,64]). No dimension depends on T, so the donor swap lines up trivially.

Non-arithmetic families (no program supervision) use the same loop. They get 8 iterations of latent re-reading of H and S, with NOOP supervised at weight 0.1, and answer through WORD or GEN.

## talker

The talker has three paths, picked by the reasoner's mode:

1. **NUM:** output str(vals[argmax answer-slot]). This is a parameter-free exact renderer, can print negatives, and has no length cap. If the chosen slot is invalid, it falls back to GEN.
2. **WORD:** copy the k-th word span of the CURRENT prompt, with k = argmax of the reasoner's word logits. The current batch is used only as the copy source, as the harness contract allows.
3. **GEN:** a 1-layer causal char decoder over 9 positions (8 chars + EOS), greedy.
   - Each position: causal self-attention over previous output chars, then cross-attention whose memory is only [Z (8 vectors) ; result slots 20-26 (7 vectors, valid-masked)], then MLP (1x in S, 2x in L).
   - Logits come from the char table, which is tied with the reader's table. That shares parameters, not information.

Confirmed: the talker never sees prompt chars, H, the prompt-number slots or the constants. Its only route to the question is the reasoner's final state, plus the WORD copy at a reasoner-chosen index.

The prompt-number slots are deliberately left out of the GEN memory. Their exact value codes would otherwise let the talker compute answers such as seq_next on its own.

The talker can still:
- translate a CMP sign into yes/no, true/false or a name (shown as intended);
- in principle, do a little arithmetic over the result slots, but only on values the reasoner chose to compute.

## why_reasoner_must_reason

The bottleneck works differently for each answer type. Shares below are from my parse (shown): train is 37.3% NUM, 31.4% WORD, 31.3% GEN; in_dist is 42.2% NUM, 27.6% WORD, 30.2% GEN.

**NUM answers.** No neural net emits a digit. The output is the exact value of a slot the reasoner chose. That value is either a prompt number or the result of ops whose type, operands, order and binding to earlier results were all chosen by the reasoner. The executor cannot choose anything and never sees text. Under a donor swap, the output must become the donor's executed result.

**WORD answers.** The index of the word to copy comes only from Z.

**GEN answers.** The decoder's whole memory is 15 reasoner-produced vectors.

This is the opposite of the sandwich, where the talker re-read every prompt word (results-digest B2/B7). Here the talker has no prompt access at all.

What could still leak:
- (a) The reader may solve WORD/GEN families itself, and the loop then just carries the conclusion. This would show up as loops:1/2 about equal to loops:8 on those families. Mitigation: a 2-layer reader; report it, do not hide it.
- (b) The reader can pre-tag the op for each number. That is reading, which is acceptable; binding results across steps still has to happen in the loop.
- (c) The GEN talker can do small computations over result slots, but only on values the reasoner wrote.
- (d) Soft-vector leakage (2106.13314) is impossible on the NUM path, which is a hard integer, and possible inside Z for GEN.
- (e) Dataset shortcuts any model gets: syllogism's first word, object_track's last recipient, and 82% template overlap.
- (f) Teacher forcing writes gold values only in training; there is no inference leak.

Labels: (a)-(c) are untested; the NUM-path argument holds by construction.

## params

**S setting.** Counted on the CPU prototype (shown): 3,327,884 parameters, against plain_tf d256 L4 at 3,244,544 (+2.6%).
- Reader: 1,669,888 (embeddings 87.6k, 2 encoder layers 1.58M).
- Reasoner block + z0: 793,856.
- Slot encoders: 99,584.
- Heads (op, 4 pointer queries, slot/word keys, mode): 101,772.
- GEN talker: 662,784.

**L setting.** d=400, 5 heads, 3 reader layers, reasoner MLP 4x, talker MLP 2x: 10,794,796 parameters, against plain_tf d384 L6 at 10,775,040 (+0.2%).
- Reader: 5,918,400.
- Reasoner: 2,572,400.
- Slots: 213,200.
- Heads: 158,796.
- Talker: 1,932,000.

The reasoner holds about 24% of the parameters but about 35-40% of the compute, because it runs 8 times.

**Compute per training example relative to plain_tf at the same parameter count:**
- Analytic, with char K/V cached: about 0.8x. S is about 230M forward MACs against about 290M; L about 720M against about 920M (suggested).
- Measured on CPU (4 threads, batch 64, unoptimised prototype that recomputes char K/V every loop): fwd+bwd 0.79 s vs 0.76 s for S (1.04x) and 1.96 s vs 2.03 s for L (0.97x) (shown, CPU only).
- Inference: about 0.1-0.2x. It is one encoder pass plus 9 tiny talker steps, against plain_tf's decode with no KV cache; CPU generate for 64 rows took 0.47 s vs 2.4 s (shown).

**GPU wall time (untested).** The 8-iteration loop issues roughly 2,000 small kernels per update. I expect 1.2-1.8x plain_tf's wall time per update.

So the same-parameter plain_tf is also roughly the same-FLOPs arm, and plain_tf looped x2 is a 2x-compute arm.

## pretrained_parts

None: 0 pretrained parameters. Everything trains from random initialisation on the 200k rows. The two hand-written, parameter-free parts are the digit-run number tokenizer and the about-15-line int64 executor. The design rule is that these only tokenise and calculate; they never choose. A borrowed reader under 100M is not needed for this benchmark, and I do not recommend one here.

## training

**Supervision source.** The rows' `steps` field, already present in batch['rows'] (data.KEEP includes it), is parsed by a hand-written converter.
- Formats handled:
  - "a op b = c", "x = a op b = c" and "a+b=c" (spaces optional);
  - expressions with precedence and brackets, e.g. "(70 - 20) / 2" and "340 * 20 / 100";
  - state_update's "+3 -> 33";
  - "sum [..]", "smallest/largest of [..]" (chains of MIN/MAX);
  - "range of [..]" (MAX chain, MIN chain, SUB);
  - "compare x y" (MIN/MAX when the answer is a number, CMP otherwise);
  - arith_bare's missing-operand rows, emitted as the inverse op;
  - verify_claim, which gets an extra CMP against the claimed number;
  - negative intermediate literals.
- Each operand value is resolved to the set of slots that hold it.
- Coverage on all 200k train rows (shown):
  - 34.6% have a program (31.8% ending in NUM, 2.8% ending in a word or label);
  - 5.5% have a 0-op NUM pointer, where the answer equals a prompt number;
  - 60.0% are answer-only.
- On a 6,000-row random sample, the vectorised reader plus executor reproduced every gold intermediate value and the answer slot for 2,033 of 2,033 program rows (shown).
- No program search: a unique depth-1 search produced spurious programs (shown), e.g. list_stats second_largest as SUB(88,18)=70 and seq_next arith as ADD(28,35)=63, so it is off.

**Loss (per batch, mean over rows):**
- Program steps t = 1..7: CE(op_t) weighted 1 on program rows (NOOP after the program ends) and 0.1 on non-program rows (all NOOP).
- Operands, on op steps only: marginal NLL over the gold slot sets, -log sum_{j in gold} p(j). For ADD/MUL/MIN/MAX the term is order-agnostic: logaddexp of the (a,b) and (b,a) joint terms.
- Plus CE(mode), over all rows.
- Plus marginal NLL of the answer-slot pointer, on NUM rows.
- Plus marginal NLL of the word pointer, on WORD rows: every word equal to the answer, case-insensitive.
- Plus talker char CE over answer chars + EOS, on GEN rows only, teacher-forced.
- No deep supervision in v1. Optional later: answer heads after every loop past the program's end.

**Optimiser and budget.** Exactly the harness and calibration settings: AdamW (0.9, 0.95), weight decay 0.1 on matrices, lr 1e-3 (S) / 7e-4 (L), 300 warmup steps then cosine to 10%, gradient clip 1, bf16 autocast, batch 256, 24k updates, shuffled order, --final-eval.

**Changes needed.** None to the harness: loss() returns (scalar, aux), and state()/talk() give the donor and loops lesions for free. Register MODELS['ledger'].
- Keep pointer logits and masks in fp32 and values in int64.
- Cache each row's parsed targets and word ids by row id; the Python overhead matters at batch 256.
- The C1 control (plain_tf writing "steps # answer") needs MAX_ANS raised to 48, and scoring of the text after '#'.

## predictions

All numbers are vs plain_tf at matched parameters, 24k updates. Labels: shown = measured, suggested = reasoned from evidence, untested = guess. The plain_tf references are from the calibration runs: 3.2M is the 4-seed mean (pooled sd 1.0, in_dist sd 1.7), 10.8M is 1 seed.

**S (3.33M vs 3.24M), suggested unless marked untested:**

| Split | plain_tf | Ledger S (range) | Label |
|---|---|---|---|
| in_dist | 75.7 | 83 (77-88) | suggested |
| answer | 43.7 | 66 (55-72) | suggested |
| frame | 71.2 | 79 (72-85) | suggested |
| vocab | 60.5 | 71 (62-78) | suggested |
| variant | 20.2 | 28 (20-38) | untested |
| family | 0.8 | 5 (0-15) | untested |
| multi-step in_dist (12 harness families) | 62.1 | 84 (75-90) | suggested |
| chain-5 in_dist (chain_ops, chain_story2, story_chain3, var_chain, state_update) | ~38 | 85 (75-93) | suggested |
| pooled-5 | 54.2 | 65 (58-70) | suggested |

- answer split: an exact executor has no answer prior, so unseen (family, answer) pairs should score near in_dist on the 14 program families, where plain_tf gets 0-35 on chain_ops, state_update, story_chain3, var_chain, table_calc, percent and backward.
- vocab split: WORD copy should handle unseen syllables; plain_tf gets 20-42 on copy_word here.
- chain-5: for reference, bare 1.2B with worked steps gets 71% on 4 of these families and the sandwich 22.5%.

**Weakest families, in_dist (plain_tf → Ledger):**
- chain_ops 8 → 85.
- state_update 40 → 85.
- var_chain 28 → 80 (the binding through variable names is the hard part).
- chain_story2 48 → 92.
- table_calc 50 → 88.
- story_chain3 65 → 85.
- verify_claim 67 → 85.
- table_lookup 28 → 30: no programs; its numeric answers go through GEN; could be 20 (untested).
- The 15 program families together: about 70 → about 92 macro.

**The 19 families with no program supervision (untested, the main risk):** about 81 → 78 macro (range 70-85). Expected losers:
- cipher_map 54 → 45.
- fewshot_number_rule 65 → 50.
- seq_next 96 → 80.
- word_filter 97 → 88.
- table_lookup about equal.
- Gains on list_index 54 → 65 (word pointer).

**Held-out families (untested):**
- unit_convert 0-10 → 10-40: the DSL can express it (MUL/DIV), but the wording is new.
- op_define 0-10.
- string_transform 0.
- clock_date 0-3.

**L (10.79M vs 10.78M, untested):** in_dist 76.0 → 85, answer 41.8 → 66, variant 21.7 → 30, family 3.8 → 6, multi-step 64.0 → 86.

**Odds (my estimates):**
- P(pooled-5 gain >= +3 at S) ≈ 0.7.
- P(chain-5 gain >= +25) ≈ 0.8.
- P(non-program families within -5) ≈ 0.5.

**Where it could lose.** A plain_tf that writes the same steps and calls the same calculator (control C1') would probably tie Ledger on the program families (±5, suggested). Ledger's distinct value would then be the clean reasoner/talker split and the lesions, not accuracy.

**Against fine-tuned small LMs (untested).** SmolLM2-135M or Pythia fine-tunes may match Ledger on in_dist overall. I expect them to lose on chain-5 and on the answer split, because one-pass multi-digit arithmetic compounds errors.

## evidence

**Supporting papers (papers.md):**
- 1511.04834 Neural Programmer: exact built-in ops plus a small RNN reader reach about 99% on templated table QA from scratch, including unseen templates.
- 1810.02338 NS-VQA: program plus executor, 99.8% from 270 programs, and failures can be attributed to one module.
- 2008.06662 NeSS: 100% on SCAN length. It also warns that an op able to write the whole answer recreates a free talker; in Ledger, ops are binary and WORD copies only a reasoner-chosen word.
- 2211.10435 PAL: executed programs keep accuracy nearly independent of number size. GSM-hard: CoT 23.1 vs PAL 61.2. This is the basis for the answer-split prediction.
- 2302.04761 Toolformer: self-taught tool use emerges only at about 775M parameters, so the calls are supervised directly from `steps`.
- 2305.18654 Faith and Fate and 2307.03381: small transformers compound per-step arithmetic errors and never reach 100% in plain format. This explains plain_tf's 8% on chain_ops.
- 1803.03067 MAC, 2510.04871 TRM, 2202.05826 Recall: re-read the input every loop, with a small shared block.
- 2405.17399 Abacus and 2502.09741 FoNE: exact digit-position and number codes.
- 2205.15659 CLRS: intermediate hints help OOD.
- 1506.03134 and 2108.04378: pointer/copy outputs generalise to unseen items.
- 1811.12889: hard-wired structure that matches the task drives systematic generalisation.

**Contradicting or cautionary:**
- 2603.21676: answer-only supervision extrapolated better than per-step; here, step supervision is the core of the design.
- 1811.12889: learned layouts fail; Ledger's op choice is learned.
- SVAMP 2103.07191 (critic): solvers can pick ops from surface cues. This is the risk for the variant split.

**Repo results:**
- Results-digest row 17 / code-map 6.9 (shown): reader + core + class head reached only 13-15%, with computed-number families near 0. The missing piece was exact computation, which is what the executor adds.
- Row 12 (shown): a calculator path with a word-embedding reader got 59.2% on new-wording calls vs 91.0% with the LM reader. Reader quality limits op choice under new wording, which is a variant-split risk.
- Row 19 (shown): worked-step targets gave +11.8 fit and +21.7 held-out when the LM wrote them. The critic's untested suggestion was that steps should supervise the core, not the talker; that is this design.
- Row 22 (shown): tiny looped reasoners beat plain twins on 6-digit sums (298 vs 154 of 300).
- CALIBRATION (shown): plain char transformers are weakest exactly on chain_ops, state_update, var_chain and chain_story2.
- data.md section 6: the sandwich gets 22.5% on chain-4; bare 1.2B 5% direct and 71% with steps.

**My own checks (shown; parse plus CPU smoke tests, no training):**
- `steps` parses to the DSL for 100% of chain_ops, chain_story2, story_chain3, var_chain, state_update, backward_solve, distance_units, div_exact, percent_rate, story_addsub, table_calc and compare_numbers train rows, 99% of arith_bare, 67% of verify_claim and 36% of list_stats.
- Every chain-5 row in the 200-per-cell dev build (all splits) is DSL-executable.
- The executor plus slot remapping reproduced 2,033 of 2,033 gold programs.
- Parameter counts and CPU timings are in the params field.
- The prototype runs through evalx's evaluate, donor_eval and the loops/shuffle/zero lesions without error.

**What is different from what already failed.** The copy-and-gate talker (row 7) and the class head (row 17) had to produce numbers neurally or read meaning through a frozen LM. Here numbers are computed exactly, and the bar is a same-size from-scratch model, not the 1.2B.

## lesions

Expected values are on in_dist; all are untested predictions with marks fixed now.

1. **Donor swap** (harness donor_eval: same family, different answer).
   - Exact should fall from about 83 to 15 or below. Mark: a drop of at least 20.
   - donor_match should be about 60% overall. Mark: at least 50%.
   - NUM families: donor_match 85-90%, exact 0-3%.
   - GEN families: donor_match about 70%.
   - WORD families: exact 15-35% (the donor's index happens to land on the right word on 2-3-way choices), donor_match 10-20%.
2. **Loops sweep** (harness {0, 1, 2, 16}).
   - loops:0: 5% or less overall.
   - loops:1 (read only, nothing written): chain-5 at most 3%; program families at most 10%, apart from rows answered by the 0-op pointer.
   - loops:2: the 1-op families (arith_bare, div_exact, distance_units, story_addsub) stay within 3 points; chain-5 falls to 15% or less, a drop of at least 50 points.
   - loops:16: within 3 points of loops:8.
3. **shuffle_state** (cross-family roll): 10% or less. **zero_state**: 5% or less; this is a format check only.
4. **noexec** (custom lesion: every result slot invalid, so NUM falls back to GEN): program families 10% or less, a drop of at least 60 on chain-5. This shows the digits come from the executor, not from a hidden neural calculator.
5. **opswap** (custom lesion: the executor swaps ADD and SUB at inference). On chain-5 rows that were right when intact, at least 90% of outputs should equal the value of the swapped program, recomputed offline from the logged program. This shows the program the reasoner wrote carries the answer and nothing compensates.
6. **Honesty check on the latent half.** On the 19 non-program families, compare loops:2 with loops:8. If they are within 3 points, the reader rather than the loop is solving those families; report it as such.

The noexec and opswap lesions need a small generate() override and need adding to LESIONS.

## decisive_test

**Screen: 1 paired seed, about 25 min on one shared 5090, about $0.20.**

Job queue/04-ledger-screen.sh (# PAR 2 or 3):
- `ledger` with cfg {"d":256,"heads":4,"n_read":2,"n_loops":8}.
- A fresh `plain_tf` {"d_model":256,"n_layers":4,"n_heads":4} (the calibration rows are not reused, per CALIBRATION.md).
- Both: 24k updates, batch 256, lr 1e-3, bf16, seed 0, shuffled order, --final-eval.
- Then re-score both checkpoints with `python -m custom_io.evalx --data sk200k_big`.

Pass marks, fixed now:
1. Chain-5 in_dist on sk200k_big (5 families x 200 = 1,000 rows): Ledger minus plain_tf at least +25 points.
2. Pooled-5 (in_dist + answer + frame + vocab + variant, standard dev): at least +3 points.
3. The 19 families without program supervision, in_dist macro mean: Ledger no worse than plain_tf minus 5.
4. Donor lesion on in_dist: exact drops by at least 20 and donor_match is at least 50%; loops:2 cuts chain-5 by at least 50 points.

Result that proves it wrong: mark 1 below +10, or mark 2 at or below 0. Then the executor angle does not beat a same-size plain transformer on this benchmark, and work stops.

If mark 1 passes but mark 2 or 3 fails: the calculator half works and the latent half (WORD/GEN) is too weak. Fix that before confirming.

**Confirmation: only if the screen passes. 12 runs, about $1.**
- 6 paired seeds, Ledger S vs plain_tf S.
- Mark 1: mean at least +25, every seed at least +15.
- Mark 2: mean at least +3 and every seed above 0. Pooled-5 seed sd is about 1.0 (shown).
- Also report the answer split, multi-step, per-family results and all lesions.
- Attribution control C1: plain_tf trained to write "steps # answer" on program rows, 2 seeds. If C1 comes within 5 points of Ledger on chain-5, credit the steps supervision rather than the executor and structure.
- Optional C1': plain_tf + steps + the same calculator. A tie there means the custom structure buys lesionability, not accuracy.

**GPU throughput check.** Measure updates per second in the first 2 minutes of the screen. If Ledger runs below about 16/s while shared, run it only 2-way rather than capping minutes, so both arms get the same number of updates.

## implementation

**Files** (none of these exist in the repo yet):
- custom_io/models/ledger.py (about 350 lines): class Ledger(Model); helpers value_code(v, valid) and execute(op, a, b); Attn and Block, a pre-LN block with optional cross-attention.
- custom_io/models/ledger_prog.py (about 150 lines): steps → program parser and per-row targets, cached by row id. No search. Port it from the prototypes, deleting the search path.
- One line in models/__init__.py: MODELS['ledger'] = Ledger.
- queue/04-ledger-screen.sh.
- About 40 lines of tests: the executor reproduces gold programs; generate never reads answer or steps.

Total is about 550 lines, a few hours for a coder. Working CPU prototypes, which are not in the repo:
- /tmp/claude-0/-home-user-learner/efeefd59-f635-5d03-989e-45808869ca31/scratchpad/nsx/ledger.py (model)
- .../nsx/progparse.py (parser)
- .../nsx/coverage.py (row classes; SEARCH=0)
- .../nsx/check_exec.py
- .../nsx/smoke.py

**Pseudo-code:**
```
read(batch):
  H = enc(tok + pos + place); nums, spans = digit_runs(ids)
  S, vals, valid = slots(H, nums, CONSTS); Kw = k_word(span_mean(H, words))

run(batch, loops, gold=None):
  Z = z0; KVc = kv(ln(H + src_c))                 # computed once
  for t in range(loops):
    Z = core(Z + step[min(t, 7)], mem=[S + src_s; H])
    if 1 <= t <= 7:
      z = ln(Z[:, 0]); lop = op_head(z)
      la = q_a(z)·k(S); lb = q_b(z)·k(S)           # masked to valid slots
      o, a, b = gold[t] or argmax
      v, ok = EXEC(o, vals[a], vals[b])
      S[20+t-1] = vcode(v, ok) + type_r + op_emb[o] + step[t] + Wz z
  return Z, S, vals, valid, mode(z), q_ans(z)·k(S), q_w(z)·Kw

state = run
talk(st, batch):  NUM -> str(vals[ans]); WORD -> current prompt word[k]; GEN -> decode(Z, S[:, 20:27])
loss(batch): targets from rows' steps; run with gold; sum the CE / marginal-NLL terms
```

**Gotchas:**
1. state() and generate() take numbers from the prompt chars only, never from rows['answer'] or rows['steps']. loss() may read steps.
2. Positions: prompts have no BOS, and every printable ASCII char has its own id, so no UNK shifts positions.
3. Keep pointer logits and masks in fp32 under bf16, and values in int64.
4. Cache the char-memory K/V and LN once per forward; the prototype recomputes them every loop, which wastes about 30% of compute.
5. Cache targets and word ids per row id; Python per-batch work otherwise costs milliseconds per step.
6. Use the order-agnostic operand loss for commutative ops.
7. Clamp the step embedding when loops > 8.
8. The GEN talker memory must exclude prompt-number slots and constants; including them is a leak.
9. DIV is exact-only; invalid results are flagged and visible to the reasoner.
10. A NUM answer from an invalid slot falls back to GEN.
11. Use no family or variant labels anywhere.
12. The dev family split has answers of up to 12 chars: NUM printing is uncapped; GEN is capped at 8 chars.
13. Override generate() for the custom noexec and opswap lesions and list them in LESIONS.
14. Prompt numbers past the first 16 are dropped. That never happens in train; the maximum is 11.

## risks

1. **The latent half is weak (biggest risk, untested).** About 58% of in_dist rows have no program. The GEN talker must produce cipher strings, letters, counts and the numbers for seq_next, fewshot and table_lookup from 8 vectors, without seeing the prompt. Plain_tf does these at 54-98%. A loss of 5-15 points on these families would erase most of the overall gain.
2. **Narrow DSL coverage.** Only 34.6% of train rows have program supervision. Search-derived programs are spurious (shown). table_lookup, fewshot and seq_next stay neural. Programs from the rows' `meta` field could raise coverage, but that is a second step beyond this angle.
3. **Op choice may not transfer to new wording** (variant and held-out family splits). This is the SVAMP shortcut. Repo row 12 showed a calculator path failing on new wording with a weak reader.
4. **Attribution.** Gains may come from the extra steps supervision, not the architecture. Control C1 is needed. A plain_tf with a calculator (C1') may tie Ledger, leaving structure and lesionability as the only advantage.
5. **GPU wall time is unmeasured.** The small-kernel loop could break the 25-min shared budget. Fallbacks: run 2-way, torch.compile, or 6 loops.
6. **Exposure bias.** One wrong op ruins the chain and there is no recovery. Training is teacher-forced only; scheduled sampling would be a v2.
7. **The reader may steal the WORD/GEN reasoning.** A bidirectional encoder can solve list_index or passage_qa itself, so the loop's credit on those families may be small. The loops:2 vs loops:8 lesion reports this.
8. **Hand-written parts are tied to this generator.** The number tokenizer and the parser of this generator's steps format do not carry over unchanged to other data.
9. **In_dist gains may be partly template memorisation** (82% template overlap) and may not hold on the human-written sets.
10. **Ben may judge a hand-written calculator "less custom".** It is a fixed tool. It is the reasoner that chooses every operation and operand.

## english_and_minecraft_path

**English.** Keep the same split: reader, looped controller writing short programs over a workspace, exact tools, and a talker that only prints or copies. The executor library grows from arithmetic to lookup, compare, count and set operations over (entity, relation, value) slots that the reader fills. The talker stays a renderer and copier. Human-written English needs either much more text or a borrowed reader; if so, the borrowing should stop at the reader, never the reasoner or talker.

**Minecraft.** The executor becomes the game plus an exact inventory/crafting calculator. Slots are inventory counts, recipe rows and coordinates, and programs are action and craft sequences. Resource planning is then exact, and a new recipe is data, not new weights.

**Few-shot learning.** A new skill becomes a new composition of existing operations, which is a much smaller thing to learn from a few examples than new arithmetic.

