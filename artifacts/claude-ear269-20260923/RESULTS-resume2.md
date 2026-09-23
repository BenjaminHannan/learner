# Exp 269 RESULTS-resume2: cloud-GPU resume attempt (builder, 2026-09-23)

## Result: BLOCKED at the weights gate -- no verdict, no arms run, $0.00 spent

Step 2 of the resume2 brief is a hard gate: the v4.1 ear checkpoint used by
265/269 must come from the Mac, with its sha256 matching the one the sealed
files record, or the run stops as BLOCKED with no retraining. The checkpoint
is not on the Mac, and BensPC (where it lives) is unreachable, so nothing
was rented, no arm ran, and M1-M8 have no numbers. P269.1-P269.7 stay
unresolved, exactly as P269.9 left them.

## Gate evidence (integer counts)

- Seals rechecked from the repo root: ear269 SEAL 15/15 OK, ourpanel269 SEAL
  2/2 OK. No sealed file changed.
- RESULTS-resume.md absent: the earlier 269-resume never ran the arms, so
  this attempt ran nothing twice (it ran nothing at all).
- Required ear checkpoint (sealed in 269 PASSMARKS line 16-17, 265 PASSMARKS,
  261b PASSMARKS, and dev269_earpreds.json ckpt_sha256): v4.1 file
  `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`,
  sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`.
- Only ear checkpoint on the Mac:
  `data/models/smolear235_v3/smolear235.safetensors` (723,673,144 bytes),
  sha256 `2852a5c0d60b2ef361cbf45eb14863b0047b56bd89e65fa90db4479ddf3fd8f8`.
  Prefix `2852a5c0` != required `55284dec`: different checkpoint (v3, not
  v4.1). 0 files on the Mac match the sealed sha. Targeted searches of the
  project trees, Downloads, and Documents found no `out_v41` directory and no
  other `smolear235.safetensors`.
- BensPC reachability: `ssh benspc` times out to 100.75.113.114:22
  (Operation timed out), so the v4.1 file cannot be pulled from BensPC either.
- Qwen GGUF `Qwen3.8-27B-UD-IQ4_XS.gguf` exists on the Mac
  (desmos-llm/bench copy, informational only). No rental was started, so no
  Hive fetch was attempted and no GGUF sha was verified. processor: moot
  without the ear checkpoint.
- vast.ai read-only checks (key used only via shell substitution, never
  printed): GET /users/current/ OK (id 553012, balance 0, credit 6.3927...,
  can_pay true); GET /instances/ lists 0 instances (0 running, so no conflict
  stop needed). No offer was searched, no instance created, no watchdog
  needed, no destroy needed. GET /instances/ confirmed empty at close.
- Machine health before the (unneeded) heavy steps: load ~39.75/53.45/64.43,
  disk 13 GB free (floor 3 GB). No heavy local step was run.

## What ran (every move listed)

- Arm A: 0 runs. Arm A265: 0 runs. Arm A261b: 0 runs. Arm B: 0 runs (its
  single earlier run stands untouched; it was not re-run).
- llama-server: 0 starts (nowhere to run it without a rental; renting without
  the ear weights would bill for an unrunnable wave).
- Scorer: 0 runs (needs apreds + pyes, which need the ear + checker).
- Latency: nothing measured (no hardware ran the pipeline; nothing to report
  even as information).

## Marks M1-M8 (no numbers; 0/100 panel turns scored)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | group_owner: 0 group-owned saves, >= 27/30 ask | no run | none |
| M2 | mixed: >= 12/15 exactly right | no run | none |
| M3 | first_person: 0 lost vs A265 | no run | none |
| M4 | named: 15/15 byte-identical to A265 | no run | none |
| M5 | 0 new wrong vs A261b | no run | none |
| M6 | false asks <= 1 | no run | none |
| M7 | non_owner_we hits lost <= 1 | no run | none |
| M8 | 0 new wrong vs A265 | no run | none |
| ALL | | | BLOCKED (no verdict) |

## Deviations

- D1-D8 from PASSMARKS/RESULTS carry over unchanged.
- D9 (new): resume2 stopped at the step-2 weights gate. No cloud spend, no
  rental, no arm execution, no scorer run. The `runs/rentcheck` recipe named
  in the brief does not exist in this worktree or on origin/main (checked
  worktree, origin/main tree, and scratchpad); the read-only rental checks
  were done with the REST calls recorded in handoff/memory/compute-availability.md
  instead. The vastai CLI is not installed (read-only REST used, as recorded).
- PUSH (artifacts/claude-ear269-20260923 + ledger): not executed as a git
  push -- COMMON RULES forbid commits/pushes and artifacts/ is gitignored.
  New file RESULTS-resume2.md and one appended ledger line (P269.10) are left
  uncommitted in the worktree for the director.

## Dollars

- This attempt spent $0.00 (0 instances, 0.0 hours). Job ceiling ($2.00 /
  3 hours) untouched. Account credit $6.3927, balance $0. $30 lifetime cap
  stands; nothing was quoted against it because nothing billable was started.

## What it means (plain English)

Think of the exam as needing a specific answer key (the v4.1 checkpoint) that
only exists on a computer that is currently offline, and the only copy on
this Mac is last month's answer key (v3) -- close in name, but every page
hashes differently, so the rules forbid swapping it in. Renting a fast
computer in the cloud would just burn Ben's money, because without the right
answer key none of the three remaining test-takers (arms A, A265, A261b) can
even start. So the honest move was to spend nothing and report the roadblock.

## What it doesn't mean

It does not mean the experiment failed: nothing ran, so nothing passed or
failed, and predictions P269.1-P269.7 are still open. It does not mean the
seals broke: both seals verify 15/15 and 2/2, and no sealed file was touched.
It does not mean arm B needs redoing: its one run stays valid and was not
repeated. It does not mean cloud GPUs can't work later: the moment the v4.1
checkpoint (sha 55284dec...) is on a reachable machine, the same resume steps
-- one GPU with 24+ GB on-demand, llama-server with the sealed flags, arms A /
A265 / A261b once each, sealed scorer -- can proceed with no re-seal.
