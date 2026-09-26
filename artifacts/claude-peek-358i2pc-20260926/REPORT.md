# peek-358i2pc REPORT — read-only progress peek at claude-sleep-358i2pc on BensPC (2026-09-26)

Read-only peek over the usual BensPC ssh (host `benspc`). No process touched, nothing written on BensPC;
only `nvidia-smi`, file reads (`Get-Content`/`Select-String`), and `Get-Date`/`Get-CimInstance` queries were used.
GPU-BUSY.txt ignored per brief.

## 1. nvidia-smi

- GPU 0: NVIDIA GeForce RTX 5070 Ti, Driver 591.86, CUDA 13.1, WDDM, display On
- Fan 35%, Temp 56C, Perf P1, Power 192W / 250W
- Memory: 13199 MiB / 16303 MiB used
- GPU-Util: 93%, Compute M. Default
- GPU compute processes (Type C): 2x `...\Python\Python310\python.exe` (PIDs 5412, 10112)
- Other GPU processes (Type C+G, desktop): dwm.exe, iVCam.exe, Discord.exe, ShellHost.exe,
  OktaVerify.exe, PowerToys.ColorPickerUI.exe, explorer.exe, CrossDeviceResume.exe,
  PowerToys.FancyZones.exe, ApplicationFrameHost.exe
- `Get-CimInstance Win32_Process` (read-only listing, not a touch): 8 python.exe total —
  4 trainers `scripts\claude_rsn358i2_run.py train --arm loop --seed {1..4} --out W\loop-s{1..4}`
  (Python310, no `--steps` override) plus 4 `lis300\venv` python.exe data-side processes.

## 2. Train logs (C:/Users/benja/rsn358i2/W/)

`plain-s*`: NO `train_log.jsonl` present (`Test-Path .../W/plain-s1/train_log.jsonl` = False;
`W/` contains only loop-s1..s4 plus loop-s1..s4.log). 0 plain logs found.

| job | train_log.jsonl lines | last line: step | last line: min | last line: dev |
|---|---|---|---|---|
| loop-s1 | 86 | 43000 | 71.7 | absent (plain eval row) |
| loop-s2 | 81 | 40500 | 70.2 | absent (plain eval row) |
| loop-s3 | 71 | 35500 | 65.5 | absent (plain eval row) |
| loop-s4 | 71 | 35500 | 65.4 | absent (plain eval row) |

Last row carrying a `dev` field per file (dev evals land every 2500 steps):

| job | last dev row: step | last dev row: min | last dev row: dev |
|---|---|---|---|
| loop-s1 | 42500 | 70.7 | {"sums4": 200, "grids5": 200} |
| loop-s2 | 40000 | 69.3 | {"sums4": 200, "grids5": 200} |
| loop-s3 | 35000 | 64.6 | {"sums4": 200, "grids5": 200} |
| loop-s4 | 35000 | 64.5 | {"sums4": 200, "grids5": 199} |

Dev-row counts: loop-s1 17, loop-s2 16, loop-s3 14, loop-s4 14.

Planned total steps: 60000. Source: `scripts/claude_rsn358a_run.py` line 363
`--steps` default 60000 (chain i2 -> 358i -> 358g -> 358a; usage line cites `[--steps 60000]`);
the 4 running launch command lines carry no `--steps` override.

## 3. Clock

- BensPC `[DateTime]::UtcNow`: 2026-09-26 18:44:11 UTC

## Deviations / notes

- `OPUS-RULES.txt` at the briefed scratchpad path did not exist (`scratchpad/briefs/` absent);
  followed the key points as restated in the task instead. No existing file edited or deleted.
- Mac pre-flight: `uptime` load ~62/52/53, `df -g /` 55 GB free (>= 3 GB required). No heavy steps run.
- Integer counts: 4 loop logs read, 0 plain logs present, 47 dev rows total (17+16+14+14),
  2 GPU-compute python processes, 1 ssh host used, 0 writes to BensPC, 0 files edited.
