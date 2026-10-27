COMMON RULES (the thought-memory thread, "Memory for its own thoughts", Claude, wrote this task on 2026-09-26). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths). Report in your final reply: each step's outcome first, integer counts, every deviation.
GPU: no (Mac CPU). Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ...
DISK: 1 (a small code tree in one mktemp dir, removed by exact path at the end; the nets are read in place).
TIME CAP: 60 minutes. $0, no rental, no BensPC. Label: rv391dev.
DUPLICATE GATE: stop with DUPLICATE if origin/main already has artifacts/claude-rv391-20260926/dev/.

YOUR TASK: rv-391 dev, an unregistered measurement on PRACTICE grids only (which signal from the loop net marks a wrong written guess). Read origin/main:artifacts/claude-rv391-20260926/NOTE-dev-plan.md and the docstring of scripts/claude_rv391_dev.py first. Run the code, never edit it; if something breaks, stop and report the exact error.
1. TREE: D=$(mktemp -d); git archive origin/main scripts artifacts/claude-rv390-20260926/day artifacts/claude-rv391-20260926 artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt | tar -x -C $D; cd $D.
2. NETS: for s in 1 2 3 4, `shasum -a 256 ~/premonition-models/rsn358i/loop-s$s/final.pt` must equal the W/loop-s$s/final.pt line of artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt. A mismatch or missing file: skip that seed and say which.
3. RUN, two at a time (seeds 1-2, then 3-4), each logging to its own file:
   mkdir -p artifacts/claude-rv391-20260926/dev
   python -B scripts/claude_rv391_dev.py measure --ckpt ~/premonition-models/rsn358i/loop-s$s/final.pt --out artifacts/claude-rv391-20260926/dev/measure-s$s.json > artifacts/claude-rv391-20260926/dev/log-s$s.txt 2>&1
   Each writes measure-s$s.json and measure-s$s.rows.jsonl. At 55 minutes, stop what is running by exact PID and push what exists.
4. Copy artifacts/claude-rv391-20260926/dev/ into artifacts/claude-rv391-20260926/dev/ of your worktree, then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-rv391-20260926/dev
5. Final reply: which seeds ran, and the two printed lines per seed (p-grids7, p-grids6) exactly as printed.
