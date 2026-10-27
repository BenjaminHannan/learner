# C1 CPU repair checks

UTC start (date -u): 2026-09-27 04:23:17 UTC
Machine: MacBook-Pro
Test process PID: 11332
HEAD at start: 57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7
Scope: chat/test_retention_chat.py tiny CPU fixtures only; no MiniCPM or GPU.
No earlier RUN-CODE fingerprint was changed.

First CPU run: 8/9; fixture path alias /var versus /private/var caused one test setup error.
Retry UTC start (date -u): 2026-09-27 04:23:47 UTC
Machine: MacBook-Pro
Retry test process PID: 11974
Retry: normalized temporary root with Path.resolve(); same tiny CPU suite only.

Second CPU retry follows runtime-code verification expansion and one new fixture test.
Retry 2 UTC start (date -u): 2026-09-27 04:24:49 UTC
Machine: MacBook-Pro
Retry 2 test process PID: 12100
Scope: chat/test_retention_chat.py tiny CPU fixtures only; no MiniCPM or GPU.

Final CPU repair suite: 10/10 passed in software-repair-tests-retry2.log.
Corrected runner and tests are uncommitted in this worktree at HEAD 57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7; parent should record the corrected commit hash later.

Targeted full-prefill-logits CPU fixture rerun.
UTC start (date -u): 2026-09-27 04:28:55 UTC
Machine: MacBook-Pro
Test process PID: 13768
HEAD at start: 57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7
Scope: chat/test_retention_chat.py only; no MiniCPM, GPU, or other experiment.

Targeted full-prefill-logits rerun: 10/10 passed; see software-repair-tests-full-prefill.log.
The repaired files remain uncommitted at HEAD 57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7; parent will record the corrected commit hash later.
