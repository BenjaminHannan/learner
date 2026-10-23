# Stage 1 run log

2026-10-23 ~20:15Z. Settings fixed before launch (the prereg left these open): STEPS=1500, bsz 16, max-len 2048
(1024 would cut the evidence out of ~60% of contexts), LoRA r16, lr 2e-4 cosine, seed 0. A per-arm time
budget can lower the step count once at step 20 (logged as steps vs steps_requested); any such cut is reported.
Boxes (Vast, run in parallel, each self-stops at 3 h):
- 57418506 claude-bb-a  A100 PCIE 40GB $0.443/h: arms a0, a
- 57418505 claude-bb-b  A100 SXM4 40GB $0.539/h: arm b, then b with --eval-loops 1
- 57418503 claude-bb-a2 A100 SXM4 40GB $0.416/h: arm a2 (Qwen3.5-2B), micro-batch 2
