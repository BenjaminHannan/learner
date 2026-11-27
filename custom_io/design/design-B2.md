# B2: design B with a content-addressed copy talker (one change)

Written 2026-10-05 about 12:25 UTC (8:25 AM ET), after the 2-seed screen and before any B2 code or run.

## What the screen showed about B (shown, seeds 100 and 101; diagnosis on B_s101's checkpoint, `custom_io/diag_ledger.py`)
- B ties plain_tf_steps on pooled-5 (+0.8) and C1' (-0.3), and wins chain-5 (99.7 / 99.9 vs 93.5 / 94.2).
- Its talker picks the right mode almost always (mode accuracy 33-40 of 40 in every weak cell outside the variant split).
  The rows it loses are lost inside the two non-program talker paths:
  - **GEN registers cannot emit what they never emitted in training.** letter_ops answer split 0/40 ("first letter of
    zijovonu" -> 'r'; the held-out answer letters z and j never appear as answers in train); digits_parity answer split 0/40
    (tens digit of 748 -> '5'; digit sums off by one); word_filter answer split 0/40.
  - **The WORD pointer's keys are content-free (word index, start position, length),** so a new sentence frame moves the
    target: copy_word frame 22/40 ("Say this word back: mimo" -> copies "out"), group_induct frame 19/40.
  - Lookups by content are weak: cipher_map 61% in_dist (A gets 100%).
- Where B loses rows to plain_tf_steps (both seeds): letter_ops answer -89, group_induct frame -40, copy_word frame -39,
  passage_qa frame -35, rule_apply -24 to -45, fewshot_number_rule -19 to -31, cipher_map -16, order_chain -13 to -33 points.
  Some of these are reasoning failures (order_chain, kin_chain, fewshot_number_rule) that a talker change cannot fix.

## The one change
The talker's pointers into the prompt become **content-addressed**, and the GEN registers can **copy** a prompt character:
1. **GEN copy (pointer-generator, See et al. 2017):** each of the 9 registers R_i also forms a query q_i = Wq LN(R_i) over the
   reader's per-character outputs X_t (keys Wk X_t, dk = 64). p_i(c) = g_i softmax(readout(R_i))_c + (1 - g_i) sum_t a_it
   [prompt char t = c], g_i = sigmoid(wg LN(R_i)). Trained by -log p_i(target); decoded by argmax p_i. A register can now
   say 'z' by pointing at the 'z' in "zijovonu", or '4' by pointing at the tens digit of 748 (the reader's place codes mark it).
2. **Content in the WORD keys:** key_k = (old content-free key) + Wc LN(mean of X over word k's characters). The reader's
   features carry each word's characters and about 4 characters of context, so "the word after 'back:'" can be found in a
   new frame.

Unchanged: reader, workspace, controller, executor, NUM pointer, mode head, loss weights, data, flags (24k updates,
batch 256, lr 1e-3, bf16). `copy: true` in the model cfg turns it on; `copy: false` (default) is exactly B (same modules,
same init, same state_dict keys). The new modules are created last, so at the same seed every shared weight starts the
same as in B. Size: B 3,252,368 + about 50k = about 3.30M (+1.8% vs plain_tf 3,244,544; the size rule is +-3%).

Why this is still "the talker translates the state": what to copy is decided by the reasoner's registers and control
token (the queries); the talker only executes a match-and-copy. The lesions below test that: shuffling or zeroing the
state must break the copies, and switching the copy off (`nocopy`) shows how much of each family the copy path carries.

## What it cannot fix (forecast, untested)
Latent arithmetic and multi-hop choice in GEN or WORD families with no program in the data (rule_apply, fewshot_number_rule,
digit sums, word_filter counts, order_chain, kin_chain). Giving those families programs would need step text the data does
not have (their `steps` are labels like "threshold", "scan list"); writing it by hand would give B2 supervision
plain_tf_steps does not get, so it is left out of this comparison.

## Lesions added
- `nocopy`: g_i forced to 1 (vocabulary only) at inference.
- `nowordc`: the content term of the WORD keys set to zero at inference.
Marks: `custom_io/PASS-MARKS.md`, addendum 2.
