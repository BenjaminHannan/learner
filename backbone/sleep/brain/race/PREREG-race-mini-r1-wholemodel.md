# Race-mini round 1, whole-model side: 4-bit scale sleep (qs) vs the add-on, on the shared dream tape

Protocol: PROTOCOL-mini.md (this folder). Replaces the paid-GPU round 1 (PREREG-race-r1-wholemodel.md, never run: the 4090s did not come).
Arm qs: race_mini.py --storage qs --qs-store fp16 --qs-round nearest --lr <scout pick> (per-group 4-bit scale and offset of every LoRA-target layer
train; codes fixed; nightly u, v x0.85 then fp16 rounding). Opponent: the add-on control, race_mini.py --storage lora (LoRA r16 a32 lr 2e-4, SHY), same job, same seeds.
Headline R = C2+C4 forward recall (200 items) after the last night, weights only, served copy.

PASS (whole-model takes the lead): pooled R(qs) >= pooled R(lora) + 4 points AND paired exact McNemar on the pooled 400 items p < 0.05 AND same
direction on both seeds AND no harm (ARC-Easy 500 >= base - 5 points on both seeds). p in [0.05, 0.2) -> seed 3 for both before the call.
TIE (champion holds): |difference| < 4 or p >= 0.2 with no harm.
WRONG (whole-model scale storage loses): pooled R(qs) <= R(lora) - 4 with p < 0.05, or harm on either seed.
Reported, no mark: night-4 recall, reverse, changed new/stale, routine, C1, held-out KL, qs vs LoRA+ x16, mean |u|, |v| and fp16 rounding loss.
Invalid round: the validity check fails (PROTOCOL-mini 8).
