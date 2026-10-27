COMMON RULES (the month-end thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-302-gpu.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, uv run python on the Mac, uptime/df checks, report in your final reply).
GPU: yes (BensPC RTX 5070 Ti; one job at a time).
TIME CAP: 150 minutes in total. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: e2e-330-dev, REPORT ONLY (dev data, no registered marks). A dress rehearsal of the month-end end-to-end test on the readable DEV bank, with the real lis-301 reader, on BensPC. Artifacts go in artifacts/claude-e2e330-dev-20260924/. The month-end thread wrote all code. Run it and never edit it. If something breaks, stop and report the exact error and traceback.

GETTING THE CODE: build a combined tree the way lis-313-f0 does: a fresh `git archive origin/builder-outbox`, then a fresh `git archive origin/main` on top (main wins). Copy artifacts/fable-self122-20260922/self122_head.pt from the Mac repo into the same path in that tree (292t needs it). Copy the tree to BensPC and run from its root.
MODELS on BensPC (never download a model other than these):
- READER = the lis-301 merged reader, C:/Users/benja/lis301/work/run/merged (safetensors sha256 must be b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890).
- BASE = openbmb/MiniCPM5-1B (Ben's yes 2026-09-23 11:01 UTC covers it). Find it with huggingface_hub.snapshot_download("openbmb/MiniCPM5-1B", local_files_only=True); only if that fails, download it once with snapshot_download. Record the commit hash.
Use the lis-301 venv (torch + transformers already there); if `import transformers` fails, pip install transformers into it and say so.

READ FIRST: design/v3/30-modes/331-e2e-bank-spec.md, artifacts/claude-e2e336-20260924/PASSMARKS.md, scripts/claude_e2e336_run.py, scripts/claude_e2e330_arms.py. The DEV bank is artifacts/claude-e2e331-dev-20260924 (dev data: fine to read).

1. Check: `sha256sum -c` (or shasum -a 256 -c) of artifacts/claude-e2e331-dev-20260924/SEAL.sha256.txt from inside that folder: all OK.
2. Run these five arms, one after another, each as its own process (B = --bank artifacts/claude-e2e331-dev-20260924, O = --out artifacts/claude-e2e330-dev-20260924/run):
   python -B scripts/claude_e2e336_run.py B O --arm claude_lis_e2e_arms:build_G --name G --model READER
   python -B scripts/claude_e2e336_run.py B O --arm claude_e2e330_arms:build_330a --name 330a --model READER
   python -B scripts/claude_e2e336_run.py B O --arm claude_e2e330_arms:build_330a_334 --name 330a_334 --model READER
   python -B scripts/claude_e2e336_run.py B O --arm claude_e2e330_arms:build_330a_cre --name 330a_cre --model READER --gen-model BASE
   python -B scripts/claude_e2e336_run.py B O --arm twin --name twin --model BASE
   (write --bank/--out explicitly; B and O above are shorthand).
3. Score: python -B scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs artifacts/claude-e2e330-dev-20260924/run/arm_*.jsonl --out artifacts/claude-e2e330-dev-20260924/score
4. RESULTS-dev.md, counts only: the scorer's printed line for every arm (asks per class and per ask_type, facts_saved/facts_total, new triples and owner/value-unsupported new triples, nosave turns with writes, clarify replies, most common reply count, confirm rows, ms median/p90, creative turns and writes, day-1 facts kept); GPU name; model commit hash; wall time per arm. Also list, for arm 330a_cre only, every new triple the scorer marks owner_value_supported=false as "triple <- nearest truth fact" (triples and truth facts only). Dev data may be quoted sparingly.
PUSH: artifacts/claude-e2e330-dev-20260924
