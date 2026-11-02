# Speed box: exact commands (lead runs these; label `speed-b0qz6e`)

Plan: 1 PRO 6000 (95 GB, ~$1.20/h), cap $2.00 => stop by ~85 min. Timeline: installs + 67 GB download in parallel (~10 min), then
mem_eager 14 + mem_fused 14 + step 14 (full 40 layers; fallback 16 layers only if it fails, 8 min) + dreamgen 12 = at most ~54 min of benches. Each has its own `timeout`; a failure never stops the next.
Hard limit: script watchdog at 85 min (merges JSON, self-stops); the Vast job wrapper kills the script at 87 min.

`backbone/vast.py` is used through `speed/box/vast_speed.py` (same commands). Differences: runs `speed/box/run_speed_box.sh`; `pack --minutes N` replaces `--hours` (an int there);
`create` has no `--hours` (the time limit is baked in at pack). Not editing backbone/.

```bash
cd /home/user/learner
# 1. pack (code + job script, ~0.5 MB)
python speed/box/vast_speed.py pack --out /tmp/speedbox --label speed-b0qz6e --minutes 92 --linger 240
# 2. find a PRO 6000 offer: >= 90 GB VRAM, >= 150 GB disk (67 GB model + pip), sm_120 needs cuda >= 12.8 (the picker enforces it)
python tools/vast_pick.py --min-vram 90 --disk 150 --max-dph 1.6 --hours 1.5 --n 8
#    pick one whose gpu is RTX PRO 6000 (not H100/A100), down >= 500 Mb/s preferred, usd_h <= ~1.25. Fallback: python speed/box/vast_speed.py search --gpu "RTX PRO 6000 WS" --max-dph 1.5
# 3. rent (disk 150 is required: default 80 is too small)
python speed/box/vast_speed.py create --offer OFFER_ID --args /tmp/speedbox/args.json --label speed-b0qz6e --disk 150
# 4. poll (every few minutes); look for '=== TICK', '-- mem_eager rc=', '=== BB DONE speed'
python speed/box/vast_speed.py status
python speed/box/vast_speed.py logs INSTANCE_ID --show 60
# 5. results: `cat` works once the box has stopped itself (after DONE + 240 s linger, or at the 85-min watchdog)
python speed/box/vast_speed.py cat INSTANCE_ID /job/out/speed_all.json --out speed/box/speed_all.json
python speed/box/vast_speed.py cat INSTANCE_ID /job/out/run_box.log --out speed/box/run_box.log     # optional; also /job/out/{mem_eager,mem_fused,step,dreamgen}.log
# 6. destroy (stops billing for storage)
python speed/box/vast_speed.py destroy INSTANCE_ID
```

If the box has not stopped itself 90 min after create: `vast_speed.py stop INSTANCE_ID`, then cat, then destroy.

## Output: /job/out/speed_all.json
Keys: `status` (rc and seconds per bench), `env` (versions), `mem_eager` (qdq + packed, eager dequant), `mem_fused` (packed + packed_fit, `--compile-dequant`),
`step` (profile_step, 40 layers = full model; `step_fallback` only if that failed), `dreamgen`. Rebuilt after every bench, so a partial run still has everything finished so far.
Read `mem_eager.compare[...].slowdown`, `logits_bitwise_equal_to_qdq`, `mem_fused.modes.packed_fit.fits_5090`; compare fused vs eager packed s/step by hand (qdq reference is only in mem_eager).

## Notes
* Env pinned as in results_a11/moebench_qwen36_rtxpro6000.json (image torch 2.9.1+cu128 / triton 3.5.1; pip: transformers 5.20.2, peft 0.21.2, accelerate 1.15.0, flash-linear-attention 0.6.0, hf hub 2.3.0, hf_xet 1.7.0).
* Model downloaded once at the pinned revision into ~/.cache/huggingface; `refs/main` is pointed at it so profile_step / gpu_bench (which pass no revision) find it; benches then run with HF_HUB_OFFLINE=1.
* Dry runs done locally (CPU): `bench_mem.py --tiny`, `gpu_bench.py --tiny-cpu` ran from an unpacked copy of the pack; `profile_step.py --help` only (no tiny mode; a GPU is required).
* Risks: profile_step `--layers 40` on the full bf16 model plus LoRA/activations is untested at 95 GB (the fallback covers an OOM, but only when no variant row was written);
  packed_fit loads 65 GB onto host RAM (A11 box had 247 GB; a smaller-RAM offer would fail that mode only); dreamgen runs ~10 min at n=64 (estimate).
