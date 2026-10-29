# Runtime inspection and deployment scope — 2026-10-29

The expected project directory resolves to `/Users/ben-hannan/Desktop/projects/beautiful-model`, branch `main`, revision `73b8e022421d9161d00703e7dc483cdb05d7374a`. It had 8,680 pre-existing modified tracked paths plus untracked work; it was left unchanged. Full path inventory is retained locally in `/private/tmp/premonition-validation-20261029/original-workspace-state.json`.

Implementation uses an isolated sparse worktree `/Users/ben-hannan/Desktop/projects/premonition-reliability`, based on draft PR 288 head `954084c103fe306c7c7abf00bab41657bcd904e9` (review base `c3288de55f64efc75468e389ab430cbe9d3ad382`). Managed worktree creation could not use the alternate source checkout; a native Git worktree was created without changing the source checkout. No model weights or user diary were copied into Git.

Installed desktop: `/Applications/Premonition.app`, version 1.2.0. Relevant desktop files matched the PR 288 parent source; onboarding lacked the existing PR race fix. The bridge defaults to `~/learner-ops/sleepmode/app`, and its current config explicitly launches `speedbench/venv312/bin/python -m sleepmlx.worker --profile lfm3_mps`, with `PYTHONPATH=~/learner-ops/sleepmlx-src`. The installed trainer checkout identified revision `94d4f4d442b8b2d0ca2147aeddc3cad81971d948`, but the changed trainer files matched reviewed base c3288de except its stricter `HARM_MAX=3.0`.

The actual model profile points at `~/learner-ops/models/lfm3-1.7b-hf`, LiquidAI/LFM3-1.7B, Torch MPS, rank-16 LoRA; PEFT/GGUF output lives under `~/learner-ops/sleepmlx`. There was no running sleep worker during inspection, no accepted adapter or in-progress night directory in that home. Historical log showed an MPS out-of-memory failure followed by a reverted night without held-out cards. These are historical log observations, not a new training run.

The installed legacy scheduler has extra pressure grace, retry, check-in and summary behavior absent from reviewed repository source. Deployment must patch only error routing and deadline handling into it, preserving those additions. The installed 3-point general harm limit must remain explicit via `SLEEPMLX_HARM_MAX=3.0` in worker_env. Profiles, base models, diary, saved memory, feedback and adapters must remain in place.

The stale Codex localhost override is commented out in `~/.codex/config.toml`; shell execution and tests worked after switching the workspace away from its symlinked Downloads path. No Codex configuration was changed.

## Practical limits

These changes address process interruption consistency, QA targets, conservative grading, stale baselines, late legacy feedback clears, desktop deadlines/readiness and draft preservation. They do not establish long-term learning gains, broad retention, removal of already learned memories, exact message lineage, no-new-day reconciliation, full worker cancellation latency, faithful optimizer resumption, or transactional GGUF export and served-check recovery. The generation store currently retains committed nightly generations without garbage collection. No richer replay or SHY recipe was adopted without comparison evidence. Real LFM3 training/export/serving and repeated-night experiments remain unverified; PC GPU memory was occupied, so other workloads were left alone.

## Installed update

Applied 21 code/config files after backing up their original bytes under `/Users/ben-hannan/learner-ops/premonition-reliability-backup-20261029-151313`. The stricter 3-point harm limit is preserved in installed gate code and explicitly in worker_env. The original scheduler additions remain. Premonition was quit and relaunched through native UI; the revised sleep sheet loaded, keyboard Right moved 30 minutes to 1 hour, and the sheet was cancelled without starting a production night. Chats and saved notes were left in place. The local desktop is still version 1.2.0 with this source patch.

The staged installed scheduler passed its 25 local tests and all 6 new worker/deadline regressions. Combining current repository tests with this older installed package produced 3 expectation failures out of152, reproduced unchanged against the original installed code: a fixed Mail timeout string versus parameterized timeout, legacy practice-row capping, and the improved demo-summary wording. These were not changed to hide failures.

Post-install import checks resolved the generation code from the configured installed source and reported grader `strict-3`, harm limit `3.0`. The real tiny-model MPS smoke was repeated against that installed source: two finite LoRA updates, positive replay KL, exact safetensors restoration, and SIGTERM guard/Clock stop passed (1.104 s model work). No LFM3 weights were loaded and no production night was started.
