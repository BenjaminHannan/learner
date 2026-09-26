Starting your copy-only finaliser — fetching sources and checking shared GPU memory first.
No NVIDIA GPU here — confirming the remaining preconditions before stopping.
Verdict: STOP — wrong host, no GPU run. Ran nothing beyond read-only checks. Edited no file. Created no file. Pushed nothing.

What this task needed:
- BensPC Windows NVIDIA GPU, BASE MiniCPM5-1B rev `87179e5c1f455ef22e6223592d2d61351b525bfc`, DATA = bm-390's BensPC folder holding `locomo10.json`, W = `python -B scripts/claude_winnl2_wrap.py`.

What this host is:
- `Darwin MacBook-Pro.local 27.0.0 ... arm64` (this worktree), not BensPC/Windows. `nvidia-smi` fails:
  - `zsh:1: command not found: nvidia-smi`, exit `127`. No total/used/free to report, so the SHARING pre-check cannot pass. No GPU step started.
- lis-302 line-2 prerequisite missing here:
  - `ls: /private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt: No such file or directory`
- `uptime`: `up 2 days, 11:32, load 32.12 45.23 53.05`. `df /`: `460G total, 12G used, 22G free (37%)` — disk OK, but irrelevant without GPU.

Moves (read-only, integer counts):
- `git fetch -q origin main builder-outbox`: exit 0. `origin/main=df9aa55`, `origin/builder-outbox=6601e1a`. Done: 1.
- `git show origin/main:handoff/queue/lis-302-gpu.md` (first 13 lines + full for context): done, 1. Followed as below.
- `git show origin/main:artifacts/claude-bm397-20260926/PLAN.md` (68 lines): done, 1. Understood TF/E20F copy-only finaliser, marks F1/F2, run-once rule. No benchmark question/answer/reply opened, printed, or quoted: 0.
- `git show` for `SEAL.sha256.txt`, `drafts.sha256.txt`, `RESULTS-benspc3.md` headers: listed only, 3. Did NOT run `sha256sum -c`, did NOT run `selftest`, did NOT copy drafts, did NOT run `claude_bm397_finalize.py run`, did NOT create `RESULTS-run.md` — all blocked by no-GPU STOP + Edit-no-file rule.
- `git ls-tree` checks (no content reads): `origin/main` has `PLAN.md`, `SEAL-judge.sha256.txt`, `SEAL.sha256.txt`, `drafts.sha256.txt`, `scripts/claude_bm397_finalize.py` (5 names); `origin/builder-outbox` has `run2/locomo_T.jsonl` and `run/locomo_E20.jsonl` (2 names). Benchmark row counts: not counted (would require opening files; skipped to stay safe). Done: 2 listings.
- `git status --porcelain`: worktree has pre-existing staged/unstaged entries from other agents; I added/modified/deleted 0 files.

Misses (blocked, integer counts):
- SEAL checks: 0 run (needs BensPC tree of main+builder-outbox).
- Selftest `BM397-SELFTEST PASS 7/7`: 0 run.
- DRAFTS copies: 0.
- GPU `run` (1986 rows each, TF then E20F): 0 runs.
- `RESULTS-run.md`: 0 created (new-file-only rule + Edit-no-file + no data to report).
- DATA `locomo10.json` sha256: 0 reported (DATA lives on BensPC, not here).
- PUSH paths (`run/`, `RESULTS-run.md`): 0 pushed.

Deviations / what broke (exact errors, no patch per instructions):
- No traceback exists because no Python was launched (correct per “if free unknown / wrong host, run nothing”).
- Error 1: `nvidia-smi` → `command not found`, exit 127 (above). Cannot prove free ≥5 GB, so no share-safe launch.
- Error 2: OPUS-RULES path from lis-302 lines 1–13 does not exist on this host (above).
- This is NOT `SHARE-STOP` (free<5GB unproven), NOT `SEAL-MISMATCH` (seals unchecked), NOT `OOM` (no CUDA log). Call it `STOP-NO-GPU-WRONG-HOST`.

lis-302 first-13-lines compliance (as required by this task’s COMMON RULES, reported here):
- Additive only: 0 files created, 0 edited, 0 deleted by me. Sealed/other-agent paths untouched.
- Fictional names only: 0 names written (no new files, no notebook writes).
- No secrets/configs printed: 0.
- Python rule / TEST-ONLY / counts rules: 0 Python runs, 0 panel items opened, 0 benchmark rows quoted.
- `uptime`/`df` checked: done (above). Parallel processes used: 0 heavy.
- Getting-files rule: used only `fetch` + `git show`/`ls-tree`; no checkout/merge/push. Done.
- Independence: benchmark replies never opened. Done.

What it means / doesn’t mean (plain high-school English):
- Means: this Mac cannot do the GPU shortening run. The job is untouched and safe to run on BensPC or inside rent-bm391 where BASE, DATA, W, and `nvidia-smi` exist.
- Doesn’t mean: nothing about bm-397 quality, F1/F2, or the gap. No score changed. No data was trained on. No output exists yet.
