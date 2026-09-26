# Disk + credit check — 2026-09-26 (UTC 01:50 task, run ~2026-09-25 21:55 local)

Worktree: /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
Read-only: nothing deleted, rented, or changed outside this PUSH path.
Deviation: OPUS-RULES.txt path given in task does not exist
(/private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt
not found; local scratchpad/ has no briefs/ dir). Proceeded under task's stated key points.

## 1. df
- `df -h /`: /dev/disk3s1s1 460Gi total, 13Gi used, 20Gi avail, 39% capacity.
- `df -h ~` (/System/Volumes/Data): 460Gi total, 390Gi used, 20Gi avail, 96% capacity.
- `df -g /`: 460 1G-blocks, 12 used, 19 available, 39%.
- `uptime`: 2 days 11:45 load; free disk on / ~19-20 GB — above 3 GB stop threshold. No stop needed.
- NOTE: root slice shows 39% while Data volume shows 96% — home data is the full one.

## 2. Sizes (du -sh, largest first; GB one-decimal in brackets)
- ~/premonition-watch: 960M [1.0 GB]
  - outbox: 933M [0.9 GB] (incl. outbox/runs 26M [0.0 GB])
  - queue: 26M [0.0 GB]
  - no `runs` child at top level (absent); other entries: status.txt, watch.log, watcher.sh, watcher.new
- ~/premonition-models: 13G [13.0 GB]
  - rd378-notes-merged 2.0G [2.0 GB]
  - rd371-verifier-merged 2.0G [2.0 GB]
  - own-m1n-mouth 2.0G [2.0 GB]
  - lis319-merged 2.0G [2.0 GB]
  - lis318-merged 2.0G [2.0 GB]
  - lis301-merged 2.0G [2.0 GB]
  - rsn353 470M [0.5 GB]
  - minilm 87M [0.1 GB]
- ~/.local/share/opencode: 129M [0.1 GB]; opencode.db 9.2M [0.0 GB] (9662464 bytes, mtime 2026-09-25 21:54)
- ~/.cache: 4.2G [4.2 GB]
  - uv 2.5G [2.5 GB]
  - codex-runtimes 1.6G [1.6 GB]
  - huggingface 90M [0.1 GB]
  - prisma 39M [0.0 GB]
  - gem 5.4M, opencode 4.7M, vastai 128K, claude 0B
- ~/Library/Caches: 335M [0.3 GB]; top entries:
  - GeoServices 89M, Homebrew 37M, com.apple.python 32M, com.apple.helpd 27M,
    com.apple.VisualIntelligenceCore 18M, com.apple.parsecd 16M, finehero-venvs 11M,
    bun 10M, com.apple.appstoreagent 7.5M, com.apple.CloudTelemetry 7.3M
- worktrees dir: 15G [15.0 GB]
  - card-experiment-handoff-7c5b27 15G [15.0 GB]
  - model-architecture-review-0161ce 327M [0.3 GB]
  - premonition-design-review-792236 16M [0.0 GB]
- /private/tmp/claude-502: 185M [0.2 GB]; top:
  - -Users-ben-hannan-novel-model 167M, bash-edit-diff 17M, -Users-ben-hannan-Desktop-projects-moe 56K,
    plus cache-break-state-*.json files at 8.0K each
- ~/.Trash: NOT READABLE — `Operation not permitted` for both du and ls (1 miss).
- find ~ -xdev -size +500M -mmin -300 (last 5 h), 2 files:
  - /Users/ben-hannan/.codex/thread_history_1.sqlite — 1258029056 bytes = 1.2G [1.2 GB], mtime 2026-09-25 21:26
  - /Users/ben-hannan/premonition-models/rd378-notes-merged/model.safetensors — 2161290944 bytes = 2.0G [2.0 GB], mtime 2026-09-25 21:05

## 3. lis301-merged sha256
- Exists: /Users/ben-hannan/premonition-models/lis301-merged/model.safetensors (2.0G, mode 600, mtime 2026-09-23 15:02)
- sha256: b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890
- MATCHES expected value exactly. (1/1 confirmed.)

## 4. vast credit + instances (key via $(cat ~/.config/vastai/vast_api_key), never printed)
- `vastai show user --raw`: credit = 8.980569333469901 (~$8.98), balance = 0.
- `vastai show instances`: 2 instances total.
  - id 52674739, label rent-382b, running, dph 0.5037037037037037 (~$0.50/hr), 1x RTX 5090, pytorch/pytorch:2.8.0-c...
  - id 52677751, label rent-bm391, running/loading, dph 0.5102962962962964 (~$0.51/hr), 1x RTX 5090, pytorch/pytorch:2.8.0-c...
  - Combined burn ≈ $1.01/hr → ~$8.9 credit ≈ under 9 hours of both running.

## 5. Three folders most likely grown in last 5 hours (mtimes, writers)
1. ~/.codex (mtime 2026-09-25 21:54; du 2.3G) — writer: Codex agent loop. Evidence: thread_history_1.sqlite 1.2G (21:26) + *-wal files at 21:54 (logs_2 4.2M, state_5 4.2M, thread_history 3.8M), logs_2.sqlite 305M (21:50). Largest recent grower.
2. ~/premonition-models/rd378-notes-merged (mtime 2026-09-25 21:06; model.safetensors 2.0G landed 21:05) — writer: model merge/train job (rd378 notes merge). Single 2.0G file appearing inside the 5h window.
3. ~/premonition-watch/queue (mtime 2026-09-25 21:52; 26M) — writer: watcher/dispatcher pipeline. Newest entries: 000-diskcheck-0926.go1.err.txt, 005t-rsn-358a-shared.go1.err.txt, reply .md files (all 21:52–21:54). Outbox/runs also active (rent-dl2 21:51, 006f-bm397-finalize 21:41) but queue has the freshest mtimes.
- Also active but older than these three: ~/.cache/uv (mtime 21:25), ~/.local/share/opencode (19:54).
