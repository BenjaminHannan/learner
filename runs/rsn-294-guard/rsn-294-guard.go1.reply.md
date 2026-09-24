Guarding training spend — setting up the $4 cap watch.
The rules file is missing — proceeding with the stated guard protocol.
Live instance `rsn-294c` found (~$0.27 so far, well under cap). Starting the 60s guard loop.
Watch finished cleanly. Verifying the full record before reporting.
VERDICT: WATCH-DONE — no stop needed. 1 instance seen, peak combined $1.50 (cap $3.80), destroyed 0, ledger lines added by me 0.

Marks table (all integer counts):

| mark | count |
|---|---|
| polls run (60 s cadence) | 139 |
| instance-list fetch errors | 0 |
| rsn-294* instance ids ever seen | 1 |
| non-rsn-294 instances touched | 0 |
| destroy commands issued | 0 |
| repo files edited or deleted | 0 |
| ledger lines appended by me | 0 |
| TEST-ONLY panels read / tuned / quoted | 0 |

Every move:
- Start 2026-09-23 21:54:51Z (3 min after Ben's 21:51Z $4 order). Disk 6 GB free (above the 3 GB floor), load high but polling is light. The OPUS-RULES.txt path did not exist (see deviations), so I followed the rules as restated in the task.
- Poll 1 found 1 live box: id 52300816, label rsn-294c, dph_total 0.5388889, already running 1811 s → started 21:24:39Z (later confirmed exact by the builder's own ledger line).
- Polls 1–134 (21:54Z–00:12Z): only that box, combined cost climbing $0.27 → $1.50. Exit file absent. No other rsn-294* id ever appeared; the account held no other instances.
- Poll 135 (00:13:14Z): box gone (builder destroyed 00:12:37Z per their ledger line). Cost frozen at $1.5048.
- Poll 137 (00:15:19Z): runs/rsn-294-train3/rsn-294-train3.exit present on origin/builder-outbox.
- Poll 139 (00:17:22Z): exit present AND zero rsn-294* live for 5+ min → stopped per rule. Final confirmation now: 0 live, exit present.

Instance record: id 52300816 (rsn-294c) — dph 0.5388889, alive 168 min (21:24:39Z–00:12:37Z), cost $1.50 by the task rule (dph_total × hours). Combined total $1.50, never reached $3.80, so nothing was destroyed and no GUARD-STOP line was written. Prior $0.40 excluded from the cap per the rule; with it the report total is $1.90 vs Ben's $4 limit.

Misses / deviations (4):
1. OPUS-RULES.txt was not at the given /private/tmp path (that session dir had no scratchpad/briefs). Followed the key points as restated in the task: additive-only, ledger append-only, no TEST-ONLY reads.
2. The train3 exit file did not exist when the watch began (only train/train2); it appeared mid-watch and the stop rule handled it.
3. `git status` shows the ledger modified (8 insertions) — that is the builder's concurrent train3 outcome lines, not mine. Grep confirms 0 GUARD-STOP lines; my script never opened the ledger. My repo file changes: 0.
4. Cost basis note: I used dph_total ($0.5389/h → $1.50) exactly per the task rule; the builder's own ledger line uses $0.4727/h (→ ~$1.32, disk excluded). Both are well under the $3.80 trip and the $4 combined limit, so the difference changes nothing.

What it means in plain English: the third training try ran on one rented graphics card for about 2 hours 48 minutes, cost about $1.50 of the $4 allowance, finished and shut itself down, and the builder posted its results. The spending guard watched the whole time, never had to pull the plug, and changed nothing. PUSH: artifacts/fable-predictions-ledger.md — nothing to push, I wrote no lines to it.
