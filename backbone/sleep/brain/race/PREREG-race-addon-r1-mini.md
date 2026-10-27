# PREREG sleep race, add-on side, round 1 on race-mini: LoRA+ (lora_B lr x16)

Replaces PREREG-race-addon-r1.md (bc44ba73...), whose full Week-2 runs never started (the 4090s did not arrive). Same single change, run
under the shared race-mini protocol (backbone/sleep/brain/race/PROTOCOL-mini.md, sealed by both sides, commit de57ac5ee on claude/project-thread-qcuhwj).
Sealed before any race-mini run.

Runs (one combined PC job, race/pc_race_mini.sh): lora_s1, lora_s2 (control: LoRA r16 a32 lr 2e-4, SHY x0.85) and lp16_s1, lp16_s2 (same + --lora-plus 16).
K2-3.7B packed 4-bit base, Week-2, shared Haiku tape, 7 nights x 300 steps, no morning gate. Seeds 1, 2 (same batches across arms).

Marks (fixed now). Primary = recall C2+C4 forward, final, pooled 400 paired items (paired exact McNemar).
- PASS: pooled lp16 >= pooled lora + 4, p < 0.05, and each seed lp16 >= lora.
- Harm (fails the round): ARC-Easy (race-mini's ARC set) < its base - 5, on either seed.
- WRONG: pooled lp16 <= pooled lora + 1.
- If 0.05 <= p < 0.2: add seed 3 for both arms before calling it (protocol rule).
- Also recorded, no mark: night-4 recall (the faster-learning check), reverse, C1, changed new/stale, routine, held-out KL, seconds per night.
Race: vs the whole-model qs arm on the same seeds; a lead needs pooled p < 0.05 and no harm fail on either side.
Validity first (protocol): bf16-base LoRA >= q4 LoRA + 3 pooled; if the gap is under 1 race-mini is not trusted and nothing here is scored.
