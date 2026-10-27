---
name: mac-disk-watcher-hold
description: Mac watcher stops launching every queued task when free disk < 5 GB; what is safe to free on Ben's Mac
metadata:
  type: project
  modified: 2026-09-25T01:36:41.503Z
---
The Mac watcher (handoff/kit/mimo/watcher.sh:56) holds ALL new launches, rentals included, while free disk is under 5 GB. Check origin/builder-outbox status/watcher.txt ("disk N GB free, holding new launches") when a queued task never starts. Seen 2026-09-24 20:50 to 2026-09-25 01:36 UTC (2-3 GB free; 402/460 GB used).

Space on the Mac (Ben's report, 2026-09-25 01:36 UTC): ~/Desktop/projects/polymarket 55 GB (Ben's other project), ~/Desktop/projects/beautiful-model 34 GB (THE PROJECT: never delete), ~/premonition-models 13 GB, ~/.cache/uv 8 GB, ~/Library/Application Support/Claude 12 GB, ~/.local/share opencode 5 GB. The old TO-DELETE staging folder is already gone.

**Why:** Mac jobs run `uv run --offline --with torch`, so `uv cache clean` would break them until re-downloaded.
**How to apply:** suggest `uv cache prune` (unused entries only), never `uv cache clean`; never suggest deleting beautiful-model or premonition-models. Related: [[web-access-environment]].
- Ben 06:54 UTC 09-26: Mac disk space is permanently OUR job ("I'm never doing it again"). Never ask Ben to empty Trash or free space; the Director/watcher does it. Big writer seen: the rent-kit section A tree (1.9 GB + tgz) built on the Mac per task; stage slim trees instead.
