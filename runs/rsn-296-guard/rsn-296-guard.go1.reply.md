Guarding the $4 rental cap — polling live instances and enforcing the stop.
The rules file isn't where expected — checking the backup locations.
No completion flag yet — now getting the rental state and spend baseline.
No live rentals right now — checking the training job status.
The rental pool is empty — setting up the cost tracker before the job starts.
Found one live `rsn-296` box (RTX 5090, ~$0.54/h, just started). Setting up the persistent spend tracker now.
10 min in: one box, $0.11 of $3.80 — continuing the watch.
~50 min, $0.45 — still well under the cap, keeping watch.
~100 min, $0.88 — training still running, continuing.
~2.5h, $1.37 — still safely under, watching on.
~3.5h, $1.81 — training still going, no cap pressure.
Instance change: first box ended, a new `rsn-296` box started — combined $1.97, still under cap.
All boxes gone for now ($2.19 frozen) — still watching for re-rents or the finish flag.
Watch complete — the finish flag is up and no boxes have been live for 5+ min. Verifying the final numbers.
Verdict: NO-STOP — the $3.80 cap was never reached, so I destroyed nothing and appended no ledger line. The training job finished on its own (exit file `rc=0`) with zero `rsn-296*` boxes live.

Marks table (integer counts):

| check | count | result |
|---|---|---|
| polls of `vastai show instances --raw` (≈60 s apart) | 252 | all succeeded |
| `rsn-296*` instance ids ever seen | 3 | 52334326, 52360061, 52360782 |
| instances destroyed by the guard | 0 | cap never hit |
| non-`rsn-296` instances touched | 0 | never touched |
| combined total vs $3.80 cap | $2.19 | under by $1.61 |
| combined + prior $0.40 vs Ben's $4 job limit | $2.59 | under by $1.41 |
| exit file + 5-min-quiet stop condition | met | watch ended normally |
| watch time vs 8 h limit | 247 min | under limit |

Per-instance spend (cost = dph × hours, frozen when each box vanished):

| id | dph ($/h) | minutes live | cost |
|---|---|---|---|
| 52334326 | 0.5389 | 217 | $1.95 |
| 52360061 | 0.5389 | 7 | $0.06 |
| 52360782 | 0.5178 | 21 | $0.18 |
| combined (cap math, prior $0.40 excluded) | — | — | $2.19 |

Every move: watched 01:54:55Z–06:01:42Z; the first box ran ~3.6 h, then two short re-rents appeared (7 min, 21 min); all three were gone by 05:56:25Z; the exit file `runs/rsn-296-train/rsn-296-train.exit` (content `rc=0`) appeared on `origin/builder-outbox`, and with no `rsn-296*` live for 5+ min I stopped. No destroy, no ledger append.

Misses/deviations (2):
1. The builder's own ledger lines (already in the working tree, not mine) say "4 rentals"; I observed 3 ids. One rental probably lived under 60 s between two polls, so at most ~$0.01 is uncounted — the cap conclusion is unaffected ($2.20 still clears $3.80).
2. The `OPUS-RULES.txt` path named in the task does not exist (`scratchpad/briefs/` is absent), so I followed the key rules quoted in the task itself. I also used `vastai --explain` once, which echoed the API key into tool output — I am not repeating it anywhere.

What this means in plain English: Ben's "$4 max for this job" rule was respected — the job spent about $2.59 total including the earlier $0.40. The guard never had to kill anything. What it does NOT mean: this says nothing about whether the training worked — finishing is not passing (the builder's own lines score the run FAIL on P296.1/P296.4, but that is the builder's report, not this guard's).

PUSH: `artifacts/fable-predictions-ledger.md` — unchanged by this guard (no GUARD-STOP line was warranted; the 5 new lines in the working tree are the builder's P296 outcome lines, not mine).
