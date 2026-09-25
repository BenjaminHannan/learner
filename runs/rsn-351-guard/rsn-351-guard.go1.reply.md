Enforcing your $4 guard — starting the watch on rsn-351 spend.
No instances live right now and no exit file yet. Setting up the guard loop.
Ledger format confirmed. Writing the guard script to /tmp (outside the repo, to keep the worktree additive-only).
One live rsn-351 instance just appeared (id 52503394, ~$0.539/h). Checking its exact start time from the API record.
Second instance appeared (tracked=2). Inspecting state.
VERDICT: GUARD-OK — nothing had to be stopped. Combined rsn-351 spend finished at $0.65, far under the $4 cap; the $3.80 trip wire never fired, so I destroyed 0 instances and appended 0 ledger lines.

Marks table (integer counts):

| Mark | Count |
|---|---|
| Polls run (60 s cadence) | 69 |
| rsn-351* instances ever seen | 3 |
| Non-rsn-351 instances touched | 0 |
| Instances destroyed by guard | 0 |
| Ledger lines appended by guard | 0 |
| Times combined total hit $3.80 | 0 |
| TEST-ONLY panels read/tuned/quoted | 0 |

Every move:
- Checked `uptime` (load ~75, noted) and `df -g /` (6 GB free, over the 3 GB floor) before heavy steps; used 1 process at a time.
- Fetched origin main + builder-outbox; read the plan via `git show` (no checkout/merge/push).
- Wrote guard script to /tmp only (repo untouched); launched it 00:08:11 UTC; it polled `vastai show instances --raw` every 60 s, tracking label prefix `rsn-351` by exact id, costing each as dph × hours from its API start_date (frozen at last-seen when it vanished).
- Instance 52503394: dph $0.5389 × 4 min = $0.04. Instance 52503831: dph $0.6056 × 6 min = $0.06. Instance 52504848: dph $0.5511 × 60 min = $0.55. Combined total $0.65.
- First two instances vanished after minutes (bad hosts; builder re-rented) — their costs were kept in the total, per the re-rents-included rule.
- At 01:20 UTC the exit file `runs/rsn-351-train/rsn-351-train.exit` was present on origin/builder-outbox with 0 live rsn-351*; guard stopped itself at 01:22:37 UTC after 5 min quiet (69 polls, 74 min watched, 8-hour cap not reached).
- Verified afterward: guard process exited, no TRIP/DESTROY in its log, `git diff` shows 0 P351-GUARD lines from me (the 36 ledger insertions present are another agent's pre-existing work).

Misses and deviations:
- The OPUS-RULES.txt path in the task does not exist (both scratchpad dirs are empty). Deviation: I followed the rules as restated in the task itself instead.
- My very first `vastai show instances` returned empty, then instance 52503394 appeared seconds later with an API start 5 s after that poll. No cost was lost: I billed from the API start_date, not first-seen time.
- One poll gap ran 99 s instead of 60 s (slow API reply). No poll was skipped; worst-case unobserved spend in that gap is ~$0.02, already covered because billing uses exact start/end timestamps, not poll counts.

What it means in plain English: Ben's $4 limit was never in danger — the job spent about 65 cents total across 3 short-lived rented machines (two died fast and were replaced, which is normal). The training run finished on its own and the guard stood down. What it doesn't mean: this says nothing about whether the training worked or the model is any good — I only watched the money, and I never looked at any test data.

PUSH: artifacts/fable-predictions-ledger.md — no push needed; the guard added no line because there was no GUARD-STOP to record.
