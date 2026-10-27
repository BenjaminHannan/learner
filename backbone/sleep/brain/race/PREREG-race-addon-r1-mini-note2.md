# Note 2 to PREREG-race-addon-r1-mini.md (05b7b2f9...): the race moves to LFM3. Sealed before any LFM3 race-mini run.

Ben, 19:45Z Oct 27: the small tier is now LiquidAI/LFM3-1.7B instead of K2-Horizon-3.7B. Both sides agreed (19:49Z) to run race-mini round 1 on LFM3.
Note 1 (75-step arms, dose validity, ceiling fallback) still applies, with these changes only:
- Base: LFM3-1.7B (model rev 40ebe0aa66), frozen as the SERVED file: LiquidAI/LFM3-1.7B-GGUF LFM3-1.7B-QAD-Q4_0.gguf (rev b3f2ae5d73), loaded with
  sleepb --q4-base --q4-format q4_0 --q4-gguf (commit 267fa0598). QAD weights are not Q4_0 of the bf16 checkpoint (~7% apart), so the served numbers are used. Not packed.
- Chat format: LFM3's ChatML no-think prompt ("<|im_start|>assistant\n<think></think>"), eos <|im_end|>; the Qwen-style Lang path, unchanged code.
- LoRA: r16 a32 lr 2e-4 on LFM3's 142 target Linears (conv in/out_proj, q/k/v/o, w1/w2/w3; not the attention gate_proj). lp16 = the same + --lora-plus 16. No lr scouting on LFM3 before the run.
- Steps a night: 75 (note 1), unless the joint race-mini ADDENDUM-2 for LFM3 sets another count after its 300-step reference; then that count, the same for every arm.
- Validity: the dose check reruns on LFM3 (300-step control >= 75-step control + 2 points final C2+C4, else nothing is scored). bf16-base vs served-base is reported, not a gate.
- Marks unchanged: PASS pooled lp16 >= c75 + 4, p < 0.05, each seed lp16 >= c75; harm ARC < base - 5 on either seed; WRONG pooled lp16 <= c75 + 1; seed 3 if 0.05 <= p < 0.2; ceiling fallback to night 4 if pooled c75 final >= 0.90.
Expectation (not a mark): LoRA+ helped most on the CPU card when plain LoRA was slow; at 75 steps on a 1.7B base the control may be slower than on K2, which favours lp16.
