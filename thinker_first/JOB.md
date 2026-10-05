# JOB: thinker-first Test 1 (layer skip/repeat map), M1 Pro
No training. Branch claude/project-thread-j68k6q, dir thinker_first/.
1. git fetch origin claude/project-thread-j68k6q && git checkout claude/project-thread-j68k6q  (or `git worktree`)
2. pip: torch (mps), transformers>=5, accelerate.
3. cd thinker_first && PYTORCH_ENABLE_MPS_FALLBACK=1 python3 layer_map.py --device mps --dtype bfloat16 --out results 2>&1 | tee run.log
   (33 variants; resumable, skips finished ones; ~1 min each expected; first do `--variants full --limit 48` as a smoke test.
   If mps errors, fall back to --device cpu --dtype float32 --variants ... and tell me.)
4. Expect `full` pooled ~75 (bare 8-shot: fresh 75.0 / R5 67.7 / R6 77.6 pooled over 576). Report if full is far from 75.
5. Commit thinker_first/results/*.json + run.log, push to the same branch. Then reply with one line: done + `full` pooled.
Write C:\\ not needed (Mac only). Also touch nothing on the 5070 Ti.
