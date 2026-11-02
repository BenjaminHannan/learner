# speed/: measured speedups for training and runs (thread "Speed up training and runs everywhere", Oct 25 2026)

Goal: cut compute time/cost of our real runs. Every % saved = more training. Land only MEASURED wins; prefer exact-math
changes (same loss/gradients up to float summation order). Approximate changes (fp8, quantized storage that changes values)
need a quality check with pass marks fixed before the run.

Layout: one subdirectory per bottleneck, owned by one worker.
- qwen36_mem/   frozen-base memory for Qwen3.6-35B-A3B sleep (packed 4-bit storage, bigger batches, cheaper GPU)
- qwen36_step/  Qwen3.6 train-step speed (profiling harness, KL-reference cache, packing, kernels)
- mlx/          Ben's Mac: chunked Gated DeltaNet in MLX training, loss-position-only logits for K2's 250k vocab
- dreamgen/     sleep dreaming/generation batching
- tau2/         tau2 store-test throughput (vLLM concurrency, simulator backoff)
- research/     reading notes (Kaggle T4 fp16, 5070 Ti FP8)

Rules for every worker:
- Base code: this branch = the sleep branch (claude/project-thread-cqc4bi) at backbone/sleep/brain/sleepb.py, backbone/train.py.
  Other code lives on other branches; read it with `git show origin/<branch>:<path>`:
  bonsai thread  claude/project-thread-e51zyw (bonsai/chunked_gated_delta.py),
  skill sleep    claude/project-thread-fqdfvg (skillsleep/),
  backbone swap  claude/project-thread-16ok47 (swap/).
- Never edit files outside your own speed/<dir>/. Never touch running jobs, Vast boxes, Ben's PC or Mac. No GPU rentals.
- Don't commit or push; the lead commits.
- New behaviour is opt-in (a flag or a patch file), default off, so running experiments are untouched.
- This container has no GPU and 4 CPUs/15 GB RAM. Test correctness on CPU with tiny configs; write a GPU bench script the lead
  can run later on a rented box, printing before/after in one JSON.
