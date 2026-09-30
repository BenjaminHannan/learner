# capability256 final launch verification

Shown: independent read-only SSH audit on BensPC, 2026-09-30T22:23:26.547692+00:00. No model was loaded and no optimizer or evaluation was executed. The audit used Python's standard library, excluding its own process lineage from the worker check. No capability worker or active lock was found. The old Mac Claude session was sleeping with no child worker or open worktree output file; it was left alone.

| Arm | Runner UTC, 2026-09-30 | First update detected UTC | Previous exit → runner start (s) | Runner start → first update detected (s) | Updates / recount | Full checkpoint SHA256 | Launcher commit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s0-loop | 21:07:01–21:20:46 | 21:08:04 | — | 62.256 | 5120 / pass | `82a8a854daeeb9873ac108a9da980567141a34ce193eb86670369255aa57ce93` | `02dce3b` |
| s0-plain | 21:21:00–21:38:35 | 21:22:02 | 14.200 | 62.286 | 5120 / pass | `b7ebc82a90edccd6cfb6ec2fe911e50b4fb2c129f12128b4d5453b8d4b9c1030` | `35c5754` |
| s1-loop | 21:38:36–21:52:08 | 21:39:36 | 1.012 | 60.277 | 5120 / pass | `00d7f53a28dfdc066f0d6d6f2c71c8474ae498c517cd98e31b5e317d67a835c3` | `35c5754` |
| s1-plain | 21:52:09–22:09:22 | 21:53:10 | 0.785 | 60.296 | 5120 / pass | `5bc11a8d8c04ba3c7a273f4674d5197e6d23efd6275428b70095a1fb41b195bf` | `35c5754` |

Each full SHA256 matches both EXIT.json and the nested CLOSED.json checkpoint hash. All four exits are 0 and all four CLOSED.json records have closed=true and optimizer_updates=5120. TRAIN-RAW SHA256 matches CLOSED.json. Recount checks parse JSON, require exact update sequence 1..5120, matching job/seed/arm, numeric-answer-CE-only objective, zero auxiliary weight, sequential visit_for_row counters, and 256 distinct rows with 20 visits each, matching CLOSED.json visits. No questions, labels, evaluation rows, or reserved panels were displayed or inspected.

Count semantics: the hash-matched sealed runner writes one TRAIN-RAW record after numeric_optimizer_step calls optimizer.step and CUDA synchronization completes (scripts/sol_cloud_capability256_v1.py, train loop). This is evidence of completed optimizer updates rather than an arbitrary line count. The runner, PLAN-v3, SEAL-v9 and RELEASE-v4 bytes on the PC match the r4 request pins. All 62 PC receipt files match their Mac copies byte for byte; FINAL-VERIFICATION.json includes the full receipt hash map. verify_final_receipts.py preserves the audit source. Secret-pattern review found no credentials in artifacts/cap256-launch; receipt command lines and paths were also reviewed.

## Lock review and validation

DRIVER_MARK now matches pc_driver.py in the real launch-cap256\pkg\<commit> path. pid_alive_driver consequently recognizes the live lock holder, and acquire_lock waits instead of moving its lock to LOCK.stale. The guard allows waiting driver processes but still blocks duplicate capability runners, owned/model-server GPU holders, and GPU memory >=3000 MiB. Unrelated reminder/Manim processes stay allowed. Lock creation is exclusive; release checks the holder PID.

All 17 tests pass on final files. The live-holder regression now enters acquire_lock with an existing live holder, intercepts the 15-second wait, and proves the original lock bytes remain intact with no stale-lock rename. The suite also exercises ownership, duplicate runner blocking, GPU guard rules, preserving existing arm output, durable receipts and stopping after a failed arm. Focused code/document whitespace checks pass. PC receipt CRLF bytes are preserved; Git’s default whole-diff whitespace check flags those carriage returns. No native Windows queue concurrency was launched. PID/command-line checks retain existing PID-reuse and simultaneous stale-lock-reclaimer limitations; this narrow fix does not redesign the lock.

## Failed attempts and evidence limits

- r4 old resource gate: R4-ROOT-CAUSE.md records a zero-update failure because NVIDIA printed [N/A] rather than N/A for desktop GPU clients. The historical 20-sample replay is prior evidence, not repeated by this audit.
- 20260930T210454Z: preserved EXIT/stderr show a zero-update ImportError from base Python's incompatible hub/transformers environment. The existing PYTHONPATH fix uses the lis300 venv packages; prior zero-update output was moved with a manifest, not deleted. This audit made no remote changes.
- 20260930T210840Z: preserved guard/STATE show it blocked beside the live s0-loop runner after the old driver mark wrongly classified the lock as stale. No runner was invoked for that attempt.

First-update times are detection receipts at a 2-second polling interval, already showing 5–13 records when observed. They are not exact timestamps of optimizer.step. Previous exit → runner start gaps are not previous exit → optimizer update gaps; the first detected update follows a further ~60–62 seconds. The internal batch STATE idle field uses the driver's post-receipt timestamp for later arms; the table recomputes the interval directly from EXIT timestamps. Training completion does not establish accuracy, transfer, recurrent advantage, or general assistant capability. Evaluation remains untested.

## Proposed evaluation — separate Ben approval required

Preserve r4 / SEAL-v9 / RELEASE-v4 and PLAN-v3 / PROTOCOL-v3 unchanged. Freeze all four final hashes and the sealed comparators before any fresh model call; run one terminal evaluation phase for recurrent and plain arms at seeds 0 and 1. Keep 4 fixed loops/segments, 20 training visits, 256 TRAIN, 64 seen-family, 64 structural, and 32 range rows. Use the sealed strict numeric target plus actually observed EOS exact scoring, identical for plain. Generate first and then perform the sealed verified-label join; no adaptive selection or protocol edits.

PLAN-v3.marks and PROTOCOL-v3.approved_marks agree: TRAIN >=244/256, seen >=52/64, structural >=52/64, range >=26/32, in both recurrent seeds. A TRAIN miss indicates underfit; TRAIN passing with a fresh-slice miss indicates transfer failure. A miss in either recurrent seed fails the sealed capability gate. Plain must receive identical scoring; passing thresholds alone does not show recurrent advantage. Keep card/village experiments separate. This is a proposal only; evaluation must wait for Ben's separate approval.
