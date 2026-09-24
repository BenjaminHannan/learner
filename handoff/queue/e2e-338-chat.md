COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-302-gpu.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time).
TIME CAP: 180 minutes in total. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: e2e-338-chat, the REGISTERED run of exp 338 (open conversation). Marks: artifacts/claude-chat338-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-chatpanel338-20260924 is TEST-ONLY: never open, print or quote its items; the runner reads it. Run once. The month-end thread wrote all code; never edit it. If something breaks, stop and report the exact error and traceback.

GETTING THE CODE AND MODELS: exactly as in handoff/queue/e2e-330-dev.md (combined tree: builder-outbox, then main on top; self122_head.pt copied in; READER = the lis-301 merged reader with its sha256 check; BASE = openbmb/MiniCPM5-1B via snapshot_download(local_files_only=True); the lis-301 venv).

1. From inside the panel folder: sha256sum -c SEAL.sha256.txt, all OK. Then, BEFORE running, write artifacts/claude-chat338-20260924/SEAL-code.sha256.txt = sha256sum of scripts/claude_chat338_agent.py scripts/claude_chat338_run.py scripts/claude_cre333_agent.py scripts/claude_e2e330_arms.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py scripts/claude_e2e336_score.py scripts/claude_age334_agent.py.
2. Run, each as its own process (P = --panel artifacts/claude-chatpanel338-20260924, O = --out artifacts/claude-chat338-20260924/run; write them out in full):
   python -B scripts/claude_chat338_run.py P --arm B --model READER --gen-model BASE O
   python -B scripts/claude_chat338_run.py P --arm P --model READER --gen-model BASE O
   python -B scripts/claude_chat338_run.py P --arm T --gen-model BASE O
   python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --score artifacts/claude-chat338-20260924/run
3. Safety check on the readable DEV bank, report only (the same 336 harness as e2e-330-dev):
   python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-chat338-20260924/dev --arm claude_chat338_run:build_P --name P338 --model READER --gen-model BASE
   python -B scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs artifacts/claude-chat338-20260924/dev/arm_P338.jsonl --out artifacts/claude-chat338-20260924/dev/score
4. RESULTS-run.md: the printed summary of step 2 with P338.2 and P338.6 marked PASS/FAIL against their bars (the rest are judged later by the thread), the printed DEV score line of step 3, GPU name, model commit hash, wall time per arm. Do NOT open the judge_*.jsonl or grammar_P.jsonl files or quote any panel reply.
PUSH: artifacts/claude-chat338-20260924
