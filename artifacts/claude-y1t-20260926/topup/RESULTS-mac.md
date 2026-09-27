# y1t topup RESULTS (label: y1t-topup, Mac run)

## Run identity
- origin/main commit: 70523d6753fcd04fb41592a51ab53bce564bb2cc
- origin/builder-outbox commit at fetch: 6011a7d093ef959e49ca857fba901626bf3f1b3a
- Label: y1t-topup. GPU: no (Mac CPU; GLM 5.3 Flash calls through Ben's opencode subscription, $0 extra). No OpenRouter, no reader, no rental, no BensPC.
- Script: scripts/claude_lis320_glm_oclow.py (helper v1.1, each call deletes its own opencode session) with "--variant low", unchanged.
- W=3: the Director's 20:06 UTC share of the opencode route's budget of 16 parallel calls.
- DUPLICATE GATE: clear (origin/builder-outbox had no artifacts/claude-y1t-20260926/topup/ at fetch). No resume: no topup/raw_new.jsonl on builder-outbox; fresh start, log is topup.log, report is RESULTS-mac.md.
- WAIT: no wait needed; lis320-pilot4-mac already finished (builder-outbox has its pilot4/RESULTS.md, committed as 8c56bf74e).
- Common rules followed: additive only (new topup/ dir + files, no edits/deletes), fictional names (seed generator), TEST-ONLY panels never read, at most 4 parallel processes (W=3), report in final reply.

## Wall time
- Wording start: Sat Sep 26 22:13:27 UTC 2026
- Wording end: Sun Sep 27 00:45:03 UTC 2026
- Wall: ~151.6 min (within the 170-minute TIME CAP).

## Seeds (step 2, verbatim)
- `{"dialogs": 2400, "turns": 16816, "intents": {"ambiguous_pronoun": 517, "ask": 1253, "backref": 1548, "confirm": 480, "correct": 1586, "doubt": 544, "former": 1271, "hypothetical": 516, "jobhome": 825, "negation_only": 484, "plan": 482, "question": 502, "smalltalk": 652, "someone_else": 468, "teach": 5688}}`
- Split: `{"seeds": 2400, "raw_rows": 1021, "parsed_kept": 645, "to_redo": 1755, "raw_rows_unparsed": 376}` (to_redo 1755 as expected)

## Hash checks (all match, else would have stopped with SEED-MISMATCH)
- seeds.jsonl = 42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43 OK
- split/seeds_redo.jsonl = e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b OK
- scripts/claude_glm_opencode_v11.py = 7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4 OK
- scripts/claude_lis320_glm_oc.py = 6fe3c80f44d2dff93ff27f643265d07e6bef41303858803d1073e2958874bb09 OK
- scripts/claude_lis320_glm_oclow.py = cd7b7c48a2a757eefb29cc9631fad3307392726981fb8943d7d6876b6b30ed90 OK

## Selftests (both pass)
- glm_oclow: `[glm320] s320-1-00004 ok`, `lis320 glm_oc selftest 4/4 ok`, `lis320 glm_oclow selftest ok (variant low on the run line; no network)`
- topup: `selftest ok`

## System
- uptime: `18:13 up 3 days, 8:06, 4 users, load averages: 64.03 61.23 50.78`
- df: `/dev/disk3s1s1 460 1G-blocks, Used 12, Available 50, Capacity 21%` (well above the stop floor)
- opencode sessions (count only, from helper project folder $D): before = 5, after = 7. v1.1 deletes only the sessions it creates; the +2 is other concurrent route users (never touched another session; no config/auth file read).

## Wording (W=3, --batch 40, --max-minutes 150, --max-failed 50; log topup.log)
- Totals (last line of topup.log, verbatim): `{"calls": 1440, "parsed": 1360, "skipped": 0, "failed_calls": 0, "batches": 36, "stopped": "time", "minutes": 151.6}`
- "call failed" lines in topup.log: 0. No errors, nothing to report per error.
- Stopped "time" (not "failed", no rerun rule triggered): 1440 of 1755 redo dialogs worded; ~315 remain for a follow-up run, which resumes from the pushed raw_new.jsonl per step 1.

## Counts (step 5, raw_new.jsonl)
- lines: 1440
- rows with parsed not null: 1360
- rows with parsed null: 80
- distinct dialog ids: 1440

## Deviation
- TREE deviation: the spec's `git archive` set omits design/v3/60-listener/relation-names.txt, which scripts/claude_lis320_seed.py reads at line 46 (run failed with FileNotFoundError without it). Additionally extracted `git archive origin/main design/v3/60-listener` into $D only (temp dir, not the worktree). No worktree/test files touched.
- Shell deviation: `$PY` as a plain string does not word-split under zsh, so uv was invoked by explicit path with identical flags (`uv run --offline --no-project --python 3.12 python -B`).

## Files pushed (PUSH: artifacts/claude-y1t-20260926/topup)
- raw_new.jsonl (1440 lines), topup.log, RESULTS-mac.md
- Temp dir $D removed after copy; confirmed gone.
