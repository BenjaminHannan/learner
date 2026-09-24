Starting your rental task — verifying setup and budget before launch.
Your pre-flight checks pass — now configuring the rented GPU.
Reader and model checksums verified — now building the rental package.
Found a cost-effective GPU option — now securing the rental.
Rental secured — now waiting for it to boot.
GPU is ready with PyTorch — now uploading your experiment files.
Upload interrupted midway — now resuming the transfer.
Environment setup complete — now running the registered experiment.
First test arm is running well — monitoring progress.
First arm nearly finished — continuing the run.
Second arm complete — launching the final test arm.
Final arm underway — tracking remaining progress.
All three arms finished — now scoring the results.
Panel scoring shows clear results — now running the control validation.
Control run finished — now verifying the final count.
Results safely back on your Mac — now finalizing the report.
Report drafted — now cleaning up the rental.
Cleanup verified — doing a final check of deliverables.
Verdict: REGISTERED run completed on rented Linux GPU — P339.1 FAIL, P339.2 FAIL (proved wrong), P339.4 PASS. Not DUPLICATE, not BUDGET-STOP, not HOST-FAIL.

Marks table (integer counts):

| Mark | Bar | Result |
|---|---|---|
| P339.1 feedback lives with exactly the right preference saved, nothing else | ≥ 32/40 | 17/40 FAIL |
| P339.2 control lives with any preference saved | 0/20 | 2/20 FAIL (proved wrong: >1) |
| P339.3 day-3 replies following preference | ≥ 80% (proved wrong if <60%) | not judged here (judge_*.jsonl never opened) |
| P339.4 preferences saved on DEV bank | 0 | 0 PASS |

Every move / miss:
- Panel seal: 4/4 OK (turns, truth, lives, README). Never opened panel items, never quoted a reply.
- SEAL-code-rent: 11/11 hashed before running.
- Arm B (claude_chat338_run:build_P): 854 rows, 60 lives, wall ~13:07–13:22 UTC (~15 min). Done.
- Arm P (claude_style339_run:build_P): 852 rows, 60 lives, wall 13:23:43–13:38:24 UTC (881 s). Done.
- Arm T (twin): 768 rows, 60 lives, wall 13:39:48–13:57:36 UTC (1068 s). Done.
- Scorer: summary 17/40 exact, 23/40 nothing saved, 0/40 extra-or-wrong, controls 2/20, saved_by_label casual 2, formal 5, longer 1, name 0, no_emoji 4, no_nickname 3, no_questions 2, shorter 2. Scorer wall <10 s.
- DEV P339: 248 rows, 10 lives, wall 14:00:12–14:03:24 UTC (192 s). ACK339-start rows: 0.
- Misses: 23/40 feedback lives saved nothing; 2/20 controls saved something; only 17/40 exactly right. Name preference saved 0 times.
- Cost: RTX 5090 32 GB, $0.4991/h, ~1.47 h, ~$0.73 of $3.50 budget. Credit at start $9.97. 1 rental total (within 4). No watchdog trigger.
- BASE commit 87179e5c1f455ef22e6223592d2d61351b525bfc. READER b4fd93a2 match. self122 5ca02173 match. route122 did not raise.
- Copy-back: B 854, P 852, T 768, dev 248 rows match before destroy. Instance 52415511 destroyed by exact id; 0 rent-339-style live after (1 unrelated cairn-smoke box untouched).

Deviations:
- SEAL-code-rent differs from builder SEAL-code on 2/11 scripts (chat338_run, e2e336_run) because main evolved since the Windows attempt; tree = builder-outbox + main per kit; code never edited.
- SSH start commands timed out at the client (25–30 s) but each process started (verified by ps + log); no work lost.
- B start time approximate (~13:07 from ps; no .start file written on the first launch); end 13:22:28 from file mtime. P/T/dev/score have exact epoch start files.
- No judge files opened, no panel reply quoted, no other model downloaded.

What it means in plain high-school English:
- The style saver mostly did not save anything: on 40 feedback cases it got 17 exactly right and saved nothing 23 times, with 0 wrong saves. On 20 control cases that look like feedback but are not, it saved 2 times when it should save 0.
- Because the bar was 32/40 and 0/20, both fail. The 2 control saves also cross the proved-wrong line, so by the fixed rule this version is proved wrong on not saving when it should not.
- On normal dev chat it saved 0 times, which is what was wanted, so that part passes.
- What it does not mean: it does not mean the replies are good or bad — the blind day-3 judging was not run here, so P339.3 is still open. It also does not mean the harness is broken — unlike Windows, all 3 arms ran fine on Linux.

PUSH: artifacts/claude-style339-20260924/RESULTS-rent.md, artifacts/claude-style339-20260924/SEAL-code-rent.sha256.txt, artifacts/claude-style339-20260924/run (9 files), artifacts/claude-style339-20260924/dev (1 file), artifacts/fable-predictions-ledger.md (1 appended line).
