# P0 probe spec (written 2026-10-06 00:07 UTC by file time, before any sampled candidate was drawn; first sampled run started 00:09:56 UTC)

Checked before writing: the B2_s100 checkpoint loads on CPU and its greedy scores match RESULT.json exactly
(family 0.62, frame 85.59, vocab 88.00). No sampled run had been made.

## What is sampled (primary, as asked: "program/pointer heads")
B2 = `custom_io/models/ledger.py` with `copy=True`. In `Ledger.run` each write step t = 1..7 takes argmax of the op head
and the two operand pointers (ledger.py:227). After the last loop the talker takes argmax of the mode head, the answer
pointer (NUM), the word pointer (WORD) and each GEN register's pointer-generator distribution (ledger.py:265, 269).

- **prog+ptr (primary):** sample op, operand a and operand b at every write step from softmax(logits / T), and sample
  the answer pointer and the word pointer from softmax(logits / T). Mode head and GEN characters stay argmax. Masked
  (invalid) slots keep probability 0. Everything else (reader, 8 loops, executor, copy talker) is unchanged. Because
  the sampled op/a/b are executed and fed back into the workspace, later steps, the registers and the mode see the
  sampled program.
- **all-heads (secondary, exploratory, fixed now before results):** prog+ptr plus the mode head sampled at T and each
  GEN register's character sampled from its pointer-generator distribution p (sharpened to p^(1/T), renormalised).
  Reported separately; the decision rule below uses prog+ptr only.

Temperatures 0.7, 1.0, 1.5. N = 32 candidates per question per temperature. One torch.Generator per
(checkpoint, split, variant, temperature), seed = 20261006 + fixed offsets. No training. CPU only.

## Rows
- (a) **heldout**: all 160 rows of dev/family.jsonl (clock_date, op_define, string_transform, unit_convert; 40 each).
- (b) **frame_wrong**: dev/frame.jsonl rows the checkpoint gets wrong greedily (new sentence frames).
- (c) **vocab_wrong**: dev/vocab.jsonl rows the checkpoint gets wrong greedily (new words).
Both (b) splits exist, so both are run. Data: skills_curriculum build `--train 200000 --dev-per-cell 40 --seed 1`
(manifest sha256 equal to FULL-BUILD-MANIFEST-200k-seed1.json).

## Scoring (known-answer; this is NOT a key-free checker)
hit = evalx.is_hit (normalised exact match against `accepted`).
- greedy pass@1 = the unmodified `generate`.
- pass@k (k = 1, 8, 32) from the 32 sampled candidates with the unbiased estimator 1 - C(n-c, k) / C(n, k), n = 32
  (pass@32 = any of the 32 hits). Also reported: "greedy or any sample" hit rate.
- distinct answers per question: number of distinct normalised talker outputs among the 32 (mean, median, max).
- distinct programs per question: distinct 7-step (op, a, b) tuples among the 32.
- answer differs from greedy: share of candidates whose output differs from the greedy output.
- well-formed share: candidate where every non-NOOP step executed validly (no inexact DIV, no division by zero, no
  overflow) AND the talker path chosen was usable without fallback (NUM: pointed slot valid; WORD: word index inside the
  prompt's words; GEN: always usable). Also reported: share with at least one non-NOOP op.

## Meaning, fixed now (heldout split, prog+ptr, per temperature and per checkpoint)
- pass@32 >= greedy + 10 points: a sample-filter-train loop has **signal to start from** on these families.
- pass@32 <= greedy + 2 points: **cold start** (no hits, so no signal); easier variants or teacher hints are needed first.
- In between: **weak signal**.
The verdict uses the best of the three temperatures, and per-temperature numbers are all reported. For frame_wrong and
vocab_wrong, greedy is 0 by construction, so pass@32 is read directly as the rescue rate (same 10 / 2 point lines).
What would prove the "signal" reading wrong even if the line is crossed: hits concentrated in one family and coming
from answers the candidate could produce without the program (for example a constant answer), checked by the per-family
table and the distinct-answers count.
