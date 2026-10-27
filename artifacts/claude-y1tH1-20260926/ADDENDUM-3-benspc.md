# y1t-H1 ADDENDUM-3: machine only (written 2026-09-26 19:27 UTC, before any y1t-H1 row exists)

y1t moved from a rental to BensPC (38a8fb073, after Ben's 18:42 UTC money message). y1t-H1 rides in the same job:
handoff/held/benspc-y1t.md step 5b runs scripts/claude_y1t_h1run.py for A (the plain MiniCPM5-1B) and B (y1t's
merged model) on the spare panel, and step 6 copies h1/rows_A.jsonl and h1/rows_B.jsonl here under run/.

What changes: the machine (BensPC, RTX 5070 Ti, torch 2.11) instead of "one rental job", and the cost (/bin/bash instead of
about $0.10 to $0.20 of rental GPU). Both arms still run on the same machine, in one job, one run per arm.

What does not change: the panel, the runner and its seal (SEAL-y1tH1-runner.sha256.txt), the scoring adapter, the
judge seed 4013, the judge brief, H1a-H1d, the INCONCLUSIVE rule and the report-only rows.
