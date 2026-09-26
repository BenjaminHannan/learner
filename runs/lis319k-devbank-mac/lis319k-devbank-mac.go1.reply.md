Reading the dev bank with lis-319 — setting up the isolated run.
Setup verified — now running the reader pipeline.
The run hit a missing dependency — verifying the failure before cleaning up.
VERDICT: STOPPED — task could not run. The reading-thread code crashes on import under the exact TREE in step 1. No reads, no classifications, no PUSH files. Label: lis319k-devbank.

MARKS (integer counts):
- teach/correct rows built: 0 (expected 69; never reached)
- facts classified (all): 0
- facts classified (y1 list): 0
- TEST-ONLY panels touched: 0
- worktree files created: 0
- PUSH paths ready: 0 of 4

EVERY MOVE:
1. `git fetch -q origin main builder-outbox` — OK.
2. Read `origin/main:handoff/queue/lis-302-gpu.md` first 13 lines — followed (additive only, fictional names, TEST-ONLY never read, report here).
3. Verified READER `~/premonition-models/lis319-merged/model.safetensors` sha256 = `e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76` — MATCH, else-branch not taken.
4. TREE: `D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.hQSWQLedvX` (mktemp -d); `git archive origin/builder-outbox artifacts/claude-e2e330-dev-20260924/run/arm_G.jsonl | tar -x -C $D` OK; `git archive origin/main scripts artifacts/claude-e2e331-dev-20260924 | tar -x -C $D` OK (~29 MB, 1 dir, DISK OK).
5. SEAL: `(cd artifacts/claude-e2e331-dev-20260924 && shasum -a 256 -c SEAL.sha256.txt)` — all 3 OK (turns.jsonl, truth.jsonl, README.md).
6. Step 2 `rows` with `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors python -B scripts/claude_lis319k_devbank.py rows --run ... --out rows.jsonl` — FAILED on import, script never edited.
7. Cleanup: `rm -rf "$D"` (exact path) — done, `ls` confirms gone. Disk free 54 GB.

EXACT ERROR (verbatim):
```
FileNotFoundError: [Errno 2] No such file or directory: '/private/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.hQSWQLedvX/design/v3/60-listener/relation-names.txt'
```
Full chain: `scripts/claude_lis319k_devbank.py:25` → `import claude_lis300_compiler` → `claude_lis300_compiler.py:23` → `ROOT / "design/v3/60-listener/relation-names.txt"` where `ROOT = Path(__file__).resolve().parents[1]` (= $D). The TREE extracts only `scripts` + the two `artifacts/` paths, so `$D/design/` never exists. The file DOES exist on `origin/main:design/v3/60-listener/relation-names.txt`. No code was edited per instruction, so I stopped.

DEVIATIONS / MISSES:
- Did not run `claude_lis319_read.py` (step 3) or `classify` (step 4) — blocked by the above.
- Did not create `artifacts/claude-lis319k-20260926/devbank/{RESULTS.md,reads_devbank.jsonl,classes_all.json,classes_y1.json}` — nothing to copy; worktree left untouched (additive-only kept).
- Device / median ms / wall time: not recorded (reader never ran; GPU: no, one-job rule never engaged).
- Did not check out or push any branch; watcher has nothing to push for the 4 PUSH paths.

WHAT IT MEANS (plain English): Think of it like a recipe that says "bake the cake" but the ingredient box it tells you to fetch doesn't include flour. The oven (reader hash) is correct and the cake tin seal (SEAL.sha256) is fine, but the script looks for its flour list in a folder the fetch step never downloads, so it quits before doing any work. Fix is for the reading thread to add `design/v3/60-listener/relation-names.txt` (at least that file) to the TREE archives; then the 69-row run can proceed. No DEV data was misread and no TEST panel was touched.
