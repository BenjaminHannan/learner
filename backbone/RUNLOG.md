# Stage 1 run log

2026-10-23 ~20:15Z. Settings fixed before launch (the prereg left these open): STEPS=1500, bsz 16, max-len 2048
(1024 would cut the evidence out of ~60% of contexts), LoRA r16, lr 2e-4 cosine, seed 0. A per-arm time
budget can lower the step count once at step 20 (logged as steps vs steps_requested); any such cut is reported.
Boxes (Vast, run in parallel, each self-stops at 3 h):
- 57420072 claude-bb-a  A100 PCIE 40GB $0.443/h: arms a0, a
- 57420069 claude-bb-b  A100 SXM4 40GB $0.539/h: arm b, then b with --eval-loops 1
- 57420065 claude-bb-a2 A100 SXM4 40GB $0.416/h: arm a2 (Qwen3.5-2B), micro-batch 2
- 57420074 claude-bb-27b RTX PRO 6000 96GB $1.20/h: Qwen3.8-27B untrained 3-shot reference (vLLM, max-len 4096; no mark)
First launch (~20:05Z) failed at unpack (no xz in the image; boxes destroyed after ~10 min, < $0.40 total); relaunched 20:17Z with gzip.
Second launch (20:15Z) failed: the runtime image has no C compiler, which Triton needs for the linear-attention
kernels (fla, and vLLM's). Relaunched 20:27Z on the -devel image: a 57421039, b 57421036, a2 57421035, 27b 57421042.
20:58Z: the time budget cut arm b to 418 steps (about 4 s/step on the A100 with the loop). Arm a's own budget will
give it more steps, so an extra box runs arm a at exactly 418 steps (claude-bb-a418) for the prereg's equal-steps
comparison; the longer arm a run is reported too. 27B box relaunched with max_num_seqs=256 (vLLM refused 1024:
too few linear-attention state slots).
- 23:12Z claude-bb-probes: arm a, 418 steps (no budget), also scored on the generalization thread's P0 and Pword probes (generalize.probes @21b4d92b7, seed 101, 500 visits each, generated on the box with that commit's learnlab in backbone/genlab).
