COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-302-gpu.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time).
TIME CAP: 240 minutes in total. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: e2e-339-style, the REGISTERED run of exp 339 (learns how the user likes to be talked to). Marks: artifacts/claude-style339-20260924/PASSMARKS.md (read it first). The panel artifacts/claude-stylepanel339-20260924 is TEST-ONLY: never open, print or quote its turns; the runner reads it. Run once. The month-end thread wrote all code; never edit it. If something breaks, stop and report the exact error and traceback.

GETTING THE CODE AND MODELS: exactly as in handoff/queue/e2e-330-dev.md (combined tree: builder-outbox, then main on top; self122_head.pt copied in; READER = the lis-301 merged reader with its sha256 check; BASE = openbmb/MiniCPM5-1B via snapshot_download(local_files_only=True); the lis-301 venv).

1. From inside the panel folder: sha256sum -c SEAL.sha256.txt, all OK. Then, BEFORE running, write artifacts/claude-style339-20260924/SEAL-code.sha256.txt = sha256sum of scripts/claude_style339_agent.py scripts/claude_style339_run.py scripts/claude_chat338_agent.py scripts/claude_chat338_run.py scripts/claude_cre333_agent.py scripts/claude_e2e330_arms.py scripts/claude_e2e336_run.py scripts/claude_e2e336_twin.py scripts/claude_age334_agent.py.
2. Run, each as its own process, through the 336 harness (write the paths out in full; PANEL = artifacts/claude-stylepanel339-20260924, OUT = artifacts/claude-style339-20260924/run):
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_chat338_run:build_P --name B --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm claude_style339_run:build_P --name P --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py --bank PANEL --out OUT --arm twin --name T --model BASE
   python -B scripts/claude_style339_run.py --panel PANEL --score OUT
3. P339.4 on the readable DEV bank:
   python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-style339-20260924/dev --arm claude_style339_run:build_P --name P339 --model READER --gen-model BASE
   Then count the rows of dev/arm_P339.jsonl whose reply starts with one of the ACK339 acknowledgements in scripts/claude_style339_agent.py (a short Python count; print the count only).
4. RESULTS-run.md: the printed summary of step 2 with P339.1 and P339.2 marked PASS/FAIL against their bars, the step 3 count with P339.4 PASS/FAIL, GPU name, model commit hash, wall time per arm. Do NOT open the judge_*.jsonl files or quote any panel reply.
PUSH: artifacts/claude-style339-20260924
