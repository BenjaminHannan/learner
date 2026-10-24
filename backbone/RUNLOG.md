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
- 14:00Z claude-sleepb4f 57521297: ab_ob_full crashed at startup. The new delta self-check builds a tiny CPU model, and the box's Triton linear-attention kernels refuse CPU tensors. Destroyed after 0.14 h. The fix (skip that check on GPU; it still runs in --selftest and smoke) is commit "skip the CPU-model delta self-check". Box 57521298's merge arm will hit the same crash after its control arm, so the merge arm is deferred.
- 14:02Z claude-sleepb5f-cqc4bi (57522280, A100 SXM4 80GB Texas, $1.078/h, hours=2): ab_ob_full relaunched with the fix.
- 14:43Z / 14:50Z: 57521298 (control done; merge crashed as expected) and 57522280 (ab_ob_full done) destroyed by a watcher as soon as their results reached the labels. Addendum 2 spend is about $1.61 including the crashed box. Results are in RESULTS-sleepB.md.
- 17:27Z claude-sleepb6l-cqc4bi (57543171, A100 SXM4 80GB France, $0.936/h, hours=2): Sleep-B addendum 3 arm ab_ob_local (targeted plasticity). claude-sleepb6s-cqc4bi (57543172, A100 SXM4 80GB Japan, $1.15/h, hours=2): ab_ob_full_s (every weight, lr 5e-6). Both seed 1, AB stage-1 schedule. Coordinator OK 16:58Z, cap $2.50; a watcher destroys each box when its result reaches the label, or after 20 min with no progress.
- 18:23Z claude-sleepb7m-cqc4bi (57548525, A100 PCIE 40GB Japan, $0.346/h, hours=2): Sleep-B addendum 2 arm ab_ob_merge (fold-in), seed 1, AB stage-1 schedule, tok budget 2048 (same gradients). Moved off Ben's PC, where three tries stalled at night 2 at 15.9/16 GB and blocked the PC queue. Within the 16:58Z $2.50 approval (about $0.70 left); a watcher destroys the box when the result reaches the label, after 20 min with no progress, or at $0.70.
- 19:10Z Sleep-B addendum 4 and 5 boxes, all seed 1, AB stage-1 schedule, tok budget 2048, hours=3:
  - claude-sleepb8a-cqc4bi (57552967, A100 SXM4 40GB California, $0.416/h): ab_ob_rot, then ab_ob_ther.
  - claude-sleepb8b-cqc4bi (57552968, A100 SXM4 40GB California, $0.416/h): ab_ob_guess, then ab_ob_twist.
  - claude-sleepb8c-cqc4bi (57552969, A100 SXM4 40GB New York, $0.539/h): ab_ob_b2 (addendum 5, work scale 2).
  - Coordinator OK 18:27Z: $1.50 cap for the four addendum-4 arms. The addendum-5 arm is under $1, which is in the default allowance. Watchers destroy each box after its last arm reports, after 20 min with no progress, or at the cap ($1.50 for 8a+8b, $0.95 for 8c). Vast credit was $6.21 at 18:30Z.
- 19:32Z the watcher destroyed 57552967 (8a) and 57552968 (8b), both California, at 0.36 h, about $0.32. 8b was still loading. 8a had started its job but had not finished a night, probably because of a slow model download; New York's 8c reached night 1 at 0.33 h. New watcher rule (`guard4`): destroy at 20 min only if the job never started, and at 36 min if no night has finished.
- 19:33Z relaunch, staying inside the $1.50 addendum-4 cap ($1.18 left):
  - claude-sleepb9a-cqc4bi (57555316, A100 PCIE 40GB Japan, $0.342/h): ab_ob_rot, then ab_ob_guess.
  - claude-sleepb9b-cqc4bi (57555322, A100 SXM4 40GB New York, $0.539/h): ab_ob_twist.
  - ab_ob_ther waits for more budget. The research note expects it to be close to null.
