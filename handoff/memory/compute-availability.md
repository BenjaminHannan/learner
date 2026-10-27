---
name: compute-availability
description: "Which machines Premonition experiments may use — BensPC RTX 5070 Ti is available again (Ben, 2026-09-19); Mac for small runs; vast.ai only with approval"
metadata: 
  node_type: memory
  type: project
  originSessionId: aa82fa83-15ca-4df2-9694-910b4cc9284b
  modified: 2026-09-19T12:04:12.989Z
---

**2026-09-19: Ben confirmed "you have an rtx 5070-ti"** — the BensPC GPU (RTX 5070 Ti, 16 GB) is available for Premonition work. This supersedes his 2026-09-18 "you can't use the gpu on benspc". The 19 Sep Core pilots already ran on it (4M model ≈ 0.5–0.65M tok/s, 600 s runs; see design/06-step1-pilot-results.md). Plan experiments and judge research-idea feasibility against a free local 5070 Ti, not Mac-only.

- Qwen server on BensPC must be stopped for training (autostart disabled); ops recipe in [[benspc-gpu-ops]].
- The Mac this session runs on is an **Apple M1 Pro, 32 GB, 10 cores**. Project Python with torch: `/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12` (system python3 has no torch). Good for small/toy runs.
- vast.ai costs money ($30 cap, see [[gpu-budget-cap]]): ask Ben with instance type and price before renting; destroy right after. **API key (2026-09-19):** Ben stored it himself at `~/.config/vastai/vast_api_key` (chmod 600, 64 hex chars; the vastai CLI reads it there). Never print, cat into context, copy or write the key; use it only via shell substitution, e.g. `-H "Authorization: Bearer $(cat ~/.config/vastai/vast_api_key)"`. The `vastai` CLI is not installed on the Mac (use the REST API with curl, or ask before installing).
- vast.ai recipe (2026-09-18): RTX 5090 on-demand (~$0.52/h), image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, runtype `ssh_direc ssh_proxy`, attach ~/.ssh/id_ed25519.pub via POST /instances/{id}/ssh/. rsync repo (exclude artifacts, .runtime, .budget, data/village), write `runtime.remote.json` with empty import_roots, run `python -B run.py --runtime runtime.remote.json step1 ...`. 4M core ≈ 1.67M tok/s; whole run ≈ 55 min ≈ $0.48.
- Ben's M3 Pro MacBook (Tailscale 100.93.41.100) never became reachable on 2026-09-18 (tailscaled wedged; fix needs `sudo launchctl kickstart -k system/com.tailscale.tailscaled`).

**Rental recipe that worked (2026-09-19, all instances destroyed the same day, ~$3 spent with Ben's approval up to $3.25):**
- These tiny card models are CPU-launch-bound: pick many fast cores + several GPUs, not a big GPU; DLPerf is a poor guide. Measured: 4x RTX 5060 Ti + 112 vCPU ran 80 twelve-thousand-step runs in ~48 min; 8x RTX 3060 + 80 old Xeon vCPU took ~88 min.
- **Never use bid/interruptible instances for this job:** runs only save at the end, and a bid box was paused 30 min into a wave (whole wave lost). On-demand only.
- **CUDA MPS nearly doubles throughput** (13 procs on one GPU: 465 -> 840 steps per 100 s): `export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps CUDA_MPS_LOG_DIRECTORY=/tmp/nvidia-mps-log; nvidia-cuda-mps-control -d` before launching; ~20 procs per GPU, `--threads 1`. The MPS daemon keeps an ssh session's stdout open, so start things with `setsid nohup ... < /dev/null &`.
- Upload only `scripts/`, `archive/opus-ovn-20260918-235851/`, `artifacts/opus-ovn-20260918-235851/exp1/data` minus `test.pt` (~1 MB). Some hosts take >20 min to pull the image: destroy and pick another.
- Keep both arms of a comparison on the same machine, each arm spread evenly over its GPUs. `pkill -f <pattern>` over ssh kills your own shell if the pattern appears in the command line: use a bracket trick (`launch_al[l].sh`).
- Always save instance ids to memory while they run, verify copied results (count + readable) BEFORE the DELETE call, then confirm `GET /instances/` is empty.

**Why:** the local GPU is free, so the $30 cap only constrains cloud rental.

**How to apply:** prefer BensPC 5070 Ti for anything beyond toy scale; Mac for quick probes; cloud only with explicit approval. Pure PyTorch is safest on the Windows box (custom CUDA/Triton kernels may be awkward).
