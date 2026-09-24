COMMON RULES (the listener thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/lis-311-chat292.md (read its first 13 lines and follow them in full: additive only, fictional names, TEST-ONLY panels never read, uv run python, etc.).
GPU: no (Mac CPU/MPS; the reader runs on MPS). Run only after lis-314-panel has finished (one reader job on the Mac at a time).
TIME CAP: 150 minutes in total. macOS has no `timeout`, so run long steps in the background and kill their exact PID if they overrun. If any single turn takes more than 5 minutes, stop and report.

YOUR TASK: REPORT ONLY (no marks). Score the listener stack on the month-end DEV bank (artifacts/claude-e2e331-dev-20260924, dev data, fine to read). Artifacts go in artifacts/claude-lis-e2edev-20260924/. The listener and month-end threads wrote the code. Run it and never edit it.

GETTING THE CODE: build the tree exactly as for lis-313-f0. Start from a fresh `git archive origin/builder-outbox`, overlay a fresh `git archive origin/main` on top, and copy in artifacts/fable-self122-20260922/self122_head.pt from the Mac repo.

1. Check `shasum -a 256 -c artifacts/claude-e2e331-dev-20260924/SEAL.sha256.txt`, the lis301-merged sha256 (b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890), `uptime` and disk.
2. Run three arms, each with --model ~/premonition-models/lis301-merged --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-lis-e2edev-20260924/run:
   python -B scripts/claude_e2e336_run.py --arm claude_lis_e2e_arms:build_C --name lisC ...
   python -B scripts/claude_e2e336_run.py --arm claude_lis_e2e_arms:build_S --name lisS ...
   python -B scripts/claude_e2e336_run.py --arm claude_lis_e2e_arms:build_G --name lisG ...
   Then run scripts/claude_e2e336_score.py over the three outputs, as its docstring says.
3. RESULTS.md: every mechanical count from the scorer for the three arms, plus device and ms (median, p90, max).
PUSH: artifacts/claude-lis-e2edev-20260924
