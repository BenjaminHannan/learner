COMMON RULES (the director, Claude, wrote this task on 2026-09-25). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md. REPORT ONLY: change nothing, install nothing, stop nothing.
GPU: yes (BensPC; one job at a time).
TIME CAP: 5 minutes in total.

YOUR TASK: 000-benspc-check. Ben asked for tonight's GPU work to run on his own PC. Check that BensPC is reachable and ready.
1. Run `nvidia-smi` on BensPC and report the exact GPU name, total memory, driver version, and whether any process is using the GPU.
2. Report free disk space on C:.
3. Report whether C:/Users/benja/lis300/venv/Scripts/python.exe runs `import torch; print(torch.cuda.is_available())`.
Final reply: one line per item, then `BENSPC OK` or `BENSPC FAIL: <reason>`.
