# STOP depot report — 2026-09-26 (claude-stop-depot-20260926)

Task: STOP (not destroy) the Director's reader depot (created 2026-09-26 19:05 UTC
per task text; spend-cut request). GPU charge ends, disk kept for a small storage fee.

## 1. Readers on the Mac (stopped the depot either way — both verified first)

- `~/premonition-models/lis319f-merged/model.safetensors`
  `shasum -a 256` = `970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b`
  MATCHES expected value exactly.
- `~/premonition-models/lis319-merged/model.safetensors`
  Path: `/Users/ben-hannan/premonition-models/lis319-merged/model.safetensors`
  (exists, 2161290944 bytes, mode 0600; hash not requested, not computed).

## 2. Depot instance (vastai; key via file only, never printed)

- Exactly one instance labelled `claude-director-depot`: id **52755827** (matches expected id).
- Other live instances present and NOT touched:
  52799251 `claude-fixsleep-dl7b` (running),
  52800271 `claude-creativechat-k1f` (running),
  52800405 `claude-sleep-358t3` (loading/stopped).
- Pre-stop state: actual_status `running`, cur_state/intended/next `running`.
- Action: `vastai stop instance 52755827` → exit 0, "stopping instance 52755827."
- Post-stop confirm (`vastai show instance 52755827 --raw`):
  actual_status `exited`, cur_state `stopped`, intended `stopped`, next `stopped`.
  Instance still exists (disk_space 25.0 GB retained) — STOPPED, NOT destroyed.

## 3. Money (from `show instance --raw`)

- start_date 1790430329.56 = 2026-09-26T13:45:29 UTC.
- dph_total $0.11361111111111112/h (dph_base $0.10666666666666667/h).
- Run duration at confirm: 18599.62 s = 5.1666 h.
- Cost so far: 5.1666 h x $0.11361111 = **$0.5870 (~$0.59)**.
- While stopped: gpuCostPerHour $0, totalHour = diskHour **$0.0069444444/h**
  = **$0.1667/day** storage.

## 4. Pre-checks / deviations

- `uptime` load high (~141) but `df -g /` showed 55 GB free (> 3 GB bar); light
  vastai-only steps, proceeded.
- OPUS-RULES.txt not found: the tasked path
  `/private/tmp/claude-502/.../76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/briefs/OPUS-RULES.txt`
  does not exist (that scratchpad dir is empty; worktree has scratchpad/ but no
  briefs/). Proceeded under the key points stated in the task itself
  (additive-only, append-only ledger, no secrets printed). No existing file edited
  or deleted; no other agent's files touched.
- No TEST-ONLY panels involved. No Python run needed (DISK: 0; no local compute).
- Ledger line appended with `cat >> artifacts/fable-predictions-ledger.md`:
  `- 2026-09-26 18:55 UTC depot 52755827 STOPPED (disk kept); 5.17 h x $0.1136 = $0.59; storage $0.1667/day.`
- Push: `artifacts/claude-stop-depot-20260926/REPORT.md artifacts/fable-predictions-ledger.md`.
