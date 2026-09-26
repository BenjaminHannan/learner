COMMON RULES (the "Fix: reading facts from chat" thread, Claude, wrote this task on 2026-09-26). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply). Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU/MPS). Run Python with: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors python -B <script> ... Run after lis319o-panel-mac has finished (one reader job on the Mac at a time).
DISK: 1 (a ~25 MB code tree in one mktemp dir, removed by exact path at the end). TIME CAP: 20 minutes. $0. Label: lis319f-ch403chk.
DATA: DEV only (2 rows from the everyday-chat DEV chats, readable). No TEST-ONLY panel is touched.

YOUR TASK: read 2 DEV chat turns with both readers, to check a false-save lead from Everyday chat's ch-403.
1. TREE: D=$(mktemp -d); git archive origin/main scripts design/v3/60-listener artifacts/claude-lis319f-20260926/chk_ch403 | tar -x -C $D; cd $D.
   OLD = ~/premonition-models/lis319-merged (model.safetensors sha256 must be e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76)
   NEW = ~/premonition-models/lis319f-merged (must be 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b). Either mismatch: stop with READER-FAIL.
2. python -B scripts/claude_lis319_read.py --model $OLD --rows artifacts/claude-lis319f-20260926/chk_ch403/rows.jsonl --out reads_old.jsonl
3. python -B scripts/claude_lis319_read.py --model $NEW --rows artifacts/claude-lis319f-20260926/chk_ch403/rows.jsonl --out reads_new.jsonl
4. Copy both into artifacts/claude-lis319f-20260926/chk_ch403/ of your worktree, write RESULTS.md there (sha checks, device, and for each row and reader the frame's act, each fact's owner/rel/value/mode and its conf, verbatim; DEV data may be quoted), then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-lis319f-20260926/chk_ch403/RESULTS.md artifacts/claude-lis319f-20260926/chk_ch403/reads_old.jsonl artifacts/claude-lis319f-20260926/chk_ch403/reads_new.jsonl
