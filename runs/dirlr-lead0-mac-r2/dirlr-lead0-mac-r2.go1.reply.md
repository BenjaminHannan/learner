Lead 0 LR sweep — checking for running jobs and staging inputs.
No Lead 0 run in progress — origin has the marks and script, source nets are local. Setting up the run workspace.
Setup verified (torch 2.14.0, selftest ok). Launching the first batch (practised loop, 3 LRs).
First batch k=1024 done (233 matches stored). k=16384 still running — waiting again with one blocking wait.
Practised loop complete and bit-reproducible (233/261 match stored). Launching the fresh-loop extra batch.
Fresh k=1024 done (3e-4 gives 60, at the rescue bar; 1e-3 reruns stored 0). Waiting for k=16384.
All 12 runs finished. Running the verdict.
Verdict is `LR_MATTERS` on both arms with bit-exact reruns. Committing the 12 result files and 6 logs.
Push is blocked in this environment — committing locally so nothing is lost.
Lead 0 complete. All 12 counts (dev 9x9, seed 1) are in, verdict run, results committed.

**Setup** (`/tmp/lead0-main`, worktree of origin/main): no prior run in progress; marks confirmed sealed on origin/main before any run; `source.pt` copied from the local main checkout; torch 2.14.0 via `uv run` (matches spec); `selftest ok`.

**Practised loop, seed 1** (the required block):
- k=1024: 176 / **233** / 207 (3e-4 / 1e-3 / 3e-3), spread 57 → lr-sensitive
- k=16384: 150 / **261** / 248, spread 111 → lr-sensitive
- 1e-3 rerun matches stored (233, 261) exactly → ruler bit-reproducible on this machine
- Word: **LR_MATTERS**

**Fresh loop, seed 1** (extra, queue was free so kept):
- k=1024: **60** / 0 / 0, spread 60 → sensitive; collapse rescued by 3e-4 at exactly the ≥60 bar (stored 0, rerun 0)
- k=16384: 78 / 24 / 0, spread 78 → sensitive; 1e-3 reruns stored (0, 24) exactly
- Word: **LR_MATTERS**

**After**: `verdict` prints both words above with `rerun_matches_stored: True`. Committed 12 JSONs + 6 logs as `458f8f8e2` on branch `claude/dir-lr-lead0-mac-r2` in `/tmp/lead0-main` (staged with `git add -f` since `artifacts/` is gitignored). **Push was denied by this environment's permissions** — someone with push rights needs to run `git push -u origin claude/dir-lr-lead0-mac-r2` from `/tmp/lead0-main`. No runners left running; marks untouched.

Note: actual runtime was ~105 min per batch of 3 (k=1024 ≈45 min, k=16384 ≈60 min), not the estimated 45.
