Timing run G — checking gates and standing by for the GPU.
No duplicate, GPU is mine (dir-g-timing), no Python running. Setting up the BensPC run folder.
Tree extracted. Running SEAL checks.
Selftest ok. Running remaining checks.
All checks pass. Launching both timing runs in one blocking command.
Both runs exited 0. Reading the TIMING lines and dev entries.
All content verified. Writing RUN-NOTE.md.
Verdict: DONE — both 200-step timing runs finished, exit 0, no OOM, no code edited, no test file touched.

Both timing runs finished (seed 13, pool h2, BensPC RTX 5070 Ti, torch 2.11.0+cu128 / CUDA 12.8):
- Run 1 parallel (default): sec/step 0.0978, projected 97.8 min/net, peak 8.84 GB.
- Run 2 serial-streams: sec/step 0.1715, projected 171.5 min/net, peak 2.41 GB.
- D at 200 steps: 1.0 (numbers4practice pick 0 any 0; sums4 and grids5 also D 1.0, all exact 0.0). steps_block_nograd 0, start_norms [22.9, 21.023, 23.552, 20.944], both runs.
- Projected hours for seeds 13+14 two-at-once (2 x min / 60 x 1.0, upper reading): parallel 3.26 h, serial 5.72 h; two at once may be faster.

Checks: selftest ended `selftest ok` ([V2],[V2b],[K4],[eval],[size] all printed); `check-mask ok`; floor `selftest ok`. SEAL: 358u code 8/8, H2 3/3, G 5/5. Memory 16303/1397/14599 MiB before and identical after. GPU-BUSY.txt named this job; left to watcher. Artifacts staged at artifacts/claude-dir-g-build-20260928/timing/ (2 JSONs, 2 logs, RUN-NOTE.md); C:/Users/benja/dirg-timing/ removed, confirmed GONE. No push (watcher pushes).

Every deviation:
1. `date -u` invalid in BensPC PowerShell — UTC times from NTFS LastWriteTimeUtc (par done 10:40:10Z, ser done 10:42:06Z) + log "min" fields.
2. Both logs UTF-16 LE/CRLF (PowerShell `>` encoding), copied byte-for-byte, content intact.
3. No `tail/head/ls -la/wmic` in PowerShell — used native equivalents; sha256sum via Git usr/bin on PATH.
4. git-bash tar path `/c/...` failed chdir; `C:/...` worked (piping call hit Mac-side 120 s timeout but tree extracted fully).
5. Duplicate gate path absent on both branches so ran; note origin/main already has runs/g-s13 and g-s14 with their own timing-par.json (different paths).
6. No OOM, so run 2 was the planned serial timing, not a fallback.
