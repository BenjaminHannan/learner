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
- 23:17Z: boxes a2 (57421035) and a418 (57424117) never returned logs (Vast log API failed for that California host the whole run), so their results are lost; destroyed. a2 relaunched in New York at a fixed 418 steps + probes (claude-bb-a2b); a418 is replaced by claude-bb-probes.
- 00:08Z Sleep-1 box claude-bb-sleep1 (A100 SXM4 NY, $0.54/h): arms s2,s0,ic,s1 on Qwen3.5-2B.
- 00:46Z claude-bb-probes2: arm a 418 steps, probes Pname,Pdepth,Prule (requested by the generalization thread).
- 00:48Z claude-bb-creative1 (NY A100): Creative-1 arms f0,c16,sleep on Qwen3.5-0.8B.
- 01:17Z sleep1 and creative1 boxes on NY hosts never uploaded logs (S3 403 for 70+ min); destroyed and relaunched (Quebec, Slovenia). Boxes now also write result summaries into their instance label.
- 01:47Z creative1 box 57448229 finished; result JSONs pulled with `vast.py cat` after stopping (cat only works on stopped boxes), then destroyed.
- 01:58Z claude-bb-creative2 (Slovenia A100, box 57450816): Creative-2 = Creative-1 arms with CREATIVE_FLAGS=--no-branch.
- 04:45Z claude-sleepb-cqc4bi (57467248, A100 SXM4 UK, $0.54/h, hours=4, cap $3; coordinator OK 03:55Z): Sleep-B arms a0,ad,ab,af,ab_noshy,ab_norem,ab_flatprio,ab_all on Qwen3.5-2B (backbone/sleep/brain/PREREG-sleepB.md). Thread "Design sleep like the human brain", branch claude/project-thread-cqc4bi.
- 05:50Z claude-sleepb2-cqc4bi (57473371, A100 SXM4 UK, $0.54/h, hours=2): Sleep-B addendum 1 arms ab_ob, ab_klctx (+ router R) with AB's stage-1 schedule. Same thread/branch; thread total cap $3.
- 06:31Z claude-sleepb2 (57473371) stopped by hand after ~30 min: ab_ob crashed on the GPU (log service 403, likely OOM on long open-book batches); ab_klctx was at night 2. Relaunched as claude-sleepb3-cqc4bi (57477625, A100 SXM4 California $0.416/h, hours=2) with token-budget micro-batching.
- 06:53Z claude-sleepb3 57477625 stuck in 'loading' for 22 min (California); destroyed. Relaunched as 57479670 on New York A100 SXM4 $0.539/h (hours=2).
- 08:18Z claude-sleepb3 57479670 finished ab_ob and ab_klctx (results in its label; see backbone/sleep/brain/RESULTS-sleepB.md). Stopped, then destroyed with 57467248 at 08:20Z. Vast's cat service still answered "command output not ready", so the result JSONs (ARC for the stage-2 and addendum arms) were not recovered. Thread GPU spend is about $2.70 of the $3 cap.
- 13:52Z claude-sleepb4f-cqc4bi (57521297, A100 SXM4 80GB Texas, $1.078/h, hours=2): Sleep-B addendum 2 arm ab_ob_full (every LoRA-target matrix gets a full-rank change, lr 2e-5), seed 1, AB stage-1 schedule. Prereg backbone/sleep/brain/PREREG-sleepB-addendum2.md. Coordinator OK 13:37Z, cap $2 across both boxes.
- 13:52Z claude-sleepb4m-cqc4bi (57521298, A100 SXM4 40GB New York, $0.539/h, hours=2): addendum 2 arms ab_ob (seed-1 control) then ab_ob_merge. Same schedule and cap.
