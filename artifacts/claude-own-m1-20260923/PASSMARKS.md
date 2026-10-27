# own-M1: the conversational mouth (fine-tuned MiniCPM5-1B + slot gate). Pass marks, fixed 2026-09-23 18:40 UTC before any training

Change vs. today: the reply is written by a fine-tuned copy of MiniCPM5-1B (Ben's reader model, Apache 2.0, already approved)
from the reply record + the user's turn + a dialog tag. Names and values go through slot tokens (<S1> <V1> <R1>), and the
printer fills them in. Code (scripts/claude_own_m1_common.py slot_check) rejects any reply with a slot the record lacks, a
missing required slot, a value on a no-value status, a capitalised word outside slots, or a digit; up to 4 sampled retries,
then the caller falls back to the 241b rewriter. Data: own-M0 (artifacts/claude-own-m0-20260923), which must be verified
PASS by the own-model thread before this runs. Training: scripts/claude_lis300_train.py unchanged (LoRA r32, every linear
layer, loss on the reply only), 2 epochs, lr 2e-4, batch 16, max-len 256, merged.

Measured on own-M0's dev split (1,000+ rows, disjoint names). These marks are for the mouth alone. Conversation quality is M3,
graded on the talking line's convbench-f0 with F0's marks; this run never opens convbench-f0.

| Mark | Bar |
|---|---|
| Pm1.1 spoke (a reply passed the gate within 5 tries) | >= 99% of dev rows |
| Pm1.2 first-try pass (greedy reply passed the gate) | >= 95% of dev rows |
| Pm1.3 replies that reach output and fail a fresh slot_check recount | 0 |
| Pm1.4 variety: distinct slotted replies on dev | >= 30% of dev rows; the single most common reply <= 3% of rows |
| Pm1.5 crashes | 0 |
Reported, no bar: fallbacks per status, median / p90 speak ms on the GPU, training minutes, tok/s, dollars.
Proved wrong if first-try pass < 80%: fine-tuning on M0 did not teach the slot format, and the 1B speaker is not viable as trained.
One change only; a FAIL gets exactly one diagnosis-driven follow-up.
