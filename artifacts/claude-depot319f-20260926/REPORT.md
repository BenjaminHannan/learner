# READER DEPOT 319f REPORT — claude-director-depot — 2026-09-26

Task: add the lis-319f reader to the depot (director, 15:20 UTC 09-26; Reading facts: lis-319f passed).
Source: `~/premonition-models/lis319f-merged/` on the Mac.
Expected sha256: `970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b`

## Verdict: DEPOT-319f READY (source verified, copy verified, depot left RUNNING, /root/reader319 untouched)

- Depot instance id: **52755827** (label `claude-director-depot`, confirmed RUNNING via read-only `vastai show instance`)
- Depot SSH: **ssh3.vast.ai:35826** (user `root`)
- Depot path: **/root/reader319f/** (6 files, all byte sizes exactly equal to the Mac source)
- Depot sha256 (`/root/reader319f/model.safetensors`): **970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b** — MATCHES Mac source and expected value, 1/1
- Mac source shasum: **970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b** — MATCH, 1/1 (no SRC-MISMATCH)
- `/root/reader319` (the earlier depot copy): **never touched** — read-only listing only; timestamps still Sep 25 20:21 / dir Sep 26 14:12, sizes unchanged
- Transfer: prescribed `rsync` could not run (depot `/usr/bin/rsync` is a **0-byte non-executable stub**, every rsync attempt died with `Permission denied`, exit 126) → fallback `scp` of the same 6 files into the new `/root/reader319f/` dir. Attempt 1 dropped after ~11 min (`Broken pipe`, the anticipated drop); attempt 2 exited 0 after ~32 min. First transfer command 15:20:13 UTC, verified copy 16:06:27 UTC → **~46 min wall**, of which the successful pass took **~32 min**. Retry stayed inside the 3 h budget.
- Depot left **RUNNING** (nothing stopped or destroyed on any instance). This task rented nothing ($0).
- Pre-step checks: `uptime` + `df -g /` done before heavy steps (Mac 54 GB free, above the 3 GB bar). Sequential commands only (never more than 1 parallel process, under the 4-process cap). Key used only via `$(cat ~/.config/vastai/vast_api_key)` inside the vastai call, never printed. No config files printed. No TEST-ONLY panels opened, read, tuned, or quoted (0).

## Depot contents (`/root/reader319f/`, `ls -la`, byte sizes match Mac source 6/6)

- chat_template.jinja (9062 B)
- config.json (749 B)
- generation_config.json (214 B)
- model.safetensors (2161290944 B, sha256 970ef0ac…4f9b)
- tokenizer.json (9894271 B)
- tokenizer_config.json (459 B)

## Marks table (integer counts)

| # | Check | Count |
|---|-------|-------|
| 1 | Mac source `shasum -a 256` runs | 1, match 1/1 |
| 2 | Depot identity confirmations (`vastai show instance`, read-only) | 1, running + label `claude-director-depot` 1/1 |
| 3 | Prescribed `rsync` attempts | 6, success 0/6 (exit 126 every time, 0-byte `/usr/bin/rsync` on depot) |
| 4 | `scp` fallback attempts (same 6 files, new dir only) | 2, success 1/2 (attempt 1 broken pipe ~11 min, attempt 2 exit 0 ~32 min) |
| 5 | Files on depot with exact source byte sizes | 6/6 |
| 6 | Depot `sha256sum` runs | 1, match 1/1 |
| 7 | Writes to `/root/reader319` | 0 |
| 8 | Other instances touched / stopped / destroyed | 0 / 0 / 0 |
| 9 | New bytes staged on the Mac | 0 |
| 10 | TEST-ONLY panels read / tuned / quoted | 0 / 0 / 0 |
| 11 | Misses (sha mismatches, wrong-file copies, wrong-dir writes) | 0 |

## Deviations (2, neither affecting the result)

1. **OPUS-RULES.txt not found**: the brief path (`/private/tmp/claude-502/.../scratchpad/briefs/OPUS-RULES.txt`) does not exist (that scratchpad dir is empty). Worked under the key points quoted in the task itself (additive-only new files, append-only ledger, key hygiene, no secrets, uptime/df checks, integer counts).
2. **rsync → scp fallback**: the depot ships a 0-byte non-executable `/usr/bin/rsync` (dated Sep 26 14:08), so the prescribed rsync command cannot run there (6 attempts, all exit 126, 0 bytes moved). Copied the identical 6 files with `scp` into the new `/root/reader319f/` dir instead (retry-on-drop kept: 1 drop, 1 clean retry, inside 3 h). Chose scp over installing rsync to avoid changing anything else on the instance. The depot-side sha256 match (970ef0ac…4f9b, 1/1) proves the copy is bit-for-bit exact regardless of tool.

## What this means / doesn't mean (plain English)

- The depot now holds a working copy of the agreed lis-319f reader file: the big model file at `/root/reader319f/model.safetensors` on instance 52755827 is bit-for-bit identical to the Mac source (same checksum), so any reader job pointed at `/root/reader319f` reads exactly the agreed facts. The old `/root/reader319` copy was not touched.
- It does NOT mean the file was tested for quality — only that the copy is exact. No test panels were opened and no tuning was done.
- It does NOT mean anything else on vast.ai changed: no other instance was touched, stopped, or destroyed, and this task spent $0 (the depot keeps billing its own $0.1136/hr until someone destroys it, which this task did not do).
