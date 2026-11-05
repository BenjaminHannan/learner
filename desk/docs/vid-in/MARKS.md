# MARKS: video projector v4 into Glim (vid-in), written 2026-11-05 before any result

Weights: video_projector_v4_FAILED_VID1.safetensors, sha256 64eb2f04734afc0d03c327006174d8ef14a6cc874c877ca11d78baae79bb4de4,
shipped as video_projector_v4.safetensors (same bytes, same hash). PC reference (bf16 torch, 5070 Ti): VID1 57.0 % (shuffled 9.7),
gap 18, VID2 69.0 %, VID3 30.6 %. Ben ruled (2026-11-05 ~07:20) that it ships despite failing its own VID1>=60 / gap<=5 marks.

## M1 parity on this Mac (8-bit MLX Nanbeige `~/learner-ops/models/nanbeige42-3b-mlx-8bit`, MLX SigLIP2 f16, projector f16)
- Test: exactly eval_video.py's VID1 (300 items = 75 four-frame sequences of held-out ReCap shard-25 images, load_holdout(500, seed 1234);
  distractors random.Random(11); prefix "Frame k: "; 10 candidates; summed caption log-prob; top-1). Images and token ids are dumped on
  BensPC from the same code (images saved after the training resize to 256x256 BICUBIC, lossless PNG) and copied here.
- PASS if VID1 top-1 >= 54.0 % AND frame-shuffled VID1 <= 15.0 %. Same-images-alone and the gap are reported, not marks.
- Text parity: 10 fixed text-only prompts, temperature 0, max_tokens 64, through glim_mlx_server (guard) on this Mac.
  A = new server with eyes on and the video projector loaded (unused); B = the currently installed server (image projector only).
  PASS if all 10 replies are byte-identical between A and B.
- If M1 fails: stop, report, ship nothing.
- Wrong if: VID1 < 54 % (the bf16 -> 8-bit gap is real for video) or shuffled within 5 points of true (frames ignored on the Mac).

## M2 fresh check (BensPC 5070 Ti, bf16 torch; same code as eval_video.py VID3 and vlm_yardstick.py VID3)
- Source: MSR-VTT 1k-A TEST split (VLM2Vec/MSR-VTT msrvtt_test_1k.json), shuffled with random.Random(0) as fetch_msrvtt.py,
  SKIPPING every video_id already in the 160-clip VID3 set; the next 300 clips that decode (>= 8 frames). Never in training
  (train used train_7k minus test_1k ids, 0 overlap) and never scored before. 8 evenly spaced frames, JPEG q90, as VID3.
- Note: VID1 is defined on still-image sequences, so "VID1 there" is read as the VID1-style multi-frame top-1 on real clips,
  i.e. VID3 scoring: "Describe this video." caption top-1 of 10 (make_cands(N, 9, seed=3)), summed log-prob.
- Score v4 (bf16, PC) and Qwen3-VL-2B-Instruct (256x256 per frame = 64 tokens, as the yardstick) on the same clips + candidates.
- PASS if v4 top-1 >= Qwen3-VL-2B top-1. v4 frame-shuffled control reported (expect well below v4).
- If M2 fails: ship anyway (Ben's ruling) and say so plainly.

## M3 in the installed app (this Mac first)
- A test clip (fresh MSR-VTT clip not in VID3/M2 training, a clear action) plays on screen; Glim is asked in chat
  "what happened in the last few seconds of this video?". PASS if the answer names the event (main subject + action, judged
  against the clip's human caption, quoted in the report) AND reply <= 15 s from send AND no memory-guard trip
  (no new run/big-exit.json, no guard exit 70/71, no OOM) during the test.
- Reported, not a mark: the same question with the clip part removed (does the answer still name the event?).

## Rules kept
Weights change only in sleep; no online training. The video projector joins sense sleep's list like the image projector if it is a
small change; else what it would take is written down. No weights published.
