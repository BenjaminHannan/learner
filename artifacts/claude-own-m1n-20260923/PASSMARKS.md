# own-M1n: the conversational mouth v2 (natural replies). Pass marks, fixed 2026-09-23 18:50 UTC before any training

ONE change vs own-M1 (v1): the training replies are artifacts/claude-own-m0b-20260923/train.jsonl (5,602 Opus-written, blind-reviewed natural replies), not own-M0's 20,000 template replies. The model (MiniCPM5-1B), code (sealed in artifacts/claude-own-m1-20260923/SEAL-code.sha256.txt), hyperparameters (LoRA r32, 2 epochs, lr 2e-4, batch 16, max-len 256, merged) and dev set (own-M0 dev, 1,000 rows) are the same as v1.

| Mark | Bar |
|---|---|
| Pm1n.1 spoke (a reply passed the gate within 5 tries) | >= 99% of dev rows |
| Pm1n.2 first-try pass (greedy reply passed the gate) | >= 95% of dev rows |
| Pm1n.3 replies that reach output and fail a fresh slot_check recount | 0 |
| Pm1n.4 variety: distinct slotted replies on dev | >= 30% of dev rows; the single most common reply <= 3% of rows |
| Pm1n.5 crashes | 0 |
Reported, no bar: fallbacks per status, speak ms, training steps (first and last loss), minutes, dollars.
Proved wrong if first-try pass < 80%: 5.6k natural rows were not enough to teach the slot format.
Fluency is not judged here. It is judged in M3 on convbench-f0, on top of the listener's reader, and never opened by this run.
