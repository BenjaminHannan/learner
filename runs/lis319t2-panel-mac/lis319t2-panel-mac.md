COMMON RULES (the "Fix: reading facts from chat" thread, Claude, wrote this task on 2026-09-26). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply). Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU/MPS; the reader runs on MPS). Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors python -B <script> ... Run only after lis319k-panel-mac AND lis319k-devbank-mac-r2 have finished (one reader job on the Mac at a time).
DISK: 1 (a ~25 MB code tree in one mktemp dir, removed by exact path at the end; the reader is read in place).
TIME CAP: 60 minutes. $0, no rental, no BensPC. Label: lis319t2-panel.
INDEPENDENCE: never open, print or quote artifacts/claude-readpanel319k-20260926/panel.jsonl, label_B.jsonl, adjudication.jsonl or the reads file you write. Scripts print counts only; push the reads file unread. This reader reads the panel exactly ONCE.

YOUR TASK: lis-319t2, one read of the sealed corrections panel with the lis-319f reader. Read origin/main:artifacts/claude-lis319t2-20260926/PASSMARKS.md first. Run the code, never edit it; if something breaks, stop and report the exact error.
1. TREE + SEALS: D=$(mktemp -d); git archive origin/main scripts design/v3/60-listener artifacts/claude-lis319t2-20260926 artifacts/claude-readpanel319k-20260926 | tar -x -C $D; cd $D.
   shasum -a 256 -c artifacts/claude-lis319t2-20260926/SEAL.sha256.txt (all OK); (cd artifacts/claude-readpanel319k-20260926 && shasum -a 256 -c SEAL.sha256.txt) (all OK). Any failure: stop.
   READER = ~/premonition-models/lis319f-merged; shasum -a 256 $READER/model.safetensors must be 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b (else stop with READER-FAIL).
2. python -B scripts/claude_lis319_rows.py --rows artifacts/claude-readpanel319k-20260926/panel.jsonl --out rows.jsonl   (expect rows 240 with history 210)
3. python -B scripts/claude_lis319_read.py --model $READER --rows rows.jsonl --out reads_panel_319f.jsonl   (record the device, median ms, wall time)
4. Copy reads_panel_319f.jsonl into artifacts/claude-lis319t2-20260926/ of your worktree, write artifacts/claude-lis319t2-20260926/RESULTS-read.md (seal checks, reader sha, device, median ms, wall time, printed counts verbatim; "B1-B3 pending judges"), then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-lis319t2-20260926/RESULTS-read.md artifacts/claude-lis319t2-20260926/reads_panel_319f.jsonl
