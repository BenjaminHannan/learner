# Prompt for GPT (web): does a small "program + exact executor + copy talker" model show that its reasoner does the work?

Written 2026-10-05 (custom reader/talker thread). GPT cannot see the repo, so everything it needs is pasted below. Paste
from the line "You are reviewing" down.

---

You are reviewing a small research result. Please be skeptical and concrete.

Label every claim **shown** (follows from the numbers below), **suggested** (reasoned, not measured) or **untested**.
Then give a plain-language summary of a few sentences for Ben, a high-school senior who runs the project.

## Context

Ben's project normally puts a ~9M-parameter latent "reasoning core" between two copies of a frozen 1.2B pretrained
language model (LFM2.5-1.2B), one as reader and one as talker. Evidence suggests the borrowed LM does most of the
reasoning. Ben asked for a custom reader and talker, ideally with nothing pretrained, built so that the reasoner has to
do the thinking. His success test: the whole model beats similarly sized models by a clear margin.

This is a separate track from the project's other experiments. Please keep it separate in your answer, and do not
transfer conclusions to the 1.2B model or to the project's other small models.

## Data and metrics

- **Skills curriculum.** 200k training rows from 34 synthetic task families: arithmetic chains, word problems, lookups,
  cipher maps, copy-a-word, object tracking, propositional logic, ordering chains and others. Prompts are short English
  sentences, and answers are short strings (a number or a word).
- **Dev splits** (40 rows per family each):
  - in_dist (same templates);
  - answer (answer values unseen in training);
  - frame (new sentence frames);
  - vocab (new words);
  - variant (new wordings);
  - family (6 held-out families).
- **pooled-5** = micro exact match over in_dist, answer, frame, vocab and variant (6,040 rows).
- **chain-5** = 5 multi-step arithmetic families, 1,000 rows.
- Every model trains from scratch, character-level, on the same rows in the same order: 24k updates, batch 256,
  lr 1e-3, bf16.
- **Screen** = 2 seeds (100, 101), paired by seed. Pass marks were written before training.

## Models (all about 3.2-3.3M parameters, nothing pretrained)

- **plain_tf**: a 4-layer char transformer (d 256) that answers directly. 3,244,544 parameters.
- **plain_tf_steps**: the same transformer, trained to write the worked steps ("12+7=19; 19*3=57 # 57") before the
  answer, on the 11 families whose data has numeric steps. 3,260,928 parameters.
- **C1'**: plain_tf_steps with a calculator overwriting each "a op b =" result while it decodes.
- **B (Ledger)**:
  - A conv char reader (receptive field ±4 chars).
  - A hand-written splitter finds the numbers and words in the prompt. It has no parameters.
  - Numbers become workspace slots with exact int64 values.
  - A controller (8 iterations of 2 shared attention blocks over 8 control tokens and 9 register tokens) emits, at each
    step, an op (NOOP/ADD/SUB/MUL/DIV/MOD/MIN/MAX/CMP) and two operand pointers. A parameter-free int64 executor
    computes the result into a new slot.
  - Programs are teacher-forced from the data's step text.
  - **Talker:** a mode head picks one of:
    - NUM: print the slot the reasoner points to;
    - WORD: copy word k of the prompt, with content-free word keys (index, start position, length);
    - GEN: a linear readout of the 9 register tokens, one char each.
  - 3,252,368 parameters.
- **B2**: B plus one change, a content-addressed copy talker. 3,302,481 parameters.
  - GEN becomes a pointer-generator (See et al. 2017). Each register mixes its vocabulary softmax with attention over
    the reader's per-char features, through a learned gate.
  - The WORD keys gain a content term: a projection of the mean reader feature over the word's chars.
  - The queries come from the reasoner's registers and control tokens.
- **A (register loop)**: 16 latent slots, 6 rounds of 3 shared blocks with cross-attention to the reader. The
  units-first register slots are trained to hold the r-th worked-step value after round r, and a linear talker reads
  them. 3,217,708 parameters.

## Results (2-seed means unless noted)

| model | pooled-5 | in_dist | answer | frame | vocab | variant | held-out families | chain-5 |
|---|---|---|---|---|---|---|---|---|
| plain_tf | 54.4 | 75.6 | 42.6 | 71.2 | 63.4 | 20.3 | 1.9 | 34.2 |
| plain_tf_steps | 67.7 | 87.5 | 62.1 | 83.2 | 79.6 | 29.5 | 0.6 | 93.8 |
| C1' | 68.9 | 88.6 | 63.8 | 84.2 | 80.5 | 30.6 | 0.6 | 96.4 |
| A | 64.5 | 84.4 | 56.8 | 83.8 | 74.4 | 25.0 | 1.6 | 63.1 |
| B | 68.6 | 85.3 | 69.8 | 77.9 | 82.9 | 31.9 | 3.1 | 99.6 |
| B2 | 73.7 | 89.6 | 75.9 | 86.7 | 87.5 | 33.5 | 0.9 | 99.8 |

Paired by seed, B2 minus each baseline on pooled-5 (seed 100 / seed 101):
- vs plain_tf_steps: +4.4 / +7.4;
- vs C1': +3.4 / +6.1;
- vs B: +4.6 / +5.7.

**Lesions on B2** (in_dist exact unless noted; both seeds):
- Donor swap (another row's reasoner state, this row's prompt for the talker): 3.8.
- Shuffled state: 7.9. Zeroed state: 0.0.
- No executor (every result invalid): program families 0.6.
- ADD and SUB swapped in the executor: 99.9% of affected chain rows give the swapped program's value.
- One controller iteration (loops:1): chain-5 0.0 / 0.1.
- Two iterations: one-op families fall 58-68 points. Our suggested cause: the mode and answer heads are only trained
  after 8 iterations.
- Copy turned off (gate forced to vocabulary): -33 points on the 5 copy-target families (cipher_map -98, letter_ops -55,
  digits_parity -22); -8.3 pooled-5.
- Word-content term turned off: -18 pooled-5 (copy_word -68, group_induct -70).
- **Zero iterations (loops:0, the talker reads the untouched initial registers): in_dist 0.0% (seed 100) and 6.76%
  (seed 101).** The pre-set mark was ≤ 5%. The seed-101 hits are all word-pointer families: copy_word 18/40,
  object_track 18/40, prop_eval 16/40, order_chain 8/40. B with content-free keys gave 3.1 / 4.4.

**Where B2 still trails plain_tf_steps** (pooled-5, per family): fewshot_number_rule -9, rule_apply -6, and -2 to -3 on
digits_parity, group_induct, order_chain and state_update. These families have no program in the data.

For A: the round-1 register interchange matched the counterfactual answer on 1.8% of rows (mark ≥ 40). Our reading is
that A's rounds recompute from the prompt rather than carrying the intermediate value.

Place codes alone (each char's index from the end of its word) changed plain_tf by +0.8 and plain_tf_steps by -0.8 on
pooled-5.

By the pre-set rules B2 is NO-GO, because the loops:0 check failed in one seed. Every other gate passed.

## Questions

1. Does the loops:0 result (0% and 6.8%, with all hits in word-pointer families) undermine the claim that B2's reasoner
   decides the answer? Is it a real leak (a talker that reasons on its own) or expected behaviour for any
   content-addressed pointer with a fixed query? What one measurement would tell those apart?
2. Credit: does B2's lead over plain_tf_steps come from the reasoner (choosing ops and operands), the exact executor,
   or the copy talker? Which lesion or control above best separates them? Is one missing?
3. Is "B2 beats same-size transformers" a fair answer to Ben's goal of a model whose reasoner does the work? Consider
   that the programs are teacher-forced from step text, the executor is exact, and the number/word splitter is
   hand-written. What is the strongest objection?
4. Should the 6-seed confirm run despite the failed check? Or should we first make one change, and if so which one?
   For any change you propose, give one change at a time, a pass mark fixed in advance, and the result that would prove
   it wrong.
5. The families B2 loses (rule_apply, fewshot_number_rule) need latent arithmetic or rule induction, and the data has
   no program for them. What is the smallest next design step for those, under the same one-change, marks-first rules?

Please end with the plain-language summary for Ben.
