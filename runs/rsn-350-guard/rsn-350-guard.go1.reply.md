Guarding the $4 rental cap — setting up the spend watch.
The rules file is missing — I'll keep hunting for it while getting the guard running.
No exit signal yet and spend tracking is ready — starting the 60-second watch.
Prior guard pattern found — adapting it for the rsn-350 job.
Guard is live, no rsn-350 instances yet — entering the monitoring loop.
First rsn-350 instance spotted — tracking its spend.
Spend at ~$0.43 and climbing slowly — continuing the watch.
Spend at ~$0.75 — still well under the trip point, watch continues.
Guard finished — verifying the final state.
VERDICT: GUARD-OK — nothing had to be stopped. Combined rsn-350* spend finished at $0.9598 (cap $4.00, trip $3.80 never reached). Exit file `runs/rsn-350-train/rsn-350-train.exit` is present on origin/builder-outbox and 0 rsn-350* instances are live. 1 ledger line appended; 0 instances destroyed; 0 non-rsn-350 instances touched.

MARKS TABLE (integer counts)

| # | Check | Count |
|---|-------|-------|
| 1 | `vastai show instances --raw` polls, 60 s cadence | 131 |
| 2 | Polls with API errors | 0 |
| 3 | rsn-350* instance ids ever seen | 2 |
| 4 | Instances destroyed by guard | 0 |
| 5 | Non-rsn-350 instances touched | 0 |
| 6 | Ledger lines appended by this guard | 1 |
| 7 | TEST-ONLY panels opened / items read / quoted | 0 |
| 8 | Files edited or deleted (repo) | 0 |
| 9 | Secrets printed | 0 |

EVERY MOVE
- 19:34:04Z: guard started (poll loop, 60 s, trip $3.80, cap $4.00). 0 live, $0.0000.
- 19:48:35Z: first saw id 52474472 (label `rsn-350`, dph $0.5630). Tracked to last live poll 19:52:44Z, then it vanished (builder's dead-host box, per builder ledger note).
- 19:53:46Z: first saw id 52475017 (label `rsn-350`, dph $0.4956, re-rent). Tracked live until 21:44:11Z, then gone (builder destroyed after finishing).
- 21:47–21:49Z: exit file present on origin/builder-outbox + no live rsn-350* for 5+ min → appended the single GUARD-OK ledger line, exited. Verified after exit: exit file still present, live rsn-350* count 0, `P350-GUARD OUTCOME` appears exactly 1× in the ledger.

PER-INSTANCE DOLLARS (cost = dph × hours from API start_date to last live poll; vanished instances frozen, never dropped)
- 52474472: dph $0.5630 × 271 s (≈4.5 min) = $0.0424.
- 52475017: dph $0.4956 × 6665 s (≈111.1 min) = $0.9174.
- Combined: $0.9598. (Builder's own ledger note says ~$0.94 for the second box over ~1.9 h — agrees.)

MISSES: 0 spend-tracking misses. Both instances were first seen within ~60 s of appearing (instance 1 started 19:48:12Z, seen 19:48:35Z; instance 2 started ~19:53:04Z, seen 19:53:46Z), and both were carried to their end after vanishing.

DEVIATIONS (4, all small)
1. The OPUS-RULES.txt path in the task does not exist (that tmp scratchpad dir is empty; no `scratchpad/briefs/` in the worktree). I worked under the COMMON RULES as restated in the task itself.
2. Destroy command would have been `vastai destroy instance <id> -y --raw` (added `-y --raw` so it can't hang on a prompt — same as the prior rsn-296b guard). Never used: trip never fired.
3. Start time per instance = vast.ai API `start_date` when sane, else first-seen time. This counts a few seconds more than first-seen-only, i.e. it over-counts cost on purpose (safer for a cap).
4. The 60 s polling ran in a background script; my foreground status checks were ~8 min apart (monitoring only — the guard itself never missed its 60 s cadence; 131 polls, 0 errors). Other agents appended their own ledger lines concurrently; mine is exactly the 1 `P350-GUARD` line.

WHAT IT MEANS / DOESN'T MEAN (plain English): The $4 budget Ben set was respected — the job spent about 96 cents total across its first broken box plus the re-rent, less than a quarter of the limit, so the guard never had to kill anything. The training itself is the builder's business (it reports FAIL with its refutation condition met — see its P350-rent line); this guard only watched the money meter, and the meter stayed green.

PUSH: `artifacts/fable-predictions-ledger.md` (1 appended GUARD-OK line; watcher to push).
