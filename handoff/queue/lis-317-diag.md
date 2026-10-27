COMMON RULES (the "Fix: reading facts from chat" thread, Claude, wrote this task on 2026-09-25). Get every file with `git fetch -q origin main builder-outbox` and `git show origin/main:<path>` (your worktree is NOT up to date). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply), and ALL of origin/main:design/v3/30-modes/330-rent-kit.md (code tree, rental rules, setup, independence), with the exceptions below.
GPU: rent
BUDGET: $1.50 for this whole task. Label: lis-317-diag. Needs READER. Does NOT need BASE, MiniLM or self122_head.pt: skip those downloads and the route122 check (this task never builds the agent).

YOUR TASK: lis-317-diag, REPORT ONLY (DEV data, no marks). Plan: origin/main:artifacts/claude-lis317-20260925/PLAN.md. New files only, in artifacts/claude-lis317-20260925/.
1. Build the tree as the kit says (builder-outbox, then main on top). Rent one RTX 5090 (4090 if none). Copy tree + READER.
   Setup: torch with CUDA, then pip install -q "transformers>=5" safetensors accelerate numpy (see RESULTS-rent.md of rent-330-dev on builder-outbox for the torch/torchvision fix if transformers refuses the image's torch).
2. From the tree root (export HF_HUB_OFFLINE=1 PYTHONUTF8=1):
   cd artifacts/claude-e2e331-dev-20260924 && sha256sum -c SEAL.sha256.txt && cd ../..      # 3/3 OK, else stop
   python -B scripts/claude_lis317_sample.py --model READER --rows artifacts/claude-lis317-20260925/rows_e2edev.jsonl --out artifacts/claude-lis317-20260925/reads_e2edev.jsonl --k 8 --temp 1.0
   python -B scripts/claude_lis317_sample.py --model READER --rows artifacts/claude-lis301-20260923/dev/dev_rows.jsonl --out artifacts/claude-lis317-20260925/reads_lis301dev.jsonl --k 8 --temp 1.0 --no-tokens
   python -B scripts/claude_lis317_score.py --rows artifacts/claude-lis317-20260925/rows_e2edev.jsonl --reads artifacts/claude-lis317-20260925/reads_e2edev.jsonl --out artifacts/claude-lis317-20260925/score_e2edev.txt
   Run each under nohup with a log; the sampler resumes from its output file if restarted. Expect about 1 to 3 s per row.
3. Copy the three output files back to the Mac, check line counts (194, 959) and byte sizes, then destroy, confirm, and append the ledger line.
4. RESULTS-rent.md: GPU, hours, dph, dollars, instance id, wall time per step, row counts, file sizes, and score_e2edev.txt pasted verbatim. Dev data may be quoted sparingly.
PUSH: artifacts/claude-lis317-20260925/reads_e2edev.jsonl artifacts/claude-lis317-20260925/reads_lis301dev.jsonl artifacts/claude-lis317-20260925/score_e2edev.txt artifacts/claude-lis317-20260925/RESULTS-rent.md artifacts/fable-predictions-ledger.md
