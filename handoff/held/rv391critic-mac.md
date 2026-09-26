COMMON RULES (the thought-memory thread, "Memory for its own thoughts", Claude, wrote this task on 2026-09-26). Additive only, fictional names, no secrets, never write to the repo-root notebook/. Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths). Report in your final reply: each step's outcome first, integer counts, every deviation.
GPU: no (Mac CPU). Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B <script> ...
DISK: 1 (a small code tree in one mktemp dir, removed by exact path at the end; the nets are read in place).
TIME CAP: 90 minutes. $0, no rental, no BensPC. Label: rv391critic.
DUPLICATE GATE: stop with DUPLICATE if origin/main already has artifacts/claude-rv391-20260926/critic/run/.

YOUR TASK: rv-391 dev 2, an unregistered probe (can a small learned critic, reading the frozen loop net's state, tell a page that can no longer be finished from one that can). Training puzzles and practice puzzles only; no test puzzle. Read origin/main:artifacts/claude-rv391-20260926/NOTE-critic-plan.md and the docstring of scripts/claude_rv391_critic.py first. Run the code, never edit it; if something breaks, stop and report the exact error.
1. TREE: D=$(mktemp -d); git archive origin/main scripts artifacts/claude-rv390-20260926/day artifacts/claude-rv391-20260926 artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt | tar -x -C $D; cd $D. Then `shasum -a 256 -c artifacts/claude-rv391-20260926/SEAL-critic.sha256.txt` must show every line OK; otherwise stop.
2. NETS: the four 358i loop nets are at ~/premonition-models/rsn358i/claude-rsn358i-20260926/W/loop-s$s/final.pt (s = 1..4). Each sha256 must equal the W/loop-s$s/final.pt line of artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt. A mismatch or missing file: skip that seed and say which.
   Untrained control: python -B scripts/claude_rv392_randnet.py --out $D/RAND/loop-r0.pt --seed 0 (report its printed line; never push it).
3. RUN, at most 3 at a time (seeds 1-3, then seed 4 and r0), each logging to its own file:
   mkdir -p artifacts/claude-rv391-20260926/critic/run
   python -B scripts/claude_rv391_critic.py probe --ckpt <net> --out artifacts/claude-rv391-20260926/critic/run/critic-s$s.json > artifacts/claude-rv391-20260926/critic/run/log-s$s.txt 2>&1
   (for r0: --ckpt $D/RAND/loop-r0.pt, names critic-r0.json and log-r0.txt). Each writes critic-*.json and critic-*.rows.jsonl. At 85 minutes, stop what is running by exact PID and push what exists.
4. Write artifacts/claude-rv391-20260926/critic/run/SOURCES.txt: each net's path and sha256 as checked, r0's printed line, torch version, minutes per run. Copy artifacts/claude-rv391-20260926/critic/run/ into your worktree, then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-rv391-20260926/critic/run
5. Final reply: which nets ran, and the four printed lines per net (t-grids7, t-grids6, p-grids7, p-grids6) exactly as printed.
