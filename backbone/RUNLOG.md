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
- 20:07Z coordinator raised the addendum-4 cap by $0.15 to $1.65, because the relaunched boxes bill above the offer price with storage. The watcher on 57555316 and 57555322 was restarted with $1.33 for those boxes, on top of the $0.32 already spent.
- 22:00Z Sleep-B addendum 6 (Week-2): claude-sleepb10w-cqc4bi (57570310, Japan, ab_ob_win) and claude-sleepb10c-cqc4bi (57570313, UK, ab_ob). Both sat in "loading" for 20 min and were destroyed at 0.36 h (about $0.33). The Japan host had loaded within minutes on two earlier runs. The suspect is the pack, which grew from 1.9 to 2.66 MB of args when the Claude API raw caches (`data/raw_week2`, 2.7 MB) were added, so `vast.py pack` now skips `*/data/raw*`. Coordinator OK 21:59Z: $2.60 for these two arms.
- 22:22Z relaunch with the smaller pack (1.95 MB): claude-sleepb11w-cqc4bi (57572667, A100 PCIE Japan $0.342/h, ab_ob_win, cap $1.40) and claude-sleepb11c-cqc4bi (57572669, A100 SXM4 UK $0.553/h, ab_ob, cap $0.85). Each watcher stops its box, pulls the result JSON and log with `cat` once the box is stopped, then destroys it.
- 23:19Z 57572669 (Week-2 control) finished in 0.95 h. The watcher's API stop was accepted, but the box stayed "running" for 10 min, so `cat` was refused and the box was destroyed with its JSON lost (label numbers only, rv=0001000). The control is being rerun on Ben's PC.
- 00:34Z 57572667 (ab_ob_win) finished at 1.66 h. Its job self-stopped (container key) about 20 min later and the box showed "exited". `cat` then worked on the second try, and result_ab_ob_win.json (909 KB) was pulled before the box was destroyed at 2.06 h. That cost about $0.77. Addendum 6 Vast spend is about $1.74 of the $2.60 cap. Lesson: wait for the job's own self-stop; don't stop from outside.
- 02:07Z claude-sleepb12c-cqc4bi (57595799, RTX 3090 24GB Quebec, $0.144/h, hours=4): Week-2 control ab_ob rerun (seed 1, tok 2048, no schedule), so the addendum-6 W1 test can be paired. Ben (02:03Z): rent only the best deal, so the offer was the top TFLOPS per dollar from tools/vast_pick.py (PR #114 branch) with >= 20 GB VRAM. Expected about 2 h and $0.35. The watcher waits for the job's own self-stop, pulls result_ab_ob.json with `cat`, then destroys; cap $0.70. The PC thread was asked to drop its control rerun.
- 02:25Z 57595799 (Quebec 3090) sat in "loading" for 16 min and was destroyed by hand (about $0.04). Its pack had grown to 2.29 MB of args because the Week-2 result JSONs were in it. `vast.py pack` now skips `results_wk*`, which brings it back to 1.95 MB. Relaunched as claude-sleepb13c-cqc4bi (57597764, RTX 3090 Czechia, $0.156/h, hours=4), packed from a worktree at b1ce3ed322 so the control runs the same sleepb.py as the other addendum-6 arms (before the PR #114 merge). Same watcher and $0.70 cap.
- 02:48Z 57597764 (Czechia 3090) sat in "created" for 20 min, never loading; destroyed (about $0.05). Two cheap 3090 hosts in a row failed to start, so the control moved to claude-sleepb14c-cqc4bi (57599726, RTX 5090 Slovakia, $0.489/h, hours=3), which has nearly the same TFLOPS per dollar (220 vs 226-248) and was running in 2 min. Same addendum-6 code (worktree at b1ce3ed322), cap $1.20. New `vast.py pack --linger 120`: the box stops itself 2 min after DONE instead of 20, because `cat` needs a stopped box anyway.
- 02:52Z Sleep-B addendum 7 (PREREG-sleepB-addendum7.md, code 224e79fa28 = PR #114 trainer + arms commit 3ef9356433), Week-2, seed 1, tok 2048, linger 120, all RTX 5090 so the round runs on one GPU type:
  - claude-sleepb15-ab_ob_b2-cqc4bi (57599951, Slovakia, $0.469/h, hours=3, cap $1.20): reference rerun.
  - claude-sleepb15-ab_ob_b4-cqc4bi (57599956, Slovakia, $0.491/h, hours=4, cap $1.80).
  - claude-sleepb15-ab_ob_tag2-cqc4bi (57599957, British Columbia, $0.544/h, hours=3, cap $1.20).
  - claude-sleepb15-ab_ob_bridge-cqc4bi (57599958, South Korea, $0.544/h, hours=3, cap $1.20).
  Ranked by TFLOPS per dollar with tools/vast_pick.py (>= 20 GB, no China or California hosts); expected about $3 for the round. Watchers pull each JSON after the self-stop, then destroy.
- 03:11Z three of the four addendum-7 boxes never started properly (b2 57599951 and tag2 57599957 stuck in "created"; bridge 57599958 running but no label by 0.36 h) and were destroyed by their watchers (up to about $0.57 at list price). b4 (57599956) ran normally.
- 03:20Z relaunched: claude-sleepb16 b2 (57603194, RTX 5090 Slovakia host 362355, $0.489/h) and tag2 (57603197, RTX 5090 Portugal, $0.563/h), both running in under 3 min; bridge on an RTX 4090 in Iceland (57603198) sat in "created" and was dropped at 0.18 h. The watcher now drops a box that is not running by 10 min (it was 20).
- 03:33Z bridge relaunched as claude-sleepb17 (57604382, RTX 4090 Brazil, $0.344/h, the best TFLOPS per dollar left outside China and the failed hosts). The round now mixes one 4090 into the 5090s; GPU differences are treated like seed noise, as in addendum 6.
- 05:54Z addendum 7 done. b2 rerun (57603194) 0.58 h, tag2 (57603197) 0.58 h, b4 (57599956) 1.09 h, all RTX 5090: JSONs pulled, then destroyed. bridge (57604382, RTX 4090 Brazil) took 1.95 h, 3.6x as long as the 5090s, and its JSON pull failed 4 times ("command output not ready") before the watcher destroyed it; label numbers only. The watcher now keeps a stopped box when a pull fails. Lesson: TFLOPS per dollar did not predict job time on this host. Prefer hosts already proven (Slovakia host 362355 ran three jobs cleanly).
- 06:30Z Sleep-B addendum 8 (PREREG-sleepB-addendum8.md), seed-2 replication, RTX 5090 Slovakia host 362355, linger 120:
  - claude-sleepb18-ab_ob_b4-s2-cqc4bi (57620850, $0.469/h, hours=3, cap $1.30);
  - claude-sleepb18-ab_ob_b2-s2-cqc4bi (57620852, $0.469/h, hours=2, cap $0.80).
  A first launch of both (57620789/57620790) was destroyed at once because `results_a7/` pushed the pack to 2.46 MB; the pack now skips every `sleep/brain/results_*` dir (1.97 MB).
