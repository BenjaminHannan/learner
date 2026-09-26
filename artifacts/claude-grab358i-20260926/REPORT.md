# grab358i REPORT — rsn-358i trained nets saved (2026-09-26)

Grab agent run on Mac worktree `card-experiment-handoff-7c5b27`, read-only against rental.
Instance `rent-358i` (vast id 52757832, 1x RTX 5090, ssh1.vast.ai direct port 57718)
was RUNNING for the whole operation. Nothing on the rental was stopped, written to, or destroyed;
only `find`/`ls`/`stat`/`tail` over ssh plus `scp` reads were used. No new rental was created ($0).

## Poll record (every 3 min, `~/job/W/<seed>/final.pt` sizes in bytes)

- Polls 1–8 (15:01–15:22 UTC): plain-s1..s4 MISSING until poll 2, then stable at 25573143;
  loop-s1..s4 MISSING throughout (loop-s1 at train step ~33000 at 15:00, ~56500 at 15:21).
- Poll 9 (15:25:53 UTC): all 8 present. loop-s{1..4} = 25764244, plain-s{1..4} = 25573143.
- Poll 10 (15:28:56 UTC): all 8 byte-identical to poll 9 → STABLE, copied immediately.
- Instance never disappeared. Total polls used: 10 of 57 allowed (~30 min of 170 min budget).

## Copy

Pre-copy disk check `df -g /`: 54 GB free (>= 6 GB required). Copied with scp to:

`~/premonition-models/rsn358i/claude-rsn358i-20260926/` (run name = rental artifacts dir)

| file | bytes | sha256 vs SEAL-run.sha256.txt |
|---|---|---|
| W/loop-s1/final.pt | 25764244 | OK |
| W/loop-s2/final.pt | 25764244 | OK |
| W/loop-s3/final.pt | 25764244 | OK |
| W/loop-s4/final.pt | 25764244 | OK |
| W/plain-s1/final.pt | 25573143 | OK |
| W/plain-s2/final.pt | 25573143 | OK |
| W/plain-s3/final.pt | 25573143 | OK |
| W/plain-s4/final.pt | 25573143 | OK |

Plus `SEAL-run.sha256.txt` copied from `~/job/artifacts/claude-rsn358i-20260926/` on the rental.
`shasum -a 256 -c SEAL-run.sha256.txt`: 8/8 OK. (Full hashes live in the SEAL file
saved alongside the .pt files; this report states only match/no-match per file.)

Total copied: 9 files (8 .pt + 1 SEAL), 205,509,548 bytes of weights.
The .pt files live OUTSIDE the repo (~/premonition-models) and are NOT pushed.

## Deviations

- `OPUS-RULES.txt` at the briefed scratchpad path did not exist (empty scratchpad dir);
  followed the key points as restated in the task instead. No existing file edited or deleted.
