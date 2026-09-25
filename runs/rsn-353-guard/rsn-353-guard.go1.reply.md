Guard on deck — enforcing the $4 combined cap on rsn-353.
The rules file path came up empty — I'll note that deviation and proceed with the guard.
No rsn-353 instances live right now, and no exit file yet. I'll set up the watch loop.
Poll loop is running but the total came out empty — debugging the parse.
Guard died. Patching it to use the working system python and relaunching.
An rsn-353 instance just appeared — guard is tracking it. Checking details.
Third instance vanished ($0.92 frozen, total $1.03). Waiting to see if it's a re-rent or job end.
Guard finished — verifying the end state independently.
VERDICT: GUARD-OK — nothing destroyed, combined spend $1.0323 (cap $4, trip $3.80 never reached). Exit file confirmed, zero instances live. One ledger line appended (PUSH: artifacts/fable-predictions-ledger.md).

Marks table (integer counts):

| Mark | Count |
|---|---|
| Polls of `vastai show instances --raw` (~60 s apart) | 135 |
| rsn-353* instance ids ever seen | 3 |
| Instances destroyed by guard | 0 |
| Non-rsn-353 instances touched | 0 |
| Ledger lines appended by me | 1 |
| Times combined total hit $3.80 | 0 |
| Live rsn-353* at end (independent re-check) | 0 |

Every move:
- 01:43 UTC: `uptime` + `df -g /` OK (39 GB free). Fetched origin/main + origin/builder-outbox. No rsn-353* live (only `lis-317-diag`, not mine to touch), no exit file yet.
- 01:44–01:47 UTC: launched guard script polling every 60 s; it tracked label prefix `rsn-353`, froze each id's cost when it vanished, summed all ids ever seen.
- 02:05 UTC: id 52515551 (`rsn-353`, $0.5389/h) appeared; vanished after 6.32 min = $0.0568.
- 02:11 UTC: id 52516357 (same label/rate) appeared; vanished after 6.29 min = $0.0565.
- 02:18 UTC: id 52517332 ($0.5267/h) appeared; ran 104.71 min = $0.9191, vanished ~04:04 UTC.
- 04:08 UTC: exit file `runs/rsn-353-train/rsn-353-train.exit` present on origin/builder-outbox AND no live rsn-353* for 5+ min → appended the one GUARD-OK ledger line with the $1.0323 total, stopped. Watch lasted ~2.4 h (limit was 8 h).

Instance details (dph × minutes = dollars): 52515551: $0.5389/h × 6.32 min = $0.0568. 52516357: $0.5389/h × 6.29 min = $0.0565. 52517332: $0.5267/h × 104.71 min = $0.9191. Combined: $1.0323.

Deviations (every one):
1. The rules file path in the task did not exist (the /private/tmp scratchpad dir was empty; `scratchpad/briefs/OPUS-RULES.txt` is not on origin/main either). I worked from the key points restated in the task itself.
2. `/usr/local/bin/python3` is a broken x86 binary ("Bad CPU type"), so the guard script used `/usr/bin/python3` for JSON parsing only (no heavy compute, so the torch/uv path was unnecessary).
3. macOS has no `setsid`; used plain `nohup ... &`.
4. First guard launch died on the broken python; ~3 min gap with no polling (01:44–01:47 UTC). Polls just before and after showed no rsn-353* (first one appeared 02:05 UTC), so almost certainly nothing missed, but I cannot prove the gap was empty.
5. Cost start time = earlier of first-seen and vast.ai's own start_date (conservative; over-counts rather than under-counts — here the difference was ~40 s).
6. The ledger already had uncommitted lines from others when I started, and other agents appended after me. My change is exactly 1 line (grep count = 1).

What this means in plain English: Ben's $4 limit was never in danger — the job spent about $1.03 across 3 short-lived machines (two quick ~6-minute tries, then one ~105-minute run that finished on its own). The guard never had to kill anything, and the training job signaled it was done. What it doesn't mean: I did not check whether the training itself worked — only that it stayed under budget.
