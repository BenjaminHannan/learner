# Vast instance listing — 2026-09-26 (read-only)

Listing time (`date -u` at listing): Sat Sep 26 13:33:27 UTC 2026.
The `vastai show instances` table was captured at ~13:33:10 UTC the same day.
No instances were rented, destroyed, or changed. Nothing was read item by item beyond this listing.

## 1. Credit

`vastai show user --raw` → `credit`: **5.742078377269856**

(API key passed via `$(cat ~/.config/vastai/vast_api_key)`; key never printed.)

## 2. Instances

`vastai show instances` summary: **2 instances**, labels `rent-brd8: 1`, `rent-lis-319f: 1`. Both `running`.

| id | label | status (actual_status / cur_state) | dph_total ($/hr) | dph_base ($/hr) | start time (UTC, from start_date epoch) |
|---|---|---|---|---|---|
| 52751954 | rent-lis-319f | running / running | 0.5037037037037037 | 0.4666666666666666 | 2026-09-26T13:17:31Z (epoch 1790428651.9453633) |
| 52752114 | rent-brd8 | running / running | 0.47 | 0.45333333333333337 | 2026-09-26T13:18:27Z (epoch 1790428707.881621) |

Detail notes (raw fields only):
- 52751954 (rent-lis-319f): 1x RTX 5090, image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, uptime_mins 15.47, duration ~952 s.
- 52752114 (rent-brd8): 1x RTX 5090, image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`, uptime_mins null, duration ~896 s.

## Deviations / notes

- The OPUS-RULES.txt file at the briefed path
  `/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt`
  did not exist, and `scratchpad/briefs/` does not exist in this worktree. The in-task rules (additive only, PUSH path only, key never printed) were followed anyway.
- Pre-step checks: `uptime` load ~49–60, `df -g /` showed 57 GB available (well above the 3 GB stop line). `date -u` printed with the listing.
- No other files were created, edited, or deleted. Disk impact of this task: 1 new file (this report) in the PUSH path.
