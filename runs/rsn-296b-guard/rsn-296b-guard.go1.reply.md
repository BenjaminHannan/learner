Guarding the $4 budget — setting up the spend watch.
No matching instances right now. Checking the train exit signal.
Tracking is live. Continuing the watch.
Still steady at ~$0.15. Continuing.
~$0.31 after 34 min. Continuing the watch.
~$0.40 after 45 min, still well under the trip wire. Continuing.
~$0.51 after nearly an hour. Continuing the watch.
Instance vanished from the live list at 10:10:34Z — cost frozen at $0.6054. Watching for the exit file or a re-rent.
Exit file is present. Waiting for the 5-minute no-live window to close.
Guard exited cleanly. Verifying the final state.
VERDICT: GUARD-OK — the $4 combined cap was never threatened; nothing was destroyed by the guard; 1 ledger line appended. PUSH path ready: artifacts/fable-predictions-ledger.md (only file changed).

Marks table (integer counts):

| Mark | Count |
|---|---|
| Polls of `vastai show instances --raw` (every ~60 s) | 71 |
| rsn-296b* instance ids ever seen | 1 |
| rsn-296 instances (label exactly rsn-296, excluded per task) seen | 0 |
| Instances destroyed by guard | 0 |
| Instances touched that were not rsn-296b* | 0 |
| Times the $3.80 trip wire was hit | 0 |
| Ledger lines appended | 1 |
| Missed polls / API errors | 0 |
| Other files created, edited, or deleted | 0 |

Every move:
- Start 09:02:07Z: `uptime` + `df -g /` checked first (58 GB free, over the 3 GB floor). Watcher script written to /tmp only (never into the repo), launched in background polling every 60 s.
- Poll 1 (09:02:08Z): instance 52383936, label exactly `rsn-296b`, dph $0.5388888889/h, status loading — recorded as job instance (it starts with `rsn-296b`; the only exclusion was label exactly `rsn-296`, which never appeared).
- Polls 2–66: same single instance live every time; running total grew ~$0.009/poll.
- 10:10:34Z: instance gone from the live list; its cost frozen at vanish time per the rule (never forgotten after disappearing).
- 10:12:39Z: `runs/rsn-296b-train/rsn-296b-train.exit` confirmed present on origin/builder-outbox.
- 10:14:43Z: no live rsn-296b* instance for 5+ min AND exit file present → appended the single GUARD-OK line to artifacts/fable-predictions-ledger.md, watcher exited. Final verify: 0 live rsn-296b* instances, exit file present, `git status` shows only the ledger modified by me.

Instance dollars (dph × minutes I observed it):
- 52383936 (label rsn-296b, dph $0.5389/h): first seen 09:02:08Z, last seen live 10:09:32Z → 67 minutes × $0.5389/h = $0.6054. Combined total $0.6054, trip wire $3.80 never reached. No stop of anything needed.

Misses and deviations:
- Miss: none on coverage — 71/71 polls succeeded, every live rsn-296b* instance seen was tracked from its first appearance (it was ~1 min old, still loading, so my cost window covers effectively its whole life).
- Deviation 1: the brief's path to OPUS-RULES.txt did not exist (no scratchpad/briefs/ anywhere; the /tmp scratchpad dir was empty). I followed the key rules as restated in the task itself (append-only ledger, additive-only, fictional names n/a, key never printed, 60 s polls, exact-id destroys only, plain-high-school-English report).
- Deviation 2: cost = dph × hours since I first saw it (frozen at vanish), not vast.ai's own billed figure — so $0.6054 is my ceiling-side estimate from first sighting, and the true bill could differ by a minute or two of startup.
- Note: the builder's own RESULTS.md (already on disk, not mine) reports this same run spent ~$0.60 on 1 rental and finished FAIL on the idea-killer — consistent with my $0.6054.

What it means / doesn't mean (plain English): think of it like a babysitter watching a taxi meter with a $4 limit. The taxi drove for about an hour and the meter read only $0.61 when the ride ended by itself — so the babysitter never had to yell stop or grab the wheel. It does NOT mean the training worked (that is the builder's separate FAIL verdict); it only means the money stayed far under Ben's limit.
