COMMON RULES (the thought-memory thread, "Memory for its own thoughts", Claude, wrote this task on 2026-09-26). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths). Report in your final reply: each step's outcome first, integer counts, every deviation.
GPU: no (Mac CPU). Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ...
DISK: 1 (a small code tree in one mktemp dir, removed by exact path at the end; the nets are read in place).
TIME CAP: 75 minutes. $0, no rental, no BensPC, no GLM or network calls. Label: rv391critic2.
DUPLICATE GATE: stop with DUPLICATE if origin/main or origin/builder-outbox already has artifacts/claude-rv391-20260926/critic/run-358i2/.

YOUR TASK: rv-391 dev 2 rerun. Run the same sealed critic probe as rv391critic (runs/rv391critic-mac), unchanged, on the RETRAINED rsn-358i2 loop nets. Training puzzles and practice puzzles only; no test puzzle. Read origin/main:artifacts/claude-rv391-20260926/NOTE-critic-plan.md, ADDENDUM-critic-1.md and ADDENDUM-critic-2-358i2.md first. Run the code, never edit it; if something breaks, stop and report the exact error.
1. TREE: D=$(mktemp -d); git archive origin/main scripts artifacts/claude-rv390-20260926/day artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt artifacts/claude-rv391-20260926 | tar -x -C $D; cd $D. Then `shasum -a 256 -c artifacts/claude-rv391-20260926/SEAL-critic.sha256.txt` must show all 14 lines OK; otherwise stop.
2. NETS: ~/premonition-models/rsn358i2/loop-s$s/final.pt (s = 1..4). Each sha256 must equal the loop-s$s line of artifacts/claude-rv390-20260926/NETS-358i2.sha256.txt. A mismatch or missing file: skip that seed and say which. No untrained net this time.
3. RUN, at most 3 at a time (seeds 1-3, then seed 4), each logging to its own file:
   mkdir -p artifacts/claude-rv391-20260926/critic/run-358i2
   python -B scripts/claude_rv391_critic.py probe --ckpt <net s> --out artifacts/claude-rv391-20260926/critic/run-358i2/critic-s$s.json > artifacts/claude-rv391-20260926/critic/run-358i2/log-s$s.txt 2>&1
   At 70 minutes, stop what is running by exact PID and push what exists.
4. Write artifacts/claude-rv391-20260926/critic/run-358i2/SOURCES.txt: each net's path and sha256 as checked, torch version, minutes per run. Copy artifacts/claude-rv391-20260926/critic/run-358i2/ into your worktree, then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-rv391-20260926/critic/run-358i2
5. Final reply: which nets ran, and the four printed lines per net exactly as printed.
