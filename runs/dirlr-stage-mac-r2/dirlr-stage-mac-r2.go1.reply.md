Staged adaptation sweep — checking prerequisites then launching the 8 dev runs.
Sources are on disk in the main checkout — verifying the staged plugin and environment.
Environment looks thin — sorting the clean checkout and torch install.
No usable torch yet — digging for the baseline setup.
Other jobs are using the machine — checking if staged runs already started.
Lead0 setup is unclear — checking its sources then preparing the staged workspace.
Launch mistyped the output paths — fixing and relaunching.
All 8 staged runs are going with no errors — waiting in one blocking hold.
Stage runs are launched and healthy; this turn ends while they cook. Handoff for the resume agent:

**Where:** `/private/tmp/lead0-main` (origin/main checkout at d734daa6e). All 4 `source.pt` present (copied the 3 missing from the main checkout).

**Running (8 dev adapts, all alive, no Traceback):**
- `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/claude_fewex_eq_bench.py adapt --arm $arm --seed $seed --init $init --plugin claude_dir_lr_stage_net --out artifacts/claude-dir-lr-20260928/stage-runs/$arm-s$seed-$init`, logs `artifacts/claude-dir-lr-20260928/stage-$arm-s$seed-$init.log`, `OMP/MKL/OPENBLAS_NUM_THREADS=1`.
- Status 21:10 EDT (76 min in): loops finished k=1 (~55 min/rung under contention); plains finished k=1, k=4 (~32 min/rung). No `adapt.json` yet. Slower than the 169/120-min estimate — machine shared with Lead0 jobs (likely done soon, freeing cores).

**Next (one tool call):** single blocking wait only —
`while pgrep -f "claude_fewex_eq_bench.py adapt" >/dev/null; do sleep 60; done` (cap <75 min). No short polls. Do NOT relaunch (check `pgrep` first; rerun only after deleting a half-written folder).

**After all 8 `adapt.json` exist:** `python3 -B scripts/claude_dir_lr_stage_report.py dev`, commit `adapt.json` + logs with `git add -f` (NOT `.pt`), then holdout only on PROMOTE verdict. No recipe/mark changes.
