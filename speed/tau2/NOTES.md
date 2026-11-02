# tau2 store-test throughput (speed/tau2)
Labels: shown = measured in repo data; suggested = reasoned/vendor, not measured here; untested = needs a box run.
No GPU/network here: nothing below was run on a 5090. Only the retry wrapper has a CPU unit test (`retry/test_retry.py`).

## Where the time goes
Shown (swap/results/summary_5090.jsonl, 80 sims = 40 tasks x 2, CONC=10): tau2 wall 452-744 s/arm; 41-55 s per sim; ~15 agent
turns per sim (1211-1462 assistant msgs / 80), ~2000 agent tokens per sim. So ~3 s per turn, of which the 3.7B/7B
decode is ~1 s. Suggested: the GPU idles ~half of each turn waiting on Haiku, and 10 streams use a small fraction of what
vLLM can batch (Qwen arms are capped at 32 seqs, K2/LFM default is hundreds).
Not in the repo logs (no per-arm startup timestamps): vLLM cold start (poll loop allows 30 min), model download, pip/uv setup.
Estimate (suggested): per arm ~8-12 min tau2 + ~3-8 min serve/download; 8 arms serial.

## Ranking (est. % of whole box time saved; suggested unless noted)
| # | fix | est. saved | changes results? |
|---|---|---|---|
| 1 | Raise tau2 `--max-concurrency` 10 -> 24 (swap CONC, skillsleep EVAL_CONC for A1/A2; A0 keeps 10 because it shares the box with day+fix). tau2 uses a semaphore, no wave barrier. | 20-30% (tau2 phase -40-55%) | No (pure speed) if Haiku does not 429; per-sim latency rises a bit, so ARM_MIN/timeouts are looser, not tighter |
| 2 | Prefetch next arm's weights in background; start first download during `uv pip install vllm`; build tau2 venv in background | 5-10% (skillsleep already overlaps the base download) | No |
| 3 | 429-safe wrapper (`retry/sitecustomize.py`, via PYTHONPATH): Retry-After, full-jitter backoff to 60 s, shared cool-down, 8 tries | removes lost reruns; needed for #1 | Only removes infra-error sims (see below) |
| 4 | Prefix caching check: log "Prefix cache hit rate" per arm (added). tau2 resends system prompt + tools (~5-8k tok) every turn. K2/LFM (dense): V1 default is on (suggested, check log). Qwen3.6/3.8 are hybrid GDN: prefix caching is off or experimental by default (suggested). Try `EXTRA_SERVE=--enable-prefix-caching` on one Qwen arm | 0 to 15% on Qwen arms (untested) | Slightly (cache/kernel path); treat as results-affecting until a 20-sim A/B matches |
| 5 | Skip vLLM restart between nothink/low/medium arms of the same repo (7B x3, 3.7B x2): serve once with reasoning-parser and parse per request | 3-6% | Maybe: parser changes content split. Untested, not patched |
| 6 | Anthropic prompt caching for simulator (`cache_control_injection_points`) | ~0 time; fewer ITPM -> fewer 429s | No. Haiku min cacheable prompt is 2-4k tokens; sim prompt is mostly shorter. Untested, not patched |
| 7 | Already fine: no `--enforce-eager` (CUDA graphs on), chunked prefill default, max-model-len 49152 is generous but costs only KV headroom | - | - |

## 429 handling (shown from code; litellm internals from memory, untested)
- Every Haiku call uses `num_retries: 6` (user sim, judge via patch). litellm's retry is a short random exponential
  (about 1-10 s) and does not read Retry-After; 10-35 sims retry in sync (skillsleep runs day+evalA0+fix = 10+10+15 sims at once).
- When retries run out tau2 ends the sim as an infra error / `too_many_errors` (swap k2_37b_low had 1). swap's
  `summarize.py` counts any such sim as a fail (reward 0) and as a DB mismatch, so 429s bias the pass rate down.
  skillsleep `common.real()` already excludes them from hint selection but `summarize()` still counts them as fails. Check `termination` in summary lines.
- Agent side (`num_retries: 2` to local vLLM) is fine.
- Real cap is Haiku's RPM/ITPM tier, unknown. At CONC=24 expect roughly 2.4x the CONC=10 call rate (~160 -> ~380 req/min, shown/estimated from sim counts).
  If `out/<arm>/speed_retry.log` shows many lines, drop CONC to 16.

## Not patched (needs Ben)
- Vast box cost: serve startup per arm is the biggest unmeasured block. Add `date` stamps around `serve` and the download so the next run measures it.
- Haiku tier: check `anthropic-ratelimit-requests-limit` header once; sets the real CONC ceiling.

## Patches (opt-in; apply from repo root of each branch: `git apply speed/tau2/<name>.patch`)
- skillsleep.patch (branch claude/project-thread-fqdfvg): EVAL_CONC default 24 (A0 stays CONC), retry wrapper in t2.sh, EXTRA_SERVE passthrough, prefix-hit log line, adds skillsleep/retry/.
- swap.patch (branch claude/project-thread-16ok47): CONC 24, prefetch, background tau2 venv, retry wrapper, EXTRA_SERVE, per-arm 429 + prefix-hit counts, adds swap/retry/.
- Both verified with `git apply --check` against the branch files and `bash -n`. The pack must ship `retry/` (vast.py packs the whole dir).
- Revert to old behaviour: CONC=10 EVAL_CONC=10 (env), delete retry/.

## For Ben
The GPU rental sits idle a lot because only 10 conversations run at once and each waits on Haiku to reply. Running ~24 at once
and downloading the next model while the current one is being tested should cut roughly a third to a half of the rented time,
without changing any answers. The risk is Haiku saying "slow down" (429); the retry helper waits politely instead of failing the conversation.

## Qwen3.5/3.6/3.8 on 5090: 17 min/sim (swap-cuda.patch, branch claude/project-thread-16ok47)
Shown (swap/RESULTS.md on that branch): in `pytorch/pytorch:2.9.1-cuda12.8-cudnn9-devel` + vLLM 0.32.0, default bf16/AWQ/NVFP4 Qwen paths die with "No supported CUDA architectures found for major versions [12]" (FlashInfer JIT, nvcc 12.8). Forcing `--moe-backend triton --gdn-prefill-backend triton` serves but ~1000 s/sim (35B); 27B smoke 80 s for 57 tokens.
Shown (code): run_box.sh has no enforce-eager (CUDA graphs on); CONC 10 is under max-num-seqs 32.
- Fix (suggested, untested on a box): image `nvidia/cuda:12.9.1-devel-ubuntu24.04` (nvcc 12.9 present, so FlashInfer JIT for sm_120 can compile); `uv pip install vllm --torch-backend=cu129` (docker hub shows latest/v0.32.0 official images are cu129, so the PyPI cu129 wheel is the matching build); apt python3/ninja/build-essential; then `flashinfer-cubin` and `flashinfer-jit-cache` from flashinfer.ai/whl and /whl/cu129, version pinned to flashinfer-python. Docs do not say jit-cache covers sm_120 (suggested: it probably does not, so nvcc JIT is the real fix and the wheels are a best-effort speedup). `FLASHINFER_CUDA_ARCH_LIST=12.0` limits JIT to the 5090 (suggested; shortens first-start compile, adds minutes once).
- Vast filter `cuda_max_good >= 12.9` (was 12.8). cu129 needs driver >= 575 (suggested; the filter is the proxy).
- Why not `vllm/vllm-openai`: its ENTRYPOINT is vllm serve, and vast_swap.py uses `runtype: args` with `bash -c`, so the job script would be fed to vllm. It would need a runtype/onstart change. cu130 (nvidia/cuda:13.0 + cu130 wheel) is a second option: needs driver R580 (or compat mode); more hosts fail the filter; no gain over 12.9.
- Triton fallback stays via `QWEN_FALLBACK=1` (default off now). Smoke now runs twice and logs seconds, plus backend lines from vllm.log.
- Is 17 min/sim only the kernels? Suggested, partly: 27B dense taking 80 s for 57 tokens is far slower than Triton GDN steady state should be, so Triton JIT/autotune on first calls per new shape (and the cold-start warmup) likely inflates the numbers. The new warm smoke2 time separates this: if smoke2 is still > 5 s, kernels are the problem; if ~1-2 s, it was compile cost. Prefix caching for hybrid models (off by default) would cost prefill only, not minutes. Untested.
- Pass marks (fixed before running): box log shows nvcc 12.9, vllm log shows no "No supported CUDA architectures"; smoke2 for 35B-A3B <= 3 s; tau2 <= 90 s/sim at CONC 10 over the first 10 sims. Wrong if: the arch error persists with nvcc 12.9 (then try cu130 image) or smoke2 stays > 20 s (then not a compile issue; check `--enforce-eager` absent and GDN backend line).
- Verified: patch applies (`git apply --check`) to the branch's run_box.sh/vast_swap.py; `bash -n` and py_compile pass. Not run on a box.
For Ben: the rented computer's compiler was one version too old for the new Qwen speed tricks, so it used a slow backup path. The patch rents a computer image with a newer compiler so the fast path can build itself. Nobody has tested it on a real box yet.
