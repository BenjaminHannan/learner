# rd-378k label gate through GPT-6 Luna (gate3luna) = FAIL, proved wrong as registered (Trustworthy notes thread, 2026-09-27 10:00 UTC)

Luna is too strict for the blind judges. It turned down 121 notes the judges passed and passed 14 they turned down.
Agreement is 489 of 624 (78.4%) against a bar of 85%, and no call was lost to the route. PASSMARKS-K therefore
registers this as a FAIL of the Luna route, and no Luna grade trains anything.

## Source
- The run: job 006-rd378k-gate3luna. Its agent (the builder) died on its own model's rate limit at about 07:25 UTC. Its
  nohup'd gate process (uv PID 12201) kept running. It ran in the job's temp tree, a `git archive` of e10b39b4b (the
  SEAL-ADD-K commit). It started at about 04:29 UTC; this time is inferred from its elapsed time. It ended before
  08:42 UTC.
- The copy: the files were copied out by the sealed finisher scripts/claude_rd378_finish.sh (sha256 6e01bfaf...). Job
  000-rescue3-rd378 started it (BASH-ONLY, c0a338df0). It pushed them to builder-outbox as 1afb020e7 and they were
  copied here (gate3luna/, pilot-luna/pilot-log.txt).
- Checked: the files contain no key text. The label rows carry ids, turn numbers and verdict words only.
- Seals: the 006 agent's transcript (runs/006-rd378k-gate3luna, go1.err.txt) shows 30 OK lines. They are:
  - SEAL-ADD-K 5, SEAL-ADD-H 1, SEAL-ADD-F 3, SEAL-ADD-E 2, SEAL-ADD-D 2, SEAL-ADD-C 2, SEAL 15;
  - the only FAILED line is scripts/claude_lis300_train.py, the one PASSMARKS-D allows.
- Checks before the run:
  - `claude_luna_run.py --check`: "luna bound ok";
  - teacher3oc selftest: "1/1 ok";
  - pilot PASS: 4 dialogs, 0 unparsed, 0 failed calls (pilot-luna/pilot-log.txt).
- The gate command matches PASSMARKS-K step 2: `--only-hash 3 --hash-rem 1 --out .../gate3luna`.

## Rows (PASSMARKS-K step 2 = addenda E and F), blind recount
The recount was done by scripts/claude_rd378k_recount.py (21ed9e52c). It is written apart from `teacher.py agree`, and
a dry run on gate2 reproduces VERIFY-gate2.md exactly. Its numbers equal the gate's own agree lines (gate3luna/agree.txt).

| Row | Bar | Got | Verdict |
|---|---|---|---|
| overall, ok vs not ok | agreement >= 85% and kappa >= 0.5 | 489 of 624 (78.4%), kappa 0.539 | FAIL |
| untrue notes | teacher "ok" on <= 15% of judge-unsupported notes | 9 of 296 (3.0%) | PASS |
| coverage, chat | usable >= 21 of 23 | 23 of 23 | PASS |
| coverage, overheard | usable >= 14 of 15 | 15 of 15 | PASS |

- Route losses (addendum H, as PASSMARKS-K defines them): 0 failed tries, 0 route-loss tries, 0 route-loss dialogs.
  failures.jsonl is empty.
- Proved wrong (PASSMARKS-K): agreement is below 85% with no route loss. So Luna, through teacher3, does not grade
  like the blind judges.

Report only:
- pass A alone: 502 of 624 (80.4%), kappa 0.589, untrue 15 of 296;
- failed calls: 0; missed_unknown_turns: 2;
- teacher counts: ok 164, unsupported 321, bad_cite 93, bad_when 28, bad_form 18; cost $0 (Codex plan);
- wall time: not recorded, because the agent died before step 8. Other notes by the same measure: at 07:25 UTC,
  27 of 38 dialogs were done after 2 h 56 min.

## Finding (counts only, not a verdict row): the misses run one way
Judge verdict (rows) against the Luna teacher's two-pass verdict (columns), for the 624 compared notes:

| judge \ teacher | ok | unsupported | bad_cite | bad_when | bad_form |
|---|---|---|---|---|---|
| ok (271) | 150 | 41 | 58 | 19 | 3 |
| unsupported (296) | 9 | 270 | 11 | 1 | 5 |
| bad_cite (29) | 3 | 5 | 21 | 0 | 0 |
| bad_when (12) | 1 | 1 | 2 | 8 | 0 |
| bad_form (16) | 1 | 4 | 1 | 0 | 10 |

- The 135 disagreements split 121 to 14. In 121, the judges said ok and Luna did not; the largest share was
  bad_cite, 58. In 14, Luna said ok and the judges did not.
- Pass A alone splits 98 to 24 (80.4%). So the second pass makes the teacher stricter still, but pass A also fails
  the bar.
- Agreement by kind: chat 267 of 344, overheard 222 of 280.
- Suggested (not shown): Luna reads the cite and time rules more strictly than the judges did. These counts cannot
  tell which side is right. The gate is defined as agreement with the judges, so the FAIL stands.

## What happens next (fixed in PASSMARKS-K before this run)
- This is a registered FAIL of the Luna route. No Luna grade trains anything. rd-378g ADDENDUM-I's grades (the held
  rd378g-label3luna) do not run.
- After GLM's weekly reset, a GLM-low gate (gate3low2) may run on the same 38 dialogs. The Thread manager reviews it
  first, and it is reported as the second route tried on these dialogs.
- labeller v3 stays the last labeller version (the Thread manager's 18:32 rule). Nothing here was used to change it.
