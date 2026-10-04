# Plateau diagnosis v1: result

Run 2026-10-04 19:03-20:16 UTC on Vast box 54189350 (RTX 5090). Copy-back sha256 checked (pull_log ok) before the box was destroyed. Full table: SCORE.txt.

## Shown
- main2 scores 68.5% on all 1,360 in_dist rows (34 families x 40) and 24.4% on the 160 family-shift rows.
- Errors are spread out, not concentrated: the worst 8 families hold 54% of errors (mark was 60%). Worst 8 = chain_ops 15, state_update 15, cipher_map 20, chain_story2 28, var_chain 28, seq_cycle 35, fewshot_number_rule 38, group_induct 45. All are multi-step or state-tracking.
- **VERDICT: CAN-NOT-FIT.** After 6 passes over 2,000 fixed rows, main2 gets only 48.1% of those same rows right (mark 85). Fresh-row practice gains +10.0 held-out (mark 15, so not UNDER-TRAINED); fixed-set gains +6.5.
- Held-out scores swing by up to 9 points between checkpoints of one run (N1: 37 -> 45 -> 43 -> 35%).
- No prompt is over the 64-token cap and no answer is over 12 tokens, so truncation does not explain errors (token count with the LFM tokenizer on all dev rows and 1/10 of train).

## Suggested (from reading the code, not tested)
The model cannot even memorise 2,000 questions, and fair scaling showed a 4x bigger core does not fit better. So the limit sits outside the core's size. Candidates, in the order the code points to them:
1. Two 32-wide pipes: reader 2048->32->256 per token, and exit 259->32->2048, then averaged down to 8 prefix slots by adaptive average pooling over positions (order inside each slot is lost).
2. Fixed 4 loop rounds (hard-coded) for multi-step families.
3. Optimiser noise: batch 1, constant lr 1e-3, clip 1.0 (the checkpoint swings above).
