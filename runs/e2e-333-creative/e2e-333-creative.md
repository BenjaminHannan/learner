COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-302-gpu.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time).
TIME CAP: 90 minutes in total.

YOUR TASK: e2e-333-creative, the REGISTERED run of exp 333 (creative v1). Marks: artifacts/claude-cre333-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-creativepanel333-20260924 is TEST-ONLY: never open, print or quote its items; the runner reads it. Run once. The month-end thread wrote all code; never edit it. If something breaks, stop and report the exact error.

GETTING THE CODE AND MODELS: exactly as in handoff/queue/e2e-330-dev.md (combined tree builder-outbox + main on top, self122_head.pt copied in, BASE = openbmb/MiniCPM5-1B via snapshot_download(local_files_only=True), the lis-301 venv). No reader is needed.

1. Check from inside the panel folder: sha256sum -c SEAL.sha256.txt, all OK. Also shasum the code: scripts/claude_cre333_agent.py scripts/claude_cre333_run.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py into artifacts/claude-cre333-20260924/SEAL-code.sha256.txt BEFORE running.
2. Run (P = --panel artifacts/claude-creativepanel333-20260924, O = --out artifacts/claude-cre333-20260924/run):
   python -B scripts/claude_cre333_run.py P --arm B O
   python -B scripts/claude_cre333_run.py P --arm P --gen-model BASE O
   python -B scripts/claude_cre333_run.py P --arm T --gen-model BASE O
   python -B scripts/claude_cre333_run.py --panel artifacts/claude-creativepanel333-20260924 --score artifacts/claude-cre333-20260924/run
3. RESULTS-run.md: the printed summary (P333.1, P333.2 with PASS/FAIL against the bars; the rest are judged later by the thread), GPU name, model commit hash, wall time per arm. Do NOT open judge_creative.jsonl or quote replies.
PUSH: artifacts/claude-cre333-20260924
